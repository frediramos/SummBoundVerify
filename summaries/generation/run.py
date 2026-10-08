#!/usr/bin/env python3
"""Runs one summary generation: Claude writes the summary of a libc
function, and gets the validation failures back until the summary passes.

    ./run.py read [--model M] [--effort E] [--max-iters N] [--commit C]

Each attempt is one `claude -p` call, followed by the target's fuzzer and,
if it sets one, its testsuite. Everything is saved to
results/<function>/<run id>/. See README.md.

Run it from summbv's virtualenv.
"""

import os
import re
import sys
import json
import yaml
import time
import uuid
import shutil
import hashlib
import tempfile
import argparse
import subprocess

from glob import glob
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# Where Claude finds its inputs, in its working copy
CONTEXT = Path("summaries/generation/context")
MAN_DIR = Path("summaries/generation/man")

# What Claude may do: read and edit its working copy, and compile with gcc.
# It cannot run summbv, so the fuzzer only runs here, once per attempt.
TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
ALLOWED = ["Bash(gcc:*)"]
DISALLOWED = ["Bash(summbv:*)", "WebFetch", "WebSearch"]

CHECK_TIMEOUT = 1800        # seconds, for the fuzzer and the testsuite
FEEDBACK_FINDINGS = 3       # fuzzer findings shown in the feedback
FEEDBACK_LOG = 6000         # characters of a failed command's output shown

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fail(message: str):
    sys.exit(f"run.py: {message}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Target ──────────────────────────────────────────────────────────────────

@dataclass
class Target:
    """A libc function to summarize, from targets/<function>/."""

    function: str
    dir: Path
    fields: dict            # everything in target.yaml, for the prompt
    manual: Path
    output: str             # the summary's file name
    fuzzer: str
    testsuite: str | None

    @classmethod
    def load(cls, function: str) -> "Target":
        folder = HERE / "targets" / function
        if not (folder / "target.yaml").exists():
            fail(f"no target {folder}/target.yaml")

        fields = yaml.safe_load((folder / "target.yaml").read_text())
        for key in ("output", "fuzzer"):
            if not fields.get(key):
                fail(f"{folder}/target.yaml sets no {key}")

        summ = yaml.safe_load((folder / "config.yaml").read_text()).get("summ")
        if fields["output"] != summ:
            fail(
                f"output ({fields['output']}) in target.yaml and "
                f"summ ({summ}) in config.yaml differ"
            )

        manual = folder / fields.get("manual", "man.txt")
        if not manual.exists():
            fail(f"no manual page {manual}")

        return cls(
            function,
            folder,
            fields,
            manual,
            fields["output"],
            fields["fuzzer"],
            fields.get("testsuite")
        )

    def files(self) -> list[Path]:
        """The files that define the target, for meta.json."""
        return sorted({self.manual, *self.dir.glob("*.yaml")})


# ── Run ─────────────────────────────────────────────────────────────────────

@dataclass
class Run:
    target: Target
    args: argparse.Namespace
    claude: str             # the claude executable
    run_id: str
    session: str            # Claude's session, kept across attempts
    out: Path               # results/<function>/<run id>/
    work: Path | None = None

    @property
    def summary_dir(self) -> Path:
        """Where Claude writes the summary, next to the fuzzer's
        config.yaml, in its working copy. The checks run there."""
        return Path("summaries/obtained") / self.target.function

    @property
    def output(self) -> Path:
        return self.summary_dir / self.target.output


@dataclass
class Check:
    """The result of the fuzzer or the testsuite on one attempt."""

    passed: bool
    time_s: float
    log: str
    report: dict | None = None      # the fuzzer's check report


# ── Working copy ────────────────────────────────────────────────────────────

def git(*args) -> bytes:
    return subprocess.run(
        ["git", "-C", REPO, *args],
        check=True,
        capture_output=True
    ).stdout


def git_files(*options) -> list[str]:
    listed = git("ls-files", "-z", *options).decode().split("\0")
    return sorted(p for p in listed if p and (REPO / p).is_file())


def tree_files() -> list[str]:
    """The working tree's files: tracked ones as they are on disk, and
    untracked ones that are not ignored."""
    return git_files("--cached", "--others", "--exclude-standard")


def uncommitted_sha256() -> str | None:
    """A hash of what the working tree has that HEAD does not: changes to
    tracked files, and untracked files. None if there is nothing."""
    diff = git("diff", "HEAD", "--binary")
    untracked = git_files("--others", "--exclude-standard")
    if not diff and not untracked:
        return None

    h = hashlib.sha256(diff)
    for p in untracked:
        h.update(p.encode() + b"\0" + (REPO / p).read_bytes())
    return h.hexdigest()


def make_work(run: Run) -> Path:
    """Claude's working copy: the repository (the working tree, or
    --commit), without git history or any existing summary of the function,
    plus the context, the manual page and the fuzzer's setup."""
    fn = run.target.function
    work = Path(tempfile.mkdtemp(prefix=f"sbv-gen-{fn}-"))

    if run.args.commit:
        archive = git("archive", run.args.commit)
        subprocess.run(["tar", "-x", "-C", work], input=archive, check=True)
    else:
        for p in tree_files():
            (work / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / p, work / p, follow_symlinks=False)

    hidden = (
        f"summaries/{fn}",
        "summaries/obtained",
        "summaries/generation"
    )
    for folder in hidden:
        shutil.rmtree(work / folder, ignore_errors=True)

    shutil.copytree(HERE / "context", work / CONTEXT)
    (work / MAN_DIR).mkdir(parents=True)
    shutil.copy(run.target.manual, work / MAN_DIR / f"{fn}.txt")

    (work / run.summary_dir).mkdir(parents=True)
    for name in ("config.yaml", "argspec.yaml"):
        shutil.copy(run.target.dir / name, work / run.summary_dir / name)

    return work


# ── Claude ──────────────────────────────────────────────────────────────────

def claude_binary() -> str:
    """$CLAUDE, `claude` on PATH, or the one in the VS Code extension."""
    found = os.environ.get("CLAUDE") or shutil.which("claude")
    if not found:
        pattern = os.path.expanduser(
            "~/.vscode-server/extensions/anthropic.claude-code-*"
            "/resources/native-binary/claude"
        )
        bundled = sorted(glob(pattern))
        found = bundled[-1] if bundled else None
    if not found:
        fail("claude not found; set CLAUDE=/path/to/claude")
    return found


def claude_env() -> dict:
    """The environment Claude runs in: without summbv's virtualenv."""
    env = dict(os.environ)
    hidden = set()

    if venv := env.pop("VIRTUAL_ENV", None):
        hidden.add(str(Path(venv) / "bin"))
    if summbv := shutil.which("summbv"):
        hidden.add(str(Path(summbv).parent))

    paths = env["PATH"].split(os.pathsep)
    env["PATH"] = os.pathsep.join(p for p in paths if p not in hidden)
    return env


def ask_claude(run: Run, message: str, first: bool) -> tuple[dict, float]:
    """One attempt: a `claude -p` call, in the same session as the previous
    ones. Returns Claude's JSON result and the call's wall time."""
    session = ["--session-id" if first else "--resume", run.session]
    cmd = [
        run.claude, "-p", "--output-format", "json",
        "--model", run.args.model, "--effort", run.args.effort,
        "--setting-sources", "project", "--strict-mcp-config",
        "--tools", TOOLS, "--permission-mode", "acceptEdits",
        "--allowedTools", *ALLOWED,
        "--disallowedTools", *DISALLOWED,
        *session,
    ]

    start = time.monotonic()
    proc = subprocess.run(
        cmd,
        input=message,
        text=True,
        capture_output=True,
        cwd=run.work,
        env=claude_env()
    )
    wall = time.monotonic() - start

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        result = {
            "is_error": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    return result, wall


def claude_metrics(result: dict, wall: float) -> dict:
    usage = result.get("usage") or {}
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    return {
        "wall_s": round(wall, 3),
        "duration_ms": result.get("duration_ms"),
        "duration_api_ms": result.get("duration_api_ms"),
        "num_turns": result.get("num_turns"),
        "cost_usd": result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens", 0),
        "cache_creation_input_tokens": cache_creation,
        "cache_read_input_tokens": cache_read,
        "output_tokens": usage.get("output_tokens", 0),
        "permission_denials": len(result.get("permission_denials") or []),
        "is_error": result.get("is_error", True),
    }


def save_transcript(run: Run):
    """Copies the session's transcript, and its subagents', if any."""
    pattern = os.path.expanduser(f"~/.claude/projects/*/{run.session}.jsonl")
    for transcript in glob(pattern):
        shutil.copy(transcript, run.out / "transcript.jsonl")
        subagents = Path(transcript).with_suffix("")
        if subagents.is_dir():
            shutil.copytree(
                subagents,
                run.out / "transcript",
                dirs_exist_ok=True
            )


# ── Checks ──────────────────────────────────────────────────────────────────

def run_check(run: Run, command: str, log_name: str):
    """Runs a check command in the summary's folder, with the working copy's
    summbv code, and saves its output as `log_name`.

    Returns its exit status, time, output and the files it created. The
    caller must delete those files, so that Claude only sees the feedback."""
    folder = run.work / run.summary_dir
    env = dict(os.environ, PYTHONPATH=str(run.work / "src"))
    before = set(folder.iterdir())

    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=folder,
            env=env,
            text=True,
            capture_output=True,
            timeout=CHECK_TIMEOUT
        )
        status, log = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        status = None
        log = (
            f"{e.stdout or ''}{e.stderr or ''}\n"
            f"(timed out after {CHECK_TIMEOUT}s)"
        )
    elapsed = round(time.monotonic() - start, 3)

    log = ANSI.sub("", log)
    (run.out / log_name).write_text(log)
    return status, elapsed, log, set(folder.iterdir()) - before


def remove(files):
    for f in files:
        shutil.rmtree(f) if f.is_dir() else f.unlink()


def run_fuzzer(run: Run, i: int) -> Check:
    """Passes when every test in the fuzzer's report is `passed`."""
    _, elapsed, log, created = run_check(
        run,
        run.target.fuzzer,
        f"fuzz-{i}.log"
    )
    report = None
    for f in created:
        if f.name.endswith("-concrete_check.json"):
            report = json.loads(f.read_text())
            shutil.copy(f, run.out / f"fuzz-{i}.json")
    remove(created)

    passed = bool(report) and all(
        test.get("verdict") == "passed" for test in report.values()
    )
    return Check(passed, elapsed, log, report)


def run_testsuite(run: Run, i: int) -> Check | None:
    """Passes when the testsuite exits with 0. None if the target has no
    testsuite."""
    if not run.target.testsuite:
        return None
    status, elapsed, log, created = run_check(
        run,
        run.target.testsuite,
        f"testsuite-{i}.log"
    )
    remove(created)
    return Check(status == 0, elapsed, log)


# ── Feedback ────────────────────────────────────────────────────────────────

def render(template: Path, values: dict) -> str:
    text = template.read_text()
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", str(value))
    return text


def code_block(text: str, lang: str = "") -> str:
    return f"```{lang}\n{text}\n```"


def end_of(log: str) -> str:
    log = log.strip()
    if len(log) <= FEEDBACK_LOG:
        return log
    return "...\n" + log[-FEEDBACK_LOG:]


def fuzzer_findings(report: dict) -> str:
    """Each failed test's verdict and counts, and its first findings: why
    the sample was rejected, and its values (the inputs, and the state and
    `Ret` after the libc call)."""
    parts = [
        "The fuzzer found inputs on which the summary disagrees with libc."
    ]

    for test, result in report.items():
        if result.get("verdict") == "passed":
            continue

        verdict = result.get("verdict")
        counts = json.dumps(result.get("counts"))
        parts.append(f"`{test}`: {verdict}, counts {counts}.")

        findings = result.get("findings") or []
        for finding in findings[:FEEDBACK_FINDINGS]:
            bindings = json.dumps(finding.get("bindings"), indent=2)
            parts.append(
                f"- {finding.get('reason')}:\n\n"
                + code_block(bindings, "json")
            )

        hidden = len(findings) - FEEDBACK_FINDINGS
        if hidden > 0:
            parts.append(f"({hidden} more findings not shown.)")

    return "\n\n".join(parts)


def what_failed(
    run: Run,
    written: bool,
    fuzz: Check,
    suite: Check | None
) -> str:
    """The {{report}} of feedback.md."""
    if not written:
        return f"There is no summary at `{run.output}`."

    parts = []
    if not fuzz.passed:
        if fuzz.report is None:
            parts.append(
                "The fuzzer failed before it could check the summary. "
                "The end of its output:\n\n"
                + code_block(end_of(fuzz.log))
            )
        else:
            parts.append(fuzzer_findings(fuzz.report))

    if suite is not None and not suite.passed:
        parts.append(
            "The testsuite failed. The end of its output:\n\n"
            + code_block(end_of(suite.log))
        )

    return "\n\n".join(parts)


# ── Records ─────────────────────────────────────────────────────────────────

def write_meta(run: Run):
    """meta.json: everything that defines the run, so runs can be compared."""
    context = sorted(p for p in (HERE / "context").rglob("*") if p.is_file())
    inputs = [
        HERE / "prompt.md",
        HERE / "feedback.md",
        *context,
        *run.target.files(),
    ]

    commit = git("rev-parse", run.args.commit or "HEAD").decode().strip()
    uncommitted = None if run.args.commit else uncommitted_sha256()
    generation_dirty = git("status", "--porcelain", "--", str(HERE)).strip()

    version = subprocess.run(
        [run.claude, "--version"],
        capture_output=True,
        text=True
    ).stdout.strip()

    write_json(run.out / "meta.json", {
        "function": run.target.function,
        "run_id": run.run_id,
        "session_id": run.session,
        "source": "commit" if run.args.commit else "working tree",
        "commit": commit,
        "uncommitted_sha256": uncommitted,
        "generation_dir_uncommitted_changes": bool(generation_dirty),
        "model": run.args.model,
        "effort": run.args.effort,
        "max_iters": run.args.max_iters,
        "claude_version": version,
        "tools": TOOLS,
        "allowed": ALLOWED,
        "disallowed": DISALLOWED,
        "inputs_sha256": {
            str(p.relative_to(HERE)): sha256(p) for p in inputs
        },
        "started_at": now(),
    })


def iteration_record(
    i: int,
    metrics: dict,
    written: bool,
    fuzz: Check,
    suite: Check | None,
    passed: bool
) -> dict:
    """iter-<i>.json"""
    return {
        "iteration": i,
        "claude": metrics,
        "summary_written": written,
        "fuzzer": {
            "passed": fuzz.passed,
            "time_s": fuzz.time_s,
            "counts": {
                test: result.get("counts")
                for test, result in (fuzz.report or {}).items()
            },
        },
        "testsuite": None if suite is None else {
            "passed": suite.passed,
            "time_s": suite.time_s,
        },
        "passed": passed,
    }


def run_summary(run: Run, iterations: list[dict], passed: bool) -> dict:
    """summary.json: the run's outcome, and its metrics summed over the
    attempts."""
    summed = (
        "wall_s",
        "duration_ms",
        "duration_api_ms",
        "num_turns",
        "cost_usd",
        "input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "output_tokens",
        "permission_denials",
    )
    totals = {
        key: sum(it["claude"][key] or 0 for it in iterations)
        for key in summed
    }
    totals["fuzzer_time_s"] = sum(it["fuzzer"]["time_s"] for it in iterations)

    return {
        "function": run.target.function,
        "run_id": run.run_id,
        "passed": passed,
        "iterations": len(iterations),
        "totals": totals,
        "finished_at": now(),
    }


# ── Main ────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("function", help="a folder in targets/")
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="high")
    ap.add_argument(
        "--max-iters",
        type=int,
        default=10,
        help="attempts before giving up (default: 10)"
    )
    ap.add_argument(
        "--commit",
        help="repository version Claude works on "
             "(default: the working tree, as it is on disk)"
    )
    ap.add_argument(
        "--keep-work",
        action="store_true",
        help="keep Claude's working copy, to inspect it"
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    target = Target.load(args.function)
    if not shutil.which("summbv"):
        fail("summbv not on PATH; activate its virtualenv")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = Run(
        target=target,
        args=args,
        claude=claude_binary(),
        run_id=run_id,
        session=str(uuid.uuid4()),
        out=HERE / "results" / target.function / run_id
    )
    run.out.mkdir(parents=True)

    prompt = render(HERE / "prompt.md", {
        **target.fields,
        "man_page": MAN_DIR / f"{target.function}.txt",
        "examples": CONTEXT / "examples",
        "templates": CONTEXT / "templates",
        "output": run.output,
    })
    (run.out / "prompt.txt").write_text(prompt)
    write_meta(run)
    run.work = make_work(run)

    source = args.commit or "working tree"
    print(
        f"{target.function}: run {run_id}  "
        f"({args.model}, effort {args.effort}, {source})"
    )

    message = prompt
    iterations = []
    passed = False

    for i in range(1, args.max_iters + 1):
        result, wall = ask_claude(run, message, first=(i == 1))
        write_json(run.out / f"claude-{i}.json", result)

        summary = run.work / run.output
        written = summary.exists()
        if written:
            shutil.copy(summary, run.out / f"summary-{i}.c")
            fuzz = run_fuzzer(run, i)
            suite = run_testsuite(run, i)
        else:
            fuzz, suite = Check(passed=False, time_s=0, log=""), None

        passed = fuzz.passed and (suite is None or suite.passed)
        metrics = claude_metrics(result, wall)
        record = iteration_record(i, metrics, written, fuzz, suite, passed)
        write_json(run.out / f"iter-{i}.json", record)
        iterations.append(record)

        status = "passed" if passed else "failed"
        checking = fuzz.time_s + (suite.time_s if suite else 0)
        print(
            f"  attempt {i:<3} {status:<7}"
            f" generating {wall:5.0f}s"
            f"   checking {checking:5.0f}s"
            f"   {metrics['output_tokens']:>7,} output tokens"
        )
        if passed:
            break

        message = render(HERE / "feedback.md", {
            "output": run.output,
            "report": what_failed(run, written, fuzz, suite),
        })
        (run.out / f"feedback-{i}.txt").write_text(message)

    save_transcript(run)
    write_json(run.out / "summary.json", run_summary(run, iterations, passed))

    if args.keep_work:
        print(f"  working copy kept in {run.work}")
    else:
        shutil.rmtree(run.work)

    outcome = "passed" if passed else "did not pass"
    print(
        f"{target.function}: {outcome} after {len(iterations)} attempt(s)"
        f"  ->  {run.out.relative_to(HERE)}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
