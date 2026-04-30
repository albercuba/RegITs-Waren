import { Camera, RotateCcw, ScanLine } from "lucide-react";

export default function PhotoCapture({ previewUrl, onFileChange, onRetake, onScan, scanning, disabled }) {
  return (
    <section className="photo-card">
      <div className="photo-preview">
        {previewUrl ? (
          <img alt="Received hardware preview" src={previewUrl} />
        ) : (
          <div className="empty-preview">
            <Camera size={42} />
            <span>Take a label photo</span>
          </div>
        )}
      </div>
      <div className="photo-actions">
        <label className="button primary">
          <Camera size={20} />
          <span>{previewUrl ? "Retake Photo" : "Open Camera"}</span>
          <input accept="image/*" capture="environment" hidden onChange={onFileChange} type="file" />
        </label>
        {previewUrl && (
          <>
            <button className="button ghost" onClick={onRetake} type="button">
              <RotateCcw size={20} />
              <span>Clear</span>
            </button>
            <button className="button secondary" disabled={disabled || scanning} onClick={onScan} type="button">
              <ScanLine size={20} />
              <span>{scanning ? "Scanning..." : "Scan Label"}</span>
            </button>
          </>
        )}
      </div>
    </section>
  );
}
