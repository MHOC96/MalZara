from database.db import get_db


class ReviewModel:
    @staticmethod
    def create(order_id, user_id, rating, feedback):
        db = get_db()
        db.execute(
            """
            INSERT OR IGNORE INTO reviews (order_id, user_id, rating, feedback)
            VALUES (?, ?, ?, ?)
            """,
            (order_id, user_id, int(rating), feedback),
        )
        db.commit()

    @staticmethod
    def get_by_order(order_id):
        db = get_db()
        return db.execute(
            "SELECT * FROM reviews WHERE order_id = ?",
            (order_id,),
        ).fetchone()

    @staticmethod
    def get_by_user(user_id):
        db = get_db()
        return db.execute(
            "SELECT * FROM reviews WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    @staticmethod
    def get_all():
        db = get_db()
        return db.execute(
            """
            SELECT r.*, u.name AS customer_name, o.total_amount
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            JOIN orders o ON o.id = r.order_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()
