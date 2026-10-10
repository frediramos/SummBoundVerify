# Summary generation

Claude writes the summaries of libc functions, in two steps:

1. **Fuzzer.** For each function on its own: after each attempt, the fuzzer
   checks the summary, and its findings are sent back, until it accepts it.
2. **Testsuite.** For all the summaries together: the testsuite runs with
   them, and its failures are sent back, until it passes or the attempts run
   out. Every summary changed here is fuzzed again, and must still pass.

A run records how many times the tools checked each summary, and the time,
tokens and cost of every attempt.

## Usage

```bash
workon sbv                     # summbv's virtualenv
./run.py                       # every target in targets/: step 1, then step 2
./run.py read write            # only these: step 1 only
./run.py report                # the latest run's tables
```

Step 2 runs only when a run covers every target, as the testsuite needs all
the summaries.

`run.py` options:

| Option | Default |
|---|---|
| `--model` | `claude-opus-5-5` |
| `--effort` | `high` |
| `--max-iters` | `10` attempts, in each step |
| `--commit` | none: Claude works on the working tree as it is on disk; with a commit, on that commit |
| `--jobs` | one per CPU: testsuite tests run at a time |
| `-keep-work` | off (keeps Claude's working copies, to inspect them) |

## Inputs

```
prompts/
    prompt.md              step 1: first message
    feedback.md            step 1: message after a failed attempt
    testsuite_prompt.md    step 2: first message
    testsuite_feedback.md  step 2: message after a failed attempt
context/examples/      previous summaries, named <function>.c
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
summname: read                        # the libc name, so step 2 can link it
manual: man.txt                       # in targets/<fn>/
output: read.c                        # the summary; same as summ in config.yaml
fuzzer: summbv -config config.yaml -run
```

The prompts can use `{{...}}` placeholders:

- `prompt.md`: every field of `target.yaml`, e.g. `{{function}}`, and
  `{{man_page}}`, `{{examples}}`, `{{templates}}`, `{{output}}`;
- `feedback.md`: `{{output}}` and `{{report}}`, what failed;
- `testsuite_prompt.md`: `{{summaries}}`, `{{tests}}`, `{{helpers}}`,
  `{{manuals}}` (a list of each function's manual page) and `{{report}}`,
  the first testsuite run's failures;
- `testsuite_feedback.md`: `{{summaries}}` and `{{report}}`.

## How a run works

Claude always works in a temporary copy of the repository, deleted after the
step. The copy has no git history, and none of the functions' existing
summaries. It is copied from the working tree as it is on disk, or from
`--commit` if given; this folder's inputs always come from disk. Claude can
read and edit its copy and run `gcc`, but not the fuzzer or the testsuite.

**Step 1**, for each function, in its own session:

1. One `claude -p` call: `prompt.md` the first time, then `feedback.md`.
2. `run.py` runs `fuzzer` on the summary.
3. Repeat until the fuzzer accepts it, or `--max-iters` is reached.
4. The accepted summary is copied, with `config.yaml` and `argspec.yaml`, to
   `summaries/obtained/<fn>/`.

The function's own example, `context/examples/<fn>.c`, is left out of its
copy. Step 2 only runs if the fuzzer accepted every summary.

**Step 2**, for all the summaries, in one session:

1. The testsuite runs with the summaries as step 1 left them
   (`make run FS=ours SUMMARIES=...`).
2. One `claude -p` call: `testsuite_prompt.md` the first time, then
   `testsuite_feedback.md`.
3. `run.py` fuzzes every summary the call changed, then runs the testsuite.
4. Repeat until every test and fuzzer check passes, or `--max-iters` is
   reached.
5. Each summary's latest version the fuzzer accepted is copied back to
   `summaries/obtained/<fn>/`.

## Results

Each run is saved to its own folder in `results/`, named after the time it
started, in UTC: e.g. `results/2026-10-12_09-15-00/`.

```
results/<run id>/
    meta.json                   model, effort, versions, source, commit, input hashes
    summary.json                each step's outcome
    step1/<fn>/
        prompt.txt              prompt as sent
        iter-<n>.json           metrics and fuzzer result of attempt n
        claude-<n>.json         raw claude -p output
        summary-<n>.c           summary after attempt n
        fuzz-<n>.json/.log      fuzzer report and output
        feedback-<n>.txt        feedback sent after attempt n
        transcript.jsonl        the whole session
        summary.json            passed, attempts, totals
    step2/
        start.json              the first testsuite run, before any change
        testsuite-<n>/          testsuite logs of run n (0: the first)
        summaries-<n>/          the summaries after attempt n (0: from step 1)
        iter-<n>.json           metrics, changes, fuzzer and testsuite results of attempt n
        claude-<n>.json         raw claude -p output
        fuzz-<n>-<fn>.json/.log fuzzer report and output, for each changed summary
        feedback-<n>.txt        feedback sent after attempt n
        transcript.jsonl        the whole session
        summary.json            passed, attempts, testsuite before and after, totals
```

`./run.py report` prints three tables (see `./run.py report -h`):

- **step1:** one row per function: attempts until the fuzzer accepted it, and
  their cost;
- **step2:** one row per testsuite run: tests passed, overall and per suite,
  the summaries changed, and the cost;
- **summary:** one row per function: its fuzzer runs and its testsuite runs
  until its suite passed, then step 2's cost, and the total.
