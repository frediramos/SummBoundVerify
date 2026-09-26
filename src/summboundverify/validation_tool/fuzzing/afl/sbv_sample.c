/*
 * The sampling harness -- see sbv_sample.h for what this is and is not.
 *
 * Record format, one block per test, on stdout:
 *
 *   V <name> <index|-> <bits> <off> <len> <hex>   one per drawn input,
 *                                       where off/len locate it on the tape
 *   M <name> <nbytes> <hex>            one per tagged region, contents after
 *   F <name> <exists> <nbytes> <hex>   one per tagged file path
 *   D fd<N> <flags> <mode> <offset> <size> <hex>   one per descriptor number
 *   R <bits> <is_pointer> <hex>        absent for a void function
 *   E ok <test>                        closes the block and names it
 *
 * and, for a run the test's own assumptions turned away:
 *
 *   E rejected
 *
 * A block is named at the end rather than the start because the draws are
 * emitted as they happen, before the test that owns them is known to have
 * finished. The reader accumulates lines and closes on E.
 *
 * Bytes are hex in memory order, so the reader interprets them with the
 * target's endianness -- the same bytes the symbolic side sees, unconverted.
 * That matters for floating point, where any conversion would destroy the
 * bit pattern that is the value under test.
 */

#include "sbv_unwrap.h"
#include "sbv_sample.h"

#include <fcntl.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define SBV_MAX_REGIONS 16
#define SBV_MAX_REGION_LEN 4096
#define SBV_MAX_FILE_PATHS 16
#define SBV_MAX_FD_TRACKS 16
#define SBV_MAX_FILE_CONTENT 4096
#define SBV_ARENA_SIZE (1u << 20)
#define SBV_NAME_LEN 64

/* Input tape ------------------------------------------------------------ */

static const unsigned char *g_input;
static size_t g_input_len;
static size_t g_input_pos;

static unsigned long g_total_execs;
static unsigned long g_total_rejected;
static unsigned long g_total_exited;

static int g_record;
static jmp_buf g_reject_jmp;

/*
 * One byte off the tape.
 *
 * Running off the end yields zeros rather than rejecting the run: AFL++ grows
 * an input only when the coverage it buys says to, so a short tape is the
 * normal case early on, and turning those runs away would starve the corpus
 * exactly when it is smallest.
 */
static unsigned char tape_byte(void) {
    if (g_input_pos >= g_input_len)
        return 0;

    return g_input[g_input_pos++];
}

/* Copying without libc: a test's helper library may redirect memcpy, and the
 * harness must not go through whatever it redirected it to. */
static void sbv_memcpy(unsigned char *dst, const unsigned char *src, size_t n) {
    size_t i;

    for (i = 0; i < n; i++)
        dst[i] = src[i];
}

static void sbv_strcpy(char *dst, size_t cap, const char *src) {
    size_t i;

    for (i = 0; src && src[i] && i + 1 < cap; i++)
        dst[i] = src[i];

    dst[i] = '\0';
}

/* File sandbox ---------------------------------------------------------- */

/*
 * Confine the files a run creates to a fresh directory.
 *
 * chroot needs root; without it the harness still works inside the
 * directory, and relative paths stay there because the generated test rejects
 * file names containing '/' (and sbv_path_safe rejects "..").
 */
static void sbv_init_sandbox(void) {
    static int ready;
    char tmpl[] = "/tmp/sbv_sandbox_XXXXXX";
    char *dir;

    if (ready)
        return;

    ready = 1;

    /* The symbolic side gives every file mode 0666 & ~022. */
    umask(022);

    dir = mkdtemp(tmpl);
    if (!dir) {
        fprintf(stderr, "sbv: cannot create sandbox dir\n");
        return;
    }

    if (chroot(dir) == 0) {
        if (chdir("/") != 0)
            fprintf(stderr, "sbv: cannot chdir to /\n");
    } else if (chdir(dir) != 0) {
        fprintf(stderr, "sbv: cannot chdir to sandbox\n");
    }
}

