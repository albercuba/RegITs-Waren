const assetTypes = ["Laptop", "Desktop", "Monitor", "Dock", "Phone", "Tablet", "Network", "Other"];

const fields = [
  ["serial_number", "Serial number"],
  ["vendor", "Vendor"],
  ["model", "Model"],
  ["ticket_number", "Ticket / PO number"],
  ["received_by", "Received by"],
];

export default function FormFields({ form, onChange }) {
  const setField = (name, value) => onChange({ ...form, [name]: value });

  return (
    <section className="panel form-panel">
      <div className="section-title">
        <p className="eyebrow">Auto-filled fields</p>
        <h2>Intake Details</h2>
      </div>
      <label>
        <span>Asset type</span>
        <select value={form.asset_type} onChange={(event) => setField("asset_type", event.target.value)}>
          <option value="">Choose asset type</option>
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
        <span>Notes</span>
        <textarea
          rows="4"
          value={form.notes}
          onChange={(event) => setField("notes", event.target.value)}
          placeholder="Condition, accessories, location..."
        />
      </label>
    </section>
  );
}
