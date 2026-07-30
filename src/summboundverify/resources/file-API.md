# WIP: File API

## `open` / `fopen`

```c
int __file_create(char* name);
```
- Creates a new file named `name` and returns its file descriptor.
- Returns `-1` if the file could not be created.

```c
int __file_close(int fd);

// Identical
int close(int fd);
```
- Closes the file associated with file descriptor `fd`.
- Returns `0` on success and `-1` on failure.

```c
int __file_delete(int fd);
```
- Deletes the file associated with file descriptor `fd`.
- Returns `1` on success and `-1` on failure.

```c
int __file_open(char* name);
```
- Opens the file named `name` and returns its file descriptor.
- Returns `-1` if the file does not exist or cannot be opened.

```c
FILE* __FILE_from_fd(int fd);
```
- Returns the `FILE*` associated with file descriptor `fd`.
- Returns `NULL` if `fd` is invalid.

```c
int __fd_from_FILE(FILE* fp);
```
- Returns the file descriptor associated with the file pointer `fp`.
- Returns `-1` if `fp` is invalid.

```c
ssize_t __file_size(int fd);
```
- Returns the size, in bytes, of the file associated with file descriptor `fd`.
- Returns `-1` if `fd` is invalid.

```c
ssize_t __file_offset(int fd);
```
- Returns the current file offset of the file associated with file descriptor `fd`.
- Returns `-1` if `fd` is invalid.

```c
ssize_t __file_set_size(int fd, size_t size);
```
- Sets the size of the file associated with file descriptor `fd` to `size` bytes.
- Returns the new file size on success, or `-1` on failure.

```c
ssize_t __file_set_offset(int fd, size_t offset);
```
- Sets the current file offset of the file associated with file descriptor `fd` to `offset`.
- Returns the new file offset on success, or `-1` on failure.

```c
int __file_set_flags(int fd, int flags);
```
- Sets the open status flags of the file associated with file descriptor `fd` to `flags`.
- Common flags include `O_RDONLY`, `O_WRONLY`, `O_RDWR`, and `O_APPEND`.

```c
int __file_set_mode(int fd, mode_t mode);
```
- Sets the mode (`st_mode`) of the file associated with file descriptor `fd`.

```c
mode_t __file_mode(int fd);
```
- Returns the `st_mode` value of the file associated with file descriptor `fd`.
- The returned value encodes both the file type and permission bits (e.g., regular file, directory, `0644`, `0755`).
- Returns `-1` if `fd` does not refer to a valid file.

```c
int __file_flags(int fd);
```
- Returns the open status flags associated with file descriptor `fd`.
- The returned value is a bitmask of the flags used when the file was opened (e.g., `O_RDONLY`, `O_WRONLY`, `O_RDWR`, `O_APPEND`, `O_NONBLOCK`).
- Returns `-1` if `fd` does not refer to a valid open file descriptor.

## `read` / `write`

```c
ssize_t __file_read(int fd, void* buffer, size_t count);

// Identical
ssize_t read(int fd, void buf[count], size_t count);
```
- Reads up to `count` bytes from the file associated with file descriptor `fd` into `buffer`.
- Returns the number of bytes read, which may be less than `count`.
- Advances the file offset by the number of bytes read.
- Returns `0` if the end of the file has been reached.
- Returns `-1` on error.

```c
ssize_t __file_write(int fd, void* buffer, size_t count);
```
- Writes up to `count` bytes from `buffer` to the file associated with file descriptor `fd`.
- Returns the number of bytes written, which may be less than `count`.
- Advances the file offset by the number of bytes written.
- Returns `-1` on error.

## `dup`

```c
int __file_dup(int oldfd);

// Identical
int dup(int oldfd);
```
- Creates a duplicate of the file descriptor `oldfd`.
- The duplicate refers to the same open file description as `oldfd`; both descriptors share the same file offset and open status flags.
- Returns the new file descriptor on success, or `-1` on failure.

```c
int __file_dup2(int oldfd, int newfd);

// Identical
int dup2(int oldfd, int newfd);
```
- Duplicates the file descriptor `oldfd` onto `newfd`.
- If `newfd` is already open, it is closed before being reused.
- The resulting descriptor refers to the same open file description as `oldfd`; both descriptors share the same file offset and open status flags.
- Returns `newfd` on success, or `-1` on failure.
