import json
import smtplib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models.schemas import EmailSettingsIn, EmailSettingsOut, LocationsIn, LocationsOut
from app.services.email import send_test_email, settings_from_payload, validate_smtp
from app.services.security import decrypt_secret, encrypt_secret, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _smtp_error_detail(prefix: str, exc: Exception) -> str:
    message = str(exc).strip()
    return f"{prefix}: {message}" if message else prefix


def _parse_locations(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        locations = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(locations, list):
        return []
    return [str(location).strip() for location in locations if str(location).strip()]


def _clean_locations(locations: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for location in locations:
        value = str(location).strip()
        key = value.casefold()
        if value and key not in seen:
            cleaned.append(value)
            seen.add(key)
    return cleaned


def _public_settings(row) -> EmailSettingsOut:
    if not row:
        return EmailSettingsOut()
    return EmailSettingsOut(
        smtp_host=row["smtp_host"],
        smtp_port=row["smtp_port"],
        smtp_username=row["smtp_username"] or "",
        sender_email=row["sender_email"],
        recipient_email=row["recipient_email"],
        use_tls=bool(row["use_tls"]),
        password_configured=bool(row["smtp_password_encrypted"]),
    )


def _load_locations() -> list[str]:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'intake_locations'").fetchone()
        if row:
            return _parse_locations(row["value"])
        legacy = conn.execute("SELECT locations FROM email_settings WHERE id = 1").fetchone()
    return _parse_locations(legacy["locations"] if legacy else "")


def _save_locations(locations: list[str]) -> list[str]:
    cleaned = _clean_locations(locations)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('intake_locations', ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (json.dumps(cleaned, ensure_ascii=False), now),
        )
    return cleaned


@router.get("/email-settings", response_model=EmailSettingsOut)
def get_email_settings() -> EmailSettingsOut:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()
    return _public_settings(row)


@router.get("/locations", response_model=LocationsOut)
def get_locations() -> LocationsOut:
    return LocationsOut(locations=_load_locations())


@router.post("/locations", response_model=LocationsOut)
def save_locations(payload: LocationsIn) -> LocationsOut:
    return LocationsOut(locations=_save_locations(payload.locations))


@router.post("/email-settings", response_model=EmailSettingsOut)
def save_email_settings(payload: EmailSettingsIn) -> EmailSettingsOut:
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()

    settings = settings_from_payload(payload)
    existing_password = (
        decrypt_secret(existing["smtp_password_encrypted"]) if existing and not payload.smtp_password else ""
    )
    if existing_password:
        settings.smtp_password = existing_password

    try:
        validate_smtp(settings)
    except smtplib.SMTPAuthenticationError as exc:
        raise HTTPException(
            status_code=400, detail=_smtp_error_detail("Authentifizierung fehlgeschlagen", exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_smtp_error_detail("SMTP-Verbindung fehlgeschlagen", exc)) from exc

    encrypted_password = encrypt_secret(payload.smtp_password or existing_password)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO email_settings (
                id, smtp_host, smtp_port, smtp_username, smtp_password_encrypted,
                sender_email, recipient_email, use_tls, updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                smtp_host = excluded.smtp_host,
                smtp_port = excluded.smtp_port,
                smtp_username = excluded.smtp_username,
                smtp_password_encrypted = excluded.smtp_password_encrypted,
                sender_email = excluded.sender_email,
                recipient_email = excluded.recipient_email,
                use_tls = excluded.use_tls,
                updated_at = excluded.updated_at
            """,
            (
                payload.smtp_host,
                payload.smtp_port,
                payload.smtp_username,
                encrypted_password,
                str(payload.sender_email),
                str(payload.recipient_email),
                int(payload.use_tls),
                now,
            ),
        )
        row = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()
    return _public_settings(row)


@router.post("/email-settings/test")
def test_email_settings(payload: EmailSettingsIn) -> dict[str, str]:
    settings = settings_from_payload(payload)
    if not payload.smtp_password:
        with get_db() as conn:
            existing = conn.execute("SELECT * FROM email_settings WHERE id = 1").fetchone()
        if existing:
            settings.smtp_password = decrypt_secret(existing["smtp_password_encrypted"])

    try:
        send_test_email(settings)
    except smtplib.SMTPAuthenticationError as exc:
        raise HTTPException(
            status_code=400, detail=_smtp_error_detail("Authentifizierung fehlgeschlagen", exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_smtp_error_detail("SMTP-Verbindung fehlgeschlagen", exc)) from exc
    return {"message": "Test-E-Mail gesendet"}
