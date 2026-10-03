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
| `LOG=dir`    | Save the logs to `dir` instead of `logs` (see [Logs](#logs)). `LOG=` saves none. |
| `SYM_FILE=N` | Make the tests' file names `N` symbolic bytes followed by `'\0'`. The first byte is non-null; the others are unconstrained, so a name has 1 to `N` characters. Default: 1 byte. |

`SYM_FILE=N` builds into `bins/sym-file-N/`, so it never reuses binaries
built with another value or without it. The KLEE build does not use it.

## Logs

`run` saves each test's summbv output to
`logs/<fs>/sym-file-<N>/<test>.log`.

`N` is the `SYM_FILE` value, 1 by default, so a plain `make run FS=angr`
saves `logs/angr/sym-file-1/open/test_01.log`.

A test's log is from the last run that included it, so a `TEST=` or `SUITE=` run update only those tests' logs. 

## Why tests fail

`run` only prints whether each test passed. To see why, run `report.py`,
which explains the logs:

```bash
make run FS=angr
./report.py                                   # every run in logs/
./report.py logs/angr/sym-file-1              # one run: every test, then the failures by reason
./report.py logs/angr/sym-file-1 --failed     # failed tests only
```

It lists each suite with how many of its tests passed, then each test: its
verdict, its description (from the test's header comment) and, if it failed,
why:

```
open  9/57 passed
  FAILED   test_01  O_RDONLY on existing file succeeds
                    precondition failed: an __assume can never hold
  FAILED   test_53  __file_open mode "w" gives the open flags O_WRONLY | O_CREAT | O_TRUNC
                    assertion failed: False
  PASSED   test_54  __file_open mode "a" gives the open flags O_WRONLY | O_CREAT | O_APPEND
```

and ends with how many tests failed for each reason:

```
Failures by reason
   106  precondition failed: an __assume can never hold
     7  assertion failed: False
     ...
```

To check that a change did not alter any result, log a run before and after
it, and compare:

```bash
make run FS=angr LOG=before
# ... make the change ...
make run FS=angr LOG=after
diff -r before after
```

## Other targets

```bash
make compile                   # regenerate lib/ and build every test
make clean                     # remove all built tests
make clean-logs                # remove all logs
```
