import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import type { DemoCaseMeta } from "../types";
import { DemoPickerModal } from "../components/DemoPickerModal";

const STEPS = [
  {
    icon: "bi-briefcase",
    title: "Create a case",
    text: "Describe your situation — title, legal area, jurisdiction and the facts you know. Everything else is organized around this one case.",
  },
  {
    icon: "bi-file-earmark-text",
    title: "Add documents & evidence",
    text: "Upload PDFs, DOCX, TXT or images. Facts are extracted from documents and labeled — never invented.",
  },
  {
    icon: "bi-exclamation-circle",
    title: "Identify issues & risks",
    text: "Possible legal issues, risks, and information gaps are surfaced with confidence levels and clear provenance.",
  },
  {
    icon: "bi-diagram-3",
    title: "Explore scenarios",
    text: "Model what-if situations, compare strategies, and prepare — or practice — negotiation.",
  },
  {
    icon: "bi-list-check",
    title: "Act with a plan",
    text: "Convert analysis into prioritized actions and track deadlines until the matter is resolved.",
  },
];

const CAPABILITIES = [
  { icon: "bi-stars", title: "AI Case Overview", text: "A structured, plain-language reading of your situation — facts, issues, gaps and next steps in one view." },
  { icon: "bi-file-earmark-text", title: "Document Intelligence", text: "Upload contracts, letters and invoices; the AI summarizes, extracts facts and flags possible issues." },
  { icon: "bi-shield-exclamation", title: "Risk Analysis", text: "Likelihood × impact risk profiles with practical mitigations, revisited as the case grows." },
  { icon: "bi-diagram-3", title: "What-If Simulator", text: "Compare alternative paths — settle, litigate, wait — with outcomes, trade-offs and key unknowns." },
  { icon: "bi-people", title: "Negotiation Copilot", text: "A preparation brief grounded in your case, plus a roleplayed counterparty to practice against." },
  { icon: "bi-chat-dots", title: "Contextual Assistant", text: "Ask questions about your case. Answers stay inside the case and label what is fact, interpretation, or missing." },
  { icon: "bi-calendar3", title: "Timeline Builder", text: "Every date in order — agreements, notices, incidents — the backbone of issue and deadline analysis." },
  { icon: "bi-alarm", title: "Deadline Tracker", text: "Statutory and practical deadlines tracked per case and surfaced on your dashboard." },
];

const WHY = [
  { icon: "bi-tag", title: "Facts are labeled, not invented", text: "Every insight is tagged: user-provided fact, extracted from document, or AI interpretation. The system never presents assumptions as facts." },
  { icon: "bi-journal-x", title: "No invented laws or citations", text: "The AI is instructed never to fabricate statutes, cases, or document contents. Where law matters, it says jurisdiction varies and verification is required." },
  { icon: "bi-bank2", title: "Structured, not a chat clone", text: "A situation becomes a case with a timeline, documents, issues, risks, scenarios, evidence and an action plan — not an endless conversation." },
  { icon: "bi-shield-lock", title: "Your data stays yours", text: "Data is stored in your own database, keys live only in backend environment variables, and passwords are hashed." },
];

const PRIVACY = [
  "Your cases, documents and analyses are stored in your own database (SQLite now, PostgreSQL-ready).",
  "Passwords are hashed; sessions use signed, expiring tokens.",
  "Gemini API keys exist only in backend environment variables — never in frontend code or the browser.",
  "AI analysis is informational; verify anything consequential with a qualified legal professional.",
];

