/*
 * The sampling harness -- see sbv_sample.h for what this is and is not.
 *
 * Record format, one block per test, on stdout:
 *
 *   V <name> <index|-> <bits> <off> <len> <hex>   one per drawn input,
 *                                       where off/len locate it on the tape
 *   M <name> <nbytes> <hex>            one per tagged region, contents after
 *   D <fdN> <flags> <mode> <offset> <nbytes> <hex>  one per tracked fd
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

#undef main
#undef open
#undef write
#undef close

#include "sbv_sample.h"

#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* The build redirects the target's exit() here with -Dexit=sbv_exit. This
 * file defines the stand-in, so it must see the name unredirected. */
#undef exit

#define SBV_MAX_REGIONS 16
#define SBV_MAX_REGION_LEN 4096
#define SBV_MAX_FILE_PATHS 16
#define SBV_MAX_FILE_CONTENT 4096
#define SBV_MAX_CHUNKS 64
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

/* Tagged memory --------------------------------------------------------- */

typedef struct {
    char name[SBV_NAME_LEN];
    unsigned char *addr;
    size_t len;
} region_t;

static region_t g_regions[SBV_MAX_REGIONS];
static int g_nregions;

/* Tagged file paths ----------------------------------------------------- */

typedef struct {
    char name[SBV_NAME_LEN];
    char path[SBV_NAME_LEN];
} file_path_t;

static file_path_t g_file_paths[SBV_MAX_FILE_PATHS];
static int g_nfile_paths;

/* File sandbox ---------------------------------------------------------- */

static int g_sandbox_ready;

static void sbv_init_sandbox(void) {
    char tmpl[] = "/tmp/sbv_sandbox_XXXXXX";
    char *dir;

    if (g_sandbox_ready)
        return;

    dir = mkdtemp(tmpl);
    if (!dir) {
        fprintf(stderr, "sbv: cannot create sandbox dir\n");
        return;
    }

    if (chroot(dir) != 0) {
        fprintf(stderr, "sbv: cannot chroot to sandbox\n");
        if (chdir(dir) != 0)
            fprintf(stderr, "sbv: cannot chdir to sandbox\n");
        g_sandbox_ready = 1;
        return;
    }

    if (chdir("/") != 0) {
        fprintf(stderr, "sbv: cannot chdir to /\n");
        return;
    }

    g_sandbox_ready = 2;
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

static void sbv_cleanup_files(void) {
    int i;
    for (i = 0; i < g_nfile_paths; i++)
        unlink(g_file_paths[i].path);
}

/* File descriptor tracking ---------------------------------------------- */

#define SBV_MAX_FD_TRACKS 16

typedef struct {
    int    fd;
    char   path[SBV_NAME_LEN];
    int    flags;
    int    mode;
    size_t offset;
    int    closed;
} fd_track_t;

static fd_track_t g_fd_tracks[SBV_MAX_FD_TRACKS];
static int g_nfd_tracks;
static int g_fd_tracking;

static fd_track_t *fd_track_find(int fd) {
    int i;
    for (i = 0; i < g_nfd_tracks; i++)
        if (g_fd_tracks[i].fd == fd)
            return &g_fd_tracks[i];
    return NULL;
}

int sbv_open(const char *path, int flags, ...) {
    int fd, mode = 0;

    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = va_arg(ap, int);
        va_end(ap);
        fd = open(path, flags, mode);
    } else {
        fd = open(path, flags);
    }

    if (g_fd_tracking && fd >= 0 && g_nfd_tracks < SBV_MAX_FD_TRACKS) {
        fd_track_t *t = &g_fd_tracks[g_nfd_tracks++];
        t->fd = fd;
        if (path)
            sbv_strcpy(t->path, sizeof(t->path), path);
        else
            t->path[0] = '\0';
        t->flags = flags;
        t->mode = mode;
        t->offset = 0;
        t->closed = 0;
    }

    return fd;
}

ssize_t sbv_write(int fd, const void *buf, size_t count) {
    ssize_t n = write(fd, buf, count);

    if (g_fd_tracking && n > 0) {
        fd_track_t *t = fd_track_find(fd);
        if (t)
            t->offset += (size_t)n;
    }

    return n;
}

int sbv_close(int fd) {
    if (g_fd_tracking) {
        fd_track_t *t = fd_track_find(fd);
        if (t)
            t->closed = 1;
    }

    return close(fd);
}

static void sbv_cleanup_fd_files(void) {
    int i;
    for (i = 0; i < g_nfd_tracks; i++)
        if (g_fd_tracks[i].path[0])
            unlink(g_fd_tracks[i].path);
}

/* File API (concrete) --------------------------------------------------- */