static int sbv_path_safe(const char *path) {
    if (!path || !path[0])
        return 0;
    if (path[0] == '/')
        return 0;
    if (strstr(path, ".."))
        return 0;
    return 1;
}

/* Up to `cap` bytes of the file at `path`. Zero if it cannot be read. */
static size_t read_path(const char *path, unsigned char *buf, size_t cap) {
    size_t total = 0;
    ssize_t n;
    int fd;

    fd = open(path, O_RDONLY);
    if (fd < 0)
        return 0;

    while (total < cap && (n = read(fd, buf + total, cap - total)) > 0)
        total += (size_t)n;

    close(fd);
    return total;
}

/* Tagged memory and file paths ------------------------------------------ */

typedef struct {
    char name[SBV_NAME_LEN];
    unsigned char *addr;
    size_t len;
} region_t;

static region_t g_regions[SBV_MAX_REGIONS];
static int g_nregions;

typedef struct {
    char name[SBV_NAME_LEN];
    char path[SBV_NAME_LEN];
} file_path_t;

static file_path_t g_file_paths[SBV_MAX_FILE_PATHS];
static int g_nfile_paths;

/* Descriptor tracking --------------------------------------------------- */

/*
 * One descriptor the test or the function under test opened.
 *
 * `offset` and `mode` are the kernel's view, snapshotted when the descriptor
 * is closed or, for one still open, when the test is recorded. `fp` is set
 * when the descriptor was handed out as a FILE*, whose buffer must be flushed
 * before the kernel's view is current.
 */
typedef struct {
    int fd;
    char path[SBV_NAME_LEN];
    int flags;
    int mode;
    size_t offset;
    int closed;
    FILE *fp;
} fd_track_t;

static fd_track_t g_fd_tracks[SBV_MAX_FD_TRACKS];
static int g_nfd_tracks;

/* The open track for `fd`. A number released by close() is reused by the
 * next open(), so a closed track never answers for it. */
static fd_track_t *fd_track_find(int fd) {
    int i;

    for (i = g_nfd_tracks - 1; i >= 0; i--)
        if (g_fd_tracks[i].fd == fd && !g_fd_tracks[i].closed)
            return &g_fd_tracks[i];

    return NULL;
}

static void fd_track_add(int fd, const char *path, int flags) {
    fd_track_t *t;

    if (fd < 0 || g_nfd_tracks >= SBV_MAX_FD_TRACKS)
        return;

    t = &g_fd_tracks[g_nfd_tracks++];
    t->fd = fd;
    sbv_strcpy(t->path, sizeof(t->path), path);
    t->flags = flags;
    t->mode = 0;
    t->offset = 0;
    t->closed = 0;
    t->fp = NULL;
}

static void fd_track_snapshot(fd_track_t *t) {
    struct stat st;
    off_t offset;

    if (t->fp)
        fflush(t->fp);

    offset = lseek(t->fd, 0, SEEK_CUR);
    t->offset = offset < 0 ? 0 : (size_t)offset;

    if (fstat(t->fd, &st) == 0)
        t->mode = (int)(st.st_mode & 07777);
}

/* A FILE* still attached to a retired track is leaked rather than closed:
 * its descriptor is gone, and its number may already belong to another. */
static void fd_track_retire(fd_track_t *t) {
    t->closed = 1;
    t->fp = NULL;
}

/* Snapshot and retire `t`, just before its descriptor is released. */
static void fd_track_close(fd_track_t *t) {
    fd_track_snapshot(t);
    fd_track_retire(t);
}

/*
 * Whether a later track reuses the number of track `i`.
 *
 * The symbolic side keys descriptors by number too, and after a close and a
 * reopen it describes the newer one, so only the latest track per number is
 * recorded.
 */
static int fd_track_superseded(int i) {
    int j;

    for (j = i + 1; j < g_nfd_tracks; j++)
        if (g_fd_tracks[j].fd == g_fd_tracks[i].fd)
            return 1;

    return 0;
}

