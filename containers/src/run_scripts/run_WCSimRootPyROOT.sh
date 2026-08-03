#!/bin/bash
# Run WCSimRootPyROOT image in interactive mode.

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/data/fiTQun_data":/fiTQun_data \
    --bind "$(pwd)/src/scripts":/scripts \
    --bind "$(pwd)/plots":/plots \
    "$(pwd)/WCSimRootPyROOT.sif" \
    bash