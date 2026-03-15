from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.user_model import UserModel


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please login first.", "warning")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id") or not session.get("is_admin"):
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.admin_login"))
        return view_func(*args, **kwargs)

    return wrapper


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

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["is_admin"] = False
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

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["is_admin"] = True
        flash("Admin login successful.", "success")
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("login.html", admin_mode=True)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