static int optional_mode(int flags, va_list ap) {
    return (flags & O_CREAT) ? va_arg(ap, int) : 0;
}

int sbv_open(const char *path, int flags, ...) {
    va_list ap;
    int fd, mode;

    va_start(ap, flags);
    mode = optional_mode(flags, ap);
    va_end(ap);

    fd = open(path, flags, mode);
    fd_track_add(fd, path, flags);
    return fd;
}

int sbv_creat(const char *path, mode_t mode) {
    int fd = creat(path, mode);

    fd_track_add(fd, path, O_WRONLY | O_CREAT | O_TRUNC);
    return fd;
}

/* The path is recorded as given: relative to `dirfd`, which is only the
 * sandbox when `dirfd` is AT_FDCWD. */
int sbv_openat(int dirfd, const char *path, int flags, ...) {
    va_list ap;
    int fd, mode;

    va_start(ap, flags);
    mode = optional_mode(flags, ap);
    va_end(ap);

    fd = openat(dirfd, path, flags, mode);
    fd_track_add(fd, path, flags);
    return fd;
}

/* The copy shares the original's file and offset, as __file_dup's does. */
int sbv_dup(int fd) {
    fd_track_t *t = fd_track_find(fd);
    int fd2 = dup(fd);

    if (t && fd2 >= 0)
        fd_track_add(fd2, t->path, t->flags);

    return fd2;
}

int sbv_dup2(int fd, int fd2) {
    fd_track_t *t, *replaced;
    int r;

    if (fd == fd2)
        return dup2(fd, fd2);

    /* dup2 silently closes whatever `fd2` referred to, so its state has to
     * be taken before the call reuses the number. */
    replaced = fd_track_find(fd2);
    if (replaced)
        fd_track_snapshot(replaced);

    r = dup2(fd, fd2);
    if (r < 0)
        return r;

    if (replaced)
        fd_track_retire(replaced);

    t = fd_track_find(fd);
    if (t)
        fd_track_add(r, t->path, t->flags);

    return r;
}

int sbv_close(int fd) {
    fd_track_t *t = fd_track_find(fd);

    if (t)
        fd_track_close(t);

    return close(fd);
}

int sbv_fclose(FILE *fp) {
    fd_track_t *t;

    /* The FILE may not be the track's own (the function fdopen'd the
     * descriptor itself), so flush it here rather than rely on t->fp. */
    fflush(fp);

    t = fd_track_find(fileno(fp));
    if (t)
        fd_track_close(t);

    return fclose(fp);
}

/* File API (concrete) --------------------------------------------------- */

/*
 * Concrete counterparts of the summary's file primitives, for the generated
 * test's setup. Descriptors handed to the function under test go through
 * sbv_open so they are tracked; the probe in __file_create does not, since
 * the symbolic side's __file_create opens no descriptor.
 */

int __file_create(const char *name) {
    int fd;

    if (!name || !name[0])
        return -1;

    fd = open(name, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0)
        return -1;

    close(fd);
    return 1;
}

/* fopen-style mode strings, read the way the symbolic side's str_to_flag
 * reads them: 'b', 't', 'c' and 'e' are ignored. */
int __file_open(const char *name, const char *flags) {
    int plus = 0, oflags;
    const char *c;

    if (!flags || !flags[0])
        return -1;

    for (c = flags + 1; *c; c++) {
        if (*c == '+')
            plus = 1;
        else if (*c != 'b' && *c != 't' && *c != 'c' && *c != 'e')
            return -1;
    }

    switch (flags[0]) {
    case 'r':
        oflags = plus ? O_RDWR : O_RDONLY;
        break;
    case 'w':
        oflags = (plus ? O_RDWR : O_WRONLY) | O_CREAT | O_TRUNC;
        break;
    case 'a':
        oflags = (plus ? O_RDWR : O_WRONLY) | O_CREAT | O_APPEND;
        break;
    default:
        return -1;
    }

    return sbv_open(name, oflags, 0644);
}

