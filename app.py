import os
import traceback

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from config import Config
from database.db import close_db, init_db
from routes.admin_routes import admin_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from services.scheduler_service import setup_scheduler


load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.setdefault("_DB_READY", False)
    app.config.setdefault("_DB_INIT_ERROR", None)

    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_nav_context():
        from flask import session

        from models.order_model import CartModel

        cart_count = 0
        if app.config.get("_DB_READY") and session.get("user_id") and not session.get("is_admin"):
            try:
                cart_count = CartModel.get_cart_count(session["user_id"])
            except Exception:
                cart_count = 0
        return {"cart_count": cart_count}

    def ensure_database():
        if app.config.get("_DB_READY"):
            return None

        if app.config.get("_DB_INIT_ERROR"):
            return app.config["_DB_INIT_ERROR"]

        try:
            init_db(app)
            app.config["_DB_READY"] = True
            return None
        except Exception as exc:
            app.logger.error("Database initialization failed: %s", exc)
            app.logger.error(traceback.format_exc())
            app.config["_DB_INIT_ERROR"] = str(exc)
            return str(exc)

    @app.before_request
    def prepare_database():
        if request.endpoint in {"health", "static"}:
            return None

        error = ensure_database()
        if error:
            return (
                render_template(
                    "error.html",
                    title="Service Unavailable",
                    message=(
                        "The app could not connect to the database. "
                        "Check DATABASE_URL in Vercel environment variables."
                    ),
                ),
                503,
            )
        return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    @app.get("/health")
    def health():
        db_error = ensure_database()
        status = "ok" if not db_error else "degraded"
        code = 200 if not db_error else 503
        return jsonify({"status": status, "database": "ready" if not db_error else db_error}), code

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", title="Page Not Found", message="The page you requested does not exist."), 404

    @app.errorhandler(500)
    def server_error(_error):
        return (
            render_template(
                "error.html",
                title="Server Error",
                message="Something went wrong on our side. Please try again.",
            ),
            500,
        )

    setup_scheduler(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
