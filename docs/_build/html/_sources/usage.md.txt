# Usage guide

This page gives a practical reading order for the repository and explains how to use the documented material.

## Reading order

Start from:

1. `README.md` for the general idea of the repository;
2. `docs/access.md` to understand how to reach the INFN machines;
3. `docs/containers.md` to understand where the `.sif` images are stored;
4. `containers/images.yml` for the structured list of available images;
5. existing setup files such as `fiTQun_WCSim_env.sh`, if present in the repository.

## Typical workflow

From a local machine:

```bash
ssh -J <INFN_USERNAME>@galilinux.pi.infn.it cc@marduk
```

Then on `marduk`:

```bash
cd /home/cc/HyperKamiokande
ls -lh
```

To open a container:

```bash
apptainer shell fiTQun_WCSim.sif
```


