# Klee Notes

## Bugs

1. Could write to a file opened as read-only. (Test 11/13)

2. Could read from a file opened as write-only.

3. `open("file", O_RDONLY)` overrides files permissions.

4. `open` changes the file permissions (POSIX permissions, e.g. `0666`).

5. `dup` copies the file struct instead of sharing it, so the offset is not propagated.

## Notes

- KLEE cannot actually create files. All files are created when launching the tool based on the CLI options. An `open` just assigns an `fd` to a filename.

- KLEE's symbolic files only have `1` character. For instance, an `open` on a symbolic string "assumes" it be `a`.  

- There is a mismatch between concrete and symbolic files. File descriptors opened with a real `open` cannot be passed to KLEE summaries.

## TODO

Changes the KLEE fork (dino-fan777/klee, branch `api_klee`) needs so the test suite runs on it. The tests are written against the shared API (`sra.h`); the fork provides it in `klee/file_api.h`, which the suite's `include/klee/sra.h` includes.

- [ ] Rename `__gen_assert(c)` to `__assert(c)`: fails when the path condition does not imply `c`.
- [ ] Add `int __file_exists(const char *name)`, returning `1` or `0`, possibly symbolic. It replaces `file_exists`, which returned a constraint.
- [ ] `__file_create(name)` must create the file under `name`, which may be symbolic, and return `1` or `-1` without leaving a descriptor open. Today it names files by letter (`'A'`, `'B'`, ...), ignores `name` and returns an open `fd`.
- [ ] `__file_open(name)` must become `__file_open(name, mode)`, with an `fopen` mode string (`"r"`, `"w"`, `"a"`, `"r+"`, `"w+"`, `"a+"`).
- [ ] `__file_mode(fd)` must become `__file_mode(fd, mode_t *mode)`, storing `st_mode` and returning `1` or `-1`.
- [ ] `__file_flags(fd)` must return all the open flags. Today it returns only the access mode, so Open 52-57 would fail on `O_CREAT`, `O_TRUNC` and `O_APPEND`.
- [ ] Add `__sym_var_array(name, index, size)`, used for symbolic file names.
- [ ] Decide how a test is judged. The KLEE runner fails a test when `completed paths = 0`; summbv fails it when an `__assert` fails.
- [ ] Record results for Open 52-57, added after the first 127 tests were run.
