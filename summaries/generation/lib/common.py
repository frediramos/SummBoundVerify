"""
What both steps of a generation use: targets, working copies, calling
Claude, running the fuzzer, and filling in templates.
"""

import os
import re
import sys
import json
import yaml
import time
import shutil
import hashlib
import tempfile
import subprocess

from glob import glob
from pathlib import Path
from typing import NoReturn
from dataclasses import dataclass
from datetime import datetime, timezone


# The generation folder, and the repository it is in
HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]

# The prompts sent to Claude
PROMPTS = HERE / "prompts"

# Where Claude finds its inputs, in its working copy
CONTEXT = Path("summaries/generation/context")

# Where the summaries go, in the repository and in a working copy
OBTAINED = Path("summaries/obtained")

# What Claude may do: read and edit its working copy, and compile with gcc.
# It cannot run summbv, so the fuzzer and the testsuite only run here.
TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
ALLOWED = ["Bash(gcc:*)"]
DISALLOWED = ["Bash(summbv:*)", "WebFetch", "WebSearch"]

CHECK_TIMEOUT = 1800        # seconds, for the fuzzer
SUITE_TIMEOUT = 4 * 3600    # seconds, for the whole testsuite
FEEDBACK_FINDINGS = 3       # fuzzer findings shown in the feedback
FEEDBACK_LOG = 6000         # characters of a failed command's output shown

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def fail(message: str) -> NoReturn:
    sys.exit(f"run.py: {message}")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- Targets -----------------------------------------------------------------

@dataclass
class Target:
    """A libc function to summarize, from targets/<function>/."""

    function: str
    dir: Path
    fields: dict            # everything in target.yaml, for the prompt
    manual: Path
    output: str             # the summary's file name
    fuzzer: str

    @classmethod
    def load(cls, function: str) -> "Target":
        folder = HERE / "targets" / function
        if not (folder / "target.yaml").exists():
            fail(f"no target {folder}/target.yaml")

        fields = yaml.safe_load((folder / "target.yaml").read_text())
        for key in ("output", "fuzzer"):
            if not fields.get(key):
                fail(f"{folder}/target.yaml sets no {key}")

        config = yaml.safe_load((folder / "config.yaml").read_text())
        if fields["output"] != config.get("summ"):
            fail(
                f"output ({fields['output']}) in target.yaml and "
                f"summ ({config.get('summ')}) in config.yaml differ"
            )

        # Step 2 links the summary into the tests in place of the libc
        # function, so it must have its name
        for file, name in (
            ("target.yaml", fields.get("summname")),
            ("config.yaml", config.get("summname"))
        ):
            if name != function:
                fail(
                    f"{folder}/{file}: summname must be {function} "
                    f"(not {name}), the libc function it replaces"
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
            fields["fuzzer"]
        )

    @classmethod
    def all(cls) -> list[str]:
        """The functions with a folder in targets/."""
        folders = (HERE / "targets").iterdir()
        return sorted(f.name for f in folders if f.is_dir())

    @property
    def summary_dir(self) -> Path:
        """
        Where the summary goes, next to the fuzzer's config.yaml, in the
        repository and in a working copy. The fuzzer runs there.
        """
        return OBTAINED / self.function

    @property
    def summary(self) -> Path:
        return self.summary_dir / self.output

    @property
    def manual_copy(self) -> Path:
        """
        The manual page in a working copy: at the same path as in the
        repository, targets/<function>/<manual>.
        """
        return self.manual.relative_to(REPO)

    def files(self) -> list[Path]:
        """The files that define the target, for meta.json."""
        return sorted({self.manual, *self.dir.glob("*.yaml")})


# -- Working copies ----------------------------------------------------------

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
    """
    The working tree's files: tracked ones as they are on disk, and
    untracked ones that are not ignored.
    """
    return git_files("--cached", "--others", "--exclude-standard")


def uncommitted_sha256() -> str | None:
    """
    A hash of what the working tree has that HEAD does not: changes to
    tracked files, and untracked files. None if there is nothing.
    """
    diff = git("diff", "HEAD", "--binary")
    untracked = git_files("--others", "--exclude-standard")
    if not diff and not untracked:
        return None

    h = hashlib.sha256(diff)
    for p in untracked:
        h.update(p.encode() + b"\0" + (REPO / p).read_bytes())
    return h.hexdigest()


def copy_repository(work: Path, commit: str | None):
    """
    The working tree as it is on disk, or `commit`, without git
    history.
    """
    if commit:
        archive = git("archive", commit)
        subprocess.run(["tar", "-x", "-C", work], input=archive, check=True)
        return

    for p in tree_files():
        (work / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / p, work / p, follow_symlinks=False)


def new_work(name: str, targets: list[Target], commit: str | None) -> Path:
    """
    A working copy of the repository, without any existing summary of the
    targets, summaries/obtained/ or this folder.
    """
    work = Path(tempfile.mkdtemp(prefix=f"sbv-gen-{name}-"))
    copy_repository(work, commit)

    hidden = [
        *(f"summaries/{t.function}" for t in targets),
        "summaries/obtained",
        "summaries/generation"
    ]
    for folder in hidden:
        shutil.rmtree(work / folder, ignore_errors=True)

    return work


