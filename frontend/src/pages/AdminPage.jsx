import { Lock } from "lucide-react";
import { useState } from "react";
import { getEmailSettings, saveEmailSettings, testEmailSettings } from "../api.js";
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

export default function AdminPage() {
  const [adminPassword, setAdminPassword] = useState("");
  const [unlocked, setUnlocked] = useState(false);
  const [settings, setSettings] = useState(emptySettings);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  async function unlock() {
    setBusy(true);
    setStatus(null);
    try {
      const data = await getEmailSettings(adminPassword);
      setSettings({ ...emptySettings, ...data, smtp_password: "" });
      setUnlocked(true);
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    setBusy(true);
    setStatus(null);
    try {
      const saved = await saveEmailSettings(adminPassword, settings);
      setSettings({ ...settings, ...saved, smtp_password: "" });
      setStatus({ type: "success", message: "Settings saved" });
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleTest() {
    setBusy(true);
    setStatus(null);
    try {
      await testEmailSettings(adminPassword, settings);
      setStatus({ type: "success", message: "Test email sent" });
    } catch (error) {
      setStatus({ type: "error", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page admin-page">
      <header className="mobile-header">
        <p className="eyebrow">Protected area</p>
        <h1>Admin Settings</h1>
      </header>

      {!unlocked ? (
        <section className="panel admin-login">
          <Lock size={32} />
          <h2>Admin Login</h2>
          <label>
            <span>Admin password</span>
            <input
              autoComplete="current-password"
              onChange={(event) => setAdminPassword(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && unlock()}
              type="password"
              value={adminPassword}
            />
          </label>
          <button className="button primary" disabled={busy || !adminPassword} onClick={unlock} type="button">
            Unlock Settings
          </button>
          {status && <p className="status error">{status.message}</p>}
        </section>
      ) : (
        <SettingsForm
          busy={busy}
          onChange={setSettings}
          onSave={handleSave}
          onTest={handleTest}
          settings={settings}
          status={status}
        />
      )}
    </div>
  );
}
