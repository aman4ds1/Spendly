from datetime import datetime
from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    member_since = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")
    initials = "".join(p[0].upper() for p in row["name"].split() if p)[:2]
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": member_since,
        "initials": initials,
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    conditions = ["user_id = ?"]
    params = [user_id]
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    where = " WHERE " + " AND ".join(conditions)

    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count"
        " FROM expenses" + where,
        params,
    ).fetchone()
    top = conn.execute(
        "SELECT category FROM expenses" + where
        + " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        params,
    ).fetchone()
    conn.close()
    return {
        "total_spent": row["total_spent"],
        "transaction_count": row["transaction_count"],
        "top_category": top["category"] if top else "—",
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conditions = ["user_id = ?"]
    params = [user_id]
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    where = " WHERE " + " AND ".join(conditions)

    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount FROM expenses"
        + where + " ORDER BY date DESC LIMIT ?",
        params + [limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conditions = ["user_id = ?"]
    params = [user_id]
    if date_from:
        conditions.append("date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        params.append(date_to)
    where = " WHERE " + " AND ".join(conditions)

    conn = get_db()
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS amount FROM expenses"
        + where + " GROUP BY category ORDER BY SUM(amount) DESC",
        params,
    ).fetchall()
    conn.close()
    if not rows:
        return []
    total = sum(r["amount"] for r in rows)
    result = []
    running = 0
    for i, r in enumerate(rows):
        if i < len(rows) - 1:
            pct = round(r["amount"] / total * 100) if total else 0
        else:
            pct = 100 - running
        running += pct
        result.append({
            "name": r["name"],
            "amount": r["amount"],
            "percent": pct,
            "slug": r["name"].lower(),
        })
    return result