/*
 * Concrete implementations of the summary file API (__file_create etc.).
 *
 * The generated test uses these in setup code for descriptor/pointer file
 * args: it creates a file, opens it, optionally writes initial data, and
 * passes the resulting fd to the function under test.
 *
 * Because this file #undefs open/write/close, the calls here reach libc
 * directly.  sbv_open/sbv_write/sbv_close are used when fd tracking is
 * desired (the fd that will be handed to the function under test).
 */

int __file_create(const char *name) {
    int fd;

    sbv_init_sandbox();

    if (!name || !name[0])
        return -1;

    fd = open(name, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0)
        return -1;

    close(fd);
    return 1;
}

int __file_open(const char *name, const char *flags) {
    int oflags = 0;

    if (!flags)
        return -1;

    if (flags[0] == 'r' && flags[1] == '+')
        oflags = O_RDWR;
    else if (flags[0] == 'r')
        oflags = O_RDONLY;
    else if (flags[0] == 'w' && flags[1] == '+')
        oflags = O_RDWR | O_CREAT | O_TRUNC;
    else if (flags[0] == 'w')
        oflags = O_WRONLY | O_CREAT | O_TRUNC;
    else if (flags[0] == 'a' && flags[1] == '+')
        oflags = O_RDWR | O_CREAT | O_APPEND;
    else if (flags[0] == 'a')
        oflags = O_WRONLY | O_CREAT | O_APPEND;
    else
        return -1;

    return sbv_open(name, oflags, 0644);
}

ssize_t __file_write(int fd, const void *buf, size_t count) {
    return sbv_write(fd, buf, count);
}

ssize_t __file_read(int fd, void *buf, size_t count) {
    return read(fd, buf, count);
}

int __file_close(int fd) {
    return sbv_close(fd);
}

ssize_t __file_set_offset(int fd, size_t offset) {
    off_t r = lseek(fd, (off_t)offset, SEEK_SET);

    if (r >= 0 && g_fd_tracking) {
        fd_track_t *t = fd_track_find(fd);
        if (t)
            t->offset = (size_t)r;
    }

    return r < 0 ? -1 : (ssize_t)r;
}

/* Emitting records ------------------------------------------------------ */

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

/* Drawing inputs -------------------------------------------------------- */

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

void _assert(int cnstr) {
    __assume(cnstr);
}

void sbv_exit(int code) {
    (void)code;
    g_total_exited++;
    longjmp(g_reject_jmp, 1);
}

int _EQ_(sbv_value a, sbv_value b) { return a == b; }
int _NEQ_(sbv_value a, sbv_value b) { return a != b; }
int _LT_(sbv_value a, sbv_value b) { return a < b; }
int _LE_(sbv_value a, sbv_value b) { return a <= b; }
int _GT_(sbv_value a, sbv_value b) { return a > b; }
int _GE_(sbv_value a, sbv_value b) { return a >= b; }

int _ULT_(sbv_value a, sbv_value b) {
    return (unsigned long)a < (unsigned long)b;
}

int _ULE_(sbv_value a, sbv_value b) {
    return (unsigned long)a <= (unsigned long)b;
}

int _UGT_(sbv_value a, sbv_value b) {
    return (unsigned long)a > (unsigned long)b;
}

int _UGE_(sbv_value a, sbv_value b) {
    return (unsigned long)a >= (unsigned long)b;
}

int _NOT_(int c) { return !c; }
int _AND_(int a, int b) { return a && b; }
int _OR_(int a, int b) { return a || b; }

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
 * function's helper library routes malloc through mem_alloc so angr can track
 * the region, and that override applies to the whole program:
 *
 *     lib.c:   void *malloc(size_t n) { return mem_alloc(n); }
 *
 * so a mem_alloc that called malloc would call straight back into itself.
 * Confirmed as the cause of the strdup harness dying with SIGSEGV. The damage
 * is wider than it looks, too: every libc routine that allocates internally
 * -- printf among them -- enters the same cycle.
 *
 * Bump allocation, reset per execution. Nothing here needs to reuse freed
 * space: a run draws a bounded input and ends.
 */
typedef struct {
    void *ptr;
    size_t size;
} chunk_t;

static chunk_t g_chunks[SBV_MAX_CHUNKS];

static unsigned char g_arena[SBV_ARENA_SIZE];
static size_t g_arena_pos;

void *mem_alloc(size_t bytes) {
    unsigned char *ptr;
    size_t aligned = (bytes + 7u) & ~(size_t)7u;
    int i;

    if (aligned == 0)
        aligned = 8;

    if (g_arena_pos + aligned > sizeof(g_arena)) {
        fail("the sampling arena is exhausted");
        return NULL;
    }

    ptr = &g_arena[g_arena_pos];
    g_arena_pos += aligned;

    for (i = 0; i < SBV_MAX_CHUNKS; i++) {
        if (g_chunks[i].ptr == NULL) {
            g_chunks[i].ptr = ptr;
            g_chunks[i].size = bytes;
            break;
        }
    }

    return ptr;
}

