# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

**Frontend** (run from `frontend/`):
- `npm install` — Install dependencies
- `npm run dev` — Start Vite dev server on port 3000 with HMR; proxies `/api` to `localhost:18888`
- `npm run build` — Production build to `frontend/dist/`

**Backend** (run from `backend/` with venv activated):
- `pip install -r requirements.txt` — Install Python dependencies
- `uvicorn app.main:app --reload --port 18888` — Run dev server with auto-reload
- `python -m uvicorn app.main:app --host 0.0.0.0 --port 18888` — Production server

**Full local dev workflow** — Run backend in one terminal, `npm run dev` in `frontend/` in another. Open `http://localhost:3000`.

**Docker** — `docker compose up --build` builds and runs the full stack on port 18888.

**Standalone executable** — `./build.sh` (PyInstaller), then `sudo ./install.sh` registers as systemd service. Use `sudo ./install.sh --uninstall` to remove.

**Deployment** — `./deploy.sh` (one-click: build frontend + start backend). Supports `--docker`, `--stop`, `--restart`, `--status`, `--logs`, `--update`.

**There are no automated tests** in this repository — verification is manual.

## Code Style

- **Python**: PEP 8. 4-space indent. `snake_case` for models/schemas, `PascalCase` for classes.
- **Vue/JS**: 2-space indent. `PascalCase` filenames for components (`TerminalView.vue`), `camelCase` for composables/stores.
- **Commits**: Conventional Commits format (`feat:`, `fix:`, `refactor:`, `docs:`).
- **`.env`** must never be committed. All config keys are defined in `backend/app/config.py` with the `MEBTTY_` prefix.

## Architecture

MebTTY is a self-hosted web terminal. A FastAPI backend manages real PTY processes (`pty.fork()`) and exposes them to a Vue 3 frontend via a custom binary WebSocket protocol. The backend serves dual role: REST API + static file server for the SPA in production.

### Backend (`backend/app/`)

The backend is organized as **module subdirectories**, each with its own `router.py` (routes) and `service.py` (business logic, when non-trivial). All routers are registered in `main.py`:

| Module | Path prefix | Responsibility |
|--------|-------------|----------------|
| `auth/` | `/api/auth` | JWT auth (HS256), bcrypt, user registration/login, avatar upload |
| `session/` | `/api/sessions` | CRUD for terminal sessions, shell discovery, reconnection |
| `terminal/` | `/api/terminal` | WebSocket endpoint + PTY host runtime + runtime manager (singleton) |
| `file/` | `/api/files` | File browser: browse/download/upload/mkdir/rename/delete, path traversal protection |
| `settings/` | `/api/settings` | Per-user preferences (theme, accent, tab format, sidebar position, session timeout) |
| `audit/` | `/api/audit` | Command logging with risk-level classification, audit event tracking |

**Key patterns:**
- `database.py` provides an `async_session_factory` and a `get_db` FastAPI dependency (commit on success, rollback on exception). Uses async SQLAlchemy with `aiosqlite` (SQLite) or `asyncpg` (PostgreSQL).
- `config.py` uses `pydantic-settings` with `MEBTTY_` env prefix. Secrets default to in-code values — set `MEBTTY_SECRET_KEY` in production.
- `models.py` defines SQLAlchemy ORM models with UUID primary keys generated via `uuid.uuid4()`. Uses `datetime.now(timezone.utc)` for timestamps.
- `schemas.py` defines Pydantic models (separate from ORM). `ConfigDict(from_attributes=True)` enables ORM-to-Pydantic conversion.

### Terminal Runtime (`backend/app/terminal/`)

The core terminal subsystem uses an abstract `Runtime` ABC (`runtime.py`) with a single implementation `HostRuntime` (`host_runtime.py`):

- **PTY creation**: `pty.fork()` spawns a child process with the target shell as a login shell (`argv[0]` prefixed with `-`).
- **I/O**: Event-driven async read loop using `asyncio.add_reader()` on the PTY master fd. Writes happen via `os.write()` in an executor thread.
- **zsh compatibility**: Strips `FPATH` from child env (lets zsh use compiled-in defaults) and sets `ZSH_DISABLE_COMPFIX=true` (prevents oh-my-zsh compaudit security check from breaking themes/completion in sandboxed environments).
- **Process lifecycle**: `stop()` sends SIGTERM, waits briefly, then SIGKILL. The runtime is NOT destroyed on WebSocket disconnect — sessions persist for reconnection.
- **RuntimeManager** (`manager.py`): Singleton that maps `session_id → Runtime`. Creates, retrieves, and destroys runtimes. Resolves shell names to full paths via `shutil.which()`.

