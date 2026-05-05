import { useEffect, useMemo, useState } from "react";
import { createSubmission, getLocations, scanPhoto } from "../api.js";
import FormFields from "../components/FormFields.jsx";
import PhotoCapture from "../components/PhotoCapture.jsx";
import SendButton from "../components/SendButton.jsx";

const emptyForm = {
  serial_number: "",
  asset_type: "",
  vendor: "",
  model: "",
  received_by: "",
  location: "",
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
  const [scanningPhotoIds, setScanningPhotoIds] = useState([]);
  const [sending, setSending] = useState(false);
  const [locations, setLocations] = useState([]);
  const [defaultReceivedBy, setDefaultReceivedBy] = useState("");
  const [defaultLocation, setDefaultLocation] = useState("");

  const activePhoto = photos.find((photo) => photo.id === activePhotoId) || photos[0] || null;
  const activePhotoIndex = activePhoto ? photos.findIndex((photo) => photo.id === activePhoto.id) : -1;
  const activeForm = activePhoto?.form || emptyForm;
  const activeOcrStatus = activePhoto?.ocrStatus || "Manuelle Eingabe erforderlich";
  const scanning = scanningPhotoIds.length > 0;
  const canSend = useMemo(
    () => photos.length > 0 && photos.every((photo) => photo.form.asset_type && (photo.form.serial_number || photo.form.notes)),
    [photos]
  );

  useEffect(() => {
    getLocations()
      .then((data) => setLocations(Array.isArray(data) ? data : []))
      .catch(() => setLocations([]));
  }, []);

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

  function handleActiveFormChange(nextForm) {
    if (!activePhoto) return;
    const sharedUpdates = {};
    if (nextForm.received_by !== activePhoto.form.received_by) {
      setDefaultReceivedBy(nextForm.received_by);
      sharedUpdates.received_by = nextForm.received_by;
    }
    if (nextForm.location !== activePhoto.form.location) {
      setDefaultLocation(nextForm.location);
      sharedUpdates.location = nextForm.location;
    }
    if (Object.keys(sharedUpdates).length > 0) {
      setPhotos((current) =>
        current.map((photo) => ({
          ...photo,
          form: photo.id === activePhoto.id ? nextForm : { ...photo.form, ...sharedUpdates },
        }))
      );
      return;
    }
    updatePhotoForm(activePhoto.id, nextForm);
  }

  async function scanSelectedPhoto(ocrImageFile, photoId, ocrCropped = false) {
    setScanningPhotoIds((current) => (current.includes(photoId) ? current : [...current, photoId]));
    updatePhotoOcrStatus(photoId, ocrCropped ? "Zugeschnittenes Etikett wird gescannt..." : "Etikett wird gescannt...");
    setMessage(null);
    try {
      const result = await scanPhoto(ocrImageFile, { ocrCropped });
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
      setScanningPhotoIds((current) => current.filter((id) => id !== photoId));
    }
  }

  function createPhotoFromFile(file) {
    return {
      id: createPhotoId(),
      originalImageFile: file,
      croppedImageFile: null,
      previewUrl: URL.createObjectURL(file),
      form: { ...emptyForm, received_by: defaultReceivedBy, location: defaultLocation },
      ocrStatus: "Labelbereich auswaehlen oder ohne Zuschnitt scannen",
    };
  }

  function handleFileChange(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    const nextPhotos = files.map(createPhotoFromFile);
    setPhotos((current) => [...current, ...nextPhotos]);
    setActivePhotoId(nextPhotos[0].id);
    event.target.value = "";
  }

  function handleRetakePhoto(photoId, event) {
    const [file] = Array.from(event.target.files || []);
    if (!file) return;
    const nextPhoto = createPhotoFromFile(file);
    setPhotos((current) =>
      current.map((photo) => {
        if (photo.id !== photoId) return photo;
        URL.revokeObjectURL(photo.previewUrl);
        return { ...nextPhoto, form: photo.form };
      })
    );
    setActivePhotoId(nextPhoto.id);
    event.target.value = "";
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
    const photosToScan = [...photos];
    for (const photo of photosToScan) {
      setActivePhotoId(photo.id);
      const ocrImageFile = photo.croppedImageFile ?? photo.originalImageFile;
      await scanSelectedPhoto(ocrImageFile, photo.id, Boolean(photo.croppedImageFile));
    }
  }

  async function handleScanOriginal(photoId) {
    const photo = photos.find((currentPhoto) => currentPhoto.id === photoId);
    if (!photo) return;
    setPhotos((current) =>
      current.map((currentPhoto) =>
        currentPhoto.id === photoId ? { ...currentPhoto, croppedImageFile: null } : currentPhoto
      )
    );
    await scanSelectedPhoto(photo.originalImageFile, photoId, false);
  }

  async function handleCropAndScan(photoId, croppedImageFile) {
    setPhotos((current) =>
      current.map((photo) => (photo.id === photoId ? { ...photo, croppedImageFile } : photo))
    );
    await scanSelectedPhoto(croppedImageFile, photoId, true);
  }

  async function handleSubmit() {
    if (!photos.length) return;
    setSending(true);
    setMessage(null);
    try {
      const results = [];
      for (const photo of photos) {
        results.push(await createSubmission(photo.form, [photo.originalImageFile]));
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
        <h1>Wareneingang</h1>
      </header>

      <PhotoCapture
        disabled={!photos.length}
        activePhotoId={activePhotoId}
        onFileChange={handleFileChange}
        onRemovePhoto={removePhoto}
        onCropAndScan={handleCropAndScan}
        onRetakePhoto={handleRetakePhoto}
        onScan={handleScan}
        onScanOriginal={handleScanOriginal}
        onSelectPhoto={setActivePhotoId}
        photos={photos}
        scanning={scanning}
      />

      {message && <section className={message.type === "error" ? "notice error" : "notice success"}>{message.text}</section>}

      {activePhoto && <section className="status-strip package-status">Paket {activePhotoIndex + 1} wird bearbeitet</section>}

      <FormFields
        form={activeForm}
        locations={locations}
        ocrStatus={activePhoto ? activeOcrStatus : "Bitte zuerst ein Foto aufnehmen"}
        onChange={handleActiveFormChange}
      />

      <SendButton disabled={!canSend} onClick={handleSubmit} sending={sending} />
    </div>
  );
}
