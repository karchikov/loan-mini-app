import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.loan_reminder_service import process_loan_reminders

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def run_loan_reminders_job() -> None:
    db = SessionLocal()

    try:
        process_loan_reminders(
            db=db,
        )
    except Exception:
        logger.exception("Loan reminders job failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_loan_reminders_job,
        CronTrigger(
            hour=9,
            minute=0,
            timezone="UTC",
        ),
        id="loan_reminders_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    logger.warning("Loan reminders scheduler started")


def shutdown_scheduler() -> None:
    if not scheduler.running:
        return

    scheduler.shutdown()

    logger.warning("Loan reminders scheduler stopped")