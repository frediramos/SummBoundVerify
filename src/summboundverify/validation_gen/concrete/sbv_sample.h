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
 *   _ULE_ etc.  compare two concrete values
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
sbv_value sym_var_named(char *name, size_t bits);

/*
 * The value of element `index` of the input array `name`.
 *
 * Recorded under the same (name, index) pair the symbolic side uses for it,
 * so an array is matched element by element rather than as an opaque blob.
 */
sbv_value sym_var_array(char *name, size_t index, size_t bits);

/*
 * `bits` fresh bytes for the input `name`, written straight to `dst`.
 *
 * The counterpart of sym_var_bytes in the symbolic API, and needed for the
 * same reason: a floating-point value cannot travel back through an integer
 * return without being converted, and converting it is exactly what must not
 * happen -- the bit pattern is the value being tested.
 */
void sym_var_bytes(char *name, void *dst, size_t bits);

/* Bounding the domain --------------------------------------------------- */

/*
 * Discard this run unless `cnstr` holds.
 *
 * The generated test bounds its inputs (`assume(_ULE_(n, MAX_NUM_1))`), and
 * those bounds are part of the summary's path condition on the symbolic side.
 * A sample that ignored them would satisfy no path and be reported as an
 * input the summary fails to cover -- a finding manufactured by the harness.
 */
void assume(int cnstr);

/* Same, in the form a summary would write it. */
void _assert(int cnstr);

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
 * Concrete readings of the constraint operators.
 *
 * These are only ever applied to values already drawn, so each one is the
 * plain comparison it looks like. The operators that have no concrete meaning
 * -- push_pc, pop_pc, is_sat, is_certain, maximize, minimize -- are absent by
 * design: a summary that uses them is never compiled into this harness.
 */
int _EQ_(sbv_value a, sbv_value b);
int _NEQ_(sbv_value a, sbv_value b);
int _LT_(sbv_value a, sbv_value b);
int _LE_(sbv_value a, sbv_value b);
int _GT_(sbv_value a, sbv_value b);
int _GE_(sbv_value a, sbv_value b);
int _ULT_(sbv_value a, sbv_value b);
int _ULE_(sbv_value a, sbv_value b);
int _UGT_(sbv_value a, sbv_value b);
int _UGE_(sbv_value a, sbv_value b);
int _NOT_(int c);
int _AND_(int a, int b);
int _OR_(int a, int b);

/* Heap ------------------------------------------------------------------ */

/*
 * The allocation primitives, concretely.
 *
 * These are here for the same reason assume() and _ULE_() are, and not for
 * the reason push_pc() is absent: allocating memory means the same thing
 * whether the pointer is symbolic or not. A concrete function's helper
 * library routes malloc through mem_alloc so angr can track the region (the
 * strdup tests do), and that library is linked here too, so the names have to
 * resolve.
 */
void *mem_alloc(size_t bytes);
void mem_free(void *ptr);

/* How many bytes `ptr` was allocated with. Zero if it did not come from
 * mem_alloc, which is also what the symbolic side reports for an unknown
 * pointer. */
size_t n_allocd(void *ptr);

/* Assert that `size` bytes at `ptr` are readable and writable. Symbolically
 * this consults the memory permissions; concretely the only thing that can be
 * checked without inviting a segfault is that the pointer is not null. */
void allocd(void *ptr, size_t size);

/* Recording the outcome ------------------------------------------------- */

/*
 * Mark `len` bytes at `addr` as observable output, under `name`.
 *
 * Registered before the call and read after it, mirroring how get_cnstr lifts
 * memory contents on the symbolic side.
 */
void mem_addr(char *name, void *addr, size_t len);

/*
 * Close the record for one test: the return value at `ret` (`bits` wide, or
 * 0/NULL for a void function) plus the current contents of every region
 * registered since the last record.
 */
void sbv_record(char *test, void *ret, size_t bits);

/* Driver interface ------------------------------------------------------ */

#define SBV_OK 0       /* ran to completion                                */
#define SBV_REJECTED 1 /* an assume()/_assert() put this input out of range */

/*
 * Run `tests` over the tape in `data`, from a clean slate.
 *
 * With `record` set, the samples are written to stdout in the line format
 * sbv_sample.c documents; without it nothing is emitted, which is what the
 * fuzzing loop wants -- there it is only building a corpus, and the recording
 * pass comes afterwards.
 */
int sbv_sample_exec(const unsigned char *data, size_t len,
                    int (*tests)(void), int record);

/* Executions, rejections and exit() calls since the process started. */
unsigned long sbv_sample_total_execs(void);
unsigned long sbv_sample_total_rejected(void);
unsigned long sbv_sample_total_exited(void);

#endif /* SBV_SAMPLE_H */
