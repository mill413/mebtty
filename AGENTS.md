# Repository Guidelines

## Project Structure & Module Organization

WebTTY is a self-hosted web terminal platform with a Python backend and a Vue 3 frontend.

- `backend/` — FastAPI application (Python 3.12+)
  - `app/main.py` — Application entry point and route definitions
  - `app/models.py` — SQLAlchemy ORM models
  - `app/schemas.py` — Pydantic request/response schemas
  - `app/config.py` — Settings via pydantic-settings (reads `.env`)
  - `app/database.py` — Async database session and engine setup
  - `requirements.txt` — Pinned dependencies
- `frontend/` — Vue 3 SPA (Vite)
  - `src/` — Application source (components, views, router, stores, i18n)
  - `index.html` — Entry HTML
  - `vite.config.js` — Vite configuration
- `docker-compose.yml` / `Dockerfile` — Container deployment
- `deploy.sh` — Production deployment script
- `.env` — Local environment variables (do not commit)

## Build, Test, and Development Commands

**Frontend** (run from `frontend/`):
- `npm install` — Install dependencies
- `npm run dev` — Start Vite dev server with HMR
- `npm run build` — Build production bundle to `frontend/dist/`
- `npm run preview` — Preview the production build locally

**Backend** (run from `backend/`, with venv activated):
- `pip install -r requirements.txt` — Install Python dependencies
- `uvicorn app.main:app --reload --port 8000` — Run the dev server with auto-reload

**Docker**:
- `docker compose up --build` — Build and run the full stack on port `8000`

## Coding Style & Naming Conventions

- **Python**: Follow PEP 8. Use 4-space indentation. Models and schemas use `snake_case`; classes use `PascalCase`.
- **Vue/JS**: Use 2-space indentation. Components use `PascalCase` filenames (`TerminalView.vue`); composables and stores use `camelCase`.
- Prefer async/await in FastAPI route handlers and SQLAlchemy queries.
- Keep `.env` out of version control; define all config keys in `backend/app/config.py`.

## Commit & Pull Request Guidelines

Commit messages follow the Conventional Commits format:
- `feat: add dynamic shell detection with brand SVG icons`
- `fix: prevent session deletion from redirecting`
- `refactor: unify new terminal button behavior`
- `docs: fix markdownlint warnings in README files`

Format: `<type>(<optional scope>): <short summary>`

Pull requests should include a description of changes, linked issues, and screenshots for UI-related work.

## Architecture Overview

The frontend communicates with the backend over HTTP (REST) and WebSocket. Terminal sessions use a custom binary WebSocket protocol for low-latency PTY I/O. Session state persists in SQLite (`backend/data/webtty.db`). Internationalization is handled by `vue-i18n` with browser locale auto-detection.
