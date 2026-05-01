import unittest

from app.services.parser import parse_label_data_with_debug


class SerialExtractionTests(unittest.TestCase):
    def assert_serial(self, text: str, expected: str) -> None:
        fields, debug = parse_label_data_with_debug(text, [])
        self.assertEqual(fields["serial_number"], expected)
        self.assertGreaterEqual(debug["confidence"], 0.7)

    def test_logitech_sn_colon_without_space(self) -> None:
        self.assert_serial("S/N:2601TVZ1C6D9", "2601TVZ1C6D9")

    def test_ocr_split_sn_label(self) -> None:
        self.assert_serial("S N 2601TVZ1C6D9", "2601TVZ1C6D9")

    def test_ocr_short_serial_label(self) -> None:
        self.assert_serial("SER NO 8CC3459KLM", "8CC3459KLM")

    def test_hp_dock_prefers_sn_over_part_and_mac(self) -> None:
        self.assert_serial(
            "\n".join(
                [
                    "HP USB-C Dock G5",
                    "P/N N59407-001",
                    "S/N 1H9523ZM9L",
                    "MAC: 98:A4:4E:88:72:C9",
                ]
            ),
            "1H9523ZM9L",
        )

    def test_iiyama_numeric_sn(self) -> None:
        self.assert_serial(
            "\n".join(
                [
                    "ProLite X2491H",
                    "S/N: 1278360205091",
                    "Part Code X2491H-B1",
                ]
            ),
            "1278360205091",
        )

    def test_german_ser_nr_label(self) -> None:
        self.assert_serial(
            "\n".join(
                [
                    "Hersteller: Lenovo",
                    "Modell: ThinkPad USB-C Dock",
                    "Ser.-Nr.: PF4ABC123",
                    "Art.-Nr.: 40AY0090EU",
                ]
            ),
            "PF4ABC123",
        )

    def test_german_seriennummer_label(self) -> None:
        self.assert_serial("Serien-Nr. R90X7A2B", "R90X7A2B")

    def test_serial_barcode_is_confident_without_label_text(self) -> None:
        fields, debug = parse_label_data_with_debug("Logitech MK295", ["2601TVZ1C6D9"])

        self.assertEqual(fields["serial_number"], "2601TVZ1C6D9")
        self.assertGreaterEqual(debug["confidence"], 0.7)


if __name__ == "__main__":
    unittest.main()
