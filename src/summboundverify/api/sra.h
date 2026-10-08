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
 * File names
 * ----------
 * File names may be concrete or symbolic strings, but the pointer to the
 * name must be concrete. A name that is empty (or, if symbolic, may start
 * with '\0') is invalid.
 *
 * Operations on symbolic names never fork. When success is feasible, the
 * required existence (or non-existence) constraint is added to the path
 * condition and the operation succeeds; the result is then
 * `ite(valid, <success>, -1)`, where `valid` states that the name is not
 * empty.
 *
 * File descriptors
 * ----------------
 * File descriptors are never fully symbolic. Every fd produced by this API
 * is either concrete or has the form `ite(cond, fd, -1)`, with `fd`
 * concrete (e.g., the result of `__file_open` on a symbolic name).
 *
 * Every function below taking an `fd` accepts exactly these two forms;
 * anything else raises an error. For `ite(cond, fd, -1)`, the operation is
 * applied to `fd` and the result is `ite(cond, <result>, <error>)`, where
 * `<error>` is the function's error value (`-1`, or `NULL` for
 * `__FILE_from_fd`). `FILE*` values follow the same rule with `NULL` in
 * place of `-1`.
 *
 * A single concrete fd may refer to several possible files, one for each
 * feasible match of a symbolic name, each guarded by a condition. Hence
 * sizes, offsets and the results of reads may be symbolic even when the fd
 * is concrete.
 *
 * Passing an fd that is not open (negative, closed or never returned by
 * this API) makes the function fail with its error value.
 *
 * Other arguments
 * ---------------
 * All other arguments (buffers, counts, sizes, offsets, modes and flags)
 * must be concrete; a symbolic value raises an error. A symbolic value
 * constrained to a single solution is accepted and concretized.
 * ========================================================================== */

/**
 * Creates a new, empty file named `name`.
 *
 * The file must be able to not exist on the current path. When this depends
 * on symbolic names (`name` or existing ones), the constraint that `name`
 * differs from every existing file is added to the path condition.
 *
 * Returns `1` on success and `-1` if the file already exists or `name` is
 * invalid. For a symbolic `name`, returns `ite(valid, 1, -1)`.
 */
int __file_create(const char* name);

/**
 * Opens the existing file named `name`. Opening never creates a file.
 *
 * `flags` is a concrete `fopen`-style mode string: `"r"`, `"r+"`, `"w"`,
 * `"w+"`, `"a"` or `"a+"`, optionally followed by `b`, `t`, `c` or `e`
 * (which are ignored). Any other string raises an error. The mode determines
 * the value returned by `__file_flags`, but it is not enforced: reads and
 * writes are always allowed, `"w"` does not truncate and `"a"` does not
 * append. The new descriptor starts at offset `0`.
 *
 * Returns a new concrete file descriptor on success, or `-1` if the file
 * does not exist or `name` is invalid. For a symbolic `name`, returns
 * `ite(valid, fd, -1)`.
 */
int __file_open(const char* name, const char* flags);

/**
 * Checks whether the file named `name` exists.
 *
 * Unlike `__file_create` and `__file_delete`, this does not constrain the
 * path condition.
 *
 * Returns `1` if the file exists and `0` otherwise. The return value can be
 * symbolic.
 */
int __file_exists(const char* name);

/**
 * Deletes the file named `name`.
 *
 * The file must be able to exist on the current path and must not be
 * referenced by an open file descriptor whose name it may equal. When this
 * depends on symbolic names, the constraint that the file exists is added to
 * the path condition.
 *
 * Returns `1` on success and `-1` on failure. For a symbolic `name`, returns
 * `ite(valid, 1, -1)`.
 */
int __file_delete(const char* name);

/**
 * Closes the file descriptor `fd`.
 *
 * Returns `0` on success and `-1` on failure.
 */
int __file_close(int fd);

/**
 * Reads up to `count` bytes from the file referenced by `fd` into `buffer`,
 * starting at the current offset. The bytes read may be symbolic.
 *
 * `buffer` and `count` must be concrete.
 *
 * Bytes past the end of the file leave `buffer` unchanged. Advances the
 * offset by the number of bytes read.
 *
 * Returns the number of bytes read, which may be less than `count`, `0` at
 * the end of the file, or `-1` on error. The return value can be symbolic.
 */
