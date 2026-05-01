# RegITs-Waren

Mobile-first interne Webanwendung für den IT-Hardware-Wareneingang.

Mitarbeitende können mit dem Smartphone ein Foto des Geräteetiketts aufnehmen. Die Anwendung scannt das Bild automatisch per OCR und Barcode-Erkennung, füllt erkannte Felder vorab aus und sendet eine E-Mail mit Fotoanhang. Alle Einträge werden in SQLite für das Audit-Protokoll gespeichert. SMTP wird im geschützten Admin-Bereich der Weboberfläche konfiguriert.

## Projektstruktur

```text
backend/
  app/
    main.py
    database.py
    routers/
      intake.py
      admin.py
    services/
      ocr.py
      parser.py
      email.py
      security.py
    models/
      schemas.py
frontend/
  src/
    pages/
      IntakePage.jsx
      AdminPage.jsx
    components/
      PhotoCapture.jsx
      FormFields.jsx
      SendButton.jsx
      SettingsForm.jsx
docker-compose.yml
.env.example
```

## Start mit Docker

1. Umgebungsdatei erstellen:

```bash
cp .env.example .env
```

2. `.env` bearbeiten und mindestens diese Werte setzen:

```env
APP_SECRET_KEY=dein-langer-zufälliger-schlüssel
ADMIN_PASSWORD=dein-admin-passwort
```

3. Anwendung starten:

```bash
docker compose up --build
```

4. Im Browser öffnen:

```text
http://localhost:8081
```

Hochgeladene Bilder werden im Docker-Volume unter `/app/uploads` gespeichert. Die SQLite-Datenbank liegt im `data` Docker-Volume.

## Admin SMTP-Einstellungen

Die Ansicht `Admin` öffnen und das `ADMIN_PASSWORD` aus `.env` eingeben.

Im Admin-Bereich können diese Werte gepflegt werden:

- SMTP-Host
- SMTP-Port
- SMTP-Benutzername
- SMTP-Passwort
- Absenderadresse
- Empfängeradresse
- TLS / STARTTLS

Das Backend prüft die SMTP-Verbindung vor dem Speichern. Das SMTP-Passwort wird mit `APP_SECRET_KEY` verschlüsselt, nie an das Frontend zurückgegeben und nicht protokolliert.

## Smartphone-Kamera

Die Anwendung nutzt:

```html
<input type="file" accept="image/*" capture="environment" />
```

Viele mobile Browser erlauben den besten Kamerazugriff nur über HTTPS, außer bei `localhost`. Fuer produktive Nutzung oder Tests im LAN sollte die Anwendung hinter einem HTTPS-Reverse-Proxy laufen.

## OCR und Barcode

Das Backend-Image installiert:

- PaddleOCR mit PaddlePaddle CPU Runtime
- zbar Runtime für `pyzbar`

PaddleOCR läuft lokal im Backend-Container. Hochgeladene Bilder werden nicht an externe OCR-Dienste gesendet. Beim ersten Start kann PaddleOCR die benötigten OCR-Modelldateien herunterladen; im Docker-Betrieb werden sie unter `/app/data/paddleocr` im Daten-Volume abgelegt. Die Standardsprache ist `german`, weil die Geräteetiketten deutschsprachige Feldnamen enthalten und Seriennummern/englische Produktnamen weiterhin mit lateinischen Zeichen erkannt werden. Bei rein englischen Etiketten kann `PADDLEOCR_LANG=en` gesetzt werden.

Barcode-Erkennung nutzt weiterhin zbar/`pyzbar` und wird mit dem OCR-Text zusammen an die bestehende regelbasierte Auswertung übergeben. Das Backend erkennt Seriennummer, Hersteller und Modell per Parser- und Scoring-Regeln. Wenn keine Werte erkannt werden, bleiben die Felder leer und können manuell bearbeitet werden.

Manueller OCR-Testpfad:

1. Anwendung mit `docker compose up --build` starten.
2. `http://localhost:8081` öffnen.
3. Ein Geräteetikett fotografieren oder hochladen.
4. Prüfen, ob `Seriennummer`, `Hersteller`, `Modell` und `Barcodes` im Formular bzw. im Admin-OCR-Debug plausibel erscheinen.

## API

Wichtige Endpunkte:

- `POST /api/scan`
- `POST /api/submissions`
- `GET /api/submissions`
- `GET /api/admin/email-settings`
- `POST /api/admin/email-settings`
- `POST /api/admin/email-settings/test`

Admin-Endpunkte erwarten den Header `X-Admin-Password`.

## Sicherheit

- Uploads werden auf Bilddateien begrenzt.
- Die Upload-Größe ist über `MAX_UPLOAD_MB` begrenzt, Standardwert `12`.
- Das SMTP-Passwort wird verschlüsselt gespeichert.
- Admin-Einstellungen erfordern `ADMIN_PASSWORD`.
- Fuer produktive Nutzung HTTPS verwenden.
