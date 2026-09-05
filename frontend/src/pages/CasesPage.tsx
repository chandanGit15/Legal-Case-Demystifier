import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { CaseSummary } from "../types";
import { NewCaseModal } from "../components/NewCaseModal";
import { Badge, CaseStatusBadge, EmptyState, ErrorState, Loading, useFetch } from "../components/ui";

export function CasesPage() {
  const { data, loading, error, refetch } = useFetch<{ cases: CaseSummary[] }>("/cases");
  const [newCaseOpen, setNewCaseOpen] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const navigate = useNavigate();
  const [demoError, setDemoError] = useState<string | null>(null);

  async function loadDemoCase() {
    setDemoBusy(true);
    setDemoError(null);
    try {
      const res = await api.post<{ case: { id: number } }>("/demo-case");
      navigate(`/cases/${res.case.id}/overview`);
    } catch (e) {
      setDemoError(e instanceof Error ? e.message : "Could not create the demo case");
      setDemoBusy(false);
    }
  }

  if (loading) return <div className="page"><Loading label="Loading cases…" /></div>;
  if (error) return <div className="page"><ErrorState message={error} onRetry={refetch} /></div>;
  const cases = data?.cases ?? [];

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>My Cases</h1>
          <p className="sub">Every case is a structured workspace: timeline, documents, issues, risks, scenarios, negotiation, evidence and an action plan.</p>
        </div>
        <div className="flex" style={{ gap: 10 }}>
          <button className="btn btn-accent" onClick={() => setNewCaseOpen(true)}>
            <i className="bi bi-plus-lg" /> New Case
          </button>
        </div>
      </div>

      {demoError && <div className="alert-box error">{demoError}</div>}

      {cases.length === 0 ? (
        <div className="card">
          <EmptyState icon="bi-briefcase" title="No cases yet">
            Create a case from your situation, or load the demo case to explore the full workspace.
          </EmptyState>
          <div className="flex" style={{ justifyContent: "center", gap: 10, paddingBottom: 10 }}>
            <button className="btn btn-primary" onClick={() => setNewCaseOpen(true)}>
              <i className="bi bi-plus-lg" /> Create your first case
            </button>
            <button className="btn btn-outline" onClick={loadDemoCase} disabled={demoBusy}>
              <i className="bi bi-stars" /> {demoBusy ? "Loading…" : "Load demo case"}
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="card mb-3">
            <div className="flex-between">
              <p className="text-faint" style={{ margin: 0, fontSize: 13.5 }}>
                {cases.length} case{cases.length === 1 ? "" : "s"} · newest first
              </p>
              <button className="btn btn-outline btn-sm" onClick={loadDemoCase} disabled={demoBusy}>
                <i className="bi bi-stars" /> {demoBusy ? "Loading…" : "Load demo case"}
              </button>
            </div>
          </div>
          <div className="card">
            <div className="list">
              {cases.map((c) => (
                <Link key={c.id} to={`/cases/${c.id}/overview`}
                      className="list-item" style={{ textDecoration: "none", color: "inherit" }}>
                  <div className="li-main">
                    <div className="li-title">{c.title}</div>
                    <div className="li-desc">
                      {c.description ? `${c.description.slice(0, 160)}${c.description.length > 160 ? "…" : ""}` : "No description yet."}
                    </div>
                    <div className="li-meta">
                      <CaseStatusBadge status={c.status} />
                      <span className="badge badge-neutral">{c.case_type || "Uncategorized"}</span>
                      {c.jurisdiction && <span className="badge badge-neutral">{c.jurisdiction}</span>}
                      {c.is_demo && <span className="badge badge-demo">Demo</span>}
                      <span className="text-faint" style={{ fontSize: 12 }}>
                        {c.counts?.documents ?? 0} docs · {c.counts?.issues ?? 0} issues · {c.counts?.risks ?? 0} risks · {c.counts?.open_actions ?? 0} open actions
                      </span>
                    </div>
                  </div>
                  <i className="bi bi-chevron-right text-faint" />
                </Link>
              ))}
            </div>
          </div>
        </>
      )}

      <NewCaseModal open={newCaseOpen} onClose={() => setNewCaseOpen(false)} />
    </div>
  );
}