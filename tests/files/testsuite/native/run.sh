#!/usr/bin/env bash
# Runs one natively built test in a fresh, empty directory, so the files it
# creates never meet those of another test. The directory is removed after.
#
#   native/run.sh bins/native/cncr-fname-1/open/test_01.test

test=$(realpath "$1")
dir=$(mktemp -d)
trap 'rm -rf "$dir"' EXIT

cd "$dir" && "$test"
