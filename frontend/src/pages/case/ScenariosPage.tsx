import { useState } from "react";
import { api } from "../../services/api";
import type {
  Scenario,
  ScenarioAnalysis,
  ScenarioComparison,
  ScenarioRowKey,
} from "../../types";
import { useCase } from "../../context/CaseContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { EmptyState, ErrorState, Loading, RiskChip } from "../../components/ui";

const ROW_KEYS: ScenarioRowKey[] = [
  "risk", "evidence", "issues", "advantages", "disadvantages",
  "information_gaps", "negotiation_position", "next_steps",
];

function FactEditor({ facts, onChange }: { facts: string[]; onChange: (next: string[]) => void }) {
  const [draft, setDraft] = useState("");
  function add() {
    const t = draft.trim();
    if (!t) return;
    onChange([...facts, t]);
    setDraft("");
  }
  return (
    <div className="fact-editor">
      <div className="dim-head">Facts (change, add or remove)</div>
      {facts.map((f, i) => (
        <div key={i} className="fact-row">
          <input
            className="form-control"
            value={f}
            onChange={(e) => onChange(facts.map((x, j) => (j === i ? e.target.value : x)))}
          />
          <button type="button" className="btn btn-danger-ghost btn-sm" onClick={() => onChange(facts.filter((_, j) => j !== i))}>
            <i className="bi bi-x-lg" />
          </button>
        </div>
      ))}
      <div className="fact-row">
        <input className="form-control" value={draft} onChange={(e) => setDraft(e.target.value)}
               placeholder="Add a fact… e.g. Employer provided 30 days notice" onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
        <button type="button" className="btn btn-outline btn-sm" onClick={add}>
          <i className="bi bi-plus-lg" /> Add
        </button>
      </div>
    </div>
  );
}

function AnalysisView({ analysis, name }: { analysis: ScenarioAnalysis; name: string }) {
  if (!analysis || Object.keys(analysis).length === 0) return null;
  const blocks: { icon: string; title: string; items?: string[]; text?: string; tone?: string }[] = [
    { icon: "bi-compass", title: "Outcome", text: analysis.outcome },
    { icon: "bi-exclamation-octagon", title: "Potential issues", items: analysis.potential_issues, tone: "red" },
    { icon: "bi-arrow-left-right", title: "Risk changes", items: analysis.risk_changes },
    { icon: "bi-file-earmark-check", title: "Evidence requirements", items: analysis.evidence_requirements },
    { icon: "bi-people", title: "Negotiation leverage", items: analysis.negotiation_leverage },
    { icon: "bi-list-check", title: "Next steps", items: analysis.next_steps },
    { icon: "bi-question-circle", title: "Unknown information", items: analysis.unknown_information, tone: "faint" },
  ];
  return (
    <div className="doc-analysis mt-2">
      <div className="flex" style={{ gap: 8, alignItems: "center", marginBottom: 8 }}>
        <span className="badge badge-violet"><i className="bi bi-diagram-3" /> Scenario-Based AI Analysis</span>
        <RiskChip level={analysis.risk_level ?? "medium"} />
      </div>
      {analysis.note && <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}><i className="bi bi-info-circle" />{analysis.note}</div>}
      <div className="dim-grid-cards" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))" }}>
        {blocks.filter((b) => b.text || (b.items && b.items.length > 0)).map((b, i) => (
          <div key={i} className="scen-block">
            <div className="dim-head"><i className={`bi ${b.icon}`} /> {b.title}</div>
            {b.text && <div className={`text-soft ${b.tone === "faint" ? "text-faint" : ""}`}>{b.text}</div>}
            {b.items && b.items.length > 0 && (
              <ul className="dim-list" style={{ color: b.tone === "red" ? "var(--red)" : "var(--ink-soft)" }}>
                {b.items.map((it, j) => <li key={j}>{it}</li>)}
              </ul>
            )}
          </div>
        ))}
      </div>
      <div className="text-faint mt-1" style={{ fontSize: 11.5 }}>
        <i className="bi bi-exclamation-triangle" /> {name}: scenario analysis is exploratory — it is
        never a guaranteed prediction of what will happen.
      </div>
    </div>
  );
}

