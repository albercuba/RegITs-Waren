import { Camera, RotateCcw, ScanLine } from "lucide-react";

export default function PhotoCapture({ photos, onFileChange, onRemovePhoto, onScan, scanning, disabled }) {
  const hasPhotos = photos.length > 0;

  return (
    <section className={hasPhotos ? "photo-card has-preview" : "photo-card is-empty"}>
      <div className="photo-preview">
        {hasPhotos ? (
          <div className="photo-grid">
            {photos.map((photo, index) => (
              <article className="photo-tile" key={photo.id}>
                <img alt={`Vorschau der erhaltenen Hardware ${index + 1}`} src={photo.previewUrl} />
                <button className="photo-remove" onClick={() => onRemovePhoto(photo.id)} type="button">
                  <RotateCcw size={16} />
                  <span>Entfernen</span>
                </button>
              </article>
            ))}
          </div>
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
          <span>{hasPhotos ? "Foto hinzufügen" : "Kamera öffnen"}</span>
          <input accept="image/*" capture="environment" hidden multiple onChange={onFileChange} type="file" />
        </label>
        {hasPhotos && (
          <>
            <button className="button secondary" disabled={disabled || scanning} onClick={onScan} type="button">
              <ScanLine size={20} />
              <span>{scanning ? "Scanne..." : "Alle scannen"}</span>
            </button>
          </>
        )}
      </div>
    </section>
  );
}
