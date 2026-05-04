import { useState } from "react";
import { ChevronDown } from "lucide-react";

const assetTypes = [
  "Laptop",
  "Desktop",
  "Monitor",
  "Dockingstation",
  "Telefon",
  "Tablet",
  "Netzwerkgerät",
  "Tastatur/Maus-Set",
  "Sonstiges",
];

const fields = [
  ["serial_number", "Seriennummer"],
  ["vendor", "Hersteller"],
  ["model", "Modell"],
  ["received_by", "Angenommen von"],
];

function LocationDropdown({ locations, value, onChange }) {
  const [open, setOpen] = useState(false);
  const hasSelectedUnknownLocation = value && !locations.includes(value);
  const options = hasSelectedUnknownLocation ? [value, ...locations] : locations;
  const label = value || "Standort auswählen";

  function selectLocation(nextValue) {
    onChange(nextValue);
    setOpen(false);
  }

  return (
    <div className="custom-select" onBlur={() => setOpen(false)}>
      <button
        aria-expanded={open}
        className="custom-select-button"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span>{label}</span>
        <ChevronDown size={18} />
      </button>
      {open && (
        <div className="custom-select-menu" role="listbox">
          <button
            className={!value ? "custom-select-option selected" : "custom-select-option"}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => selectLocation("")}
            type="button"
          >
            Standort auswählen
          </button>
          {options.map((location) => (
            <button
              className={location === value ? "custom-select-option selected" : "custom-select-option"}
              key={location}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectLocation(location)}
              type="button"
            >
              {location}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function FormFields({ form, onChange, ocrStatus, locations = [] }) {
  const setField = (name, value) => onChange({ ...form, [name]: value });

  return (
    <section className="panel form-panel">
      <div className="section-title">
        <p className="eyebrow">Automatisch erkannte Felder</p>
        <h2>Wareneingang Details</h2>
      </div>
      <div className="status-strip form-status">
        <span>{ocrStatus}</span>
      </div>
      <label>
        <span>Gerätetyp</span>
        <select value={form.asset_type} onChange={(event) => setField("asset_type", event.target.value)}>
          <option value="">Gerätetyp auswählen</option>
          {assetTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      {fields.map(([name, label]) => (
        <div key={name} className="field-group">
          <label>
            <span>{label}</span>
            <input value={form[name]} onChange={(event) => setField(name, event.target.value)} placeholder={label} />
          </label>
          {name === "received_by" && (
            <label>
              <span>Standort</span>
              <LocationDropdown locations={locations} value={form.location || ""} onChange={(value) => setField("location", value)} />
            </label>
          )}
        </div>
      ))}
      <label>
        <span>Notizen</span>
        <textarea
          rows="4"
          value={form.notes}
          onChange={(event) => setField("notes", event.target.value)}
          placeholder="Zustand, Zubehör, Standort..."
        />
      </label>
    </section>
  );
}
