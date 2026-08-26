import sys
import json
import logging
import traceback

from pathlib import Path
from typing import Literal
from argparse import Namespace

from summboundverify.exceptions import RunError
from summboundverify.logger import Colors, section, setup_logging
from summboundverify.options import parse_input_args
from summboundverify.validation_gen import ValidationGenerator, CCompiler

Arch = Literal['x86', 'x64']

logger = logging.getLogger(__name__)

ENGINE_TITLES = {
    'se': 'Symbolic execution (angr)',
    'fuzz': 'Fuzzing (AFL++)',
}


def compile_validation_test(arch: Arch, file: Path, libs: list[str]):
    name = file.stem + '.test'
    out = file.parent / name
    comp = CCompiler(arch, file, out, libs)
    comp.compile()
    return out


# Takes command line / config file arguments
def run_validation_gen(args: Namespace, engine: str = 'se',
                       outputfile: Path | None = None):
    '''
    Take command line args and run the test generation
    @args: \'argparse\' Namespace object
    @engine: which backend the test is emitted for ('se' or 'fuzz')
    @outputfile: override for the generated test path
    '''
    concrete_function = Path(args.func) if args.func else None
    target_summary = Path(args.summ) if args.summ else None
    outputfile = Path(outputfile) if outputfile else Path(args.o)
    summname = args.summname
    funcname = args.funcname

    if not concrete_function and not target_summary:
        err = "ERROR: At least the code for a concrete function or summary MUST be provided"
        sys.exit(err)

    if not concrete_function and not funcname:
        err = (
            "ERROR: No concrete function code or name provided\n"
            "INFO: In the absence of the code, a name must be specified in order to call the function"
        )
        sys.exit(err)

    if not target_summary and not summname:
        err = (
            "ERROR: No summary code or name provided\n"
            "INFO: In the absence of the code, a name must be specified in order to call the summary"
        )
        sys.exit(err)

    valgenerator = ValidationGenerator(
        concrete_function,
        target_summary,
        outputfile,
        arraysize=args.arraysize,
        nullbytes=args.nullbytes,
        maxnum=args.maxvalue,
        maxnames=args.maxnames,
        default=args.defaultvalues,
        concrete_arrays=args.concretearray,
        memory=args.memory,
        cncrt_name=funcname,
        summ_name=summname,
        no_api=args.noapi,
        engine=engine,
    )

    valgenerator.gen()
    return outputfile




def sampler_libs(args: Namespace) -> list:
    '''The libraries the sampling harness needs: everything but the summary.

    `--lib` covers two roles at once. It is where the summary comes from when
    no `-summ` was given, and it is where the concrete function's helpers come
    from (tests/libc/synth/*/strdup passes both). The sampler must link the
    second and must not link the first: a summary is written against the
    symbolic API, and the harness deliberately implements none of it, so
    linking it fails on push_pc, _ITE_VAR_ and the rest.
    '''
    from summboundverify.validation_gen.utils import parse_c_file
    from summboundverify.validation_gen.function_parser.visitors import (
        FunctionVisitor,
    )

    if not args.summname:
        return list(args.lib or [])

    keep = []
    for lib in (args.lib or []):
        path = Path(lib)
        try:
            defined = FunctionVisitor(parse_c_file(path), path).functions()
        except Exception:
            # Unparseable is not the same as "is the summary". Keeping it is
            # the recoverable mistake; dropping a helper is a link error.
            keep.append(lib)
            continue

        if args.summname in defined:
            logger.debug("Not linking %s into the sampler: it is the summary",
                         path.name)
            continue

        keep.append(lib)

    return keep




