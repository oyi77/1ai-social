import os
import logging
import smtplib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Welcome to 1ai-social",
        "body": """Hi {name},

Welcome to 1ai-social! We're excited to have you on board.

Your account is now active and ready to use. You can start creating and managing your social media content right away.

Getting Started:
- Log in to your dashboard: {dashboard_url}
- Check out our documentation: {docs_url}
- Join our community: {community_url}

If you have any questions, feel free to reach out to our support team.

Best regards,
The 1ai-social Team

---
{unsubscribe_link}
""",
    },
    "invoice": {
        "subject": "Your Monthly Invoice - 1ai-social",
        "body": """Hi {name},

Your monthly invoice is ready for download.

Invoice Details:
- Invoice Number: {invoice_number}
- Amount: {amount}
- Period: {period}
- Due Date: {due_date}

View Invoice: {invoice_url}

Payment Methods:
- Credit Card
- Bank Transfer
- PayPal

If you have any questions about your invoice, please contact our billing team.

Best regards,
The 1ai-social Team

---
{unsubscribe_link}
""",
    },
    "payment_failed": {
        "subject": "Payment Failed - Action Required",
        "body": """Hi {name},

We attempted to process your payment on {attempt_date}, but it failed.

Reason: {failure_reason}

Please update your payment method to avoid service interruption:
- Update Payment: {payment_url}

Your service will be suspended on {suspension_date} if payment is not received.

Need help? Contact our support team immediately.

Best regards,
The 1ai-social Team

---
{unsubscribe_link}
""",
    },
    "trial_expiring": {
        "subject": "Your Trial Expires Soon",
        "body": """Hi {name},

Your free trial expires in {days_remaining} days.

Trial Expiration Date: {expiration_date}

Upgrade now to continue using 1ai-social:
- View Plans: {pricing_url}
- Upgrade Account: {upgrade_url}

Special Offer: Use code TRIAL20 for 20% off your first month!

Questions? Our team is here to help.

Best regards,
The 1ai-social Team

---
{unsubscribe_link}
""",
    },
    "team_invite": {
        "subject": "{inviter_name} invited you to join {team_name} on 1ai-social",
        "body": """Hi {invitee_name},

{inviter_name} has invited you to join the team "{team_name}" on 1ai-social.

Accept Invitation: {invite_url}

This invitation expires in 7 days.

If you don't have a 1ai-social account yet, you can create one here: {signup_url}

Best regards,
The 1ai-social Team

---
{unsubscribe_link}
""",
    },
}


class EmailProvider(ABC):
    @abstractmethod
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        pass


class SMTPEmailProvider(EmailProvider):
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = to
            msg["Subject"] = subject

            if bcc:
                msg["Bcc"] = ", ".join(bcc)

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                recipients = [to]
                if bcc:
                    recipients.extend(bcc)
                server.sendmail(self.from_email, recipients, msg.as_string())

            logger.info(f"Email sent successfully to {to}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {str(e)}")
            return False


class SESEmailProvider(EmailProvider):
    def __init__(self, region: str = "us-east-1"):
        try:
            import boto3

            self.client = boto3.client("ses", region_name=region)
        except ImportError:
            raise ImportError("boto3 is required for SES email provider")

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        try:
            destination = {"ToAddresses": [to]}
            if bcc:
                destination["BccAddresses"] = bcc

            self.client.send_email(
                Source=os.getenv("SES_FROM_EMAIL", "noreply@1ai-social.com"),
                Destination=destination,
                Message={
                    "Subject": {"Data": subject},
                    "Body": {"Text": {"Data": body}},
                },
            )

            logger.info(f"Email sent successfully to {to} via SES")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to} via SES: {str(e)}")
            return False