export function LandingPage() {
  const { user } = useAuth();
  const [demos, setDemos] = useState<DemoCaseMeta[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  // Hooks must run unconditionally (no early return above them), so the
  // signed-in redirect is state-driven instead of a conditional return.
  const [redirectToDashboard, setRedirectToDashboard] = useState(Boolean(user));

  useEffect(() => {
    if (user) setRedirectToDashboard(true);
  }, [user]);

  useEffect(() => {
    api.get<{ demos: DemoCaseMeta[] }>("/demo-catalog")
      .then((d) => setDemos(d.demos))
      .catch(() => setDemos([]));
  }, []);

  if (redirectToDashboard) return <Navigate to="/dashboard" replace />;

  async function exploreDemo() {
    if (demos.length === 0) {
      // Catalog unavailable — fall back to the classic single rental demo.
      try {
        const res = await api.post<{ case: { id: number } }>("/demo/session", { kind: "rental" });
        window.location.assign(`/cases/${res.case.id}/overview`);
      } catch {
        setPickerOpen(true);
      }
      return;
    }
    setPickerOpen(true);
  }

  return (
    <div className="landing">
      <header className="landing-nav">
        <Link to="/" className="brand">
          <span className="brand-mark"><i className="bi bi-bank2" /></span>
          <span>Legal Case Demystifier<small>Case intelligence workspace</small></span>
        </Link>
        <div className="landing-nav-links">
          <a href="#how">How it works</a>
          <a href="#capabilities">Capabilities</a>
          <a href="#why">Why it's different</a>
          <Link to="/login" className="btn btn-outline btn-sm">Sign in</Link>
          <Link to="/register" className="btn btn-accent btn-sm">Get started</Link>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="overline" style={{ color: "#93a4c0" }}>Legal Case Demystifier</div>
          <h1>Understand Your Case. Explore Your Options. Decide What Comes Next.</h1>
          <p className="landing-sub">
            Legal Case Demystifier transforms complex legal situations and documents into
            structured insights, risks, scenarios, and practical next steps.
          </p>
          <div className="landing-cta">
            <Link to="/register" className="btn btn-accent btn-lg"><i className="bi bi-stars" /> Analyze My Case</Link>
            <button className="btn btn-outline btn-lg" onClick={() => void exploreDemo()}
                    style={{ background: "transparent", color: "#fff", borderColor: "#3d4f73" }}>
              <i className="bi bi-briefcase" /> Explore Demo Case
            </button>
          </div>
          <div className="landing-trust">
            <span><i className="bi bi-shield-check" /> Structured legal workspace</span>
            <span><i className="bi bi-journal-x" /> No invented laws or citations</span>
            <span><i className="bi bi-translate" /> Multilingual explanations</span>
          </div>
          <div className="landing-demos" style={{ marginTop: 14 }}>
            {demos.map((d) => (
              <span key={d.kind} className="overline" style={{ color: "#93a4c0" }}>
                <i className={`bi ${d.icon}`} style={{ marginRight: 4 }} /> {d.title}
              </span>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section" id="how">
        <div className="landing-section-head">
          <div className="overline">How it works</div>
          <h2>From situation to structured case</h2>
          <p>Not a chatbot — a workflow. Each step builds on the last, always tied to your case.</p>
        </div>
        <div className="landing-grid landing-grid-5">
          {STEPS.map((s, i) => (
            <div className="landing-step" key={s.title}>
              <span className="landing-step-num">{i + 1}</span>
              <i className={`bi ${s.icon}`} />
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-section-alt" id="capabilities">
        <div className="landing-section-head">
          <div className="overline">Core capabilities</div>
          <h2>Everything a case needs, in one workspace</h2>
        </div>
        <div className="landing-grid landing-grid-4">
          {CAPABILITIES.map((c) => (
            <div className="landing-card" key={c.title}>
              <i className={`bi ${c.icon}`} />
              <h3>{c.title}</h3>
              <p>{c.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" id="why">
        <div className="landing-section-head">
          <div className="overline">Why Legal Case Demystifier</div>
          <h2>An assistant that respects the difference between fact and guesswork</h2>
        </div>
        <div className="landing-grid landing-grid-2">
          {WHY.map((w) => (
            <div className="landing-card" key={w.title}>
              <i className={`bi ${w.icon}`} />
              <h3>{w.title}</h3>
              <p>{w.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section landing-section-alt" id="privacy">
        <div className="landing-section-head">
          <div className="overline">Privacy</div>
          <h2>Built on isolation, transparency and control</h2>
        </div>
        <div className="landing-privacy">
          {PRIVACY.map((p) => (
            <div key={p} className="landing-card" style={{ margin: 0 }}>
              <i className="bi bi-shield-lock" />
              <p style={{ margin: 0 }}>{p}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-section-head">
          <div className="overline">Disclaimer</div>
          <h2>Informational only — never legal advice</h2>
        </div>
        <div className="disclaimer" style={{ maxWidth: 760, margin: "0 auto", fontSize: 13.5 }}>
          <i className="bi bi-shield-shaded" />
          <div>
            This application provides informational and decision-support assistance and is not
            a substitute for advice from a qualified legal professional. AI-generated content
            may contain errors and must be verified by a qualified legal professional before
            any action is taken. The platform never invents laws, citations, or document
            contents, and never guarantees outcomes.
          </div>
        </div>
      </section>

      <DemoPickerModal open={pickerOpen} demos={demos} onClose={() => setPickerOpen(false)} />

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <span className="brand">
            <span className="brand-mark"><i className="bi bi-bank2" /></span>
            <span>Legal Case Demystifier<small>Case intelligence workspace</small></span>
          </span>
          <div className="landing-footer-links">
            <Link to="/login">Sign in</Link>
            <Link to="/register">Create account</Link>
            <a href="#privacy">Privacy</a>
            <Link to="/privacy">Privacy policy</Link>
          </div>
          <p>Informational and decision-support assistance — not a substitute for qualified legal advice.</p>
        </div>
      </footer>
    </div>
  );
}