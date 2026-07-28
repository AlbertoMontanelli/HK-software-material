#!/bin/bash

set -euo pipefail

INPUT_FILE=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --input_file)
            INPUT_FILE="$2"
            shift 2
            ;;

        --output_file)
            OUTPUT_FILE="$2"
            shift 2
            ;;

        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;

        *)
            if [[ -z "$INPUT_FILE" ]]; then
                INPUT_FILE="$1"
                shift
            else
                echo "Unexpected positional argument: $1" >&2
                exit 1
            fi
            ;;
    esac
done

if [[ -z "$INPUT_FILE" ]]; then
    echo "Usage:" >&2
    echo "  $0 input.root [--output_file output.root]" >&2
    echo "  $0 --input_file input.root [--output_file output.root]" >&2
    exit 1
fi

CMD=(
    apptainer exec
    --bind "$(pwd)/data/WCSim_data:/WCSim_data"
    --bind "$(pwd)/src/scripts:/scripts"
    "$(pwd)/WCSimRootPyROOT.sif"
    python
    /scripts/WCSim_muplus_michel_summary.py
    --input_file "/WCSim_data/${INPUT_FILE}"
)

if [[ -n "$OUTPUT_FILE" ]]; then
    CMD+=(
        --output_file "/WCSim_data/${OUTPUT_FILE}"
    )
fi

"${CMD[@]}"