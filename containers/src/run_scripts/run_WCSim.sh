#!/bin/bash
# Run WCSim inside the hk_prod_0.2.13_dev sandbox.
#
# Usage:
#   ./src/run_scripts/run_WCSim.sh <macro_file>
#
# The macro is searched in:
#   src/WCSim_macros/
#
# The detector tuning file is fixed to:
#   HKFD_tuning_parameters_cwcs1.1.mac
#
# WCSim output files should be written by the macro to:
#   /output_data/<output_file>.root
#
# which corresponds to:
#   data/WCSim_data/

set -euo pipefail

# Resolve the containers/ directory independently of the current working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SANDBOX="${BASE_DIR}/hk_prod_0.2.13_dev"

MACRO_DIR="${BASE_DIR}/src/WCSim_macros"
WCSIM_DATA_DIR="${BASE_DIR}/data/WCSim_data"

MACRO_FILE="$1"
TUNING_FILE="HKFD_tuning_parameters_cwcs1.1.mac"


mkdir -p "${WCSIM_DATA_DIR}"

apptainer exec \
    --bind "${WCSIM_DATA_DIR}":/output_data \
    --bind "${MACRO_DIR}":/WCSim_macros:ro \
    "${SANDBOX}" \
    bash -c '
        set -e

        source /opt/HyperK/Geant4/install/bin/geant4.sh
        source /opt/HyperK/root_build/bin/thisroot.sh
        source /opt/HyperK/WCSim-install/bin/this_wcsim.sh

        # Needed because the cwcs1.1 tuning file uses the relative path
        # data/CathodeParameters.txt.
        cd /opt/HyperK/WCSim-install

        exec WCSim \
            "/WCSim_macros/$1" \
            "/WCSim_macros/$2"
    ' _ "${MACRO_FILE}" "${TUNING_FILE}"