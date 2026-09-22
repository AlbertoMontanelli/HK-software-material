#!/bin/bash
# Run fiTQun inside the hk_prod_0.2.13_dev sandbox.
#
# Usage:
#   ./src/run_scripts/run_fiTQun.sh <input_file> <num_events> <output_file>
#
# The input WCSim ROOT file is searched in:
#   data/WCSim_data/
#
# The output fiTQun ROOT file is written to:
#   data/fiTQun_data/
#
# The fiTQun parameter file is fixed to:
#   data/fiTQun_config/test_fitqun.parameters.dat
#
# The tuning files are fixed to:
#   data/fiTQun_config/fitqun-tuning-files-0.1.0/const/

set -euo pipefail

# Resolve the containers/ directory independently of the current working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SANDBOX="${BASE_DIR}/hk_prod_0.2.13_dev"

WCSIM_DATA_DIR="${BASE_DIR}/data/WCSim_data"
FITQUN_DATA_DIR="${BASE_DIR}/data/fiTQun_data"
FITQUN_CONFIG_DIR="${BASE_DIR}/data/fiTQun_config"

PARAM_FILE="${FITQUN_CONFIG_DIR}/test_fitqun.parameters.dat"
TUNING_DIR="${FITQUN_CONFIG_DIR}/fitqun-tuning-files-0.1.0/const"

INPUT_FILE="$1"
NUM_EVENTS="$2"
OUTPUT_FILE="$3"

mkdir -p "${FITQUN_DATA_DIR}"

apptainer exec \
    --bind "${WCSIM_DATA_DIR}":/WCSim_data:ro \
    --bind "${FITQUN_DATA_DIR}":/fiTQun_data \
    --bind "${FITQUN_CONFIG_DIR}":/fiTQun_config:ro \
    "${SANDBOX}" \
    bash -c '
        set -e

        source /opt/HyperK/root_build/bin/thisroot.sh
        source /opt/HyperK/WCSim-install/bin/this_wcsim.sh

        export FITQUN_ROOT=/opt/HyperK/fiTQun
        export FITQUN_CONST_DIR=/fiTQun_config/fitqun-tuning-files-0.1.0/const

        cd "${FITQUN_ROOT}"

        exec ./runfiTQunWC \
            -n "$1" \
            -p /fiTQun_config/test_fitqun.parameters.dat \
            -r "/fiTQun_data/$3" \
            "/WCSim_data/$2"
    ' _ "${NUM_EVENTS}" "${INPUT_FILE}" "${OUTPUT_FILE}"