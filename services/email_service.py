import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app


class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        if not current_app.config.get("ENABLE_EMAIL"):
            print(f"[EMAIL DISABLED] To: {to_email} | Subject: {subject}\n{body}")
            return True

        server = current_app.config["MAIL_SERVER"]
        port = current_app.config["MAIL_PORT"]
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

        try:
            with smtplib.SMTP(server, port) as smtp:
                if current_app.config.get("MAIL_USE_TLS"):
                    smtp.starttls()
                smtp.login(username, password)
                smtp.sendmail(sender, [to_email], message.as_string())
            print(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
            return True
        except Exception as exc:
            print(f"[EMAIL FAILED] To: {to_email} | Subject: {subject} | Reason: {exc}")
            return False

    @staticmethod
    def send_html_email(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        if not current_app.config.get("ENABLE_EMAIL"):
            print(f"[EMAIL DISABLED] To: {to_email} | Subject: {subject}\n{text_body}")
            return True

        server = current_app.config["MAIL_SERVER"]
        port = current_app.config["MAIL_PORT"]
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

        try:
            with smtplib.SMTP(server, port) as smtp:
                if current_app.config.get("MAIL_USE_TLS"):
                    smtp.starttls()
                smtp.login(username, password)
                smtp.sendmail(sender, [to_email], message.as_string())
            print(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
            return True
        except Exception as exc:
            print(f"[EMAIL FAILED] To: {to_email} | Subject: {subject} | Reason: {exc}")
            return False
