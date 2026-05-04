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
  const [photos, setPhotos] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [ocrStatus, setOcrStatus] = useState("Manuelle Eingabe erforderlich");
  const [message, setMessage] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [sending, setSending] = useState(false);

  const canSend = useMemo(() => Boolean(photos.length && form.asset_type && (form.serial_number || form.notes)), [photos, form]);

  function mergeDetectedFields(current, result) {
    const fields = result.fields || {};
    return {
      ...current,
      serial_number: current.serial_number || fields.serial_number || "",
      asset_type: current.asset_type || fields.asset_type || "",
      vendor: current.vendor || fields.vendor || "",
      model: current.model || fields.model || "",
      notes: [current.notes, fields.notes].filter(Boolean).join(current.notes && fields.notes ? "\n" : ""),
      raw_text: [current.raw_text, result.raw_text].filter(Boolean).join("\n\n"),
      detected_candidates: JSON.stringify([
        ...JSON.parse(current.detected_candidates || "[]"),
        ...(result.serial_candidates || []),
      ]),
    };
  }

  async function scanSelectedPhoto(file) {
    setScanning(true);
    setOcrStatus("Etikett wird gescannt...");
    setMessage(null);
    try {
      const result = await scanPhoto(file);
      setForm((current) => mergeDetectedFields(current, result));
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
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setPhotos((current) => [
      ...current,
      ...files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        previewUrl: URL.createObjectURL(file),
      })),
    ]);
    event.target.value = "";
    scanSelectedPhoto(files[0]);
  }

  function removePhoto(id) {
    setPhotos((current) => {
      const target = current.find((photo) => photo.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      const next = current.filter((photo) => photo.id !== id);
      if (next.length === 0) setOcrStatus("Manuelle Eingabe erforderlich");
      return next;
    });
  }

  async function handleScan() {
    for (const photo of photos) {
      await scanSelectedPhoto(photo.file);
    }
  }

  async function handleSubmit() {
    if (!photos.length) return;
    setSending(true);
    setMessage(null);
    try {
      const result = await createSubmission(form, photos.map((photo) => photo.file));
      setMessage({ type: "success", text: `Eintrag #${result.id} gesendet` });
      setForm(emptyForm);
      photos.forEach((photo) => URL.revokeObjectURL(photo.previewUrl));
      setPhotos([]);
      setOcrStatus("Manuelle Eingabe erforderlich");
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
        disabled={!photos.length}
        onFileChange={handleFileChange}
        onRemovePhoto={removePhoto}
        onScan={handleScan}
        photos={photos}
        scanning={scanning}
      />

      {message && <section className={message.type === "error" ? "notice error" : "notice success"}>{message.text}</section>}

      <FormFields form={form} ocrStatus={ocrStatus} onChange={setForm} />

      <SendButton disabled={!canSend} onClick={handleSubmit} sending={sending} />
    </div>
  );
}
