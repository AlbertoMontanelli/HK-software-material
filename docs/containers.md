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
cc@marduk:/home/cc/HyperKamiokande/
```

The currently referenced images are:

| Image | Remote path | Purpose |
|---|---|---|
| `fiTQun_latest.sif` | `/home/cc/HyperKamiokande/fiTQun_latest.sif` | fiTQun environment |
| `fiTQun_WCSim.sif` | `/home/cc/HyperKamiokande/fiTQun_WCSim.sif` | fiTQun + WCSim environment |

## Metadata file

The file `containers/images.yml` is meant to be a compact, structured reference. It can be read and, if needed later, parsed by scripts.

If an image is moved, renamed, rebuilt, or replaced, update `containers/images.yml` and this page.

## Container images building

This section summarizes how the available Apptainer images are obtained.

## Accessing the container directory

The container images are stored on `marduk`:

```text
/home/cc/HyperKamiokande/
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
cd /home/cc/HyperKamiokande
ls -lh
```

Expected relevant files include:

```text
fiTQun_latest.sif
fiTQun_WCSim.sif
fiTQun_WCSim.def
fiTQun_WCSim_env.sh
```

## Building the images

### Pulling the fiTQun image

The base fiTQun image can be pulled from the Hyper-K GitLab container registry. Access requires valid Hyper-K GitLab credentials and a personal access token with read access to the container registry. First, create an HTTP token with registry read permission from your Hyper-K GitLab profile.

Login to the registry with:

```bash
apptainer registry login --username <USERNAME> docker://registry.git.hyperk.org
```

Then pull the latest fiTQun image:

```bash
apptainer pull fiTQun_latest.sif docker://registry.git.hyperk.org/hyperk/recon/fitqun:latest
```

This image contains fiTQun and its dependencies; the full WCSim setup needed for all workflows is not present.

### Building the fiTQun + WCSim image

The combined image is built from the definition file:

```text
fiTQun_WCSim.def
```

Build it with:

```bash
apptainer build fiTQun_WCSim.sif fiTQun_WCSim.def
```

This produces:

```text
fiTQun_WCSim.sif
```

which is intended to provide a single environment containing both fiTQun and WCSim-related components.

## Environment setup

The repository contains an environment helper script:

```text
fiTQun_WCSim_env.sh
```

Before running software inside or together with the container, inspect and source it if needed:

```bash
source fiTQun_WCSim_env.sh
```

The purpose of this script is to define useful paths and environment variables for the local setup.

## Compatibility note: WCSimRoot versions

The combined `fiTQun_WCSim.sif` image currently contains two WCSimRoot installations:

- `WCSimRoot 1.12.29`, inherited from the original `fiTQun_latest.sif` image and used by the pre-existing fiTQun build;
- `WCSimRoot 1.12.30`, produced when the full WCSim installation is built inside the combined image.

This means that `runfiTQun` and `WCSim` may be linked against different WCSimRoot versions.
This may cause compatibility problems: if a WCSim ROOT file produced by the full WCSim installation cannot be read correctly by runfiTQun the most likely issue is this mismatch between these two WCSimRoot versions.

For a cleaner production setup, fiTQun should eventually be rebuilt against the same WCSimRoot installation used by the full WCSim build.
