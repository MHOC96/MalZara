import os

from apscheduler.schedulers.background import BackgroundScheduler

from models.subscription_model import SubscriptionModel
from services.email_service import EmailService
from services.reminder_service import send_special_day_reminders


def setup_scheduler(app):
    should_start = not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if not should_start:
        return

    scheduler = BackgroundScheduler(daemon=True)

    def reminder_job():
        with app.app_context():
            result = send_special_day_reminders(days_before=7)
            print(
                "[REMINDER JOB] completed "
                f"(sent: {result['sent']}, failed: {result['failed']}, skipped: {result['skipped']}, total: {result['total']})"
            )

    def reminder_job_1day():
        with app.app_context():
            result = send_special_day_reminders(days_before=1)
            print(
                "[REMINDER JOB 1-DAY] completed "
                f"(sent: {result['sent']}, failed: {result['failed']}, skipped: {result['skipped']}, total: {result['total']})"
            )

    def subscription_expiry_warning_job():
        """Warn users whose subscription expires within 3 days."""
        with app.app_context():
            expiring = SubscriptionModel.get_expiring_soon(days=3)
            notified = 0
            for sub in expiring:
                success = EmailService.send_subscription_expiry_warning(
                    to_email=sub["customer_email"],
                    customer_name=sub["customer_name"],
                    plan=sub["plan"],
                    end_date=sub["end_date"],
                )
                if success:
                    notified += 1
            print(f"[SUBSCRIPTION EXPIRY WARNING] Notified {notified}/{len(expiring)} expiring subscribers.")

    def subscription_auto_renewal_job():
        """Auto-renew subscriptions that have already expired."""
        with app.app_context():
            result = SubscriptionModel.auto_renew()
            print(
                f"[SUBSCRIPTION AUTO-RENEWAL] renewed: {result['renewed']}, skipped: {result['skipped']}"
            )

    scheduler.add_job(reminder_job, "cron", hour=8, minute=0, id="special_day_reminder_7day", replace_existing=True)
    scheduler.add_job(reminder_job_1day, "cron", hour=8, minute=5, id="special_day_reminder_1day", replace_existing=True)
    scheduler.add_job(subscription_expiry_warning_job, "cron", hour=8, minute=10, id="subscription_expiry_warning", replace_existing=True)
    scheduler.add_job(subscription_auto_renewal_job, "cron", hour=8, minute=15, id="subscription_auto_renewal", replace_existing=True)
    scheduler.start()
    app.extensions["scheduler"] = scheduler
