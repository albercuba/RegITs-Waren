# RegITs-Waren

Mobile-first internal web application for IT hardware intake.

Employees can take a label photo with a phone, scan it with OCR/barcode detection, edit the detected metadata, and send an email with the photo attached. Submissions are stored in SQLite for auditing. SMTP settings are configured from the protected Admin page.

## Project Structure

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

## Run With Docker

1. Create your environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set at least:

```env
APP_SECRET_KEY=your-long-random-secret
ADMIN_PASSWORD=your-admin-password
```

3. Start the app:

```bash
docker compose up --build
```

4. Open:

```text
http://localhost:8080
```

Uploaded images are stored in the Docker volume mounted at `/app/uploads`. SQLite data is stored in the `data` Docker volume.

## Admin SMTP Settings

Open the `Admin` view and enter `ADMIN_PASSWORD` from `.env`.

The Admin page lets you configure:

- SMTP host
- SMTP port
- SMTP username
- SMTP password
- Sender email
- Recipient email
- TLS / STARTTLS

The backend validates the SMTP connection before saving. The SMTP password is encrypted using `APP_SECRET_KEY`, is never returned to the frontend, and should not appear in logs.

If no database SMTP settings exist, the backend uses the optional fallback SMTP values from `.env`.

## Phone Camera Notes

The app uses:

```html
<input type="file" accept="image/*" capture="environment" />
```

Most mobile browsers require HTTPS for the best camera behavior outside `localhost`. For production or LAN phone testing, place the app behind an HTTPS reverse proxy.

## OCR And Barcode

The Docker backend image installs:

- Tesseract OCR
- zbar runtime for `pyzbar`

The backend extracts serial number, vendor, model, and ticket/PO values with regex-based parsing. If detection fails, fields remain editable and empty.

## API

Main endpoints:

- `POST /api/scan`
- `POST /api/submissions`
- `GET /api/submissions`
- `GET /api/admin/email-settings`
- `POST /api/admin/email-settings`
- `POST /api/admin/email-settings/test`

Admin endpoints require the `X-Admin-Password` header.

## Security Notes

- Image upload content type is validated.
- Upload size is limited with `MAX_UPLOAD_MB`, default `12`.
- SMTP password is encrypted at rest.
- Admin settings require `ADMIN_PASSWORD`.
- Use HTTPS for production.
