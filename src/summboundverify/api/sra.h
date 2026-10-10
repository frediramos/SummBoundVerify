/* ============================================================================
 *** Symbolic Reflection API ***
 * ========================================================================== */


/* ============================================================================
 * Core Primitives
 * ========================================================================== */

 /**
 * Takes the symbolic variable `var` and returns a value that it may denote
 * given the current path condition.
 */
long __concretize(symbolic var);

/**
 * Reports an error originating from `filename` at line `line` with the
 * message `message`.
 *
 * This function does not return.
 */
void __report_error(const char* filename, unsigned int line, const char* message);


/**
 * Takes the symbolic variable `var` and returns the maximum value that it
 * may denote given the current path condition.
 */
long __maximize(symbolic var);

/**
 * Takes the symbolic variable `var` and returns the minimum value that it
 * may denote given the current path condition.
 */
long __minimize(symbolic var);

/**
 * Returns a new symbolic variable with a uniquely generated identifier
 * and denoting a value with `size` bits.
 */
symbolic __sym_var(size_t size);

/**
 * Returns a new symbolic variable identified by `name` and denoting a
 * value with `size` bits.
 */
symbolic __sym_var_named(char *name, size_t size);

/**
 * Returns a new symbolic variable identified by an array `name` and an
 * index `index`, denoting a value with `size` bits.
 *
 * Used to fill symbolic arrays.
 */
symbolic __sym_var_array(char *name, size_t index, size_t size);

/**
 * Checks if variable `var` is symbolic.
 */
int __is_symbolic(symbolic var);

/**
 * Calls the SMT solver to check if the constraint `cnstr` is satisfiable
 * given the current path condition.
 */
int __is_sat(cnstr_t cnstr);

/**
 * Calls the SMT solver to check if the constraint `cnstr` is certainly
 * true given the current path condition.
 */
int __is_certain(cnstr_t cnstr);

/**
 * Adds the constraint `cnstr` to the current path condition of the
 * symbolic state.
 */
void __assume(cnstr_t cnstr);

/**
 * Calls the SMT solver to check if the constraint `cnstr` is certainly
 * true given the current path condition.
 * If not, reports an assertion failure and terminates execution.
 */
void __sra_assert(cnstr_t cnstr);

/**
 * Saves the current path condition by creating a copy and pushing it
 * onto the path condition stack.
 *
 * This operation is typically used before exploring a new execution
 * branch so that the current condition can later be restored.
 */
void __push_pc(void);

/**
 * Restores the previous path condition by popping the top element from
 * the path condition stack.
 *
 * This is typically used after finishing the exploration of a branch,
 * reverting the path condition to its earlier state.
 */
void __pop_pc(void);


/* ============================================================================
 * Constraints
 * ========================================================================== */

/**
 * Returns the logical negation of `cnstr`.
 *
 * Equivalent to: `!cnstr`
 */
cnstr_t _NOT_(cnstr_t cnstr);

/**
 * Returns the logical disjunction of `cnstr1` and `cnstr2`.
 *
 * Equivalent to: `cnstr1 || cnstr2`
 */
cnstr_t _OR_(cnstr_t cnstr1, cnstr_t cnstr2);

/**
 * Returns the logical conjunction of `cnstr1` and `cnstr2`.
 *
 * Equivalent to: `cnstr1 && cnstr2`
 */
cnstr_t _AND_(cnstr_t cnstr1, cnstr_t cnstr2);

/**
 * Returns a signed less-than constraint.
 *
 * Equivalent to: `var1 < var2`
 */
cnstr_t _LT_(symbolic var1, symbolic var2);

/**
 * Returns a signed less-than-or-equal constraint.
 *
 * Equivalent to: `var1 <= var2`
 */
cnstr_t _LE_(symbolic var1, symbolic var2);

/**
 * Returns a signed greater-than constraint.
 *
 * Equivalent to: `var1 > var2`
 */
cnstr_t _GT_(symbolic var1, symbolic var2);

/**
 * Returns a signed greater-than-or-equal constraint.
 *
 * Equivalent to: `var1 >= var2`
 */
cnstr_t _GE_(symbolic var1, symbolic var2);

/**
 * Returns an equality constraint.
 *
 * Equivalent to: `var1 == var2`
 */
cnstr_t _EQ_(symbolic var1, symbolic var2);

/**
 * Returns an inequality constraint.
 *
 * Equivalent to: `var1 != var2`
 */
cnstr_t _NEQ_(symbolic var1, symbolic var2);

/**
 * Returns an unsigned less-than constraint.
 *
 * Equivalent to: `var1 < var2` using unsigned comparison.
 */
cnstr_t _ULT_(symbolic var1, symbolic var2);

/**
 * Returns an unsigned less-than-or-equal constraint.
 *
 * Equivalent to: `var1 <= var2` using unsigned comparison.
 */
