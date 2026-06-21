#!/bin/bash
# Shell script to run WCSim trigger counting inside the container.
# Usage: run inside the '/home/cc/HyperKamiokande/containers' directory:
#     './src/run_scripts/WCSim_analyze_event.sh <input_wcsim_root>'
# The input WCSim root file is searched inside 'data/WCSim_data/' directory.

INPUT_FILE="$1"
shift

CMD=(
    apptainer exec
    --bind "$(pwd)/data/WCSim_data":/WCSim_data
    --bind "$(pwd)/src/scripts":/scripts
    "$(pwd)/WCSimRootPyROOT.sif"
    python /scripts/WCSim_analyze_event.py
    "/WCSim_data/${INPUT_FILE}"
    "$@"
)

"${CMD[@]}"