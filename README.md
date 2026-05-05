# RegITs-Waren

Mobile-first interne Webanwendung fuer den IT-Hardware-Wareneingang.

Mitarbeitende koennen mit dem Smartphone ein oder mehrere Fotos von Geraeteetiketten aufnehmen. Jedes Foto wird als eigenes Paket behandelt: OCR und Barcode-Erkennung fuellen erkannte Felder vorab aus, der Eintrag wird in SQLite gespeichert und per E-Mail mit Fotoanhang versendet. SMTP und Wareneingang-Standorte werden im geschuetzten Admin-Bereich konfiguriert.

## Projektstruktur

```text
backend/
  app/
    main.py
    database.py
    routers/
    services/
    models/
  tests/
frontend/
  src/
docker-compose.yml
.env.example
```

## Lokale Entwicklung

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
set DATABASE_PATH=./data/regits-dev.db
set UPLOAD_DIR=./uploads
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Standard-URLs:

- Frontend dev: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/health`

## Docker

1. Umgebungsdatei erstellen:

```bash
cp .env.example .env
```

2. `.env` bearbeiten:

```env
APP_SECRET_KEY=dein-langer-zufaelliger-schluessel
ADMIN_PASSWORD=dein-admin-passwort
MAX_UPLOAD_MB=12
CORS_ORIGINS=http://localhost:8081
```

3. Starten:

```bash
docker compose up --build
```

4. Oeffnen:

```text
http://localhost:8081
```

Docker Compose nutzt Volumes fuer `/app/data` und `/app/uploads`. Die Container laufen mit nicht-root Benutzern, Healthchecks sind fuer Backend und Frontend konfiguriert.

## Admin

Die Ansicht `Admin` mit `ADMIN_PASSWORD` entsperren.

SMTP-Einstellungen:

- SMTP-Host, Port, Benutzername, Passwort
- Absenderadresse und Empfaengeradresse
- TLS/STARTTLS

Das Backend prueft die SMTP-Verbindung vor dem Speichern. Das SMTP-Passwort wird mit `APP_SECRET_KEY` verschluesselt und nie an das Frontend zurueckgegeben.

Standorte:

- Eigene Karte `Standorte` unterhalb der SMTP-Einstellungen
- Mehrere Standorte koennen unabhaengig von SMTP gespeichert werden
- `Standort` und `Angenommen von` werden innerhalb einer Aufnahme-Session auf weitere Fotos uebernommen

OCR Debug:

- Debugdaten und gespeicherte Upload-Bilder sind admin-geschuetzt
- Der Admin-Bereich laedt Preview-Bilder mit dem Header `X-Admin-Password`

## OCR und Barcode

Das Backend-Image installiert Tesseract OCR und zbar. Seriennummern werden mit label-aware Parsern und einer Kandidaten/Scoring-Pipeline erkannt.

Nach dem Aufnehmen oder Hochladen eines Fotos kann optional der Labelbereich zugeschnitten werden. Der Zuschnitt ist nicht verpflichtend, hilft aber oft dabei, OCR schneller und genauer zu machen, weil Tesseract nur den relevanten Bildausschnitt verarbeitet. Mit `Ohne Zuschneiden scannen` bleibt der bisherige Ablauf erhalten und das komplette Foto wird fuer OCR verwendet.

Der Zuschnitt wird nur fuer die OCR-Erkennung genutzt. Fuer den finalen Wareneingangseintrag und den E-Mail-Anhang bleibt das urspruengliche Foto erhalten, sofern ein Foto eingereicht wird.

Wichtige Regeln:

- Explizite Labels wie `S/N`, `Serial`, `Seriennummer` gewinnen gegen generische Kandidaten
- UPC/EAN/GTIN werden nicht als Seriennummer uebernommen, wenn eine echte Seriennummer vorhanden ist
- UniFi/Ubiquiti Labels setzen `Hersteller = Ubiquiti`, Modellcodes wie `U7-LR` oder `USW-Lite-8-PoE`, Seriennummern aus `(AK)58D61F517119` / `(RX)847848C64FB6` und UPC in `Notizen`
- Generische Labels mit `Part Code`, `P/N`, `Model No.` und aehnlichen Feldern werden bevorzugt vor Fallback-Heuristiken ausgewertet

## API

Wichtige Endpunkte:

- `GET /api/health`
- `POST /api/scan`
- `POST /api/submissions`
- `GET /api/locations`
- `GET /api/admin/email-settings`
- `POST /api/admin/email-settings`
- `POST /api/admin/email-settings/test`
- `GET /api/admin/locations`
- `POST /api/admin/locations`
- `GET /api/scan/debug/{debug_id}` mit `X-Admin-Password`
- `GET /api/uploads/{filename}` mit `X-Admin-Password`

## Sicherheit und Produktion

Produktions-Checkliste:

- `ADMIN_PASSWORD` aendern
- `APP_SECRET_KEY` auf einen langen, zufaelligen Wert setzen und danach nicht verlieren
- `CORS_ORIGINS` auf die echte Frontend-Origin setzen, z. B. `https://waren.example.de`
- Hinter einem HTTPS-Reverse-Proxy betreiben
- Volumes und Backups schuetzen
- Netzwerkzugriff einschraenken, wenn die App nur im LAN genutzt werden soll
- `.env` nicht committen