def run_fuzz(
    summary_test: Path | None,
    concrete_test: Path,
    constraints: dict,
    args: Namespace,
) -> Path | None:
    '''Put the two halves together: a formula per summary path, and samples.

    `constraints` arrives already filled when symbolic execution ran in this
    same invocation; otherwise the summary is executed here, on its own.
    '''
    from summboundverify.validation_tool import sampling

    arch = args.compile or 'x86'

    if summary_test is not None:
        constraints = sampling.summary_formulas(
            summary_test, libs=args.lib, arch=arch,
            timeout=args.timeout, results_dir=args.results,
        )

    if not args.run:
        return None

    try:
        results, _ = sampling.validate_by_sampling(
            concrete_test, constraints,
            libs=sampler_libs(args), arch=arch, execs=args.execs,
            timeout=args.timeout, results_dir=args.results,
        )
    except ValueError as e:
        # A width disagreement is systematic, not a property of one sample:
        # the two halves were built for different word sizes and nothing they
        # produce is comparable. Say so once, rather than per sample.
        raise RunError(str(e))

    sampling.log_report(results)

    out = Path(args.results) / f'{concrete_test.stem}_check.json'
    sampling.write_report(results, out)
    logger.info("Sample check written to %s", out)

    return out


def run_angr(binary: Path, args: Namespace) -> tuple[Path, dict]:

    from summboundverify.validation_tool import angrEngine

    engine = angrEngine(
        binary,
        timeout=args.timeout,
        results_dir=args.results,
        stats_dir=args.stats,
        convert_ascii=args.ascii,
    )

    engine.run()

    # Written by the print_counterexamples hook, one entry per test.
    results = Path(args.results) / f'{binary.name}_result.json'

    return results, engine.constraints


def run_se(test: Path, args: Namespace) -> tuple[Path | None, dict]:

    if not args.compile:
        return None, {}

    # angr loads a binary, not a source file.
    binary = compile_validation_test(args.compile, test, args.lib)

    if not args.run:
        return None, {}

    return run_angr(binary, args)


def fuzz_outputfiles(args: Namespace) -> tuple[Path, Path]:
    """The two halves of a fuzzing run: the symbolic summary and the sampler.

    Both are always suffixed, in a `fuzz` run as much as a `both` run. Neither
    is *the* test -- one is a formula generator and the other draws the
    samples checked against it -- so naming one of them after the requested
    output would suggest a primacy it does not have.
    """
    out = Path(args.o)
    return (
        out.with_name(f'{out.stem}-summary{out.suffix}'),
        out.with_name(f'{out.stem}-concrete{out.suffix}'),
    )


def load_results(path: Path | None) -> dict:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def test_id(key: str) -> str:
    '''The bare test name, so both engines' results line up.

    Symbolic execution keys its results by binary (`<name>.test_1`); the
    sample check keys them by test alone (`test_1`), because it is written
    from a report that already belongs to one target. Reducing both to the
    last component is what lets them be shown side by side.
    '''
    _, _, test = key.rpartition('.')
    return test or key


def se_verdict(entry: dict) -> tuple[str, str]:
    result = entry.get('result', 'unknown')
    color = Colors.green if result == 'exact' else Colors.yellow
    return result, color


def fuzz_verdict(entry: dict) -> tuple[str, str]:
    '''One line for what sampling established about a test.

    Reads the sample check, not the raw sample dump: the counts are what a
    reader needs, since "passed" over three samples and "passed" over thirty
    are different claims.
    '''
    verdict = entry.get('verdict', 'unknown')
    checked = entry.get('checked') or 0

    detail = f' ({checked} sample(s))' if checked else ''

    if verdict == 'mismatched':
        findings = entry.get('findings') or []
        bindings = findings[0].get('bindings') if findings else None
        if bindings:
            detail += ' [{}]'.format(
                ', '.join(f'{k}={v}' for k, v in bindings.items())
            )
        color = Colors.red

    elif verdict == 'starved':
        color = Colors.yellow

    else:
        color = Colors.green

    return f'{verdict}{detail}', color


