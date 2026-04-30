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

export default function IntakePage() {
  const [photo, setPhoto] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [ocrStatus, setOcrStatus] = useState("Manual input required");
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
    setOcrStatus("Scanning label...");
    setMessage(null);
    try {
      const result = await scanPhoto(file);
      setForm((current) => ({ ...current, ...result.fields, raw_text: result.raw_text || "" }));
      setOcrStatus(result.status === "fields_detected" ? "Fields detected" : "Manual input required");
    } catch (error) {
      setOcrStatus("Manual input required");
      setMessage({ type: "error", text: error.message });
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
    setOcrStatus("Manual input required");
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
      setMessage({ type: "success", text: `Submission #${result.id} sent` });
      setForm(emptyForm);
      resetPhoto();
      setSubmissions(await getSubmissions());
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page intake-page">
      <header className="mobile-header">
        <p className="eyebrow">RegITs-Waren</p>
        <h1>Hardware Intake</h1>
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
          <p className="eyebrow">Audit log</p>
          <h2>Recent Submissions</h2>
        </div>
        <div className="recent-list">
          {submissions.length === 0 && <p className="empty-text">No submissions yet.</p>}
          {submissions.map((item) => (
            <article className="submission-row" key={item.id}>
              <div>
                <strong>{item.serial_number || "No serial"}</strong>
                <span>{item.vendor || "Unknown vendor"} · {item.asset_type || "Unsorted"}</span>
              </div>
              <time>{new Date(item.created_at).toLocaleString()}</time>
            </article>
          ))}
        </div>
      </section>

      <SendButton disabled={!canSend} onClick={handleSubmit} sending={sending} />
    </div>
  );
}
