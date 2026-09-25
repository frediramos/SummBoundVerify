## Running the Tests

Generate and compile all tests:

```sh
make test
```

Generate, compile, and run all tests:

```sh
make test-run
```

Remove all generated files:

```sh
make clean
```

During execution, each summary test is reported as **PASS**/**FAIL**.
## File system tests (fuzzing)

Each directory under `files/argspec` is one test, organised like the `libc`
ones: a summary, a concrete implementation, an argspec, a `config.yaml`, its
own `Makefile` and the expected outputs.

| File                       | Checked by      | What it pins down                         |
|----------------------------|-----------------|-------------------------------------------|
| `expected_summary_test.c`  | `make test`     | the generated summary test                |
| `expected_concrete_test.c` | `make test`     | the generated concrete (AFL++) test       |
| `expected_result.json`     | `make test-run` | the verdict the fuzz engine must reach    |

`expected_result.json` maps each test to a verdict:

```json
{
  "test_1": {
    "verdict": "passed"
  }
}
```

- `passed` — a correct summary: every sample is admitted.
- `mismatched` — a summary that is wrong on purpose (the `*_bug`
  directories): the engine must find a counterexample. These guard against
  a checker that accepts everything.

From `files/argspec`, `make test`, `make test-run` and `make clean` run every
test; from inside a test directory they run that one alone, and `make gen` /
`make run` generate or run it without comparing. `EXECS` sets how many inputs
the fuzzer tries (default 2000):

```sh
make test-run EXECS=5000
make -C dup_write_bug test-run
```

After an intended change to the generated code, refresh a test's expected
files from its directory with `make gen`, then copy
`<dir>_validation-summary.c` and `<dir>_validation-concrete.c` over the
`expected_*_test.c` files.