cnstr_t _ULE_(symbolic var1, symbolic var2);

/**
 * Returns an unsigned greater-than constraint.
 *
 * Equivalent to: `var1 > var2` using unsigned comparison.
 */
cnstr_t _UGT_(symbolic var1, symbolic var2);

/**
 * Returns an unsigned greater-than-or-equal constraint.
 *
 * Equivalent to: `var1 >= var2` using unsigned comparison.
 */
cnstr_t _UGE_(symbolic var1, symbolic var2);

/**
 * Returns a constraint representing a conditional expression.
 *
 * Equivalent to: `cond ? cnstr1 : cnstr2`
 *
 * This function is intended for constraints only.
 */
cnstr_t _ITE_(cnstr_t cond, cnstr_t cnstr1, cnstr_t cnstr2);

/**
 * Returns a symbolic variable representing a conditional expression.
 *
 * Equivalent to: `cond ? var1 : var2`
 *
 * This function is intended for variables only.
 */
cnstr_t _ITE_VAR_(cnstr_t cond, symbolic var1, symbolic var2);


/* ============================================================================
 * Lists
 * ========================================================================== */

/**
 * Returns a new empty list.
 */
list_t __lst_mk(void);

/**
 * Prepends `value` to `lst`.
 */
list_t __lst_cons(symbolic value, list_t lst);

/**
 * Returns a constraint that is true if `lst` is empty and false otherwise.
 */
cnstr_t __lst_empty(list_t lst);

/**
 * Returns the tail of `lst`, that is, `lst` without its first element.
 */
list_t __lst_tl(list_t lst);

/**
 * Returns the first element (head) of `lst`.
 */
symbolic __lst_hd(list_t lst);

/**
 * Returns the number of elements contained in `lst`.
 */
size_t __lst_len(list_t lst);

/**
 * Returns a new list containing `n` copies of the byte `c`.
 */
list_t __lst_nbytes(char c, size_t n);

/**
 * Returns a new list containing `n` null (`'\0'`) bytes.
 */
list_t __lst_zeros(size_t n);

/**
 * Stores a conditional value at the memory address pointed to by `ptr`.
 *
 * The resulting value is an if-then-else expression: if `pc` evaluates
 * to true, the byte at `ptr` is `c`; otherwise, it retains its previous
 * value.
 *
 * If `ptr` is symbolic, the write is performed over the set of possible
 * addresses represented by `ptr`. For each affected address, the resulting
 * value is encoded as an if-then-else expression that captures both the
 * path condition `pc` and whether that address is selected by `ptr`.
 */
void __cond_write(void *ptr, symbolic c, cnstr_t pc);


/* ============================================================================
 * Heap
 * ========================================================================== */

/**
 * Allocates `nbytes` bytes of memory on the heap and returns a pointer
 * to the allocated region.
 */
void *__mem_alloc(size_t nbytes);

/**
 * Frees the heap region pointed to by `ptr`.
 *
 * The pointer must have been returned by `__mem_alloc`.
 */
void __mem_free(void *ptr);

/**
 * Returns the number of allocated bytes pointed to by `ptr`.
 *
 * The pointer must have been returned by `__mem_alloc`.
 */
size_t __n_allocd(void *ptr);

/**
 * Throws an exception if the `n` bytes of memory starting at `ptr` do not have
 * read/write permissions.
 *
 * The input `ptr` does not need to be a heap pointer allocated by
 * `__mem_alloc`.
 */
size_t __allocd(void *ptr, size_t n);


/* ============================================================================
 * Files
 * ==========================================================================
 *
 * Names may be concrete or symbolic strings (the pointer must be concrete).
 * An empty name, or a symbolic one that may start with '\0', is invalid.
 * Operations on symbolic names never fork: when success is feasible, the
 * needed (non-)existence constraint is added to the path condition and the
 * result is `ite(valid, <success>, -1)`, `valid` meaning a non-empty name.
 *
 * Descriptors are concrete or `ite(cond, fd, -1)` with `fd` concrete; any
 * other form raises an error. On `ite(cond, fd, -1)` an operation applies to
 * `fd` and returns `ite(cond, <result>, <error>)`. Functions that only look a
 * descriptor up (`__file_size`, `__file_offset`, `__file_flags`,
 * `__FILE_from_fd`, `__fd_from_FILE`) also accept nested `ite`s over several
 * descriptors, as long as one case is `-1`. `FILE*` values follow the same
 * rules with `NULL` for `-1`. A concrete fd may refer to several possible
 * files (one per match of a symbolic name), so sizes, offsets and reads may
 * be symbolic. A descriptor that is not open makes a function fail with its
 * error value (`-1`, or `NULL` for `__FILE_from_fd`).
 *
 * All other arguments must be concrete (or symbolic with a single solution).
 * ========================================================================== */

