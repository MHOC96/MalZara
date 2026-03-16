from pathlib import Path
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from models.offer_model import OfferModel
from models.order_model import OrderModel
from models.product_model import ProductModel
from models.specialday_model import SpecialDayModel
from models.user_model import UserModel
from routes.auth_routes import admin_required
from services.email_service import EmailService
from services.reminder_service import send_special_day_reminders


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

DEFAULT_PRODUCT_IMAGE = "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1200&q=60"


def _save_image_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None

    filename = secure_filename(file_storage.filename)
    if "." not in filename:
        return None, "Invalid image file."

    extension = filename.rsplit(".", 1)[1].lower()
    allowed_extensions = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", set())
    if extension not in allowed_extensions:
        allowed_text = ", ".join(sorted(allowed_extensions))
        return None, f"Unsupported image format. Allowed: {allowed_text}."

    upload_dir = Path(current_app.root_path) / "static" / "images" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    generated_name = f"{uuid4().hex}.{extension}"
    save_path = upload_dir / generated_name
    file_storage.save(save_path)

    return url_for("static", filename=f"images/uploads/{generated_name}"), None


def _resolve_product_image(existing_image=""):
    uploaded_image, upload_error = _save_image_file(request.files.get("image_file"))
    if upload_error:
        return None, upload_error
    if uploaded_image:
        return uploaded_image, None

    image_url = request.form.get("image_url", "").strip()
    if image_url:
        return image_url, None

    if existing_image:
        return existing_image, None

    return DEFAULT_PRODUCT_IMAGE, None


@admin_bp.route("/dashboard")
@admin_required
def admin_dashboard():
    products = ProductModel.get_all(include_inactive=True)
    offers = OfferModel.get_all_offers_admin()
    customers = UserModel.get_all_customers()
    orders = OrderModel.get_all_orders_with_users()
    special_days = SpecialDayModel.get_all_with_users()

    return render_template(
        "admin_dashboard.html",
        products=products,
        offers=offers,
        customers=customers,
        orders=orders,
        special_days=special_days,
    )


@admin_bp.route("/api/summary")
@admin_required
def admin_summary_api():
    return jsonify(
        {
            "products": len(ProductModel.get_all(include_inactive=True)),
            "offers": len(OfferModel.get_all_offers_admin()),
            "customers": len(UserModel.get_all_customers()),
            "orders": len(OrderModel.get_all_orders_with_users()),
            "special_days": len(SpecialDayModel.get_all_with_users()),
        }
    )


@admin_bp.route("/products/add", methods=["POST"])
@admin_required
def add_product():
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    try:
        price = float(request.form.get("price", "0"))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Invalid price or stock value.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    if not name or not category or not description:
        flash("Product name, category, and description are required.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    image_url, image_error = _resolve_product_image()
    if image_error:
        flash(image_error, "danger")
        return redirect(url_for("admin.admin_dashboard"))

    ProductModel.create(name, category, description, price, image_url, stock)
    flash("Product created successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/products/<int:product_id>/edit", methods=["POST"])
@admin_required
def edit_product(product_id):
    product = ProductModel.get_by_id(product_id)
    if not product:
        flash("Product not found.", "warning")
        return redirect(url_for("admin.admin_dashboard"))

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()

    try:
        price = float(request.form.get("price", "0"))
        stock = int(request.form.get("stock", "0"))
    except ValueError:
        flash("Invalid price or stock value.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    image_url, image_error = _resolve_product_image(existing_image=product["image_url"])
    if image_error:
        flash(image_error, "danger")
        return redirect(url_for("admin.admin_dashboard"))

    is_active = 1 if request.form.get("is_active") == "on" else 0
    ProductModel.update(product_id, name, category, description, price, image_url, stock, is_active)
    flash("Product updated.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    ProductModel.delete(product_id)
    flash("Product deleted.", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/offers/add", methods=["POST"])
@admin_required
def add_offer():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    product_id = request.form.get("product_id") or None
    offer_link = request.form.get("offer_link", "").strip() or None
    expiry_date = request.form.get("expiry_date", "").strip()

    try:
        discount_percent = float(request.form.get("discount_percent", "0"))
    except ValueError:
        flash("Invalid discount value.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    if not title or not description or not expiry_date:
        flash("Offer title, description and expiry date are required.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    OfferModel.create(title, description, discount_percent, product_id, expiry_date, offer_link)

    sent_count = 0
    failed_count = 0

    base_url = current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000")
    subject = "New MalZara Promotional Offer"
    text_body = (
        f"{title}\n\n"
        f"{description}\n"
        f"Discount: {discount_percent:.0f}%\n"
        f"Valid until: {expiry_date}\n\n"
        "Shop now at MalZara and save on fresh flower packages."
    )

    customers = UserModel.get_all_customers()
    for customer in customers:
        html_body = render_template(
            "emails/promotional_campaign.html",
            subject=subject,
            customer_name=customer["name"],
            body=text_body,
            app_base_url=base_url,
        )
        
        success = EmailService.send_html_email(
            to_email=customer["email"],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        if success:
            sent_count += 1
        else:
            failed_count += 1

    flash(
        f"Offer created. Campaign emails sent: {sent_count}, failed: {failed_count}.",
        "success" if failed_count == 0 else "warning",
    )
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/offers/<int:offer_id>/deactivate", methods=["POST"])
@admin_required
def deactivate_offer(offer_id):
    OfferModel.deactivate(offer_id)
    flash("Offer deactivated.", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/campaign/send", methods=["POST"])
@admin_required
def send_campaign():
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()

    if not subject or not body:
        flash("Campaign subject and message are required.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    sent_count = 0
    failed_count = 0

    base_url = current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000")
    customers = UserModel.get_all_customers()

    for customer in customers:
        html_body = render_template(
            "emails/promotional_campaign.html",
            subject=subject,
            customer_name=customer["name"],
            body=body,
            app_base_url=base_url,
        )

        success = EmailService.send_html_email(
            to_email=customer["email"],
            subject=subject,
            text_body=body,
            html_body=html_body,
        )
        if success:
            sent_count += 1
        else:
            failed_count += 1

    flash(
        f"Email campaign completed. Sent: {sent_count}, failed: {failed_count}.",
        "success" if failed_count == 0 else "warning",
    )
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reminders/send", methods=["POST"])
@admin_required
def send_special_day_reminder_campaign():
    result = send_special_day_reminders(days_before=7)
    flash(
        (
            "Special day reminders completed "
            f"(sent: {result['sent']}, failed: {result['failed']}, skipped: {result['skipped']}, total events: {result['total']})."
        ),
        "success" if result["failed"] == 0 else "warning",
    )
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/orders/<int:order_id>/schedule", methods=["POST"])
@admin_required
def schedule_order_delivery(order_id):
    delivery_date = request.form.get("delivery_date", "").strip()

    if not delivery_date:
        flash("Delivery date is required.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    try:
        selected_date = datetime.strptime(delivery_date, "%Y-%m-%d").date()
        if selected_date < datetime.utcnow().date():
            flash("Delivery date cannot be in the past.", "danger")
            return redirect(url_for("admin.admin_dashboard"))
    except ValueError:
        flash("Invalid delivery date format.", "danger")
        return redirect(url_for("admin.admin_dashboard"))

    OrderModel.update_delivery_date(order_id, delivery_date)
    flash("Delivery date assigned successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))
