import { ClipboardList, Inbox, Mail, Moon, Settings, ShieldCheck, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import AdminPage from "./pages/AdminPage.jsx";
import IntakePage from "./pages/IntakePage.jsx";
import regitsLogo from "./assets/regits_cloud_logo.png";

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
      <p className="eyebrow">Demnächst</p>
      <h2>{title}</h2>
      <p>Diese Ansicht ist für die nächste Version reserviert. Wareneingang und Admin-Einstellungen sind im MVP bereit.</p>
    </section>
  );
}

function getInitialTheme() {
  const saved = localStorage.getItem("regits-theme");
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [activeView, setActiveView] = useState("receiving");
  const [theme, setTheme] = useState(getInitialTheme);
  const isDark = theme === "dark";

  useEffect(() => {
    document.body.dataset.theme = theme;
    localStorage.setItem("regits-theme", theme);
  }, [theme]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-logo">
          <img src={regitsLogo} alt="" className="topbar-logo-image" />
          <span>REGITS-WAREN</span>
        </div>
        <div className="topbar-title">IT-Hardware Wareneingang</div>
        <div className="topbar-right">
          <span className="topbar-count">MVP</span>
          <button
            aria-label={isDark ? "Helles Design aktivieren" : "Dunkles Design aktivieren"}
            className={isDark ? "theme-switch dark" : "theme-switch"}
            onClick={() => setTheme(isDark ? "light" : "dark")}
            title={isDark ? "Helles Design" : "Dunkles Design"}
            type="button"
          >
            <Sun className="theme-icon sun" size={14} />
            <span className="theme-track"><span className="theme-thumb" /></span>
            <Moon className="theme-icon moon" size={14} />
          </button>
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
