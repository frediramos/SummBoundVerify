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
make run FS=native             # all tests, run natively on Linux, as the reference
make run-all                   # ours, then angr (not native)
make run SUITE=open            # only the open() tests
make run TEST=open/test_01     # one test, with summbv's output shown
```

Tests are named by their path without `.c`: `open/test_01` for
`klee-testsuite/individual-tests/open/test_01.c`. The suites are `open`,
`close`, `read`, `write`, `lseek`, `chmod` and `dup`.

A test passes when summbv exits with status 0 (natively, when the test itself
does). `run` prints a line per test and the totals, and exits non-zero if any
test failed. The results on each file system, and on KLEE, are in
[RESULTS.md](RESULTS.md).

## Options

These can be combined, e.g. `make run FS=angr SUITE=dup SYM_FILE=3`.

| Option       | Effect                                                              |
|--------------|---------------------------------------------------------------------|
| `FS=angr`    | Use angr's native file system (`summbv -angr-fs`). Default: ours.   |
| `FS=native`  | Run the tests natively on Linux, without summbv (see [Native reference](#native-reference)). |
| `SUITE=name` | Run only the tests for one system call.                             |
| `TEST=name`  | Run one test and show summbv's output.                              |
| `LOG=dir`    | Save the logs to `dir` instead of `logs` (see [Logs](#logs)). `LOG=` saves none. |
| `SYM_FILE=N` | Make the tests' file names `N` symbolic bytes followed by `'\0'`. The first byte is non-null; the others are unconstrained, so a name has 1 to `N` characters. Default: 1 byte. |
| `CNCR_FILE=N` | Make the tests' file names `N` concrete characters instead: a test's first name is `"AA..."`, its second `"BB..."`. Cannot be combined with `SYM_FILE`. |

`SYM_FILE=N` and `CNCR_FILE=N` build into `bins/sym-fname-N/` and
`bins/cncr-fname-N/`, so they never reuse binaries built another way. The
KLEE build uses neither.

## Native reference

`make run FS=native` builds the tests against `native/sra_native.c`, an
implementation of the API that does the real Linux operation in each
function, and runs each one natively in a fresh temporary directory. It takes
a few seconds.

The kernel is the reference: a test that fails natively expects something
other than POSIX behaviour, so it cannot test any engine fairly. The tests are
built with `-DNATIVE`, which makes their file names concrete (`CNCR_FILE=N`
sets the names' length; `SYM_FILE` is not allowed). A failed
`__assume` or `__sra_assert` is reported by its position in the test, e.g.
`__sra_assert #2 does not hold`.

Run it as a normal user: root bypasses file permissions, so the permission
tests would fail.

## Logs

`run` saves each test's summbv output to `logs/<fs>/<kind>/<test>.log`,
where `<kind>` is the kind of file names the run used: `sym-fname-<N>` or
`cncr-fname-<N>`.

A plain `make run FS=angr` uses 1 symbolic byte, so it saves
`logs/angr/sym-fname-1/open/test_01.log`. `make run FS=angr CNCR_FILE=1`
saves `logs/angr/cncr-fname-1/open/test_01.log`.

A test's log is from the last run that included it, so a `TEST=` or `SUITE=` run update only those tests' logs. 

## Why tests fail

`run` only prints whether each test passed. To see why, run `report.py`,
which explains the logs:

```bash
make run FS=angr
./report.py                                   # every run in logs/
./report.py logs/angr/sym-fname-1              # one run: every test, then the failures by reason
./report.py logs/angr/sym-fname-1 --failed     # failed tests only
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
