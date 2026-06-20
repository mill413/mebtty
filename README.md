# MebTTY

<p align="center">
  <strong>A self-hosted web terminal that brings the full power of your server to any browser.</strong><br>
  <em>MebTTY = MebTTY Makes Browsers TTY.</em><br>
  Open a tab, pick your shell, and start working — no SSH client, no setup, no friction.
</p>

<p align="center">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/mill413/mebtty?label=version&color=blueviolet" alt="Version">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/vue-3.4%2B-brightgreen?logo=vue.js&logoColor=white" alt="Vue">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
</p>

---

MebTTY turns any modern browser into a fully-featured terminal. Built with **FastAPI** and **Vue 3**, it provides real PTY sessions with support for bash, zsh, fish, nushell and more — including oh-my-zsh themes and interactive TUI programs like vim, htop, and less.

A built-in **file browser** lets you browse, preview, edit, upload, download, rename, and delete files alongside your terminal. A **Catppuccin-themed** UI with dark/light modes, customizable accent colors, multi-tab support, and four languages (English, 简体中文, 繁體中文, 日本語) make it pleasant to use every day.

MebTTY also includes a first-class **plugin system**. Built-in features such as the file browser, default theme, and icon pack are registered as plugins, and administrators can install `.mtpx` packages that contribute panels, toolbar actions, settings sections, themes, icon packs, and file providers.

Deploy with a single script or Docker — and access your server from anywhere.

## Features

### Terminal

- **Full PTY Support** — Real pseudo-terminal via `pty.fork()` with login shell invocation; bash, zsh, fish, nushell, and more
- **Dynamic Shell Detection** — Automatically discovers available shells from `/etc/shells` and PATH, with brand SVG icons
- **Interactive Programs** — vim, less, top, htop, and all TUI applications work flawlessly
- **oh-my-zsh Compatibility** — Full support for themes, plugins, and autocompletion
- **Session Persistence** — Disconnect and reconnect to running sessions without losing state; sessions survive server restarts
- **Custom Binary WebSocket Protocol** — Efficient, low-latency terminal I/O with heartbeat keep-alive
- **xterm.js Powered** — 256-color support, 5000-line scrollback, search, clickable URLs, Unicode 11

### Multi-Tab Interface

- **Multiple Sessions** — Open and switch between multiple terminal sessions in a single window
- **Tab Management** — Create, close, rename (double-click), and drag-reorder tabs
- **Settings as a Tab** — Settings page opens as a tab within the terminal view for seamless workflow
- **Customizable Tab Titles** — Template-based titles with `{shell}`, `{index}`, `{title}`, `{user}`, `{cwd}` variables
- **Live Working Directory Titles** — `{cwd}` follows the active shell directory and displays compact names (`~` for home, last directory otherwise)
- **Dynamic Browser Title** — Window title updates to reflect the active session

### File Browser

- **Sidebar Explorer** — Toggleable, resizable sidebar with directory tree view and breadcrumb navigation
- **Full File Operations** — Browse, upload, download, create directories, rename, and delete files
- **Inline Preview & Editor** — Double-click text files to open a resizable editor pane beside the terminal
- **Auto-Save by Default** — Text edits save automatically, with manual save support and dirty-state protection
- **Read-Only Media Preview** — Images open as previews; unsupported non-text files show metadata instead of editing controls
- **Optional Line Numbers** — File editor line numbers can be enabled in settings
- **Catppuccin File Icons** — 200+ themed SVG icons for files and folders
- **Context Menu** — Right-click for quick file operations
- **Configurable Root** — Set the browse root directory via environment variable
- **Path Safety Checks** — Relative paths start from the configured browse root; absolute paths are resolved and rely on OS permissions

### Appearance & Customization

- **Catppuccin Color Scheme** — Mocha (dark) and Latte (light) palettes for both UI and terminal
- **Three Theme Modes** — System (follows OS preference), Dark, and Light
- **Customizable Accent Color** — 7 presets (violet, blue, emerald, amber, red, pink, cyan) plus a custom color picker
- **Full Custom Themes** — Customize dark and light color tokens independently
- **Plugin Themes & Icons** — Enabled plugins can contribute selectable themes and file icon packs
- **Configurable Status Bar** — Show/hide, drag-to-reorder items (shell, process status, connection), left/right positioning
- **Sidebar Position** — Choose left or right side for the file browser

### Plugins

