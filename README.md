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
http://localhost:8080
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

- Tesseract OCR
- zbar Runtime für `pyzbar`

Das Backend erkennt Seriennummer, Hersteller und Modell per regelbasierter Auswertung. Wenn keine Werte erkannt werden, bleiben die Felder leer und können manuell bearbeitet werden.

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