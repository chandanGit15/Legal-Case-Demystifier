import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import type { User } from "../types";
import { ErrorState, Loading } from "../components/ui";
import {
  INDIAN_STATES,
  INDIAN_UNION_TERRITORIES,
  JURISDICTION_COUNTRY,
} from "../utils/constants";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "hi", label: "हिन्दी" },
  { code: "zh", label: "中文" },
  { code: "ar", label: "العربية" },
  { code: "pt", label: "Português" },
];

export function SettingsPage() {
  const { refreshUser } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ configured: boolean; demo_mode: boolean; model: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.get<{ settings: User }>("/settings")
      .then((d) => { if (!cancelled) setUser(d.settings); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load"); });
    api.get<{ configured: boolean; demo_mode: boolean; model: string }>("/settings/ai-status")
      .then((d) => { if (!cancelled) setAiStatus(d); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!user) return;
    setSaved(false);
    setError(null);
    try {
      const d = await api.put<{ settings: User }>("/settings", user);
      setUser(d.settings);
      setSaved(true);
      refreshUser();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save settings");
    }
  }

  if (error && !user) return <div className="page"><ErrorState message={error} onRetry={() => window.location.reload()} /></div>;
  if (!user) return <div className="page"><Loading label="Loading settings…" /></div>;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="sub">Profile, defaults, AI connectivity and privacy.</p>
        </div>
      </div>

      <div className="card mb-3">
        <h3 className="card-title">Profile</h3>
        <form onSubmit={save}>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Full name</label>
              <input className="form-control" value={user.name}
                     onChange={(e) => setUser({ ...user, name: e.target.value })} />
            </div>
            <div>
              <label className="form-label">Email</label>
              <input className="form-control" type="email" value={user.email}
                     onChange={(e) => setUser({ ...user, email: e.target.value })} />
            </div>
          </div>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Default jurisdiction</label>
              <input className="form-control" value={JURISDICTION_COUNTRY} readOnly
                     aria-readonly="true" title="The application is India-only" />
              <div className="form-hint">Fixed — this application is for the Indian legal context.</div>
            </div>
            <div>
              <label className="form-label" htmlFor="st-default-state">Default state / UT</label>
              <select id="st-default-state" className="form-select" value={user.default_state}
                      onChange={(e) => setUser({ ...user, default_state: e.target.value })}>
                <option value="">None — I'll choose per case</option>
                <optgroup label="States">
                  {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </optgroup>
                <optgroup label="Union Territories">
                  {INDIAN_UNION_TERRITORIES.map((s) => <option key={s} value={s}>{s}</option>)}
                </optgroup>
              </select>
              <div className="form-hint">Used for jurisdiction-aware analysis when a case doesn't set one.</div>
            </div>
          </div>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Preferred language</label>
              <select className="form-select" value={user.language}
                      onChange={(e) => setUser({ ...user, language: e.target.value })}>
                {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
              </select>
              <div className="form-hint">AI explanations and assistant replies use this language.</div>
            </div>
          </div>
          {error && <div className="alert-box error">{error}</div>}
          {saved && <div className="alert-box success">Settings saved.</div>}
          <button className="btn btn-primary" type="submit">Save settings</button>
        </form>
      </div>

      <div className="card mb-3">
        <h3 className="card-title">AI engine</h3>
        {aiStatus === null ? (
          <p className="text-faint">Checking…</p>
        ) : aiStatus.configured ? (
          <p className="text-soft" style={{ fontSize: 13.5 }}>
            <span className="badge badge-green"><i className="bi bi-check-circle" /> Live AI connected</span>{" "}
            Model: <span className="mono">{aiStatus.model}</span>. All analysis is routed through the centralized AI service layer.
          </p>
        ) : (
          <div>
            <span className="badge badge-demo"><i className="bi bi-stars" /> Demo mode</span>
            <p className="text-soft mt-2" style={{ fontSize: 13.5 }}>
              No <span className="mono">GEMINI_API_KEY</span> is configured, so the AI service returns
              clearly-labeled demo analysis. Set the environment variable in the backend and restart it to
              enable live Gemini analysis. The key is never exposed to the frontend.
            </p>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="card-title">Privacy &amp; security</h3>
        <ul style={{ fontSize: 13.5, color: "var(--ink-soft)", lineHeight: 1.8, paddingLeft: 18, marginBottom: 0 }}>
          <li>Your data is stored in your own database (SQLite now, PostgreSQL-ready).</li>
          <li>Passwords are hashed; authentication uses signed tokens with expiry.</li>
          <li>API keys live only in backend environment variables — never in the browser.</li>
          <li>AI analysis is labeled by provenance (user-provided, extracted from document, AI interpretation, missing, requires verification).</li>
          <li>AI output is informational only and is not legal advice.</li>
        </ul>
      </div>
    </div>
  );
}