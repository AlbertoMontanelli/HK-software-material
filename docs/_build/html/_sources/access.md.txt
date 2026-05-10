# Access to INFN machines

This page explains how to access the remote machine that stores the HK software container images.

The key point is that access to `galilinux` is personal: every INFN user has their own username and password. For this reason, this repository does not hardcode a specific username.

## Machines involved

| Machine | Role | User |
|---|---|---|
| `galilinux.pi.infn.it` | INFN jump server | personal INFN username |
| `marduk` | machine where the HK material is stored | `cc` |

The relevant remote directory on `marduk` is:

```text
/home/cc/HyperKamiokande/
```

## Access through the jump server

Use the following command, replacing `<INFN_USERNAME>` with your personal INFN username:

```bash
ssh -J <INFN_USERNAME>@galilinux.pi.infn.it cc@marduk
```

For example, if your INFN username were `myuser`, the command would be:

```bash
ssh -J myuser@galilinux.pi.infn.it cc@marduk
```

This is equivalent to doing the connection in two steps:

```bash
ssh <INFN_USERNAME>@galilinux.pi.infn.it
ssh cc@marduk
```

The one-line `ssh -J` form is usually cleaner because it keeps the local workflow shorter.

## Access from INFN network or VPN

If you are already on the INFN network, or connected through the INFN VPN, `marduk` may be reachable directly:

```bash
ssh cc@marduk
```

Whether this works depends on the local network configuration and DNS resolution.

## After login

Once connected to `marduk`, go to the HK software material directory:

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
fiTQun_git_repo/
utils/
```
