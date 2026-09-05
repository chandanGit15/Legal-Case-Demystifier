import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { useToast } from "../context/ToastContext";
import { initialsOf } from "../utils/format";
import { LANGUAGES } from "../utils/i18n";
import { NewCaseModal } from "../components/NewCaseModal";

const NAV: { to: string; key: string; icon: string; end: boolean }[] = [
  { to: "/dashboard", key: "navDashboard", icon: "bi-grid", end: true },
  { to: "/cases", key: "navCases", icon: "bi-briefcase", end: false },
  { to: "/documents", key: "navDocuments", icon: "bi-file-earmark-text", end: false },
  { to: "/assistant", key: "navAssistant", icon: "bi-chat-dots", end: false },
  { to: "/risk-center", key: "navRisk", icon: "bi-shield-check", end: false },
  { to: "/scenarios", key: "navScenarios", icon: "bi-diagram-3", end: false },
  { to: "/negotiation", key: "navNegotiation", icon: "bi-people", end: false },
  { to: "/action-plan", key: "navActionPlan", icon: "bi-list-check", end: false },
  { to: "/settings", key: "navSettings", icon: "bi-gear", end: false },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const toast = useToast();
  const [newCaseOpen, setNewCaseOpen] = useState(false);
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    toast.info("Signed out. See you soon.");
    navigate("/");
  }

  return (
    <div>
      <a className="skip-link" href="#app-main">Skip to content</a>
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/dashboard" className="brand">
            <span className="brand-mark"><i className="bi bi-bank2" /></span>
            <span>Legal Case Demystifier<small>{t("brandSubtitle")}</small></span>
          </NavLink>
          <nav className="topnav">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}
                       className={({ isActive }) => (isActive ? "active" : "")}>
                <i className={`bi ${item.icon}`} />{t(item.key)}
              </NavLink>
            ))}
          </nav>
          <div className="topbar-actions">
            <button className="btn btn-accent btn-sm" onClick={() => setNewCaseOpen(true)}>
              <i className="bi bi-plus-lg" /> {t("newCase")}
            </button>
            <select
              className="form-select form-select-sm lang-select"
              value={language}
              aria-label={t("language")}
              title={t("language")}
              onChange={(e) => setLanguage(e.target.value)}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.native}</option>
              ))}
            </select>
            <div className="user-chip" title={user?.email}>
              <span className="user-avatar">{initialsOf(user?.name ?? "U")}</span>
              <span className="user-name">{user?.name}</span>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={handleLogout}
                    style={{ color: "#b9c4d8" }} aria-label={t("signOut")}
                    data-tip={t("signOut")}>
              <i className="bi bi-box-arrow-right" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>
      <main id="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <span>
          Informational and decision-support assistance only — not a substitute for
          advice from a qualified legal professional.
        </span>
        <span className="af-links">
          <Link to="/privacy">Privacy policy</Link>
        </span>
      </footer>
      <NewCaseModal open={newCaseOpen} onClose={() => setNewCaseOpen(false)} />
    </div>
  );
}
