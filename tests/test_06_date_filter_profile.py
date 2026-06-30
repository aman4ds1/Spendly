"""
Tests for Step 6: Date Filter for Profile Page
- GET /profile accepts optional date_from / date_to query params (YYYY-MM-DD)
- Absent or malformed params fall back to unfiltered "All Time" view silently
- date_from > date_to: flashes error, falls back to unfiltered
- All three data sections (summary stats, recent transactions, category breakdown)
  respect the active date filter
- Auth guard: unauthenticated requests redirect to /login
"""

import pytest
from werkzeug.security import generate_password_hash
import database.db as db_module
from database.db import init_db, get_db, create_user
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)
from app import app as flask_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path, monkeypatch):
    """Isolated Flask app with a per-test temporary SQLite database."""
    db_file = str(tmp_path / "test_spendly.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    })
    with flask_app.app_context():
        init_db()
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Test client that is already registered and logged in."""
    resp = client.post("/register", data={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    }, follow_redirects=False)
    # If register redirects to profile, we are logged in. If it returned 200
    # (e.g. already exists), attempt login.
    if resp.status_code not in (301, 302):
        client.post("/login", data={
            "email": "test@example.com",
            "password": "password123",
        })
    return client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id():
    """Return the id of the first user in the test DB."""
    conn = get_db()
    row = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
    conn.close()
    return row["id"]


def _insert_expense(user_id, amount, category, date_str, description="expense"):
    """Insert a single expense directly into the test DB."""
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date_str, description),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auth Guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_unauthenticated_get_redirects_to_login(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 302, "Expected redirect for unauthenticated request"
        assert "/login" in resp.headers["Location"], (
            "Unauthenticated /profile should redirect to /login"
        )

    def test_unauthenticated_get_with_date_params_redirects_to_login(self, client):
        resp = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        assert resp.status_code == 302, "Expected redirect even when date params supplied"
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# Happy Path — No Params (Unfiltered / All Time)
# ---------------------------------------------------------------------------

class TestNoParams:
    def test_no_params_returns_200(self, auth_client):
        resp = auth_client.get("/profile")
        assert resp.status_code == 200, "Logged-in GET /profile should return 200"

    def test_no_params_renders_profile_page(self, auth_client):
        resp = auth_client.get("/profile")
        assert b"profile" in resp.data.lower(), (
            "Response should contain profile-related content"
        )

    def test_no_params_shows_rupee_symbol(self, auth_client):
        resp = auth_client.get("/profile")
        # ₹ encoded as UTF-8 bytes
        assert "₹".encode() in resp.data, (
            "Profile page should always display the ₹ symbol"
        )

    def test_no_params_zero_expenses_shows_zero_total(self, auth_client):
        """A user with no expenses sees ₹0 total, not an error."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        assert b"0" in resp.data, "Zero-expense user should see 0 amounts"


# ---------------------------------------------------------------------------
# Happy Path — Valid Date Range Filters Data
# ---------------------------------------------------------------------------

class TestValidDateRange:
    def test_valid_range_returns_200(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 50.00, "Food", "2025-06-15", "in range")
            _insert_expense(uid, 200.00, "Bills", "2025-01-01", "out of range")

        resp = auth_client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        assert resp.status_code == 200, "Valid date range should return 200"

    def test_valid_range_includes_in_range_expense(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 75.00, "Food", "2025-06-15", "lunch")

        resp = auth_client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        assert b"75" in resp.data, (
            "In-range expense amount should appear in filtered response"
        )

    def test_valid_range_excludes_out_of_range_expense(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 75.00, "Food", "2025-06-15", "in range lunch")
            _insert_expense(uid, 9999.00, "Bills", "2024-01-01", "old bill")

        resp = auth_client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        assert b"9999" not in resp.data, (
            "Out-of-range expense should not appear in filtered response"
        )

    def test_valid_range_shows_rupee_symbol(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 50.00, "Food", "2025-06-15")

        resp = auth_client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        assert "₹".encode() in resp.data, (
            "₹ symbol must appear regardless of active date filter"
        )

    def test_only_date_from_provided_does_not_crash(self, auth_client):
        resp = auth_client.get("/profile?date_from=2025-01-01")
        assert resp.status_code == 200, "Only date_from provided should not crash"

    def test_only_date_to_provided_does_not_crash(self, auth_client):
        resp = auth_client.get("/profile?date_to=2025-12-31")
        assert resp.status_code == 200, "Only date_to provided should not crash"

    def test_boundary_dates_inclusive(self, auth_client, app):
        """Expenses on the exact boundary dates must be included."""
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 11.00, "Food", "2025-06-01", "boundary start")
            _insert_expense(uid, 22.00, "Food", "2025-06-30", "boundary end")

        resp = auth_client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        assert b"11" in resp.data, "Expense on date_from boundary should be included"
        assert b"22" in resp.data, "Expense on date_to boundary should be included"


