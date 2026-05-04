import unittest
import sys
import types
from unittest.mock import Mock, patch

if "pydantic_settings" not in sys.modules:
    pydantic_settings = types.ModuleType("pydantic_settings")

    class BaseSettings:
        pass

    def SettingsConfigDict(**kwargs):
        return kwargs

    pydantic_settings.BaseSettings = BaseSettings
    pydantic_settings.SettingsConfigDict = SettingsConfigDict
    sys.modules["pydantic_settings"] = pydantic_settings

if "pydantic" not in sys.modules:
    pydantic = types.ModuleType("pydantic")

    class BaseModel:
        pass

    def Field(*args, **kwargs):
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return args[0] if args else kwargs.get("default", None)

    pydantic.BaseModel = BaseModel
    pydantic.EmailStr = str
    pydantic.Field = Field
    sys.modules["pydantic"] = pydantic

security = types.ModuleType("app.services.security")
security.decrypt_secret = lambda value: value or ""
sys.modules["app.services.security"] = security

from app.services.email import SmtpSettings, validate_smtp


def smtp_settings(port: int, use_tls: bool = True) -> SmtpSettings:
    return SmtpSettings(
        smtp_host="smtp.example.test",
        smtp_port=port,
        smtp_username="user",
        smtp_password="secret",
        sender_email="sender@example.test",
        recipient_email="recipient@example.test",
        use_tls=use_tls,
    )


class SmtpConnectionTests(unittest.TestCase):
    def test_port_465_uses_implicit_tls(self) -> None:
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=None)

        with patch("app.services.email.smtplib.SMTP_SSL", return_value=smtp) as smtp_ssl, patch(
            "app.services.email.smtplib.SMTP"
        ) as smtp_plain:
            validate_smtp(smtp_settings(465))

        smtp_ssl.assert_called_once_with("smtp.example.test", 465, timeout=15)
        smtp_plain.assert_not_called()
        smtp.starttls.assert_not_called()
        smtp.login.assert_called_once_with("user", "secret")

    def test_starttls_port_uses_plain_smtp_then_starttls(self) -> None:
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=None)

        with patch("app.services.email.smtplib.SMTP", return_value=smtp) as smtp_plain, patch(
            "app.services.email.smtplib.SMTP_SSL"
        ) as smtp_ssl:
            validate_smtp(smtp_settings(587))

        smtp_plain.assert_called_once_with("smtp.example.test", 587, timeout=15)
        smtp_ssl.assert_not_called()
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("user", "secret")


if __name__ == "__main__":
    unittest.main()
