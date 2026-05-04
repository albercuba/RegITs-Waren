# RegITs-Waren

Mobile-first interne Webanwendung für den IT-Hardware-Wareneingang.

Mitarbeitende können mit dem Smartphone ein oder mehrere Fotos von Geräteetiketten aufnehmen. Jedes Foto wird als eigenes Paket behandelt: Die Anwendung scannt das Bild automatisch per OCR und Barcode-Erkennung, füllt erkannte Felder vorab aus und sendet eine E-Mail mit Fotoanhang. Einträge werden in SQLite gespeichert. SMTP und Wareneingang-Standorte werden im geschützten Admin-Bereich der Weboberfläche konfiguriert.

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

Im Admin-Bereich können die SMTP-Werte gepflegt werden:

- SMTP-Host
- SMTP-Port
- SMTP-Benutzername
- SMTP-Passwort
- Absenderadresse
- Empfängeradresse
- TLS / STARTTLS

Das Backend prüft die SMTP-Verbindung vor dem Speichern. Das SMTP-Passwort wird mit `APP_SECRET_KEY` verschlüsselt, nie an das Frontend zurückgegeben und nicht protokolliert.

## Admin Standorte

Unterhalb der SMTP-Einstellungen gibt es eine eigene Karte `Standorte`. Dort können mehrere Standorte für den Wareneingang gepflegt und unabhängig von den SMTP-Einstellungen gespeichert werden.

Im Wareneingang erscheint `Standort` als Auswahlliste unter `Angenommen von`. Wenn `Angenommen von` oder `Standort` in einer Session gesetzt wird, übernimmt die App den Wert für alle weiteren Fotos/Pakete derselben Session.

## OCR Debug

Der Admin-Bereich enthält eine OCR-Debug-Ansicht. Mit einer Debug-ID können Raw-OCR-Text, erkannte Kandidaten, Konfidenz und Scoring-Details geprüft werden.

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

Das Backend erkennt Seriennummer, Hersteller, Modell, Gerätetyp und Notizen per regelbasierter Auswertung. Wenn keine Werte erkannt werden, bleiben die Felder leer und können manuell bearbeitet werden.

Die Seriennummer-Erkennung nutzt eine Kandidaten- und Scoring-Pipeline. Produktbarcodes wie UPC/EAN/GTIN werden nicht als Seriennummer übernommen, außer ein Wert ist klar als Seriennummer markiert.

Bekannte label-spezifische Parser:

- HP USB-C Dock G5
- iiyama ProLite X2491H
- Logitech MK295
- UniFi/Ubiquiti Geräte, z. B. `U7-LR` und `USW-Lite-8-PoE`

Bei UniFi/Ubiquiti-Labels wird der Hersteller als `Ubiquiti` gesetzt, das Modell aus Modellcodes wie `U7-LR` oder `USW-Lite-8-PoE` gelesen, die Seriennummer aus dem Muster `(AK)58D61F517119` / `(RX)847848C64FB6` extrahiert und eine UPC als `UPC: <digits>` in den Notizen gespeichert.

## API

Wichtige Endpunkte:

- `POST /api/scan`
- `POST /api/submissions`
- `GET /api/submissions`
- `GET /api/locations`
- `GET /api/admin/email-settings`
- `POST /api/admin/email-settings`
- `POST /api/admin/email-settings/test`
- `GET /api/admin/locations`
- `POST /api/admin/locations`
- `GET /api/admin/scan/debug/{debug_id}`

Admin-Endpunkte erwarten den Header `X-Admin-Password`.

## Sicherheit

- Uploads werden auf Bilddateien begrenzt.
- Die Upload-Größe ist über `MAX_UPLOAD_MB` begrenzt, Standardwert `12`.
- Das SMTP-Passwort wird verschlüsselt gespeichert.
- Admin-Einstellungen erfordern `ADMIN_PASSWORD`.
- Fuer produktive Nutzung HTTPS verwenden.