ssize_t __file_write(int fd, const void *buf, size_t count) {
    return write(fd, buf, count);
}

ssize_t __file_set_offset(int fd, size_t offset) {
    off_t r = lseek(fd, (off_t)offset, SEEK_SET);

    return r < 0 ? -1 : (ssize_t)r;
}

static const char *fdopen_mode(int fd) {
    int flags = fcntl(fd, F_GETFL);

    if (flags < 0)
        return NULL;

    switch (flags & O_ACCMODE) {
    case O_RDONLY:
        return "r";
    case O_WRONLY:
        return (flags & O_APPEND) ? "a" : "w";
    default:
        return (flags & O_APPEND) ? "a+" : "r+";
    }
}

/*
 * The FILE* for `fd`, created on first use and handed out again after that,
 * as the symbolic side keeps one per descriptor.
 *
 * fdopen allocates the FILE through libc's malloc. A test whose helper
 * library redirects malloc to __mem_alloc (see the heap section) would get it
 * from the arena instead, and fclose would then hand an arena pointer to
 * glibc's free() -- the same hazard driver.c avoids stdio for. No such test
 * takes a FILE* today.
 */
FILE *__FILE_from_fd(int fd) {
    fd_track_t *t = fd_track_find(fd);
    const char *mode;
    FILE *fp;

    if (t && t->fp)
        return t->fp;

    mode = fdopen_mode(fd);
    if (!mode)
        return NULL;

    fp = fdopen(fd, mode);
    if (t)
        t->fp = fp;

    return fp;
}

/* Drawing inputs -------------------------------------------------------- */

static void put_hex(const unsigned char *bytes, size_t n) {
    static const char digits[] = "0123456789abcdef";
    size_t i;

    for (i = 0; i < n; i++) {
        putchar(digits[bytes[i] >> 4]);
        putchar(digits[bytes[i] & 0xf]);
    }
}

static void record_draw(const char *name, long index, int indexed,
                        const unsigned char *bytes, size_t bits,
                        size_t offset, size_t taken) {
    if (!g_record)
        return;

    printf("V %s ", name);

    if (indexed)
        printf("%ld ", index);
    else
        printf("- ");

    /* The tape offset and byte count are reported because a seed generator
     * needs to know where to put a value it wants this draw to produce, and
     * that layout is a property of the harness, not something worth
     * re-deriving from the generated source. `taken` is not always bits/8:
     * a scalar draw is capped at the width of sbv_value. */
    printf("%lu %lu %lu ",
           (unsigned long)bits, (unsigned long)offset, (unsigned long)taken);

    put_hex(bytes, (bits + 7) / 8);
    putchar('\n');
}

static sbv_value draw_value(char *name, size_t bits, long index, int indexed) {
    unsigned char bytes[sizeof(sbv_value)];
    sbv_value value = 0;
    size_t nbytes = (bits + 7) / 8;
    size_t offset = g_input_pos;
    size_t i;

    if (nbytes > sizeof(value))
        nbytes = sizeof(value);

    for (i = 0; i < sizeof(bytes); i++)
        bytes[i] = 0;

    for (i = 0; i < nbytes; i++)
        bytes[i] = tape_byte();

    /* Assemble little-endian, then hand back the value the test will store
     * into a possibly narrower variable. The record keeps the bytes, not the
     * assembled number, so the reader is not guessing at the width. */
    for (i = nbytes; i > 0; i--)
        value = (value << 8) | bytes[i - 1];

    record_draw(name, index, indexed, bytes, bits, offset, nbytes);
    return value;
}

sbv_value __sym_var_named(char *name, size_t bits) {
    return draw_value(name, bits, 0, 0);
}

sbv_value __sym_var_array(char *name, size_t index, size_t bits) {
    return draw_value(name, bits, (long)index, 1);
}

/* Bounding the domain --------------------------------------------------- */

void __assume(int cnstr) {
    if (cnstr)
        return;

    g_total_rejected++;
    longjmp(g_reject_jmp, 1);
}

