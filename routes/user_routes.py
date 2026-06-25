from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for

from models.offer_model import OfferModel
from models.order_model import CartModel, OrderModel
from models.product_model import ProductModel
from models.review_model import ReviewModel
from models.specialday_model import SpecialDayModel
from models.subscription_model import SubscriptionModel
from models.user_model import UserModel
from routes.auth_routes import login_required
from services.email_service import EmailService
from services.stripe_service import StripeService


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
    products = ProductModel.get_all(category=selected_category, limit=6)
    offers = OfferModel.get_active_offers()
    special_days = SpecialDayModel.get_by_user(session["user_id"])
    orders = OrderModel.get_orders_by_user(session["user_id"], limit=8)
    subscription = SubscriptionModel.get_by_user(session["user_id"])

    # Build in-app notifications: events within next 7 days
    today = date.today()
    notifications = []
    for sd in special_days:
        try:
            event_dt = date.fromisoformat(sd["event_date"])
            # Compare month/day (recurring yearly events)
            event_this_year = event_dt.replace(year=today.year)
            if event_this_year < today:
                event_this_year = event_dt.replace(year=today.year + 1)
            days_left = (event_this_year - today).days
            if 0 <= days_left <= 7:
                notifications.append({
                    "event_name": sd["event_name"],
                    "person_name": sd["person_name"],
                    "days_left": days_left,
                    "event_date": sd["event_date"],
                })
        except (ValueError, TypeError):
            pass

    # Build reviewed order ids set for UI
    reviewed_order_ids = ReviewModel.get_reviewed_order_ids(session["user_id"])
    user_reviews = ReviewModel.get_by_user(session["user_id"], limit=5)

    return render_template(
        "dashboard.html",
        products=products,
        categories=categories,
        selected_category=selected_category,
        offers=offers,
        special_days=special_days,
        orders=orders,
        subscription=subscription,
        notifications=notifications,
        reviewed_order_ids=reviewed_order_ids,
        user_reviews=user_reviews,
        plan_prices=SubscriptionModel.PLAN_PRICES,
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

    product_reviews = ReviewModel.get_by_product(product_id)
    return render_template("product_detail.html", product=product, product_reviews=product_reviews)


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
    subscription = SubscriptionModel.get_by_user(session["user_id"])
    return render_template("cart.html", cart_items=cart_items, total=total, subscription=subscription)


@user_bp.route("/api/cart")
@login_required
def api_cart():
    cart_items = CartModel.get_user_cart(g.current_user_id)
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
                delivery_date=request.form.get("delivery_date", "").strip(),
                payment_method=request.form.get("payment_method", "Simulated Card"),
                subscription=SubscriptionModel.get_by_user(session["user_id"]),
            )

        delivery_address = request.form.get("delivery_address", "").strip()
        delivery_date_raw = request.form.get("delivery_date", "").strip()
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
                delivery_date=delivery_date_raw,
                payment_method=payment_method,
            )

        # Validate delivery date
        try:
            chosen_date = datetime.strptime(delivery_date_raw, "%Y-%m-%d").date()
            if chosen_date <= date.today():
                raise ValueError("Date must be in the future.")
            delivery_date = chosen_date.isoformat()
        except (ValueError, TypeError):
            flash("Please select a valid future delivery date.", "danger")
            return render_template(
                "checkout.html",
                cart_items=cart_items,
                subtotal=subtotal,
                discount_amount=discount_amount,
                total=total,
                active_offers=active_offers,
                selected_offer_id=selected_offer_id,
                delivery_address=delivery_address,
                delivery_date=delivery_date_raw,
                payment_method=payment_method,
                subscription=SubscriptionModel.get_by_user(session["user_id"]),
            )

        if payment_method == "Credit/Debit Card (Stripe)":
            order_meta = {
                "delivery_address": delivery_address,
                "delivery_date": delivery_date,
                "total_amount": total,
                "discount_amount": discount_amount,
                "action": "stripe_success"
            }
            session_url = StripeService.create_checkout_session(cart_items, order_meta)
            if session_url:
                return redirect(session_url)
            else:
                flash("Stripe encountered an error. Please try again or use a simulated method.", "danger")
                return redirect(url_for("user.checkout"))

        # Traditional Simulated Payment Flow
        order_id, order_total = OrderModel.create_order(
            user_id=session["user_id"],
            cart_items=cart_items,
            payment_method=payment_method,
            delivery_address=delivery_address,
            delivery_date=delivery_date,
            total_amount=total,
        )
        CartModel.clear_user_cart(session["user_id"])

        user = UserModel.get_by_id(session["user_id"])
        if user:
            html_body = render_template(
                "emails/order_confirmation.html",
                customer_name=user["name"],
                cart_items=cart_items,
                subtotal=subtotal,
                discount_amount=discount_amount,
                total=order_total,
                delivery_date=delivery_date,
                delivery_address=delivery_address,
                app_base_url=current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000"),
            )
            text_body = (
                f"Hello {user['name']},\n\n"
                f"Thank you for your order at MalZara.\n"
                f"Subtotal: Rs. {subtotal:.2f}\n"
                f"Discount: -Rs. {discount_amount:.2f}\n"
                f"Total: Rs. {order_total:.2f}\n"
                f"Delivery Date: {delivery_date}\n"
                f"Delivery Address: {delivery_address}\n\n"
                "Your flowers are being prepared with care.\n"
                "- MalZara Team"
            )
            EmailService.send_html_email(
                to_email=user["email"],
                subject="MalZara Order Confirmation",
                text_body=text_body,
                html_body=html_body,
            )

        flash(f"Order placed! Your gift will be delivered on {delivery_date}.", "success")
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
        delivery_date="",
        payment_method="Credit/Debit Card (Stripe)",
        subscription=SubscriptionModel.get_by_user(session["user_id"]),
    )


