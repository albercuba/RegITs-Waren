import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from app.database import get_db
from app.models.schemas import EmailSettingsIn, IntakeMetadata
from app.services.security import decrypt_secret


@dataclass
class SmtpSettings:
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    sender_email: str
    recipient_email: str
    use_tls: bool


def load_smtp_settings() -> SmtpSettings | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()

    if row:
        return SmtpSettings(
            smtp_host=row["smtp_host"],
            smtp_port=row["smtp_port"],
            smtp_username=row["smtp_username"] or "",
            smtp_password=decrypt_secret(row["smtp_password_encrypted"]),
            sender_email=row["sender_email"],
            recipient_email=row["recipient_email"],
            use_tls=bool(row["use_tls"]),
        )

    return None



def validate_smtp(settings: SmtpSettings) -> None:
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.ehlo()
        if settings.use_tls:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)


def settings_from_payload(payload: EmailSettingsIn) -> SmtpSettings:
    return SmtpSettings(
        smtp_host=payload.smtp_host,
        smtp_port=payload.smtp_port,
        smtp_username=payload.smtp_username,
        smtp_password=payload.smtp_password,
        sender_email=str(payload.sender_email),
        recipient_email=str(payload.recipient_email),
        use_tls=payload.use_tls,
    )


def send_test_email(settings: SmtpSettings) -> None:
    message = EmailMessage()
    message["Subject"] = "RegITs-Waren SMTP test"
    message["From"] = settings.sender_email
    message["To"] = settings.recipient_email
    message.set_content("SMTP settings are working.")
    _send_message(settings, message)


def send_intake_email(metadata: IntakeMetadata, image_path: Path, created_at: str) -> None:
    settings = load_smtp_settings()
    if not settings:
        raise RuntimeError("SMTP settings are not configured")

    message = EmailMessage()
    serial = metadata.serial_number or "No serial"
    message["Subject"] = f"Hardware intake: {serial}"
    message["From"] = settings.sender_email
    message["To"] = settings.recipient_email
    body = "\n".join(
        [
            "New hardware intake submission",
            "",
            f"Timestamp: {created_at}",
            f"Serial number: {metadata.serial_number}",
            f"Asset type: {metadata.asset_type}",
            f"Vendor: {metadata.vendor}",
            f"Model: {metadata.model}",
            f"Received by: {metadata.received_by}",
            f"Notes: {metadata.notes}",
        ]
    )
    message.set_content(body)
    data = image_path.read_bytes()
    message.add_attachment(data, maintype="image", subtype=image_path.suffix.lstrip(".") or "jpeg", filename=image_path.name)
    _send_message(settings, message)


def _send_message(settings: SmtpSettings, message: EmailMessage) -> None:
    validate_smtp(settings)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.ehlo()
        if settings.use_tls:
            smtp.starttls()
            smtp.ehlo()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
