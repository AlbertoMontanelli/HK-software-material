#!/bin/bash
# Shell script to filter WCSim events based on the number of triggers.
# Usage: run inside the '/home/cc/HyperKamiokande/containers' directory:
#     './src/run_scripts/WCSim_filter.sh <input_wcsim_root>
#     <output_file>'
# The input/output WCSim root file is searched inside
# 'data/WCSim_data/' directory.

INPUT_FILE="$1"

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/src/scripts":/scripts \
    "$(pwd)/WCSimRootPyROOT.sif" \
    python /scripts/WCSim_filter.py \
        "/WCSim_data/${INPUT_FILE}"