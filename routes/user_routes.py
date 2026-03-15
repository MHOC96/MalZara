from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.offer_model import OfferModel
from models.order_model import CartModel, OrderModel
from models.product_model import ProductModel
from models.specialday_model import SpecialDayModel
from models.user_model import UserModel
from routes.auth_routes import login_required
from services.email_service import EmailService


user_bp = Blueprint("user", __name__)


@user_bp.route("/")
def home_redirect():
    if session.get("user_id") and session.get("is_admin"):
        return redirect(url_for("admin.admin_dashboard"))
    if session.get("user_id"):
        return redirect(url_for("user.dashboard"))
    return redirect(url_for("auth.login"))


@user_bp.route("/dashboard")
@login_required
def dashboard():
    if session.get("is_admin"):
        return redirect(url_for("admin.admin_dashboard"))

    categories = ProductModel.get_categories()
    selected_category = request.args.get("category")
    products = ProductModel.get_all(category=selected_category)
    offers = OfferModel.get_active_offers()
    special_days = SpecialDayModel.get_by_user(session["user_id"])
    orders = OrderModel.get_orders_by_user(session["user_id"])

    return render_template(
        "dashboard.html",
        products=products,
        categories=categories,
        selected_category=selected_category,
        offers=offers,
        special_days=special_days,
        orders=orders,
    )


@user_bp.route("/products")
@login_required
def products():
    categories = ProductModel.get_categories()
    selected_category = request.args.get("category")
    products_data = ProductModel.get_all(category=selected_category)
    return render_template(
        "products.html",
        products=products_data,
        categories=categories,
        selected_category=selected_category,
    )


@user_bp.route("/api/products")
@login_required
def api_products():
    category = request.args.get("category")
    products_data = ProductModel.get_all(category=category)
    payload = [
        {
            "id": p["id"],
            "name": p["name"],
            "category": p["category"],
            "description": p["description"],
            "price": p["price"],
            "image_url": p["image_url"],
            "stock": p["stock"],
        }
        for p in products_data
    ]
    return jsonify(payload)


@user_bp.route("/products/<int:product_id>")
@login_required
def product_detail(product_id):
    product = ProductModel.get_by_id(product_id)
    if not product or not product["is_active"]:
        flash("Product not found.", "warning")
        return redirect(url_for("user.products"))

    return render_template("product_detail.html", product=product)


@user_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    try:
        product_id = int(request.form.get("product_id", "0"))
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        flash("Invalid cart data.", "danger")
        return redirect(url_for("user.products"))

    flower_type = request.form.get("flower_type", "").strip()
    bouquet_size = request.form.get("bouquet_size", "").strip()
    color_theme = request.form.get("color_theme", "").strip()
    card_message = request.form.get("card_message", "").strip()

    flower_names = [name.strip() for name in request.form.getlist("flower_name[]")]
    flower_qty_inputs = request.form.getlist("flower_qty[]")
    bouquet_parts = []
    for name, qty_raw in zip(flower_names, flower_qty_inputs):
        if not name:
            continue
        try:
            qty = int(qty_raw)
        except ValueError:
            continue
        if qty > 0:
            bouquet_parts.append(f"{name} x{qty}")

    if bouquet_parts:
        flower_type = ", ".join(bouquet_parts)
        bouquet_size = bouquet_size or f"Custom Mix ({len(bouquet_parts)} types)"

    if quantity <= 0:
        flash("Quantity must be at least 1.", "warning")
        return redirect(url_for("user.products"))

    product = ProductModel.get_by_id(product_id)
    if not product or not product["is_active"]:
        flash("Selected product is not available.", "danger")
        return redirect(url_for("user.products"))

    CartModel.add_to_cart(
        user_id=session["user_id"],
        product_id=product_id,
        quantity=quantity,
        flower_type=flower_type,
        bouquet_size=bouquet_size,
        color_theme=color_theme,
        card_message=card_message,
    )
    flash("Item added to cart.", "success")
    return redirect(request.referrer or url_for("user.products"))


