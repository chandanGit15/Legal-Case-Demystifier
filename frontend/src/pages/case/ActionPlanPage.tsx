import { useState } from "react";
import { api } from "../../services/api";
import type { ActionItem, Deadline, DeadlineCandidate } from "../../types";
import { useCase } from "../../context/CaseContext";
import { useToast } from "../../context/ToastContext";
import { Badge, EmptyState, ErrorState, Loading } from "../../components/ui";

const STATUS_GROUPS: { key: string; label: string; icon: string }[] = [
  { key: "not_started", label: "Not started", icon: "bi-circle" },
  { key: "in_progress", label: "In progress", icon: "bi-arrow-repeat" },
  { key: "completed", label: "Completed", icon: "bi-check-circle" },
  { key: "skipped", label: "Skipped", icon: "bi-slash-circle" },
];

const PRIORITY_TONE: Record<string, string> = {
  high: "red", medium: "amber", low: "green",
};

function daysUntil(dateStr: string): number {
  const d = new Date(dateStr + "T00:00:00");
  return Math.ceil((d.getTime() - Date.now()) / 86400000);
}

export function ActionPlanPage() {
  const { caseId, actions, deadlines, issues, loading, error, refresh } = useCase();
  const toast = useToast();

  // Action form.
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [reason, setReason] = useState("");
  const [relatedIssue, setRelatedIssue] = useState("");
  const [requiredEvidence, setRequiredEvidence] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [savingAction, setSavingAction] = useState(false);

  // Deadline form.
  const [dTitle, setDTitle] = useState("");
  const [dDue, setDDue] = useState("");
  const [dDescription, setDDescription] = useState("");
  const [savingDeadline, setSavingDeadline] = useState(false);

  // AI.
  const [generating, setGenerating] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [candidates, setCandidates] = useState<DeadlineCandidate[] | null>(null);
  const [accepting, setAccepting] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  async function addAction(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setFormError("An action title is required."); return; }
    setSavingAction(true); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/action-plan`, {
        title, description, priority, reason, related_issue: relatedIssue,
        required_evidence: requiredEvidence, due_date: dueDate,
      });
      setTitle(""); setDescription(""); setPriority("medium"); setReason("");
      setRelatedIssue(""); setRequiredEvidence(""); setDueDate("");
      refresh();
      toast.success("Action added.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the action");
    } finally { setSavingAction(false); }
  }

  async function generate() {
    setGenerating(true); setFormError(null);
    try {
      const res = await api.post<{ added_actions?: ActionItem[]; duplicates_skipped?: number }>(`/cases/${caseId}/action-plan/generate`);
      refresh();
      if ((res.added_actions ?? []).length > 0) {
        toast.success(`${res.added_actions!.length} action(s) added from the case record.`);
      } else {
        toast.info(`No new actions — ${res.duplicates_skipped ?? 0} already on the plan.`);
      }
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not generate the plan");
    } finally { setGenerating(false); }
  }

  async function setActionStatus(a: ActionItem, status: string) {
    await api.put(`/action-items/${a.id}`, { status });
    refresh();
  }

  async function removeAction(id: number) {
    if (!window.confirm("Delete this action item?")) return;
    await api.del(`/cases/${caseId}/actions/${id}`);
    refresh();
  }

  async function addDeadline(e: React.FormEvent) {
    e.preventDefault();
    if (!dTitle.trim() || !dDue) { setFormError("A deadline title and date are required."); return; }
    setSavingDeadline(true); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/deadlines`, { title: dTitle, due_date: dDue, description: dDescription });
      setDTitle(""); setDDue(""); setDDescription("");
      refresh();
      toast.success("Deadline added.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the deadline");
    } finally { setSavingDeadline(false); }
  }

  async function setDeadlineStatus(d: Deadline, status: string) {
    await api.patch(`/cases/${caseId}/deadlines/${d.id}`, { status });
    refresh();
  }

  async function removeDeadline(id: number) {
    if (!window.confirm("Delete this deadline?")) return;
    await api.del(`/cases/${caseId}/deadlines/${id}`);
    refresh();
  }

  async function extractDates() {
    setExtracting(true); setFormError(null);
    try {
      const res = await api.post<{ candidates?: DeadlineCandidate[]; note?: string }>(`/cases/${caseId}/deadlines/extract`);
      setCandidates(res.candidates ?? []);
      if ((res.candidates ?? []).length === 0) toast.info(res.note ?? "No candidate dates found.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Extraction failed");
    } finally { setExtracting(false); }
  }

  async function acceptCandidate(i: number) {
    const c = candidates![i];
    setAccepting(i); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/deadlines`, {
        title: c.title, due_date: c.date, description: c.note ?? "",
        source: c.confidence === "extracted" ? "ai" : "user",
      });
      setCandidates((prev) => prev!.filter((_, j) => j !== i));
      refresh();
      toast.success("Date added to the tracker.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the date");
    } finally { setAccepting(null); }
  }

  const grouped = (key: string) => actions.filter((a) => a.status === key);
  const now = new Date();
  const bucket = (d: Deadline): "overdue" | "soon" | "upcoming" | "done" => {
    if (d.status === "completed" || d.status === "missed") return "done";
    const days = daysUntil(d.due_date);
    if (days < 0) return "overdue";
    if (days <= 7) return "soon";
    return "upcoming";
  };
  const buckets: Record<string, Deadline[]> = { overdue: [], soon: [], upcoming: [], done: [] };
  deadlines.forEach((d) => buckets[bucket(d)].push(d));

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Action plan &amp; deadlines</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5 }}>
          Concrete next steps with reasons and required evidence, plus a deadline tracker
          grouped by urgency. AI-generated actions always trace to the case record.
        </p>
      </div>

      {formError && <div className="alert-box error mb-3">{formError}</div>}

      <div className="card mb-3">
        <div className="flex-between mb-2">
          <h3 className="card-title">Action plan</h3>
          <button className="btn btn-outline btn-sm" onClick={generate} disabled={generating}>
            <i className="bi bi-stars" /> {generating ? "Generating…" : "Generate action plan from case"}
          </button>
        </div>
        <form onSubmit={addAction}>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Action title *</label>
              <input className="form-control" value={title} onChange={(e) => setTitle(e.target.value)}
                     placeholder="e.g. Obtain the itemized statement of deductions" />
            </div>
            <div className="form-row cols-2" style={{ gridTemplateColumns: "1fr 1fr", margin: 0 }}>
              <div>
                <label className="form-label">Priority</label>
                <select className="form-select" value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                </select>
              </div>
              <div>
                <label className="form-label">Deadline</label>
                <input className="form-control" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
              </div>
            </div>
          </div>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Description</label>
              <textarea className="form-control" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div>
              <label className="form-label">Reason (why this matters)</label>
              <textarea className="form-control" rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
                        placeholder="What makes this step necessary?" />
            </div>
          </div>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Related issue</label>
              <select className="form-select" value={relatedIssue} onChange={(e) => setRelatedIssue(e.target.value)}>
                <option value="">None</option>
                {issues.map((i) => <option key={i.id} value={i.title}>{i.title}</option>)}
              </select>
            </div>
            <div>
              <label className="form-label">Required evidence</label>
              <input className="form-control" value={requiredEvidence} onChange={(e) => setRequiredEvidence(e.target.value)}
                     placeholder="What proof backs or enables this step?" />
            </div>
          </div>
          <button className="btn btn-primary mt-2" disabled={savingAction}>
            {savingAction ? "Adding…" : <><i className="bi bi-plus-lg" /> Add action</>}
          </button>
        </form>
      </div>

      <div className="mb-3">
        {loading ? <div className="card"><Loading label="Loading actions…" /></div>
          : error ? <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>
          : actions.length === 0 ? (
            <div className="card">
              <EmptyState icon="bi-list-check" title="No action items yet">
                Add actions manually or generate an action plan from the case — it turns gaps,
                risks, unverified evidence and deadlines into concrete steps.
              </EmptyState>
            </div>
          ) : (
            <div className="flex" style={{ gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
              {STATUS_GROUPS.map((g) => {
                const items = grouped(g.key);
                return (
                  <div key={g.key} className="ap-column">
                    <div className="ap-column-head">
                      <i className={`bi ${g.icon}`} />
                      {g.label}
                      <span className="ap-count">{items.length}</span>
                    </div>
                    {items.length === 0 && <div className="text-faint" style={{ fontSize: 12.5, padding: "8px 4px" }}>Empty</div>}
                    {items.map((a) => (
                      <div key={a.id} className="card ap-card">
                        <div className="flex-between" style={{ alignItems: "flex-start" }}>
                          <div style={{ fontWeight: 700, fontSize: 13.5, lineHeight: 1.4 }}>{a.title}</div>
                          <button className="btn btn-danger-ghost btn-sm" onClick={() => removeAction(a.id)}>
                            <i className="bi bi-trash" />
                          </button>
                        </div>
                        {a.description && <div className="text-soft" style={{ fontSize: 12.5, marginTop: 4 }}>{a.description}</div>}
                        <div className="li-meta" style={{ marginTop: 6 }}>
                          <Badge tone={PRIORITY_TONE[a.priority] ?? "neutral"}>{a.priority}</Badge>
                          {a.due_date && (
                            <Badge tone={daysUntil(a.due_date) < 0 ? "red" : daysUntil(a.due_date) <= 7 ? "amber" : "green"}>
                              {daysUntil(a.due_date) < 0 ? `${Math.abs(daysUntil(a.due_date))}d overdue` : `${daysUntil(a.due_date)}d left`}
                            </Badge>
                          )}
                          {a.category === "ai_plan" && <span className="badge badge-violet" style={{ fontSize: 10 }}>AI</span>}
                        </div>
                        {a.reason && (
                          <div className="ap-reason"><i className="bi bi-lightbulb" /> {a.reason}</div>
                        )}
                        {a.related_issue && (
                          <div className="ap-chip"><i className="bi bi-exclamation-circle" /> {a.related_issue}</div>
                        )}
                        {a.required_evidence && (
                          <div className="ap-chip" style={{ color: "var(--brand-800)", background: "var(--brand-50)" }}>
                            <i className="bi bi-paperclip" /> {a.required_evidence}
                          </div>
                        )}
                        <div className="mt-2">
                          <select className="form-select" style={{ width: "100%", padding: "4px 8px", fontSize: 12.5 }}
                                  value={a.status} onChange={(e) => setActionStatus(a, e.target.value)}>
                            {STATUS_GROUPS.map((sg) => <option key={sg.key} value={sg.key}>{sg.label}</option>)}
                          </select>
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
      </div>

      <div className="card mb-3">
        <div className="flex-between mb-2">
          <h3 className="card-title">Deadline tracker</h3>
          <button className="btn btn-outline btn-sm" onClick={extractDates} disabled={extracting}>
            <i className="bi bi-calendar2-week" /> {extracting ? "Extracting…" : "Extract dates from case"}
          </button>
        </div>
        <form onSubmit={addDeadline} className="mb-3">
          <div className="form-row cols-3">
            <div>
              <label className="form-label">Deadline title *</label>
              <input className="form-control" value={dTitle} onChange={(e) => setDTitle(e.target.value)}
                     placeholder="e.g. Itemized statement window" />
            </div>
            <div>
              <label className="form-label">Date *</label>
              <input className="form-control" type="date" value={dDue} onChange={(e) => setDDue(e.target.value)} />
            </div>
            <div>
              <label className="form-label">Notes</label>
              <input className="form-control" value={dDescription} onChange={(e) => setDDescription(e.target.value)} />
            </div>
          </div>
          <button className="btn btn-primary btn-sm mt-2" disabled={savingDeadline}>
            {savingDeadline ? "Adding…" : <><i className="bi bi-plus-lg" /> Add deadline</>}
          </button>
        </form>

        {candidates !== null && candidates.length > 0 && (
          <div className="extract-tray mb-3">
            <div className="dim-head mb-1"><i className="bi bi-calendar-check" /> Extracted dates — review before adding</div>
            {candidates.map((c, i) => (
              <div key={i} className="extract-row">
                <div className="flex" style={{ gap: 8, alignItems: "center", flex: "1 1 auto", flexWrap: "wrap" }}>
                  <b>{c.title}</b>
                  <span className="mono" style={{ fontSize: 12.5 }}>{c.date}</span>
                  <span className={`badge ${c.confidence === "extracted" ? "badge-blue" : "badge-amber"}`} style={{ fontSize: 10 }}>
                    {c.confidence === "extracted" ? "extracted" : "needs confirmation"}
                  </span>
                </div>
                <div className="text-faint" style={{ fontSize: 11.5, flex: "0 1 100%" }}>
                  {c.note} — source: {c.source}
                </div>
                <button className="btn btn-primary btn-sm" disabled={accepting === i} onClick={() => acceptCandidate(i)}>
                  {accepting === i ? "Adding…" : <><i className="bi bi-check-lg" /> Add to tracker</>}
                </button>
              </div>
            ))}
            <button className="btn btn-ghost btn-sm mt-1" onClick={() => setCandidates(null)}>Dismiss</button>
          </div>
        )}
        {candidates !== null && candidates.length === 0 && (
          <div className="disclaimer disclaimer-info mb-3" style={{ fontSize: 12 }}>
            <i className="bi bi-info-circle" /> No dated deadlines found in the case documents.
            Add relevant dates manually above.
          </div>
        )}

        <div className="disclaimer disclaimer-warn mb-3" style={{ fontSize: 11.5 }}>
          <i className="bi bi-exclamation-triangle" /> Extracted dates are not legal deadlines.
          A legally binding deadline must be verified against jurisdiction-specific rules before
          relying on it.
        </div>

        {loading ? <Loading label="Loading deadlines…" />
          : error ? <ErrorState message={error} onRetry={() => void refresh()} />
          : deadlines.length === 0 ? (
            <EmptyState icon="bi-alarm" title="No deadlines tracked">
              Deadlines can be flagged automatically during document analysis, extracted from the
              case, or added manually.
            </EmptyState>
          ) : (
            <div className="card-grid cols-3">
              {[
                { key: "overdue", label: "Overdue", tone: "red", icon: "bi-exclamation-octagon" },
                { key: "soon", label: "Due soon (≤ 7 days)", tone: "amber", icon: "bi-alarm" },
                { key: "upcoming", label: "Upcoming", tone: "green", icon: "bi-calendar3" },
              ].map((b) => (
                <div key={b.key}>
                  <div className="dl-head"><i className={`bi ${b.icon}`} style={{ color: `var(--${b.tone})` }} /> {b.label}</div>
                  <div className="dl-list">
                    {buckets[b.key].length === 0 && <div className="text-faint" style={{ fontSize: 12.5 }}>None</div>}
                    {buckets[b.key].map((d) => {
                      const days = daysUntil(d.due_date);
                      return (
                        <div key={d.id} className="dl-item">
                          <div className="flex-between" style={{ alignItems: "flex-start" }}>
                            <div>
                              <div style={{ fontWeight: 600, fontSize: 13 }}>{d.title}</div>
                              <div className="mono text-faint" style={{ fontSize: 12 }}>{d.due_date} · {days < 0 ? `${Math.abs(days)}d overdue` : days === 0 ? "today" : `${days}d left`}</div>
                              {d.description && <div className="text-faint" style={{ fontSize: 11.5 }}>{d.description}</div>}
                              {d.source === "ai" && <span className="badge badge-violet" style={{ fontSize: 10, marginTop: 3 }}>flagged by AI</span>}
                            </div>
                            <button className="btn btn-danger-ghost btn-sm" onClick={() => removeDeadline(d.id)}>
                              <i className="bi bi-trash" />
                            </button>
                          </div>
                          <select className="form-select" style={{ width: "100%", padding: "3px 8px", fontSize: 12, marginTop: 6 }}
                                  value={d.status} onChange={(e) => setDeadlineStatus(d, e.target.value)}>
                            <option value="pending">pending</option>
                            <option value="completed">completed</option>
                            <option value="missed">missed</option>
                          </select>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}