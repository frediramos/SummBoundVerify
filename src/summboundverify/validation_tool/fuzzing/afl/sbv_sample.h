/*
 * The sampling harness.
 *
 * This is deliberately *not* an implementation of the validation API. The
 * previous concrete backend tried to be one, and that was the design's weak
 * joint: primitives like push_pc(), is_sat() or _ITE_() describe a symbolic
 * state, and giving them concrete behaviour meant inventing a semantics they
 * do not have.
 *
 * Nothing here interprets a summary. The summary is executed symbolically, by
 * angr, and never compiled into this harness. What is compiled here is the
 * concrete function and the generated test that feeds it -- so the only
 * primitives that need a concrete meaning are the ones the *test* uses, and
 * every one of them has an obvious one once the values are concrete:
 *
 *   sym_var_*   draw this input's value from the fuzzer's byte tape
 *   assume      this input is outside the test's domain; discard the run
 *   _ULE_       compare two concrete values
 *   mem_addr    remember this region, so its final contents get recorded
 *
 * The names are the API's on purpose. The generated test is built by the same
 * code path for both engines, so an argument called "str" is called "str" on
 * both sides -- which is what lets a recorded sample be matched against the
 * formula angr produced for the summary.
 */

#ifndef SBV_SAMPLE_H
#define SBV_SAMPLE_H

#include <stddef.h>
#include <sys/types.h>

/* Widest value a drawn scalar can be handed back as. Pointer-sized, matching
 * `symbolic` in the stub prelude, so an argument declared in the generated
 * test converts the same way under both engines. */
typedef long sbv_value;

/* Drawing inputs -------------------------------------------------------- */

/*
 * The value of the input variable `name`, `bits` wide, taken from the tape.
 *
 * Bits beyond the requested width are zero, so assigning the result to a
 * narrower type loses nothing that was ever there.
 */
sbv_value __sym_var_named(char *name, size_t bits);

/*
 * The value of element `index` of the input array `name`.
 *
 * Recorded under the same (name, index) pair the symbolic side uses for it,
 * so an array is matched element by element rather than as an opaque blob.
 */
sbv_value __sym_var_array(char *name, size_t index, size_t bits);

/* Bounding the domain --------------------------------------------------- */

/*
 * Discard this run unless `cnstr` holds.
 *
 * The generated test bounds its inputs (`assume(_ULE_(n, MAX_NUM_1))`), and
 * those bounds are part of the summary's path condition on the symbolic side.
 * A sample that ignored them would satisfy no path and be reported as an
 * input the summary fails to cover -- a finding manufactured by the harness.
 */
void __assume(int cnstr);

/*
 * Stand-in for exit(), which the build redirects here with -Dexit=sbv_exit.
 *
 * A concrete function that calls exit() would take the harness down with it,
 * and AFL++ would read the dead process as a crash -- a finding manufactured
 * by the harness. There is no return value to record for such a run, so it
 * is discarded exactly as a rejected one is.
 */
void sbv_exit(int code);

/*
 * The one constraint operator the concrete test uses: the unsigned bound on
 * a scalar with a `maxvalue` (`__assume(_ULE_(n, MAX_NUM_1))`). Everything
 * else the test compares is written as plain C, and the summary -- the only
 * code that would use the rest -- is never compiled into this harness.
 */
int _ULE_(sbv_value a, sbv_value b);

/* Heap ------------------------------------------------------------------ */

/*
 * The allocation primitive, concretely.
 *
 * Allocating memory means the same thing whether the pointer is symbolic or
 * not. A concrete function's helper library routes malloc through
 * __mem_alloc so angr can track the region (the strdup tests do), and that
 * library is linked here too, so the name has to resolve.
 */
void *__mem_alloc(size_t nbytes);

/* Recording the outcome ------------------------------------------------- */

/*
 * Mark `len` bytes at `addr` as observable output, under `name`.
 *
 * Registered before the call and read after it, mirroring how get_cnstr lifts
 * memory contents on the symbolic side.
 */
void __mem_addr(char *name, void *addr, size_t len);

/*
 * Tag a file path for post-call observation.
 *
 * After the function under test returns, the file at `path` is checked for
 * existence and its contents are recorded. `name` is the join key matching
 * the symbolic side's `file_{name}_exists` and `file_{name}_byte_{i}`.
 */
void __file_addr(char *name, const char *path);

/*
 * Close the record for one test: the return value at `ret` (`bits` wide, or
 * 0/NULL for a void function) plus the current contents of every region
 * registered since the last record.
 *
 * `is_pointer` is passed on rather than inferred, because the bytes of an
 * address look exactly like the bytes of an integer and the two cannot be
 * checked the same way -- see the note in sbv_sample.c.
 */
void sbv_record(char *test, void *ret, size_t bits, int is_pointer);

/* File descriptor interception ------------------------------------------ */

/* glibc's FILE, named without pulling <stdio.h> into every translation unit:
 * a concrete function may define its own printf or puts. */
struct _IO_FILE;

/*
 * Wrappers around the calls that create or release a descriptor.
 *
 * The build redirects the target's calls here with -Dopen=sbv_open etc.;
 * sbv_unwrap.h undoes that for sbv_sample.c and driver.c. Each wrapper calls
 * the real function and remembers which path, flags and file the descriptor
 * refers to.
 *
 * read, write and lseek are deliberately not wrapped. The offset is asked of
 * the kernel -- lseek(fd, 0, SEEK_CUR) -- when a descriptor is closed and
 * when the test is recorded, which also covers O_APPEND, descriptors sharing
 * an offset through dup, and I/O through stdio or readv/writev.
 */
int sbv_open(const char *path, int flags, ...);
int sbv_creat(const char *path, mode_t mode);
int sbv_openat(int dirfd, const char *path, int flags, ...);
int sbv_dup(int fd);
int sbv_dup2(int fd, int fd2);
int sbv_close(int fd);
int sbv_fclose(struct _IO_FILE *fp);

/* File API (concrete) --------------------------------------------------- */

/*
 * Concrete implementations of the file primitives the generated test uses.
 *
 * Used by the test setup when an argument has type 'descriptor' or 'pointer'
 * in its argspec: the test creates a file, opens it, optionally writes its
 * initial contents, and passes the resulting fd (or FILE*) to the function
 * under test.
 */
int __file_create(const char *name);
int __file_open(const char *name, const char *flags);
ssize_t __file_write(int fd, const void *buf, size_t count);
ssize_t __file_set_offset(int fd, size_t offset);
struct _IO_FILE *__FILE_from_fd(int fd);

/* Driver interface ------------------------------------------------------ */

/*
 * Run `tests` over the tape in `data`, from a clean slate.
 *
 * With `record` set, the samples are written to stdout in the line format
 * sbv_sample.c documents; without it nothing is emitted, which is what the
 * fuzzing loop wants -- there it is only building a corpus, and the recording
 * pass comes afterwards.
 */
void sbv_sample_exec(const unsigned char *data, size_t len,
                     int (*tests)(void), int record);

/* Executions, rejections and exit() calls since the process started. */
unsigned long sbv_sample_total_execs(void);
unsigned long sbv_sample_total_rejected(void);
unsigned long sbv_sample_total_exited(void);

#endif /* SBV_SAMPLE_H */
