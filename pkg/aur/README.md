# AUR packaging

This directory contains the Arch User Repository package metadata for `mebtty`.

`mebtty` installs the prebuilt Linux amd64 executable from GitHub Releases and a systemd service. The service runs as root so MebTTY can authenticate local users with PAM and drop terminal sessions to the selected user's uid/gid. It does not enable or start the service automatically.

After installing, adjust the PAM service in `/etc/mebtty/mebtty.env` if your system needs a service other than `login`:

```bash
MEBTTY_PAM_SERVICE=login
```

## Local test

From the repository root:

```bash
./pkg/aur/test-aur-package.sh
```

The script copies the AUR files to a temporary directory, generates `.SRCINFO`, and builds the package with `makepkg`. If `makepkg` is not available locally, it falls back to an Arch Linux Docker container.

## Release workflow

The GitHub release workflow rewrites `pkgver` and checksums for the tagged release, generates `.SRCINFO`, creates an AUR source archive, and can publish to AUR when the required secrets are configured.

Required secrets for AUR publishing:

- `AUR_SSH_PRIVATE_KEY`: SSH private key with access to `aur@aur.archlinux.org:mebtty.git`

If this secret is not configured, the workflow still builds and uploads the AUR source archive to the GitHub Release. AUR commits use `haruto <mill413@outlook.com>` as the author identity.
