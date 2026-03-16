from datetime import date, timedelta

from database.db import get_db


class SubscriptionModel:
    PLAN_DURATIONS = {
        "monthly": 30,
        "yearly": 365,
    }
    PLAN_PRICES = {
        "monthly": 9.99,
        "yearly": 89.99,
    }

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        return db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    @staticmethod
    def subscribe(user_id, plan):
        db = get_db()
        today = date.today()
        days = SubscriptionModel.PLAN_DURATIONS.get(plan, 30)
        end = today + timedelta(days=days)

        existing = SubscriptionModel.get_by_user(user_id)
        if existing:
            # Reactivate / upgrade existing row
            db.execute(
                """
                UPDATE subscriptions
                SET plan = ?, status = 'active', start_date = ?, end_date = ?
                WHERE user_id = ?
                """,
                (plan, today.isoformat(), end.isoformat(), user_id),
            )
        else:
            db.execute(
                """
                INSERT INTO subscriptions (user_id, plan, status, start_date, end_date)
                VALUES (?, ?, 'active', ?, ?)
                """,
                (user_id, plan, today.isoformat(), end.isoformat()),
            )
        db.commit()

    @staticmethod
    def cancel(user_id):
        db = get_db()
        db.execute(
            "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = ?",
            (user_id,),
        )
        db.commit()

    @staticmethod
    def is_active(user_id):
        sub = SubscriptionModel.get_by_user(user_id)
        if not sub:
            return False
        return sub["status"] == "active" and sub["end_date"] >= date.today().isoformat()

    @staticmethod
    def get_all():
        db = get_db()
        return db.execute(
            """
            SELECT s.*, u.name AS customer_name, u.email AS customer_email
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            ORDER BY s.created_at DESC
            """
        ).fetchall()

    @staticmethod
    def get_expiring_soon(days=3):
        """Return active subscriptions expiring within `days` days (not yet expired)."""
        db = get_db()
        today = date.today()
        cutoff = (today + timedelta(days=days)).isoformat()
        today_iso = today.isoformat()
        return db.execute(
            """
            SELECT s.*, u.name AS customer_name, u.email AS customer_email
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.status = 'active'
              AND s.end_date >= ?
              AND s.end_date <= ?
            ORDER BY s.end_date
            """,
            (today_iso, cutoff),
        ).fetchall()

    @staticmethod
    def auto_renew():
        """
        Automatically renew subscriptions that have expired.
        Returns a dict with counts: renewed, skipped.
        """
        db = get_db()
        today = date.today()
        today_iso = today.isoformat()

        # Find expired-but-active subscriptions
        expired = db.execute(
            """
            SELECT * FROM subscriptions
            WHERE status = 'active' AND end_date < ?
            """,
            (today_iso,),
        ).fetchall()

        renewed = 0
        for sub in expired:
            plan = sub["plan"]
            days = SubscriptionModel.PLAN_DURATIONS.get(plan, 30)
            new_end = today + timedelta(days=days)
            db.execute(
                """
                UPDATE subscriptions
                SET start_date = ?, end_date = ?, status = 'active'
                WHERE id = ?
                """,
                (today_iso, new_end.isoformat(), sub["id"]),
            )
            renewed += 1

        db.commit()
        return {"renewed": renewed, "skipped": len(expired) - renewed}
