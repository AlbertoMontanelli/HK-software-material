#!/bin/bash

INPUT_FILE="$1"
shift

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/src/scripts":/scripts \
    "$(pwd)/WCSimRootPyROOT.sif" \
    python /scripts/WCSim_trigger_debug.py \
    "/WCSim_data/${INPUT_FILE}" \
    "$@"