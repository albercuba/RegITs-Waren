import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import get_db, utc_timestamp
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
        raise HTTPException(status_code=400, detail="Nur Bilddateien sind erlaubt")


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
                raise HTTPException(status_code=413, detail=f"Bild überschreitet {get_settings().max_upload_mb} MB Limit")
            output.write(chunk)
    return target


def _store_scan_debug(path: Path, result: dict) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scan_debug (
                created_at, image_path, raw_text, normalized_text, barcodes, candidates,
                best_guess_serial, confidence_score, fields
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                utc_timestamp(),
                str(path),
                result.get("raw_text", ""),
                result.get("serial_debug", {}).get("normalized_text", ""),
                json.dumps(result.get("barcodes", []), ensure_ascii=False),
                json.dumps(result.get("serial_candidates", []), ensure_ascii=False),
                result.get("best_guess_serial", ""),
                result.get("confidence_score", 0),
                json.dumps(result.get("fields", {}), ensure_ascii=False),
            ),
        )
        return cursor.lastrowid


@router.post("/scan")
def scan_label(photo: UploadFile = File(...)) -> dict:
    path = _save_upload(photo, "scan")
    result = scan_image(path)
    result["debug_id"] = _store_scan_debug(path, result)
    return result


@router.post("/scan/debug")
def scan_label_debug(photo: UploadFile = File(...)) -> dict:
    path = _save_upload(photo, "scan-debug")
    result = scan_image(path)
    result["debug_id"] = _store_scan_debug(path, result)
    return result


@router.get("/scan/debug/{debug_id}")
def get_scan_debug(debug_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM scan_debug WHERE id = ?", (debug_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Debug-Daten nicht gefunden")
    data = dict(row)
    for key in ("barcodes", "candidates", "fields"):
        data[key] = json.loads(data[key] or "[]" if key != "fields" else data[key] or "{}")
    data["image_file"] = Path(data["image_path"]).name
    data["image_url"] = f"/api/uploads/{data['image_file']}"
    return data


@router.post("/submissions")
def create_submission(metadata: str = Form(...), photo: UploadFile = File(...)) -> dict:
    try:
        payload = IntakeMetadata(**json.loads(metadata))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Ungültige Metadaten") from exc

    image_path = _save_upload(photo, "intake")
    created_at = utc_now()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO submissions (
                created_at, serial_number, asset_type, vendor, model, received_by, notes, image_path,
                raw_text, detected_candidates, user_corrected_serial
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                payload.detected_candidates,
                payload.serial_number,
            ),
        )
        submission_id = cursor.lastrowid

    try:
        send_intake_email(payload, image_path, created_at)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Eintrag gespeichert, aber E-Mail-Versand fehlgeschlagen: {exc}") from exc

    return {"id": submission_id, "created_at": created_at, "image_path": image_path.name}


@router.get("/submissions")
def list_submissions(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
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
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    return FileResponse(path)
