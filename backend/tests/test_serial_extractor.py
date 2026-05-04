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

    def test_ubiquiti_u7_lr_label(self) -> None:
        fields, debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "Ubiquiti Inc.",
                    "ui.com",
                    "U7-LR",
                    "(RX)847848C64FB6",
                    "UPC",
                    "8 10177 16192 9",
                    "08/18/25",
                    "Made in Vietnam",
                ]
            ),
            [],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "U7-LR")
        self.assertEqual(fields["serial_number"], "847848C64FB6")
        self.assertEqual(fields["notes"], "UPC: 810177161929")
        self.assertEqual(debug["confidence"], 1.0)

    def test_ubiquiti_usw_lite_label(self) -> None:
        fields, _debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "Ubiquiti Inc.",
                    "ui.com",
                    "USW-Lite-8-PoE",
                    "(AK)58D61F517119",
                    "UPC",
                    "8 10010 07115 6",
                    "11/17/25",
                    "Made in China",
                ]
            ),
            [],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "USW-Lite-8-PoE")
        self.assertEqual(fields["serial_number"], "58D61F517119")
        self.assertEqual(fields["notes"], "UPC: 810010071156")

    def test_ubiquiti_upc_is_not_selected_as_serial_number(self) -> None:
        fields, debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "Ubiquiti Inc.",
                    "USW-Lite-8-PoE",
                    "(AK)58D61F517119",
                    "UPC",
                    "8 10010 07115 6",
                ]
            ),
            ["810010071156"],
        )

        self.assertEqual(fields["serial_number"], "58D61F517119")
        self.assertNotEqual(fields["serial_number"], "810010071156")
        self.assertEqual(fields["notes"], "UPC: 810010071156")
        self.assertEqual(debug["candidates"][0]["source"], "ubiquiti_identifier")

    def test_ubiquiti_serial_wins_over_model_barcode(self) -> None:
        fields, debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "GENUINE UBIQUITI PRODUCT",
                    "Ubiquiti Inc.",
                    "ui.com",
                    "USW-Lite-8-PoE",
                    "(AK)58D61F517119",
                    "UPC",
                    "8 10010 07115 6",
                ]
            ),
            ["USW-LITE-8-POE", "810010071156"],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "USW-Lite-8-PoE")
        self.assertEqual(fields["serial_number"], "58D61F517119")
        self.assertNotEqual(fields["serial_number"], "USW-LITE-8-POE")
        self.assertEqual(debug["candidates"][0]["source"], "ubiquiti_identifier")

    def test_ubiquiti_model_is_not_serial_when_identifier_is_missing(self) -> None:
        fields, debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "Ubiquiti Inc.",
                    "USW-Lite-8-PoE",
                    "UPC",
                    "8 10010 07115 6",
                    "Made in China",
                ]
            ),
            ["USW-LITE-8-POE", "810010071156"],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "USW-Lite-8-PoE")
        self.assertEqual(fields["serial_number"], "")
        self.assertEqual(fields["notes"], "UPC: 810010071156")
        self.assertTrue(debug["needs_confirmation"])

    def test_ubiquiti_u7_lr_label_without_vendor_text(self) -> None:
        fields, debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "U7-LR",
                    "(RX)847848C64FB6",
                    "UPC",
                    "8 10177 16192 9",
                    "08/18/25",
                    "Made in Vietnam",
                ]
            ),
            [],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "U7-LR")
        self.assertEqual(fields["serial_number"], "847848C64FB6")
        self.assertEqual(fields["notes"], "UPC: 810177161929")
        self.assertEqual(debug["confidence"], 1.0)

    def test_ubiquiti_u7_lr_label_with_noisy_spacing_and_casing(self) -> None:
        fields, _debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "u7 lr",
                    "(rx) 847848c64fb6",
                    "upc",
                    "8 10177 16192 9",
                ]
            ),
            [],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "U7-LR")
        self.assertEqual(fields["serial_number"], "847848C64FB6")
        self.assertEqual(fields["notes"], "UPC: 810177161929")

    def test_ubiquiti_u7_lr_model_can_come_from_barcode_candidate(self) -> None:
        fields, debug = parse_label_data_with_debug(
            "\n".join(
                [
                    "(RX)847848C64FB6",
                    "UPC",
                    "8 10177 16192 9",
                    "08/18/25",
                    "Made in Vietnam",
                ]
            ),
            ["U7-LR", "810177161929"],
        )

        self.assertEqual(fields["vendor"], "Ubiquiti")
        self.assertEqual(fields["model"], "U7-LR")
        self.assertEqual(fields["serial_number"], "847848C64FB6")
        self.assertEqual(fields["notes"], "UPC: 810177161929")
        self.assertEqual(debug["confidence"], 1.0)


if __name__ == "__main__":
    unittest.main()
