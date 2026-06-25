from functools import wraps

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, session, url_for

from models.user_model import UserModel
from services.jwt_service import JWTService


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _user_id_from_jwt():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    payload = JWTService.decode_token(auth_header[7:])
    if not payload or payload.get("type") != "access":
        return None

    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None


def get_current_user_id():
    jwt_user_id = _user_id_from_jwt()
    if jwt_user_id is not None:
        return jwt_user_id
    return session.get("user_id")


def get_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return None
    return UserModel.get_by_id(user_id)


def _is_api_request():
    return request.path.startswith("/api") or request.is_json or request.accept_mimetypes.best == "application/json"


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            if _is_api_request():
                return jsonify({"error": "Authentication required"}), 401
            flash("Please login first.", "warning")
            return redirect(url_for("auth.login"))
        g.current_user_id = user_id
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or not user["is_admin"]:
            if _is_api_request():
                return jsonify({"error": "Admin access required"}), 403
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.admin_login"))
        g.current_user_id = user["id"]
        g.current_user = user
        return view_func(*args, **kwargs)

    return wrapper


def _start_session(user):
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["is_admin"] = bool(user["is_admin"])


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone_number = request.form.get("phone_number", "").strip()

        if not name or not email or not password or not phone_number:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        if UserModel.get_by_email(email):
            flash("Email is already registered.", "warning")
            return render_template("register.html")

        UserModel.create_user(name, email, password, phone_number)
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = UserModel.authenticate(email, password)
        if not user or user["is_admin"]:
            flash("Invalid customer credentials.", "danger")
            return render_template("login.html")

        _start_session(user)
        flash("Welcome back!", "success")
        return redirect(url_for("user.dashboard"))

    return render_template("login.html")


@auth_bp.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = UserModel.authenticate(email, password)
        if not user or not user["is_admin"]:
            flash("Invalid admin credentials.", "danger")
            return render_template("login.html", admin_mode=True)

        _start_session(user)
        flash("Admin login successful.", "success")
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("login.html", admin_mode=True)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    admin_only = bool(data.get("admin_only"))

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = UserModel.authenticate(email, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if admin_only and not user["is_admin"]:
        return jsonify({"error": "Admin access required"}), 403

    if not admin_only and user["is_admin"]:
        return jsonify({"error": "Use admin login for admin accounts"}), 403

    return jsonify(JWTService.issue_token_pair(user))


@auth_bp.route("/api/refresh", methods=["POST"])
def api_refresh():
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token") or ""
    if not refresh_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            refresh_token = auth_header[7:]

    if not refresh_token:
        return jsonify({"error": "Refresh token required"}), 400

    payload = JWTService.decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return jsonify({"error": "Invalid or expired refresh token"}), 401

    user = UserModel.get_by_id(int(payload.get("sub")))
    if not user:
        return jsonify({"error": "User not found"}), 401

    return jsonify(JWTService.issue_token_pair(user))


@auth_bp.route("/api/me")
@login_required
def api_me():
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "phone_number": user["phone_number"],
            "is_admin": bool(user["is_admin"]),
        }
    )
