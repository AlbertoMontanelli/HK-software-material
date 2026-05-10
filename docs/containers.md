# Container images

The HK software environment may rely on Apptainer images. These images are large binary files and should not be stored in this Git repository.

Instead, this repository stores references to the remote images in:

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
