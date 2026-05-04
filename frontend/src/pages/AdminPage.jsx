import { Lock } from "lucide-react";
import { useState } from "react";
import { getEmailSettings, getScanDebug, saveEmailSettings, testEmailSettings } from "../api.js";
import SettingsForm from "../components/SettingsForm.jsx";

const emptySettings = {
  smtp_host: "",
  smtp_port: 587,
  smtp_username: "",
  smtp_password: "",
  sender_email: "",
  recipient_email: "",
  use_tls: true,
  password_configured: false,
  locations: [],
};

function germanError(message) {
  const map = {
    "Admin authentication required": "Admin-Anmeldung erforderlich",
    "SMTP connection failed": "SMTP-Verbindung fehlgeschlagen",
    "Authentication failed": "Authentifizierung fehlgeschlagen",
    "Request failed": "Anfrage fehlgeschlagen",
  };
  return map[message] || message;
}

function isBlank(value) {
  return String(value ?? "").trim() === "";
}

function missingSettingsMessage(settings) {
  const missing = [];

  if (isBlank(settings.smtp_host)) missing.push("SMTP-Host");
  if (!Number(settings.smtp_port) || Number(settings.smtp_port) < 1 || Number(settings.smtp_port) > 65535) {
    missing.push("SMTP-Port");
  }
  if (isBlank(settings.sender_email)) missing.push("Absenderadresse");
  if (isBlank(settings.recipient_email)) missing.push("Empfängeradresse");
  if (!isBlank(settings.smtp_username) && isBlank(settings.smtp_password) && !settings.password_configured) {
    missing.push("SMTP-Passwort");
  }

  if (missing.length === 0) return "";
  if (missing.length === 1) return `${missing[0]} fehlt.`;
  return `Folgende Pflichtfelder fehlen: ${missing.join(", ")}.`;
}

export default function AdminPage() {
  const [adminPassword, setAdminPassword] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [settings, setSettings] = useState(emptySettings);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [debugId, setDebugId] = useState("");
  const [debugData, setDebugData] = useState(null);

  async function unlock() {
    setBusy(true);
    setStatus(null);
    try {
      const data = await getEmailSettings(adminPassword);
      setSettings({ ...emptySettings, ...data, smtp_password: "" });
      setUnlocked(true);
    } catch (error) {
      setStatus({ type: "error", message: germanError(error.message) });
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    const validationMessage = missingSettingsMessage(settings);
    if (validationMessage) {
      setStatus({ type: "error", message: validationMessage });
      return;
    }

    setBusy(true);
    setStatus(null);
    try {
      const saved = await saveEmailSettings(adminPassword, settings);
      setSettings({ ...settings, ...saved, smtp_password: "" });
      setStatus({ type: "success", message: "Einstellungen gespeichert" });
    } catch (error) {
      setStatus({ type: "error", message: germanError(error.message) });
    } finally {
      setBusy(false);
    }
  }

  async function handleTest() {
    const validationMessage = missingSettingsMessage(settings);
    if (validationMessage) {
      setStatus({ type: "error", message: validationMessage });
      return;
    }

    setBusy(true);
    setStatus(null);
    try {
      await testEmailSettings(adminPassword, settings);
      setStatus({ type: "success", message: "Test-E-Mail gesendet" });
    } catch (error) {
      setStatus({ type: "error", message: germanError(error.message) });
    } finally {
      setBusy(false);
    }
  }

  async function loadDebugData() {
    if (!debugId) return;
    setBusy(true);
    setStatus(null);
    try {
      setDebugData(await getScanDebug(debugId));
    } catch (error) {
      setStatus({ type: "error", message: germanError(error.message) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page admin-page">
      <header className="mobile-header">
        <p className="eyebrow">Geschützter Bereich</p>
        <h1>Admin-Einstellungen</h1>
      </header>

      {!unlocked ? (
        <section className="panel admin-login">
          <Lock size={32} />
          <h2>Admin-Anmeldung</h2>
          <label>
            <span>Admin-Passwort</span>
            <input
              autoComplete="current-password"
              onChange={(event) => setAdminPassword(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && unlock()}
              type="password"
              value={adminPassword}
            />
          </label>
          <button className="button primary" disabled={busy || !adminPassword} onClick={unlock} type="button">
            Einstellungen entsperren
          </button>
          {status && <p className="status error">{status.message}</p>}
        </section>
      ) : (
        <>
          <SettingsForm
            busy={busy}
            onChange={setSettings}
            onSave={handleSave}
            onTest={handleTest}
            settings={settings}
            status={status}
          />
          <section className="panel form-panel">
            <div className="section-title">
              <p className="eyebrow">OCR Debug</p>
              <h2>Scan prüfen</h2>
            </div>
            <label>
              <span>Debug-ID</span>
              <input value={debugId} onChange={(event) => setDebugId(event.target.value)} inputMode="numeric" />
            </label>
            <button className="button secondary" disabled={busy || !debugId} onClick={loadDebugData} type="button">
              Debugdaten laden
            </button>
            {debugData && (
              <div className="debug-view">
                {debugData.image_url && <img alt="" src={debugData.image_url} />}
                <div className="debug-grid">
                  <strong>Seriennummer</strong>
                  <span>{debugData.best_guess_serial || "Nicht erkannt"}</span>
                  <strong>Konfidenz</strong>
                  <span>{debugData.confidence_score ?? 0}</span>
                </div>
                <h3>Kandidaten</h3>
                <div className="debug-candidates">
                  {(debugData.candidates || []).map((candidate) => (
                    <article key={`${candidate.value}-${candidate.score}`} className="submission-row">
                      <div>
                        <strong>{candidate.value}</strong>
                        <span>{candidate.reason || (candidate.reasons || []).join(", ")}</span>
                      </div>
                      <span>{candidate.score}</span>
                    </article>
                  ))}
                </div>
                <h3>OCR Text</h3>
                <pre>{debugData.raw_text}</pre>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
