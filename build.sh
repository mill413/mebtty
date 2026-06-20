#!/usr/bin/env bash
#
# MebTTY - Build standalone Linux executable
#
# Usage:
#   ./build.sh              # Build frontend + backend into a single executable
#   ./build.sh --clean      # Remove build artifacts
#   ./build.sh --help       # Show help
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
BUILD_OUTPUT="$SCRIPT_DIR/build"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

log()  { echo -e "${GREEN}[Build]${NC} $*"; }
warn() { echo -e "${YELLOW}[Build]${NC} $*"; }
err()  { echo -e "${RED}[Build]${NC} $*" >&2; }
dim()  { echo -e "${DIM}$*${NC}"; }

# ── Helpers ──────────────────────────────────────────────────────

check_deps() {
    local missing=()
    command -v python3 >/dev/null 2>&1 || missing+=(python3)
    command -v node    >/dev/null 2>&1 || missing+=(node)
    command -v npm     >/dev/null 2>&1 || missing+=(npm)
    if [[ ${#missing[@]} -gt 0 ]]; then
        err "Missing required tools: ${missing[*]}"
        exit 1
    fi

    local py_version
    py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local py_major py_minor
    py_major=$(echo "$py_version" | cut -d. -f1)
    py_minor=$(echo "$py_version" | cut -d. -f2)
    if (( py_major < 3 || (py_major == 3 && py_minor < 12) )); then
        err "Python 3.12+ required, found $py_version"
        exit 1
    fi

    log "Dependencies check passed (Python $py_version)"
}

build_frontend() {
    log "Building frontend..."
    cd "$FRONTEND_DIR"
    if [[ ! -d node_modules ]]; then
        log "Installing frontend dependencies..."
        npm install
    fi
    npm run build
    log "Frontend built -> frontend/dist/"
}

setup_venv() {
    log "Setting up Python virtual environment..."
    cd "$BACKEND_DIR"

    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
    fi

    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    pip install -q pyinstaller
    log "Python environment ready."
}

build_executable() {
    log "Building executable with PyInstaller..."
    cd "$BACKEND_DIR"
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"

    # Check that frontend dist exists
    if [[ ! -d "$FRONTEND_DIR/dist" ]]; then
        err "Frontend dist not found at $FRONTEND_DIR/dist"
        err "Run frontend build first."
        exit 1
    fi

    # Run PyInstaller using the spec file
    pyinstaller --clean --noconfirm mebtty.spec

    # Move output to project-level build directory
    mkdir -p "$BUILD_OUTPUT"
    cp "$BACKEND_DIR/dist/mebtty" "$BUILD_OUTPUT/mebtty"
    chmod +x "$BUILD_OUTPUT/mebtty"

    local size
    size=$(du -h "$BUILD_OUTPUT/mebtty" | cut -f1)

    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  Build complete!${NC}"
    echo -e "${CYAN}  Executable: build/mebtty ($size)${NC}"
    echo -e "${CYAN}  Run:        sudo ./build/mebtty${NC}"
    echo -e "${CYAN}  Install:    sudo ./install.sh${NC}"
    echo -e "${CYAN}========================================${NC}"
}

clean() {
    log "Cleaning build artifacts..."
    rm -rf "$BUILD_OUTPUT"
    rm -rf "$BACKEND_DIR/build"
    rm -rf "$BACKEND_DIR/dist"
    rm -rf "$BACKEND_DIR/__pycache__"
    rm -rf "$BACKEND_DIR/app/__pycache__"
    log "Done."
}

print_help() {
    echo "MebTTY - Build standalone executable"
    echo ""
    echo "Usage: ./build.sh [command]"
    echo ""
    echo "Commands:"
    echo "  (none)     Build frontend + package into executable"
    echo "  --clean    Remove build artifacts"
    echo "  --help     Show this help message"
    echo ""
    echo "Output:"
    echo "  build/mebtty    Standalone executable"
    echo ""
    echo "After building, install with:"
    echo "  sudo ./install.sh"
}

# ── Main ─────────────────────────────────────────────────────────

case "${1:-}" in
    --clean)
        clean
        ;;
    --help|-h)
        print_help
        ;;
    *)
        check_deps
        build_frontend
        setup_venv
        build_executable
        ;;
esac
