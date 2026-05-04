import json
import os
import shutil
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

os.environ["CORS_ORIGINS"] = "http://allowed.example,http://localhost:8081"

from app.config import get_settings
from app.database import init_db
from app.main import app

ADMIN_PASSWORD = "test-admin-password"


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (16, 16), "white").save(output, format="JPEG")
    return output.getvalue()


class ApiStartupTests(unittest.TestCase):
    def setUp(self) -> None:
        test_root = Path.cwd() / ".test-data"
        test_root.mkdir(exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp(dir=test_root))
        root = self.temp_dir
        os.environ["DATABASE_PATH"] = str(root / "regits-test.db")
        os.environ["UPLOAD_DIR"] = str(root / "uploads")
        os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD
        os.environ["APP_SECRET_KEY"] = "test-secret"
        os.environ["MAX_UPLOAD_MB"] = "1"
        os.environ["CORS_ORIGINS"] = "http://allowed.example,http://localhost:8081"
        get_settings.cache_clear()
        init_db()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        get_settings.cache_clear()

    @property
    def admin_headers(self) -> dict[str, str]:
        return {"X-Admin-Password": ADMIN_PASSWORD}

    def test_app_imports_and_health_works(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_public_locations_endpoint_works(self) -> None:
        response = self.client.get("/api/locations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_admin_locations_save_and_load(self) -> None:
        save_response = self.client.post(
            "/api/admin/locations",
            json={"locations": ["Friedrichshafen", "Ravensburg"]},
            headers=self.admin_headers,
        )
        load_response = self.client.get("/api/admin/locations", headers=self.admin_headers)

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(load_response.status_code, 200)
        self.assertEqual(load_response.json(), {"locations": ["Friedrichshafen", "Ravensburg"]})

    def test_admin_password_is_required(self) -> None:
        missing_response = self.client.get("/api/admin/locations")
        invalid_response = self.client.get("/api/admin/locations", headers={"X-Admin-Password": "wrong"})

        self.assertEqual(missing_response.status_code, 401)
        self.assertEqual(invalid_response.status_code, 401)

    def test_submission_accepts_location_metadata(self) -> None:
        metadata = {
            "serial_number": "ABC123456",
            "asset_type": "Monitor",
            "vendor": "iiyama",
            "model": "X2491H-B1",
            "received_by": "Test User",
            "location": "Ravensburg",
            "notes": "",
        }
        files = {"photos": ("label.jpg", image_bytes(), "image/jpeg")}

        with patch("app.routers.intake.send_intake_email", return_value=None):
            response = self.client.post(
                "/api/submissions",
                data={"metadata": json.dumps(metadata)},
                files=files,
            )

        self.assertEqual(response.status_code, 200)
        submissions = self.client.get("/api/submissions", headers=self.admin_headers)
        self.assertEqual(submissions.status_code, 200)
        self.assertEqual(submissions.json()[0]["location"], "Ravensburg")

    def test_valid_small_image_scan_is_accepted(self) -> None:
        with patch(
            "app.routers.intake.scan_image",
            return_value={
                "fields": {},
                "raw_text": "",
                "serial_debug": {},
                "barcodes": [],
                "serial_candidates": [],
            },
        ):
            response = self.client.post(
                "/api/scan",
                files={"photo": ("label.jpg", image_bytes(), "image/jpeg")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("debug_id", response.json())

    def test_spoofed_image_upload_is_rejected(self) -> None:
        response = self.client.post(
            "/api/scan",
            files={"photo": ("not-image.jpg", b"this is not an image", "image/jpeg")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Ungültige Bilddatei", response.json()["detail"])

    def test_oversized_upload_is_rejected(self) -> None:
        response = self.client.post(
            "/api/scan",
            files={"photo": ("large.jpg", b"0" * (1024 * 1024 + 1), "image/jpeg")},
        )

        self.assertEqual(response.status_code, 413)

    def test_debug_and_upload_endpoints_require_admin(self) -> None:
        response = self.client.get("/api/scan/debug/1")
        upload_response = self.client.get("/api/uploads/example.jpg")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(upload_response.status_code, 401)

    def test_cors_allowed_origin_is_echoed(self) -> None:
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://allowed.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://allowed.example")

    def test_cors_blocked_origin_is_not_allowed(self) -> None:
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://blocked.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
