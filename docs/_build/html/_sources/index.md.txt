# HK Software Material

This documentation collects practical notes for accessing and using the Hyper-Kamiokande software material referenced by this repository.

The repository is intentionally lightweight: large artifacts such as Singularity/Apptainer images are documented, but not stored in Git.

```{toctree}
:maxdepth: 2
:caption: Contents

access
containers
usage
repository_structure
```

## Main idea

The repository should contain:

- documentation;
- container definition files, when they are small enough;
- environment setup snippets;
- references to external software resources;
- notes useful for reproducibility.

The repository should not contain:

- `.sif` images;
- large ROOT files;
- generated simulation output;
- local logs or temporary files.

## Remote container location

The currently referenced container images are stored on:

```text
cc@marduk:/home/cc/HyperKamiokande/
```

Access may require the INFN network, INFN VPN, or the `galilinux` jump server.
