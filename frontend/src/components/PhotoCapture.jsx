import { Camera, Crop, RotateCcw, ScanLine } from "lucide-react";
import { useRef, useState } from "react";

const initialCrop = { x: 10, y: 24, width: 80, height: 52 };
const minCropSize = 14;

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function getPointerPercent(event, element) {
  const rect = element.getBoundingClientRect();
  return {
    x: clamp(((event.clientX - rect.left) / rect.width) * 100, 0, 100),
    y: clamp(((event.clientY - rect.top) / rect.height) * 100, 0, 100),
  };
}

function moveCrop(crop, dx, dy) {
  return {
    ...crop,
    x: clamp(crop.x + dx, 0, 100 - crop.width),
    y: clamp(crop.y + dy, 0, 100 - crop.height),
  };
}

function resizeCrop(crop, handle, dx, dy) {
  let { x, y, width, height } = crop;

  if (handle.includes("w")) {
    const nextX = clamp(x + dx, 0, x + width - minCropSize);
    width += x - nextX;
    x = nextX;
  }
  if (handle.includes("e")) {
    width = clamp(width + dx, minCropSize, 100 - x);
  }
  if (handle.includes("n")) {
    const nextY = clamp(y + dy, 0, y + height - minCropSize);
    height += y - nextY;
    y = nextY;
  }
  if (handle.includes("s")) {
    height = clamp(height + dy, minCropSize, 100 - y);
  }

  return { x, y, width, height };
}

async function createCroppedFile(photo, crop) {
  const image = new Image();
  image.src = photo.previewUrl;
  await image.decode();

  const sourceX = Math.round((crop.x / 100) * image.naturalWidth);
  const sourceY = Math.round((crop.y / 100) * image.naturalHeight);
  const sourceWidth = Math.round((crop.width / 100) * image.naturalWidth);
  const sourceHeight = Math.round((crop.height / 100) * image.naturalHeight);
  const canvas = document.createElement("canvas");
  canvas.width = sourceWidth;
  canvas.height = sourceHeight;
  const context = canvas.getContext("2d");
  context.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, 0, 0, sourceWidth, sourceHeight);

  const type = photo.originalImageFile.type === "image/png" ? "image/png" : "image/jpeg";
  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob((nextBlob) => (nextBlob ? resolve(nextBlob) : reject(new Error("Crop failed"))), type, 0.92);
  });
  const extension = type === "image/png" ? "png" : "jpg";
  const baseName = photo.originalImageFile.name.replace(/\.[^.]+$/, "") || "label";
  return new File([blob], `${baseName}-ocr-crop.${extension}`, { type });
}

function CropEditor({ photo, disabled, onCropAndScan, onRetake, onScanOriginal }) {
  const frameRef = useRef(null);
  const pointerRef = useRef(null);
  const [crop, setCrop] = useState(initialCrop);
  const [cropping, setCropping] = useState(false);

  function handlePointerDown(event, mode) {
    if (disabled) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    pointerRef.current = {
      mode,
      last: getPointerPercent(event, frameRef.current),
    };
  }

  function handlePointerMove(event) {
    if (!pointerRef.current || !frameRef.current) return;
    const next = getPointerPercent(event, frameRef.current);
    const dx = next.x - pointerRef.current.last.x;
    const dy = next.y - pointerRef.current.last.y;
    const mode = pointerRef.current.mode;
    setCrop((current) => (mode === "move" ? moveCrop(current, dx, dy) : resizeCrop(current, mode, dx, dy)));
    pointerRef.current.last = next;
  }

  function handlePointerUp() {
    pointerRef.current = null;
  }

  async function handleCropAndScan() {
    setCropping(true);
    try {
      const croppedImageFile = await createCroppedFile(photo, crop);
      await onCropAndScan(photo.id, croppedImageFile);
    } finally {
      setCropping(false);
    }
  }

  return (
    <div className="crop-panel">
      <div className="crop-heading">
        <Crop size={18} />
        <div>
          <strong>Labelbereich auswählen</strong>
          <span>Ziehe den Rahmen um das Etikett, damit die Erkennung schneller und genauer wird.</span>
        </div>
      </div>
      <div
        className="crop-frame"
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        ref={frameRef}
      >
        <img alt="Ausgewaehltes Foto zum Zuschneiden" draggable="false" src={photo.previewUrl} />
        <div
          className="crop-box"
          onPointerDown={(event) => handlePointerDown(event, "move")}
          style={{
            left: `${crop.x}%`,
            top: `${crop.y}%`,
            width: `${crop.width}%`,
            height: `${crop.height}%`,
          }}
        >
          {["nw", "ne", "sw", "se"].map((handle) => (
            <span
              aria-hidden="true"
              className={`crop-handle ${handle}`}
              key={handle}
              onPointerDown={(event) => {
                event.stopPropagation();
                handlePointerDown(event, handle);
              }}
            />
          ))}
        </div>
      </div>
      <div className="crop-actions">
        <button className="button primary" disabled={disabled || cropping} onClick={handleCropAndScan} type="button">
          <ScanLine size={20} />
          <span>{cropping ? "Bereite Scan vor..." : "Zuschneiden & scannen"}</span>
        </button>
        <button className="button secondary" disabled={disabled} onClick={() => onScanOriginal(photo.id)} type="button">
          <ScanLine size={20} />
          <span>Ohne Zuschneiden scannen</span>
        </button>
        <label className="button ghost">
          <Camera size={20} />
          <span>Neu aufnehmen</span>
          <input accept="image/*" capture="environment" hidden onChange={(event) => onRetake(photo.id, event)} type="file" />
        </label>
      </div>
    </div>
  );
}

export default function PhotoCapture({
  photos,
  activePhotoId,
  onFileChange,
  onRemovePhoto,
  onScan,
  onScanDeep,
  onCropAndScan,
  onRetakePhoto,
  onScanOriginal,
  onSelectPhoto,
  scanning,
  disabled,
}) {
  const hasPhotos = photos.length > 0;
  const selectedPhotoId = activePhotoId || photos[0]?.id || "";
  const selectedPhoto = photos.find((photo) => photo.id === selectedPhotoId) || photos[0] || null;
  const scannedPhotoCount = photos.filter(
    (photo) =>
      !photo.ocrStatus.includes("Wartet") &&
      !photo.ocrStatus.includes("auswaehlen") &&
      !photo.ocrStatus.includes("wird gescannt")
  ).length;

  return (
    <section className={hasPhotos ? "photo-card has-preview" : "photo-card is-empty"}>
      <div className="photo-preview">
        {hasPhotos ? (
          <div className="photo-stack">
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
            {selectedPhoto && (
              <CropEditor
                disabled={disabled || scanning}
                onCropAndScan={onCropAndScan}
                onRetake={onRetakePhoto}
                onScanOriginal={onScanOriginal}
                photo={selectedPhoto}
              />
            )}
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
              <span>{scanning ? `Scanne ${scannedPhotoCount}/${photos.length}` : "Alle scannen"}</span>
            </button>
            <button className="button ghost" disabled={disabled || scanning} onClick={onScanDeep} type="button">
              <ScanLine size={20} />
              <span>Genauer scannen</span>
            </button>
          </>
        )}
      </div>
    </section>
  );
}
