# Spec: Add Expense

## Overview
This step implements the "Add Expense" feature, replacing the placeholder stub at `GET /expenses/add` with a fully working form that lets logged-in users record a new expense. The form collects amount, category, date, and an optional description, then inserts the record into the `expenses` table. On success the user is redirected to their profile page where the new expense appears immediately.

## Depends on
- Step 01 — Database setup (`expenses` table exists)
- Step 04/05 — Profile page (redirect destination after add)
- Step 03 — Login/logout (session-based auth guard)

## Routes
- `GET  /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the expense, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The existing `expenses` table already has all required columns: `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates
- **Create:** `templates/expenses/add.html` — form page extending `base.html`
- **Modify:** none

## Files to change
- `app.py` — replace the stub `add_expense` route with GET+POST implementation
- `database/db.py` — add `add_expense(user_id, amount, category, date, description)` helper

## Files to create
- `templates/expenses/add.html` — the add-expense form template

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQLite via `get_db()`
- Parameterised queries only — never string-format user input into SQL
- Passwords hashed with werkzeug (keep existing auth intact)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard: redirect to `/login` if `user_id` not in session
- Amount must be a positive number (validate server-side; show inline error on failure)
- Date must be a valid `YYYY-MM-DD` string; default to today if blank
- Category must be one of the fixed list: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Description is optional (max 200 chars)
- On validation failure re-render the form with the user's input preserved and an error message
- On success flash a confirmation message and redirect to `/profile`

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders a form with fields: amount, category (dropdown), date, description
- [ ] Submitting the form with valid data inserts a row in `expenses` and redirects to `/profile`
- [ ] The new expense appears in the transactions list on the profile page
- [ ] Submitting with a missing or non-positive amount re-renders the form with an error
- [ ] Submitting with an invalid date re-renders the form with an error
- [ ] All previously entered field values are preserved on validation failure
