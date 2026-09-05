import { useState } from "react";
import { api } from "../../services/api";
import type { EvidenceItem, LegalIssue } from "../../types";
import { useCase } from "../../context/CaseContext";
import { useToast } from "../../context/ToastContext";
import { ProvenanceBadge } from "../../components/ProvenanceBadge";
import { Badge, EmptyState, ErrorState, Loading } from "../../components/ui";

const TYPES: [string, string, string][] = [
  ["document", "Document", "bi-file-earmark-text"],
  ["email", "Email", "bi-envelope"],
  ["message", "Message", "bi-chat-left-text"],
  ["photo", "Photo", "bi-image"],
  ["contract", "Contract", "bi-file-earmark-text"],
  ["receipt", "Receipt", "bi-receipt"],
  ["witness", "Witness", "bi-person-badge"],
  ["other", "Other", "bi-paperclip"],
];

const VERIFY: [string, string][] = [
  ["unverified", "Unverified"],
  ["verified", "Verified"],
  ["disputed", "Disputed"],
];

function iconFor(type: string) {
  const hit = TYPES.find(([v]) => v === type);
  if (hit) return hit[2];
  if (type === "recording") return "bi-mic";
  if (type === "message") return "bi-chat-left-text";
  return "bi-paperclip";
}
function typeLabel(type: string) {
  return TYPES.find(([v]) => v === type)?.[1] ?? type;
}
function importanceTone(v: string) {
  return v === "high" ? "badge-amber" : v === "low" ? "badge-neutral" : "badge-blue";
}
function statusLabel(s: string) {
  return s === "not_provided" ? "Not provided" : s === "original" ? "Original held" : "Copy held";
}