### WebSocket Protocol (`terminal/ws_handler.py` + `frontend/src/services/terminal-ws.js`)

Custom binary protocol for low-latency PTY I/O:

```
[opcode: 1 byte][length: 4 bytes big-endian][payload: N bytes]
```

| Opcode | Name | Direction | Description |
|--------|------|-----------|-------------|
| `0x01` | INPUT | Client→Server | Keyboard input |
| `0x02` | OUTPUT | Server→Client | Terminal output |
| `0x03` | RESIZE | Client→Server | cols+rows as two uint16 |
| `0x04` | HEARTBEAT | Bidirectional | 30-second keep-alive |
| `0x05` | CLOSE | Bidirectional | Graceful disconnect |
| `0x06` | ERROR | Server→Client | Error message (UTF-8) |

The WebSocket handler spawns two async tasks (reader + writer) that race — when either finishes, the other is cancelled and the session is marked `"detached"` (runtime preserved for recovery).

### Auth Flow

1. JWT access tokens (HS256, default 60min) + refresh tokens (default 7 days).
2. `get_current_user` dependency extracts the token via `OAuth2PasswordBearer`, decodes it, and returns the `User` ORM object.
3. Frontend stores tokens in `localStorage`, attaches via Axios interceptor, and redirects to `/login` on 401.
4. Password hashing via `bcrypt` (through `passlib`).

### Frontend (`frontend/src/`)

- **Vue 3 Composition API** with Pinia stores, Vue Router, and vue-i18n.
- **Router** (`router/index.js`): Lazy-loaded views. Guards check for access token in localStorage (not Pinia state, since stores reset on refresh).
- **Stores** (Pinia):
  - `auth.js` — Login/register/logout, token refresh, user profile.
  - `terminal.js` — Multi-tab session management. Tabs have IDs (local counter) and reference backend session IDs. Open/close/switch/reorder tabs, create/reconnect/delete sessions.
  - `theme.js` — Three modes: system (follows OS `prefers-color-scheme`), dark, light. Resolved to `data-theme` attribute for CSS.
  - `settings.js` — User preferences synced to backend and localStorage. Handles accent color application, status bar layout, tab title formatting.
- **i18n**: 4 languages (en-US, zh-CN, zh-TW, ja). Auto-detection via `navigator.language` with prefix fallback. Preference saved to localStorage.
- **WebSocket client** (`services/terminal-ws.js`): Encodes/decodes the binary protocol, handles heartbeat, resize forwarding, and terminal input binding via xterm.js `onData`.

### Database

SQLite by default (`sqlite+aiosqlite:///./mebtty.db`). PostgreSQL supported via `asyncpg`. Tables: `users`, `sessions`, `command_logs`, `audit_events`, `user_settings`. Auto-migration in `main.py`'s `migrate_db()` adds columns to existing SQLite tables (since SQLite doesn't support `ALTER TABLE ADD COLUMN` via SQLAlchemy).

### Startup Sequence (`main.py` lifespan)

1. `init_db()` — `Base.metadata.create_all`
2. `migrate_db()` — Add missing columns (SQLite-only)
3. `cleanup_stale_sessions()` — Mark sessions with status `"running"`/`"starting"`/`"created"` as `"stopped"`
4. `cleanup_expired_sessions()` — Delete sessions older than per-user timeout (default: disabled / 0)
5. On shutdown: log, no cleanup (PTY processes are children of this process, die with it)

### Serving the Frontend

In production, the backend serves the frontend SPA from `frontend/dist/`. The path is auto-detected but can be set via `MEBTTY_STATIC_DIR`. Assets are mounted at `/assets`; all other routes fall back to `index.html` for client-side routing.

### Standalone Executable (`build.sh` + `backend/mebtty.spec` + `install.sh`)

`build.sh` builds the frontend, creates a venv, installs PyInstaller, and runs `pyinstaller mebtty.spec`. The spec bundles `bundle_entry.py` (entry point), all app modules as hidden imports, and embeds `frontend/dist` as data. The output is `build/mebtty` — a single self-contained Linux binary.
