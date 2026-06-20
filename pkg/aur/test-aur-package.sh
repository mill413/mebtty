#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="${TMPDIR:-/tmp}/mebtty-aur-test"

rm -rf "${WORK_DIR}"
mkdir -p "${WORK_DIR}"
cp \
  "${SCRIPT_DIR}/PKGBUILD" \
  "${SCRIPT_DIR}/mebtty.install" \
  "${SCRIPT_DIR}/mebtty.tmpfiles" \
  "${WORK_DIR}/"

if command -v makepkg >/dev/null 2>&1; then
  (
    cd "${WORK_DIR}"
    makepkg --printsrcinfo > .SRCINFO
    makepkg -Cfs --noconfirm
    makepkg --source --noconfirm
  )
else
  docker run --rm \
    -v "${WORK_DIR}:/pkg" \
    archlinux:latest \
    bash -lc '
      set -euo pipefail
      pacman -Sy --noconfirm --needed base-devel git
      useradd -m builder
      chown -R builder:builder /pkg
      su builder -c "cd /pkg && makepkg --printsrcinfo > .SRCINFO"
      su builder -c "cd /pkg && makepkg -Cfs --noconfirm"
      su builder -c "cd /pkg && makepkg --source --noconfirm"
    '
fi

echo
echo "AUR package test completed:"
find "${WORK_DIR}" -maxdepth 1 -type f -name "*.pkg.tar.*" -print
find "${WORK_DIR}" -maxdepth 1 -type f -name "*.src.tar.*" -print