def print_summary(se_results: Path | None, fuzz_results: Path | None):
    '''Side-by-side verdicts, so a `both` run ends with one thing to read.'''
    se = load_results(se_results)
    fuzz = load_results(fuzz_results)

    if not se and not fuzz:
        return

    rows: dict[str, dict] = {}

    for key, entry in se.items():
        rows.setdefault(test_id(key), {})['se'] = se_verdict(entry)

    # The check report is already one entry per test, not nested under a
    # per-engine key the way the raw sample dump is.
    for key, entry in fuzz.items():
        rows.setdefault(test_id(key), {})['fuzz'] = fuzz_verdict(entry)

    unknown = ('not run', Colors.white)
    width = max(len(name) for name in rows)

    section('Summary')

    for name, verdicts in rows.items():
        se_text, se_color = verdicts.get('se', unknown)
        fz_text, fz_color = verdicts.get('fuzz', unknown)

        print(
            f"  {name:<{width}}"
            f"  symbolic: {se_color}{se_text:<12}{Colors.reset}"
            f"  fuzz: {fz_color}{fz_text}{Colors.reset}",
            file=sys.stderr,
        )

        # The engines only contradict each other in one direction: sampling
        # found a concrete input the symbolic result says cannot exist. The
        # opposite (SE reports a bug, sampling does not) is expected -- a
        # bounded set of samples simply may not have reached it.
        if se_text == 'exact' and fz_text.startswith('mismatched'):
            print(
                f"  {Colors.red}the engines disagree: one of them is wrong"
                f"{Colors.reset}",
                file=sys.stderr,
            )

        if fz_text.startswith('starved'):
            print(
                f"  {Colors.yellow}sampling checked nothing; its verdict "
                f"carries no weight{Colors.reset}",
                file=sys.stderr,
            )

    print(file=sys.stderr, flush=True)


def plan_engines(args: Namespace) -> list[str]:
    '''The engines to actually run, after refusing the ones that cannot work.

    Symbolic execution is dropped when the concrete function is one angr
    cannot finish, *even when it was asked for explicitly*: the alternative
    is a run that burns the whole timeout and reports nothing.

    When that leaves nothing, fuzzing stands in. Refusing the only requested
    engine and then validating nothing at all would be strictly less useful
    than running the engine that handles precisely these targets, but it is
    a substitution, so it is announced rather than slipped in quietly.
    '''
    from summboundverify.validation_tool.se_support import se_obstacles_in

    engines = ['se', 'fuzz'] if args.engine == 'both' else [args.engine]

    if 'se' not in engines or not args.func:
        return engines

    obstacles = se_obstacles_in(args.func, args.funcname)

    if not obstacles:
        return engines

    name = args.funcname or Path(args.func).stem
    engines = [engine for engine in engines if engine != 'se']

    logger.warning(
        "Skipping symbolic execution: %s %s.\n"
        "angr cannot finish this target, so it would run until the timeout "
        "and report nothing.",
        name, "; ".join(obstacles),
    )

    if engines:
        return engines

    from summboundverify.validation_tool.fuzz_engine import afl_available

    if not afl_available():
        raise RunError(
            f"Symbolic execution was skipped ({obstacles[0]}) and fuzzing, "
            f"the engine that handles such targets, needs AFL++ "
            f"(Debian/Ubuntu: apt install afl++). Nothing was validated."
        )

    logger.warning("Falling back to fuzzing, the only engine left for %s", name)
    return ['fuzz']


def main():
    try:
        # Parse all input (cli and config file)
        args = parse_input_args()

        setup_logging(args.debug)

        # Run a given binary and exit
        if args.run and args.binary:
            run_angr(args.binary, args)
            return 0

        engines = plan_engines(args)
        results: dict[str, Path | None] = {}

        # Formulas carried from symbolic execution to fuzzing within one run.
        se_constraints: dict = {}

        for engine in engines:

            # A single engine's output is unambiguous on its own.
            if len(engines) > 1:
                section(ENGINE_TITLES[engine])

            if engine == 'se':
                test = run_validation_gen(args, engine='se')
                results['se'], se_constraints = run_se(test, args)

            else:
                summary_test, concrete_test = fuzz_outputfiles(args)

                # A `both` run has already executed the summary, and the
                # formulas it produced are the same ones a summary-only test
                # would build. Doing it twice buys nothing.
                if se_constraints:
                    logger.info(
                        "Reusing the summary's path conditions from the "
                        "symbolic run instead of executing it again"
                    )
                    summary_test = None
                else:
                    run_validation_gen(
                        args, engine='summary', outputfile=summary_test
                    )

                run_validation_gen(
                    args, engine='concrete', outputfile=concrete_test
                )

                if args.run:
                    results['fuzz'] = run_fuzz(
                        summary_test, concrete_test, se_constraints, args
                    )

        if len(engines) > 1 and args.run:
            print_summary(results.get('se'), results.get('fuzz'))

    except Exception as e:
        print(traceback.format_exc())
        print(e)
        return 1

    return 0
