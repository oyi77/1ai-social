"""
Dunning workflow for handling failed payments with retry logic.

Retry Schedule:
- Day 0: Payment fails -> Attempt 1, notify customer
- Day 1: Retry 1 -> If fails, Attempt 2
- Day 4: Retry 2 -> If fails, Attempt 3
- Day 7: Retry 3 -> If fails, suspend account
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

try:
    from ..notifications.email import send_email

    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger.warning("Email notifications module not available")

Base = declarative_base()


class DunningEvent(Base):
    """Dunning event model for tracking payment retry workflow."""

    __tablename__ = "dunning_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    event_type = Column(String(50), nullable=False)
    attempt_number = Column(Integer, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


RETRY_SCHEDULE = {
    1: 1,  # Retry after 1 day
    2: 3,  # Retry after 3 more days (total 4 days)
    3: 3,  # Retry after 3 more days (total 7 days)
}

MAX_RETRY_ATTEMPTS = 3


class DunningManager:
    """Manages dunning workflow for failed payments."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def handle_payment_failure(
        self, tenant_id: str, subscription_id: Optional[int] = None
    ) -> dict:
        """
        Handle payment failure and schedule first retry.

        Args:
            tenant_id: Tenant ID
            subscription_id: Subscription ID (optional)

        Returns:
            Dict with status and next action
        """
        attempt_number = 1
        next_retry_at = datetime.utcnow() + timedelta(days=RETRY_SCHEDULE[1])

        event = DunningEvent(
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            event_type="payment_failed",
            attempt_number=attempt_number,
            next_retry_at=next_retry_at,
        )

        self.db.add(event)
        self.db.commit()

        self._log_email(
            tenant_id,
            "payment_failed",
            f"Payment failed. Retry scheduled for {next_retry_at.isoformat()}",
        )

        logger.info(
            f"Payment failure recorded for tenant {tenant_id}, "
            f"attempt {attempt_number}, next retry: {next_retry_at}"
        )

        return {
            "status": "retry_scheduled",
            "attempt_number": attempt_number,
            "next_retry_at": next_retry_at.isoformat(),
        }

    def schedule_retry(self, tenant_id: str, attempt_number: int) -> dict:
        """
        Schedule next retry attempt.

        Args:
            tenant_id: Tenant ID
            attempt_number: Current attempt number

        Returns:
            Dict with status and next action
        """
        if attempt_number > MAX_RETRY_ATTEMPTS:
            return self.suspend_account(tenant_id)

        if attempt_number not in RETRY_SCHEDULE:
            logger.error(f"Invalid attempt number: {attempt_number}")
            return {"status": "error", "message": "Invalid attempt number"}

        last_event = (
            self.db.query(DunningEvent)
            .filter_by(tenant_id=tenant_id)
            .order_by(DunningEvent.created_at.desc())
            .first()
        )

        if not last_event:
            logger.warning(f"No previous dunning event found for tenant {tenant_id}")
            return {"status": "error", "message": "No previous event found"}

        days_to_add = RETRY_SCHEDULE[attempt_number]
        next_retry_at = datetime.utcnow() + timedelta(days=days_to_add)

        event = DunningEvent(
            tenant_id=tenant_id,
            subscription_id=last_event.subscription_id,
            event_type="retry_scheduled",
            attempt_number=attempt_number,
            next_retry_at=next_retry_at,
        )

        self.db.add(event)
        self.db.commit()

        self._log_email(
            tenant_id,
            "retry_scheduled",
            f"Retry attempt {attempt_number} scheduled for {next_retry_at.isoformat()}",
        )

        logger.info(
            f"Retry scheduled for tenant {tenant_id}, "
            f"attempt {attempt_number}, next retry: {next_retry_at}"
        )

        return {
            "status": "retry_scheduled",
            "attempt_number": attempt_number,
            "next_retry_at": next_retry_at.isoformat(),
        }

    def suspend_account(self, tenant_id: str) -> dict:
        """
        Suspend account after final retry failure.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dict with status
        """
        last_event = (
            self.db.query(DunningEvent)
            .filter_by(tenant_id=tenant_id)
            .order_by(DunningEvent.created_at.desc())
            .first()
        )

        event = DunningEvent(
            tenant_id=tenant_id,
            subscription_id=last_event.subscription_id if last_event else None,
            event_type="account_suspended",
            attempt_number=None,
            next_retry_at=None,
        )

        self.db.add(event)
        self.db.commit()

        self._log_email(
            tenant_id,
            "account_suspended",
            "Account suspended due to payment failure after 3 retry attempts",
        )

        logger.warning(f"Account suspended for tenant {tenant_id}")

        return {"status": "account_suspended", "tenant_id": tenant_id}

    def recover_payment(self, tenant_id: str) -> dict:
        """
        Record successful payment recovery.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dict with status
        """
        last_event = (
            self.db.query(DunningEvent)
            .filter_by(tenant_id=tenant_id)
            .order_by(DunningEvent.created_at.desc())
            .first()
        )

        event = DunningEvent(
            tenant_id=tenant_id,
            subscription_id=last_event.subscription_id if last_event else None,
            event_type="payment_recovered",
            attempt_number=None,
            next_retry_at=None,
        )

        self.db.add(event)
        self.db.commit()

        self._log_email(
            tenant_id, "payment_recovered", "Payment successfully recovered"
        )

        logger.info(f"Payment recovered for tenant {tenant_id}")

        return {"status": "payment_recovered", "tenant_id": tenant_id}

    def _log_email(self, tenant_id: str, email_type: str, message: str) -> None:
        """
        Send email notification for dunning events.

        Args:
            tenant_id: Tenant ID
            email_type: Type of email
            message: Email message
        """
        logger.info(
            f"[EMAIL] tenant_id={tenant_id}, type={email_type}, message={message}"
        )

        if not EMAIL_AVAILABLE:
            logger.warning("Email module not available, skipping email send")
            return

        email_templates = {
            "payment_failed": {
                "template": "payment_failed",
                "subject": "Payment Failed - Action Required",
            },
            "retry_scheduled": {
                "template": "payment_failed",
                "subject": "Payment Retry Scheduled",
            },
            "account_suspended": {
                "template": "payment_failed",
                "subject": "Account Suspended - Payment Required",
            },
            "payment_recovered": {
                "template": "welcome",
                "subject": "Payment Successful - Account Restored",
            },
        }

        template_info = email_templates.get(email_type)
        if not template_info:
            logger.warning(f"Unknown email type: {email_type}")
            return

        try:
            send_email(
                to=f"tenant_{tenant_id}@example.com",
                subject=template_info["subject"],
                template=template_info["template"],
                data={
                    "name": f"Tenant {tenant_id}",
                    "attempt_date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "failure_reason": "Payment method declined",
                    "payment_url": "#",
                    "suspension_date": (datetime.utcnow() + timedelta(days=7)).strftime(
                        "%Y-%m-%d"
                    ),
                    "user_id": tenant_id,
                    "dashboard_url": "#",
                    "docs_url": "#",
                    "community_url": "#",
                },
            )
            logger.info(
                f"Email sent successfully for {email_type} to tenant {tenant_id}"
            )
        except Exception as e:
            logger.error(f"Failed to send email for {email_type}: {e}")


def get_pending_retries(db_session: Session) -> list:
    """
    Get all pending retry attempts that are due.

    Args:
        db_session: Database session

    Returns:
        List of DunningEvent records
    """
    now = datetime.utcnow()
    return (
        db_session.query(DunningEvent)
        .filter(
            DunningEvent.event_type.in_(["payment_failed", "retry_scheduled"]),
            DunningEvent.next_retry_at <= now,
        )
        .all()
    )