Uploads:

- Uploadgroesse wird mit `MAX_UPLOAD_MB` begrenzt
- Dateien muessen echte, von Pillow lesbare Bilder sein
- Gespeicherte Dateinamen werden serverseitig generiert
- Bilder werden beim Speichern neu geschrieben, um unnoetige Metadaten wie EXIF zu vermeiden

CORS:

`CORS_ORIGINS` ist kommasepariert. Standard fuer lokale Entwicklung:

```text
http://localhost:8081,http://localhost:5173,http://127.0.0.1:5173
```

## Backup und Restore

Backup der Docker-Volumes:

```bash
docker compose stop
docker run --rm -v regits-waren_data:/data -v %cd%:/backup alpine tar czf /backup/regits-data.tgz -C /data .
docker run --rm -v regits-waren_uploads:/uploads -v %cd%:/backup alpine tar czf /backup/regits-uploads.tgz -C /uploads .
docker compose start
```

Restore:

```bash
docker compose stop
docker run --rm -v regits-waren_data:/data -v %cd%:/backup alpine sh -c "rm -rf /data/* && tar xzf /backup/regits-data.tgz -C /data"
docker run --rm -v regits-waren_uploads:/uploads -v %cd%:/backup alpine sh -c "rm -rf /uploads/* && tar xzf /backup/regits-uploads.tgz -C /uploads"
docker compose up -d
```

Bei anderen Compose-Projektnamen koennen die Volume-Namen abweichen. Mit `docker volume ls` pruefen.

## Tests und Checks

Backend:

```bash
cd backend
pytest
ruff check .
black --check .
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Docker:

```bash
docker compose config
```

## Troubleshooting

- Tesseract/OCR: Sicherstellen, dass `tesseract-ocr`, `tesseract-ocr-deu` und `tesseract-ocr-eng` installiert sind.
- OCR erkennt Daten nicht: Foto neu aufnehmen oder den Zuschnitt enger um das eigentliche Etikett ziehen und erneut scannen.
- Barcode/zbar: `pyzbar` benoetigt die zbar Runtime (`libzbar0` im Dockerfile).
- SMTP: Port 465 nutzt implizites TLS, Port 587 typischerweise STARTTLS. Fehlermeldungen aus dem SMTP-Test werden im Admin-Bereich angezeigt.
- HTTPS/Kamera: Mobile Browser erlauben Kamera-Uploads am zuverlaessigsten ueber HTTPS oder `localhost`.
- CORS/Admin: Die Browser-Origin muss in `CORS_ORIGINS` stehen. Admin-Endpunkte erwarten `X-Admin-Password`.

## Screenshots / Workflow

Platzhalter:

- Wareneingang mit mehreren Foto-Karten
- Admin SMTP-Einstellungen
- Admin Standorte
- OCR Debug Ansicht
