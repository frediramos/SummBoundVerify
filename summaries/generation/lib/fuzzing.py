"""
Step 1: Claude writes the summary of one function, and gets the fuzzer's
findings back until the fuzzer accepts it. The summary is then copied to
summaries/obtained/<function>/. Everything is saved to
results/<run id>/step1/<function>/.
"""

import uuid
import shutil

from pathlib import Path
from dataclasses import dataclass

from .common import (
    HERE,
    REPO,
    CONTEXT,
    PROMPTS,
    NO_CHECK,
    Run,
    Check,
    Target,
    now,
    render,
    new_work,
    run_fuzzer,
    write_json,
    sum_metrics,
    claude_metrics,
    save_transcript,
    copy_fuzzer_setup,
    what_fuzzer_found,
)


@dataclass
class Attempt:
    """One `claude -p` call, and the fuzzer's check of the summary it left."""

    number: int
    claude: dict            # time, tokens and cost of the call
    written: bool           # whether there was a summary to check
    fuzz: Check

    @property
    def passed(self) -> bool:
        return self.fuzz.passed

    def record(self) -> dict:
        """iter-<number>.json"""
        return {
            "iteration": self.number,
            "claude": self.claude,
            "summary_written": self.written,
            "fuzzer": self.fuzz.record(),
            "passed": self.passed,
        }


# -- Working copy ------------------------------------------------------------

def context_files(target: Target) -> list[Path]:
    """
    The files of context/ that Claude sees: all of them, except the
    function's own example, context/examples/<function>.c.
    """
    own = HERE / "context" / "examples" / f"{target.function}.c"
    files = (HERE / "context").rglob("*")
    return sorted(p for p in files if p.is_file() and p != own)


def make_work(target: Target, commit: str | None) -> Path:
    """
    Claude's working copy: the repository without any existing summary of
    the function, plus the context, the manual page and the fuzzer's setup.
    """
    work = new_work(target.function, [target], commit)

    for p in context_files(target):
        copy = work / CONTEXT / p.relative_to(HERE / "context")
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(p, copy)

    (work / target.manual_copy).parent.mkdir(parents=True)
    shutil.copy(target.manual, work / target.manual_copy)

    copy_fuzzer_setup(target, work / target.summary_dir)
    return work


# -- Prompt and feedback -----------------------------------------------------

def first_prompt(target: Target) -> str:
    """prompt.md, filled in for the target."""
    return render(PROMPTS / "prompt.md", {
        **target.fields,
        "man_page": target.manual_copy,
        "examples": CONTEXT / "examples",
        "templates": CONTEXT / "templates",
        "output": target.summary,
    })


def feedback(target: Target, attempt: Attempt, out: Path) -> str:
    """feedback.md, filled in with what failed; saved as feedback-<n>.txt."""
    if attempt.written:
        report = what_fuzzer_found(attempt.fuzz)
    else:
        report = f"There is no summary at `{target.summary}`."

    message = render(PROMPTS / "feedback.md", {
        "output": target.summary,
        "report": report,
    })
    (out / f"feedback-{attempt.number}.txt").write_text(message)
    return message


# -- The loop ----------------------------------------------------------------

def attempt(
    run: Run,
    target: Target,
    session: str,
    work: Path,
    out: Path,
    number: int,
    message: str
) -> Attempt:
    """
    Sends `message` to Claude, then runs the fuzzer on the summary it left.
    Saves claude-<n>.json, summary-<n>.c, fuzz-<n>.* and iter-<n>.json.
    """
    result, wall = run.claude.ask(message, session, number == 1, work)
    write_json(out / f"claude-{number}.json", result)

    summary = work / target.summary
    written = summary.exists()

    if written:
        shutil.copy(summary, out / f"summary-{number}.c")
        fuzz = run_fuzzer(target, work, out, f"fuzz-{number}")
    else:
        fuzz = NO_CHECK

    done = Attempt(number, claude_metrics(result, wall), written, fuzz)
    write_json(out / f"iter-{number}.json", done.record())
    return done


def publish(target: Target, work: Path) -> Path:
    """
    Copies the summary the fuzzer accepted, with the fuzzer's setup, to
    summaries/obtained/<function>/, replacing any earlier one.
    """
    folder = REPO / target.summary_dir
    shutil.rmtree(folder, ignore_errors=True)
    copy_fuzzer_setup(target, folder)
    shutil.copy(work / target.summary, folder)
    return folder


def write_summary(target: Target, attempts: list[Attempt], out: Path):
    """summary.json: the target's outcome, and its metrics summed."""
    write_json(out / "summary.json", {
        "function": target.function,
        "passed": attempts[-1].passed,
        "iterations": len(attempts),
        "totals": {
            **sum_metrics([a.claude for a in attempts]),
            "fuzzer_time_s": sum(a.fuzz.time_s for a in attempts),
        },
        "finished_at": now(),
    })


def print_attempt(attempt: Attempt):
    status = "passed" if attempt.passed else "failed"
    tokens = attempt.claude["output_tokens"]
    print(
        f"    attempt {attempt.number:<3} {status:<7}"
        f" generating {attempt.claude['wall_s']:5.0f}s"
        f"   fuzzing {attempt.fuzz.time_s:5.0f}s"
        f"   {tokens:>7,} output tokens"
    )


def generate(run: Run, target: Target) -> bool:
    """
    Step 1 for one target. Returns whether the fuzzer accepted its summary,
    which is then in summaries/obtained/<function>/.
    """
    out = run.out / "step1" / target.function
    out.mkdir(parents=True)
    session = str(uuid.uuid4())
    work = make_work(target, run.commit)

    print(f"  {target.function}")
    message = first_prompt(target)
    (out / "prompt.txt").write_text(message)

    attempts = []
    for number in range(1, run.max_iters + 1):
        attempts.append(
            attempt(run, target, session, work, out, number, message)
        )
        print_attempt(attempts[-1])
        if attempts[-1].passed:
            break
        message = feedback(target, attempts[-1], out)

    save_transcript(session, out)
    write_summary(target, attempts, out)

    passed = attempts[-1].passed
    if passed:
        publish(target, work)

    if run.keep_work:
        print(f"    working copy kept in {work}")
    else:
        shutil.rmtree(work)

    return passed
