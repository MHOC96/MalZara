from datetime import datetime

from database.db import get_db


class CartModel:
    @staticmethod
    def get_user_cart(user_id):
        db = get_db()
        return db.execute(
            """
            SELECT c.*, p.name, p.price, p.image_url, p.stock,
                   (c.quantity * p.price) AS item_total
            FROM cart c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ? AND p.is_active = 1
            ORDER BY c.created_at DESC
            """,
            (user_id,),
        ).fetchall()

    @staticmethod
    def add_to_cart(user_id, product_id, quantity, flower_type, bouquet_size, color_theme, card_message):
        db = get_db()
        existing = db.execute(
            """
            SELECT id, quantity FROM cart
            WHERE user_id = ? AND product_id = ?
            AND COALESCE(flower_type, '') = COALESCE(?, '')
            AND COALESCE(bouquet_size, '') = COALESCE(?, '')
            AND COALESCE(color_theme, '') = COALESCE(?, '')
            AND COALESCE(card_message, '') = COALESCE(?, '')
            """,
            (user_id, product_id, flower_type, bouquet_size, color_theme, card_message),
        ).fetchone()

        if existing:
            db.execute(
                "UPDATE cart SET quantity = quantity + ? WHERE id = ?",
                (int(quantity), existing["id"]),
            )
        else:
            db.execute(
                """
                INSERT INTO cart (user_id, product_id, quantity, flower_type, bouquet_size, color_theme, card_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, product_id, int(quantity), flower_type, bouquet_size, color_theme, card_message),
            )
        db.commit()

    @staticmethod
    def update_quantity(cart_item_id, user_id, quantity):
        db = get_db()
        if int(quantity) <= 0:
            CartModel.remove_item(cart_item_id, user_id)
            return

        db.execute(
            "UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?",
            (int(quantity), cart_item_id, user_id),
        )
        db.commit()

    @staticmethod
    def remove_item(cart_item_id, user_id):
        db = get_db()
        db.execute("DELETE FROM cart WHERE id = ? AND user_id = ?", (cart_item_id, user_id))
        db.commit()

    @staticmethod
    def clear_user_cart(user_id):
        db = get_db()
        db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        db.commit()


class OrderModel:
    @staticmethod
    def create_order(user_id, cart_items, payment_method, delivery_address, delivery_date=None, total_amount=None):
        db = get_db()
        subtotal = sum(item["item_total"] for item in cart_items)
        total = float(total_amount) if total_amount is not None else float(subtotal)
        scheduled_delivery_date = delivery_date or datetime.utcnow().date().isoformat()
        order_status = "Pending Delivery Schedule" if delivery_date is None else "Confirmed"
        cursor = db.execute(
            """
            INSERT INTO orders (user_id, total_amount, payment_method, payment_status, delivery_address, delivery_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                total,
                payment_method,
                "Paid (Simulated)",
                delivery_address,
                scheduled_delivery_date,
                order_status,
            ),
        )
        order_id = cursor.lastrowid

        for item in cart_items:
            db.execute(
                """
                INSERT INTO order_items
                (order_id, product_id, quantity, unit_price, flower_type, bouquet_size, color_theme, card_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["price"],
                    item["flower_type"],
                    item["bouquet_size"],
                    item["color_theme"],
                    item["card_message"],
                ),
            )

        db.commit()
        return order_id, total

    @staticmethod
    def update_delivery_date(order_id, delivery_date):
        db = get_db()
        db.execute(
            """
            UPDATE orders
            SET delivery_date = ?, status = ?
            WHERE id = ?
            """,
            (delivery_date, "Confirmed", order_id),
        )
        db.commit()

    @staticmethod
    def get_orders_by_user(user_id):
        db = get_db()
        return db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()

    @staticmethod
    def get_order_items(order_id):
        db = get_db()
        return db.execute(
            """
            SELECT oi.*, p.name AS product_name
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = ?
            """,
            (order_id,),
        ).fetchall()

    @staticmethod
    def get_all_orders_with_users():
        db = get_db()
        return db.execute(
            """
            SELECT o.*, u.name AS customer_name, u.email AS customer_email
            FROM orders o
            JOIN users u ON u.id = o.user_id
            ORDER BY o.created_at DESC
            """
        ).fetchall()
