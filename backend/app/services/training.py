import json
from pathlib import Path

from app.services.parser import parse_label_data_with_debug


TRAINING_PATH = Path(__file__).resolve().parents[1] / "label_training_examples.json"


def load_training_examples() -> list[dict]:
    return json.loads(TRAINING_PATH.read_text(encoding="utf-8"))


def validate_training_examples() -> list[dict]:
    results = []
    for example in load_training_examples():
        fields, serial_debug = parse_label_data_with_debug(example["raw_text"], example.get("barcodes", []))
        expected = example["expected"]
        failures = {
            key: {"expected": value, "actual": fields.get(key, "")}
            for key, value in expected.items()
            if fields.get(key, "") != value
        }
        results.append(
            {
                "name": example["name"],
                "ok": not failures,
                "failures": failures,
                "fields": fields,
                "serial_debug": serial_debug,
            }
        )
    return results


if __name__ == "__main__":
    output = validate_training_examples()
    print(json.dumps(output, indent=2, ensure_ascii=False))
    raise SystemExit(0 if all(item["ok"] for item in output) else 1)