export function ScenariosPage() {
  const { caseId, scenarios, loading, error, refresh, caseData, issues, evidence, gaps, riskAssessment } = useCase();

  // Create form
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [parameters, setParameters] = useState("");
  const [facts, setFacts] = useState<string[]>([]);

  // Per-scenario editing
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editParams, setEditParams] = useState("");
  const [editFacts, setEditFacts] = useState<string[]>([]);
  const [savingEdit, setSavingEdit] = useState(false);

  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [comparing, setComparing] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const openVerified = evidence.filter((e) => e.verification === "verified").length;
  const openGaps = gaps.filter((g) => g.status === "open").length;

  function startEdit(s: Scenario) {
    setEditingId(s.id);
    setEditName(s.name);
    setEditDesc(s.description ?? "");
    setEditParams(s.parameters ?? "");
    setEditFacts((s.facts ?? []).map((f) => f.text));
  }

  async function addScenario(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setFormError("A scenario name is required."); return; }
    setFormError(null);
    try {
      await api.post(`/cases/${caseId}/scenarios`, {
        name, description, parameters,
        facts: facts.filter((f) => f.trim()).map((text) => ({ text })),
      });
      setName(""); setDescription(""); setParameters(""); setFacts([]);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not create the scenario");
    }
  }

  async function saveEdit(s: Scenario) {
    setSavingEdit(true); setFormError(null);
    try {
      await api.put(`/cases/${caseId}/scenarios/${s.id}`, {
        name: editName, description: editDesc, parameters: editParams,
        facts: editFacts.filter((f) => f.trim()).map((text) => ({ text })),
      });
      setEditingId(null);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save the scenario");
    } finally { setSavingEdit(false); }
  }

  async function analyze(s: Scenario) {
    setAnalyzingId(s.id);
    try {
      await api.post(`/cases/${caseId}/scenarios/${s.id}/analyze`);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Analysis failed");
    } finally { setAnalyzingId(null); }
  }

  async function runComparison() {
    if (selected.length < 2) return;
    setComparing(true);
    setFormError(null);
    try {
      const res = await api.post<ScenarioComparison>(`/cases/${caseId}/scenarios/compare`, { scenario_ids: selected });
      setComparison(res);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Comparison failed");
    } finally { setComparing(false); }
  }

  async function remove(id: number) {
    if (!window.confirm("Delete this scenario?")) return;
    await api.del(`/cases/${caseId}/scenarios/${id}`);
    setSelected((prev) => prev.filter((x) => x !== id));
    refresh();
  }

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">What-if simulator</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5 }}>
          Change the facts, define alternative futures, and compare paths side by side against
          the case as it stands. Scenario-Based AI Analysis is exploratory — never a guaranteed prediction.
        </p>
      </div>

      {formError && <div className="alert-box error mb-3">{formError}</div>}

      <div className="card-grid cols-2 mb-3" style={{ alignItems: "start" }}>
        <div className="card">
          <h3 className="card-title">New scenario</h3>
          <form onSubmit={addScenario}>
            <label className="form-label">Scenario name *</label>
            <input className="form-control mb-2" value={name} onChange={(e) => setName(e.target.value)}
                   placeholder="e.g. Employer provided 30 days notice" />
            <div className="form-row cols-2">
              <div>
                <label className="form-label">What happens?</label>
                <textarea className="form-control" rows={2} value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          placeholder="Describe the alternative in plain terms." />
              </div>
              <div>
                <label className="form-label">Assumptions / parameters</label>
                <textarea className="form-control" rows={2} value={parameters}
                          onChange={(e) => setParameters(e.target.value)}
                          placeholder="What must be true? e.g. 'The landlord misses the itemization deadline.'" />
              </div>
            </div>
            <div className="mt-2"><FactEditor facts={facts} onChange={setFacts} /></div>
            <button className="btn btn-primary mt-2"><i className="bi bi-diagram-3" /> Create scenario</button>
          </form>
        </div>

        <div className="card">
          <h3 className="card-title">Current scenario <span className="badge badge-neutral badge-xs">baseline</span></h3>
          <p className="text-soft" style={{ fontSize: 12.5, marginTop: 0 }}>
            Every alternative is compared against the case exactly as recorded today.
          </p>
          <div className="current-facts">
            <div className="cf-row"><span>Case status</span><b>{caseData?.status?.replace(/_/g, " ") ?? "—"}</b></div>
            <div className="cf-row"><span>Potential issues</span><b>{issues.length}</b></div>
            <div className="cf-row"><span>Evidence verified</span><b>{openVerified} of {evidence.length}</b></div>
            <div className="cf-row"><span>Open information gaps</span><b>{openGaps}</b></div>
            <div className="cf-row">
              <span>Overall risk</span>
              {riskAssessment
                ? <RiskChip level={riskAssessment.overall_level} />
                : <b className="text-faint">not assessed</b>}
            </div>
          </div>
          <div className="disclaimer disclaimer-warn mt-2" style={{ fontSize: 11.5 }}>
            <i className="bi bi-exclamation-triangle" /> Run the risk analysis on the Risk Analysis
            tab to keep this baseline current.
          </div>
        </div>
      </div>

      {loading && <div className="card"><Loading label="Loading scenarios…" /></div>}
      {error && <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>}
      {!loading && !error && scenarios.length === 0 && (
        <div className="card">
          <EmptyState icon="bi-diagram-3" title="No scenarios yet">
            Create one to explore — e.g. "we settle now" vs "we wait for the itemized statement".
          </EmptyState>
        </div>
      )}

      {!loading && !error && scenarios.length > 0 && (
        <>
          {scenarios.length >= 2 && (
            <div className="card mb-3">
              <div className="flex-between mb-2">
                <h3 className="card-title">Compare scenarios</h3>
                <button className="btn btn-outline btn-sm" disabled={selected.length < 2 || comparing}
                        onClick={runComparison}>
                  <i className="bi bi-arrows-angle-expand" /> {comparing ? "Comparing…" : "Compare selected"}
                </button>
              </div>
              <p className="text-faint" style={{ fontSize: 12.5, marginTop: 0 }}>
                Select two or more scenarios. The comparison table always includes the current scenario
                as its first column. ({selected.length} selected)
              </p>
              <div className="flex" style={{ gap: 8, flexWrap: "wrap" }}>
                {scenarios.map((s) => (
                  <label key={s.id} className="badge badge-neutral"
                         style={{ cursor: "pointer", padding: "6px 12px", fontSize: 12.5 }}>
                    <input type="checkbox" style={{ marginRight: 6, accentColor: "var(--brand-600)" }}
                           checked={selected.includes(s.id)}
                           onChange={(e) => {
                             setSelected((prev) => e.target.checked
                               ? [...prev, s.id]
                               : prev.filter((x) => x !== s.id));
                           }} />
                    {s.name}
                  </label>
                ))}
              </div>
              {comparison && (
                <div className="mt-2">
                  {comparison.note && <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}><i className="bi bi-info-circle" />{comparison.note}</div>}
                  <div className="compare-scroll">
                    <table className="compare-table">
                      <thead>
                        <tr>
                          <th className="row-label">Dimension</th>
                          {comparison.columns.map((c) => (
                            <th key={c.id}>
                              {c.name}
                              <div className="mt-1"><RiskChip level={c.risk_level} /></div>
                              {c.summary && <div className="compare-col-summary">{c.summary}</div>}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {ROW_KEYS.map((rk) => (
                          <tr key={rk}>
                            <td className="row-label">{comparison.row_labels?.[rk] ?? rk}</td>
                            {comparison.columns.map((c) => (
                              <td key={c.id}>{comparison.rows[c.id]?.[rk] ?? "—"}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {comparison.trade_offs && (
                    <div className="text-soft mt-2" style={{ fontSize: 13 }}><b>Trade-offs:</b> {comparison.trade_offs}</div>
                  )}
                  {comparison.recommendation && (
                    <div className="text-soft mt-1" style={{ fontSize: 13 }}><b>Recommendation:</b> {comparison.recommendation}</div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="card">
            <div className="list">
              {scenarios.map((s) => {
                const analyzed = s.analysis && Object.keys(s.analysis).length > 0;
                const isEditing = editingId === s.id;
                return (
                  <div key={s.id} className="list-item" style={{ flexDirection: "column", alignItems: "stretch" }}>
                    <div className="flex-between" style={{ alignItems: "flex-start" }}>
                      <div className="li-main">
                        <div className="flex" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <label className="checkbox-inline" style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 6 }}>
                            <input type="checkbox" style={{ accentColor: "var(--brand-600)" }}
                                   checked={selected.includes(s.id)}
                                   onChange={(e) => setSelected((prev) => e.target.checked ? [...prev, s.id] : prev.filter((x) => x !== s.id))} />
                          </label>
                          <div className="li-title">{isEditing ? editName : s.name}</div>
                          {!isEditing && <RiskChip level={s.risk_level} />}
                          {!isEditing && analyzed && <span className="badge badge-violet badge-xs"><i className="bi bi-diagram-3" /> Analyzed</span>}
                        </div>
                        {!isEditing && s.description && <div className="li-desc">{s.description}</div>}
                        {!isEditing && s.parameters && (
                          <div className="li-desc text-faint" style={{ fontSize: 12.5 }}>
                            <i className="bi bi-sliders" /> {s.parameters}
                          </div>
                        )}
                        {!isEditing && (s.facts ?? []).length > 0 && (
                          <div className="scen-facts">
                            {(s.facts ?? []).map((f, i) => (
                              <span key={i} className="badge badge-neutral">{f.text}</span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="flex" style={{ gap: 6, flexDirection: "column", alignItems: "flex-end" }}>
                        <div className="flex" style={{ gap: 6 }}>
                          {!isEditing && (
                            <button className="btn btn-outline btn-sm" onClick={() => startEdit(s)}>
                              <i className="bi bi-pencil" /> Facts
                            </button>
                          )}
                          {!isEditing && !analyzed && (
                            <button className="btn btn-outline btn-sm" disabled={analyzingId === s.id}
                                    onClick={() => analyze(s)}>
                              {analyzingId === s.id ? "Analyzing…" : <><i className="bi bi-stars" /> Analyze</>}
                            </button>
                          )}
                          <button className="btn btn-danger-ghost btn-sm" onClick={() => remove(s.id)}>
                            <i className="bi bi-trash" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {isEditing && (
                      <div className="edit-panel mt-2">
                        <label className="form-label">Scenario name</label>
                        <input className="form-control mb-2" value={editName} onChange={(e) => setEditName(e.target.value)} />
                        <div className="form-row cols-2">
                          <div>
                            <label className="form-label">What happens?</label>
                            <textarea className="form-control" rows={2} value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
                          </div>
                          <div>
                            <label className="form-label">Assumptions / parameters</label>
                            <textarea className="form-control" rows={2} value={editParams} onChange={(e) => setEditParams(e.target.value)} />
                          </div>
                        </div>
                        <div className="mt-2"><FactEditor facts={editFacts} onChange={setEditFacts} /></div>
                        <div className="flex mt-2" style={{ gap: 8 }}>
                          <button className="btn btn-primary btn-sm" disabled={savingEdit}
                                  onClick={() => saveEdit(s)}>
                            {savingEdit ? "Saving…" : <><i className="bi bi-save" /> Save facts</>}
                          </button>
                          <button className="btn btn-ghost btn-sm" onClick={() => setEditingId(null)}>Cancel</button>
                        </div>
                      </div>
                    )}

                    {!isEditing && analyzed && <AnalysisView analysis={s.analysis} name={s.name} />}
                  </div>
                );
              })}
            </div>
          </div>
          <div className="mt-3"><LegalDisclaimer /></div>
        </>
      )}
    </div>
  );
}