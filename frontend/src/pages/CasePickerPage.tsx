import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { CaseSummary } from "../types";
import { CaseStatusBadge, EmptyState, ErrorState, Loading } from "../components/ui";

const SECTION_INFO: Record<string, { title: string; icon: string; blurb: string }> = {
  documents: {
    title: "Documents",
    icon: "bi-file-earmark-text",
    blurb: "Upload and analyze documents — facts are extracted with clear provenance.",
  },
  assistant: {
    title: "AI Assistant",
    icon: "bi-chat-dots",
    blurb: "Ask contextual questions about a case. The assistant stays inside the case.",
  },
  risks: {
    title: "Risk Center",
    icon: "bi-shield-check",
    blurb: "Assess and mitigate risks across your matters.",
  },
  scenarios: {
    title: "Scenarios",
    icon: "bi-diagram-3",
    blurb: "Explore what-if scenarios and compare strategies.",
  },
  negotiation: {
    title: "Negotiation",
    icon: "bi-people",
    blurb: "Prepare, strategize and practice negotiation.",
  },
  "action-plan": {
    title: "Action Plan",
    icon: "bi-list-check",
    blurb: "Plan next steps, track deadlines and stay on schedule.",
  },
};

export function CasePickerPage({ section }: { section: string }) {
  const info = SECTION_INFO[section] ?? SECTION_INFO.documents;
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.get<{ cases: CaseSummary[] }>("/cases")
      .then((d) => { if (!cancelled) setCases(d.cases); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load"); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1><i className={`bi ${info.icon}`} style={{ marginRight: 10, color: "var(--brand-600)" }} />{info.title}</h1>
          <p className="sub">{info.blurb} This section works inside a specific case.</p>
        </div>
      </div>
      {error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : cases === null ? (
        <div className="card"><Loading label="Loading cases…" /></div>
      ) : cases.length === 0 ? (
        <div className="card">
          <EmptyState icon={info.icon} title="No cases yet">
            Create a case first, then return here to work with your {info.title.toLowerCase()}.
          </EmptyState>
          <div className="flex" style={{ justifyContent: "center", paddingBottom: 10 }}>
            <Link to="/cases" className="btn btn-primary"><i className="bi bi-briefcase" /> Go to My Cases</Link>
          </div>
        </div>
      ) : cases.length === 1 ? (
        <Navigate to={`/cases/${cases[0].id}/${section}`} replace />
      ) : (
        <div className="card">
          <p className="text-faint" style={{ marginBottom: 4, fontSize: 13.5 }}>
            Select a case to open its {info.title.toLowerCase()} section.
          </p>
          <div className="list">
            {cases.map((c) => (
              <div key={c.id} className="list-item">
                <div className="li-main">
                  <div className="li-title">{c.title}</div>
                  <div className="li-desc">
                    {c.case_type || "Uncategorized"}{c.jurisdiction && ` · ${c.jurisdiction}`}
                    {c.is_demo && " · Demo"}
                  </div>
                  <div className="li-meta"><CaseStatusBadge status={c.status} /></div>
                </div>
                <button className="btn btn-outline btn-sm" onClick={() => navigate(`/cases/${c.id}/${section}`)}>
                  Open {info.title} <i className="bi bi-arrow-right" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}