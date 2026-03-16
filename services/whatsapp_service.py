import os
from flask import current_app

try:
    from twilio.rest import Client
except ImportError:
    Client = None


class WhatsAppService:
    @staticmethod
    def send_message(to_number: str, message: str) -> bool:
        """
        Sends a WhatsApp message using Twilio.
        If Twilio credentials are not set (or twilio is not installed),
        falls back to printing the message to the console (Mock Mode).
        """
        if not current_app.config.get("ENABLE_WHATSAPP", True):
            print(f"[WHATSAPP DISABLED] To: {to_number}\n{message}")
            return True

        account_sid = current_app.config.get("TWILIO_ACCOUNT_SID")
        auth_token = current_app.config.get("TWILIO_AUTH_TOKEN")
        from_number = current_app.config.get("TWILIO_WHATSAPP_NUMBER")

        if not account_sid or not auth_token or not from_number or not Client:
            print(f"--- [WHATSAPP MOCK LOG] ---\nTo: whatsapp:{to_number}\nMessage:\n{message}\n---------------------------")
            return True

        # Ensure numbers are formatted with 'whatsapp:' prefix
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        try:
            client = Client(account_sid, auth_token)
            msg = client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            print(f"[WHATSAPP SENT] SID: {msg.sid} | To: {to_number}")
            return True
        except Exception as exc:
            print(f"[WHATSAPP FAILED] To: {to_number} | Reason: {exc}")
            return False
