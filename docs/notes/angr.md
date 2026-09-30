# angr Notes

## Bugs

1. `fopen` modes `"w"` and `"w+"` do not set `O_TRUNC` (`mode_to_flag`): `"w"` gives `65` instead of glibc's `577`. (Open 53/56)

2. `open` ignores `O_TRUNC`, so opening an existing file for writing never truncates it.

3. `open` creates a missing file opened for writing, with or without `O_CREAT`, so `"r+"` or `O_RDWR` on a missing file succeeds. (Open 05/06)

4. `open` ignores `O_EXCL`: `O_CREAT | O_EXCL` on an existing file succeeds.

5. A symbolic file name is concretized to one of its values (`solver.eval`), without binding it: nothing records the choice, so each use of the name can choose again and mean a different file. Two `open(fname, O_CREAT | O_RDWR)` on the same symbolic `fname` opened `" "` and `"\x10"`: two different files, where a real system opens the same file twice. The same happens inside the tests' setup: `__file_create(fname)` created `"\x02"`, and the `__file_open(fname, "r+")` that follows created a second file, `"\x10"` (see 3). So a test is rarely about one file: `__assume(exists(fname))` is unsatisfiable when it picks a name that was not created (106 tests), and tests that get past it may be working on a different file from the one they created (e.g. Read 08/09). A correct engine either binds the value it picks (`fname == value`), or splits the path once per file the name could denote.

6. There is no `lseek` summary: it returns an unconstrained value. (Lseek 11)

7. There is no `truncate` or `ftruncate` summary: they return an unconstrained value and leave the file unchanged. `SimFile` has no way to resize a file either: it keeps the size in the private `_size`, which only `write` changes.

8. Files created by `open` have no end of file (`has_end=False`): reads always return the full count and grow the file.

9. `open` ignores `O_CREAT`: it creates a missing file only when opened for writing, so `O_CREAT | O_RDONLY` on a missing file fails. (Open 09)

10. There is no `chmod` summary: it returns an unconstrained value. (Chmod 02)

11. The libc `access` summary ignores the file system: it returns a symbolic `0` or `-1` for any file. (The `access` syscall summary does check it.)

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
  | `__file_create(name)` | `open(name, O_WRONLY \| O_CREAT \| O_EXCL)`, then `close` | `posix.open`, with the file-exists check that `O_EXCL` should do (see 4) |
  | `__file_set_size(fd, size)` | `ftruncate` | sets `SimFile._size` (see 7) |

  All of them load names as `fopen` does, so a symbolic name is concretized (see 5).

- In `src/.../fs/native/functions.py`, each bug is marked `BUG #N` with its number here, and each place where angr is helped is marked `FAIR CHANCE`.

- Relative file names are resolved against `/home/user`, so `"A"` is `/home/user/A`.
