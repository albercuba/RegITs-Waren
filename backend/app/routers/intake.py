import json
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import get_settings
from app.database import get_db, utc_timestamp
from app.models.schemas import IntakeMetadata
from app.services.email import send_intake_email, utc_now
from app.services.ocr import scan_image
from app.services.security import require_admin

router = APIRouter(prefix="/api", tags=["intake"])


def _upload_dir() -> Path:
    path = Path(get_settings().upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


IMAGE_FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "BMP": ".bmp",
    "GIF": ".gif",
}


def _validate_image(upload: UploadFile) -> None:
    if not upload.content_type or not upload.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Nur Bilddateien sind erlaubt")


def _read_upload_bytes(upload: UploadFile) -> bytes:
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail=f"Bild überschreitet {get_settings().max_upload_mb} MB Limit")
    return data


def _load_verified_image(data: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        image = Image.open(BytesIO(data))
        if image.format not in IMAGE_FORMAT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Nicht unterstütztes Bildformat")
        return ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Ungültige Bilddatei") from exc


def _store_sanitized_image(image: Image.Image, target: Path) -> None:
    if image.format == "JPEG" and image.mode not in {"RGB", "L"}:
        image = image.convert("RGB")
    save_kwargs = {"format": image.format}
    image.save(target, **save_kwargs)


def _save_upload(upload: UploadFile, prefix: str) -> Path:
    _validate_image(upload)
    image = _load_verified_image(_read_upload_bytes(upload))
    suffix = IMAGE_FORMAT_EXTENSIONS.get(image.format, ".jpg")
    target = _upload_dir() / f"{prefix}-{uuid.uuid4().hex}{suffix}"
    try:
        _store_sanitized_image(image, target)
    except OSError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Bild konnte nicht gespeichert werden") from exc
    return target


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


def _is_truthy(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on"}


def _store_scan_debug(path: Path, result: dict, ocr_cropped: bool = False, mode: str = "fast") -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO scan_debug (
                created_at, image_path, raw_text, normalized_text, barcodes, candidates,
                best_guess_serial, confidence_score, fields, ocr_cropped
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1 if ocr_cropped else 0,
            ),
        )
        return cursor.lastrowid


@router.post("/scan")
def scan_label(
    photo: UploadFile = File(...),
    ocr_cropped: str | None = Form(default=None),
    mode: str = Form(default="fast"),
    x_ocr_cropped: str | None = Header(default=None, alias="X-OCR-Cropped"),
) -> dict:
    cropped = _is_truthy(ocr_cropped) or _is_truthy(x_ocr_cropped)
    path = _save_upload(photo, "scan")
    result = scan_image(path, mode=mode)
    result["ocr_cropped"] = cropped
    result["mode"] = mode if mode in {"fast", "deep"} else "fast"
    result["debug_id"] = _store_scan_debug(path, result, cropped, result["mode"])
    return result


@router.post("/scan/debug", dependencies=[Depends(require_admin)])
def scan_label_debug(
    photo: UploadFile = File(...),
    ocr_cropped: str | None = Form(default=None),
    mode: str = Form(default="deep"),
    x_ocr_cropped: str | None = Header(default=None, alias="X-OCR-Cropped"),
) -> dict:
    cropped = _is_truthy(ocr_cropped) or _is_truthy(x_ocr_cropped)
    path = _save_upload(photo, "scan-debug")
    result = scan_image(path, mode=mode)
    result["ocr_cropped"] = cropped
    result["mode"] = mode if mode in {"fast", "deep"} else "deep"
    result["debug_id"] = _store_scan_debug(path, result, cropped, result["mode"])
    return result


@router.get("/scan/debug/{debug_id}", dependencies=[Depends(require_admin)])
def get_scan_debug(debug_id: int) -> dict:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM scan_debug WHERE id = ?", (debug_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Debug-Daten nicht gefunden")
    data = dict(row)
    for key in ("barcodes", "candidates", "fields"):
        data[key] = json.loads(data[key] or "[]" if key != "fields" else data[key] or "{}")
    data["ocr_cropped"] = bool(data.get("ocr_cropped"))
    data["image_file"] = Path(data["image_path"]).name
    data["image_url"] = f"/api/uploads/{data['image_file']}"
    return data


@router.get("/locations")
def list_locations() -> list[str]:
    with get_db() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'intake_locations'").fetchone()
        if row:
            return _parse_locations(row["value"])
        legacy = conn.execute("SELECT locations FROM email_settings WHERE id = 1").fetchone()
    return _parse_locations(legacy["locations"] if legacy else "")


@router.post("/submissions")
def create_submission(metadata: str = Form(...), photos: list[UploadFile] = File(...)) -> dict:
    try:
        payload = IntakeMetadata(**json.loads(metadata))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Ungültige Metadaten") from exc

    if not photos:
        raise HTTPException(status_code=400, detail="Mindestens ein Foto ist erforderlich")

    image_paths = [_save_upload(photo, "intake") for photo in photos]
    primary_image_path = image_paths[0]
    created_at = utc_now()
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO submissions (
                created_at, serial_number, asset_type, vendor, model, received_by, location, notes, image_path,
                raw_text, detected_candidates, user_corrected_serial, image_paths
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                payload.serial_number,
                payload.asset_type,
                payload.vendor,
                payload.model,
                payload.received_by,
                payload.location,
                payload.notes,
                str(primary_image_path),
                payload.raw_text,
                payload.detected_candidates,
                payload.serial_number,
                json.dumps([str(path) for path in image_paths], ensure_ascii=False),
            ),
        )
        submission_id = cursor.lastrowid

    try:
        send_intake_email(payload, image_paths, created_at)
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Eintrag gespeichert, aber E-Mail-Versand fehlgeschlagen: {exc}"
        ) from exc

    return {"id": submission_id, "created_at": created_at, "image_paths": [path.name for path in image_paths]}


@router.get("/submissions", dependencies=[Depends(require_admin)])
def list_submissions(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM submissions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) | {"image_file": Path(row["image_path"]).name} for row in rows]


@router.get("/uploads/{filename}", dependencies=[Depends(require_admin)])
def get_upload(filename: str) -> FileResponse:
    path = (_upload_dir() / Path(filename).name).resolve()
    upload_root = _upload_dir().resolve()
    if path.parent != upload_root or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Datei nicht gefunden")
    return FileResponse(path)
