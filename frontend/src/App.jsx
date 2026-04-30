import { ClipboardList, Inbox, Mail, Settings, ShieldCheck, Sun } from "lucide-react";
import { useState } from "react";
import AdminPage from "./pages/AdminPage.jsx";
import IntakePage from "./pages/IntakePage.jsx";

const navItems = [
  { id: "receiving", label: "Wareneingang", icon: Inbox },
  { id: "inventory", label: "Inventar", icon: ClipboardList },
  { id: "queue", label: "E-Mail-Warteschlange", icon: Mail },
  { id: "audit", label: "Audit-Protokoll", icon: ShieldCheck },
  { id: "admin", label: "Admin", icon: Settings },
];

function Placeholder({ title }) {
  return (
    <section className="panel placeholder-panel">
      <p className="eyebrow">Demnaechst</p>
      <h2>{title}</h2>
      <p>Diese Ansicht ist fuer die naechste Version reserviert. Wareneingang und Admin-Einstellungen sind im MVP bereit.</p>
    </section>
  );
}

export default function App() {
  const [activeView, setActiveView] = useState("receiving");

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-logo">REGITS-WAREN</div>
        <div className="topbar-title">IT-Hardware Wareneingang</div>
        <div className="topbar-right">
          <span className="topbar-count">MVP</span>
          <span className="theme-pill">
            <Sun size={14} />
          </span>
        </div>
      </header>

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">RW</span>
          <div>
            <strong>RegITs-Waren</strong>
            <small>Hardware Wareneingang</small>
          </div>
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={activeView === item.id ? "nav-button active" : "nav-button"}
                key={item.id}
                onClick={() => setActiveView(item.id)}
                type="button"
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="content">
        {activeView === "receiving" && <IntakePage />}
        {activeView === "admin" && <AdminPage />}
        {activeView === "inventory" && <Placeholder title="Inventar" />}
        {activeView === "queue" && <Placeholder title="E-Mail-Warteschlange" />}
        {activeView === "audit" && <Placeholder title="Audit-Protokoll" />}
      </main>
    </div>
  );
}