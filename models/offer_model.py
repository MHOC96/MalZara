from database.db import get_db


class OfferModel:
    @staticmethod
    def create(title, description, discount_percent, product_id, expiry_date, offer_link=None):
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO offers (title, description, discount_percent, product_id, offer_link, expiry_date, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (title, description, float(discount_percent), product_id, offer_link, expiry_date),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def get_active_offers():
        db = get_db()
        return db.execute(
            """
            SELECT o.*, p.name AS product_name
            FROM offers o
            LEFT JOIN products p ON p.id = o.product_id
            WHERE o.is_active = 1 AND o.expiry_date >= CURRENT_DATE
            ORDER BY o.created_at DESC
            """
        ).fetchall()

    @staticmethod
    def get_active_offers_for_product(product_id):
        db = get_db()
        return db.execute(
            """
            SELECT o.*, p.name AS product_name
            FROM offers o
            LEFT JOIN products p ON p.id = o.product_id
            WHERE o.is_active = 1
                            AND o.expiry_date >= CURRENT_DATE
              AND o.product_id = ?
            ORDER BY o.created_at DESC
            """,
            (product_id,),
        ).fetchall()

    @staticmethod
    def get_active_offer_by_id(offer_id):
        db = get_db()
        return db.execute(
            """
            SELECT o.*, p.name AS product_name
            FROM offers o
            LEFT JOIN products p ON p.id = o.product_id
            WHERE o.id = ?
              AND o.is_active = 1
                            AND o.expiry_date >= CURRENT_DATE
            """,
            (offer_id,),
        ).fetchone()

    @staticmethod
    def get_all_offers_admin():
        db = get_db()
        return db.execute(
            """
            SELECT o.*, p.name AS product_name
            FROM offers o
            LEFT JOIN products p ON p.id = o.product_id
            ORDER BY o.created_at DESC
            """
        ).fetchall()

    @staticmethod
    def deactivate(offer_id):
        db = get_db()
        db.execute("UPDATE offers SET is_active = 0 WHERE id = ?", (offer_id,))
        db.commit()
