import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from app.services.barcode_candidates import classify_barcode_candidates
from app.services.ocr import scan_image


def write_test_image(path: Path) -> None:
    Image.new("RGB", (24, 24), "white").save(path, format="JPEG")


class BarcodeFirstTests(unittest.TestCase):
    def scan_with_barcodes(self, barcodes: list[str], ocr_text: str = "S/N OCR123456") -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "label.jpg"
            write_test_image(path)
            with (
                patch("app.services.ocr._decode_barcodes_fast", return_value=barcodes),
                patch("app.services.ocr._decode_barcodes_deep", return_value=barcodes),
                patch("app.services.ocr._ocr_text", return_value=ocr_text) as ocr_text_mock,
                patch("app.services.ocr._ocr_fallback_text", return_value=""),
            ):
                result = scan_image(path)
            result["_ocr_text_called"] = ocr_text_mock.called
            return result

    def test_no_barcodes_runs_tesseract(self) -> None:
        result = self.scan_with_barcodes([], "S/N OCR123456")

        self.assertTrue(result["_ocr_text_called"])
        self.assertFalse(result["ocr_skipped"])

    def test_one_strong_serial_barcode_skips_tesseract(self) -> None:
        result = self.scan_with_barcodes(["ABC123456"])

        self.assertFalse(result["_ocr_text_called"])
        self.assertTrue(result["ocr_skipped"])
        self.assertEqual(result["skip_reason"], "confident_barcode")
        self.assertEqual(result["fields"]["serial_number"], "ABC123456")

    def test_clear_strong_serial_among_multiple_barcodes_can_skip_tesseract(self) -> None:
        result = self.scan_with_barcodes(["ABC123456", "5099206092372"])

        self.assertFalse(result["_ocr_text_called"])
        self.assertTrue(result["ocr_skipped"])
        self.assertEqual(result["fields"]["serial_number"], "ABC123456")

    def test_ambiguous_multiple_barcodes_runs_tesseract(self) -> None:
        result = self.scan_with_barcodes(["ABC123456", "XYZ987654"], "S/N ABC123456")

        self.assertTrue(result["_ocr_text_called"])
        self.assertFalse(result["ocr_skipped"])

    def test_ean_upc_barcode_is_not_used_as_serial(self) -> None:
        result = self.scan_with_barcodes(["5099206092372"], "")

        self.assertTrue(result["_ocr_text_called"])
        self.assertNotEqual(result["fields"]["serial_number"], "5099206092372")
        self.assertEqual(result["barcode_candidates"][0]["kind"], "ean_upc")

    def test_mac_barcode_is_not_used_as_serial(self) -> None:
        result = self.scan_with_barcodes(["AA:BB:CC:DD:EE:FF"], "")

        self.assertTrue(result["_ocr_text_called"])
        self.assertNotEqual(result["fields"]["serial_number"], "AA:BB:CC:DD:EE:FF")
        self.assertEqual(result["barcode_candidates"][0]["kind"], "mac")

    def test_ocr_text_near_serial_label_boosts_matching_barcode(self) -> None:
        candidates = classify_barcode_candidates(["ABC123456"], "Device\nS/N: ABC123456", "")

        self.assertGreaterEqual(candidates[0]["score"], 80)
        self.assertIn("near serial label in OCR text", candidates[0]["reasons"])

    def test_ocr_text_near_part_or_model_label_penalizes_matching_barcode(self) -> None:
        candidates = classify_barcode_candidates(["ABC123456"], "Model: ABC123456", "")

        self.assertLess(candidates[0]["score"], 50)
        self.assertIn("near non-serial label in OCR text", candidates[0]["reasons"])

    def test_response_includes_barcode_candidates(self) -> None:
        result = self.scan_with_barcodes(["ABC123456"])

        self.assertIn("barcode_candidates", result)
        self.assertEqual(result["barcode_candidates"][0]["normalized"], "ABC123456")


if __name__ == "__main__":
    unittest.main()
