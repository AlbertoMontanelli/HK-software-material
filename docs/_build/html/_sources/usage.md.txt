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

or:

```bash
singularity shell fiTQun_WCSim.sif
```

Which command works depends on the software installed on the server.

## Local paths

Every user may have a different local working directory. For this reason, the documentation avoids assuming a fixed local path such as:

```text
/home/alberto/...
```

Instead, users should adapt commands to their own working area.

## Remote paths

The common remote path is:

```text
/home/cc/HyperKamiokande/
```

This path is the relevant stable reference for the container images.

## Updating the documentation

When adding a new software image or changing an existing one:

1. update `containers/images.yml`;
2. update `docs/containers.md` if the user-facing explanation changes;
3. update `README.md` only if the general structure changes.

Avoid putting long machine-specific instructions directly in `README.md`. The README should remain a concise entry point.

## Building the documentation locally

Install the documentation dependencies:

```bash
python -m pip install -r docs/requirements.txt
```

Build the HTML documentation:

```bash
sphinx-build -b html docs docs/_build/html
```

Open:

```text
docs/_build/html/index.html
```

## Deploying online with GitHub Pages

The workflow in `.github/workflows/docs.yml` builds and deploys the Sphinx documentation to GitHub Pages.

In GitHub, enable:

```text
Settings → Pages → Build and deployment → Source: GitHub Actions
```

Then push to `main`.
