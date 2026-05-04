import { Camera, RotateCcw, ScanLine } from "lucide-react";

export default function PhotoCapture({ photos, activePhotoId, onFileChange, onRemovePhoto, onScan, onSelectPhoto, scanning, disabled }) {
  const hasPhotos = photos.length > 0;
  const selectedPhotoId = activePhotoId || photos[0]?.id || "";

  return (
    <section className={hasPhotos ? "photo-card has-preview" : "photo-card is-empty"}>
      <div className="photo-preview">
        {hasPhotos ? (
          <div className="photo-grid">
            {photos.map((photo, index) => (
              <article className={photo.id === selectedPhotoId ? "photo-tile active" : "photo-tile"} key={photo.id}>
                <button className="photo-select" onClick={() => onSelectPhoto(photo.id)} type="button">
                  <img alt={`Vorschau der erhaltenen Hardware ${index + 1}`} src={photo.previewUrl} />
                  <span>{photo.id === selectedPhotoId ? `Paket ${index + 1} wird bearbeitet` : `Paket ${index + 1}`}</span>
                </button>
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
          <input accept="image/*" capture="environment" hidden onChange={onFileChange} type="file" />
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
