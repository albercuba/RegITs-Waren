import { ClipboardList, Inbox, Mail, Settings, ShieldCheck } from "lucide-react";
import { useState } from "react";
import AdminPage from "./pages/AdminPage.jsx";
import IntakePage from "./pages/IntakePage.jsx";

const navItems = [
  { id: "receiving", label: "Receiving", icon: Inbox },
  { id: "inventory", label: "Inventory", icon: ClipboardList },
  { id: "queue", label: "Email Queue", icon: Mail },
  { id: "audit", label: "Audit Log", icon: ShieldCheck },
  { id: "admin", label: "Admin", icon: Settings },
];

function Placeholder({ title }) {
  return (
    <section className="panel placeholder-panel">
      <p className="eyebrow">Coming next</p>
      <h2>{title}</h2>
      <p>This view is reserved for the next iteration. Receiving and Admin Settings are ready for the MVP.</p>
    </section>
  );
}

export default function App() {
  const [activeView, setActiveView] = useState("receiving");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">RW</span>
          <div>
            <strong>RegITs-Waren</strong>
            <small>Hardware intake</small>
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
        {activeView === "inventory" && <Placeholder title="Inventory" />}
        {activeView === "queue" && <Placeholder title="Email Queue" />}
        {activeView === "audit" && <Placeholder title="Audit Log" />}
      </main>
    </div>
  );
}
