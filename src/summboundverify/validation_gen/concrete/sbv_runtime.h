/*
 * Concrete backend for the SummBoundVerify API.
 *
 * The symbolic backend implements this API as angr SimProcedures hooked onto
 * the stub symbols emitted into the generated test (see validation_tool/api).
 * This header declares the same API with *concrete* semantics, so the very
 * same generated test can be linked into a native binary and executed on
 * concrete inputs.
 *
 * Generated tests include this header instead of the stub prelude when the
 * test is emitted with engine='fuzz' (see validation_gen/validation.py).
 *
 * Having real prototypes visible matters: without them every call goes
 * through the default argument promotions, and a `char` argument reaching a
 * wider parameter would leave the upper bits undefined.
 */

#ifndef SBV_RUNTIME_H
#define SBV_RUNTIME_H

#include <stddef.h>

#define INT_SIZE (sizeof(int) * 8)
#define LONG_SIZE (sizeof(long) * 8)
#define CHAR_SIZE (sizeof(char) * 8)
#define PTR_SIZE (sizeof(void *) * 8)

/*
 * `symbolic` is `void*` in the stub prelude, purely so that any scalar can be
 * passed without a cast. Concretely we need an integer type wide enough to
 * hold a pointer, so that both uses keep working.
 */
typedef long symbolic;
typedef int state_t;
typedef unsigned int cnstr_t;
typedef unsigned int result_t;
typedef unsigned int list_t;

/* ------------------------------------------------------------------ */
/* Core primitives                                                     */
/* ------------------------------------------------------------------ */

symbolic sym_var(size_t size);
symbolic sym_var_named(char *name, size_t size);
symbolic sym_var_array(char *name, size_t index, size_t size);

/*
 * Fill `size` bits at `dst` with fresh input, instead of returning a value.
 *
 * sym_var_named() carries its draw inside a `symbolic` (a void*), which only
 * works for types a pointer can be reinterpreted as. Floating point cannot:
 * there is no conversion from void* to double, and the draw would not survive
 * one anyway. Writing through a pointer sidesteps both problems and is exact
 * for any width.
 */
void sym_var_bytes(char *name, void *dst, size_t size);

/*
 * Stand-in for exit(), which the fuzz build redirects here with
 * -Dexit=sbv_exit.
 */
void sbv_exit(int code);

int is_symbolic(symbolic var);
int is_sat(cnstr_t cnstr);
int is_certain(cnstr_t cnstr);

void assume(cnstr_t cnstr);
void _assert(int expr);

void push_pc(void);
void pop_pc(void);

long maximize(symbolic var);
long minimize(symbolic var);

/* ------------------------------------------------------------------ */
/* Constraints                                                         */
/* ------------------------------------------------------------------ */

cnstr_t _NOT_(cnstr_t cnstr);
cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2);
cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2);

cnstr_t _EQ_(symbolic var1, symbolic var2);
cnstr_t _NEQ_(symbolic var1, symbolic var2);

cnstr_t _LT_(symbolic var1, symbolic var2);
cnstr_t _LE_(symbolic var1, symbolic var2);
cnstr_t _GT_(symbolic var1, symbolic var2);
cnstr_t _GE_(symbolic var1, symbolic var2);

cnstr_t _ULT_(symbolic var1, symbolic var2);
cnstr_t _ULE_(symbolic var1, symbolic var2);
cnstr_t _UGT_(symbolic var1, symbolic var2);
cnstr_t _UGE_(symbolic var1, symbolic var2);

cnstr_t _ITE_(cnstr_t cond, cnstr_t cnstr1, cnstr_t cnstr2);
symbolic _ITE_VAR_(cnstr_t cond, symbolic var1, symbolic var2);

/* ------------------------------------------------------------------ */
/* Lists                                                               */
/* ------------------------------------------------------------------ */

list_t lst_mk(void);
list_t lst_cons(symbolic value, list_t lst);
cnstr_t lst_empty(list_t lst);
list_t lst_tl(list_t lst);
symbolic lst_hd(list_t lst);
size_t lst_len(list_t lst);
list_t lst_nbytes(char c, size_t n);
list_t lst_zeros(size_t n);

/* ------------------------------------------------------------------ */
/* Heap / memory                                                       */
/* ------------------------------------------------------------------ */

void allocd(void *ptr, size_t size);
void is_rw(void *ptr, size_t size);
int mallocd(void *ptr);
void cond_write(void *ptr, symbolic c, cnstr_t pc);
void *mem_alloc(size_t bytes);
void mem_free(void *ptr);
size_t n_allocd(void *ptr);

/* ------------------------------------------------------------------ */
/* Validation API (emitted into the test body)                         */
/* ------------------------------------------------------------------ */

state_t save_current_state(void);
cnstr_t get_cnstr(symbolic var, size_t size);
void store_cnstr(char *name, cnstr_t constraint);
void halt_all(state_t state);
result_t check_implications(char *constraint1, char *constraint2);
void print_counterexamples(result_t result);
void mem_addr(char *name, void *addr, size_t length);

/* ------------------------------------------------------------------ */
/* Driver interface                                                    */
/* ------------------------------------------------------------------ */

#define SBV_OK 0       /* ran to completion, summary matched the concrete fn */
#define SBV_REJECTED 1 /* an assume()/_assert() rejected this input          */
#define SBV_DIVERGED 2 /* summary and concrete function disagreed            */

/*
 * Run `entry` once with `data` as the input tape, and return one of the
 * SBV_* codes above. `entry` is the generated test's main(), renamed by the
 * compiler via -Dmain=... so the driver can own the real main().
 */
int sbv_fuzz_exec(const unsigned char *data, size_t len, int (*entry)(void));

/* Number of input bytes the last run actually consumed. */
size_t sbv_fuzz_consumed(void);

/* Index (1-based) of the test that diverged, or 0 if none did. */
int sbv_fuzz_diverged_test(void);

/* Number of test functions the last run checked. */
int sbv_fuzz_ntests(void);

/* Human-readable description of the last divergence ("" if none). */
const char *sbv_fuzz_report(void);

/*
 * The inputs of the last run, decoded and named.
 *
 * sym_var_named()/sym_var_array() receive the variable's name from the
 * generated test, so the runtime can report a counterexample as
 * `str[0]=0x61 str[1]=0x00 n=3` rather than as a hex blob -- independently of
 * which fuzzing engine produced the bytes.
 */
const char *sbv_fuzz_inputs(void);

/* Totals across every run in this process (persistent-mode aware). */
unsigned long sbv_fuzz_total_execs(void);
unsigned long sbv_fuzz_total_rejected(void);

/* Of those, the ones where the target called exit() rather than an
 * assumption turning the input away. */
unsigned long sbv_fuzz_total_exited(void);

#endif /* SBV_RUNTIME_H */
