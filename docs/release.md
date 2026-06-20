# Release Process

This project keeps release-ready code on `master` and ongoing work on `develop`.

## Branch Model

| Branch | Purpose |
| ------ | ------- |
| `develop` | Integration branch for day-to-day development |
| `master` | Release branch; tags are cut from here |
| `feature/*` | Short-lived feature branches created from `develop` |
| `fix/*` | Short-lived bug-fix branches created from `develop`, unless patching an already released version |

Normal flow:

```bash
git switch develop
git switch -c feature/my-change

# commit work

git switch develop
git merge --no-ff feature/my-change
```

Release flow:

```bash
git switch develop
git pull --ff-only

# run validation locally
python -m compileall backend/app
(cd frontend && npm run build)

git switch master
git pull --ff-only
git merge --no-ff develop
git tag vX.Y.Z
git push origin master vX.Y.Z
```

The GitHub Actions release workflow validates that the tag is reachable from `origin/master`.

## Version Tags

Allowed tag formats:

- `vX.Y.Z` for stable releases, for example `v0.2.2`
- `vX.Y.Z.dev` for development prereleases, for example `v0.3.0.dev`

Stable tags create normal GitHub Releases. `.dev` tags create prereleases and skip AUR publishing.

## Release Workflow Outputs

When a tag is pushed, `.github/workflows/release.yml` builds:

| Asset | Description |
| ----- | ----------- |
| `mebtty-X.Y.Z-linux-amd64` | Standalone Linux amd64 executable |
| `mebtty_X.Y.Z_amd64.deb` | Debian/Ubuntu amd64 package |
| `mebtty-X.Y.Z-1.src.tar.gz` | AUR source package |
| `checksums.txt` | SHA256 checksums for release assets |

Release notes are generated from GitHub's release-notes API using `.github/release.yml`, then extended with installation instructions and asset descriptions.

## AUR Publishing

The release workflow can publish the `mebtty` AUR package when the repository secret `AUR_SSH_PRIVATE_KEY` is configured.

The private key must have access to:

```text
ssh://aur@aur.archlinux.org/mebtty.git
```

The workflow:

1. Copies `pkg/aur/PKGBUILD`, `mebtty.install`, and `mebtty.tmpfiles`.
2. Rewrites `pkgver` and source checksums for the current tag.
3. Generates `.SRCINFO` in an Arch Linux container.
4. Uploads the AUR source archive to the GitHub Release.
5. Pushes the updated AUR repository for stable releases when `AUR_SSH_PRIVATE_KEY` exists.

AUR commits use:

```text
haruto <mill413@outlook.com>
```

## Local Package Checks

### AUR

```bash
./pkg/aur/test-aur-package.sh
```

This builds the AUR package locally with `makepkg` when available, otherwise through an Arch Linux Docker container.

### Debian

```bash
./pkg/deb/build-deb.sh 0.2.2
```

The Debian helper builds a local `.deb` package from the existing standalone binary or invokes `build.sh` when the binary is missing.

## Runtime Configuration After Install

Packaged installs use:

| Path | Purpose |
| ---- | ------- |
| `/etc/mebtty/mebtty.env` | Environment configuration |
| `/var/lib/mebtty/mebtty.db` | SQLite database |
| `/var/lib/mebtty/uploads` | Uploaded files and avatars |
| `/var/lib/mebtty/plugins` | Installed third-party plugins |

After changing `/etc/mebtty/mebtty.env`, restart the service:

```bash
sudo systemctl restart mebtty
```

## Pre-Release Checklist

- `python -m compileall backend/app`
- `cd frontend && npm run build`
- Local browser smoke test with `./deploy.sh --local-test`
- Verify terminal creation with local user authentication when systemd/PAM behavior changed
- Verify plugin install/update/enable/disable/delete when plugin system behavior changed
- Confirm `README.md`, `README.zh-CN.md`, package docs, and release notes still match behavior
