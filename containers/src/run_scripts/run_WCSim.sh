#!/bin/bash
# Shell script to run WCSim inside the container.
# Usage: run inside the '/home/cc/HyperKamiokande/containers' directory:
#     './run_scripts/run_wcsim.sh <macro_file>'
# The macro is searched inside 'src/WCSim_macros/' directory.
# The output files are saved in 'data/WCSim_data/' directory.
# Change the name of the WCSim output file in the macro.

MACRO_FILE="$1"

apptainer run \
    --bind "$(pwd)/data/WCSim_data":/output_data \
    --bind "$(pwd)/src/WCSim_macros":/WCSim_macros \
    "$(pwd)/WCSim.sif" \
    "/WCSim_macros/${MACRO_FILE}" \
    "/opt/WCSim/install/macros/tuning_parameters_hkfd.mac"