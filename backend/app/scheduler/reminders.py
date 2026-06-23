import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.loan_expiration_service import process_expired_draft_loans
from app.services.loan_interest_accrual_service import process_daily_interest_accrual
from app.services.loan_reminder_service import process_loan_reminders

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def run_loan_reminders_job() -> None:
    db = SessionLocal()

    try:
        process_loan_reminders(db=db)
    except Exception:
        logger.exception("Loan reminders job failed")
        db.rollback()
    finally:
        db.close()


def run_draft_expiration_job() -> None:
    db = SessionLocal()

    try:
        expired_count = process_expired_draft_loans(db=db)

        logger.info(
            "Draft loan expiration job completed. Expired loans: %s",
            expired_count,
        )
    except Exception:
        logger.exception("Draft loan expiration job failed")
        db.rollback()
    finally:
        db.close()


def run_interest_accrual_job() -> None:
    db = SessionLocal()

    try:
        process_daily_interest_accrual(db=db)
    except Exception:
        logger.exception("Interest accrual job failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_draft_expiration_job,
        CronTrigger(
            hour=0,
            minute=1,
            timezone="UTC",
        ),
        id="loan_draft_expiration_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        run_interest_accrual_job,
        CronTrigger(
            hour=0,
            minute=5,
            timezone="UTC",
        ),
        id="loan_interest_accrual_daily",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

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

    logger.warning(
        "Scheduler started "
        "(draft expiration + interest accrual + reminders)"
    )


def shutdown_scheduler() -> None:
    if not scheduler.running:
        return

    scheduler.shutdown()

    logger.warning("Scheduler stopped")