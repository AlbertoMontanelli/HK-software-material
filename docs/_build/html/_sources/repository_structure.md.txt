# Repository structure

The repository separates lightweight documentation from large external artifacts.

## Recommended structure

```text
HK-software-material/
├── README.md
├── LICENSE
├── HK_Software_Guide.tex
├── HK_software_guide.pdf
├── fiTQun_WCSim.def
├── fiTQun_WCSim_env.sh
├── containers/
│   └── images.yml
├── docs/
│   ├── conf.py
│   ├── index.md
│   ├── access.md
│   ├── containers.md
│   ├── usage.md
│   ├── repository_structure.md
│   ├── requirements.txt
│   ├── _static/
│   └── _templates/
└── .github/
    └── workflows/
        └── docs.yml
```

## What belongs in Git

Good candidates for Git:

- Markdown documentation;
- LaTeX source files;
- small setup scripts;
- container definition files such as `.def`;
- small environment setup files;
- YAML metadata files;
- GitHub workflow files.

## What does not belong in Git

Avoid committing:

- `.sif` container images;
- large ROOT files;
- generated simulation samples;
- temporary output;
- logs;
- personal credentials;
- private keys;
- personal machine-specific configuration.

## Why this structure is useful

The repository remains easy to clone and read, while still documenting the actual software environment used on the INFN machines.

This is especially useful when the environment is not fully reproducible from GitHub alone, because some resources are stored on restricted servers.
