import { Inbox, Moon, Settings, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import AdminPage from "./pages/AdminPage.jsx";
import IntakePage from "./pages/IntakePage.jsx";
import regitsLogo from "./assets/regits_cloud_logo.png";

const navItems = [
  { id: "receiving", label: "Wareneingang", icon: Inbox },
  { id: "admin", label: "Admin", icon: Settings },
];

function GitHubIcon() {
  return (
    <svg aria-hidden="true" className="github-icon" viewBox="0 0 16 16">
      <path
        d="M8 0.2a8 8 0 0 0-2.53 15.59c0.4 0.07 0.55-0.17 0.55-0.38v-1.34c-2.23 0.49-2.7-1.08-2.7-1.08-0.36-0.92-0.89-1.17-0.89-1.17-0.73-0.5 0.06-0.49 0.06-0.49 0.8 0.06 1.23 0.83 1.23 0.83 0.72 1.22 1.87 0.87 2.33 0.66 0.07-0.52 0.28-0.87 0.51-1.07-1.78-0.2-3.64-0.89-3.64-3.95 0-0.87 0.31-1.59 0.82-2.15-0.08-0.2-0.36-1.02 0.08-2.12 0 0 0.67-0.21 2.2 0.82a7.6 7.6 0 0 1 4.01 0c1.53-1.03 2.2-0.82 2.2-0.82 0.44 1.1 0.16 1.92 0.08 2.12 0.51 0.56 0.82 1.28 0.82 2.15 0 3.07-1.87 3.75-3.65 3.95 0.29 0.25 0.54 0.73 0.54 1.48v2.2c0 0.21 0.15 0.46 0.55 0.38A8 8 0 0 0 8 0.2Z"
        fill="currentColor"
      />
    </svg>
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
        <div className="sidebar-footer">
          <a className="sidebar-link" href="https://github.com/albercuba/RegITs-Waren" rel="noreferrer" target="_blank">
            <GitHubIcon />
            <span>GitHub</span>
          </a>
        </div>
      </aside>

      <main className="content">
        {activeView === "receiving" && <IntakePage />}
        {activeView === "admin" && <AdminPage />}
      </main>
    </div>
  );
}
