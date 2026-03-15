from database.db import get_db


class ProductModel:
    @staticmethod
    def get_all(category=None, include_inactive=False):
        db = get_db()
        query = "SELECT * FROM products"
        clauses = []
        params = []

        if not include_inactive:
            clauses.append("is_active = 1")
        if category:
            clauses.append("category = ?")
            params.append(category)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY created_at DESC, id DESC"
        return db.execute(query, tuple(params)).fetchall()

    @staticmethod
    def get_by_id(product_id):
        db = get_db()
        return db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    @staticmethod
    def create(name, category, description, price, image_url, stock):
        db = get_db()
        cursor = db.execute(
            """
            INSERT INTO products (name, category, description, price, image_url, stock)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, float(price), image_url, int(stock)),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(product_id, name, category, description, price, image_url, stock, is_active):
        db = get_db()
        db.execute(
            """
            UPDATE products
            SET name = ?, category = ?, description = ?, price = ?, image_url = ?, stock = ?, is_active = ?
            WHERE id = ?
            """,
            (name, category, description, float(price), image_url, int(stock), int(is_active), product_id),
        )
        db.commit()

    @staticmethod
    def delete(product_id):
        db = get_db()
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
        db.commit()

    @staticmethod
    def get_categories():
        db = get_db()
        rows = db.execute("SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category").fetchall()
        return [row["category"] for row in rows]
