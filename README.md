# HK Software Material

This repository collects notes, references, configuration snippets, and documentation related to the Hyper-Kamiokande software environment used for simulation and reconstruction studies.

The repository is intended to document **how to access and use existing HK software material**, rather than to store large binary artifacts directly.

## Repository contents

```text
HK-software-material/
├── README.md
├── containers/
│   └── images.yml
├── docs/
│   ├── conf.py
│   ├── index.md
│   ├── access.md
│   ├── containers.md
│   ├── usage.md
│   ├── repository_structure.md
│   └── requirements.txt
└── .github/
    └── workflows/
        └── docs.yml
```

The main documentation lives in `docs/` and can be rendered locally with Sphinx or deployed online with GitHub Pages.

## Large files policy

Large files such as Singularity/Apptainer images (`*.sif`) are **not stored in this repository**.

The current container images are stored on the INFN machine `marduk`:

```text
/home/cc/HyperKamiokande/
```

Access depends on the user's INFN account and network situation. See:

- [`docs/access.md`](docs/access.md)
- [`docs/containers.md`](docs/containers.md)
- [`containers/images.yml`](containers/images.yml)

## Documentation

The documentation is written mostly in Markdown and built with Sphinx using `myst-parser`.

To build it locally:

```bash
python -m pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```

Then open:

```text
docs/_build/html/index.html
```

## GitHub Pages

A GitHub Actions workflow is provided in:

```text
.github/workflows/docs.yml
```

It builds the Sphinx documentation and deploys it to GitHub Pages when changes are pushed to `main`.

In the GitHub repository settings, enable:

```text
Settings → Pages → Build and deployment → Source: GitHub Actions
```

## Recommended workflow

1. Put source notes, references, and lightweight configuration files in Git.
2. Keep large binaries such as `.sif`, `.root`, `.zbs`, and output logs outside Git.
3. Document external resources in `containers/images.yml` and in the Markdown documentation.
4. Keep access instructions generic, because each INFN user has a personal username and password.
