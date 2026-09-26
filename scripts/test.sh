#!/bin/sh
set -eu
SCD_TEST_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export PYTHONPATH="$SCD_TEST_ROOT/core/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$SCD_TEST_ROOT"
python3 -m unittest discover -s tests
python3 evals/run_eval.py examples/ledgerly
./scd validate examples/ledgerly