- **Installable `.mtpx` Packages** — Upload plugin packages from Settings or the plugin API
- **Built-In Plugin Foundation** — File browser, default theme, and Catppuccin icons are bundled plugins and update with MebTTY itself
- **Runtime Contributions** — Plugins can add terminal panels, toolbar buttons, settings sections, themes, icon packs, and file providers
- **Admin-Only Management** — Installing, enabling, disabling, and deleting plugins requires an administrator account
- **Package Validation** — Plugin IDs, schemas, permissions, safe zip paths, file counts, and expanded size are validated before installation
- **Frontend Plugin API** — Frontend plugins receive Vue helpers and the authenticated `ctx.api` client

### Internationalization

- **Four Languages** — English, 简体中文, 繁體中文, 日本語
- **Browser Auto-Detection** — Matches `navigator.language` with prefix fallback
- **Persistent Preference** — Saved to both localStorage and server-side user settings

### Security & Administration

- **JWT Authentication** — Token-based auth with access/refresh token rotation and bcrypt password hashing
- **Automatic Token Refresh** — Expired access tokens are refreshed transparently before redirecting to login
- **First-User Admin Setup** — The first registered MebTTY user becomes an administrator; existing databases without an admin promote the oldest user
- **Local User Login for Terminals** — Terminal creation can authenticate a local OS user with PAM and run the PTY as that user
- **User Avatar** — Upload and display profile pictures (PNG, JPEG, WebP, GIF)
- **Audit Logging** — Track all user actions and executed commands with risk levels
- **Admin Controls** — Admin-only audit event listing and plugin management; per-user access scoping
- **Password Management** — Change password with current password verification

### Deployment & Operations

- **One-Click Deploy** — Single shell script handles dependency checks, build, and server startup
- **Repeatable Redeploys** — Re-run `./deploy.sh` or `./deploy.sh --docker` to rebuild and replace the running instance
- **Standalone Executable** — Build a single Linux binary with PyInstaller, install as a systemd service with security hardening and auto-restart
- **Docker Support** — Multi-stage build with persistent volumes and auto-restart
- **Session Auto-Cleanup** — Stale sessions cleaned on server restart; expired sessions auto-deleted by configurable timeout
- **Database Flexibility** — SQLite by default, PostgreSQL supported for production

## Architecture

```text
Browser (xterm.js)
    │
    │  HTTPS / WSS
    ▼
FastAPI Backend
    ├── REST API (auth, sessions, files, settings, audit, plugins)
    └── WebSocket Handler (binary protocol)
            │
            ▼
        PTY Runtime
            │
            ├── bash
            ├── zsh (oh-my-zsh)
            ├── fish
            ├── nushell
            └── sh / dash / ksh / csh / tcsh
```

**Tech Stack**

| Layer    | Technology                                       |
| -------- | ------------------------------------------------ |
| Frontend | Vue 3 (Composition API), Pinia, xterm.js v5      |
| Backend  | FastAPI, SQLAlchemy (async), aiosqlite / asyncpg |
| Terminal | Python PTY (`pty.fork`), login shell             |
| Database | SQLite (default), PostgreSQL supported           |
| Auth     | JWT (HS256), bcrypt password hashing             |
| i18n     | vue-i18n with browser locale auto-detection      |
| Plugins  | `.mtpx` zip packages, manifest-driven frontend runtime |

## Quick Start

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
python -m uvicorn app.main:app --host 0.0.0.0 --port 18888
```

Open `http://localhost:18888` and register your first account.

Run the backend as root when you need local-user terminal sessions.

### Shell Script

```bash
./deploy.sh
```

This will automatically install dependencies, build the frontend and start the server on port 18888.
It is safe to run repeatedly after code changes; the script replaces the currently running instance.
Use `sudo -E ./deploy.sh` for production local-user terminal sessions.

```bash
./deploy.sh --status     # Check server status
./deploy.sh --stop       # Stop the server
./deploy.sh --restart    # Restart the server
./deploy.sh --logs       # Tail server logs
./deploy.sh --update     # Pull latest code and redeploy
./deploy.sh --docker     # Deploy via Docker Compose
./deploy.sh --local-test # Start hot-reload backend + frontend servers
./deploy.sh --help       # Show all commands
```

### Docker

```bash
docker compose up -d
```

Open `http://localhost:18888` and register your first account.

### Standalone Executable (systemd service)

Build a single self-contained binary that includes both the backend and the frontend, then install it as a systemd service.

