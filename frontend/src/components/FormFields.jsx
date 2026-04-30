const assetTypes = ["Laptop", "Desktop", "Monitor", "Dockingstation", "Telefon", "Tablet", "Netzwerkgeraet", "Sonstiges"];

const fields = [
  ["serial_number", "Seriennummer"],
  ["vendor", "Hersteller"],
  ["model", "Modell"],
  ["received_by", "Angenommen von"],
];

export default function FormFields({ form, onChange }) {
  const setField = (name, value) => onChange({ ...form, [name]: value });

  return (
    <section className="panel form-panel">
      <div className="section-title">
        <p className="eyebrow">Automatisch erkannte Felder</p>
        <h2>Wareneingang Details</h2>
      </div>
      <label>
        <span>Geraetetyp</span>
        <select value={form.asset_type} onChange={(event) => setField("asset_type", event.target.value)}>
          <option value="">Geraetetyp auswaehlen</option>
          {assetTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      {fields.map(([name, label]) => (
        <label key={name}>
          <span>{label}</span>
          <input value={form[name]} onChange={(event) => setField(name, event.target.value)} placeholder={label} />
        </label>
      ))}
      <label>
        <span>Notizen</span>
        <textarea
          rows="4"
          value={form.notes}
          onChange={(event) => setField("notes", event.target.value)}
          placeholder="Zustand, Zubehoer, Standort..."
        />
      </label>
    </section>
  );
}