@user_bp.route("/checkout/success")
@login_required
def checkout_success():
    """Endpoint Stripe redirects to after successful payment."""
    action = request.args.get("action")
    if action != "stripe_success":
        flash("Invalid return request.", "danger")
        return redirect(url_for("user.dashboard"))

    delivery_address = request.args.get("delivery_address", "")
    delivery_date = request.args.get("delivery_date", "")
    total_amount = request.args.get("total_amount", "0")
    discount_amount = request.args.get("discount_amount", "0")

    cart_items = CartModel.get_user_cart(session["user_id"])
    if not cart_items:
        flash("Order already confirmed or cart empty.", "success")
        return redirect(url_for("user.dashboard"))

    subtotal = sum(item["item_total"] for item in cart_items)

    order_id, order_total = OrderModel.create_order(
        user_id=session["user_id"],
        cart_items=cart_items,
        payment_method="Credit/Debit Card (Stripe)",
        delivery_address=delivery_address,
        delivery_date=delivery_date,
        total_amount=float(total_amount),
    )
    CartModel.clear_user_cart(session["user_id"])

    user = UserModel.get_by_id(session["user_id"])
    if user:
        html_body = render_template(
            "emails/order_confirmation.html",
            customer_name=user["name"],
            cart_items=cart_items,
            subtotal=subtotal,
            discount_amount=float(discount_amount),
            total=order_total,
            delivery_date=delivery_date,
            delivery_address=delivery_address,
            app_base_url=current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000"),
        )
        text_body = (
            f"Hello {user['name']},\n\n"
            f"Thank you for your order at MalZara.\n"
            f"Subtotal: Rs. {subtotal:.2f}\n"
            f"Discount: -Rs. {float(discount_amount):.2f}\n"
            f"Total: Rs. {order_total:.2f}\n"
            f"Delivery Date: {delivery_date}\n"
            f"Delivery Address: {delivery_address}\n\n"
            "Your flowers are being prepared with care.\n"
            "- MalZara Team"
        )
        EmailService.send_html_email(
            to_email=user["email"],
            subject="MalZara Order Confirmation",
            text_body=text_body,
            html_body=html_body,
        )

    flash(f"Payment successful! Order confirmed for {delivery_date}.", "success")
    return redirect(url_for("user.dashboard"))


@user_bp.route("/checkout/cancel")
@login_required
def checkout_cancel():
    """Endpoint Stripe redirects to if user cancels payment flow."""
    flash("Payment was cancelled. You can try again when ready.", "warning")
    return redirect(url_for("user.checkout"))


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


# ---------------------------------------------------------------------------
# Subscription routes
# ---------------------------------------------------------------------------

@user_bp.route("/subscribe", methods=["GET", "POST"])
@login_required
def subscribe():
    if session.get("is_admin"):
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == "POST":
        plan = request.form.get("plan", "").strip().lower()
        if plan not in ("monthly", "yearly"):
            flash("Invalid plan selected.", "danger")
            return redirect(url_for("user.subscribe"))

        SubscriptionModel.subscribe(user_id=session["user_id"], plan=plan)
        plan_label = "Monthly" if plan == "monthly" else "Yearly"
        flash(f"Successfully subscribed to MySara {plan_label} Plan! Enjoy your benefits.", "success")
        return redirect(url_for("user.dashboard"))

    subscription = SubscriptionModel.get_by_user(session["user_id"])
    return render_template(
        "subscribe.html",
        subscription=subscription,
        plan_prices=SubscriptionModel.PLAN_PRICES,
    )


@user_bp.route("/subscription/cancel", methods=["POST"])
@login_required
def cancel_subscription():
    SubscriptionModel.cancel(session["user_id"])
    flash("Your subscription has been cancelled.", "info")
    return redirect(url_for("user.dashboard"))


# ---------------------------------------------------------------------------
# Review / Rating routes
# ---------------------------------------------------------------------------

@user_bp.route("/review/submit", methods=["GET", "POST"])
@login_required
def submit_review():
    order_id = request.args.get("order_id") or request.form.get("order_id")
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        flash("Invalid order.", "danger")
        return redirect(url_for("user.dashboard"))

    # Verify this order belongs to the current user
    order = OrderModel.get_order_for_user(order_id, session["user_id"])
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("user.dashboard"))

    existing_review = ReviewModel.get_by_order(order_id)
    if existing_review:
        flash("You have already reviewed this order.", "info")
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0
        feedback = request.form.get("feedback", "").strip()

        if rating < 1 or rating > 5:
            flash("Please select a rating between 1 and 5.", "danger")
            return render_template("review_form.html", order=order)

        # Get the first product from the order items for linking
        order_items = OrderModel.get_order_items(order_id)
        product_id = order_items[0]["product_id"] if order_items else None

        ReviewModel.create(
            order_id=order_id,
            user_id=session["user_id"],
            rating=rating,
            feedback=feedback,
            product_id=product_id,
        )
        flash("Thank you for your feedback!", "success")
        return redirect(url_for("user.dashboard"))

    return render_template("review_form.html", order=order)
