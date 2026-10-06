#!/usr/bin/env bash
# Runs one test on KLEE, in the image "make klee-image" builds, with the
# suite's own KLEE runner. Prints KLEE's output, and exits 0 if the test
# passed, 1 if not, as the suite's scripts/verdict.sh judges it.
#
#   klee/run.sh open/test_01
#
# The suite is mounted read-only and copied, so KLEE's output never lands in it.

image=${KLEE_IMAGE:-klee-testsuite-fork}
suites=$(cd "$(dirname "$0")/../klee-testsuite" && pwd)

suite=${1%%/*}
n=${1##*/test_}

if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "klee/run.sh: no image $image; build it with: make klee-image" >&2
    exit 1
fi

docker run --rm -v "$suites:/suite:ro" "$image" bash -c "
    cp -r /suite /tmp/suite && cd /tmp/suite &&
    make --no-print-directory -s -C individual-tests/$suite run_$n &&
    sh scripts/verdict.sh individual-tests/$suite/klee-out-test_$n.log"
