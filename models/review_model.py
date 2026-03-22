from database.db import get_db


class ReviewModel:
    @staticmethod
    def create(order_id, user_id, rating, feedback, product_id=None):
        db = get_db()
        db.execute(
            """
            INSERT OR IGNORE INTO reviews (order_id, user_id, rating, feedback, product_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, user_id, int(rating), feedback, product_id),
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
            """
            SELECT r.*, u.name AS customer_name, p.name AS product_name
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            LEFT JOIN products p ON p.id = r.product_id
            WHERE r.user_id = ?
            ORDER BY r.created_at DESC
            """,
            (user_id,),
        ).fetchall()

    @staticmethod
    def get_by_product(product_id):
        db = get_db()
        return db.execute(
            """
            SELECT r.*, u.name AS customer_name
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            WHERE r.product_id = ?
            ORDER BY r.created_at DESC
            """,
            (product_id,),
        ).fetchall()

    @staticmethod
    def get_all():
        db = get_db()
        return db.execute(
            """
            SELECT r.*, u.name AS customer_name, o.total_amount,
                   p.name AS product_name
            FROM reviews r
            JOIN users u ON u.id = r.user_id
            JOIN orders o ON o.id = r.order_id
            LEFT JOIN products p ON p.id = r.product_id
            ORDER BY r.created_at DESC
            """
        ).fetchall()

    @staticmethod
    def delete(review_id):
        db = get_db()
        db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        db.commit()
