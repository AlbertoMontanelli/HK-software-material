#!/bin/bash
# Shell script to run WCSim detector display inside the container.
# Usage: run inside the '/home/cc/HyperKamiokande/containers' directory:
#     './src/run_scripts/WCSim_detector_display.sh <input_wcsim_root>
#     <output_pdf> [event_index] [trigger_index]'
# The input WCSim root file is searched inside 'data/WCSim_data/' directory.
# The output plots are saved in 'plots/' directory.

INPUT_FILE="$1"
OUTPUT_PDF="$2"
shift 2

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/src/scripts":/scripts \
    --bind "$(pwd)/plots":/plots \
    "$(pwd)/WCSimRootPyROOT.sif" \
    python /scripts/WCSim_detector_display.py \
        "/WCSim_data/${INPUT_FILE}" \
        "/plots/${OUTPUT_PDF}" \
        "$@"