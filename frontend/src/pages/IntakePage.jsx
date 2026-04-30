import { useEffect, useMemo, useState } from "react";
import { createSubmission, getSubmissions, scanPhoto } from "../api.js";
import FormFields from "../components/FormFields.jsx";
import PhotoCapture from "../components/PhotoCapture.jsx";
import SendButton from "../components/SendButton.jsx";

const emptyForm = {
  serial_number: "",
  asset_type: "",
  vendor: "",
  model: "",
  received_by: "",
  notes: "",
  raw_text: "",
};

function germanDate(value) {
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function germanError(message) {
  const map = {
    "Only image uploads are allowed": "Nur Bilddateien sind erlaubt",
    "Invalid metadata": "Ungültige Metadaten",
    "SMTP settings are not configured": "SMTP-Einstellungen sind nicht konfiguriert",
    "Request failed": "Anfrage fehlgeschlagen",
  };
  if (message?.startsWith("Submission saved, but email failed")) {
    return "Eintrag gespeichert, aber E-Mail-Versand fehlgeschlagen";
  }
  if (message?.includes("Image exceeds")) {
    return "Das Bild ist zu groß";
  }
  return map[message] || message;
}

export default function IntakePage() {
  const [photo, setPhoto] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [ocrStatus, setOcrStatus] = useState("Manuelle Eingabe erforderlich");
  const [message, setMessage] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [sending, setSending] = useState(false);
  const [submissions, setSubmissions] = useState([]);

  useEffect(() => {
    getSubmissions().then(setSubmissions).catch(() => setSubmissions([]));
  }, []);

  const canSend = useMemo(() => Boolean(photo && form.asset_type && (form.serial_number || form.notes)), [photo, form]);

  async function scanSelectedPhoto(file) {
    setScanning(true);
    setOcrStatus("Etikett wird gescannt...");
    setMessage(null);
    try {
      const result = await scanPhoto(file);
      setForm((current) => ({ ...current, ...result.fields, raw_text: result.raw_text || "" }));
      setOcrStatus(result.status === "fields_detected" ? "Felder erkannt" : "Manuelle Eingabe erforderlich");
    } catch (error) {
      setOcrStatus("Manuelle Eingabe erforderlich");
      setMessage({ type: "error", text: germanError(error.message) });
    } finally {
      setScanning(false);
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    setPreviewUrl(URL.createObjectURL(file));
    scanSelectedPhoto(file);
  }

  function resetPhoto() {
    setPhoto(null);
    setPreviewUrl("");
    setOcrStatus("Manuelle Eingabe erforderlich");
  }

  async function handleScan() {
    if (!photo) return;
    await scanSelectedPhoto(photo);
  }

  async function handleSubmit() {
    if (!photo) return;
    setSending(true);
    setMessage(null);
    try {
      const result = await createSubmission(form, photo);
      setMessage({ type: "success", text: `Eintrag #${result.id} gesendet` });
      setForm(emptyForm);
      resetPhoto();
      setSubmissions(await getSubmissions());
    } catch (error) {
      setMessage({ type: "error", text: germanError(error.message) });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page intake-page">
      <header className="mobile-header">
        <p className="eyebrow">RegITs-Waren</p>
        <h1>Wareneingang</h1>
      </header>

      <PhotoCapture
        disabled={!photo}
        onFileChange={handleFileChange}
        onRetake={resetPhoto}
        onScan={handleScan}
        previewUrl={previewUrl}
        scanning={scanning}
      />

      <section className="status-strip">
        <span>{ocrStatus}</span>
      </section>
      {message && <section className={message.type === "error" ? "notice error" : "notice success"}>{message.text}</section>}

      <FormFields form={form} onChange={setForm} />

      <section className="panel recent-panel">
        <div className="section-title">
          <p className="eyebrow">Audit-Protokoll</p>
          <h2>Letzte Einträge</h2>
        </div>
        <div className="recent-list">
          {submissions.length === 0 && <p className="empty-text">Noch keine Einträge.</p>}
          {submissions.map((item) => (
            <article className="submission-row" key={item.id}>
              <div>
                <strong>{item.serial_number || "Keine Seriennummer"}</strong>
                <span>{item.vendor || "Unbekannter Hersteller"} | {item.asset_type || "Nicht zugeordnet"}</span>
              </div>
              <time>{germanDate(item.created_at)}</time>
            </article>
          ))}
        </div>
      </section>

      <SendButton disabled={!canSend} onClick={handleSubmit} sending={sending} />
    </div>
  );
}