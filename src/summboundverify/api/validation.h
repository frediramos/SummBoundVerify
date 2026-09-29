/* ============================================================================
 * Validation Primitives
 * ========================================================================== */

/**
 * Saves a copy of the current symbolic state.
 *
 * Returns a `state_t` representing the saved state.
 */
state_t __save_current_state(void);

/**
 * Builds a formula denoting the conjunction of the current path condition
 * and `Ret == var`.
 *
 * `Ret` is a fresh symbolic variable.
 *
 * The `size` parameter specifies the size of `var` in bits.
 */
cnstr_t __get_cnstr(symbolic var, size_t size);

/**
 * Stores the given constraint `constraint`, associating it with the key
 * `name`.
 */
void __store_cnstr(char *name, cnstr_t constraint);

/**
 * Marks `n + 1` consecutive memory addresses, starting from `addr`
 * (inclusive), to be evaluated by the summary validation tool.
 */
void __mem_addr(char *name, void *addr, size_t n);

/**
 * Tags a file path for post-call observation.
 *
 * After the function under test executes, the file at `path` is checked
 * for existence and its contents are compared against the summary's
 * constraints. `name` is the join key used to match symbolic and
 * concrete observations.
 */
void __file_addr(char *name, const char *path);

/**
 * Checks the correctness implications for the previously stored constraints
 * associated with the keys `summ` and `cncrt`.
 *
 * Returns a `result_t` containing the validation result.
 */
result_t __check_implications(char *summ, char *cncrt);

/**
 * Halts all current execution paths and resumes a single path from `state`.
 *
 * If `state` is `NULL`, resumes from the current state.
 */
void __halt_all(state_t state);

/**
 * Prints the validation results.
 *
 * Also prints counterexample models for implications that were proven
 * to be wrong.
 */
void __print_counterexamples(result_t result);