**Prerequisites:** Python 3.12+, Node.js 18+, npm

```bash
# Build: compile frontend and package into a single executable
./build.sh

# Install: copy binary, create data dirs, generate config, register systemd service
sudo ./install.sh
```

After installation, MebTTY runs as a managed systemd service. The service starts as root so it can authenticate local users with PAM and drop terminal sessions to the selected user's uid/gid, similar to `sshd` and `login`.

```bash
sudo systemctl start mebtty      # Start the service
sudo systemctl stop mebtty       # Stop the service
sudo systemctl restart mebtty    # Restart the service
sudo systemctl status mebtty     # Check service status
sudo journalctl -u mebtty -f     # View logs
```

| Path                              | Description                          |
| --------------------------------- | ------------------------------------ |
| `/usr/local/bin/mebtty`           | Executable binary                    |
| `/etc/mebtty/mebtty.env`          | Environment config (auto-generated)  |
| `/var/lib/mebtty/mebtty.db`       | SQLite database                      |
| `/var/lib/mebtty/uploads`         | Uploaded files                       |
| `/var/lib/mebtty/plugins`         | Installed third-party plugins        |

```bash
# Uninstall (removes service and binary, keeps data and config)
sudo ./install.sh --uninstall
```

### Arch Linux (AUR)

```bash
yay -S mebtty
sudo systemctl enable --now mebtty
```

The AUR package installs the `mebtty` system service. It does not start the service automatically during package installation.

## Configuration

All settings are configured via environment variables (prefix: `MEBTTY_`):

| Variable                               | Default                                | Description                                  |
| -------------------------------------- | -------------------------------------- | -------------------------------------------- |
| `MEBTTY_SECRET_KEY`                    | Auto-generated                         | JWT signing key. **Set this in production.** |
| `MEBTTY_DATABASE_URL`                  | `sqlite+aiosqlite:///./mebtty.db`      | Database connection string                   |
| `MEBTTY_BROWSE_ROOT`                   | `~` (user home)                        | Root directory for the file browser          |
| `MEBTTY_STATIC_DIR`                    | Auto-detected                          | Path to frontend build output                |
| `MEBTTY_UPLOAD_DIR`                    | `./uploads`                            | Directory for uploaded files and avatars     |
| `MEBTTY_ACCESS_TOKEN_EXPIRE_MINUTES`   | `60`                                   | JWT access token lifetime                    |
| `MEBTTY_REFRESH_TOKEN_EXPIRE_DAYS`     | `7`                                    | JWT refresh token lifetime                   |
| `MEBTTY_MAX_UPLOAD_SIZE`               | `104857600`                            | Max upload size in bytes (100MB)             |
| `MEBTTY_REGISTRATION_ENABLED`          | `true`                                 | Allow creating new MebTTY web accounts       |
| `MEBTTY_HOST`                          | `0.0.0.0`                              | Server bind address                          |
| `MEBTTY_PORT`                          | `18888`                                | Server listen port                           |
| `MEBTTY_ALLOW_ROOT_LOCAL_USER`         | `false`                                | Allow selecting `root` as a local terminal user |
| `MEBTTY_PAM_SERVICE`                   | `login`                                | PAM service used to verify local user passwords |
| `MEBTTY_PLUGIN_DIR`                    | `./plugins`                            | Directory where uploaded plugins are installed |
| `MEBTTY_PLUGIN_MAX_SIZE`               | `20971520`                             | Max `.mtpx` package size and expanded size in bytes |
| `MEBTTY_PLUGIN_INSTALL_ENABLED`        | `true`                                 | Allow installing third-party plugins through API/UI |
| `MEBTTY_PLUGIN_SIGNATURE_REQUIRED`     | `false`                                | Reserved flag for signature enforcement       |
| `MEBTTY_PLUGIN_BACKEND_CODE_ENABLED`   | `false`                                | Reserved flag for trusted backend plugin code |

When installed as a system service, the web application starts as root. When creating a terminal, users enter a local username and password. After PAM authentication succeeds, the terminal process drops privileges to that local user and defaults to that user's home directory when no working directory is provided.

### Production Example

```bash
export MEBTTY_SECRET_KEY="your-random-secret-string"
export MEBTTY_DATABASE_URL="sqlite+aiosqlite:////data/mebtty.db"
sudo -E ./deploy.sh
```

## Project Structure

