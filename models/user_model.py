import bcrypt

from database.db import get_db


class UserModel:
    @staticmethod
    def create_user(name, email, password, phone_number, is_admin=False):
        db = get_db()
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cursor = db.execute(
            """
            INSERT INTO users (name, email, password, phone_number, is_admin)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), email.strip().lower(), hashed, phone_number.strip(), int(is_admin)),
        )
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def authenticate(email, password):
        user = UserModel.get_by_email(email)
        if not user:
            return None

        valid = bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8"))
        return user if valid else None

    @staticmethod
    def get_by_email(email):
        db = get_db()
        return db.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()

    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    @staticmethod
    def get_all_customers():
        db = get_db()
        return db.execute(
            "SELECT id, name, email, phone_number, created_at FROM users WHERE is_admin = 0 ORDER BY created_at DESC"
        ).fetchall()

    @staticmethod
    def count_customers():
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS cnt FROM users WHERE is_admin = 0").fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def get_all_user_emails():
        db = get_db()
        rows = db.execute("SELECT email FROM users WHERE is_admin = 0").fetchall()
        return [row["email"] for row in rows]
