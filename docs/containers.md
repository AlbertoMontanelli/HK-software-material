# Container images

The HK software environment may rely on Apptainer images. These images are large binary files and should not be stored in this Git repository.
The repository only documents where they are located, how they can be accessed, and how they can be rebuilt if needed.

This repository stores references to the remote images in:

```text
containers/images.yml
```

## Remote location

The current remote location is:

```text
cc@marduk:/home/cc/HyperKamiokande/containers/
```

The currently referenced images are:

| Image | Remote path | Purpose |
|---|---|---|
| `fiTQun.sif` | `/home/cc/HyperKamiokande/containers/fiTQun.sif` | fiTQun environment |
| `WCSim.sif` | `/home/cc/HyperKamiokande/containers/WCSim.sif` | WCSim environment |

## Metadata file

The file `containers/images.yml` is meant to be a compact, structured reference. It can be read and, if needed later, parsed by scripts.

If an image is moved, renamed, rebuilt, or replaced, update `containers/images.yml` and this page.

## Container images building

This section summarizes how the available Apptainer images are obtained.

### Accessing the container directory

The container images are stored on `marduk`:

```text
/home/cc/HyperKamiokande/containers/
```

If you are outside the INFN network, access usually requires the `galilinux` jump server:

```bash
ssh -J <INFN_USERNAME>@galilinux.pi.infn.it cc@marduk
```

where `<INFN_USERNAME>` must be replaced with your personal INFN username.

If you are already connected through the INFN network or VPN, direct access may work:

```bash
ssh cc@marduk
```

Once logged into `marduk`:

```bash
cd /home/cc/HyperKamiokande/containers
```

### Building fiTQun image

The fiTQun image is based on the official Hyper-K GitLab container registry image:

```bash
registry.git.hyperk.org/hyperk/recon/fitqun
```

Since the registry is private, first login with your Hyper-K GitLab credentials or a personal access token with container-registry read access:

```bash
apptainer registry login --username <USERNAME> docker://registry.git.hyperk.org
```

For reproducibility, the Apptainer definition file should use a fixed image digest rather than the moving latest tag. The tested image is built from:

```bash
registry.git.hyperk.org/hyperk/recon/fitqun@sha256:54e4856f12380b67853713f3992bac776292c36a6660fe54503131d9b688d490
```

Build the derived fiTQun image with:

```bash
apptainer build fiTQun.sif fiTQun.def
```

This derived image keeps the official fiTQun installation, adds a runtime setup script, and downloads the Hyper-K tuning constants directly into:

```bash
/usr/local/hk/fiTQun/const
```

The image is meant for fiTQun reconstruction only. WCSim event generation is handled by a separate WCSim image.

### Building WCSim image


The WCSim image is built from the Hyper-K software base image used by the official WCSim CI workflow:

```bash
ghcr.io/hyperk/hk-software:0.0.2
```

This image provides the main external dependencies, including ROOT, Geant4, hk-pilot, and the Hyper-K software environment. The WCSim source code is then cloned and built inside the derived Apptainer image.

For reproducibility, the build uses a fixed WCSim commit rather than the moving develop branch:

```bash
5be124b35a5832bc1d90466169acc581d8b6fbd7
```

Build the WCSim image with:

```bash
apptainer build WCSim.sif WCSim.def
```

The derived image installs WCSim under:

```bash
/opt/WCSim/install
```

and provides a `%runscript` so that `apptainer run` automatically loads the ROOT/Geant4/WCSim environment and forwards the user-provided arguments to the WCSim executable.

The image is meant for WCSim event generation only. fiTQun reconstruction is handled by a separate fiTQun image.


## Basic usage

### Running WCSim

Use `WCSim.sif` to generate a WCSim ROOT file. Bind the directory containing the WCSim macro and bind the output directory to the same container path used inside the macro, for example `/output_data`:

```bash
apptainer run \
  --bind "$(pwd)/WCSim_macros":/macros \
  --bind "$(pwd)/WCSim_output_data":/output_data \
  WCSim.sif \
  /macros/muplus_michel_HK.mac \
  /opt/WCSim/install/macros/tuning_parameters_hkfd.mac
```

The first argument is the user macro. The second argument is the WCSim tuning macro; the default Hyper-K far detector tuning file is already available inside the image.

### Running fiTQun

Use `fiTQun.sif` to reconstruct a WCSim ROOT file. The Hyper-K fiTQun constants are already stored inside the image, so only the directory containing the WCSim input file and the desired fiTQun output file has to be bind-mounted:

```bash
apptainer run \
  --bind "$(pwd)/WCSim_output_data":/data \
  fiTQun.sif \
  -n 1 \
  -p /usr/local/hk/fiTQun/ParameterOverrideFiles/HyperK.parameters.dat \
  -r /data/fiTQun.root \
  /data/WCSim_muplus_michel.root
```

Here `-n` selects the number of events to process, `-p` selects the fiTQun parameter override file, `-r` defines the output ROOT file, and the final argument is the input WCSim ROOT file.

## Compatibility note: WCSimRoot versions

`fiTQun.sif` and `WCSim.sif` images currently contain two WCSimRoot installations:

- `WCSimRoot 1.12.29`, inherited from the original `fiTQun.sif` image and used by the pre-existing fiTQun build;
- `WCSimRoot 1.12.30`, produced when the full WCSim installation is built inside the dedicated WCSim image.

This means that `runfiTQun` and `WCSim` may be linked against different WCSimRoot versions.
This may cause compatibility problems: if a WCSim ROOT file produced by the WCSim image cannot be read correctly by `runfiTQun`, the most likely issue is this mismatch between these two WCSimRoot versions.

## Compatibility note: detector geometry and fiTQun tuning

The current WCSim and fiTQun chain is technically usable, but the detector geometry used during simulation must be consistent with the fiTQun tuning used during reconstruction.

For example, the tested WCSim macro used the realistic Hyper-K geometry:

```text
/WCSim/WCgeom HyperK_HybridmPMT_IDonly_Realistic
```

while the fiTQun command above uses:

```text
/usr/local/hk/fiTQun/ParameterOverrideFiles/HyperK.parameters.dat
```

which sets:

```text
< fiTQun.WCSimConfig = HyperK >
< fiTQun.WCSimPMTType = 20inchBandL >
```

This means that fiTQun runs with the available Hyper-K 20-inch B\&L PMT tuning files, not with a dedicated tuning for the full realistic hybrid/mPMT geometry. Therefore, this setup validates the technical chain:

```text
WCSim simulation -> WCSim ROOT file -> fiTQun reconstruction -> fiTQun ROOT output
```

but it should not be interpreted as a full physics validation of the realistic Hyper-K detector geometry. For physics studies, use a WCSim geometry compatible with the available fiTQun tuning, or provide dedicated fiTQun tuning files and parameter overrides for the chosen WCSim geometry.

