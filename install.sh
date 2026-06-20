#!/usr/bin/env bash
#
# MebTTY - Install / uninstall systemd service
#
# Usage:
#   sudo ./install.sh              # Install executable + systemd service
#   sudo ./install.sh --uninstall  # Remove service and files
#   sudo ./install.sh --help       # Show help
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXEC_SRC="$SCRIPT_DIR/build/mebtty"
EXEC_DEST="/usr/local/bin/mebtty"
SERVICE_SRC="$SCRIPT_DIR/mebtty.service"
SERVICE_DEST="/etc/systemd/system/mebtty.service"
ENV_FILE="/etc/mebtty/mebtty.env"
DATA_DIR="/var/lib/mebtty"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[Install]${NC} $*"; }
warn() { echo -e "${YELLOW}[Install]${NC} $*"; }
err()  { echo -e "${RED}[Install]${NC} $*" >&2; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        err "This script must be run as root (use sudo)."
        exit 1
    fi
}

install() {
    check_root

    # Check that the executable exists
    if [[ ! -f "$EXEC_SRC" ]]; then
        err "Executable not found at $EXEC_SRC"
        err "Run ./build.sh first."
        exit 1
    fi

    if systemctl is-active --quiet mebtty.service 2>/dev/null; then
        log "Stopping existing service before replacing executable..."
        systemctl stop mebtty.service
    fi

    # Copy executable
    log "Installing executable -> $EXEC_DEST"
    cp "$EXEC_SRC" "$EXEC_DEST"
    chmod 755 "$EXEC_DEST"

    # Create data directories
    log "Creating data directory -> $DATA_DIR"
    mkdir -p "$DATA_DIR/uploads"
    chown -R root:root "$DATA_DIR"
    chmod 750 "$DATA_DIR" "$DATA_DIR/uploads"

    # Generate secret key if env file doesn't exist
    if [[ ! -f "$ENV_FILE" ]]; then
        log "Creating environment config -> $ENV_FILE"
        install -d -m 750 -o root -g root "$(dirname "$ENV_FILE")"
        SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
        cat > "$ENV_FILE" <<EOF
# MebTTY environment configuration
# Modify and restart: systemctl restart mebtty

MEBTTY_SECRET_KEY=$SECRET
MEBTTY_HOST=0.0.0.0
MEBTTY_PORT=18888
MEBTTY_PAM_SERVICE=login
EOF
        chown root:root "$ENV_FILE"
        chmod 640 "$ENV_FILE"
    else
        warn "Environment file already exists, skipping ($ENV_FILE)"
        chown root:root "$(dirname "$ENV_FILE")" "$ENV_FILE"
        chmod 750 "$(dirname "$ENV_FILE")"
        chmod 640 "$ENV_FILE"
    fi

    # Install systemd service
    log "Installing systemd service -> $SERVICE_DEST"
    cp "$SERVICE_SRC" "$SERVICE_DEST"
    chmod 644 "$SERVICE_DEST"

    # Enable and start
    systemctl daemon-reload
    systemctl enable mebtty.service
    systemctl start mebtty.service

    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  MebTTY installed and started!${NC}"
    echo -e "${CYAN}${NC}"
    echo -e "${CYAN}  Executable: $EXEC_DEST${NC}"
    echo -e "${CYAN}  Config:     $ENV_FILE${NC}"
    echo -e "${CYAN}  Data:       $DATA_DIR${NC}"
    echo -e "${CYAN}  Service:    root user${NC}"
    echo -e "${CYAN}  Web UI:     http://localhost:18888${NC}"
    echo -e "${CYAN}${NC}"
    echo -e "${CYAN}  systemctl start mebtty${NC}"
    echo -e "${CYAN}  systemctl stop mebtty${NC}"
    echo -e "${CYAN}  systemctl status mebtty${NC}"
    echo -e "${CYAN}  journalctl -u mebtty -f${NC}"
    echo -e "${CYAN}========================================${NC}"
}

uninstall() {
    check_root

    log "Stopping MebTTY service..."
    systemctl stop mebtty.service 2>/dev/null || true
    systemctl disable mebtty.service 2>/dev/null || true

    if [[ -f "$SERVICE_DEST" ]]; then
        log "Removing service file..."
        rm -f "$SERVICE_DEST"
    fi

    if [[ -f "$EXEC_DEST" ]]; then
        log "Removing executable..."
        rm -f "$EXEC_DEST"
    fi

    systemctl daemon-reload

    warn "Data directory kept: $DATA_DIR"
    warn "Config file kept: $ENV_FILE"
    log "To remove all data: rm -rf $DATA_DIR /etc/mebtty"
    log "Uninstall complete."
}

print_help() {
    echo "MebTTY - Install systemd service"
    echo ""
    echo "Usage: sudo ./install.sh [command]"
    echo ""
    echo "Commands:"
    echo "  (none)        Install executable and register systemd service"
    echo "  --uninstall   Stop service and remove installed files"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  Run ./build.sh first to create the executable."
}

# ── Main ─────────────────────────────────────────────────────────

case "${1:-}" in
    --uninstall)
        uninstall
        ;;
    --help|-h)
        print_help
        ;;
    *)
        install
        ;;
esac
