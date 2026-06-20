#!/usr/bin/env bash
#
# MebTTY - One-click deployment script
#
# Usage:
#   ./deploy.sh              # Build/rebuild and replace the running server
#   ./deploy.sh --docker     # Build and start via Docker
#   ./deploy.sh --stop       # Stop the running server or Docker container
#   ./deploy.sh --restart    # Restart the server
#   ./deploy.sh --status     # Check server status
#   ./deploy.sh --logs       # Tail server logs
#   ./deploy.sh --update     # Pull latest code and redeploy
#   ./deploy.sh --dev        # Start local hot-reload dev servers
#
# Short options: -D (docker), -K (docker-stop), -s (stop),
#                -r (restart), -t (status), -l (logs), -u (update),
#                -d (dev)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/venv"
DATA_DIR="$BACKEND_DIR/data"
ENV_FILE="$SCRIPT_DIR/.env"
PID_FILE="$SCRIPT_DIR/.mebtty.pid"
DEV_BACKEND_PID_FILE="$SCRIPT_DIR/.mebtty-dev-backend.pid"
DEV_FRONTEND_PID_FILE="$SCRIPT_DIR/.mebtty-dev-frontend.pid"
LOG_FILE="$SCRIPT_DIR/mebtty.log"
DEV_BACKEND_LOG_FILE="$SCRIPT_DIR/mebtty-dev-backend.log"
DEV_FRONTEND_LOG_FILE="$SCRIPT_DIR/mebtty-dev-frontend.log"

# Load .env file if exists
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

HOST="${MEBTTY_HOST:-0.0.0.0}"
PORT="${MEBTTY_PORT:-18888}"
DEV_FRONTEND_HOST="${MEBTTY_DEV_FRONTEND_HOST:-127.0.0.1}"
DEV_FRONTEND_PORT="${MEBTTY_DEV_FRONTEND_PORT:-3000}"
PLUGIN_DIR="${MEBTTY_PLUGIN_DIR:-$DATA_DIR/plugins}"

# Required minimum versions
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=12
MIN_NODE_MAJOR=18

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
NC='\033[0m'

log()  { echo -e "${GREEN}[MebTTY]${NC} $*"; }
warn() { echo -e "${YELLOW}[MebTTY]${NC} $*"; }
err()  { echo -e "${RED}[MebTTY]${NC} $*" >&2; }
dim()  { echo -e "${DIM}$*${NC}"; }

# ── Helpers ──────────────────────────────────────────────────────

is_server_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

