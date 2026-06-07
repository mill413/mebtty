# WebTTY Enterprise

<p align="center">
  <strong>A self-hosted, enterprise-grade web terminal platform</strong><br>
  Access your servers from anywhere through a modern browser — no SSH client required.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/vue-3.4%2B-brightgreen?logo=vue.js&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

## Features

- **Full Terminal Experience** — Run bash, zsh, fish and any other shell with full PTY support
- **Interactive Programs** — vim, less, top, htop and other TUI applications work flawlessly
- **Multi-Tab Interface** — Open multiple terminal sessions in a single browser window
- **WebSocket Binary Protocol** — Efficient, low-latency communication with custom binary framing
- **oh-my-zsh Support** — Full compatibility with themes, plugins and autocompletion
- **Session Persistence** — Reconnect to running sessions without losing state
- **Audit Logging** — Track all user actions for compliance and security
- **File Management** — Upload and download files through the terminal interface
- **JWT Authentication** — Secure access with token-based authentication
- **One-Click Deploy** — Run with Docker or a single shell script

## Architecture

```
Browser (xterm.js)
    │
    │  HTTPS / WSS
    ▼
FastAPI Backend
    ├── REST API (auth, sessions, files, audit)
    └── WebSocket Handler (binary protocol)
            │
            ▼
        PTY Runtime
            │
            ├── bash
            ├── zsh (oh-my-zsh)
            └── fish
```

**Tech Stack**

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 (Composition API), Pinia, xterm.js v5 |
| Backend | FastAPI, SQLAlchemy (async), aiosqlite |
| Terminal | Python PTY (pty.fork), login shell |
| Database | SQLite (default), PostgreSQL supported |
| Auth | JWT with RSA, bcrypt password hashing |

## Quick Start

### Docker (Recommended)

```bash
docker compose up -d
```

Open `http://localhost:8000` and register your first account.

### Shell Script

```bash
./deploy.sh
```

This will automatically:
1. Install Python and Node dependencies
2. Build the frontend
3. Start the server on port 8000

Stop the server:

```bash
./deploy.sh --stop
```

### Manual Setup

<details>
<summary>Click to expand</summary>

**Prerequisites:** Python 3.12+, Node.js 18+, npm

```bash
# Frontend
cd frontend
npm install
npm run build

# Backend
cd ../backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start (serves both API and frontend)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

</details>

## Configuration

All settings are configured via environment variables (prefix: `WEBTTY_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBTTY_SECRET_KEY` | Auto-generated | JWT signing key. **Set this in production.** |
| `WEBTTY_DATABASE_URL` | `sqlite+aiosqlite:///./webtty.db` | Database connection string |
| `WEBTTY_STATIC_DIR` | Auto-detected | Path to frontend build output |
| `WEBTTY_UPLOAD_DIR` | `./uploads` | Directory for uploaded files |
| `WEBTTY_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT access token lifetime |
| `WEBTTY_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | JWT refresh token lifetime |
| `WEBTTY_MAX_UPLOAD_SIZE` | `104857600` | Max upload size in bytes (100MB) |

### Production Example

```bash
export WEBTTY_SECRET_KEY="your-random-secret-string"
export WEBTTY_DATABASE_URL="sqlite+aiosqlite:////data/webtty.db"
./deploy.sh
```

## Project Structure

```
web-terminal/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Settings and environment variables
│   │   ├── database.py          # SQLAlchemy async session factory
│   │   ├── models.py            # Database models (User, Session, etc.)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── auth/                # Authentication module
│   │   │   ├── router.py        #   Login, register, refresh endpoints
│   │   │   ├── service.py       #   JWT token generation and validation
│   │   │   └── dependencies.py  #   Auth dependency for protected routes
│   │   ├── session/             # Session management module
│   │   │   ├── router.py        #   CRUD endpoints for terminal sessions
│   │   │   └── service.py       #   Session lifecycle logic
│   │   ├── terminal/            # Terminal runtime module
│   │   │   ├── host_runtime.py  #   PTY process management (pty.fork)
│   │   │   ├── runtime.py       #   Abstract runtime interface
│   │   │   ├── manager.py       #   Session manager and reconnection
│   │   │   ├── ws_handler.py    #   WebSocket handler (binary protocol)
│   │   │   └── router.py        #   WebSocket endpoint registration
│   │   ├── file/                # File management module
│   │   │   └── router.py        #   Upload/download endpoints
│   │   └── audit/               # Audit logging module
│   │       ├── router.py        #   Audit query endpoints
│   │       └── service.py       #   Audit event recording
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.js              # Vue application entry point
│   │   ├── App.vue              # Root component
│   │   ├── router/              # Vue Router configuration
│   │   ├── stores/              # Pinia state management
│   │   │   ├── auth.js          #   Auth state and token management
│   │   │   └── terminal.js      #   Session and tab state
│   │   ├── services/
│   │   │   ├── api.js           #   Axios HTTP client
│   │   │   └── terminal-ws.js   #   WebSocket client (binary protocol)
│   │   ├── components/
│   │   │   ├── layout/          #   UI layout components
│   │   │   │   ├── StatusBar.vue
│   │   │   │   ├── SplitPane.vue
│   │   │   │   └── TerminalToolbar.vue
│   │   │   └── terminal/        #   Terminal-specific components
│   │   │       ├── TerminalPane.vue   # xterm.js wrapper
│   │   │       └── TerminalTabs.vue   # Multi-tab UI
│   │   ├── views/               # Page-level components
│   │   │   ├── LoginView.vue
│   │   │   ├── HomeView.vue
│   │   │   └── TerminalView.vue
│   │   └── styles/
│   │       └── global.css
│   ├── package.json
│   └── vite.config.js
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml           # Docker Compose configuration
├── deploy.sh                    # One-click deployment script
├── .dockerignore
├── .gitignore
├── prd.md                       # Product Requirements Document
└── design.md                    # Technical Design Specification
```

## WebSocket Protocol

The terminal uses a custom binary protocol for efficiency:

```
┌─────────┬────────────┬─────────┐
│ opcode  │  length    │ payload │
│ (1 byte)│ (4 bytes)  │ (N bytes)│
└─────────┴────────────┴─────────┘
```

| Opcode | Name | Direction | Description |
|--------|------|-----------|-------------|
| `0x01` | INPUT | Client → Server | Keyboard input |
| `0x02` | OUTPUT | Server → Client | Terminal output |
| `0x03` | RESIZE | Client → Server | Window size change |
| `0x04` | HEARTBEAT | Bidirectional | Keep-alive ping |
| `0x05` | CLOSE | Bidirectional | Graceful close |
| `0x06` | ERROR | Server → Client | Error message |

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create a new user account |
| POST | `/api/auth/login` | Authenticate and get JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sessions` | List all sessions |
| POST | `/api/sessions` | Create a new terminal session |
| POST | `/api/sessions/{id}/reconnect` | Reconnect to an existing session |
| DELETE | `/api/sessions/{id}` | Delete a session |

### Terminal

| Method | Endpoint | Description |
|--------|----------|-------------|
| WebSocket | `/api/terminal/ws/{session_id}` | Terminal WebSocket connection |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check endpoint |

## Development

```bash
# Terminal 1: Backend with hot reload
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend dev server with API proxy
cd frontend
npm run dev
```

The frontend dev server runs on `http://localhost:3000` and proxies `/api` requests to the backend.

## License

MIT