# ---------------------------------------------------------------------------
# Edge — Malformed Date Strings
# ---------------------------------------------------------------------------

class TestMalformedDates:
    @pytest.mark.parametrize("params", [
        "date_from=not-a-date",
        "date_to=not-a-date",
        "date_from=not-a-date&date_to=also-bad",
        "date_from=13-2025-01",       # wrong order
        "date_from=2025/06/01",       # wrong separator
        "date_from=2025-13-01",       # invalid month
        "date_from=",                 # empty string
        "date_from=2025-06-01&date_to=not-a-date",
    ])
    def test_malformed_date_does_not_crash(self, auth_client, params):
        resp = auth_client.get(f"/profile?{params}")
        assert resp.status_code == 200, (
            f"Malformed date params '{params}' should not crash the app — "
            f"expected 200, got {resp.status_code}"
        )

    def test_malformed_date_from_falls_back_to_unfiltered(self, auth_client, app):
        """With a bad date_from, all expenses (no filter) should be shown."""
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 88.00, "Food", "2024-03-15", "old expense")

        resp = auth_client.get("/profile?date_from=not-a-date")
        assert b"88" in resp.data, (
            "When date_from is malformed the view should fall back to unfiltered "
            "and show all expenses"
        )

    def test_malformed_date_to_falls_back_to_unfiltered(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 77.00, "Food", "2024-03-15", "old expense")

        resp = auth_client.get("/profile?date_to=not-a-date")
        assert b"77" in resp.data, (
            "When date_to is malformed the view should fall back to unfiltered"
        )


# ---------------------------------------------------------------------------
# Edge — date_from > date_to
# ---------------------------------------------------------------------------