```text
mebtty/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── config.py            # Settings and environment variables
│   │   ├── database.py          # SQLAlchemy async session factory
│   │   ├── models.py            # Database models (User, Session, etc.)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── auth/                # Authentication module
│   │   │   ├── router.py        #   Login, register, refresh, avatar endpoints
│   │   │   ├── service.py       #   JWT token generation and validation
│   │   │   └── dependencies.py  #   Auth dependency for protected routes
│   │   ├── session/             # Session management module
│   │   │   ├── router.py        #   CRUD endpoints and shell detection
│   │   │   └── service.py       #   Session lifecycle logic
│   │   ├── terminal/            # Terminal runtime module
│   │   │   ├── host_runtime.py  #   PTY process management (pty.fork)
│   │   │   ├── runtime.py       #   Abstract runtime interface
│   │   │   ├── manager.py       #   Session manager and reconnection
│   │   │   ├── ws_handler.py    #   WebSocket handler (binary protocol)
│   │   │   └── router.py        #   WebSocket endpoint registration
│   │   ├── file/                # File management module
│   │   │   └── router.py        #   Browse, upload, download, mkdir, rename, delete
│   │   ├── plugins/             # Plugin manifests, installer, registry, API
│   │   │   ├── builtin.py       #   Built-in plugin registration
│   │   │   ├── installer.py     #   .mtpx upload validation and installation
│   │   │   ├── manager.py       #   Plugin lifecycle helpers
│   │   │   └── router.py        #   Plugin API and asset serving
│   │   ├── settings/            # User settings module
│   │   │   └── router.py        #   Get/update user preferences
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
│   │   │   ├── terminal.js      #   Session and tab state
│   │   │   ├── theme.js         #   Theme mode and accent color
│   │   │   └── settings.js      #   User preferences
│   │   ├── i18n/                # Internationalization
│   │   │   ├── index.js         #   i18n setup and browser locale detection
│   │   │   └── locales/         #   Language files (en-US, zh-CN, zh-TW, ja)
│   │   ├── services/
│   │   │   ├── api.js           #   Axios HTTP client
│   │   │   └── terminal-ws.js   #   WebSocket client (binary protocol)
│   │   ├── components/
│   │   │   ├── layout/          #   UI layout components
│   │   │   │   ├── StatusBar.vue
│   │   │   │   └── SplitPane.vue
│   │   │   ├── terminal/        #   Terminal-specific components
│   │   │   │   ├── TerminalPane.vue   # xterm.js wrapper
│   │   │   │   ├── TerminalTabs.vue   # Multi-tab UI
│   │   │   │   ├── FileBrowser.vue    # Sidebar file explorer
│   │   │   │   └── FileEditorPane.vue # File preview and text editor
│   │   │   ├── plugins/         #   Plugin panel and settings hosts
│   │   │   └── common/
│   │   │       └── ThemeToggle.vue    # Theme mode switcher
│   │   ├── plugins/
│   │   │   └── registry.js      # Frontend plugin runtime
│   │   ├── views/               # Page-level components
│   │   │   ├── LoginView.vue
│   │   │   ├── HomeView.vue
│   │   │   ├── TerminalView.vue
│   │   │   └── SettingsView.vue
│   │   └── styles/
│   │       └── global.css
│   ├── package.json
│   └── vite.config.js
├── build.sh                     # Build standalone executable (PyInstaller)
├── install.sh                   # Install/uninstall systemd service
├── mebtty.service               # systemd unit file
├── pkg/
│   ├── deb/                     # Debian package files
│   │   ├── DEBIAN/              #   DEBIAN metadata (control, postinst, etc.)
│   │   ├── build-deb.sh         #   Local deb build script
│   │   └── README.md
│   └── aur/                     # AUR package files
│       ├── PKGBUILD
│       ├── mebtty.install
│       ├── mebtty.tmpfiles
│       └── README.md
├── docs/
│   ├── plugin-system.md         # Plugin package and frontend API guide
│   └── release.md               # Branch, release, tag, and AUR workflow
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.yml           # Docker Compose configuration
├── deploy.sh                    # One-click deployment script
├── .dockerignore
└── .gitignore
```

## WebSocket Protocol

The terminal uses a custom binary protocol for efficiency:

```text
┌─────────┬────────────┬─────────┐
│ opcode  │  length    │ payload │
│ (1 byte)│ (4 bytes)  │ (N bytes)│
└─────────┴────────────┴─────────┘
```

