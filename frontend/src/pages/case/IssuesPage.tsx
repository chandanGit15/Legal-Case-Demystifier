import { useState } from "react";
import { api } from "../../services/api";
import type { InfoGap, LegalIssue } from "../../types";
import { useCase } from "../../context/CaseContext";
import { useToast } from "../../context/ToastContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { ProvenanceBadge } from "../../components/ProvenanceBadge";
import { Badge, EmptyState, ErrorState, Loading } from "../../components/ui";

const CATEGORIES = ["contract", "employment", "residential tenancy", "property", "family", "consumer", "liability", "other"];

const ISSUE_STATUSES: [string, string][] = [
  ["open", "Open"],
  ["investigating", "Investigating"],
  ["resolved", "Resolved"],
  ["not_actionable", "Not actionable"],
];

const GAP_STATUSES: { value: string; label: string; tone: string }[] = [
  { value: "open", label: "Open", tone: "" },
  { value: "found", label: "Found", tone: "on-green" },
  { value: "not_applicable", label: "Not applicable", tone: "" },
];

const PRIORITY_ORDER = ["high", "medium", "low"];

function confidenceTone(level: string) {
  return level === "high" ? "badge-blue" : level === "low" ? "badge-neutral" : "badge-amber";
}
function priorityTone(level: string) {
  return level === "high" ? "badge-red" : level === "low" ? "badge-neutral" : "badge-amber";
}
function statusTone(status: string) {
  return status === "found" ? "green" : status === "not_applicable" ? "neutral" : "amber";
}

