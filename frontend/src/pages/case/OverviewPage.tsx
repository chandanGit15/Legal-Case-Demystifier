import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../services/api";
import type { AiResult, LegalIssue, TimelineEvent } from "../../types";
import { useCase } from "../../context/CaseContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { ProvenanceBadge } from "../../components/ProvenanceBadge";
import { CaseStatusBadge, EmptyState, RiskChip } from "../../components/ui";
import { caseStatusMeta } from "../../utils/constants";
import { formatDate } from "../../utils/format";

interface OverviewAnalysis extends AiResult {
  summary?: string;
  key_facts?: { text: string; source: string; label?: string }[];
  possible_issues?: { title: string; category?: string; confidence?: string; basis?: string }[];
  information_gaps?: { question: string; why_it_matters?: string }[];
  suggested_actions?: string[];
  risk_notes?: string[];
  requires_verification?: string[];
}

export function OverviewPage() {
  const { caseData, issues, timeline, risks, gaps, actions, refreshing } = useCase();
  const [analysis, setAnalysis] = useState<OverviewAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runAnalysis() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<OverviewAnalysis>(`/cases/${caseData!.id}/overview/analyze`, {});
      setAnalysis(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  if (!caseData) return null;
  const counts = caseData.counts;
  const status = caseStatusMeta(caseData.status);
  const jurisdiction = caseData.jurisdiction
    || [caseData.country, caseData.state].filter(Boolean).join(", ");

  return (
    <div>
      <div className="flex-between mb-3" style={{ alignItems: "flex-start" }}>
        <div>
          <div className="overline mb-1">Case overview</div>
          <p className="text-soft" style={{ margin: 0, fontSize: 13.5, maxWidth: 660 }}>
            Everything on this page — and every tab in this workspace — is scoped to case
            #{caseData.id} and reads from one shared case context.
          </p>
        </div>
        <button className="btn btn-primary" onClick={runAnalysis} disabled={busy || refreshing}>
          <i className="bi bi-stars" /> {busy ? "Analyzing…" : analysis ? "Re-run AI overview" : "Run AI overview"}
        </button>
      </div>

      {/* KPI strip */}
      <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))" }}>
        <Stat icon="bi-calendar3" label="Timeline" value={counts?.timeline_events ?? timeline.length} to="timeline" />
        <Stat icon="bi-file-earmark-text" label="Documents" value={counts?.documents ?? 0} to="documents" />
        <Stat icon="bi-exclamation-circle" label="Legal issues" value={counts?.issues ?? issues.length} to="issues" />
        <Stat icon="bi-shield-exclamation" label="Risks" value={counts?.risks ?? risks.length} to="risks" />
        <Stat icon="bi-diagram-3" label="Scenarios" value={counts?.scenarios ?? 0} to="scenarios" />
        <Stat icon="bi-collection" label="Evidence" value={counts?.evidence_items ?? 0} to="evidence" />
        <Stat icon="bi-list-check" label="Open actions" value={counts?.open_actions ?? 0} to="action-plan" />
        <Stat icon="bi-alarm" label="Deadlines" value={counts?.upcoming_deadlines ?? 0} to="action-plan" />
      </div>

      {/* Case summary + parties */}
      <div className="card-grid cols-2 mb-3">
        <div className="card">
          <div className="flex-between mb-2">
            <h3 className="card-title">Case summary</h3>
            <div className="flex" style={{ gap: 8 }}>
              <CaseStatusBadge status={caseData.status} />
            </div>
          </div>
          {caseData.description ? (
            <p className="text-soft" style={{ whiteSpace: "pre-line", margin: 0, fontSize: 13.5, lineHeight: 1.7 }}>
              {caseData.description}
            </p>
          ) : (
            <EmptyState icon="bi-pencil-square" title="No description yet">
              Edit the case to add the situation in your own words.
            </EmptyState>
          )}
          <div className="li-meta mt-2" style={{ marginTop: 12 }}>
            {caseData.case_type && <span className="badge badge-neutral"><i className="bi bi-tag" /> {caseData.case_type}</span>}
            <span className="badge badge-neutral"><i className="bi bi-flag" /> {status.label}</span>
            {caseData.stage && <span className="badge badge-neutral">{caseData.stage}</span>}
            {caseData.is_demo && <span className="badge badge-demo"><i className="bi bi-stars" /> Demo case</span>}
          </div>
        </div>

        <div className="card">
          <h3 className="card-title">Parties</h3>
          {caseData.parties ? (
            <>
              <p className="text-soft" style={{ margin: 0, fontSize: 13.5, lineHeight: 1.7, whiteSpace: "pre-line" }}>
                {caseData.parties}
              </p>
              <div className="form-hint" style={{ marginTop: 8 }}>
                Record the parties in the case edit dialog — you can note roles (e.g. tenant / landlord).
              </div>
            </>
          ) : (
            <EmptyState icon="bi-people" title="Parties not recorded">
              Who is involved? Edit the case and add the parties to keep every analysis anchored to the right people.
            </EmptyState>
          )}
          <div className="li-meta mt-2" style={{ marginTop: 12 }}>
            {jurisdiction
              ? <span className="badge badge-neutral"><i className="bi bi-geo-alt" /> {jurisdiction}</span>
              : <span className="badge badge-neutral">Jurisdiction not set</span>}
            <span className="badge badge-neutral"><i className="bi bi-clock-history" /> created {formatDate(caseData.created_at)}</span>
          </div>
        </div>
      </div>

      {error && <div className="alert-box error">{error}</div>}

      {/* AI case brief */}
      {analysis ? (
        <div className="card mb-3">
          <div className="flex-between mb-2">
            <h3 className="card-title">AI case brief</h3>
            <AiModeBadge mode={analysis.mode} />
          </div>
          {analysis.note && <div className="disclaimer disclaimer-info mb-2"><i className="bi bi-info-circle" />{analysis.note}</div>}
          {analysis.summary && (
            <p className="text-soft" style={{ whiteSpace: "pre-line", margin: "0 0 14px", fontSize: 13.5, lineHeight: 1.7 }}>
              <b>Summary:</b> {analysis.summary}
            </p>
          )}
          {analysis.suggested_actions && analysis.suggested_actions.length > 0 && (
            <div className="mb-2">
              <div className="overline mb-1">Suggested next steps</div>
              <div className="flex" style={{ gap: 8, flexWrap: "wrap" }}>
                {analysis.suggested_actions.map((a, i) => (
                  <span key={i} className="badge badge-neutral" style={{ padding: "6px 10px" }}>{a}</span>
                ))}
              </div>
            </div>
          )}
          <div className="brief-grid">
            <BriefSection icon="bi-file-earmark-check" title="Facts" tone="green">
              {(analysis.key_facts ?? []).map((f, i) => (
                <BriefFact key={i} text={f.text} source={f.source} label={f.label} />
              ))}
              {(!analysis.key_facts || analysis.key_facts.length === 0) && <BriefEmpty>No extracted facts yet — add a document or describe the situation.</BriefEmpty>}
            </BriefSection>

            <BriefSection icon="bi-lightbulb" title="AI interpretation" tone="violet">
              {(analysis.risk_notes ?? []).map((r, i) => (
                <div key={i} className="brief-line"><i className="bi bi-asterisk" />{r}</div>
              ))}
              {(!analysis.risk_notes || analysis.risk_notes.length === 0) && <BriefEmpty>Interpretive notes will appear here once there is enough material.</BriefEmpty>}
            </BriefSection>

            <BriefSection icon="bi-question-circle" title="Unknown information" tone="amber">
              {(analysis.information_gaps ?? []).map((g, i) => (
                <div key={i} className="brief-line">
                  <ProvenanceBadge source="gap" />
                  <span>{g.question}</span>
                  {g.why_it_matters && <span className="text-faint" style={{ display: "block", marginLeft: 70 }}>{g.why_it_matters}</span>}
                </div>
              ))}
              {(analysis.requires_verification ?? []).map((r, i) => (
                <div key={`v${i}`} className="brief-line">
                  <ProvenanceBadge source="verify" />
                  <span>{r}</span>
                </div>
              ))}
              {(!analysis.information_gaps || analysis.information_gaps.length === 0)
                && (!analysis.requires_verification || analysis.requires_verification.length === 0)
                && <BriefEmpty>No open questions for the moment.</BriefEmpty>}
            </BriefSection>

            <BriefSection icon="bi-exclamation-diamond" title="Potential issues" tone="red">
              {(analysis.possible_issues ?? []).map((i, idx) => (
                <div key={idx} className="brief-line">
                  <ProvenanceBadge source="ai" />
                  <span><b>{i.title}</b></span>
                  {i.basis && <span className="text-faint" style={{ display: "block", marginLeft: 70 }}>{i.basis}</span>}
                  {i.confidence && <span className="text-faint" style={{ display: "block", marginLeft: 70 }}>confidence: {i.confidence}</span>}
                </div>
              ))}
              {(!analysis.possible_issues || analysis.possible_issues.length === 0) && <BriefEmpty>No potential issues identified yet.</BriefEmpty>}
            </BriefSection>
          </div>
        </div>
      ) : (
        <div className="card mb-3">
          <EmptyState icon="bi-stars" title="Structured AI case brief">
            Run the AI overview to build a brief that separates <b>facts</b>, <b>AI interpretation</b>,
            <b> unknown information</b> and <b>potential issues</b> — every claim carries a provenance label.
          </EmptyState>
        </div>
      )}

      {/* Key issues + important dates */}
      <div className="card-grid cols-2 mb-3">
        <div className="card">
          <SectionHead title={`Key issues (${issues.length})`} to="issues" />
          {issues.length === 0 ? (
            <p className="text-faint" style={{ fontSize: 13.5, margin: 0 }}>
              No issues recorded yet. Record them on the <Link to={`/cases/${caseData.id}/issues`}>Legal Issues</Link> tab or run AI detection.
            </p>
          ) : (
            <div className="list">
              {issues.slice(0, 5).map((issue: LegalIssue) => (
                <div key={issue.id} className="list-item" style={{ padding: "10px 2px" }}>
                  <div className="li-main">
                    <div className="li-title" style={{ fontSize: 13.5 }}>{issue.title}</div>
                    <div className="li-meta">
                      <ProvenanceBadge source={issue.provenance} />
                      <span className="badge badge-neutral">confidence: {issue.confidence}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <SectionHead title="Important dates" to="timeline" />
          {timeline.length === 0 ? (
            <p className="text-faint" style={{ fontSize: 13.5, margin: 0 }}>
              No dates recorded yet. Add them on the <Link to={`/cases/${caseData.id}/timeline`}>Timeline</Link> tab.
            </p>
          ) : (
            <div className="list">
              {[...timeline]
                .sort((a, b) => (a.date < b.date ? 1 : -1))
                .slice(0, 5)
                .map((ev: TimelineEvent) => (
                <div key={ev.id} className="list-item" style={{ padding: "8px 2px", alignItems: "center" }}>
                  <span className="mono" style={{ fontSize: 12, color: "var(--ink-faint)", minWidth: 84 }}>{ev.date}</span>
                  <div className="li-main">
                    <div className="li-title" style={{ fontSize: 13.5 }}>{ev.title}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Risks + missing information */}
      <div className="card-grid cols-2 mb-3">
        <div className="card">
          <SectionHead title={`Potential risks (${risks.length})`} to="risks" />
          {risks.length === 0 ? (
            <p className="text-faint" style={{ fontSize: 13.5, margin: 0 }}>
              No risks assessed yet. Use the <Link to={`/cases/${caseData.id}/risks`}>Risk Analysis</Link> tab.
            </p>
          ) : (
            <div className="list">
              {risks.slice(0, 5).map((r) => (
                <div key={r.id} className="list-item" style={{ padding: "10px 2px" }}>
                  <div className="li-main">
                    <div className="li-title" style={{ fontSize: 13.5 }}>{r.title}</div>
                    <div className="li-meta">
                      <RiskChip level={r.overall_risk} />
                      <ProvenanceBadge source={r.provenance} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <SectionHead title={`Missing information (${gaps.length})`} to="issues" />
          {gaps.length === 0 ? (
            <p className="text-faint" style={{ fontSize: 13.5, margin: 0 }}>
              No open information gaps — or none detected yet. Run the AI overview to surface what is still unknown.
            </p>
          ) : (
            <div className="list">
              {gaps.slice(0, 5).map((g) => (
                <div key={g.id} className="list-item" style={{ padding: "10px 2px" }}>
                  <div className="li-main">
                    <div className="li-title" style={{ fontSize: 13.5 }}>{g.question}</div>
                    {g.priority && <div className="li-meta"><span className="badge badge-neutral">priority: {g.priority}</span></div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recommended next steps */}
      <div className="card mb-3">
        <SectionHead title="Recommended next steps" to="action-plan" />
        {actions.length === 0 ? (
          <p className="text-faint" style={{ fontSize: 13.5, margin: 0 }}>
            Nothing planned yet. Open the <Link to={`/cases/${caseData.id}/action-plan`}>Action Plan</Link> tab to add steps and deadlines.
          </p>
        ) : (
          <div className="list">
            {actions.slice(0, 6).map((a) => (
              <div key={a.id} className="list-item" style={{ padding: "10px 2px", alignItems: "center" }}>
                <i className={`bi ${a.status === "done" ? "bi-check-circle-fill" : "bi-circle"}`}
                   style={{ color: a.status === "done" ? "var(--green)" : "var(--ink-faint)", fontSize: 15 }} />
                <div className="li-main">
                  <div className="li-title" style={{ fontSize: 13.5 }}>{a.title}</div>
                  {a.category && <div className="li-desc" style={{ fontSize: 12.5 }}>{a.category}</div>}
                </div>
                <div className="li-meta" style={{ marginTop: 0 }}>
                  <span className="badge badge-neutral">{a.priority} priority</span>
                  {a.due_date && <span className="mono" style={{ fontSize: 12 }}>due {a.due_date}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <LegalDisclaimer />
    </div>
  );
}

/* ---- small helpers ------------------------------------------------------- */

function Stat({ icon, label, value, to }: { icon: string; label: string; value: number; to: string }) {
  const { caseData } = useCase();
  if (!caseData) return null;
  return (
    <Link to={`/cases/${caseData.id}/${to}`} className="kpi" style={{ textDecoration: "none", display: "block" }}>
      <div className="flex" style={{ gap: 8, alignItems: "center", marginBottom: 6 }}>
        <i className={`bi ${icon}`} style={{ color: "var(--brand-500)" }} />
        <span className="overline" style={{ fontSize: 10 }}>{label}</span>
      </div>
      <div className="kpi-value" style={{ fontSize: 22 }}>{value}</div>
    </Link>
  );
}

function SectionHead({ title, to }: { title: string; to?: string }) {
  const { caseData } = useCase();
  if (!caseData) return null;
  return (
    <div className="flex-between mb-2">
      <h3 className="card-title">{title}</h3>
      {to && (
        <Link to={`/cases/${caseData.id}/${to}`} className="btn btn-ghost btn-sm">
          View all <i className="bi bi-arrow-right" />
        </Link>
      )}
    </div>
  );
}

const BRIEF_TONE_COLORS: Record<string, string> = {
  green: "var(--green)",
  violet: "var(--violet)",
  amber: "var(--amber)",
  red: "var(--red)",
};

function BriefSection({ icon, title, tone, children }: {
  icon: string; title: string; tone: string; children: React.ReactNode;
}) {
  return (
    <div className="brief-section">
      <div className="brief-head">
        <i className={`bi ${icon}`} style={{ color: BRIEF_TONE_COLORS[tone] ?? "var(--ink-soft)" }} />
        <b>{title}</b>
      </div>
      <div className="brief-body">{children}</div>
    </div>
  );
}

function BriefFact({ text, source, label }: { text: string; source: string; label?: string }) {
  const prov = source === "document" ? "document" : "user";
  const labelText = label ?? (source === "document" ? "FACT EXTRACTED FROM DOCUMENT" : "USER FACT");
  return (
    <div className="brief-line">
      <ProvenanceBadge source={prov} />
      <span>{text}</span>
      <span className="text-faint" style={{ display: "block", marginLeft: 70, fontSize: 11.5, letterSpacing: "0.04em" }}>{labelText}</span>
    </div>
  );
}

function BriefEmpty({ children }: { children: React.ReactNode }) {
  return <p className="text-faint" style={{ fontSize: 12.5, margin: 0 }}>{children}</p>;
}

function AiModeBadge({ mode }: { mode: string }) {
  if (mode === "ai") return <span className="badge badge-green"><i className="bi bi-check-circle" /> Live AI</span>;
  return <span className="badge badge-demo"><i className="bi bi-stars" /> Demo analysis</span>;
}