ssize_t __file_read(int fd, void* buffer, size_t count);

/**
 * Writes `count` bytes from `buffer` to the file referenced by `fd`, starting
 * at the current offset.
 *
 * `buffer` and `count` must be concrete.
 *
 * `buffer` is read as a C string: bytes after its first concrete '\0' are
 * not written (symbolic bytes are, even if they may be '\0'). Writing past
 * the end of the file first extends it with '\0' bytes. Advances the offset
 * by `count`.
 *
 * Returns `count` on success (writes are never partial), or `-1` on error.
 */
ssize_t __file_write(int fd, const void* buffer, size_t count);

/**
 * Returns the size, in bytes, of the file referenced by `fd`. The returned
 * size may be symbolic.
 *
 * Returns `-1` on error.
 */
ssize_t __file_size(int fd);

/**
 * Returns the current offset of the file referenced by `fd`. The returned
 * offset may be symbolic.
 *
 * Returns `-1` on error.
 */
ssize_t __file_offset(int fd);

/**
 * Sets the size of the file referenced by `fd` to `size` bytes, truncating it
 * or extending it with '\0' bytes.
 *
 * `size` must be concrete.
 *
 * Returns the new file size on success, or `-1` on failure.
 */
ssize_t __file_set_size(int fd, size_t size);

/**
 * Sets the current offset of the file referenced by `fd` to `offset`, which
 * may lie past the end of the file.
 *
 * `offset` must be concrete.
 *
 * Returns the new offset on success, or `-1` on failure.
 */
ssize_t __file_set_offset(int fd, size_t offset);

/**
 * Sets the permission bits of the descriptor `fd` to `mode`.
 *
 * `mode` must be concrete. The umask `022` is applied, so the stored value
 * is `mode & ~022`.
 *
 * The mode belongs to the descriptor (and its duplicates), not to the file:
 * opening the same file again yields the default mode.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_set_mode(int fd, mode_t mode);

/**
 * Stores the permission bits of the descriptor `fd` in `*mode`.
 *
 * `mode` must be a concrete pointer. The default is `0644` (`0666` with the
 * umask `022` applied). No file-type bits (e.g., `S_IFREG`) are set.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_mode(int fd, mode_t* mode);

/**
 * Returns the open status flags of `fd`, derived from the mode string given
 * to `__file_open`:
 *
 *   "r"  -> O_RDONLY           "r+" -> O_RDWR
 *   "w"  -> O_WRONLY|O_CREAT|O_TRUNC
 *   "w+" -> O_RDWR|O_CREAT|O_TRUNC
 *   "a"  -> O_WRONLY|O_CREAT|O_APPEND
 *   "a+" -> O_RDWR|O_CREAT|O_APPEND
 *
 * Returns `-1` on error.
 */
int __file_flags(int fd);

/**
 * Creates a duplicate of the file descriptor `oldfd`.
 *
 * The duplicate refers to the same open file description as `oldfd`; both
 * descriptors share the same offset, mode and open status flags.
 *
 * Returns the new file descriptor on success, or `-1` on failure.
 */
int __file_dup(int oldfd);

/**
 * Duplicates the file descriptor `oldfd` onto `newfd`.
 *
 * If `newfd` is open, it is closed before being reused. If `oldfd` equals
 * `newfd`, nothing is done. The resulting descriptor refers to the same open
 * file description as `oldfd`; both descriptors share the same offset, mode
 * and open status flags.
 *
 * Both arguments may have the form `ite(cond, fd, -1)`; the operation is
 * applied to each combination of their cases.
 *
 * Returns `newfd` on success, or `-1` on failure.
 */
int __file_dup2(int oldfd, int newfd);

/**
 * Returns the `FILE*` associated with the file descriptor `fd`.
 *
 * Returns `NULL` on error.
 */
FILE* __FILE_from_fd(int fd);

/**
 * Returns the file descriptor associated with the file pointer `fp`.
 *
 * `fp` is either concrete or has the form `ite(cond, fp, NULL)`, as returned
 * by `__FILE_from_fd`.
 *
 * Returns `-1` if `fp` is `NULL` or does not belong to an open descriptor.
 */
int __fd_from_FILE(FILE* fp);