| Opcode  | Name      | Direction       | Description        |
| ------- | --------- | --------------- | ------------------ |
| `0x01`  | INPUT     | Client → Server | Keyboard input     |
| `0x02`  | OUTPUT    | Server → Client | Terminal output    |
| `0x03`  | RESIZE    | Client → Server | Window size change |
| `0x04`  | HEARTBEAT | Bidirectional   | Keep-alive ping    |
| `0x05`  | CLOSE     | Bidirectional   | Graceful close     |
| `0x06`  | ERROR     | Server → Client | Error message      |
| `0x07`  | CWD       | Server → Client | Current directory  |

## API Reference

### Authentication

| Method | Endpoint                     | Description                        |
| ------ | ---------------------------- | ---------------------------------- |
| POST   | `/api/auth/register`         | Create a new user account          |
| POST   | `/api/auth/login`            | Authenticate and get JWT tokens    |
| POST   | `/api/auth/refresh`          | Refresh access token               |
| GET    | `/api/auth/me`               | Get current user info              |
| POST   | `/api/auth/change-password`  | Change account password            |
| POST   | `/api/auth/avatar`           | Upload avatar image                |
| GET    | `/api/auth/avatar/{filename}`| Serve avatar file                  |

### Sessions

| Method | Endpoint                       | Description                      |
| ------ | ------------------------------ | -------------------------------- |
| GET    | `/api/sessions`                | List all sessions                |
| POST   | `/api/sessions`                | Create a new terminal session    |
| GET    | `/api/sessions/shells`         | List available shells            |
| GET    | `/api/sessions/{id}`           | Get a specific session           |
| POST   | `/api/sessions/{id}/reconnect` | Reconnect to an existing session |
| DELETE | `/api/sessions/{id}`           | Delete a session                 |

### Terminal

| Method    | Endpoint                          | Description                   |
| --------- | --------------------------------- | ----------------------------- |
| WebSocket | `/api/terminal/ws/{session_id}`   | Terminal WebSocket connection |

### Files

| Method | Endpoint                       | Description                      |
| ------ | ------------------------------ | -------------------------------- |
| GET    | `/api/files/browse`            | Browse directory contents        |
| POST   | `/api/files/upload-browse`     | Upload file to a directory       |
| GET    | `/api/files/download-browse`   | Download a file                  |
| GET    | `/api/files/read`              | Read a text file for editing     |
| PUT    | `/api/files/write`             | Save a text file                 |
| POST   | `/api/files/mkdir`             | Create a new directory           |
| POST   | `/api/files/rename`            | Rename a file or directory       |
| POST   | `/api/files/delete`            | Delete a file or directory       |
| POST   | `/api/files/upload`            | Upload file to a session         |
| GET    | `/api/files/download`          | Download from a session          |
| GET    | `/api/files/list`              | List files in a session          |

### Settings

| Method | Endpoint         | Description                  |
| ------ | ---------------- | ---------------------------- |
| GET    | `/api/settings`  | Get user settings            |
| PUT    | `/api/settings`  | Update user settings         |

### Plugins

| Method | Endpoint                                  | Description                              |
| ------ | ----------------------------------------- | ---------------------------------------- |
| GET    | `/api/plugins`                            | List installed built-in and third-party plugins |
| GET    | `/api/plugins/{plugin_id}`                | Get one plugin                           |
| POST   | `/api/plugins/install`                    | Install or update an `.mtpx` package (admin only) |
| POST   | `/api/plugins/{plugin_id}/enable`         | Enable a plugin (admin only)             |
| POST   | `/api/plugins/{plugin_id}/disable`        | Disable a plugin (admin only)            |
| DELETE | `/api/plugins/{plugin_id}`                | Delete a third-party plugin (admin only) |
| GET    | `/api/plugins/{plugin_id}/assets/{path}`  | Serve enabled third-party plugin assets  |

### Audit

| Method | Endpoint                            | Description                         |
| ------ | ----------------------------------- | ----------------------------------- |
| GET    | `/api/audit/commands/{session_id}`  | List commands for a session         |
| GET    | `/api/audit/events`                 | List all audit events (admin only)  |
| GET    | `/api/audit/events/{user_id}`       | List events for a user              |

### Health

| Method | Endpoint        | Description           |
| ------ | --------------- | --------------------- |
| GET    | `/api/health`   | Health check endpoint |

## Development

The repository uses a release-oriented branch model:

