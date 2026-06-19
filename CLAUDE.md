# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly — a Flask-based expense tracker built as a step-by-step learning project. Many parts are intentionally left as placeholders/stubs for the student to implement in later "steps."

## Commands

- Activate venv: `.\venv\Scripts\Activate.ps1` (PowerShell)
- Run the app: `python app.py` (serves on port 5001, debug mode)
- Run tests: `pytest`
- Run a single test: `pytest path/to/test_file.py::test_name`
- Install deps: `pip install -r requirements.txt`

## Architecture

- `app.py` — single Flask app with all routes. Page routes (`/`, `/register`, `/login`, `/terms`, `/privacy`) render templates from `templates/`. Several routes (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`) are placeholder stubs marked "coming in Step N" — not yet implemented.
- `database/db.py` — currently a stub. Per its header comments, it is meant to provide:
  - `get_db()` — SQLite connection with `row_factory` and foreign keys enabled
  - `init_db()` — creates tables with `CREATE TABLE IF NOT EXISTS`
  - `seed_db()` — inserts sample dev data
- `templates/base.html` — shared layout (nav, footer, font/CSS includes) extended by all pages via Jinja blocks (`title`, `head`, `content`, `scripts`).
- `static/css/landing.css` — single shared stylesheet for all pages (landing, login, register, terms, privacy were merged into this one file).
- `static/js/main.js` — shared client-side JS.

## Notes

- This is a teaching codebase progressing through numbered "Steps" (e.g., Step 1 = database setup, Step 3 = logout, Step 4 = profile, Step 7–9 = expense CRUD). When implementing a stub route, check for references to its step number for intended scope.
