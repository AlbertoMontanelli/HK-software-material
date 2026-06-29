#!/bin/bash

apptainer exec \
    --bind "$(pwd)/data/WCSim_data":/WCSim_data \
    --bind "$(pwd)/data/fiTQun_data":/fiTQun_data \
    "$(pwd)/WCSimRootPyROOT.sif" \
    root -l

