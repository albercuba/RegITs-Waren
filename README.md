# RegITs-Waren

Mobile-first interne Webanwendung fuer den IT-Hardware-Wareneingang.

Mitarbeitende koennen mit dem Smartphone ein Foto des Geraeteetiketts aufnehmen. Die Anwendung scannt das Bild automatisch per OCR und Barcode-Erkennung, fuellt erkannte Felder vorab aus und sendet eine E-Mail mit Fotoanhang. Alle Eintraege werden in SQLite fuer das Audit-Protokoll gespeichert. SMTP wird im geschuetzten Admin-Bereich der Weboberflaeche konfiguriert.

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
APP_SECRET_KEY=dein-langer-zufaelliger-schluessel
ADMIN_PASSWORD=dein-admin-passwort
```

3. Anwendung starten:

```bash
docker compose up --build
```

4. Im Browser oeffnen:

```text
http://localhost:8080
```

Hochgeladene Bilder werden im Docker-Volume unter `/app/uploads` gespeichert. Die SQLite-Datenbank liegt im `data` Docker-Volume.

## Admin SMTP-Einstellungen

Die Ansicht `Admin` oeffnen und das `ADMIN_PASSWORD` aus `.env` eingeben.

Im Admin-Bereich koennen diese Werte gepflegt werden:

- SMTP-Host
- SMTP-Port
- SMTP-Benutzername
- SMTP-Passwort
- Absenderadresse
- Empfaengeradresse
- TLS / STARTTLS

Das Backend prueft die SMTP-Verbindung vor dem Speichern. Das SMTP-Passwort wird mit `APP_SECRET_KEY` verschluesselt, nie an das Frontend zurueckgegeben und nicht protokolliert.

## Smartphone-Kamera

Die Anwendung nutzt:

```html
<input type="file" accept="image/*" capture="environment" />
```

Viele mobile Browser erlauben den besten Kamerazugriff nur ueber HTTPS, ausser bei `localhost`. Fuer produktive Nutzung oder Tests im LAN sollte die Anwendung hinter einem HTTPS-Reverse-Proxy laufen.

## OCR und Barcode

Das Backend-Image installiert:

- Tesseract OCR
- zbar Runtime fuer `pyzbar`

Das Backend erkennt Seriennummer, Hersteller und Modell per regelbasierter Auswertung. Wenn keine Werte erkannt werden, bleiben die Felder leer und koennen manuell bearbeitet werden.

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
- Die Upload-Groesse ist ueber `MAX_UPLOAD_MB` begrenzt, Standardwert `12`.
- Das SMTP-Passwort wird verschluesselt gespeichert.
- Admin-Einstellungen erfordern `ADMIN_PASSWORD`.
- Fuer produktive Nutzung HTTPS verwenden.