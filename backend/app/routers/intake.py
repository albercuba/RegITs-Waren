import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import get_db
from app.models.schemas import IntakeMetadata
from app.services.email import send_intake_email, utc_now
from app.services.ocr import scan_image

router = APIRouter(prefix="/api", tags=["intake"])


def _upload_dir() -> Path:
    path = Path(get_settings().upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"} else ".jpg"


def _validate_image(upload: UploadFile) -> None:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")


def _save_upload(upload: UploadFile, prefix: str) -> Path:
    _validate_image(upload)
    limit = get_settings().max_upload_mb * 1024 * 1024
    target = _upload_dir() / f"{prefix}-{uuid.uuid4().hex}{_extension(upload.filename or '')}"
    size = 0
    with target.open("wb") as output:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                output.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"Image exceeds {get_settings().max_upload_mb} MB limit")
            output.write(chunk)
    return target


@router.post("/scan")
def scan_label(photo: UploadFile = File(...)) -> dict:
    path = _save_upload(photo, "scan")
    return scan_image(path)


@router.post("/submissions")
def create_submission(metadata: str = Form(...), photo: UploadFile = File(...)) -> dict:
    try:
        payload = IntakeMetadata(**json.loads(metadata))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid metadata") from exc

    image_path = _save_upload(photo, "intake")
    created_at = utc_now()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO submissions (
                created_at, serial_number, asset_type, vendor, model, received_by, notes, image_path, raw_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                payload.serial_number,
                payload.asset_type,
                payload.vendor,
                payload.model,
                payload.received_by,
                payload.notes,
                str(image_path),
                payload.raw_text,
            ),
        )
        submission_id = cursor.lastrowid

    try:
        send_intake_email(payload, image_path, created_at)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Submission saved, but email failed: {exc}") from exc

    return {"id": submission_id, "created_at": created_at, "image_path": image_path.name}


@router.get("/submissions")
def list_submissions(limit: int = 20) -> list[dict]:
    limit = min(max(limit, 1), 100)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM submissions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) | {"image_file": Path(row["image_path"]).name} for row in rows]


@router.get("/uploads/{filename}")
def get_upload(filename: str) -> FileResponse:
    path = (_upload_dir() / Path(filename).name).resolve()
    upload_root = _upload_dir().resolve()
    if upload_root not in path.parents or not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