- `develop` is the integration branch for ongoing development.
- `master` is reserved for release-ready code and tagged versions.
- Feature branches should branch from `develop` and merge back into `develop`.
- Release tags (`vX.Y.Z` or `vX.Y.Z.dev`) must point to commits reachable from `master`.

```bash
# Terminal 1: Backend with hot reload
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 18888

# Terminal 2: Frontend dev server with API proxy
cd frontend
npm run dev
```

The frontend dev server runs on `http://localhost:3000` and proxies `/api` requests to the backend.

The deployment script also provides a local hot-reload mode:

```bash
./deploy.sh --local-test
```

See [`docs/plugin-system.md`](docs/plugin-system.md) for plugin development and package format details. See [`docs/release.md`](docs/release.md) for the release, tag, package, and AUR publishing workflow.

## Open Source & Third-Party Notices

MebTTY is built on open-source software and includes a small number of bundled assets. The table below lists the major direct dependencies and assets that are relevant to normal use and redistribution. Transitive dependencies are recorded in the lock files and package metadata generated by each ecosystem.

### Backend

| Project | Used for | License |
| ------- | -------- | ------- |
| [FastAPI](https://fastapi.tiangolo.com/) | HTTP API framework | MIT |
| [Uvicorn](https://www.uvicorn.org/) | ASGI server | BSD-3-Clause |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM and database access | MIT |
| [Alembic](https://alembic.sqlalchemy.org/) | Database migrations | MIT |
| [Pydantic](https://docs.pydantic.dev/) / [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Data validation and configuration | MIT |
| [python-jose](https://github.com/mpdavis/python-jose) | JWT handling | MIT |
| [passlib](https://passlib.readthedocs.io/) / [bcrypt](https://github.com/pyca/bcrypt) | Password hashing utilities | BSD / Apache-2.0 |
| [python-multipart](https://github.com/Kludex/python-multipart) | Multipart form parsing and uploads | Apache-2.0 |
| [aiofiles](https://github.com/Tinche/aiofiles) | Async file I/O | Apache-2.0 |
| [websockets](https://websockets.readthedocs.io/) | WebSocket protocol support | BSD-3-Clause |
| [aiosqlite](https://aiosqlite.omnilib.dev/) | Async SQLite access | MIT |
| [redis-py](https://redis.readthedocs.io/) | Redis client support | MIT |

### Frontend

| Project | Used for | License |
| ------- | -------- | ------- |
| [Vue](https://vuejs.org/) | UI framework | MIT |
| [Vue Router](https://router.vuejs.org/) | Client-side routing | MIT |
| [Pinia](https://pinia.vuejs.org/) | Application state management | MIT |
| [vue-i18n](https://vue-i18n.intlify.dev/) | Internationalization | MIT |
| [Axios](https://axios-http.com/) | HTTP client | MIT |
| [xterm.js](https://xtermjs.org/) and addons | Browser terminal emulator | MIT |
| [Split.js](https://split.js.org/) | Resizable split panes | MIT |
| [vscode-icon-resolver](https://github.com/DevYatsu/file-extension-icon) | File icon name resolution | MIT |
| [Vite](https://vite.dev/) / [@vitejs/plugin-vue](https://github.com/vitejs/vite-plugin-vue) | Frontend build tooling | MIT |

### Bundled Assets

| Asset | Used for | License / Notice |
| ----- | -------- | ---------------- |
| Noto Sans | UI font | Apache-2.0, see [`frontend/src/assets/fonts/NotoSans-OFL.txt`](frontend/src/assets/fonts/NotoSans-OFL.txt) |
| JetBrains Mono Nerd Font | Terminal font | SIL Open Font License 1.1, see [`frontend/src/assets/fonts/JetBrainsMonoNLNerdFont-OFL.txt`](frontend/src/assets/fonts/JetBrainsMonoNLNerdFont-OFL.txt) |
| [Catppuccin Icons for VSCode](https://github.com/catppuccin/vscode-icons) | File and folder icons | MIT, bundled SVG assets under [`frontend/public/catppuccin-icons/`](frontend/public/catppuccin-icons/) |

When updating dependencies or replacing bundled assets, keep the corresponding upstream copyright notices and license terms with the distribution.

## License

MebTTY is released under the MIT License. See [`LICENSE`](LICENSE) for the full license text.

Unless otherwise noted, source files authored for this project are licensed under MIT. Third-party dependencies and bundled assets remain under their respective upstream licenses. This section is provided as a practical notice for users and redistributors; it does not replace the original license texts shipped by upstream projects.
