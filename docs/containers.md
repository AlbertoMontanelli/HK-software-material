# Container images

The HK software environment may rely on Singularity/Apptainer images. These images are large binary files and should not be stored in this Git repository.

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

## Why images are not tracked by Git

Git is not a good place for large binary artifacts because:

- every clone becomes heavy;
- binary diffs are inefficient;
- GitHub has file-size limits;
- the images are tied to a specific computing environment;
- access may be restricted to INFN users.

The repository should document the existence, path, and purpose of the images, while the images themselves remain on the INFN machine.

## Using an image on marduk

After connecting to `marduk`:

```bash
cd /home/cc/HyperKamiokande
apptainer shell fiTQun_WCSim.sif
```

or, depending on the local installation:

```bash
singularity shell fiTQun_WCSim.sif
```

Then inspect or source the associated environment file if needed:

```bash
ls -lh
cat fiTQun_WCSim_env.sh
source fiTQun_WCSim_env.sh
```

## Metadata file

The file `containers/images.yml` is meant to be a compact, structured reference. It can be read by humans and, if needed later, parsed by scripts.

Example entry:

```yaml
- name: fiTQun_WCSim
  filename: fiTQun_WCSim.sif
  remote_user: cc
  host: marduk
  path: /home/cc/HyperKamiokande/fiTQun_WCSim.sif
```

If an image is moved, renamed, rebuilt, or replaced, update `containers/images.yml` and this page.
