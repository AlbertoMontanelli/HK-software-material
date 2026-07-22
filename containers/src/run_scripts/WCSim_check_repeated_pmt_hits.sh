#!/bin/bash

set -euo pipefail

INPUT_FILE="$1"
shift

CMD=(
    apptainer exec
    --bind "$(pwd)/data/WCSim_data:/WCSim_data"
    --bind "$(pwd)/src/scripts:/scripts"
    "$(pwd)/WCSimRootPyROOT.sif"
    python
    /scripts/WCSim_check_repeated_pmt_hits.py
    --input_file "/WCSim_data/${INPUT_FILE}"
    "$@"
)

"${CMD[@]}"