def copy_fuzzer_setup(target: Target, folder: Path):
    """The fuzzer's config.yaml and argspec.yaml, into `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("config.yaml", "argspec.yaml"):
        shutil.copy(target.dir / name, folder / name)


# -- Claude ------------------------------------------------------------------

@dataclass
class Claude:
    """How Claude is called: the executable, the model and the effort."""

    binary: str
    model: str
    effort: str

    @classmethod
    def find(cls, model: str, effort: str) -> "Claude":
        """$CLAUDE, `claude` on PATH, or the one in the VS Code extension."""
        found = os.environ.get("CLAUDE") or shutil.which("claude")
        if found:
            return cls(found, model, effort)

        pattern = os.path.expanduser(
            "~/.vscode-server/extensions/anthropic.claude-code-*"
            "/resources/native-binary/claude"
        )
        bundled = sorted(glob(pattern))
        if not bundled:
            fail("claude not found; set CLAUDE=/path/to/claude")
        return cls(bundled[-1], model, effort)

    def version(self) -> str:
        return subprocess.run(
            [self.binary, "--version"],
            capture_output=True,
            text=True
        ).stdout.strip()

    def ask(
        self,
        message: str,
        session: str,
        first: bool,
        work: Path
    ) -> tuple[dict, float]:
        """
        A `claude -p` call, in the same session as the previous ones.
        Returns Claude's JSON result and the call's wall time.
        """
        resume = ["--session-id" if first else "--resume", session]
        cmd = [
            self.binary, "-p", "--output-format", "json",
            "--model", self.model, "--effort", self.effort,
            "--setting-sources", "project", "--strict-mcp-config",
            "--tools", TOOLS, "--permission-mode", "acceptEdits",
            "--allowedTools", *ALLOWED,
            "--disallowedTools", *DISALLOWED,
            *resume,
        ]

        start = time.monotonic()
        proc = subprocess.run(
            cmd,
            input=message,
            text=True,
            capture_output=True,
            cwd=work,
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


@dataclass
class Run:
    """One generation: step 1 for each target, then step 2."""

    claude: Claude
    run_id: str
    out: Path               # results/<run id>/
    commit: str | None      # the repository version, or the working tree
    max_iters: int          # attempts before giving up, in each step
    jobs: int               # testsuite tests run at a time
    keep_work: bool         # keep the working copies, to inspect them


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


# The metrics summed over attempts
SUMMED = (
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


def sum_metrics(metrics: list[dict]) -> dict:
    """The metrics of several calls, summed."""
    return {
        key: sum(m[key] or 0.0 for m in metrics)
        for key in SUMMED
    }


def save_transcript(session: str, out: Path):
    """Copies the session's transcript, and its subagents', if any."""
    pattern = os.path.expanduser(f"~/.claude/projects/*/{session}.jsonl")
    for transcript in glob(pattern):
        shutil.copy(transcript, out / "transcript.jsonl")
        subagents = Path(transcript).with_suffix("")
        if subagents.is_dir():
            shutil.copytree(
                subagents,
                out / "transcript",
                dirs_exist_ok=True
            )


# -- The fuzzer --------------------------------------------------------------

@dataclass
class Check:
    """The fuzzer's result on one summary."""

    passed: bool
    time_s: float
    log: str
    report: dict | None = None      # the fuzzer's check report

    def record(self) -> dict:
        counts = {
            test: result.get("counts")
            for test, result in (self.report or {}).items()
        }
        return {
            "passed": self.passed,
            "time_s": self.time_s,
            "counts": counts,
        }


NO_CHECK = Check(passed=False, time_s=0, log="")


def run_command(
    command: str,
    folder: Path,
    env: dict,
    timeout: int = CHECK_TIMEOUT
):
    """Runs `command` in `folder`: returns its status, time and output."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=folder,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout
        )
        status, log = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        status = None
        log = (
            f"{e.stdout or ''}{e.stderr or ''}\n"
            f"(timed out after {timeout}s)"
        )
    elapsed = round(time.monotonic() - start, 3)
    return status, elapsed, ANSI.sub("", log)


def remove(files):
    for f in files:
        if f.is_dir():
            shutil.rmtree(f)
        else:
            f.unlink()


def run_fuzzer(target: Target, work: Path, out: Path, name: str) -> Check:
    """
    Runs the target's fuzzer on its summary in `work`, with the working
    copy's summbv code, and saves its output as <name>.log and its report
    as <name>.json in `out`. Passes when every test in the report is
    `passed`.

    Leaves nothing behind in the working copy, so Claude only sees what the
    feedback says.
    """
    folder = work / target.summary_dir
    env = dict(os.environ, PYTHONPATH=str(work / "src"))
    before = set(folder.iterdir())

    _, elapsed, log = run_command(target.fuzzer, folder, env)
    (out / f"{name}.log").write_text(log)

    report = None
    created = set(folder.iterdir()) - before
    for f in created:
        if f.name.endswith("-concrete_check.json"):
            report = json.loads(f.read_text())
            shutil.copy(f, out / f"{name}.json")
    remove(created)

    passed = bool(report) and all(
        test.get("verdict") == "passed" for test in report.values()
    )
    return Check(passed, elapsed, log, report)


# -- Templates ---------------------------------------------------------------

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
    """
    Each failed test's verdict and counts, and its first findings: why the
    sample was rejected, and its values (the inputs, and the state and
    `Ret` after the libc call).
    """
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


def what_fuzzer_found(check: Check) -> str:
    """Why the fuzzer rejected a summary, for the feedback."""
    if check.report is None:
        return (
            "The fuzzer failed before it could check the summary. "
            "The end of its output:\n\n"
            + code_block(end_of(check.log))
        )
    return fuzzer_findings(check.report)
