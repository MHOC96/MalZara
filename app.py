from dotenv import load_dotenv
from flask import Flask, render_template

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

    app.teardown_appcontext(close_db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

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

    init_db(app)
    setup_scheduler(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