class TestDateRangeInverted:
    def test_inverted_range_returns_200(self, auth_client):
        resp = auth_client.get(
            "/profile?date_from=2025-12-31&date_to=2025-01-01",
            follow_redirects=True,
        )
        assert resp.status_code == 200, (
            "Inverted date range should return 200 (not crash)"
        )

    def test_inverted_range_flashes_error_message(self, auth_client):
        resp = auth_client.get(
            "/profile?date_from=2025-12-31&date_to=2025-01-01",
            follow_redirects=True,
        )
        # The spec requires a visible flash error about the date order.
        # Check for a fragment that works regardless of exact wording.
        data_lower = resp.data.lower()
        assert b"date" in data_lower, (
            "Inverted date range should flash an error message mentioning 'date'"
        )
        # Must contain an indication that start/end order is wrong
        assert b"before" in data_lower or b"after" in data_lower or b"cannot" in data_lower, (
            "Flash error should communicate that start must be before end"
        )

    def test_inverted_range_shows_unfiltered_data(self, auth_client, app):
        """When range is inverted, fall back shows ALL expenses (no filter applied)."""
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 55.00, "Food", "2024-03-15", "any expense")

        resp = auth_client.get(
            "/profile?date_from=2025-12-31&date_to=2025-01-01",
            follow_redirects=True,
        )
        assert b"55" in resp.data, (
            "Inverted range falls back to unfiltered so all expenses should appear"
        )

    def test_equal_dates_do_not_trigger_error(self, auth_client):
        """date_from == date_to is a valid single-day range, not an error."""
        resp = auth_client.get(
            "/profile?date_from=2025-06-15&date_to=2025-06-15",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Should NOT flash the order error for equal dates
        data_lower = resp.data.lower()
        # We verify by ensuring the page still renders normally (no 500)
        assert b"profile" in data_lower or "₹".encode() in resp.data


# ---------------------------------------------------------------------------
# Edge — Zero Expenses in Filtered Range
# ---------------------------------------------------------------------------

class TestZeroExpensesInRange:
    def test_no_expenses_in_range_returns_200(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            # Insert expense outside the queried range
            _insert_expense(uid, 100.00, "Bills", "2024-01-01", "old bill")

        resp = auth_client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert resp.status_code == 200, (
            "User with no expenses in range should see 200, not an error"
        )

    def test_no_expenses_in_range_shows_zero_total(self, auth_client, app):
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 100.00, "Bills", "2024-01-01", "old bill")

        resp = auth_client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert b"0" in resp.data, (
            "Zero expenses in range should show 0 amounts, not crash"
        )

    def test_no_expenses_at_all_with_filter_returns_200(self, auth_client):
        """User with zero total expenses (not just filtered) sees no error."""
        resp = auth_client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# "All Time" Preset — Clean URL Behavior
# ---------------------------------------------------------------------------

class TestAllTimePreset:
    def test_clean_url_returns_200(self, auth_client):
        """The clean /profile URL (no query params) is the All Time view."""
        resp = auth_client.get("/profile")
        assert resp.status_code == 200

    def test_all_time_url_has_no_date_params(self, auth_client):
        """The All Time URL must not include date_from or date_to query params."""
        # This verifies the spec rule: "All Time preset passes no query params"
        # The clean URL is simply /profile
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        # The page should indicate "all time" state is active (rendered as active preset)
        # We look for the all-time or no date restriction wording
        assert b"profile" in resp.data.lower()

    def test_all_time_shows_all_expenses(self, auth_client, app):
        """With no date params, all expenses regardless of date appear."""
        with app.app_context():
            uid = _get_user_id()
            _insert_expense(uid, 111.00, "Food", "2020-01-01", "very old")
            _insert_expense(uid, 222.00, "Bills", "2030-12-31", "far future")

        resp = auth_client.get("/profile")
        assert b"111" in resp.data, "All Time view should include very old expenses"
        assert b"222" in resp.data, "All Time view should include future-dated expenses"


# ---------------------------------------------------------------------------
# Query Helper Unit Tests
# ---------------------------------------------------------------------------

class TestQueryHelpers:
    """Directly test that get_summary_stats, get_recent_transactions, and
    get_category_breakdown correctly filter by date_from / date_to."""

    def setup_method(self, method):
        """Create a user so _get_user_id() has a row to find."""
        from app import app as flask_app
        with flask_app.app_context():
            create_user("Test User", "test@example.com",
                        generate_password_hash("password123"))

    def _setup_expenses(self, user_id):
        """Insert three expenses at distinct dates."""
        _insert_expense(user_id, 10.00, "Food",  "2025-03-01", "march")
        _insert_expense(user_id, 20.00, "Food",  "2025-06-15", "june")
        _insert_expense(user_id, 30.00, "Bills", "2025-09-30", "sept")

    # --- get_summary_stats ---

    def test_summary_stats_no_filter_counts_all(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            stats = get_summary_stats(uid)
            assert stats["transaction_count"] == 3
            assert abs(stats["total_spent"] - 60.00) < 0.01

    def test_summary_stats_date_range_filters_correctly(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            stats = get_summary_stats(uid, date_from="2025-05-01", date_to="2025-07-31")
            assert stats["transaction_count"] == 1, (
                "Only the June expense falls in May-July range"
            )
            assert abs(stats["total_spent"] - 20.00) < 0.01

    def test_summary_stats_no_results_returns_zero(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            stats = get_summary_stats(uid, date_from="2030-01-01", date_to="2030-12-31")
            assert stats["transaction_count"] == 0
            assert stats["total_spent"] == 0

    def test_summary_stats_only_date_from(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            stats = get_summary_stats(uid, date_from="2025-06-01")
            # June + September expenses
            assert stats["transaction_count"] == 2

    def test_summary_stats_only_date_to(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            stats = get_summary_stats(uid, date_to="2025-06-30")
            # March + June expenses
            assert stats["transaction_count"] == 2

    # --- get_recent_transactions ---

    def test_recent_transactions_no_filter_returns_all(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            txns = get_recent_transactions(uid)
            assert len(txns) == 3

    def test_recent_transactions_date_range_filters_correctly(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            txns = get_recent_transactions(uid, date_from="2025-05-01", date_to="2025-07-31")
            assert len(txns) == 1, "Only June expense in May-July range"
            assert txns[0]["amount"] == 20.00

    def test_recent_transactions_empty_range_returns_empty_list(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            txns = get_recent_transactions(uid, date_from="2030-01-01", date_to="2030-12-31")
            assert txns == [], "No expenses in future range should return empty list"

    def test_recent_transactions_ordered_by_date_desc(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            txns = get_recent_transactions(uid)
            dates = [t["date"] for t in txns]
            assert dates == sorted(dates, reverse=True), (
                "Transactions should be ordered newest first"
            )

    def test_recent_transactions_only_date_from(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            txns = get_recent_transactions(uid, date_from="2025-06-01")
            assert len(txns) == 2, "June + September when date_from=2025-06-01"

    def test_recent_transactions_only_date_to(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            txns = get_recent_transactions(uid, date_to="2025-06-30")
            assert len(txns) == 2, "March + June when date_to=2025-06-30"

    # --- get_category_breakdown ---

    def test_category_breakdown_no_filter_includes_all(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            cats = get_category_breakdown(uid)
            names = [c["name"] for c in cats]
            assert "Food" in names
            assert "Bills" in names

    def test_category_breakdown_date_range_filters_correctly(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            # Only September expense (Bills) is in the range
            cats = get_category_breakdown(uid, date_from="2025-09-01", date_to="2025-09-30")
            assert len(cats) == 1, "Only Bills category in September range"
            assert cats[0]["name"] == "Bills"
            assert abs(cats[0]["amount"] - 30.00) < 0.01

    def test_category_breakdown_empty_range_returns_empty_list(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            cats = get_category_breakdown(uid, date_from="2030-01-01", date_to="2030-12-31")
            assert cats == [], "No expenses in range should return empty list"

    def test_category_breakdown_percentages_sum_to_100(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            cats = get_category_breakdown(uid)
            total_pct = sum(c["percent"] for c in cats)
            assert total_pct == 100, (
                f"Category percentages should sum to 100, got {total_pct}"
            )

    def test_category_breakdown_percentages_sum_to_100_with_filter(self, app):
        with app.app_context():
            uid = _get_user_id()
            # Multiple categories in range
            _insert_expense(uid, 40.00, "Food", "2025-06-01")
            _insert_expense(uid, 60.00, "Bills", "2025-06-15")
            cats = get_category_breakdown(uid, date_from="2025-06-01", date_to="2025-06-30")
            total_pct = sum(c["percent"] for c in cats)
            assert total_pct == 100, (
                f"Filtered category percentages should sum to 100, got {total_pct}"
            )

    def test_category_breakdown_only_date_from(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            cats = get_category_breakdown(uid, date_from="2025-09-01")
            assert len(cats) == 1
            assert cats[0]["name"] == "Bills"

    def test_category_breakdown_only_date_to(self, app):
        with app.app_context():
            uid = _get_user_id()
            self._setup_expenses(uid)
            cats = get_category_breakdown(uid, date_to="2025-03-31")
            assert len(cats) == 1
            assert cats[0]["name"] == "Food"
