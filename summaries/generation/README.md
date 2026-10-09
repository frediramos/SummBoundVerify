# Summary generation

Claude writes the summary of a libc function. After each attempt, the fuzzer
checks it and any failures are sent back, until the summary passes. Each run
records the number of attempts, and the time and tokens of each one.

## Usage

```bash
workon sbv                     # summbv's virtualenv
./run.py read                  # one run for read
./report.py                    # tables of all runs
```

`run.py` options:

| Option | Default |
|---|---|
| `--model` | `claude-opus-5-5` |
| `--effort` | `high` |
| `--max-iters` | `10` |
| `--commit` | none: Claude works on the working tree as it is on disk; with a commit, on that commit |
| `-keep-work` | off (keeps Claude's working copy, to inspect it) |

## Inputs

```
prompt.md              first message of a run
feedback.md            message after a failed attempt
context/examples/      previous summaries
context/templates/     summarization templates
targets/<fn>/
    target.yaml        the function (see below)
    man.txt            its manual page
    config.yaml        fuzzer setup (incl. execs)
    argspec.yaml       fuzzer arguments
```

`target.yaml`:

```yaml
function: read
summname: summ_read
manual: man.txt                       # in targets/<fn>/
output: read.c                        # the summary; same as summ in config.yaml
fuzzer: summbv -config config.yaml -run
testsuite:                            # optional; empty = skipped
```

`prompt.md` and `feedback.md` can use `{{...}}` placeholders:

- every field of `target.yaml`, e.g. `{{function}}`;
- `{{man_page}}`, `{{examples}}`, `{{templates}}`, `{{output}}`;
- in `feedback.md` only, `{{report}}`: what failed.

## How a run works

1. **Copy.** `run.py` makes a temporary copy of the repository for Claude to
   work in, and deletes it after the run. The copy has no git history and no
   existing summary of the function. It is copied from the working tree as
   it is on disk, uncommitted changes included, or from `--commit` if given.
   `context/` and the target's files always come from disk.
2. **Generate.** One `claude -p` call, with `prompt.md` the first time and
   `feedback.md` after that, all in the same session.
3. **Check.** `run.py` runs `fuzzer`, then `testsuite`, in
   `summaries/obtained/<fn>/`. Claude cannot run them itself.
4. **Repeat** steps 2–3 until both pass, or `--max-iters` is reached.

## Results

```
results/<fn>/<run id>/
    meta.json           model, effort, versions, source, commit, input hashes
    prompt.txt          prompt as sent
    iter-<n>.json       metrics and check results of attempt n
    claude-<n>.json     raw claude -p output
    summary-<n>.c       summary after attempt n
    fuzz-<n>.json/.log  fuzzer report and output
    feedback-<n>.txt    feedback sent after attempt n
    transcript.jsonl    the whole session
    summary.json        passed, attempts, totals
```

Metrics:

- **Attempts:** the number of `claude -p` calls until the summary passed.
- **Time:** `duration_api_ms` is model time; `wall_s` is the whole call,
  including tools. Fuzzing time is recorded separately.
- **Tokens:** `report.py` sums the three input counters (uncached, cache
  write, cache read) into one input figure.