export function EvidencePage() {
  const { caseId, evidence, issues, loading, error, refresh } = useCase();
  const toast = useToast();

  const [filter, setFilter] = useState("all");
  const [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [itemType, setItemType] = useState("document");
  const [importance, setImportance] = useState("medium");
  const [verification, setVerification] = useState("unverified");
  const [source, setSource] = useState("");
  const [date, setDate] = useState("");
  const [status, setStatus] = useState("copy");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function addItem(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setFormError("A title is required."); return; }
    setSaving(true); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/evidence`, {
        title, description, item_type: itemType, importance, verification,
        source, date, status, notes,
      });
      setTitle(""); setDescription(""); setSource(""); setDate(""); setNotes("");
      setItemType("document"); setImportance("medium"); setVerification("unverified"); setStatus("copy");
      setShowAdd(false);
      toast.success("Evidence item added.");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the item");
    } finally { setSaving(false); }
  }

  async function remove(id: number) {
    if (!window.confirm("Remove this evidence item?")) return;
    await api.del(`/cases/${caseId}/evidence/${id}`);
    toast.info("Evidence item removed.");
    refresh();
  }

  async function setVerificationStatus(item: EvidenceItem, value: string) {
    await api.patch(`/cases/${caseId}/evidence/${item.id}`, { verification: value });
    refresh();
  }
  async function setImportanceValue(item: EvidenceItem, value: string) {
    await api.patch(`/cases/${caseId}/evidence/${item.id}`, { importance: value });
    refresh();
  }
  async function linkIssue(item: EvidenceItem, issueId: string) {
    if (!issueId) return;
    const ids = (item.related_issues ?? []).map((i) => i.id);
    if (!ids.includes(Number(issueId))) ids.push(Number(issueId));
    await api.patch(`/cases/${caseId}/evidence/${item.id}`, { related_issue_ids: ids });
    toast.success("Evidence linked to the issue.");
    refresh();
  }
  async function unlinkIssue(item: EvidenceItem, issueId: number) {
    const ids = (item.related_issues ?? []).filter((i) => i.id !== issueId).map((i) => i.id);
    await api.patch(`/cases/${caseId}/evidence/${item.id}`, { related_issue_ids: ids });
    toast.info("Link removed.");
    refresh();
  }

  const visible = filter === "all" ? evidence : evidence.filter((i) => i.item_type === filter);
  const counts: Record<string, number> = {};
  evidence.forEach((i) => { counts[i.item_type] = (counts[i.item_type] ?? 0) + 1; });
  const verCounts = { verified: 0, unverified: 0, disputed: 0 };
  evidence.forEach((i) => { const v = i.verification || "unverified"; if (v in verCounts) verCounts[v as keyof typeof verCounts]++; });
  const linked = evidence.filter((i) => (i.related_issues?.length ?? 0) > 0).length;

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Evidence organizer</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5, maxWidth: 700 }}>
          What supports your case, how important it is, whether it is verified, and which issue it
          supports. Link each piece of evidence to the issues it bears on.
        </p>
      </div>

      {/* Summary strip */}
      {evidence.length > 0 && (
        <div className="flex" style={{ gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          <Badge tone="green"><i className="bi bi-check2-circle" /> {verCounts.verified} verified</Badge>
          <Badge tone="amber"><i className="bi bi-exclamation-circle" /> {verCounts.unverified} unverified</Badge>
          <Badge tone="red"><i className="bi bi-shield-exclamation" /> {verCounts.disputed} disputed</Badge>
          <span className="badge badge-neutral"><i className="bi bi-link-45deg" /> {linked} linked to issues</span>
        </div>
      )}

      {/* Add + filters */}
      <div className="card mb-3">
        <div className="flex-between">
          <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
            <button className={`btn btn-sm ${filter === "all" ? "btn-primary" : "btn-ghost"}`} onClick={() => setFilter("all")}>
              All ({evidence.length})
            </button>
            {TYPES.map(([v, l]) => (
              <button key={v} className={`btn btn-sm ${filter === v ? "btn-primary" : "btn-ghost"}`} onClick={() => setFilter(v)}>
                {l} ({counts[v] ?? 0})
              </button>
            ))}
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => setShowAdd((s) => !s)}>
            <i className="bi bi-plus-lg" /> Add item
          </button>
        </div>

        {showAdd && (
          <form onSubmit={addItem} style={{ borderTop: "1px dashed var(--line)", marginTop: 12, paddingTop: 14 }}>
            <div className="form-row cols-2">
              <div>
                <label className="form-label">Name *</label>
                <input className="form-control" value={title} onChange={(e) => setTitle(e.target.value)}
                       placeholder="e.g. Email confirming move-out date" />
              </div>
              <div>
                <label className="form-label">Date</label>
                <input className="form-control" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              </div>
            </div>
            <div className="form-row cols-3">
              <div>
                <label className="form-label">Type</label>
                <select className="form-select" value={itemType} onChange={(e) => setItemType(e.target.value)}>
                  {TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
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
              <div>
                <label className="form-label">Authenticity</label>
                <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="original">Original</option>
                  <option value="copy">Copy</option>
                  <option value="not_provided">Not provided</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="form-label">Description</label>
                <textarea className="form-control" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
              </div>
            </div>
            <div className="form-row cols-2">
              <div>
                <label className="form-label">Source</label>
                <input className="form-control" value={source} onChange={(e) => setSource(e.target.value)}
                       placeholder="Where it came from" />
              </div>
              <div>
                <label className="form-label">Notes</label>
                <input className="form-control" value={notes} onChange={(e) => setNotes(e.target.value)}
                       placeholder="Chain of custody, condition, context…" />
              </div>
            </div>
            {formError && <div className="alert-box error">{formError}</div>}
            <button className="btn btn-primary" disabled={saving}>
              {saving ? "Adding…" : <><i className="bi bi-plus-lg" /> Add item</>}
            </button>
          </form>
        )}
      </div>

      {loading && <div className="card"><Loading label="Loading evidence…" /></div>}
      {error && <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>}
      {!loading && !error && evidence.length === 0 && (
        <div className="card">
          <EmptyState icon="bi-collection" title="No evidence recorded">
            Add the items that support your case — key facts extracted from document analyses appear
            here automatically.
          </EmptyState>
        </div>
      )}

      {!loading && !error && visible.length === 0 && evidence.length > 0 && (
        <div className="card">
          <EmptyState icon="bi-funnel" title="Nothing in this type">
            No {filter} items — switch filters or add one.
          </EmptyState>
        </div>
      )}

      {!loading && !error && visible.length > 0 && (
        <div className="evidence-board">
          {visible.map((item) => (
            <EvidenceCard key={item.id} item={item} issues={issues}
                          onVerify={(v) => void setVerificationStatus(item, v)}
                          onImportance={(v) => void setImportanceValue(item, v)}
                          onLink={(id) => void linkIssue(item, id)}
                          onUnlink={(id) => void unlinkIssue(item, id)}
                          onDelete={() => void remove(item.id)} />
          ))}
        </div>
      )}
    </div>
  );
}

function EvidenceCard({ item, issues, onVerify, onImportance, onLink, onUnlink, onDelete }: {
  item: EvidenceItem;
  issues: LegalIssue[];
  onVerify: (v: string) => void;
  onImportance: (v: string) => void;
  onLink: (issueId: string) => void;
  onUnlink: (issueId: number) => void;
  onDelete: () => void;
}) {
  const related = item.related_issues ?? [];
  const linkedIds = new Set(related.map((i) => i.id));
  const available = issues.filter((i) => !linkedIds.has(i.id));
  const verification = item.verification || "unverified";
  const importance = item.importance || "medium";

  return (
    <div className="evidence-card">
      <div className="ev-head">
        <div className={`ev-icon t-${item.item_type}`}>
          <i className={`bi ${iconFor(item.item_type)}`} />
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="ev-title">{item.title}</div>
          {item.date && <div className="ev-date">{item.date}</div>}
        </div>
        <button className="btn btn-danger-ghost btn-sm" onClick={onDelete} title="Remove item">
          <i className="bi bi-trash" />
        </button>
      </div>

      {item.description && <div className="ev-desc">{item.description}</div>}
      {item.source && <div className="ev-date"><i className="bi bi-geo-alt" style={{ marginRight: 4 }} />{item.source}</div>}

      <div className="ev-meta">
        <ProvenanceBadge source={item.provenance} />
        <span className="badge badge-neutral">{typeLabel(item.item_type)}</span>
        <Badge tone={item.status}>{statusLabel(item.status)}</Badge>
      </div>

      <div className="ev-footer">
        <div className="flex" style={{ gap: 6, alignItems: "center" }}>
          <select className="form-select mini" value={importance} onChange={(e) => onImportance(e.target.value)} title="Importance">
            <option value="high">High importance</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div className="seg">
          {VERIFY.map(([v, l]) => (
            <button key={v} className={verification === v ? (v === "verified" ? "on-green" : v === "disputed" ? "on" : "on") : ""}
                    onClick={() => verification !== v && onVerify(v)} title={v === "verified" ? "You hold/verified this item" : v === "disputed" ? "Authenticity disputed" : "Not yet verified"}>
              {l}
            </button>
          ))}
        </div>
      </div>

      <div>
        {related.length > 0 && (
          <div className="ev-chips" style={{ marginBottom: 6 }}>
            {related.map((iss) => (
              <span key={iss.id} className="issue-chip">
                <i className="bi bi-link-45deg" /> {iss.title}
                <span className="x" onClick={() => onUnlink(iss.id)} title="Unlink">&times;</span>
              </span>
            ))}
          </div>
        )}
        {available.length > 0 && (
          <div className="ev-select-row">
            <select className="form-select mini" value="" onChange={(e) => { onLink(e.target.value); e.target.value = ""; }}>
              <option value="">+ Link to an issue…</option>
              {available.map((i) => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          </div>
        )}
        {issues.length === 0 && <div className="ev-date">Record issues first to link evidence.</div>}
      </div>
    </div>
  );
}
