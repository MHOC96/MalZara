import os
import re
import sqlite3
import importlib
from pathlib import Path

from flask import g

try:
    psycopg = importlib.import_module("psycopg")
    dict_row = importlib.import_module("psycopg.rows").dict_row
except ImportError:  # pragma: no cover - available in deployment once requirements are installed
    psycopg = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parent.parent


class CompatCursor:
    def __init__(self, cursor, backend: str, generated_returning: bool = False):
        self._cursor = cursor
        self._backend = backend
        self._generated_returning = generated_returning
        self._cached_lastrowid = None

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        if self._backend == "sqlite":
            return self._cursor.lastrowid

        if not self._generated_returning:
            return None

        if self._cached_lastrowid is not None:
            return self._cached_lastrowid

        row = self._cursor.fetchone()
        if row is None:
            return None

        self._cached_lastrowid = row["id"] if isinstance(row, dict) else row[0]
        return self._cached_lastrowid


class CompatConnection:
    def __init__(self, connection, backend: str):
        self._connection = connection
        self._backend = backend

    def execute(self, query, params=()):
        translated_query, generated_returning = _translate_query(query, self._backend)
        cursor = self._connection.cursor()
        cursor.execute(translated_query, params or ())
        return CompatCursor(cursor, self._backend, generated_returning)

    def executescript(self, script: str):
        if self._backend == "sqlite":
            return self._connection.executescript(script)

        for statement in _split_sql_statements(script):
            self.execute(statement)

    def commit(self):
        self._connection.commit()

    def close(self):
        self._connection.close()


def _split_sql_statements(script: str):
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def _replace_qmark_placeholders(query: str) -> str:
    result = []
    in_single_quote = False
    in_double_quote = False
    i = 0

    while i < len(query):
        ch = query[i]

        if ch == "'" and not in_double_quote:
            if in_single_quote and i + 1 < len(query) and query[i + 1] == "'":
                result.append("''")
                i += 2
                continue
            in_single_quote = not in_single_quote
            result.append(ch)
            i += 1
            continue

        if ch == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(ch)
            i += 1
            continue

        if ch == "?" and not in_single_quote and not in_double_quote:
            result.append("%s")
        else:
            result.append(ch)
        i += 1

    return "".join(result)


def _translate_query_for_postgres(query: str):
    translated = query
    insert_or_ignore_pattern = re.compile(r"(?is)\bINSERT\s+OR\s+IGNORE\s+INTO\b")
    had_insert_or_ignore = bool(insert_or_ignore_pattern.search(translated))

    if had_insert_or_ignore:
        translated = insert_or_ignore_pattern.sub("INSERT INTO", translated, count=1)

    translated = translated.replace("date('now')", "CURRENT_DATE")
    translated = _replace_qmark_placeholders(translated)

    if had_insert_or_ignore and "ON CONFLICT" not in translated.upper():
        translated = translated.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    generated_returning = False
    upper_translated = translated.lstrip().upper()
    if upper_translated.startswith("INSERT") and "RETURNING" not in upper_translated and "ON CONFLICT DO NOTHING" not in upper_translated:
        translated = translated.rstrip().rstrip(";") + " RETURNING id"
        generated_returning = True

    return translated, generated_returning


def _translate_query(query: str, backend: str):
    if backend == "postgres":
        return _translate_query_for_postgres(query)
    return query, False


def _is_postgres_url(db_url: str) -> bool:
    lowered = (db_url or "").lower()
    return lowered.startswith("postgresql://") or lowered.startswith("postgres://") or lowered.startswith("postgresql:/") or lowered.startswith("postgres:/")


def is_postgres() -> bool:
    from flask import current_app

    return _is_postgres_url(current_app.config["DATABASE_URL"])


def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql:/") and not db_url.startswith("postgresql://"):
        return db_url.replace("postgresql:/", "postgresql://", 1)
    if db_url.startswith("postgres:/") and not db_url.startswith("postgres://"):
        return db_url.replace("postgres:/", "postgres://", 1)
    return db_url


def _resolve_db_path(db_url: str) -> str:
    # Vercel serverless filesystem is read-only except /tmp.
    if os.getenv("VERCEL") == "1" and not db_url.startswith("/tmp/"):
        return "/tmp/malzara.db"

    if os.path.isabs(db_url):
        return db_url
    return str(BASE_DIR / db_url)


def get_db():
    if "db" not in g:
        from flask import current_app

        configured_url = current_app.config["DATABASE_URL"]

        if _is_postgres_url(configured_url):
            if psycopg is None:
                raise RuntimeError("PostgreSQL URL is configured but psycopg is not installed.")

            normalized_url = _normalize_db_url(configured_url)
            connection = psycopg.connect(normalized_url, row_factory=dict_row)
            g.db = CompatConnection(connection, "postgres")
        else:
            db_path = _resolve_db_path(configured_url)
            try:
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
                sqlite_connection = sqlite3.connect(db_path)
            except sqlite3.OperationalError as exc:
                fallback_path = "/tmp/malzara.db"
                if db_path == fallback_path:
                    raise

                current_app.logger.warning(
                    "Primary sqlite path failed (%s): %s. Falling back to %s",
                    db_path,
                    exc,
                    fallback_path,
                )
                Path("/tmp").mkdir(parents=True, exist_ok=True)
                sqlite_connection = sqlite3.connect(fallback_path)

            sqlite_connection.row_factory = sqlite3.Row
            sqlite_connection.execute("PRAGMA foreign_keys = ON")
            g.db = CompatConnection(sqlite_connection, "sqlite")

    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _table_exists(db, table_name: str) -> bool:
    from flask import current_app

    if _is_postgres_url(current_app.config["DATABASE_URL"]):
        row = db.execute(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()
        return row is not None

    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _ensure_performance_indexes(db):
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_cart_user_id ON cart(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_special_days_user_id ON special_days(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_special_days_event_date ON special_days(event_date)",
        "CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_offers_active_expiry ON offers(is_active, expiry_date)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_products_category_active ON products(category, is_active)",
    ]
    for statement in indexes:
        db.execute(statement)


def init_db(app):
    schema_filename = "schema_postgres.sql" if _is_postgres_url(app.config["DATABASE_URL"]) else "schema.sql"
    schema_path = BASE_DIR / "database" / schema_filename
    with app.app_context():
        db = get_db()

        if not _table_exists(db, "users"):
            with open(schema_path, "r", encoding="utf-8") as schema_file:
                db.executescript(schema_file.read())

        if not is_postgres():
            _ensure_reviews_table(db)
            _ensure_subscriptions_table(db)
            _ensure_offers_offer_link_column(db)
            _ensure_reviews_product_id_column(db)

        _ensure_performance_indexes(db)

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


def _ensure_reviews_table(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            product_id INTEGER,
            rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            feedback TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(order_id, user_id),
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
        """
    )


def _ensure_subscriptions_table(db):
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL CHECK (plan IN ('monthly', 'yearly')),
            status TEXT NOT NULL DEFAULT 'active',
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )


def _ensure_reviews_product_id_column(db):
    columns = db.execute("PRAGMA table_info(reviews)").fetchall()
    if not columns:
        return

    column_names = {column[1] for column in columns}
    if "product_id" not in column_names:
        db.execute("ALTER TABLE reviews ADD COLUMN product_id INTEGER REFERENCES products(id) ON DELETE SET NULL")
