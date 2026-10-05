# Klee Notes

## Bugs

1. Could write to a file opened as read-only. ([PR](https://github.com/klee/klee/pull/1804))

2. Could read from a file opened as write-only. ([PR](https://github.com/klee/klee/pull/1804))

3. `open("file", O_RDONLY)` overrides files permissions. ([issue](https://github.com/klee/klee/issues/1815) + [PR](https://github.com/klee/klee/pull/1825)) (Open 12, 44)

4. `open` changes the file permissions (POSIX permissions, e.g. `0666`). ([issue](https://github.com/klee/klee/issues/1815) + [PR](https://github.com/klee/klee/pull/1825)) (Open 45, 46; it also fires in the tests' setup: see `tests/files/testsuite/RESULTS.md`)

5. `dup` copies the file struct instead of sharing it, so the offset is not propagated. (Dup 11)

## Notes

- KLEE cannot actually create files. All files are created when launching the tool based on the CLI options (the fork's `__file_create` adds them at run time). An `open` just assigns an `fd` to a filename.

- KLEE's symbolic files only have `1` character, named by position (`A`, `B`, ...). For instance, an `open` on a symbolic string "assumes" it is `A`.

- There is a mismatch between concrete and symbolic files. File descriptors opened with a real `open` cannot be passed to KLEE summaries.

- The test suite runs on the fork ([dino-fan777/klee](https://github.com/dino-fan777/klee), branch `shared-testsuite`), which implements the suite's shared API (`sra.h`) in `klee/file_api.h`. It follows the same rule as angr: the API uses KLEE's own code, and leaves KLEE's limitations and bugs for the tests to find.

  | API function | On KLEE |
  |---|---|
  | `__file_create(name)` | Creates the next symbolic file, with 10 symbolic bytes and a symbolic `stat`, like `--sym-files`. KLEE names files by position, so only where `name` is the next letter (`'A'`, `'B'`, ...); elsewhere it returns `-1`. |
  | `__file_exists(name)` | KLEE's own lookup of a symbolic file, by letter |
  | `__file_delete(name)` | KLEE's `unlink` |
  | `__file_open(name, mode)` | KLEE's `open`, with `fopen`'s flags for `mode` |
  | `__file_flags(fd)` | The flags `open` was given. KLEE's descriptors keep only the access mode, so `open` also records them, in `open_flags`; nothing else reads it. |
  | `__file_mode` / `__file_set_mode` | The file's `st_mode` |
  | `__sra_assert(c)` | `klee_assert(c)`. Not `__assert`, which uClibc defines. |

- The suite judges a KLEE run like summbv: an `__sra_assert` must hold on every path (the suite's `scripts/verdict.sh`).
