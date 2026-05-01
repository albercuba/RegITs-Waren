# RegITs-Waren Codex Agent Instructions

## Project Goal

RegITs-Waren supports IT goods intake. Users photograph hardware labels, the app scans OCR and barcodes, pre-fills asset metadata, stores submissions in SQLite, and sends intake emails.

The most important extracted field is the serial number. Scan behavior should favor fast, reliable serial detection over trying to perfectly classify every possible label field.

## Priorities

- Make serial-number detection fast and dependable.
- Treat serial-shaped barcode values as high-priority signals.
- Support German and English serial labels, including `S/N`, `SN`, `SNR`, `Ser.-Nr.`, `Serien-Nr.`, `Seriennummer`, `S-Nummer`, `Serial No`, and `Service Tag`.
- Avoid confusing serial numbers with part numbers, article numbers, model numbers, MAC addresses, EAN/GTIN/UPC barcodes, quantities, or regulatory identifiers.
- Keep OCR fallback work limited to uncertain cases so normal scans stay quick.
- Preserve manual correction paths; users must always be able to fix OCR results before submitting.

## Tech Stack

- Backend: FastAPI, SQLite, Pillow, Tesseract OCR, pyzbar.
- Frontend: React.
- Runtime: Docker Compose.
- Tests: Python `unittest`.

## Coding Rules

- Keep changes small, focused, and aligned with the existing code style.
- Prefer parser/ranking improvements before introducing heavier OCR or ML workflows.
- Use structured parser rules and tests for known label formats.
- Add or update tests whenever OCR, barcode, parser, or serial extraction behavior changes.
- Do not revert unrelated user changes.
- Do not commit secrets, credentials, customer data, or private label photos.

## Verification

For backend OCR/parser changes, run:

```sh
env PYTHONPATH=backend python3 -m unittest backend.tests.test_serial_extractor
env PYTHONPATH=backend python3 -m app.services.training
```

For frontend changes, inspect `frontend/package.json` and use the existing npm scripts.

## Commit Messages

Always provide a suggested conventional commit message after making code changes. Include the type, for example:

- `fix: improve German serial extraction`
- `feat: add scan training feedback loop`
- `test: cover German label serial formats`
- `docs: add Codex project instructions`