void sbv_exit(int code) {
    (void)code;
    g_total_exited++;
    longjmp(g_reject_jmp, 1);
}

int _ULE_(sbv_value a, sbv_value b) {
    return (unsigned long)a <= (unsigned long)b;
}

/* Heap ------------------------------------------------------------------ */

/*
 * Abandon this run.
 *
 * Not an abort: the harness dying is what AFL++ reads as a crash, and a
 * crash the harness caused itself would be reported as a finding about the
 * function under test. Discarded like a rejected input instead.
 */
static void fail(const char *why) {
    fprintf(stderr, "sbv: %s\n", why);
    g_total_rejected++;
    longjmp(g_reject_jmp, 1);
}

/*
 * A private arena, rather than libc's allocator.
 *
 * This is not an optimisation, it is the only way this can work. A concrete
 * function's helper library routes malloc through __mem_alloc so angr can
 * track the region, and that override applies to the whole program:
 *
 *     lib.c:   void *malloc(size_t n) { return __mem_alloc(n); }
 *
 * so a __mem_alloc that called malloc would call straight back into itself.
 * Confirmed as the cause of the strdup harness dying with SIGSEGV. The damage
 * is wider than it looks, too: every libc routine that allocates internally
 * -- printf among them -- enters the same cycle.
 *
 * Bump allocation, rewound wholesale per execution. Nothing here needs to
 * reuse freed space: a run draws a bounded input and ends.
 */
static unsigned char g_arena[SBV_ARENA_SIZE];
static size_t g_arena_pos;

void *__mem_alloc(size_t nbytes) {
    unsigned char *ptr;
    size_t aligned = (nbytes + 7u) & ~(size_t)7u;

    if (aligned == 0)
        aligned = 8;

    if (g_arena_pos + aligned > sizeof(g_arena)) {
        fail("the sampling arena is exhausted");
        return NULL;
    }

    ptr = &g_arena[g_arena_pos];
    g_arena_pos += aligned;
    return ptr;
}

/* Recording the outcome ------------------------------------------------- */

void __mem_addr(char *name, void *addr, size_t len) {
    region_t *r;

    if (g_nregions >= SBV_MAX_REGIONS)
        return;

    if (len > SBV_MAX_REGION_LEN)
        len = SBV_MAX_REGION_LEN;

    r = &g_regions[g_nregions++];
    sbv_strcpy(r->name, sizeof(r->name), name);
    r->addr = (unsigned char *)addr;
    r->len = len;
}

void __file_addr(char *name, const char *path) {
    file_path_t *fp;

    if (g_nfile_paths >= SBV_MAX_FILE_PATHS)
        return;

    fp = &g_file_paths[g_nfile_paths++];
    sbv_strcpy(fp->name, sizeof(fp->name), name);
    sbv_strcpy(fp->path, sizeof(fp->path), path);
}

static void emit_regions(void) {
    int i;

    for (i = 0; i < g_nregions; i++) {
        printf("M %s %lu ", g_regions[i].name,
               (unsigned long)g_regions[i].len);
        put_hex(g_regions[i].addr, g_regions[i].len);
        putchar('\n');
    }
}

static void emit_files(void) {
    unsigned char buf[SBV_MAX_FILE_CONTENT];
    size_t nbytes;
    int i, exists;

    for (i = 0; i < g_nfile_paths; i++) {
        exists = access(g_file_paths[i].path, F_OK) == 0;
        nbytes = exists ? read_path(g_file_paths[i].path, buf, sizeof(buf)) : 0;

        printf("F %s %d %lu ", g_file_paths[i].name, exists,
               (unsigned long)nbytes);
        put_hex(buf, nbytes);
        putchar('\n');
    }
}

/* Content is read back through the path, not the descriptor: a descriptor
 * opened O_WRONLY cannot be read, and a closed one no longer exists. */