class EmailQueue:
    def __init__(self, max_retries: int = 3, retry_delay_seconds: int = 300):
        self.queue: List[Dict[str, Any]] = []
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def add(
        self,
        to: str,
        subject: str,
        body: str,
        bcc: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        email_id = str(uuid.uuid4())
        self.queue.append(
            {
                "id": email_id,
                "to": to,
                "subject": subject,
                "body": body,
                "bcc": bcc or [],
                "metadata": metadata or {},
                "retries": 0,
                "created_at": datetime.utcnow(),
                "next_retry_at": datetime.utcnow(),
                "status": "pending",
            }
        )
        logger.info(f"Email {email_id} added to queue for {to}")
        return email_id

    def process(self, provider: EmailProvider) -> Dict[str, int]:
        results = {"sent": 0, "failed": 0, "retried": 0}

        for email in self.queue[:]:
            if email["status"] == "sent":
                continue

            if email["next_retry_at"] > datetime.utcnow():
                continue

            success = provider.send(
                to=email["to"],
                subject=email["subject"],
                body=email["body"],
                bcc=email["bcc"] if email["bcc"] else None,
            )

            if success:
                email["status"] = "sent"
                results["sent"] += 1
                self.queue.remove(email)
                logger.info(f"Email {email['id']} sent successfully")
            else:
                email["retries"] += 1
                if email["retries"] >= self.max_retries:
                    email["status"] = "failed"
                    results["failed"] += 1
                    self.queue.remove(email)
                    logger.error(
                        f"Email {email['id']} failed after {self.max_retries} retries"
                    )
                else:
                    email["next_retry_at"] = datetime.utcnow() + timedelta(
                        seconds=self.retry_delay_seconds
                    )
                    results["retried"] += 1
                    logger.warning(
                        f"Email {email['id']} retry {email['retries']}/{self.max_retries}"
                    )

        return results

    def get_status(self, email_id: str) -> Optional[Dict[str, Any]]:
        for email in self.queue:
            if email["id"] == email_id:
                return {
                    "id": email["id"],
                    "status": email["status"],
                    "retries": email["retries"],
                    "created_at": email["created_at"].isoformat(),
                }
        return None


def generate_unsubscribe_link(user_id: str, email: str, base_url: str = None) -> str:
    if base_url is None:
        base_url = os.getenv("APP_BASE_URL", "https://1ai-social.com")

    params = {
        "user_id": user_id,
        "email": email,
        "token": _generate_unsubscribe_token(user_id, email),
    }
    return f"{base_url}/unsubscribe?{urlencode(params)}"


def _generate_unsubscribe_token(user_id: str, email: str) -> str:
    import hashlib

    data = f"{user_id}:{email}:{os.getenv('UNSUBSCRIBE_SECRET', 'default-secret')}"
    return hashlib.sha256(data.encode()).hexdigest()


def send_email(
    to: str,
    subject: str,
    template: str,
    data: Dict[str, Any],
    bcc: Optional[List[str]] = None,
    provider: Optional[EmailProvider] = None,
    queue: Optional[EmailQueue] = None,
    use_queue: bool = False,
) -> bool:
    if template not in EMAIL_TEMPLATES:
        logger.error(f"Template '{template}' not found")
        return False

    template_config = EMAIL_TEMPLATES[template]
    body = template_config["body"]
    subject = template_config["subject"]

    data.setdefault(
        "unsubscribe_link",
        generate_unsubscribe_link(
            data.get("user_id", "unknown"),
            to,
        ),
    )

    try:
        body = body.format(**data)
        subject = subject.format(**data)
    except KeyError as e:
        logger.error(f"Missing template variable: {str(e)}")
        return False

    if use_queue and queue:
        queue.add(to=to, subject=subject, body=body, bcc=bcc, metadata=data)
        return True

    if provider is None:
        provider = _get_default_provider()

    if provider is None:
        logger.error("No email provider configured")
        return False

    return provider.send(to=to, subject=subject, body=body, bcc=bcc)


def _get_default_provider() -> Optional[EmailProvider]:
    provider_type = os.getenv("EMAIL_PROVIDER", "smtp").lower()

    if provider_type == "ses":
        try:
            return SESEmailProvider(region=os.getenv("AWS_REGION", "us-east-1"))
        except Exception as e:
            logger.error(f"Failed to initialize SES provider: {str(e)}")
            return None

    elif provider_type == "smtp":
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@1ai-social.com")

        if not all([smtp_host, smtp_user, smtp_password]):
            logger.error("SMTP configuration incomplete")
            return None

        return SMTPEmailProvider(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            from_email=from_email,
        )

    logger.error(f"Unknown email provider: {provider_type}")
    return None
