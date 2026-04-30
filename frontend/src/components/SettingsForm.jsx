import { MailCheck, Save } from "lucide-react";

export default function SettingsForm({ settings, onChange, onSave, onTest, busy, status }) {
  const setField = (name, value) => onChange({ ...settings, [name]: value });

  return (
    <section className="panel form-panel">
      <div className="section-title">
        <p className="eyebrow">Protected admin</p>
        <h2>SMTP Settings</h2>
      </div>
      <div className="form-grid">
        <label>
          <span>SMTP host</span>
          <input value={settings.smtp_host} onChange={(event) => setField("smtp_host", event.target.value)} />
        </label>
        <label>
          <span>SMTP port</span>
          <input
            inputMode="numeric"
            type="number"
            value={settings.smtp_port}
            onChange={(event) => setField("smtp_port", Number(event.target.value))}
          />
        </label>
      </div>
      <label>
        <span>SMTP username</span>
        <input value={settings.smtp_username} onChange={(event) => setField("smtp_username", event.target.value)} />
      </label>
      <label>
        <span>SMTP password</span>
        <input
          autoComplete="new-password"
          placeholder={settings.password_configured ? "Password already configured" : ""}
          type="password"
          value={settings.smtp_password}
          onChange={(event) => setField("smtp_password", event.target.value)}
        />
      </label>
      <label>
        <span>Sender email</span>
        <input type="email" value={settings.sender_email} onChange={(event) => setField("sender_email", event.target.value)} />
      </label>
      <label>
        <span>Recipient email</span>
        <input
          type="email"
          value={settings.recipient_email}
          onChange={(event) => setField("recipient_email", event.target.value)}
        />
      </label>
      <label className="toggle-row">
        <input checked={settings.use_tls} onChange={(event) => setField("use_tls", event.target.checked)} type="checkbox" />
        <span>Use TLS / STARTTLS</span>
      </label>
      <div className="settings-actions">
        <button className="button secondary" disabled={busy} onClick={onTest} type="button">
          <MailCheck size={20} />
          <span>Test Email</span>
        </button>
        <button className="button primary" disabled={busy} onClick={onSave} type="button">
          <Save size={20} />
          <span>Save Settings</span>
        </button>
      </div>
      {status && <p className={status.type === "error" ? "status error" : "status success"}>{status.message}</p>}
    </section>
  );
}
