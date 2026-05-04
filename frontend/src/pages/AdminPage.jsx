import { Lock, Plus, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import {
  getAdminLocations,
  getEmailSettings,
  getScanDebug,
  getUploadBlob,
  saveEmailSettings,
  saveLocations,
  testEmailSettings,
} from "../api.js";
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
  const [locationsStatus, setLocationsStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const [locations, setLocations] = useState([]);
  const [debugId, setDebugId] = useState("");
  const [debugData, setDebugData] = useState(null);
  const [debugImageUrl, setDebugImageUrl] = useState("");

  async function unlock() {
    setBusy(true);
    setStatus(null);
    setLocationsStatus(null);
    try {
      const [data, locationData] = await Promise.all([getEmailSettings(adminPassword), getAdminLocations(adminPassword)]);
      setSettings({ ...emptySettings, ...data, smtp_password: "" });
      setLocations(locationData.locations || []);
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

  function addLocation() {
    setLocations((current) => [...current, ""]);
  }

  function updateLocation(index, value) {
    setLocations((current) => current.map((location, currentIndex) => (currentIndex === index ? value : location)));
  }

  function removeLocation(index) {
    setLocations((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  async function handleSaveLocations() {
    setBusy(true);
    setLocationsStatus(null);
    try {
      const saved = await saveLocations(adminPassword, locations);
      setLocations(saved.locations || []);
      setLocationsStatus({ type: "success", message: "Standorte gespeichert" });
    } catch (error) {
      setLocationsStatus({ type: "error", message: germanError(error.message) });
    } finally {
      setBusy(false);
    }
  }

  async function loadDebugData() {
    if (!debugId) return;
    setBusy(true);
    setStatus(null);
    setDebugData(null);
    if (debugImageUrl) {
      URL.revokeObjectURL(debugImageUrl);
      setDebugImageUrl("");
    }
    try {
      const data = await getScanDebug(debugId, adminPassword);
      setDebugData(data);
      if (data.image_file) {
        const imageBlob = await getUploadBlob(data.image_file, adminPassword);
        setDebugImageUrl(URL.createObjectURL(imageBlob));
      }
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
              <p className="eyebrow">Wareneingang</p>
              <h2>Standorte</h2>
            </div>
            <div className="location-list">
              {locations.map((location, index) => (
                <div className="location-row" key={`location-${index}`}>
                  <label>
                    <span>Standort {index + 1}</span>
                    <input value={location} onChange={(event) => updateLocation(index, event.target.value)} />
                  </label>
                  <button className="icon-button" onClick={() => removeLocation(index)} title="Standort entfernen" type="button">
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
            </div>
            <div className="settings-actions location-actions">
              <button className="button secondary" disabled={busy} onClick={addLocation} type="button">
                <Plus size={20} />
                <span>Standort hinzufügen</span>
              </button>
              <button className="button primary" disabled={busy} onClick={handleSaveLocations} type="button">
                <Save size={20} />
                <span>Standorte speichern</span>
              </button>
            </div>
            {locationsStatus && (
              <p className={locationsStatus.type === "error" ? "status error" : "status success"}>{locationsStatus.message}</p>
            )}
          </section>
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
                {debugImageUrl && <img alt="" src={debugImageUrl} />}
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
