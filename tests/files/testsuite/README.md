# File-system test suite

Runs the file-system test suite in `klee-testsuite/` (a git submodule) with
summbv. The tests are written against the shared API in `lib/sra.h`, so the
same tests also run on KLEE.

The first time, fetch the submodule and build everything:

```bash
git submodule update --init
make compile
```

`make compile` also regenerates `lib/sra.h` and `lib/sra.c`, so it needs the
Python environment where summbv is installed.

## Running tests

```bash
make run                       # all tests, on our file system
make run FS=angr               # all tests, on angr's native file system
make run-all                   # both, one after the other
make run SUITE=open            # only the open() tests
make run TEST=open/test_01     # one test, with summbv's output shown
```

Tests are named by their path without `.c`: `open/test_01` for
`klee-testsuite/individual-tests/open/test_01.c`. The suites are `open`,
`close`, `read`, `write`, `lseek`, `chmod` and `dup`.

A test passes when summbv exits with status 0. `run` prints a line per test
and the totals, and exits non-zero if any test failed.

## Options

These can be combined, e.g. `make run FS=angr SUITE=dup SYM_FILE=3`.

| Option       | Effect                                                              |
|--------------|---------------------------------------------------------------------|
| `FS=angr`    | Use angr's native file system (`summbv -angr-fs`). Default: ours.   |
| `SUITE=name` | Run only the tests for one system call.                             |
| `TEST=name`  | Run one test and show summbv's output.                              |
| `SYM_FILE=N` | Make the tests' file names `N` symbolic bytes followed by `'\0'`. The first byte is non-null; the others are unconstrained, so a name has 1 to `N` characters. Default: 1 byte. |

`SYM_FILE=N` builds into `bins/sym-file-N/`, so it never reuses binaries
built with another value or without it. The KLEE build does not use it.

## Other targets

```bash
make compile                   # regenerate lib/ and build every test
make clean                     # remove all built tests
```
