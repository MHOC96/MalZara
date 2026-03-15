import os

from apscheduler.schedulers.background import BackgroundScheduler

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

    scheduler.add_job(reminder_job, "cron", hour=8, minute=0, id="special_day_reminder", replace_existing=True)
    scheduler.start()
    app.extensions["scheduler"] = scheduler
