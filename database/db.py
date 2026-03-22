import os
import sqlite3
from pathlib import Path

from flask import g


BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_db_path(db_url: str) -> str:
    if os.path.isabs(db_url):
        return db_url
    return str(BASE_DIR / db_url)


def get_db():
    if "db" not in g:
        from flask import current_app

        db_path = _resolve_db_path(current_app.config["DATABASE_URL"])
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    schema_path = BASE_DIR / "database" / "schema.sql"
    with app.app_context():
        db = get_db()
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            db.executescript(schema_file.read())

        _ensure_offers_offer_link_column(db)
        _ensure_reviews_product_id_column(db)

        from models.user_model import UserModel

        if not UserModel.get_by_email("admin@malzara.com"):
            UserModel.create_user(
                name="MalZara Admin",
                email="admin@malzara.com",
                password="Admin@123",
                phone_number="0000000000",
                is_admin=True,
            )

        db.commit()


def _ensure_offers_offer_link_column(db):
    columns = db.execute("PRAGMA table_info(offers)").fetchall()
    column_names = {column[1] for column in columns}
    if "offer_link" not in column_names:
        db.execute("ALTER TABLE offers ADD COLUMN offer_link TEXT")


def _ensure_reviews_product_id_column(db):
    columns = db.execute("PRAGMA table_info(reviews)").fetchall()
    if not columns:
        return  # table doesn't exist yet, schema.sql will create it
    column_names = {column[1] for column in columns}
    if "product_id" not in column_names:
        db.execute("ALTER TABLE reviews ADD COLUMN product_id INTEGER REFERENCES products(id) ON DELETE SET NULL")

