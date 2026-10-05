# Test suite results

The 133 tests in `klee-testsuite/`, run on each file system. A test passes
only if every `__sra_assert` holds on every path. Bug numbers refer to
[docs/notes/angr.md](../../../docs/notes/angr.md) and
[docs/notes/klee.md](../../../docs/notes/klee.md).

| Suite | Native | Ours | angr, symbolic names | angr, concrete names | KLEE |
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
| KLEE | the suite's own runner, `make json_all`, on the fork (see [klee.md](../../../docs/notes/klee.md)) |

## Native

Every test passes on Linux, so each failure below is the engine's, not the
test's.

## Ours

Our file system does not model the C library's file functions yet, so tests
fail at their first call to one:

- 102 reach angr's own `open`, which expects angr's file system plugin
  (`'SymbolicFS' object has no attribute 'get'`).
- 18 call `chmod` and 1 calls `lseek`, which return an unconstrained value.

The 12 that pass use only the API (Open 52-57: the `__file_open` modes) or an
invalid descriptor.

## angr

- **Symbolic names:** 103 tests fail at their precondition. angr concretizes
  a symbolic name to an arbitrary value without binding it (bug 5), so
  `__assume(exists(fname))` checks a file that was never created.
- **Concrete names:** every test reaches what it tests, and each of the 59
  failures is an angr bug: bug 6, no `lseek` (28); bug 10, no `chmod` (18);
  bugs 1, 3, 4, 9 and 12, `open`, `read` and `write` (8); bug 13, no
  permissions (3); bug 14, no descriptor limit (2).

## KLEE

All 74 failures are `__sra_assert` failures:

- Bug 4 fires in the tests' setup. `create_test_file` opens the file with
  `__file_open(name, "r+")`: KLEE's `open` without `O_CREAT` takes mode `0`,
  so the file's permissions become `0000`, and later `open`s of it fail with
  `EACCES`.
- A file from `__file_create` has a symbolic `stat`, as KLEE's `--sym-files`
  do, so its permissions are symbolic: `open` splits on its permission
  check, and the test's `__sra_assert` fails on the paths where they refuse
  the operation.
- Bug 3 fails Open 12 and 44, bug 4 Open 45 and 46, and bug 5 Dup 11. Open 47
  and Dup 06 pass only because KLEE's fixed table of 32 descriptors matches
  the limit they set: KLEE ignores `setrlimit`.