void mem_free(void *ptr) {
    int i;

    /* Forgotten, not reclaimed: the arena is rewound wholesale when the next
     * execution starts, and a run is far too short for reuse to matter. */
    for (i = 0; i < SBV_MAX_CHUNKS; i++) {
        if (g_chunks[i].ptr == ptr) {
            g_chunks[i].ptr = NULL;
            g_chunks[i].size = 0;
            break;
        }
    }
}

size_t n_allocd(void *ptr) {
    int i;

    for (i = 0; i < SBV_MAX_CHUNKS; i++)
        if (g_chunks[i].ptr == ptr)
            return g_chunks[i].size;

    return 0;
}

void allocd(void *ptr, size_t size) {
    (void)size;
    __assume(ptr != NULL);
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

    if (!sbv_path_safe(path))
        return;

    sbv_init_sandbox();

    fp = &g_file_paths[g_nfile_paths++];
    sbv_strcpy(fp->name, sizeof(fp->name), name);
    sbv_strcpy(fp->path, sizeof(fp->path), path);
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
    int i;

    if (!g_record) {
        g_nregions = 0;
        sbv_cleanup_files();
        g_nfile_paths = 0;
        sbv_cleanup_fd_files();
        g_nfd_tracks = 0;
        return;
    }

    for (i = 0; i < g_nregions; i++) {
        printf("M %s %lu ", g_regions[i].name,
               (unsigned long)g_regions[i].len);
        put_hex(g_regions[i].addr, g_regions[i].len);
        putchar('\n');
    }

    for (i = 0; i < g_nfile_paths; i++) {
        int exists = access(g_file_paths[i].path, F_OK) == 0 ? 1 : 0;
        int nbytes = 0;
        unsigned char buf[SBV_MAX_FILE_CONTENT];

        if (exists) {
            int fd = open(g_file_paths[i].path, O_RDONLY);
            if (fd >= 0) {
                int n = read(fd, buf, sizeof(buf));
                if (n > 0) nbytes = n;
                close(fd);
            }
        }

        printf("F %s %d %d ", g_file_paths[i].name, exists, nbytes);
        if (nbytes > 0)
            put_hex(buf, (size_t)nbytes);
        putchar('\n');
    }

    sbv_cleanup_files();

    for (i = 0; i < g_nfd_tracks; i++) {
        int symfd = 3 + i;
        int nbytes = 0;
        unsigned char buf[SBV_MAX_FILE_CONTENT];

        if (g_fd_tracks[i].path[0]) {
            int rfd = open(g_fd_tracks[i].path, O_RDONLY);
            if (rfd >= 0) {
                int n = read(rfd, buf, sizeof(buf));
                if (n > 0) nbytes = n;
                close(rfd);
            }
        }

        printf("D fd%d %d %d %lu %d ",
               symfd,
               g_fd_tracks[i].flags,
               g_fd_tracks[i].mode,
               (unsigned long)g_fd_tracks[i].offset,
               nbytes);
        if (nbytes > 0)
            put_hex(buf, (size_t)nbytes);
        putchar('\n');
    }

    sbv_cleanup_fd_files();

    if (ret != 0 && bits != 0) {
        unsigned char bytes[sizeof(long double)];
        size_t nbytes = (bits + 7) / 8;

        if (nbytes > sizeof(bytes))
            nbytes = sizeof(bytes);

        sbv_memcpy(bytes, (const unsigned char *)ret, nbytes);

        printf("R %lu %d ", (unsigned long)bits, is_pointer ? 1 : 0);
        put_hex(bytes, nbytes);
        putchar('\n');
    }

    printf("E ok %s\n", test);
    g_nregions = 0;
    g_nfile_paths = 0;
    g_nfd_tracks = 0;
}

/* Driver interface ------------------------------------------------------ */

static void reset(const unsigned char *data, size_t len, int record) {
    g_input = data;
    g_input_len = len;
    g_input_pos = 0;

    g_nregions = 0;
    g_nfile_paths = 0;
    g_nfd_tracks = 0;
    g_fd_tracking = 1;
    g_record = record;

    /* Rewind the arena wholesale: each execution allocates from scratch, and
     * the persistent loop would otherwise exhaust it after enough runs. */
    g_arena_pos = 0;
    for (int i = 0; i < SBV_MAX_CHUNKS; i++) {
        g_chunks[i].ptr = NULL;
        g_chunks[i].size = 0;
    }
}

int sbv_sample_exec(const unsigned char *data, size_t len,
                    int (*tests)(void), int record) {
    reset(data, len, record);
    g_total_execs++;

    sbv_init_sandbox();

    if (setjmp(g_reject_jmp) != 0) {
        if (record)
            printf("E rejected\n");
        return SBV_REJECTED;
    }

    tests();
    return SBV_OK;
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
