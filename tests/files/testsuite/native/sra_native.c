/*
 * The Symbolic Reflection API, run natively: every function does the real
 * Linux operation, and there are no symbolic values.
 *
 * Running the test suite on this (make run FS=native) uses the kernel as the
 * reference: a test that fails here expects something other than POSIX
 * behaviour, so it does not test a symbolic engine fairly either. Tests are
 * built with -DNATIVE, which makes their file names and flags concrete.
 *
 * A failed __assume or __sra_assert exits with status 1 and an error line in the
 * style of summbv's, numbered by its position in the test, for report.py.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <malloc.h>
#include <sys/stat.h>

#include "sra.h"

/* Reported by F_GETFL on 64-bit Linux for every file, though O_LARGEFILE is
 * 0 in user space there */
#define KERNEL_O_LARGEFILE 0100000

static void fail(const char *error, const char *message, int n) {
    fprintf(stderr, "%s: %s #%d does not hold\n", error, message, n);
    exit(1);
}

static void unsupported(const char *function) {
    fprintf(stderr, "NotImplementedApiError: %s is not supported natively\n", function);
    exit(1);
}

/* ============================================================================
 * Core primitives
 * ========================================================================== */

void __assume(cnstr_t cnstr) {
    static int n = 0;
    n++;
    if (!cnstr)
        fail("PreconditionError", "__assume", n);
}

void __sra_assert(cnstr_t cnstr) {
    static int n = 0;
    n++;
    if (!cnstr)
        fail("AssertionError", "__sra_assert", n);
}

void __report_error(const char *filename, unsigned int line, const char *message) {
    fprintf(stderr, "ReportError: Runtime error detected in '%s' at line %u: %s\n",
            filename, line, message);
    exit(1);
}

/* Nothing is symbolic, so every value is its own only value */
long __concretize(symbolic var) { return (long) var; }
long __maximize(symbolic var)   { return (long) var; }
long __minimize(symbolic var)   { return (long) var; }
int __is_symbolic(symbolic var) { (void) var; return 0; }
int __is_sat(cnstr_t cnstr)     { return cnstr != 0; }
int __is_certain(cnstr_t cnstr) { return cnstr != 0; }

/* Tests built with -DNATIVE make no symbolic values */
symbolic __sym_var(size_t size) {
    (void) size;
    unsupported("__sym_var");
    return 0;
}

symbolic __sym_var_named(char *name, size_t size) {
    (void) name; (void) size;
    unsupported("__sym_var_named");
    return 0;
}

symbolic __sym_var_array(char *name, size_t index, size_t size) {
    (void) name; (void) index; (void) size;
    unsupported("__sym_var_array");
    return 0;
}

/* There is one path, so there is no path condition to save */
void __push_pc(void) {}
void __pop_pc(void) {}

/* ============================================================================
 * Constraints: plain C truth values
 * ========================================================================== */

cnstr_t _NOT_(cnstr_t c)              { return !c; }
cnstr_t _OR_(cnstr_t a, cnstr_t b)    { return a || b; }
cnstr_t _AND_(cnstr_t a, cnstr_t b)   { return a && b; }

cnstr_t _LT_(symbolic a, symbolic b)  { return (long) a <  (long) b; }
cnstr_t _LE_(symbolic a, symbolic b)  { return (long) a <= (long) b; }
cnstr_t _GT_(symbolic a, symbolic b)  { return (long) a >  (long) b; }
cnstr_t _GE_(symbolic a, symbolic b)  { return (long) a >= (long) b; }
cnstr_t _EQ_(symbolic a, symbolic b)  { return (long) a == (long) b; }
cnstr_t _NEQ_(symbolic a, symbolic b) { return (long) a != (long) b; }

cnstr_t _ULT_(symbolic a, symbolic b) { return (unsigned long) a <  (unsigned long) b; }
cnstr_t _ULE_(symbolic a, symbolic b) { return (unsigned long) a <= (unsigned long) b; }
cnstr_t _UGT_(symbolic a, symbolic b) { return (unsigned long) a >  (unsigned long) b; }
cnstr_t _UGE_(symbolic a, symbolic b) { return (unsigned long) a >= (unsigned long) b; }

cnstr_t _ITE_(cnstr_t cond, cnstr_t a, cnstr_t b) { return cond ? a : b; }

cnstr_t _ITE_VAR_(cnstr_t cond, symbolic a, symbolic b) {
    return (cnstr_t) (long) (cond ? a : b);
}

/* ============================================================================
 * Lists: not used by the test suite
 * ========================================================================== */

list_t __lst_mk(void)                          { unsupported("__lst_mk"); return 0; }
list_t __lst_cons(symbolic v, list_t l)        { (void) v; (void) l; unsupported("__lst_cons"); return 0; }
cnstr_t __lst_empty(list_t l)                  { (void) l; unsupported("__lst_empty"); return 0; }
list_t __lst_tl(list_t l)                      { (void) l; unsupported("__lst_tl"); return 0; }
symbolic __lst_hd(list_t l)                    { (void) l; unsupported("__lst_hd"); return 0; }
size_t __lst_len(list_t l)                     { (void) l; unsupported("__lst_len"); return 0; }
list_t __lst_nbytes(char c, size_t n)          { (void) c; (void) n; unsupported("__lst_nbytes"); return 0; }
list_t __lst_zeros(size_t n)                   { (void) n; unsupported("__lst_zeros"); return 0; }

