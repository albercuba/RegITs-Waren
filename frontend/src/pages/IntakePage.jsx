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

function createPhotoId() {
  return crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function IntakePage() {
  const [photos, setPhotos] = useState([]);
  const [activePhotoId, setActivePhotoId] = useState("");
  const [message, setMessage] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [sending, setSending] = useState(false);

  const activePhoto = photos.find((photo) => photo.id === activePhotoId) || photos[0] || null;
  const activeForm = activePhoto?.form || emptyForm;
  const activeOcrStatus = activePhoto?.ocrStatus || "Manuelle Eingabe erforderlich";
  const canSend = useMemo(
    () => photos.length > 0 && photos.every((photo) => photo.form.asset_type && (photo.form.serial_number || photo.form.notes)),
    [photos]
  );

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

  function updatePhotoForm(photoId, updater) {
    setPhotos((current) =>
      current.map((photo) =>
        photo.id === photoId
          ? {
              ...photo,
              form: typeof updater === "function" ? updater(photo.form) : updater,
            }
          : photo
      )
    );
  }

  function updatePhotoOcrStatus(photoId, ocrStatus) {
    setPhotos((current) => current.map((photo) => (photo.id === photoId ? { ...photo, ocrStatus } : photo)));
  }

  async function scanSelectedPhoto(file, photoId) {
    setScanning(true);
    updatePhotoOcrStatus(photoId, "Etikett wird gescannt...");
    setMessage(null);
    try {
      const result = await scanPhoto(file);
      updatePhotoForm(photoId, (current) => mergeDetectedFields(current, result));
      updatePhotoOcrStatus(
        photoId,
        result.serial_debug?.needs_confirmation
          ? "Seriennummer bitte prüfen"
          : result.status === "fields_detected"
            ? "Felder erkannt"
            : "Manuelle Eingabe erforderlich"
      );
    } catch (error) {
      updatePhotoOcrStatus(photoId, "Manuelle Eingabe erforderlich");
      setMessage({ type: "error", text: germanError(error.message) });
    } finally {
      setScanning(false);
    }
  }

  function handleFileChange(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    const nextPhotos = files.map((file) => ({
        id: createPhotoId(),
        file,
        previewUrl: URL.createObjectURL(file),
        form: { ...emptyForm },
        ocrStatus: "Manuelle Eingabe erforderlich",
      }));
    setPhotos((current) => [...current, ...nextPhotos]);
    setActivePhotoId(nextPhotos[0].id);
    event.target.value = "";
    scanSelectedPhoto(nextPhotos[0].file, nextPhotos[0].id);
  }

  function removePhoto(id) {
    setPhotos((current) => {
      const target = current.find((photo) => photo.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      const next = current.filter((photo) => photo.id !== id);
      if (activePhotoId === id) setActivePhotoId(next[0]?.id || "");
      return next;
    });
  }

  async function handleScan() {
    for (const photo of photos) {
      await scanSelectedPhoto(photo.file, photo.id);
    }
  }

  async function handleSubmit() {
    if (!photos.length) return;
    setSending(true);
    setMessage(null);
    try {
      const results = [];
      for (const photo of photos) {
        results.push(await createSubmission(photo.form, [photo.file]));
      }
      setMessage({ type: "success", text: `${results.length} Eintraege gesendet` });
      photos.forEach((photo) => URL.revokeObjectURL(photo.previewUrl));
      setPhotos([]);
      setActivePhotoId("");
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
        activePhotoId={activePhotoId}
        onFileChange={handleFileChange}
        onRemovePhoto={removePhoto}
        onScan={handleScan}
        onSelectPhoto={setActivePhotoId}
        photos={photos}
        scanning={scanning}
      />

      {message && <section className={message.type === "error" ? "notice error" : "notice success"}>{message.text}</section>}

      <FormFields
        form={activeForm}
        ocrStatus={activePhoto ? activeOcrStatus : "Bitte zuerst ein Foto aufnehmen"}
        onChange={(nextForm) => activePhoto && updatePhotoForm(activePhoto.id, nextForm)}
      />

      <SendButton disabled={!canSend} onClick={handleSubmit} sending={sending} />
    </div>
  );
}