@user_bp.route("/cart")
@login_required
def cart():
    cart_items = CartModel.get_user_cart(session["user_id"])
    total = sum(item["item_total"] for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@user_bp.route("/api/cart")
@login_required
def api_cart():
    cart_items = CartModel.get_user_cart(session["user_id"])
    total = sum(item["item_total"] for item in cart_items)
    payload = {
        "items": [
            {
                "id": i["id"],
                "product_id": i["product_id"],
                "name": i["name"],
                "quantity": i["quantity"],
                "price": i["price"],
                "item_total": i["item_total"],
                "flower_type": i["flower_type"],
                "bouquet_size": i["bouquet_size"],
                "color_theme": i["color_theme"],
                "card_message": i["card_message"],
            }
            for i in cart_items
        ],
        "total": total,
    }
    return jsonify(payload)


@user_bp.route("/cart/update", methods=["POST"])
@login_required
def update_cart():
    try:
        cart_item_id = int(request.form.get("cart_item_id", "0"))
        quantity = int(request.form.get("quantity", "1"))
    except ValueError:
        flash("Invalid quantity.", "danger")
        return redirect(url_for("user.cart"))

    CartModel.update_quantity(cart_item_id, session["user_id"], quantity)
    flash("Cart updated.", "info")
    return redirect(url_for("user.cart"))


@user_bp.route("/cart/remove", methods=["POST"])
@login_required
def remove_cart_item():
    try:
        cart_item_id = int(request.form.get("cart_item_id", "0"))
    except ValueError:
        flash("Invalid cart item.", "danger")
        return redirect(url_for("user.cart"))

    CartModel.remove_item(cart_item_id, session["user_id"])
    flash("Item removed from cart.", "info")
    return redirect(url_for("user.cart"))


@user_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartModel.get_user_cart(session["user_id"])
    subtotal = sum(item["item_total"] for item in cart_items)
    active_offers = OfferModel.get_active_offers()
    selected_offer_id = request.form.get("offer_id") or request.args.get("offer_id") or ""

    discount_amount = 0.0
    total = float(subtotal)
    selected_offer = None

    if selected_offer_id:
        try:
            selected_offer = OfferModel.get_active_offer_by_id(int(selected_offer_id))
        except ValueError:
            selected_offer = None

    if selected_offer:
        if selected_offer["product_id"]:
            eligible_subtotal = sum(
                item["item_total"] for item in cart_items if item["product_id"] == selected_offer["product_id"]
            )
        else:
            eligible_subtotal = subtotal

        discount_amount = (eligible_subtotal * float(selected_offer["discount_percent"])) / 100.0
        total = max(0.0, float(subtotal) - float(discount_amount))

    if not cart_items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("user.products"))

    if request.method == "POST":
        action = request.form.get("action", "place")
        if action == "preview":
            return render_template(
                "checkout.html",
                cart_items=cart_items,
                subtotal=subtotal,
                discount_amount=discount_amount,
                total=total,
                active_offers=active_offers,
                selected_offer_id=selected_offer_id,
                delivery_address=request.form.get("delivery_address", "").strip(),
                payment_method=request.form.get("payment_method", "Simulated Card"),
            )

        delivery_address = request.form.get("delivery_address", "").strip()
        payment_method = request.form.get("payment_method", "Simulated Card")

        if not delivery_address:
            flash("Delivery address is required.", "danger")
            return render_template(
                "checkout.html",
                cart_items=cart_items,
                subtotal=subtotal,
                discount_amount=discount_amount,
                total=total,
                active_offers=active_offers,
                selected_offer_id=selected_offer_id,
                delivery_address=delivery_address,
                payment_method=payment_method,
            )

        order_id, order_total = OrderModel.create_order(
            user_id=session["user_id"],
            cart_items=cart_items,
            payment_method=payment_method,
            delivery_address=delivery_address,
            delivery_date=None,
            total_amount=total,
        )
        CartModel.clear_user_cart(session["user_id"])

        user = UserModel.get_by_id(session["user_id"])
        if user:
            EmailService.send_email(
                to_email=user["email"],
                subject="MalZara Order Confirmation",
                body=(
                    f"Hello {user['name']},\n\n"
                    f"Thank you for your order at MalZara.\n"
                    f"Subtotal: ${subtotal:.2f}\n"
                    f"Discount: -${discount_amount:.2f}\n"
                    f"Total: ${order_total:.2f}\n"
                    "Delivery Date: Assigned by admin after confirmation.\n\n"
                    "Your flowers are being prepared with care.\n"
                    "- MalZara Team"
                ),
            )

        flash("Order placed successfully. Delivery date will be assigned by admin.", "success")
        return redirect(url_for("user.dashboard"))

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        subtotal=subtotal,
        discount_amount=discount_amount,
        total=total,
        active_offers=active_offers,
        selected_offer_id=selected_offer_id,
        delivery_address="",
        payment_method="Simulated Card",
    )


@user_bp.route("/special-days/add", methods=["POST"])
@login_required
def add_special_day():
    event_name = request.form.get("event_name", "").strip()
    person_name = request.form.get("person_name", "").strip()
    event_date = request.form.get("event_date", "").strip()
    preferred_flower_package = request.form.get("preferred_flower_package") or None

    if not event_name or not person_name or not event_date:
        flash("Please fill all required special day fields.", "danger")
        return redirect(url_for("user.dashboard"))

    SpecialDayModel.create(
        user_id=session["user_id"],
        event_name=event_name,
        person_name=person_name,
        event_date=event_date,
        preferred_flower_package=preferred_flower_package,
    )
    flash("Special day saved successfully.", "success")
    return redirect(url_for("user.dashboard"))
