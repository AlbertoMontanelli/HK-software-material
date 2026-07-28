#!/bin/bash

set -euo pipefail

INPUT_FILE="$1"
EVENT_LIST="$2"

INPUT_BASENAME="${INPUT_FILE%.root}"
OUTPUT_FILE="${INPUT_BASENAME}_fiTQun.root"

BASE_DIR="$(pwd)"

echo "Input file:  ${INPUT_FILE}"
echo "Event list:  ${EVENT_LIST}"
echo "Output file: ${OUTPUT_FILE}"

apptainer run \
    --bind "${BASE_DIR}/data/WCSim_data":/WCSim_data \
    --bind "${BASE_DIR}/data/fiTQun_data":/fiTQun_data \
    "${BASE_DIR}/fiTQun.sif" \
    -p /usr/local/hk/fiTQun/ParameterOverrideFiles/HyperK.parameters.dat \
    -l "/WCSim_data/${EVENT_LIST}" \
    -r "/fiTQun_data/${OUTPUT_FILE}" \
    "/WCSim_data/${INPUT_FILE}"