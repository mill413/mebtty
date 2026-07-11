#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

run_actionlint() {
    if command -v actionlint >/dev/null 2>&1; then
        actionlint
        return
    fi

    if command -v docker >/dev/null 2>&1; then
        docker run --rm \
            -v "$ROOT_DIR:/repo" \
            -w /repo \
            rhysd/actionlint:latest
        return
    fi

    echo "ERROR: actionlint is not installed and Docker is unavailable." >&2
    echo "Install actionlint: https://github.com/rhysd/actionlint" >&2
    exit 1
}

run_dry_run() {
    if ! command -v act >/dev/null 2>&1; then
        echo "ERROR: act is required for --dry-run." >&2
        echo "Install act: https://nektosact.com/installation/" >&2
        exit 1
    fi

    act push --dryrun \
        --workflows .github/workflows \
        --platform ubuntu-24.04=catthehacker/ubuntu:act-24.04
}

run_actionlint

if [[ "${1:-}" == "--dry-run" ]]; then
    run_dry_run
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--dry-run]" >&2
    exit 2
fi

echo "GitHub Actions checks passed."