export function IssuesPage() {
  const { caseId, issues, gaps, loading, error, refresh } = useCase();
  const toast = useToast();

  // Manual issue form
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [confidence, setConfidence] = useState("medium");

  // Gap form + UI state
  const [gapOpen, setGapOpen] = useState(false);
  const [gq, setGq] = useState("");
  const [gwhy, setGwhy] = useState("");
  const [grel, setGrel] = useState("");
  const [ghow, setGhow] = useState("");
  const [gpriority, setGpriority] = useState("medium");

  const [busy, setBusy] = useState<string | null>(null); // which action is running
  const [formError, setFormError] = useState<string | null>(null);

  async function addIssue(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setFormError("An issue title is required."); return; }
    setBusy("addIssue"); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/issues`, { title, description, category, confidence });
      setTitle(""); setDescription(""); setCategory(""); setConfidence("medium");
      toast.success("Issue added to the case.");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the issue");
    } finally { setBusy(null); }
  }

  async function runIssueDetection() {
    setBusy("detectIssues"); setFormError(null);
    try {
      const res = await api.post<{ added_issues: unknown[]; duplicates_skipped?: number }>(`/cases/${caseId}/issues/detect`);
      const added = res.added_issues?.length ?? 0;
      if (added > 0) toast.success(`${added} potential issue${added === 1 ? "" : "s"} identified.`);
      else toast.info("No new issues identified — everything on file is already recorded.");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Detection failed");
    } finally { setBusy(null); }
  }

  async function runGapAnalysis() {
    setBusy("gapAnalyze"); setFormError(null);
    try {
      const res = await api.post<{ added_gaps: unknown[]; duplicates_skipped?: number }>(`/cases/${caseId}/information-gaps`);
      const added = res.added_gaps?.length ?? 0;
      if (added > 0) toast.success(`${added} information gap${added === 1 ? "" : "s"} identified.`);
      else toast.info("No new gaps found — nothing obviously missing on file.");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Gap analysis failed");
    } finally { setBusy(null); }
  }

  async function setIssueStatus(issue: LegalIssue, status: string) {
    await api.patch(`/cases/${caseId}/issues/${issue.id}`, { status });
    toast.success(`Issue marked ${status.replace("_", " ")}.`);
    refresh();
  }

  async function removeIssue(issue: LegalIssue) {
    if (!window.confirm(`Remove "${issue.title}"?`)) return;
    await api.del(`/cases/${caseId}/issues/${issue.id}`);
    toast.info("Issue removed.");
    refresh();
  }

  async function addGap(e: React.FormEvent) {
    e.preventDefault();
    if (!gq.trim()) { setFormError("Describe what is missing."); return; }
    setBusy("addGap"); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/gaps`, {
        question: gq, why_it_matters: gwhy, priority: gpriority,
        related_issue: grel, how_to_find: ghow,
      });
      setGq(""); setGwhy(""); setGrel(""); setGhow(""); setGpriority("medium"); setGapOpen(false);
      toast.success("Gap added to What's Missing?");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the gap");
    } finally { setBusy(null); }
  }

  async function setGapStatus(gap: InfoGap, status: string) {
    await api.patch(`/cases/${caseId}/gaps/${gap.id}`, { status });
    refresh();
  }

  async function removeGap(gap: InfoGap) {
    if (!window.confirm(`Remove "${gap.question}"?`)) return;
    await api.del(`/cases/${caseId}/gaps/${gap.id}`);
    toast.info("Gap removed.");
    refresh();
  }

  function jumpToIssue(issueTitle: string) {
    const title = issueTitle.trim().toLowerCase();
    if (!title) return;
    const match = issues.find((i) => i.title.trim().toLowerCase() === title || i.title.trim().toLowerCase().includes(title) || title.includes(i.title.trim().toLowerCase()));
    if (match) {
      document.getElementById(`issue-card-${match.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  const openGaps = gaps.filter((g) => g.status === "open");
  const foundGaps = gaps.filter((g) => g.status === "found");
  const naGaps = gaps.filter((g) => g.status === "not_applicable");
  const priorityGroups: Record<string, InfoGap[]> = { high: [], medium: [], low: [] };
  for (const g of openGaps) (priorityGroups[g.priority] ??= []).push(g);

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Legal issue detection & information gaps</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5 }}>
          Two connected modules: potential legal issues grounded in this case's facts, documents and timeline,
          and the information that is still missing to be confident about them. AI suggestions are
          interpretations — never legal certainty.
        </p>
      </div>

      {/* -------- AI run bar -------- */}
      <div className="card mb-3">
        <div className="flex-between">
          <div>
            <h3 className="card-title" style={{ marginBottom: 2 }}>AI analysis</h3>
            <p className="card-sub" style={{ margin: 0 }}>Run both analyzers — each is idempotent and skips what is already on file.</p>
          </div>
          <div className="flex" style={{ gap: 8 }}>
            <button className="btn btn-outline btn-sm" onClick={runIssueDetection} disabled={busy !== null}>
              <i className="bi bi-stars" /> {busy === "detectIssues" ? "Detecting…" : "Detect legal issues"}
            </button>
            <button className="btn btn-outline btn-sm" onClick={runGapAnalysis} disabled={busy !== null}>
              <i className="bi bi-search" /> {busy === "gapAnalyze" ? "Analyzing…" : "Find what's missing"}
            </button>
          </div>
        </div>
        {formError && <div className="alert-box error" style={{ marginTop: 12 }}>{formError}</div>}
      </div>

      {loading && <div className="card"><Loading label="Loading issues…" /></div>}
      {error && <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>}

      {/* -------- Potential legal issues -------- */}
      {!loading && !error && (
        <>
          <div className="flex-between mb-2">
            <div>
              <div className="overline">Potential legal issues</div>
              <p className="text-soft" style={{ margin: "3px 0 0", fontSize: 12.5 }}>
                Confidence reflects how strongly the information on file supports the issue — not a statement of legal certainty.
              </p>
            </div>
          </div>

          {/* Manual add */}
          <div className="card mb-3">
            <div className="flex-between mb-2">
              <h3 className="card-title">Add an issue you've identified</h3>
              <span className="card-sub">Rich details (evidence, documents, impact) come automatically from AI detection.</span>
            </div>
            <form onSubmit={addIssue}>
              <div className="form-row cols-2">
                <div>
                  <label className="form-label">Issue title *</label>
                  <input className="form-control" value={title} onChange={(e) => setTitle(e.target.value)}
                         placeholder="e.g. Possible breach of the service agreement" />
                </div>
                <div className="form-row cols-2" style={{ gridTemplateColumns: "1fr 1fr", margin: 0 }}>
                  <div>
                    <label className="form-label">Category</label>
                    <select className="form-select" value={category} onChange={(e) => setCategory(e.target.value)}>
                      <option value="">Select…</option>
                      {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="form-label">Confidence</label>
                    <select className="form-select" value={confidence} onChange={(e) => setConfidence(e.target.value)}>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                </div>
              </div>
              <div className="form-row">
                <div>
                  <label className="form-label">Why it may be an issue</label>
                  <textarea className="form-control" rows={2} value={description}
                            onChange={(e) => setDescription(e.target.value)} />
                </div>
              </div>
              <button className="btn btn-primary" disabled={busy !== null}>
                {busy === "addIssue" ? "Adding…" : <><i className="bi bi-plus-lg" /> Add issue</>}
              </button>
            </form>
          </div>

          {issues.length === 0 ? (
            <div className="card">
              <EmptyState icon="bi-shield-exclamation" title="No legal issues recorded">
                Add issues yourself or run AI detection — it works from the case facts, timeline, evidence and document analyses.
              </EmptyState>
            </div>
          ) : (
            <div className="mb-3">
              {issues.map((issue) => {
                const impact = issue.impact || "";
                const supporting = issue.supporting_facts || [];
                const docs = issue.related_documents || [];
                const missing = issue.missing_information || [];
                return (
                  <div key={issue.id} className="issue-card" id={`issue-card-${issue.id}`}>
                    <div className="issue-card-top">
                      <div style={{ minWidth: 0 }}>
                        <div className="issue-title">{issue.title}</div>
                        <div className="flex" style={{ gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                          <ProvenanceBadge source={issue.provenance} />
                          <span className={`badge ${confidenceTone(issue.confidence)}`}>Confidence: {issue.confidence}</span>
                          {issue.category && <span className="badge badge-neutral">{issue.category}</span>}
                          <Badge tone={issue.status}>{issue.status}</Badge>
                          {impact && <span className="badge badge-violet">Impact assessed</span>}
                        </div>
                        <div className="issue-warn">
                          <i className="bi bi-exclamation-triangle" />
                          <span>Confidence is an assessment of the available information — it is not legal certainty and does not predict an outcome.</span>
                        </div>
                        {issue.description && <div className="issue-why">{issue.description}</div>}
                        {impact && (
                          <div className="issue-impact">
                            <b><i className="bi bi-broadcast" style={{ marginRight: 5 }} /> Potential impact</b>
                            {impact}
                          </div>
                        )}
                        <div className="detail-grid">
                          <div className="detail-block">
                            <h5><i className="bi bi-collection" /> Supporting evidence</h5>
                            {supporting.length ? (
                              <ul>{supporting.map((s, i) => <li key={i}>{s}</li>)}</ul>
                            ) : <div className="detail-none">No supporting facts recorded.</div>}
                          </div>
                          <div className="detail-block">
                            <h5><i className="bi bi-file-earmark-text" /> Related documents</h5>
                            {docs.length ? (
                              <ul>{docs.map((d, i) => <li key={i}>{d}</li>)}</ul>
                            ) : <div className="detail-none">No documents linked yet.</div>}
                          </div>
                          <div className="detail-block">
                            <h5><i className="bi bi-question-circle" /> Missing information</h5>
                            {missing.length ? (
                              <ul>{missing.map((m, i) => <li key={i}>{m}</li>)}</ul>
                            ) : <div className="detail-none">Nothing missing recorded for this issue.</div>}
                          </div>
                        </div>
                      </div>
                      <div className="issue-actions">
                        <select className="form-select mini" value={issue.status}
                                onChange={(e) => void setIssueStatus(issue, e.target.value)}>
                          {ISSUE_STATUSES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                        </select>
                        <button className="btn btn-danger-ghost btn-sm" onClick={() => removeIssue(issue)} title="Remove issue">
                          <i className="bi bi-trash" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* -------- What's Missing? -------- */}
          <div className="card mt-2" style={{ borderColor: "var(--line-strong)" }}>
            <div className="flex-between" style={{ marginBottom: 6 }}>
              <div>
                <div className="overline mb-1"><i className="bi bi-patch-question" style={{ marginRight: 5 }} /> What's Missing?</div>
                <p className="text-soft" style={{ margin: 0, fontSize: 12.5, maxWidth: 620 }}>
                  Information that could materially change the analysis — each gap links to the issue it affects.
                </p>
              </div>
              <div className="flex" style={{ gap: 8 }}>
                <button className="btn btn-outline btn-sm" onClick={() => setGapOpen((v) => !v)}>
                  <i className="bi bi-plus-lg" /> Add a gap
                </button>
                <button className="btn btn-outline btn-sm" onClick={runGapAnalysis} disabled={busy !== null}>
                  <i className="bi bi-search" /> {busy === "gapAnalyze" ? "Analyzing…" : "Re-analyze"}
                </button>
              </div>
            </div>

            {gapOpen && (
              <form onSubmit={addGap} style={{ borderTop: "1px dashed var(--line)", paddingTop: 14, marginBottom: 14 }}>
                <div className="form-row cols-2">
                  <div>
                    <label className="form-label">What is missing? *</label>
                    <input className="form-control" value={gq} onChange={(e) => setGq(e.target.value)}
                           placeholder="e.g. Missing written notice of termination" />
                  </div>
                  <div>
                    <label className="form-label">Priority</label>
                    <select className="form-select" value={gpriority} onChange={(e) => setGpriority(e.target.value)}>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </div>
                </div>
                <div className="form-row">
                  <div>
                    <label className="form-label">Why it matters</label>
                    <textarea className="form-control" rows={2} value={gwhy} onChange={(e) => setGwhy(e.target.value)} />
                  </div>
                </div>
                <div className="form-row cols-2">
                  <div>
                    <label className="form-label">Affects issue</label>
                    <select className="form-select" value={grel} onChange={(e) => setGrel(e.target.value)}>
                      <option value="">Not linked to a recorded issue</option>
                      {issues.map((i) => <option key={i.id} value={i.title}>{i.title}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="form-label">How to find it</label>
                    <input className="form-control" value={ghow} onChange={(e) => setGhow(e.target.value)}
                           placeholder="e.g. Ask the other party in writing for a copy" />
                  </div>
                </div>
                {formError && <div className="alert-box error">{formError}</div>}
                <button className="btn btn-primary" disabled={busy !== null}>
                  {busy === "addGap" ? "Saving…" : <><i className="bi bi-plus-lg" /> Save gap</>}
                </button>
              </form>
            )}

            {gaps.length === 0 ? (
              <EmptyState icon="bi-patch-check" title="Nothing missing right now">
                Run "Find what's missing" — the analyzer surfaces documents, dates and records whose absence could change the analysis.
              </EmptyState>
            ) : (
              <>
                {/* Open gaps grouped by priority */}
                {PRIORITY_ORDER.map((level) => {
                  const group = priorityGroups[level] || [];
                  if (!group.length) return null;
                  return (
                    <div key={level} className="gap-block">
                      <div className="flex-between mb-2">
                        <div className="overline" style={{ textTransform: "none", letterSpacing: "0.03em", fontWeight: 700 }}>
                          <Badge tone={level}>{level === "high" ? "High priority" : level === "medium" ? "Medium priority" : "Low priority"}</Badge>
                          <span style={{ color: "var(--ink-faint)", fontSize: 12.5, fontWeight: 500, marginLeft: 8 }}>
                            {group.length} open
                          </span>
                        </div>
                      </div>
                      {group.map((gap) => (
                        <GapRow key={gap.id} gap={gap} issues={issues}
                                onStatus={(s) => void setGapStatus(gap, s)}
                                onDelete={() => void removeGap(gap)}
                                onJump={jumpToIssue} />
                      ))}
                    </div>
                  );
                })}

                {/* Found / not applicable */}
                {foundGaps.length > 0 && (
                  <div className="gap-block">
                    <div className="overline mb-2" style={{ fontSize: 11.5 }}><i className="bi bi-check2-circle" style={{ marginRight: 5 }} /> Found ({foundGaps.length})</div>
                    {foundGaps.map((gap) => (
                      <GapRow key={gap.id} gap={gap} issues={issues} dimmed
                              onStatus={(s) => void setGapStatus(gap, s)}
                              onDelete={() => void removeGap(gap)}
                              onJump={jumpToIssue} />
                    ))}
                  </div>
                )}
                {naGaps.length > 0 && (
                  <div className="gap-block">
                    <div className="overline mb-2" style={{ fontSize: 11.5 }}><i className="bi bi-x-circle" style={{ marginRight: 5 }} /> Not applicable ({naGaps.length})</div>
                    {naGaps.map((gap) => (
                      <GapRow key={gap.id} gap={gap} issues={issues}
                              onStatus={(s) => void setGapStatus(gap, s)}
                              onDelete={() => void removeGap(gap)}
                              onJump={jumpToIssue} />
                    ))}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="mt-3"><LegalDisclaimer /></div>
        </>
      )}
    </div>
  );
}

function GapRow({ gap, issues, dimmed, onStatus, onDelete, onJump }: {
  gap: InfoGap;
  issues: LegalIssue[];
  dimmed?: boolean;
  onStatus: (s: string) => void;
  onDelete: () => void;
  onJump: (issueTitle: string) => void;
}) {
  const linked = gap.related_issue
    ? issues.some((i) => i.title.trim().toLowerCase() === gap.related_issue!.trim().toLowerCase())
    : false;
  return (
    <div className={`gap-card ${dimmed ? "is-found" : ""}`}>
      <div className="gap-head">
        <div style={{ minWidth: 0 }}>
          <div className="gap-question">{gap.question}</div>
          <div className="gap-meta">
            {gap.related_issue && (
              <>
                <b>Affects:</b>{" "}
                {linked ? (
                  <span className="gap-tag" title="Jump to this issue" onClick={() => onJump(gap.related_issue!)}>
                    <i className="bi bi-link-45deg" style={{ marginRight: 3 }} />{gap.related_issue}
                  </span>
                ) : (
                  <span>{gap.related_issue}</span>
                )}
                <span style={{ margin: "0 8px", color: "var(--line-strong)" }}>·</span>
              </>
            )}
            <b>Why it matters:</b> {gap.why_it_matters || "Not recorded."}
          </div>
          {gap.how_to_find && (
            <div className="gap-how">
              <i className="bi bi-arrow-up-right" />
              <span><b>How to find it:</b> {gap.how_to_find}</span>
            </div>
          )}
        </div>
        <div className="flex" style={{ flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
          <div className="seg">
            {GAP_STATUSES.map((s) => (
              <button key={s.value}
                      className={gap.status === s.value ? (s.tone || "on") : ""}
                      onClick={() => gap.status !== s.value && onStatus(s.value)}
                      title={s.label}>
                {s.label}
              </button>
            ))}
          </div>
          <button className="btn btn-danger-ghost btn-sm" onClick={onDelete} title="Remove gap">
            <i className="bi bi-trash" />
          </button>
        </div>
      </div>
    </div>
  );
}
