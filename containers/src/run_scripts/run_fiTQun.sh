#!/bin/bash
# Script shell to run fiTQun inside the container.
# Usage: run inside the '/home/cc/HyperKamiokande/containers' directory:
#     './run_scripts/run_fitqun.sh <input_wcsim_root> <output_fitqun_root>'
# The input WCSim root file is searched inside 'data/WCSim_data/' directory.
# The output fiTQun root file is saved in 'data/fiTQun_data/' directory.


INPUT_FILE="$1"
OUTPUT_FILE="$2"
NUM_EVENTS="${3:-1}"

apptainer run \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/data/fiTQun_data":/fiTQun_data \
    "$(pwd)/fiTQun.sif" \
    -n "${NUM_EVENTS}" \
    -p /usr/local/hk/fiTQun/ParameterOverrideFiles/HyperK.parameters.dat \
    -r /fiTQun_data/${OUTPUT_FILE} \
    /WCSim_data/${INPUT_FILE}