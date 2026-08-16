/* ============================================================================
 *** Symbolic Reflection API (WIP) ***
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


/* ============================================================================
 *** File Functions (WIP) ***
 * ========================================================================== */

 /**
 * Creates a new file named `name`. 
 *
 * Returns `1` on success and`-1` if the file could not be created.
 */
int __file_create(const char* name);

/**
 * Opens the file named `name` and returns its file descriptor.
 *
 * Returns `-1` if the file does not exist or cannot be opened.
 */
int __file_open(const char* name);

/**
 * Returns `1` if the file named `name` exists and `0` otherwise.
 */
int __file_exists(const char* name);

/**
 * Deletes the file associated with name `name`.
 *
 * Returns `1` on success and `-1` on failure.
 */
int __file_delete(const char* name);

/**
 * Closes the file associated with file descriptor `fd`.
 *
 * Returns `0` on success and `-1` on failure.
 */
int __file_close(int fd);

/**
 * Reads up to `count` bytes from the file associated with file descriptor
 * `fd` into `buffer`.
 *
 * Returns the number of bytes read, which may be less than `count`.
 * Advances the file offset by the number of bytes read.
 * Returns `0` if the end of the file has been reached.
 * Returns `-1` on error.
 */
ssize_t __file_read(int fd, void* buffer, size_t count);

/**
 * Writes up to `count` bytes from `buffer` to the file associated with file
 * descriptor `fd`.
 *
 * Returns the number of bytes written, which may be less than `count`.
 * Advances the file offset by the number of bytes written.
 * Returns `-1` on error.
 */
ssize_t __file_write(int fd, void* buffer, size_t count);

/**
 * Returns the size, in bytes, of the file associated with file descriptor
 * `fd`.
 *
 * Returns `-1` if `fd` is invalid.
 */
ssize_t __file_size(int fd);

/**
 * Returns the current file offset of the file associated with file descriptor
 * `fd`.
 *
 * Returns `-1` if `fd` is invalid.
 */
ssize_t __file_offset(int fd);

/**
 * Sets the size of the file associated with file descriptor `fd` to `size`
 * bytes.
 *
 * Returns the new file size on success, or `-1` on failure.
 */
ssize_t __file_set_size(int fd, size_t size);

/**
 * Sets the current file offset of the file associated with file descriptor
 * `fd` to `offset`.
 *
 * Returns the new file offset on success, or `-1` on failure.
 */
ssize_t __file_set_offset(int fd, size_t offset);

/**
 * Sets the open status flags of the file associated with file descriptor `fd`
 * to `flags`.
 *
 * Common flags include `O_RDONLY`, `O_WRONLY`, `O_RDWR`, and `O_APPEND`.
 */
int __file_set_flags(int fd, int flags);

/**
 * Sets the mode (`st_mode`) of the file associated with file descriptor `fd`.
 */
int __file_set_mode(int fd, mode_t mode);

/**
 * Stores the `st_mode` value of the file associated with file descriptor `fd`
 * in `*mode`.
 *
 * The stored value encodes both the file type and permission bits (e.g.,
 * regular file, directory, `0644`, `0755`).
 *
 * Returns `0` on success and `-1` on failure.
 */
int __file_mode(int fd, mode_t* mode);

/**
 * Returns the open status flags associated with file descriptor `fd`.
 *
 * The returned value is a bitmask of the flags used when the file was opened
 * (e.g., `O_RDONLY`, `O_WRONLY`, `O_RDWR`, `O_APPEND`, `O_NONBLOCK`).
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
 * Returns `newfd` on success, or `-1` on failure.
 */
int __file_dup2(int oldfd, int newfd);

/**
 * Returns the `FILE*` associated with file descriptor `fd`.
 *
 * Returns `NULL` if `fd` is invalid.
 */
FILE* __FILE_from_fd(int fd);

/**
 * Returns the file descriptor associated with the file pointer `fp`.
 *
 * Returns `-1` if `fp` is invalid.
 */
int __fd_from_FILE(FILE* fp);