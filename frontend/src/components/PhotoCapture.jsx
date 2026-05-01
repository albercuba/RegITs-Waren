import { Camera, RotateCcw, ScanLine } from "lucide-react";

export default function PhotoCapture({ previewUrl, onFileChange, onRetake, onScan, scanning, disabled }) {
  return (
    <section className={previewUrl ? "photo-card has-preview" : "photo-card is-empty"}>
      <div className="photo-preview">
        {previewUrl ? (
          <img alt="Vorschau der erhaltenen Hardware" src={previewUrl} />
        ) : (
          <div className="empty-preview">
            <Camera size={42} />
            <span>Etikett fotografieren</span>
          </div>
        )}
      </div>
      <div className="photo-actions">
        <label className="button primary">
          <Camera size={20} />
          <span>{previewUrl ? "Foto neu aufnehmen" : "Kamera öffnen"}</span>
          <input accept="image/*" capture="environment" hidden onChange={onFileChange} type="file" />
        </label>
        {previewUrl && (
          <>
            <button className="button ghost" onClick={onRetake} type="button">
              <RotateCcw size={20} />
              <span>Entfernen</span>
            </button>
            <button className="button secondary" disabled={disabled || scanning} onClick={onScan} type="button">
              <ScanLine size={20} />
              <span>{scanning ? "Scanne..." : "Erneut scannen"}</span>
            </button>
          </>
        )}
      </div>
    </section>
  );
}
