# Spec: Registration

## Overview
Implements user registration so a visitor can create a Spendly account. The `/register` route gains POST handling: it validates input, hashes the password with werkzeug, inserts a new row into the `users` table via `database/db.py`, starts a logged-in session, and redirects to the profile page. This is the first authentication step in the roadmap — it lays the groundwork for login (Step 3 area) and the session-based access checks that later steps (profile, expense CRUD) will depend on.

## Depends on
Step 1 — Database setup (`users` table, `get_db()`, `init_db()`). Already complete.

## Routes
- `GET /register` — render the registration form — public (already implemented, unchanged)
- `POST /register` — validate form data, create the user, log them in, redirect to `/profile` — public

## Database changes
No database changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already supports registration as defined in `database/db.py`.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — render `{{ error }}` for validation/duplicate-email failures (markup already present); repopulate `name`/`email` field values on validation failure so the user doesn't retype everything

## Files to change
- `app.py` — add `app.secret_key` (required for Flask sessions), add `POST` method handling to the `/register` route: read form fields, validate, check for duplicate email, hash password, insert user, set `session["user_id"]`, redirect to `/profile`
- `database/db.py` — no functional changes expected; reuse `get_db()`

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate: name not blank, email not blank and well-formed, password minimum 8 characters
- Catch the `UNIQUE` constraint violation on `email` (`sqlite3.IntegrityError`) and show "An account with this email already exists." rather than crashing
- Store the session key as `user_id` so later steps (logout, profile) can rely on the same convention

## Definition of done
- [ ] Submitting the registration form with valid, unique data creates a row in `users` with a hashed (not plaintext) password
- [ ] After successful registration, the session contains the new `user_id` and the browser is redirected to `/profile`
- [ ] Submitting with an email that already exists shows the auth-error banner and does not create a duplicate row
- [ ] Submitting with a blank name, invalid email, or password under 8 characters shows the auth-error banner and does not insert a row
- [ ] Re-submitting after a validation error keeps the previously entered name/email in the form fields
- [ ] App starts and existing routes (`/`, `/login`, `/terms`, `/privacy`) are unaffected