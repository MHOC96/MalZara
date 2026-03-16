import os
from flask import current_app, url_for

try:
    import stripe
except ImportError:
    stripe = None


class StripeService:
    @staticmethod
    def is_configured() -> bool:
        """Check if Stripe API keys are configured."""
        if not stripe:
            return False
        secret_key = current_app.config.get("STRIPE_SECRET_KEY")
        return bool(secret_key)

    @staticmethod
    def create_checkout_session(cart_items, order_meta: dict) -> str:
        """
        Creates a Stripe Checkout Session.
        If Stripe is not configured, returns a 'mock' success URL.
        
        order_meta contains strings that we pass back through checkout success.
        """
        if not StripeService.is_configured():
            print("[STRIPE MOCK] Stripe not configured. Proceeding via mock payment flow.")
            # Redirect straight to success, simulating a completed payment
            return url_for("user.checkout_success", **order_meta, _external=True)

        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]

        line_items = []
        for item in cart_items:
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": item["name"],
                        "description": f"Quantity: {item['quantity']} | Customizations: {item['flower_type']}",
                    },
                    # Stripe expects amounts in cents
                    "unit_amount": int(float(item["price"]) * 100),
                },
                "quantity": item["quantity"],
            })

        # Add discount as a negative line item if applicable
        discount = order_meta.get("discount_amount", 0.0)
        if discount > 0:
            # We must pass the subtotal and discount logic through Stripe Coupons ideally, 
            # but for simplicity we can just add a single coupon or modify total.
            # To keep it simple and foolproof for this iteration, we create a one-time coupon on the fly.
            try:
                coupon = stripe.Coupon.create(
                    amount_off=int(discount * 100),
                    currency="usd",
                    duration="once"
                )
                discounts = [{"coupon": coupon.id}]
            except Exception as e:
                print(f"[STRIPE ERR] Could not create coupon: {e}")
                discounts = []
        else:
            discounts = []

        try:
            # Reconstruct the dict as URL params for the success URL
            success_url = url_for("user.checkout_success", _external=True) + "?" + "&".join([f"{k}={v}" for k, v in order_meta.items()])
            cancel_url = url_for("user.checkout_cancel", _external=True)

            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                discounts=discounts
            )
            return session.url
        except Exception as e:
            print(f"[STRIPE SESSION ERR] {e}")
            return None
