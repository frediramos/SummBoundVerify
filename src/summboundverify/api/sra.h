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
 * Asserts that `cnstr` holds.
 *
 * If `cnstr` is unsatisfiable, reports an assertion failure and terminates
 * execution.
 */
void __assert(cnstr_t cnstr);

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
void __assert(cnstr_t cnstr);

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
 * Throws an exception if the memory pointed to by `ptr` does not have
 * read/write permissions.
 *
 * The input `ptr` does not need to be a heap pointer allocated by
 * `__mem_alloc`.
 */
size_t __allocd(void *ptr);


/* ============================================================================
 * Files
 * ==========================================================================
 *
 * File names may be either concrete or symbolic strings. All other arguments
 * must be concrete values.
 * ========================================================================== */

/**
 * Creates a new file named `name`.
 *
 * `name` may be either a concrete or symbolic string.
 *
 * Returns `1` on success and `-1` if the file could not be created.
 */
int __file_create(const char* name);

/**
 * Opens the file named `name` with the specified `flags`.
 *
 * `name` may be either a concrete or symbolic string. `flags` must be
 * concrete.
 *
 * Returns the file descriptor on success, or `-1` if the file does not
 * exist or cannot be opened.
 */
int __file_open(const char* name, const char* flags);

/**
 * Checks whether the file named `name` exists.
 *
 * `name` may be either a concrete or symbolic string.
 *
 * Returns `1` if the file exists and `0` otherwise. The return value can be symbolic.
 */
int __file_exists(const char* name);

/**
 * Deletes the file named `name`.
 *
 * `name` may be either a concrete or symbolic string.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_delete(const char* name);

/**
 * Closes the file associated with file descriptor `fd`.
 *
 * `fd` must be concrete.
 *
 * Returns `0` on success and `-1` on failure.
 */
int __file_close(int fd);

/**
 * Reads up to `count` bytes from the file associated with file descriptor
 * `fd` into `buffer`. The bytes read may be symbolic.
 *
 * `fd`, `buffer`, and `count` must be concrete.
 *
 * Returns the number of bytes read, which may be less than `count`.
 * Advances the file offset by the number of bytes read.
 * Returns `0` if the end of the file has been reached.
 * Returns `-1` on error.
 * The return value can be symbolic.
 */
ssize_t __file_read(int fd, void* buffer, size_t count);

/**
 * Writes up to `count` bytes from `buffer` to the file associated with file
 * descriptor `fd`.
 *
 * `fd`, `buffer`, and `count` must be concrete.
 *
 * Returns the number of bytes written, which may be less than `count`.
 * Advances the file offset by the number of bytes written.
 * Returns `-1` on error.
 */
ssize_t __file_write(int fd, const void* buffer, size_t count);

/**
 * Returns the size, in bytes, of the file associated with file descriptor
 * `fd`. The returned size may be symbolic.
 *
 * `fd` must be concrete.
 *
 * Returns `-1` if `fd` is invalid.
 */
ssize_t __file_size(int fd);

/**
 * Returns the current file offset of the file associated with file descriptor
 * `fd`. The returned offset may be symbolic.
 *
 * `fd` must be concrete.
 *
 * Returns `-1` if `fd` is invalid.
 */
ssize_t __file_offset(int fd);

/**
 * Sets the size of the file associated with file descriptor `fd` to `size`
 * bytes.
 *
 * `fd` and `size` must be concrete.
 *
 * Returns the new file size on success, or `-1` on failure.
 */
ssize_t __file_set_size(int fd, size_t size);

/**
 * Sets the current file offset of the file associated with file descriptor
 * `fd` to `offset`.
 *
 * `fd` and `offset` must be concrete.
 *
 * Returns the new file offset on success, or `-1` on failure.
 */
ssize_t __file_set_offset(int fd, size_t offset);

/**
 * Sets the mode (`st_mode`) of the file associated with file descriptor `fd`.
 *
 * `fd` and `mode` must be concrete.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_set_mode(int fd, mode_t mode);

/**
 * Stores the `st_mode` value of the file associated with file descriptor
 * `fd` in `*mode`.
 *
 * The stored value encodes both the file type and permission bits (e.g.,
 * regular file, directory, `0644`, `0755`).
 *
 * `fd` and `mode` must be concrete.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_mode(int fd, mode_t* mode);

/**
 * Returns the open status flags associated with file descriptor `fd`.
 *
 * The returned value is a bitmask of the flags used when the file was opened
 * (e.g., `O_RDONLY`, `O_WRONLY`, `O_RDWR`, `O_APPEND`, `O_NONBLOCK`).
 *
 * `fd` must be concrete.
 *
 * Returns `-1` if `fd` does not refer to a valid open file descriptor.
 */
int __file_flags(int fd);

/**
 * Creates a duplicate of the file descriptor `oldfd`.
 *
 * The duplicate refers to the same open file description as `oldfd`; both
 * descriptors share the same file offset and open status flags.
 *
 * `oldfd` must be concrete.
 *
 * Returns the new file descriptor on success, or `-1` on failure.
 */
int __file_dup(int oldfd);

/**
 * Duplicates the file descriptor `oldfd` onto `newfd`.
 *
 * If `newfd` is already open, it is closed before being reused.
 * The resulting descriptor refers to the same open file description as
 * `oldfd`; both descriptors share the same file offset and open status flags.
 *
 * `oldfd` and `newfd` must be concrete.
 *
 * Returns `newfd` on success, or `-1` on failure.
 */
int __file_dup2(int oldfd, int newfd);

/**
 * Returns the `FILE*` associated with file descriptor `fd`.
 *
 * `fd` must be concrete.
 *
 * Returns `NULL` if `fd` is invalid.
 */
FILE* __FILE_from_fd(int fd);

/**
 * Returns the file descriptor associated with the file pointer `fp`.
 *
 * `fp` must be concrete.
 *
 * Returns `-1` if `fp` is invalid.
 */
int __fd_from_FILE(FILE* fp);
