# Spec: Login and Logout

## Overview
Implements authentication for returning users. The `/login` route gains POST handling: it looks up the user by email, verifies the password against the stored hash, starts a logged-in session, and redirects to the profile page. The `/logout` route is implemented to clear the session and redirect to the landing page. This is Step 3 in the roadmap — it builds directly on the `users` table and session convention (`session["user_id"]`) introduced during registration (Step 2), and is required before profile (Step 4) and expense CRUD (Steps 7–9) can enforce logged-in access.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`, `init_db()`). Already complete.
- Step 2 — Registration (`users` table populated, `session["user_id"]` convention, password hashing with werkzeug). Already complete.

## Routes
- `GET /login` — render the login form — public (already implemented, unchanged)
- `POST /login` — validate credentials, start session, redirect to `/profile` — public
- `GET /logout` — clear the session, redirect to `/` — logged-in (replaces the placeholder stub)

## Database changes
No database changes. The `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already supports lookup-by-email and password verification as defined in `database/db.py`.

## Templates
- **Create:** none
- **Modify:** `templates/login.html` — repopulate the `email` field value on validation failure (markup pattern already used in `register.html`)

## Files to change
- `app.py` — add `POST` method to the `/login` route: read form fields, look up user by email, verify password with `check_password_hash`, set `session["user_id"]` on success, redirect to `/profile`; on failure render `login.html` with a generic error. Replace the `/logout` placeholder stub with a real implementation: clear the session (`session.clear()` or `session.pop("user_id", None)`) and redirect to `/` (`landing`).
- `database/db.py` — add a `get_user_by_email(email)` function that runs a parameterised `SELECT` against the `users` table and returns the row (or `None`)

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash` / `check_password_hash`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use one generic error message ("Invalid email or password.") for both "no such user" and "wrong password" cases — never reveal which one failed
- Store the session key as `user_id`, matching the convention from registration
- `/logout` must work even if no session exists (don't error on an already-logged-out request)

## Definition of done
- [ ] Submitting `/login` with a registered email and correct password sets `session["user_id"]` and redirects to `/profile`
- [ ] Submitting `/login` with an unregistered email shows "Invalid email or password." and does not set a session
- [ ] Submitting `/login` with a registered email but wrong password shows "Invalid email or password." and does not set a session
- [ ] Re-submitting after a failed login keeps the previously entered email in the form field
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`
- [ ] Visiting `/logout` while already logged out redirects to `/` without raising an error
- [ ] App starts and existing routes (`/`, `/register`, `/terms`, `/privacy`) are unaffected
