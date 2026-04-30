from pydantic import BaseModel, EmailStr, Field


class IntakeMetadata(BaseModel):
    serial_number: str = ""
    asset_type: str = ""
    vendor: str = ""
    model: str = ""
    received_by: str = ""
    notes: str = ""
    raw_text: str = ""


class EmailSettingsIn(BaseModel):
    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(gt=0, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: EmailStr
    recipient_email: EmailStr
    use_tls: bool = True


class EmailSettingsOut(BaseModel):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    sender_email: str = ""
    recipient_email: str = ""
    use_tls: bool = True
    password_configured: bool = False
