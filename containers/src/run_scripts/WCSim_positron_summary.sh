#!/bin/bash

set -euo pipefail

INPUT_FILE="$1"
shift

ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output_file)
            ARGS+=(--output_file "/WCSim_data/$2")
            shift 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/src/scripts":/scripts \
    --bind "$(pwd)/plots":/plots \
    "$(pwd)/WCSimRootPyROOT.sif" \
    python /scripts/WCSim_positron_summary.py \
    --input_file "/WCSim_data/${INPUT_FILE}" \
    "${ARGS[@]}"