import tempfile
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

try:
    import app.config  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name != "pydantic_settings":
        raise
    config_module = types.ModuleType("app.config")

    class TestSettings:
        ocr_max_dimension = 1800
        paddleocr_lang = "german"
        paddleocr_use_angle_cls = True
        paddleocr_min_confidence = 0.35

    config_module.get_settings = lambda: TestSettings()
    sys.modules["app.config"] = config_module

from app.services import ocr


class FakePaddleEngine:
    def __init__(self, result):
        self.result = result
        self.seen_path_exists = False

    def ocr(self, image_path, cls=True):
        self.seen_path_exists = Path(image_path).exists()
        return self.result


class PaddleOcrServiceTests(unittest.TestCase):
    def test_paddleocr_lines_are_plain_text_with_metadata(self) -> None:
        fake_engine = FakePaddleEngine(
            [
                [
                    ([[0, 0], [10, 0], [10, 10], [0, 10]], ("HP USB-C Dock G5", 0.94)),
                    ([[0, 12], [10, 12], [10, 22], [0, 22]], ("S/N 1H9523ZM9L", 0.88)),
                    ([[0, 24], [10, 24], [10, 34], [0, 34]], ("noise", 0.12)),
                ]
            ]
        )

        with patch("app.services.ocr.get_ocr_engine", return_value=fake_engine):
            text, metadata = ocr._ocr_text_from_image(Image.new("RGB", (40, 40), "white"))

        self.assertTrue(fake_engine.seen_path_exists)
        self.assertEqual(text, "HP USB-C Dock G5\nS/N 1H9523ZM9L")
        self.assertEqual([item["text"] for item in metadata], ["HP USB-C Dock G5", "S/N 1H9523ZM9L"])
        self.assertEqual(metadata[1]["confidence"], 0.88)

    def test_scan_image_keeps_api_shape_and_barcode_serial(self) -> None:
        fake_engine = FakePaddleEngine([[([[0, 0], [1, 0], [1, 1], [0, 1]], ("Logitech MK295", 0.9))]])

        with tempfile.NamedTemporaryFile(suffix=".png") as image_file:
            Image.new("RGB", (40, 40), "white").save(image_file.name)
            with (
                patch("app.services.ocr.get_ocr_engine", return_value=fake_engine),
                patch("app.services.ocr._decode_barcodes", return_value=["2601TVZ1C6D9"]),
            ):
                result = ocr.scan_image(Path(image_file.name))

        self.assertEqual(result["status"], "fields_detected")
        self.assertEqual(result["fields"]["serial_number"], "2601TVZ1C6D9")
        self.assertEqual(result["barcodes"], ["2601TVZ1C6D9"])
        self.assertIn("raw_text", result)
        self.assertIn("raw_ocr_text", result)
        self.assertIn("serial_debug", result)
        self.assertEqual(result["ocr_lines"][0]["text"], "Logitech MK295")

    def test_scan_image_reports_ocr_error_without_crashing(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".png") as image_file:
            Image.new("RGB", (40, 40), "white").save(image_file.name)
            with patch("app.services.ocr.get_ocr_engine", side_effect=RuntimeError("model missing")):
                result = ocr.scan_image(Path(image_file.name))

        self.assertEqual(result["status"], "manual_input_required")
        self.assertIn("model missing", result["ocr_error"])
        self.assertEqual(result["raw_text"], "")


if __name__ == "__main__":
    unittest.main()