is_pid_file_running() {
    local pid_file="$1"
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

get_server_pid() {
    if [[ -f "$PID_FILE" ]]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

get_pid_from_file() {
    local pid_file="$1"
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file"
    else
        echo ""
    fi
}

wait_for_health() {
    local max_wait=${1:-15}
    local url="http://localhost:$PORT/api/health"
    for ((i = 1; i <= max_wait; i++)); do
        if curl -sf "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

check_port_available() {
    check_tcp_port_available "$PORT"
}

check_tcp_port_available() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
            return 1
        fi
    elif command -v lsof >/dev/null 2>&1; then
        if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
            return 1
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
            return 1
        fi
    fi
    return 0
}

docker_compose_available() {
    command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1
}

docker_compose_service_ids() {
    if ! docker_compose_available; then
        return 0
    fi
    cd "$SCRIPT_DIR"
    docker compose ps -q mebtty 2>/dev/null || true
}

ensure_env_secret() {
    # Persist a generated secret key to .env so it survives restarts
    if [[ -z "${MEBTTY_SECRET_KEY:-}" ]]; then
        local key
        key=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
        mkdir -p "$(dirname "$ENV_FILE")"
        if [[ -f "$ENV_FILE" ]]; then
            echo "" >> "$ENV_FILE"
        fi
        echo "# Auto-generated JWT secret (remove to regenerate)" >> "$ENV_FILE"
        echo "MEBTTY_SECRET_KEY=$key" >> "$ENV_FILE"
        export MEBTTY_SECRET_KEY="$key"
        log "Generated and persisted secret key to .env"
    fi
}

stop_local_server_if_present() {
    if is_server_running || [[ -f "$PID_FILE" ]]; then
        stop_server
        return 0
    fi
    return 1
}

stop_docker_deployment_if_running() {
    local ids
    ids=$(docker_compose_service_ids)
    if [[ -z "$ids" ]]; then
        return 1
    fi

    log "Stopping Docker deployment..."
    cd "$SCRIPT_DIR"
    docker compose down --remove-orphans
    log "Docker deployment stopped."
    return 0
}

stop_deployments() {
    local stopped=0

    if stop_local_server_if_present; then
        stopped=1
    fi
    if stop_dev_servers_if_present; then
        stopped=1
    fi
    if stop_docker_deployment_if_running; then
        stopped=1
    fi

    if [[ "$stopped" -eq 0 ]]; then
        warn "MebTTY is not running."
    fi
}

# ── Commands ─────────────────────────────────────────────────────

check_deps() {
    local missing=()
    command -v python3 >/dev/null 2>&1 || missing+=(python3)
    command -v node    >/dev/null 2>&1 || missing+=(node)
    command -v npm     >/dev/null 2>&1 || missing+=(npm)
    command -v curl    >/dev/null 2>&1 || missing+=(curl)
    command -v setsid  >/dev/null 2>&1 || missing+=(setsid)
    if [[ ${#missing[@]} -gt 0 ]]; then
        err "Missing required tools: ${missing[*]}"
        err "Please install them and try again."
        exit 1
    fi

    # Check Python version
    local py_version
    py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local py_major py_minor
    py_major=$(echo "$py_version" | cut -d. -f1)
    py_minor=$(echo "$py_version" | cut -d. -f2)
    if (( py_major < MIN_PYTHON_MAJOR || (py_major == MIN_PYTHON_MAJOR && py_minor < MIN_PYTHON_MINOR) )); then
        err "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ required, found $py_version"
        exit 1
    fi

    # Check Node.js version
    local node_version
    node_version=$(node -v | sed 's/^v//')
    local node_major
    node_major=$(echo "$node_version" | cut -d. -f1)
    if (( node_major < MIN_NODE_MAJOR )); then
        err "Node.js ${MIN_NODE_MAJOR}+ required, found v$node_version"
        exit 1
    fi

    log "Dependencies check passed (Python $py_version, Node.js v$node_version)"
}

build_frontend() {
    log "Building frontend..."
    cd "$FRONTEND_DIR"
    if [[ ! -d node_modules ]]; then
        log "Installing frontend dependencies..."
        npm install
    fi
    npm run build
    log "Frontend built successfully -> frontend/dist/"
}

setup_backend() {
    log "Setting up backend..."
    cd "$BACKEND_DIR"

    if [[ ! -d "$VENV_DIR" ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi

    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    log "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt

    mkdir -p "$DATA_DIR" "$BACKEND_DIR/uploads" "$PLUGIN_DIR"
}

setup_frontend_dev() {
    cd "$FRONTEND_DIR"
    if [[ ! -d node_modules ]]; then
        log "Installing frontend dependencies..."
        npm install
    fi
}

start_server() {
    cd "$BACKEND_DIR"
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"

    # Stop existing instance if running
    stop_local_server_if_present || true

    # Wait for port to become available
    if ! check_port_available; then
        log "Waiting for port $PORT to be released..."
        for ((i = 1; i <= 10; i++)); do
            sleep 1
            if check_port_available; then
                break
            fi
        done
        if ! check_port_available; then
            # Last resort: force kill anything on this port
            if command -v fuser >/dev/null 2>&1; then
                fuser -k "${PORT}/tcp" 2>/dev/null || true
                sleep 1
            fi
        fi
        if ! check_port_available; then
            err "Port $PORT is already in use. Set MEBTTY_PORT to a different port or stop the other process."
            exit 1
        fi
    fi

    export MEBTTY_STATIC_DIR="$FRONTEND_DIR/dist"
    export MEBTTY_DATABASE_URL="${MEBTTY_DATABASE_URL:-sqlite+aiosqlite:///$DATA_DIR/mebtty.db}"
    export MEBTTY_PLUGIN_DIR="$PLUGIN_DIR"
    ensure_env_secret

    log "Starting MebTTY server on $HOST:$PORT..."
    dim "  Frontend: $MEBTTY_STATIC_DIR"
    dim "  Database: $MEBTTY_DATABASE_URL"
    dim "  Plugins: $MEBTTY_PLUGIN_DIR"

    nohup setsid python3 -m uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        >> "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"

    # Wait for server to become healthy
    log "Waiting for server to start..."
    if wait_for_health 15; then
        local pid
        pid=$(cat "$PID_FILE")
        echo ""
        echo -e "${CYAN}========================================${NC}"
        echo -e "${CYAN}  MebTTY is running!${NC}"
        echo -e "${CYAN}  Open:   http://localhost:$PORT${NC}"
        echo -e "${CYAN}  PID:    $pid${NC}"
        echo -e "${CYAN}  Log:    $LOG_FILE${NC}"
        echo -e "${CYAN}  Stop:   ./deploy.sh --stop${NC}"
        echo -e "${CYAN}  Status: ./deploy.sh --status${NC}"
        echo -e "${CYAN}========================================${NC}"
    else
        # Server might have crashed
        if is_server_running; then
            warn "Server started but health check timed out."
            warn "Check logs: ./deploy.sh --logs"
        else
            err "Server failed to start. Last log output:"
            tail -20 "$LOG_FILE"
            rm -f "$PID_FILE"
            exit 1
        fi
    fi
}

stop_process_from_pid_file() {
    local pid_file="$1"
    local name="$2"

    if is_pid_file_running "$pid_file"; then
        local pid
        pid=$(get_pid_from_file "$pid_file")
        log "Stopping $name (PID: $pid)..."
        pkill -P "$pid" 2>/dev/null || true
        kill "$pid" 2>/dev/null || true
        for ((i = 1; i <= 5; i++)); do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        if kill -0 "$pid" 2>/dev/null; then
            warn "$name did not stop gracefully, force killing..."
            kill -9 "$pid" 2>/dev/null || true
            pkill -9 -P "$pid" 2>/dev/null || true
        fi
        log "$name stopped."
        rm -f "$pid_file"
        return 0
    fi

    if [[ -f "$pid_file" ]]; then
        warn "$name was not running (stale PID file removed)."
        rm -f "$pid_file"
        return 0
    fi

    return 1
}

stop_dev_servers_if_present() {
    local stopped=0
    if stop_process_from_pid_file "$DEV_FRONTEND_PID_FILE" "frontend dev server"; then
        stopped=1
    fi
    if stop_process_from_pid_file "$DEV_BACKEND_PID_FILE" "backend dev server"; then
        stopped=1
    fi
    [[ "$stopped" -eq 1 ]]
}

start_dev_servers() {
    check_deps
    setup_backend
    setup_frontend_dev
    stop_docker_deployment_if_running || true
    stop_local_server_if_present || true
    stop_dev_servers_if_present || true

    if ! check_tcp_port_available "$PORT"; then
        err "Backend port $PORT is already in use. Set MEBTTY_PORT to a different port or stop the other process."
        exit 1
    fi
    if ! check_tcp_port_available "$DEV_FRONTEND_PORT"; then
        err "Frontend dev port $DEV_FRONTEND_PORT is already in use. Set MEBTTY_DEV_FRONTEND_PORT to a different port or stop the other process."
        exit 1
    fi

    ensure_env_secret
    export MEBTTY_DATABASE_URL="${MEBTTY_DATABASE_URL:-sqlite+aiosqlite:///$DATA_DIR/mebtty.db}"
    export MEBTTY_UPLOAD_DIR="${MEBTTY_UPLOAD_DIR:-$BACKEND_DIR/uploads}"
    export MEBTTY_PLUGIN_DIR="$PLUGIN_DIR"
    export MEBTTY_STATIC_DIR=""
    export MEBTTY_PORT="$PORT"
    export MEBTTY_DEV_FRONTEND_PORT="$DEV_FRONTEND_PORT"

    log "Starting backend dev server with reload on $HOST:$PORT..."
    cd "$BACKEND_DIR"
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    nohup setsid python3 -m uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        >> "$DEV_BACKEND_LOG_FILE" 2>&1 &
    echo $! > "$DEV_BACKEND_PID_FILE"

    log "Starting frontend dev server on $DEV_FRONTEND_HOST:$DEV_FRONTEND_PORT..."
    cd "$FRONTEND_DIR"
    nohup setsid npm run dev -- \
        --host "$DEV_FRONTEND_HOST" \
        --port "$DEV_FRONTEND_PORT" \
        >> "$DEV_FRONTEND_LOG_FILE" 2>&1 &
    echo $! > "$DEV_FRONTEND_PID_FILE"

    log "Waiting for backend health..."
    if ! wait_for_health 20; then
        warn "Backend health check timed out. Check logs with ./deploy.sh --logs"
    fi

    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  MebTTY dev mode is running!${NC}"
    echo -e "${CYAN}  Open:     http://localhost:$DEV_FRONTEND_PORT${NC}"
    echo -e "${CYAN}  Backend:  http://localhost:$PORT${NC}"
    echo -e "${CYAN}  Backend PID:  $(cat "$DEV_BACKEND_PID_FILE")${NC}"
    echo -e "${CYAN}  Frontend PID: $(cat "$DEV_FRONTEND_PID_FILE")${NC}"
    echo -e "${CYAN}  Logs:     ./deploy.sh --logs${NC}"
    echo -e "${CYAN}  Stop:     ./deploy.sh --stop${NC}"
    echo -e "${CYAN}========================================${NC}"
}

stop_server() {
    if is_server_running; then
        local pid
        pid=$(get_server_pid)
        log "Stopping server (PID: $pid)..."

        # Kill child processes first (uvicorn workers)
        pkill -P "$pid" 2>/dev/null || true

        # Send SIGTERM first, wait up to 5 seconds
        kill "$pid" 2>/dev/null || true
        for ((i = 1; i <= 5; i++)); do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            warn "Server did not stop gracefully, force killing..."
            kill -9 "$pid" 2>/dev/null || true
            pkill -9 -P "$pid" 2>/dev/null || true
        fi

        # Also kill any remaining processes on the port
        if command -v fuser >/dev/null 2>&1; then
            fuser -k "${PORT}/tcp" 2>/dev/null || true
        fi

        sleep 1

        log "Server stopped."
    elif [[ -f "$PID_FILE" ]]; then
        warn "Server was not running (stale PID file removed)."
    else
        warn "Server is not running."
    fi
    rm -f "$PID_FILE"
}

show_status() {
    if is_pid_file_running "$DEV_BACKEND_PID_FILE" || is_pid_file_running "$DEV_FRONTEND_PID_FILE"; then
        echo -e "${GREEN}●${NC} MebTTY dev mode"
        if is_pid_file_running "$DEV_BACKEND_PID_FILE"; then
            echo -e "  Backend PID:  $(get_pid_from_file "$DEV_BACKEND_PID_FILE")"
            echo -e "  Backend URL:  http://localhost:$PORT"
            if curl -sf "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
                echo -e "  Backend:      ${GREEN}healthy${NC}"
            else
                echo -e "  Backend:      ${YELLOW}unreachable${NC}"
            fi
        else
            echo -e "  Backend:      ${RED}stopped${NC}"
        fi
        if is_pid_file_running "$DEV_FRONTEND_PID_FILE"; then
            echo -e "  Frontend PID: $(get_pid_from_file "$DEV_FRONTEND_PID_FILE")"
            echo -e "  Frontend URL: http://localhost:$DEV_FRONTEND_PORT"
        else
            echo -e "  Frontend:     ${RED}stopped${NC}"
        fi
    elif is_server_running; then
        local pid
        pid=$(get_server_pid)
        echo -e "${GREEN}●${NC} MebTTY is running"
        echo -e "  PID:    $pid"
        echo -e "  URL:    http://localhost:$PORT"
        echo -e "  Log:    $LOG_FILE"

        # Check health endpoint
        if curl -sf "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
            echo -e "  Health: ${GREEN}healthy${NC}"
        else
            echo -e "  Health: ${YELLOW}unreachable${NC}"
        fi
    else
        echo -e "${RED}●${NC} MebTTY is not running"
        if [[ -f "$PID_FILE" ]]; then
            warn "Stale PID file found. Run ./deploy.sh --stop to clean up."
        fi
    fi
}

show_logs() {
    if [[ -f "$DEV_BACKEND_LOG_FILE" || -f "$DEV_FRONTEND_LOG_FILE" ]]; then
        log "Tailing dev logs (Ctrl+C to exit)..."
        local logs=()
        [[ -f "$DEV_BACKEND_LOG_FILE" ]] && logs+=("$DEV_BACKEND_LOG_FILE")
        [[ -f "$DEV_FRONTEND_LOG_FILE" ]] && logs+=("$DEV_FRONTEND_LOG_FILE")
        tail -f "${logs[@]}"
    elif [[ ! -f "$LOG_FILE" ]]; then
        warn "No log file found at $LOG_FILE"
        exit 1
    else
        log "Tailing logs (Ctrl+C to exit)..."
        tail -f "$LOG_FILE"
    fi
}

restart_server() {
    local docker_ids
    docker_ids=$(docker_compose_service_ids)
    if [[ -n "$docker_ids" ]]; then
        docker_deploy
        return
    fi

    stop_local_server_if_present || true
    start_server
}

deploy_local() {
    check_deps
    build_frontend
    setup_backend
    stop_docker_deployment_if_running || true
    start_server
}

update_and_redeploy() {
    log "Updating MebTTY..."

    # Check if we're in a git repo
    if ! command -v git >/dev/null 2>&1; then
        err "git is required for --update."
        exit 1
    fi
    if [[ ! -d "$SCRIPT_DIR/.git" ]]; then
        err "Not a git repository. Cannot update."
        exit 1
    fi

    cd "$SCRIPT_DIR"
    log "Pulling latest changes..."
    git pull --ff-only || {
        err "git pull failed. Resolve conflicts and try again."
        exit 1
    }

    log "Rebuilding and restarting..."
    deploy_local
}

docker_deploy() {
    if ! command -v docker >/dev/null 2>&1; then
        err "Docker is not installed."
        exit 1
    fi
    ensure_env_secret
    stop_local_server_if_present || true
    log "Building and replacing Docker containers..."
    cd "$SCRIPT_DIR"
    docker compose up --build --force-recreate --remove-orphans -d
    log "Docker containers started."
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  MebTTY is running (Docker)!${NC}"
    echo -e "${CYAN}  Open:   http://localhost:18888${NC}"
    echo -e "${CYAN}  Stop:   ./deploy.sh --docker-stop${NC}"
    echo -e "${CYAN}  Logs:   docker compose logs -f${NC}"
    echo -e "${CYAN}========================================${NC}"
}

docker_stop() {
    if ! stop_docker_deployment_if_running; then
        warn "Docker deployment is not running."
    fi
}

print_help() {
    echo "MebTTY - Self-hosted web terminal"
    echo ""
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  (none)             Build frontend + replace running backend server"
    echo "  --docker,     -D   Build/rebuild and replace Docker Compose deployment"
    echo "  --docker-stop,-K   Stop Docker containers"
    echo "  --stop,       -s   Stop the running server or Docker container"
    echo "  --restart,    -r   Restart the server"
    echo "  --status,     -t   Check if the server is running"
    echo "  --logs,       -l   Tail server logs"
    echo "  --update,     -u   Pull latest code and redeploy"
    echo "  --dev,        -d   Start local hot-reload backend + frontend servers"
    echo "  --local-test       Alias for --dev"
    echo "  --help,       -h   Show this help message"
    echo ""
    echo "Environment variables (or .env file):"
    echo "  MEBTTY_HOST              Bind address          (default: 0.0.0.0)"
    echo "  MEBTTY_PORT              Listen port            (default: 18888)"
    echo "  MEBTTY_SECRET_KEY        JWT secret             (default: auto-generated)"
    echo "  MEBTTY_DATABASE_URL      Database URL           (default: SQLite in data/)"
    echo "  MEBTTY_UPLOAD_DIR        Upload directory       (default: ./uploads)"
    echo "  MEBTTY_PLUGIN_DIR        Plugin directory       (default: data/plugins)"
    echo "  MEBTTY_PLUGIN_MAX_SIZE   Plugin package bytes   (default: 20971520)"
    echo "  MEBTTY_PLUGIN_INSTALL_ENABLED Enable plugin install (default: true)"
    echo "  MEBTTY_MAX_UPLOAD_SIZE   Max upload size bytes  (default: 104857600)"
    echo "  MEBTTY_DEV_FRONTEND_HOST Dev frontend host      (default: 127.0.0.1)"
    echo "  MEBTTY_DEV_FRONTEND_PORT Dev frontend port      (default: 3000)"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh                        # Quick start"
    echo "  ./deploy.sh --dev                  # Local hot-reload development"
    echo "  MEBTTY_PORT=3000 ./deploy.sh       # Start on port 3000"
    echo "  ./deploy.sh --status               # Check server status"
}

# ── Main ─────────────────────────────────────────────────────────

case "${1:-}" in
    --docker|-D)
        docker_deploy
        ;;
    --docker-stop|-K)
        docker_stop
        ;;
    --stop|-s)
        stop_deployments
        ;;
    --restart|-r)
        restart_server
        ;;
    --status|-t)
        show_status
        ;;
    --logs|-l)
        show_logs
        ;;
    --update|-u)
        update_and_redeploy
        ;;
    --dev|-d|--local-test)
        start_dev_servers
        ;;
    --help|-h)
        print_help
        ;;
    *)
        deploy_local
        ;;
esac
