from flask import current_app, render_template

from models.offer_model import OfferModel
from models.product_model import ProductModel
from models.specialday_model import SpecialDayModel
from models.user_model import UserModel
from services.email_service import EmailService
from services.whatsapp_service import WhatsAppService


def _build_offer_url(offer):
    if offer and offer["offer_link"]:
        return offer["offer_link"]
    return current_app.config.get("OFFERS_PAGE_URL") or f"{current_app.config.get('APP_BASE_URL', '').rstrip('/')}/products"


def send_special_day_reminders(days_before=7):
    reminders = SpecialDayModel.get_upcoming_events_within_days(days_before)
    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for event in reminders:
        user = UserModel.get_by_id(event["user_id"])
        if not user:
            skipped_count += 1
            continue

        featured_product = None
        if event["preferred_flower_package"]:
            featured_product = ProductModel.get_by_id(event["preferred_flower_package"])
        if not featured_product:
            products = ProductModel.get_all()
            featured_product = products[0] if products else None

        related_offers = []
        if event["preferred_flower_package"]:
            related_offers = OfferModel.get_active_offers_for_product(event["preferred_flower_package"])
        if not related_offers:
            related_offers = OfferModel.get_active_offers()

        active_offer = related_offers[0] if related_offers else None
        offer_url = _build_offer_url(active_offer)

        subject = "Your Special Day is Coming Soon - Celebrate with MalZara"

        text_body = (
            f"Hello {user['name']},\n\n"
            f"Your {event['event_name']} for {event['person_name']} is coming soon on {event['event_date']}.\n"
            "Celebrate the moment with a beautiful MalZara flower package.\n\n"
        )

        if active_offer:
            text_body += (
                f"Special Offer: {active_offer['title']} ({active_offer['discount_percent']:.0f}% off)\n"
                f"Offer link: {offer_url}\n\n"
            )

        text_body += "View Special Flower Offers: " + offer_url + "\n\n- MalZara Team"

        html_body = render_template(
            "emails/special_day_reminder.html",
            customer_name=user["name"],
            event_name=event["event_name"],
            person_name=event["person_name"],
            event_date=event["event_date"],
            days_until_event=event["days_until_event"],
            featured_product=featured_product,
            active_offer=active_offer,
            offer_url=offer_url,
            app_base_url=current_app.config.get("APP_BASE_URL", "http://127.0.0.1:5000"),
        )

        success = EmailService.send_html_email(
            to_email=user["email"],
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
        if success:
            sent_count += 1
        else:
            failed_count += 1

        # Also send WhatsApp notification via Twilio (or mock log) if phone number exists
        if user.get("phone_number"):
            WhatsAppService.send_message(
                to_number=user["phone_number"],
                message=(f"🔔 MalZara Reminder 🔔\n{text_body}")
            )

    return {
        "sent": sent_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "total": len(reminders),
    }
