# angr Notes

## Bugs

1. `fopen` modes `"w"` and `"w+"` do not set `O_TRUNC` (`mode_to_flag`): `"w"` gives `65` instead of glibc's `577`. (Open 53/56)

2. `open` ignores `O_TRUNC`, so opening an existing file for writing never truncates it.

3. `open` creates a missing file opened for writing, with or without `O_CREAT`, so `"r+"` or `O_RDWR` on a missing file succeeds. (Open 05/06)

4. `open` ignores `O_EXCL`: `O_CREAT | O_EXCL` on an existing file succeeds. (Open 15)

5. A symbolic file name is concretized to one value (`solver.eval`) without binding it, so each use of the name can pick a different value and mean a different file: two `open(fname)` on the same symbolic `fname` opened `" "` and `"\x10"`. With symbolic names, `__assume(exists(fname))` therefore checks an arbitrary name that was never created, and fails. (103 tests)

6. There is no `lseek` summary: it returns an unconstrained value and leaves the offset unchanged, so data written and then read back after `lseek(fd, 0, SEEK_SET)` does not match. (Lseek 01-15, and 13 other tests that seek)

7. There is no `truncate` or `ftruncate` summary: they return an unconstrained value and leave the file unchanged. `SimFile` has no way to resize a file either: it keeps the size in the private `_size`, which only `write` changes.

8. Files created by `open` have no end of file (`has_end=False`): reads always return the full count and grow the file.

9. `open` ignores `O_CREAT`: it creates a missing file only when opened for writing, so `O_CREAT | O_RDONLY` on a missing file fails. (Open 09)

10. There is no `chmod` summary: it returns an unconstrained value. (Chmod 01-13, Open 42-46)

11. The libc `access` summary ignores the file system: it returns a symbolic `0` or `-1` for any file. (The `access` syscall summary does check it.)

12. `read` and `write` ignore the access mode: reading a file opened `O_WRONLY`, or writing one opened `O_RDONLY`, succeeds instead of failing with `EBADF`. A descriptor's flags are only checked for `O_APPEND`. (Read 03, Write 03)

13. angr has no file permissions: a file keeps no mode, and `open` never checks one, so opening a `0444` file for writing succeeds. Nor can a program read a mode back: libc's `fstat` has no summary, so it returns an unconstrained value and leaves the `stat` buffer unchanged. (Open 10-12)

14. angr ignores the descriptor limit: there is no `setrlimit` summary, and descriptors are numbered up to a fixed 8192 (`max_fds`) whatever `RLIMIT_NOFILE` is. So after limiting a program to 32 descriptors, a further `open` and `dup2(fd, 32)` succeed instead of failing with `EMFILE` and `EBADF`. (Open 47, Dup 06)

## Notes

- To give angr a fair chance:
  - The engine turns off `ALL_FILES_EXIST` on angr's file system. It is on by default in symbolic mode, and makes `open` invent any missing file, even read-only, with symbolic contents and size.
  - `__file_create` gives the file it creates an end of file (`has_end=True`). Files created by angr's own `open` still have none.

- The API functions run angr's own summaries, so the tests see angr's behaviour:

  | API function | Stands for | angr code it runs |
  |---|---|---|
  | `__file_open(name, mode)` | `fopen`, returning the fd | `fopen` summary: `mode_to_flag`, `posix.open` |
  | `__file_close(fd)` | `close` | `close` summary |
  | `__file_exists(name)` | `access(name, F_OK)` | `access` syscall summary |
  | `__file_flags(fd)` | `fcntl(fd, F_GETFL)` | the descriptor's `flags` |
  | `__file_create(name)` | `open(name, O_WRONLY \| O_CREAT \| O_EXCL, 0644)`, then `close` | `posix.open`, with the file-exists check that `O_EXCL` should do (see 4); records the mode `0644` (see 13) |
  | `__file_set_size(fd, size)` | `ftruncate` | sets `SimFile._size` (see 7) |
  | `__file_set_mode(fd, mode)` | `fchmod` | records the mode in the state's globals; only `__file_mode` reads it (see 13) |
  | `__file_mode(fd, &mode)` | `fstat`'s `st_mode` | the recorded mode, as a regular file; for other files, `posix.fstat`: a new symbolic `st_mode` (see 13) |

  All of them load names as `fopen` does, so a symbolic name is concretized (see 5).

- In `src/.../fs/native/functions.py`, each bug is marked `BUG #N` with its number here, and each place where angr is helped is marked `FAIR CHANCE`.

- Relative file names are resolved against `/home/user`, so `"A"` is `/home/user/A`.
