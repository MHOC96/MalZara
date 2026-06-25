from database.db import get_db, is_postgres


class SpecialDayModel:
    @staticmethod
    def create(user_id, event_name, person_name, event_date, preferred_flower_package):
        db = get_db()
        db.execute(
            """
            INSERT INTO special_days (user_id, event_name, person_name, event_date, preferred_flower_package)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, event_name, person_name, event_date, preferred_flower_package),
        )
        db.commit()

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        return db.execute(
            """
            SELECT s.*, p.name AS preferred_product_name
            FROM special_days s
            LEFT JOIN products p ON p.id = s.preferred_flower_package
            WHERE s.user_id = ?
            ORDER BY s.event_date ASC
            """,
            (user_id,),
        ).fetchall()

    @staticmethod
    def get_all_with_users():
        db = get_db()
        return db.execute(
            """
            SELECT s.*, u.name AS customer_name, u.email AS customer_email, p.name AS preferred_product_name
            FROM special_days s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN products p ON p.id = s.preferred_flower_package
            ORDER BY s.event_date ASC
            """
        ).fetchall()

    @staticmethod
    def count_all():
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS cnt FROM special_days").fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def get_events_by_date(event_date):
        db = get_db()
        return db.execute(
            """
            SELECT s.*, p.name AS preferred_product_name
            FROM special_days s
            LEFT JOIN products p ON p.id = s.preferred_flower_package
            WHERE s.event_date = ?
            """,
            (event_date,),
        ).fetchall()

    @staticmethod
    def get_upcoming_events_within_days(days=7):
        db = get_db()
        if is_postgres():
            return db.execute(
                """
                SELECT s.*, p.name AS preferred_product_name,
                       (s.event_date - CURRENT_DATE) AS days_until_event
                FROM special_days s
                LEFT JOIN products p ON p.id = s.preferred_flower_package
                WHERE s.event_date > CURRENT_DATE
                  AND s.event_date <= (CURRENT_DATE + (%s * INTERVAL '1 day'))
                ORDER BY s.event_date ASC
                """,
                (int(days),),
            ).fetchall()

        return db.execute(
            """
            SELECT s.*, p.name AS preferred_product_name,
                   CAST(julianday(s.event_date) - julianday(date('now')) AS INTEGER) AS days_until_event
            FROM special_days s
            LEFT JOIN products p ON p.id = s.preferred_flower_package
            WHERE date(s.event_date) > date('now')
              AND date(s.event_date) <= date('now', ?)
            ORDER BY s.event_date ASC
            """,
            (f"+{int(days)} days",),
        ).fetchall()