void __cond_write(void *ptr, symbolic c, cnstr_t pc) {
    if (pc)
        *(char *) ptr = (char) (long) c;
}

/* ============================================================================
 * Heap
 * ========================================================================== */

void *__mem_alloc(size_t nbytes)       { return malloc(nbytes); }
void __mem_free(void *ptr)             { free(ptr); }
size_t __n_allocd(void *ptr)           { return malloc_usable_size(ptr); }
size_t __allocd(void *ptr, size_t n)   { (void) ptr; return n; }

/* ============================================================================
 * Files
 * ========================================================================== */

/* The flags each descriptor from __file_open was opened with. __file_flags
 * reports them: F_GETFL does not keep creation flags such as O_CREAT. */
#define MAX_FDS 1024

static int opened_flags[MAX_FDS];
static int opened[MAX_FDS];

static void record(int fd, int flags) {
    if (fd >= 0 && fd < MAX_FDS) {
        opened[fd] = 1;
        opened_flags[fd] = flags;
    }
}

static void forget(int fd) {
    if (fd >= 0 && fd < MAX_FDS)
        opened[fd] = 0;
}

/* The open flags glibc's fopen uses for `mode` */
static int fopen_flags(const char *mode) {
    int flags;

    switch (mode[0]) {
    case 'r': flags = O_RDONLY; break;
    case 'w': flags = O_WRONLY | O_CREAT | O_TRUNC; break;
    case 'a': flags = O_WRONLY | O_CREAT | O_APPEND; break;
    default:  return -1;
    }

    if (strchr(mode, '+'))
        flags = (flags & ~O_ACCMODE) | O_RDWR;
    if (strchr(mode, 'x'))
        flags |= O_EXCL;
    if (strchr(mode, 'e'))
        flags |= O_CLOEXEC;

    return flags;
}

int __file_create(const char *name) {
    int fd = open(name, O_WRONLY | O_CREAT | O_EXCL, 0644);
    if (fd < 0)
        return -1;
    close(fd);
    return 1;
}

int __file_open(const char *name, const char *mode) {
    int flags = fopen_flags(mode);
    if (flags < 0)
        return -1;

    int fd = open(name, flags, 0666);
    record(fd, flags);
    return fd;
}

int __file_exists(const char *name) {
    return access(name, F_OK) == 0 ? 1 : 0;
}

int __file_delete(const char *name) {
    return unlink(name) == 0 ? 1 : -1;
}

int __file_close(int fd) {
    forget(fd);
    return close(fd) == 0 ? 0 : -1;
}

ssize_t __file_read(int fd, void *buffer, size_t count) {
    return read(fd, buffer, count);
}

ssize_t __file_write(int fd, const void *buffer, size_t count) {
    return write(fd, buffer, count);
}

ssize_t __file_size(int fd) {
    struct stat st;
    return fstat(fd, &st) == 0 ? st.st_size : -1;
}

ssize_t __file_offset(int fd) {
    return lseek(fd, 0, SEEK_CUR);
}

ssize_t __file_set_size(int fd, size_t size) {
    return ftruncate(fd, (off_t) size) == 0 ? (ssize_t) size : -1;
}

ssize_t __file_set_offset(int fd, size_t offset) {
    return lseek(fd, (off_t) offset, SEEK_SET);
}

int __file_set_mode(int fd, mode_t mode) {
    return fchmod(fd, mode) == 0 ? 1 : -1;
}

int __file_mode(int fd, mode_t *mode) {
    struct stat st;
    if (fstat(fd, &st) != 0)
        return -1;
    *mode = st.st_mode;
    return 1;
}

int __file_flags(int fd) {
    int flags = fcntl(fd, F_GETFL);
    if (flags < 0)
        return -1;

    /* A descriptor closed with close() rather than __file_close keeps its
     * record, so use one only if the kernel still agrees with it */
    int kept = O_ACCMODE | O_APPEND;
    if (fd < MAX_FDS && opened[fd] && (opened_flags[fd] & kept) == (flags & kept))
        return opened_flags[fd];

    return flags & ~KERNEL_O_LARGEFILE;
}

int __file_dup(int oldfd) {
    int fd = dup(oldfd);
    if (fd >= 0 && oldfd < MAX_FDS && opened[oldfd])
        record(fd, opened_flags[oldfd]);
    return fd;
}

int __file_dup2(int oldfd, int newfd) {
    int fd = dup2(oldfd, newfd);
    if (fd >= 0) {
        forget(fd);
        if (oldfd < MAX_FDS && opened[oldfd])
            record(fd, opened_flags[oldfd]);
    }
    return fd;
}

FILE *__FILE_from_fd(int fd) {
    return fdopen(fd, "r+");
}

int __fd_from_FILE(FILE *fp) {
    return fp ? fileno(fp) : -1;
}
