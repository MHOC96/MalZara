from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from models.offer_model import OfferModel
from models.order_model import OrderModel
from models.product_model import ProductModel
from models.review_model import ReviewModel
from models.specialday_model import SpecialDayModel
from models.user_model import UserModel
from routes.auth_routes import admin_required
from services.email_service import EmailService
from services.reminder_service import send_special_day_reminders


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

DEFAULT_PRODUCT_IMAGE = "https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1200&q=60"


def _configure_cloudinary():
    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME", "")
    api_key = current_app.config.get("CLOUDINARY_API_KEY", "")
    api_secret = current_app.config.get("CLOUDINARY_API_SECRET", "")
    if not cloud_name or not api_key or not api_secret:
        return False

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )
    return True


def _extract_cloudinary_public_id(image_url):
    if not image_url:
        return None

    cloud_name = current_app.config.get("CLOUDINARY_CLOUD_NAME", "")
    if not cloud_name:
        return None

    parsed = urlparse(image_url)
    if parsed.netloc != "res.cloudinary.com" or f"/{cloud_name}/" not in parsed.path:
        return None

    marker = "/image/upload/"
    if marker not in parsed.path:
        return None

    asset_path = parsed.path.split(marker, 1)[1]
    path_parts = asset_path.split("/")
    if path_parts and path_parts[0].startswith("v") and path_parts[0][1:].isdigit():
        path_parts = path_parts[1:]

    if not path_parts:
        return None

    public_id = "/".join(path_parts)
    if "." in public_id:
        public_id = public_id.rsplit(".", 1)[0]
    return public_id or None


def _delete_cloudinary_image(image_url):
    public_id = _extract_cloudinary_public_id(image_url)
    if not public_id:
        return

    if not _configure_cloudinary():
        current_app.logger.warning("Skipping Cloudinary image deletion because Cloudinary config is missing.")
        return

    try:
        cloudinary.uploader.destroy(public_id, invalidate=True, resource_type="image")
    except Exception as exc:
        current_app.logger.warning("Failed to delete Cloudinary image %s: %s", public_id, exc)


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

    if not _configure_cloudinary():
        return None, "Cloudinary is not configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET."

    public_id = f"product_{uuid4().hex}"
    folder = current_app.config.get("CLOUDINARY_UPLOAD_FOLDER", "malzara/products")

    try:
        result = cloudinary.uploader.upload(
            file_storage.stream,
            folder=folder,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
        )
    except Exception as exc:
        return None, f"Image upload failed: {exc}"

    image_url = result.get("secure_url")
    if not image_url:
        return None, "Image upload failed. Please try again."
    return image_url, None


def _resolve_product_image(existing_image=""):
    uploaded_image, upload_error = _save_image_file(request.files.get("image_file"))
    if upload_error:
        return None, upload_error
    if uploaded_image:
        if existing_image and existing_image != uploaded_image:
            _delete_cloudinary_image(existing_image)
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
    reviews = ReviewModel.get_all()

    return render_template(
        "admin_dashboard.html",
        products=products,
        offers=offers,
        customers=customers,
        orders=orders,
        special_days=special_days,
        reviews=reviews,
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
    product = ProductModel.get_by_id(product_id)
    if product:
        _delete_cloudinary_image(product["image_url"])
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
    customers = UserModel.get_all_customers()
    app_base_url = current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000")

    for customer in customers:
        text_body = (
            f"{title}\n\n"
            f"{description}\n"
            f"Discount: {discount_percent:.0f}%\n"
            f"Valid until: {expiry_date}\n\n"
            "Shop now at MalZara and save on fresh flower packages."
        )
        html_body = render_template(
            "emails/promotional_campaign.html",
            subject=f"New Offer: {title}",
            customer_name=customer["name"],
            body=f"{description}\n\n💐 Discount: {discount_percent:.0f}% off\n📅 Valid until: {expiry_date}",
            app_base_url=app_base_url,
        )
        success = EmailService.send_html_email(
            to_email=customer["email"],
            subject="New MalZara Promotional Offer",
            text_body=text_body,
            html_body=html_body,
        )
        if success:
            sent_count += 1
        else:
            failed_count += 1

    flash("Offer created successfully.", "success")
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
    customers = UserModel.get_all_customers()
    app_base_url = current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000")

    for customer in customers:
        html_body = render_template(
            "emails/promotional_campaign.html",
            subject=subject,
            customer_name=customer["name"],
            body=body,
            app_base_url=app_base_url,
        )
        if EmailService.send_html_email(customer["email"], subject, body, html_body):
            sent_count += 1
        else:
            failed_count += 1

    flash("Campaign sent successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/reminders/send", methods=["POST"])
@admin_required
def send_special_day_reminder_campaign():
    result = send_special_day_reminders(days_before=7)
    flash("Special day reminders sent.", "success")
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


@admin_bp.route("/api/orders/<int:order_id>/items")
@admin_required
def get_order_items(order_id):
    items = OrderModel.get_order_items(order_id)
    return jsonify(
        [
            {
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "flower_type": item["flower_type"],
                "bouquet_size": item["bouquet_size"],
                "color_theme": item["color_theme"],
                "card_message": item["card_message"],
            }
            for item in items
        ]
    )


@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@admin_required
def delete_review(review_id):
    ReviewModel.delete(review_id)
    flash("Review deleted.", "info")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/customers/<int:customer_id>")
@admin_required
def customer_detail(customer_id):
    customer = UserModel.get_by_id(customer_id)
    if not customer or customer["is_admin"]:
        flash("Customer not found.", "warning")
        return redirect(url_for("admin.admin_dashboard"))

    orders = OrderModel.get_orders_by_user(customer_id)
    special_days = SpecialDayModel.get_by_user(customer_id)
    offers = OfferModel.get_active_offers()

    return render_template(
        "admin_customer_detail.html",
        customer=customer,
        orders=orders,
        special_days=special_days,
        offers=offers,
    )


@admin_bp.route("/customers/<int:customer_id>/send-offer", methods=["POST"])
@admin_required
def send_customer_offer(customer_id):
    customer = UserModel.get_by_id(customer_id)
    if not customer:
        flash("Customer not found.", "warning")
        return redirect(url_for("admin.admin_dashboard"))

    offer_id = request.form.get("offer_id")
    custom_message = request.form.get("custom_message", "").strip()

    offer = None
    if offer_id:
        try:
            offer = OfferModel.get_active_offer_by_id(int(offer_id))
        except (ValueError, TypeError):
            pass

    if not offer and not custom_message:
        flash("Please select an offer or enter a custom message.", "danger")
        return redirect(url_for("admin.customer_detail", customer_id=customer_id))

    subject = "Special Offer Just for You — MalZara 🌸"
    app_base_url = current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000")

    body_parts = []
    if custom_message:
        body_parts.append(custom_message)
    if offer:
        body_parts.append(
            f"\n💐 {offer['title']}\n"
            f"{offer['description']}\n"
            f"Discount: {offer['discount_percent']:.0f}% off\n"
            f"Valid until: {offer['expiry_date']}"
        )

    body_text = "\n".join(body_parts)

    html_body = render_template(
        "emails/promotional_campaign.html",
        subject="A Special Offer Just for You",
        customer_name=customer["name"],
        body=body_text,
        app_base_url=app_base_url,
    )

    success = EmailService.send_html_email(
        to_email=customer["email"],
        subject=subject,
        text_body=f"Hello {customer['name']},\n\n{body_text}\n\n- MalZara Team",
        html_body=html_body,
    )

    return redirect(url_for("admin.customer_detail", customer_id=customer_id))