static void emit_fds(void) {
    unsigned char buf[SBV_MAX_FILE_CONTENT];
    struct stat st;
    size_t nbytes, size;
    fd_track_t *t;
    int i;

    for (i = 0; i < g_nfd_tracks; i++) {
        t = &g_fd_tracks[i];

        if (fd_track_superseded(i))
            continue;

        if (!t->closed)
            fd_track_snapshot(t);

        nbytes = read_path(t->path, buf, sizeof(buf));
        size = stat(t->path, &st) == 0 ? (size_t)st.st_size : nbytes;

        printf("D fd%d %d %d %lu %lu ", t->fd, t->flags, t->mode,
               (unsigned long)t->offset, (unsigned long)size);
        put_hex(buf, nbytes);
        putchar('\n');
    }
}

static void emit_return(void *ret, size_t bits, int is_pointer) {
    unsigned char bytes[sizeof(long double)];
    size_t nbytes = (bits + 7) / 8;

    if (ret == 0 || bits == 0)
        return;

    if (nbytes > sizeof(bytes))
        nbytes = sizeof(bytes);

    sbv_memcpy(bytes, (const unsigned char *)ret, nbytes);

    printf("R %lu %d ", (unsigned long)bits, is_pointer ? 1 : 0);
    put_hex(bytes, nbytes);
    putchar('\n');
}

/*
 * Put the sandbox back the way the test found it: release every descriptor
 * still open, delete every file the test touched, forget every tag.
 *
 * Runs after every test, recorded or not, and after a rejected run, so that
 * the next test starts from an empty directory with descriptor 3 free, as the
 * symbolic side's does.
 */
static void end_test(void) {
    fd_track_t *t;
    int i;

    for (i = 0; i < g_nfd_tracks; i++) {
        t = &g_fd_tracks[i];

        if (t->closed)
            continue;

        if (t->fp)
            fclose(t->fp);
        else
            close(t->fd);

        t->closed = 1;
    }

    for (i = 0; i < g_nfd_tracks; i++)
        if (g_fd_tracks[i].path[0])
            unlink(g_fd_tracks[i].path);

    for (i = 0; i < g_nfile_paths; i++)
        unlink(g_file_paths[i].path);

    g_nregions = 0;
    g_nfile_paths = 0;
    g_nfd_tracks = 0;
}

/*
 * Returning an address is different in kind from returning a value.
 *
 * The number itself carries no meaning across runs: symbolically it is
 * wherever angr laid the buffer out, concretely it is wherever the loader
 * did, and neither says anything about the other. Comparing them produced a
 * confident counterexample for a memcpy summary that is perfectly correct.
 *
 * So the flag travels with the value and the checker declines to compare it.
 * What a pointer return *does* mean -- which of the arguments it aliases --
 * would need the addresses of those arguments recorded on both sides, and
 * the symbolic side only knows them when regions are tagged with mem_addr.
 */
void sbv_record(char *test, void *ret, size_t bits, int is_pointer) {
    if (g_record) {
        emit_regions();
        emit_files();
        emit_fds();
        emit_return(ret, bits, is_pointer);
        printf("E ok %s\n", test);
    }

    end_test();
}

/* Driver interface ------------------------------------------------------ */

static void reset(const unsigned char *data, size_t len, int record) {
    g_input = data;
    g_input_len = len;
    g_input_pos = 0;
    g_record = record;

    /* Rewind the arena wholesale: each execution allocates from scratch, and
     * the persistent loop would otherwise exhaust it after enough runs. */
    g_arena_pos = 0;
}

void sbv_sample_exec(const unsigned char *data, size_t len,
                     int (*tests)(void), int record) {
    reset(data, len, record);
    g_total_execs++;

    sbv_init_sandbox();

    if (setjmp(g_reject_jmp) != 0) {
        end_test();
        if (record)
            printf("E rejected\n");
        return;
    }

    tests();
    end_test();
}

unsigned long sbv_sample_total_execs(void) {
    return g_total_execs;
}

unsigned long sbv_sample_total_rejected(void) {
    return g_total_rejected;
}

unsigned long sbv_sample_total_exited(void) {
    return g_total_exited;
}
