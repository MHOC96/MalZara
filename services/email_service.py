import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app


class EmailService:
    @staticmethod
    def _send_in_background(app, to_email, subject, message):
        """Send an email in a background thread to avoid blocking the request."""
        def _send():
            with app.app_context():
                server = app.config["MAIL_SERVER"]
                port = app.config["MAIL_PORT"]
                username = app.config["MAIL_USERNAME"]
                password = app.config["MAIL_PASSWORD"]
                sender = app.config["MAIL_FROM"]

                try:
                    with smtplib.SMTP(server, port, timeout=10) as smtp:
                        if app.config.get("MAIL_USE_TLS"):
                            smtp.starttls()
                        smtp.login(username, password)
                        smtp.sendmail(sender, [to_email], message.as_string())
                    print(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
                except Exception as exc:
                    print(f"[EMAIL FAILED] To: {to_email} | Subject: {subject} | Reason: {exc}")

        thread = threading.Thread(target=_send, daemon=True)
        thread.start()

    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        if not current_app.config.get("ENABLE_EMAIL"):
            print(f"[EMAIL DISABLED] To: {to_email} | Subject: {subject}\n{body}")
            return True

        username = current_app.config["MAIL_USERNAME"]
        password = current_app.config["MAIL_PASSWORD"]
        sender = current_app.config["MAIL_FROM"]

        if not username or not password:
            print(f"[EMAIL FAILED] To: {to_email} | Subject: {subject} | Reason: Missing credentials")
            return False

        message = MIMEText(body, "plain")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to_email

        app = current_app._get_current_object()
        EmailService._send_in_background(app, to_email, subject, message)
        return True

    @staticmethod
    def send_html_email(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        if not current_app.config.get("ENABLE_EMAIL"):
            print(f"[EMAIL DISABLED] To: {to_email} | Subject: {subject}\n{text_body}")
            return True

        username = current_app.config["MAIL_USERNAME"]
        password = current_app.config["MAIL_PASSWORD"]
        sender = current_app.config["MAIL_FROM"]

        if not username or not password:
            print(f"[EMAIL FAILED] To: {to_email} | Subject: {subject} | Reason: Missing credentials")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to_email
        message.attach(MIMEText(text_body, "plain"))
        message.attach(MIMEText(html_body, "html"))

        app = current_app._get_current_object()
        EmailService._send_in_background(app, to_email, subject, message)
        return True