/**
 * Creates a new, empty file named `name`, constraining it to differ from
 * every existing file.
 *
 * Returns `1` on success, `-1` if the file exists or `name` is invalid.
 */
int __file_create(const char* name);

/**
 * Opens the existing file named `name`; never creates one. The descriptor
 * starts at offset `0`.
 *
 * `flags` is an `fopen` mode: "r", "r+", "w", "w+", "a" or "a+", optionally
 * followed by b, t, c or e (ignored). It only sets `__file_flags`: reads and
 * writes are always allowed, "w" does not truncate and "a" does not append.
 *
 * Returns a new descriptor, or `-1` if the file does not exist or `name` is
 * invalid.
 */
int __file_open(const char* name, const char* flags);

/**
 * Returns `1` if the file named `name` exists and `0` otherwise (possibly
 * symbolic). Does not constrain the path condition.
 */
int __file_exists(const char* name);

/**
 * Deletes the file named `name`, constraining it to exist. It must not be
 * open.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_delete(const char* name);

/**
 * Closes `fd`. Returns `0` on success and `-1` on failure.
 */
int __file_close(int fd);

/**
 * Reads up to `count` bytes from `fd` into `buffer` at the current offset,
 * and advances the offset by the bytes read. Bytes past the end of the file
 * leave `buffer` unchanged.
 *
 * Returns the bytes read (possibly symbolic), `0` at the end of the file, or
 * `-1` on error.
 */
ssize_t __file_read(int fd, void* buffer, size_t count);

/**
 * Writes `count` bytes from `buffer` to `fd` at the current offset, and
 * advances the offset by `count`. Writing past the end first pads the file
 * with '\0'. `buffer` is read as a C string: bytes after its first concrete
 * '\0' are not written.
 *
 * Returns `count` (writes are never partial), or `-1` on error.
 */
ssize_t __file_write(int fd, const void* buffer, size_t count);

/**
 * Returns the size of the file of `fd` (possibly symbolic), or `-1` on error.
 */
ssize_t __file_size(int fd);

/**
 * Returns the offset of `fd` (possibly symbolic), or `-1` on error.
 */
ssize_t __file_offset(int fd);

/**
 * Truncates the file of `fd` to `size` bytes, or pads it with '\0'.
 *
 * Returns the new size, or `-1` on error.
 */
ssize_t __file_set_size(int fd, size_t size);

/**
 * Sets the offset of `fd` to `offset`, which may be past the end of the file.
 *
 * Returns the new offset, or `-1` on error.
 */
ssize_t __file_set_offset(int fd, size_t offset);

/**
 * Sets the permission bits of the file `fd` refers to, to `mode`, as chmod
 * does: no umask is applied. The mode belongs to the file: every descriptor of
 * it sees the change, and the mode outlives them.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_set_mode(int fd, mode_t mode);

/**
 * Stores the permission bits of the file `fd` refers to in `*mode`: `0644`
 * for a new file, with no file-type bits (e.g., `S_IFREG`).
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_mode(int fd, mode_t* mode);

/**
 * Returns the open flags of `fd`, from its `__file_open` mode, or `-1` on
 * error:
 *
 *   "r"  -> O_RDONLY           "r+" -> O_RDWR
 *   "w"  -> O_WRONLY|O_CREAT|O_TRUNC
 *   "w+" -> O_RDWR|O_CREAT|O_TRUNC
 *   "a"  -> O_WRONLY|O_CREAT|O_APPEND
 *   "a+" -> O_RDWR|O_CREAT|O_APPEND
 */
int __file_flags(int fd);

/**
 * Duplicates `oldfd`; both share the offset, mode and flags.
 *
 * Returns the new descriptor, or `-1` on failure.
 */
int __file_dup(int oldfd);

/**
 * Duplicates `oldfd` onto `newfd`, closing `newfd` first if open (nothing is
 * done if they are equal). Both share the offset, mode and flags. Each
 * argument may be `ite(cond, fd, -1)`; every combination of cases is applied.
 *
 * Returns `newfd`, or `-1` on failure.
 */
int __file_dup2(int oldfd, int newfd);

/**
 * Limits descriptors to `0` to `n - 1`, as setrlimit(RLIMIT_NOFILE) does:
 * past the limit, `__file_open` and `__file_dup` fail (EMFILE), and
 * `__file_dup2` fails for `newfd >= n` (EBADF). Descriptors already open stay
 * open. The default limit is 1024. `n` must be concrete.
 *
 * Returns `1` on success, or `-1` if `n` is negative.
 */
int __file_set_max_fds(int n);

/**
 * Returns the `FILE*` of `fd`, or `NULL` on error.
 */
FILE* __FILE_from_fd(int fd);

/**
 * Returns the descriptor of `fp` (concrete or `ite(cond, fp, NULL)`), or `-1`
 * if `fp` is `NULL` or not open.
 */
int __fd_from_FILE(FILE* fp);
