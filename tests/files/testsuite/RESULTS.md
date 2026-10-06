# Test suite results

The 133 tests in `klee-testsuite/`, run on each file system. Bug numbers refer to
[docs/notes/angr.md](../../../docs/notes/angr.md) and
[docs/notes/klee.md](../../../docs/notes/klee.md).

| Suite | Native | Ours | angr (symb fnames)| angr (cncrt fnames) | KLEE |
|---|---|---|---|---|---|
| `open` | 57/57 | 6/57 | 10/57 | 39/57 | 18/57 |
| `close` | 10/10 | 2/10 | 2/10 | 9/10 | 8/10 |
| `read` | 12/12 | 1/12 | 2/12 | 8/12 | 7/12 |
| `write` | 13/13 | 1/13 | 2/13 | 8/13 | 2/13 |
| `lseek` | 15/15 | 0/15 | 0/15 | 0/15 | 12/15 |
| `chmod` | 13/13 | 0/13 | 0/13 | 0/13 | 1/13 |
| `dup` | 13/13 | 2/13 | 2/13 | 10/13 | 11/13 |
| **Total** | **133** | **12** | **18** | **74** | **59** |

How each column was run:

| Column | Command |
|---|---|
| Native | `make run FS=native` |
| Ours | `make run` |
| angr, symbolic names | `make run FS=angr` |
| angr, concrete names | `make run FS=angr CNCR_FILE=1` |
| KLEE | `make run FS=klee`, after `make klee-image` (see [README](README.md#klee)) |

## Native

Every test passes on Linux, so each failure below is the engine's, not the
test's.

## Ours

TODO

## angr

**Symbolic names:** 103 tests fail before reaching what they test.

- angr turns a symbolic name into one arbitrary value, and forgets the
  choice (bug 5).
- So `__assume(exists(fname))` asks about a file that was never created,
  and cannot hold.

**Concrete names:** every test reaches what it tests. The 59 failures are all
angr bugs:

- 28: no `lseek` (bug 6)
- 18: no `chmod` (bug 10)
- 8: `open`, `read` and `write` mishandle flags (bugs 1, 3, 4, 9, 12)
- 3: no file permissions (bug 13)
- 2: no descriptor limit (bug 14)

## KLEE

All 74 failures are `__sra_assert` failures, for these reasons:

- **The setup sets off bug 4.** `create_test_file` opens the file with
  `__file_open(name, "r+")`. KLEE's `open` then overwrites the file's
  permissions with `0000`, so every later `open` of it fails with `EACCES`.
- **The test file's permissions are unknown.** KLEE creates it with a
  symbolic `stat`, as it does for `--sym-files`. So `open` explores both
  "permission granted" and "permission denied", and the test's
  `__sra_assert` fails on the denied paths.
- **The rewritten tests find KLEE bugs:**
  - Open 12, 44: `O_RDONLY` skips the read-permission check (bug 3)
  - Open 45, 46: `open` overwrites the file's mode (bug 4)
  - Dup 11: `dup`'d descriptors don't share the offset (bug 5)

Open 47 and Dup 06 pass only by coincidence: KLEE ignores `setrlimit`, but its
fixed table of 32 descriptors matches the limit they set.
