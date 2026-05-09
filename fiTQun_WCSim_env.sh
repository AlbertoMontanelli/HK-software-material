#!/bin/bash

# ==============================
# fiTQun + WCSim container environment
# ==============================

# Stop only if an unset variable is used inside this setup script.
# Do not use "set -e" here, because this script is meant to execute arbitrary commands.
set -u

# ------------------------------
# Main package locations
# ------------------------------

export HK_ROOT=/usr/local/hk

export FITQUN_SRC=${HK_ROOT}/fiTQun
export FITQUN_INSTALL=${HK_ROOT}/fiTQun/install-Linux_x86_64-gcc_8-python_3.12.1

export ROOT_INSTALL=${HK_ROOT}/ROOT/install-Linux_x86_64-gcc_8-python_3.12.1
export WCSIMROOT_INSTALL=${HK_ROOT}/WCSimRoot/install-Linux_x86_64-gcc_8-python_3.12.1
export TOOLFRAMEWORKCORE_INSTALL=${HK_ROOT}/ToolFrameworkCore/install-Linux_x86_64-gcc_8-python_3.12.1

export WCSIMFULL_INSTALL=${HK_ROOT}/WCSimFull/install
export GEANT4_INSTALL=${HK_ROOT}/Geant4/install-10.3.3

# ------------------------------
# fiTQun variables
# ------------------------------

# fiTQun uses this to find parameter/configuration files.
export FITQUN_ROOT=${FITQUN_SRC}

# ------------------------------
# Geant4 data files
# ------------------------------

export G4DATA=${GEANT4_INSTALL}/share/Geant4-10.3.3/data

export G4LEDATA=${G4DATA}/G4EMLOW6.50
export G4LEVELGAMMADATA=${G4DATA}/PhotonEvaporation4.3.2
export G4NEUTRONHPDATA=${G4DATA}/G4NDL4.5
export G4RADIOACTIVEDATA=${G4DATA}/RadioactiveDecay5.1.1
export G4REALSURFACEDATA=${G4DATA}/RealSurface1.0
export G4SAIDXSDATA=${G4DATA}/G4SAIDDATA1.1
export G4ENSDFSTATEDATA=${G4DATA}/G4ENSDFSTATE2.1

# ------------------------------
# Executables
# ------------------------------

export PATH=${WCSIMFULL_INSTALL}/bin:${GEANT4_INSTALL}/bin:${FITQUN_INSTALL}/bin:${ROOT_INSTALL}/bin:${PATH:-}

# ------------------------------
# Dynamic libraries
# ------------------------------

export LD_LIBRARY_PATH=${WCSIMFULL_INSTALL}/lib:${WCSIMFULL_INSTALL}/lib64:${GEANT4_INSTALL}/lib64:${GEANT4_INSTALL}/lib:${FITQUN_INSTALL}/lib:${WCSIMROOT_INSTALL}/lib:${TOOLFRAMEWORKCORE_INSTALL}/lib:${ROOT_INSTALL}/lib:/.singularity.d/libs:${LD_LIBRARY_PATH:-}

# ------------------------------
# ROOT include path
# ------------------------------

export ROOT_INCLUDE_PATH=${WCSIMROOT_INSTALL}/include/WCSimRoot:${WCSIMROOT_INSTALL}/include:${ROOT_INCLUDE_PATH:-}

# ------------------------------
# Run the command passed to this script
# ------------------------------

exec "$@"
