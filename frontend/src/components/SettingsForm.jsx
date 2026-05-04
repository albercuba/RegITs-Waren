import { MailCheck, Save } from "lucide-react";

export default function SettingsForm({ settings, onChange, onSave, onTest, busy, status }) {
  const setField = (name, value) => onChange({ ...settings, [name]: value });
  const setLocations = (value) =>
    setField(
      "locations",
      value
        .split("\n")
        .map((location) => location.trim())
        .filter(Boolean)
    );

  return (
    <section className="panel form-panel">
      <div className="section-title">
        <p className="eyebrow">Geschützter Adminbereich</p>
        <h2>SMTP-Einstellungen</h2>
      </div>
      <div className="form-grid">
        <label>
          <span>SMTP-Host</span>
          <input value={settings.smtp_host} onChange={(event) => setField("smtp_host", event.target.value)} />
        </label>
        <label>
          <span>SMTP-Port</span>
          <input
            inputMode="numeric"
            type="number"
            value={settings.smtp_port}
            onChange={(event) => setField("smtp_port", Number(event.target.value))}
          />
        </label>
      </div>
      <label>
        <span>SMTP-Benutzername</span>
        <input value={settings.smtp_username} onChange={(event) => setField("smtp_username", event.target.value)} />
      </label>
      <label>
        <span>SMTP-Passwort</span>
        <input
          autoComplete="new-password"
          placeholder={settings.password_configured ? "Passwort ist bereits gespeichert" : ""}
          type="password"
          value={settings.smtp_password}
          onChange={(event) => setField("smtp_password", event.target.value)}
        />
      </label>
      <label>
        <span>Absenderadresse</span>
        <input type="email" value={settings.sender_email} onChange={(event) => setField("sender_email", event.target.value)} />
      </label>
      <label>
        <span>Empfängeradresse</span>
        <input
          type="email"
          value={settings.recipient_email}
          onChange={(event) => setField("recipient_email", event.target.value)}
        />
      </label>
      <label className="toggle-row">
        <input checked={settings.use_tls} onChange={(event) => setField("use_tls", event.target.checked)} type="checkbox" />
        <span>TLS / STARTTLS verwenden</span>
      </label>
      <div className="section-title settings-subsection">
        <p className="eyebrow">Wareneingang</p>
        <h2>Standorte</h2>
      </div>
      <label>
        <span>Standorte</span>
        <textarea
          onChange={(event) => setLocations(event.target.value)}
          placeholder={"Lager\nBüro\nAußenstelle"}
          rows="4"
          value={(settings.locations || []).join("\n")}
        />
      </label>
      <div className="settings-actions">
        <button className="button secondary" disabled={busy} onClick={onTest} type="button">
          <MailCheck size={20} />
          <span>Test-E-Mail</span>
        </button>
        <button className="button primary" disabled={busy} onClick={onSave} type="button">
          <Save size={20} />
          <span>Einstellungen speichern</span>
        </button>
      </div>
      {status && <p className={status.type === "error" ? "status error" : "status success"}>{status.message}</p>}
    </section>
  );
}
