#!/bin/bash

INPUT_FILE="$1"
shift

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/src/scripts":/scripts \
    --bind "$(pwd)/plots":/plots \
    "$(pwd)/WCSimRootPyROOT.sif" \
    python /scripts/WCSim_positron_analysis.py \
    --summary_root_file "/WCSim_data/${INPUT_FILE}" \
    "$@"