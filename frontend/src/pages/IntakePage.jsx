import { useMemo, useState } from "react";
import { createSubmission, scanPhoto } from "../api.js";
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
  detected_candidates: "",
};

function germanError(message) {
  const map = {
    "Only image uploads are allowed": "Nur Bilddateien sind erlaubt",
    "Invalid metadata": "Ungültige Metadaten",
    "SMTP settings are not configured": "SMTP-Einstellungen sind nicht konfiguriert",
    "Request failed": "Anfrage fehlgeschlagen",
    "Scan timed out": "Der Scan hat zu lange gedauert. Bitte ein naeheres, schaerferes Foto versuchen oder die Daten manuell eintragen.",
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

  const canSend = useMemo(() => Boolean(photo && form.asset_type && (form.serial_number || form.notes)), [photo, form]);

  async function scanSelectedPhoto(file) {
    setScanning(true);
    setOcrStatus("Etikett wird gescannt...");
    setMessage(null);
    try {
      const result = await scanPhoto(file);
      setForm((current) => ({
        ...current,
        ...result.fields,
        raw_text: result.raw_text || "",
        detected_candidates: JSON.stringify(result.serial_candidates || []),
      }));
      setOcrStatus(
        result.serial_debug?.needs_confirmation
          ? "Seriennummer bitte prüfen"
          : result.status === "fields_detected"
            ? "Felder erkannt"
            : "Manuelle Eingabe erforderlich"
      );
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

      {message && <section className={message.type === "error" ? "notice error" : "notice success"}>{message.text}</section>}

      <FormFields form={form} ocrStatus={ocrStatus} onChange={setForm} />

      <SendButton disabled={!canSend} onClick={handleSubmit} sending={sending} />
    </div>
  );
}
