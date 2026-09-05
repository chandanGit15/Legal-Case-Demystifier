import { useState } from "react";
import { api } from "../../services/api";
import type { TimelineEvent } from "../../types";
import { useCase } from "../../context/CaseContext";
import { useToast } from "../../context/ToastContext";
import { EmptyState, ErrorState, Loading } from "../../components/ui";

const EVENT_TYPES: [string, string][] = [
  ["incident", "Incident"],
  ["communication", "Communication"],
  ["document", "Document"],
  ["deadline", "Deadline"],
  ["payment", "Payment"],
  ["legal_action", "Legal action"],
  ["other", "Other"],
];

const DATE_STATUS_META: Record<string, { label: string; tone: string }> = {
  user_confirmed: { label: "Confirmed date", tone: "green" },
  extracted: { label: "Extracted from source", tone: "blue" },
  potential: { label: "Date uncertain", tone: "amber" },
};

interface Candidate {
  date: string;
  title: string;
  description: string;
  event_type: string;
  importance: string;
  date_status: string;
  reason?: string;
  mode?: string;
}
interface ExtractionResult {
  events: Candidate[];
  missing_dates?: { about: string; context?: string }[];
  conflicts?: { about: string; between?: string[] }[];
  note?: string;
}

export function TimelinePage() {
  const { caseId, timeline, loading, error, refresh } = useCase();
  const toast = useToast();

  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [description, setDescription] = useState("");
  const [eventType, setEventType] = useState("incident");
  const [importance, setImportance] = useState("medium");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // AI extraction state
  const [extracting, setExtracting] = useState(false);
  const [extract, setExtract] = useState<ExtractionResult | null>(null);
  const [candidateDates, setCandidateDates] = useState<Record<number, string>>({});
  const [accepting, setAccepting] = useState<number | null>(null);

  async function addEvent(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !date) {
      setFormError("A title and a date are required.");
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      await api.post(`/cases/${caseId}/timeline`, {
        title, date, description, event_type: eventType, importance, date_status: "user_confirmed",
      });
      setTitle(""); setDate(""); setDescription(""); setEventType("incident"); setImportance("medium");
      setShowAdd(false);
      toast.success("Event added to the timeline.");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the event");
    } finally {
      setSaving(false);
    }
  }

  async function runExtraction() {
    setExtracting(true);
    setFormError(null);
    try {
      const res = await api.post<ExtractionResult>(`/cases/${caseId}/timeline/extract`);
      setExtract(res);
      const dates: Record<number, string> = {};
      res.events?.forEach((c, i) => { dates[i] = c.date ?? ""; });
      setCandidateDates(dates);
      if (res.events?.length) toast.success(`${res.events.length} dated event${res.events.length === 1 ? "" : "s"} found — review before adding.`);
      else toast.info("No new dated events found — nothing is added without your confirmation.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Extraction failed");
    } finally {
      setExtracting(false);
    }
  }

  async function acceptCandidate(idx: number) {
    const cand = extract?.events?.[idx];
    if (!cand) return;
    setAccepting(idx);
    try {
      await api.post(`/cases/${caseId}/timeline`, {
        title: cand.title, date: candidateDates[idx] || cand.date,
        description: cand.description, event_type: cand.event_type || "other",
        importance: cand.importance || "medium", date_status: cand.date_status || "extracted",
        source: cand.date_status === "potential" ? "ai" : "document",
      });
      toast.success(`"${cand.title}" added to the timeline.`);
      const remaining = (extract!.events ?? []).filter((_, i) => i !== idx);
      setExtract({ ...extract!, events: remaining });
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the event");
    } finally {
      setAccepting(null);
    }
  }

  async function removeEvent(ev: TimelineEvent) {
    if (!window.confirm(`Delete "${ev.title}" from the timeline?`)) return;
    await api.del(`/cases/${caseId}/timeline/${ev.id}`);
    toast.info("Event removed.");
    refresh();
  }

  async function confirmDate(ev: TimelineEvent) {
    await api.patch(`/cases/${caseId}/timeline/${ev.id}`, { date_status: "user_confirmed" });
    toast.success("Date confirmed by you.");
    refresh();
  }

  async function updateImportance(ev: TimelineEvent, importance: string) {
    await api.patch(`/cases/${caseId}/timeline/${ev.id}`, { importance });
    refresh();
  }

  const sorted = [...timeline].sort((a, b) => (a.date < b.date ? -1 : 1));
  const counts: Record<string, number> = {};
  for (const e of sorted) {
    const key = (e.date_status || "user_confirmed");
    counts[key] = (counts[key] || 0) + 1;
  }
  const unconfirmed = (counts.extracted || 0) + (counts.potential || 0);

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Case timeline</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5, maxWidth: 680 }}>
          Key dates in chronological order. Every event carries a type, an importance level and a date
          confidence label — nothing is silently assumed from AI extraction.
        </p>
      </div>

      {/* Toolbar */}
      <div className="flex-between mb-3">
        <div className="tl-legend">
          {EVENT_TYPES.map(([v, l]) => (
            <span key={v} className="sw"><i className={`dot-${v}`} /> {l}</span>
          ))}
        </div>
        <div className="flex" style={{ gap: 8 }}>
          <button className="btn btn-outline btn-sm" onClick={runExtraction} disabled={extracting}>
            <i className="bi bi-magic" /> {extracting ? "Scanning case material…" : "Extract dates from case"}
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAdd((v) => !v)}>
            <i className="bi bi-plus-lg" /> Add event
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="card mb-3">
          <h3 className="card-title">Add an event</h3>
          <form onSubmit={addEvent}>
            <div className="form-row cols-2">
              <div>
                <label className="form-label">Title *</label>
                <input className="form-control" value={title} onChange={(e) => setTitle(e.target.value)}
                       placeholder="e.g. Notice of termination sent" />
              </div>
              <div>
                <label className="form-label">Date *</label>
                <input className="form-control" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              </div>
            </div>
            <div className="form-row cols-2">
              <div>
                <label className="form-label">Event type</label>
                <select className="form-select" value={eventType} onChange={(e) => setEventType(e.target.value)}>
                  {EVENT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              <div>
                <label className="form-label">Importance</label>
                <select className="form-select" value={importance} onChange={(e) => setImportance(e.target.value)}>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="form-label">Details</label>
                <input className="form-control" value={description} onChange={(e) => setDescription(e.target.value)}
                       placeholder="What happened?" />
              </div>
            </div>
            {formError && <div className="alert-box error">{formError}</div>}
            <button className="btn btn-primary" disabled={saving}>
              {saving ? "Adding…" : <><i className="bi bi-plus-lg" /> Add to timeline</>}
            </button>
          </form>
        </div>
      )}

      {loading && <div className="card"><Loading label="Loading timeline…" /></div>}
      {error && <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>}

      {!loading && !error && unconfirmed > 0 && (
        <div className="alert-box info" style={{ marginBottom: 14 }}>
          <b>{unconfirmed} event{unconfirmed === 1 ? "" : "s"} on the timeline {unconfirmed === 1 ? "has" : "have"} a date that was extracted or inferred,
          not confirmed by you. Review and confirm those dates before relying on them.</b>
        </div>
      )}

      {!loading && !error && extract && (
        <div className="card mb-3" style={{ borderColor: "var(--violet)" }}>
          <div className="flex-between mb-2">
            <div>
              <div className="overline mb-1">AI extraction review</div>
              <p className="text-soft" style={{ margin: 0, fontSize: 12.5 }}>
                Dated events surfaced from the case material. Nothing is added until you accept it —
                potential dates are marked and never assumed.
              </p>
            </div>
            <button className="btn btn-danger-ghost btn-sm" onClick={() => setExtract(null)}><i className="bi bi-x-lg" /></button>
          </div>
          {extract.note && <div className="extract-note"><i className="bi bi-stars" style={{ marginRight: 5 }} />{extract.note}</div>}
          {(extract.conflicts?.length ?? 0) > 0 && (
            <div className="alert-box warn" style={{ marginBottom: 10 }}>
              <b>Conflicting dates found:</b>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {extract.conflicts!.map((c, i) => (
                  <li key={i} style={{ fontSize: 12.5 }}>{c.about}{c.between?.length ? ` — ${c.between.join(" vs ")}` : ""}</li>
                ))}
              </ul>
            </div>
          )}
          {(extract.missing_dates?.length ?? 0) > 0 && (
            <div className="alert-box warn" style={{ marginBottom: 10 }}>
              <b>Mentioned without a date (not added):</b>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                {extract.missing_dates!.map((m, i) => (
                  <li key={i} style={{ fontSize: 12.5 }}><b>{m.about}</b>{m.context ? ` — ${m.context}` : ""}</li>
                ))}
              </ul>
            </div>
          )}
          {(!extract.events || extract.events.length === 0) ? (
            <p className="text-soft" style={{ fontSize: 13, margin: 0 }}>
              No new dated events were found in the current case material. Dates are only extracted when a source
              states them explicitly — try uploading a document that contains dates.
            </p>
          ) : (
            extract.events.map((cand, i) => {
              const meta = DATE_STATUS_META[cand.date_status] || DATE_STATUS_META.extracted;
              return (
                <div key={i} className="extract-card">
                  <div className="flex-between" style={{ alignItems: "flex-start", gap: 12 }}>
                    <div style={{ minWidth: 0 }}>
                      <div className="cand-title">{cand.title}</div>
                      <div className="cand-reason">
                        {cand.description}
                        {cand.reason && <span style={{ display: "block", marginTop: 3 }}><b>Why flagged:</b> {cand.reason}</span>}
                      </div>
                      <div className="ev-meta" style={{ marginTop: 7 }}>
                        <span className={`badge badge-${meta.tone}`}>{meta.label}</span>
                        <span className="badge badge-neutral">{cand.event_type || "other"}</span>
                      </div>
                    </div>
                    <div className="flex" style={{ gap: 8, flexDirection: "column", alignItems: "flex-end" }}>
                      <div className="extract-date">
                        <input className="form-control" type="date" value={candidateDates[i] ?? ""}
                               onChange={(e) => setCandidateDates((d) => ({ ...d, [i]: e.target.value }))} />
                      </div>
                      <button className="btn btn-primary btn-sm" disabled={accepting === i || !candidateDates[i]}
                              onClick={() => acceptCandidate(i)}>
                        {accepting === i ? "Adding…" : <><i className="bi bi-plus-lg" /> Accept & add</>}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {!loading && !error && sorted.length === 0 && (
        <div className="card">
          <EmptyState icon="bi-calendar3" title="No timeline events yet">
            Add the key dates of your situation — they drive issue detection and risk analysis.
          </EmptyState>
        </div>
      )}
      {!loading && !error && sorted.length > 0 && (
        <div className="card">
          <div className="timeline">
            {sorted.map((ev) => {
              const type = ev.event_type || "other";
              const imp = ev.importance || "medium";
              const ds = ev.date_status || "user_confirmed";
              const meta = DATE_STATUS_META[ds];
              return (
                <div key={ev.id}
                     className={`tl-item tl-${type} imp-${imp} ${ds === "potential" ? "potential" : ""}`}>
                  <div className="tl-date">
                    <span className="day">{ev.date}</span>
                    {imp === "high" && <span className="badge badge-amber">important</span>}
                    {type === "deadline" && <span className="badge badge-amber">deadline</span>}
                    <span className={`badge badge-${meta?.tone ?? "green"}`} title="Date confidence">{meta?.label ?? ds}</span>
                  </div>
                  <div className="flex-between" style={{ gap: 8, alignItems: "flex-start" }}>
                    <div style={{ minWidth: 0 }}>
                      <div className="tl-title">{ev.title}</div>
                      {ev.description && <div className="li-desc">{ev.description}</div>}
                      <div className="li-meta">
                        <SourceBadge source={ev.source} />
                        <span className="badge badge-neutral">{EVENT_TYPES.find(([v]) => v === type)?.[1] ?? type}</span>
                        {imp !== "medium" && <span className="badge badge-neutral">{imp} importance</span>}
                      </div>
                    </div>
                    <div className="tl-actions">
                      {ds !== "user_confirmed" && (
                        <button className="btn btn-outline btn-sm" onClick={() => confirmDate(ev)}
                                title="I verified this date myself">
                          <i className="bi bi-check2-circle" /> Confirm date
                        </button>
                      )}
                      <select className="form-select mini" value={imp}
                              onChange={(e) => void updateImportance(ev, e.target.value)} title="Importance">
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                      </select>
                      <button className="btn btn-danger-ghost btn-sm" onClick={() => removeEvent(ev)}>
                        <i className="bi bi-trash" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function SourceBadge({ source }: { source: string }) {
  if (source === "document") return <span className="badge badge-green">from document</span>;
  if (source === "ai") return <span className="badge badge-violet">AI interpretation</span>;
  return <span className="badge badge-blue">user-provided</span>;
}
