import { useState } from "react";
import { api } from "../../services/api";
import type { RiskAssessment, RiskDimension } from "../../types";
import { useCase } from "../../context/CaseContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { EmptyState, ErrorState, Loading } from "../../components/ui";

const LEVEL_COLORS: Record<string, string> = {
  low: "#2e9e5b",
  medium: "#d98e1f",
  high: "#d64541",
  critical: "#a6265f",
};

const LEVEL_TONES: Record<string, string> = {
  low: "green",
  medium: "amber",
  high: "red",
  critical: "violet",
};

function levelColor(level: string) {
  return LEVEL_COLORS[level] ?? LEVEL_COLORS.medium;
}

const DIMENSION_ORDER = [
  "legal", "evidence", "deadline", "financial",
  "negotiation", "procedural", "information_gap",
];

function orderDimensions(dimensions: RiskDimension[]): RiskDimension[] {
  return [...dimensions].sort(
    (a, b) => DIMENSION_ORDER.indexOf(a.key) - DIMENSION_ORDER.indexOf(b.key),
  );
}

/** Inline SVG radar of the seven risk dimensions. */
function RiskRadar({ dimensions }: { dimensions: RiskDimension[] }) {
  const size = 340;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 118;
  const n = dimensions.length;
  const labels = orderDimensions(dimensions);
  const points = (value: number) =>
    labels
      .map((d, i) => {
        const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        const r = (Math.max(0, Math.min(100, value)) / 100) * maxR;
        return `${(cx + r * Math.cos(angle)).toFixed(1)},${(cy + r * Math.sin(angle)).toFixed(1)}`;
      })
      .join(" ");

  const axis = (i: number) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    return {
      x: cx + maxR * Math.cos(angle),
      y: cy + maxR * Math.sin(angle),
    };
  };

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="risk-radar" role="img"
         aria-label="Risk radar chart of seven dimensions">
      {[25, 50, 75, 100].map((v) => {
        const r = (v / 100) * maxR;
        return <polygon key={v} points={points(v)} fill="none" stroke="var(--line)" strokeWidth={1} />;
      })}
      {labels.map((_, i) => {
        const p = axis(i);
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="var(--line)" strokeWidth={1} />;
      })}
      <polygon
        points={points(100)}
        fill={levelColor("medium")}
        fillOpacity={0.04}
        stroke={levelColor("medium")}
        strokeWidth={1}
        strokeDasharray="3 3"
        className="risk-radar-boundary"
      />
      <polygon
        points={points(Math.max(...labels.map((d) => d.score), 5))}
        fill="var(--brand-600)"
        fillOpacity={0.18}
        stroke="var(--brand-600)"
        strokeWidth={2}
        strokeLinejoin="round"
      />
      {labels.map((d, i) => {
        const p = axis(i);
        const angle = -Math.PI / 2 + (i * 2 * Math.PI) / n;
        const lx = cx + (maxR + 24) * Math.cos(angle);
        const ly = cy + (maxR + 24) * Math.sin(angle);
        const score = Math.max(0, Math.min(100, d.score));
        const sx = cx + (score / 100) * maxR * Math.cos(angle);
        const sy = cy + (score / 100) * maxR * Math.sin(angle);
        return (
          <g key={d.key}>
            <circle cx={sx} cy={sy} r={4} fill={levelColor(d.level)} />
            <text x={lx} y={ly} textAnchor={Math.abs(Math.cos(angle)) < 0.3 ? "middle" : (lx > cx ? "start" : "end")}
                  dominantBaseline="middle" className="risk-radar-label">
              {d.label.replace(" Risk", "")}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function ScoreBar({ score, level }: { score: number; level: string }) {
  return (
    <div className="score-bar">
      <div className="score-bar-fill" style={{ width: `${Math.max(2, Math.min(100, score))}%`, background: levelColor(level) }} />
    </div>
  );
}

function DimensionCard({ d }: { d: RiskDimension }) {
  const tone = LEVEL_TONES[d.level] ?? "neutral";
  return (
    <div className="card dim-card">
      <div className="flex-between" style={{ alignItems: "flex-start" }}>
        <div>
          <div className="dim-card-title">{d.label}</div>
          <div className="dim-card-score">
            {d.score}<span className="text-faint">/100</span>
          </div>
        </div>
        <span className={`badge badge-${tone}`}>{d.level.toUpperCase()}</span>
      </div>
      <ScoreBar score={d.score} level={d.level} />
      <div className="dim-reason">
        <i className="bi bi-question-circle" /> {d.reason}
      </div>
      <div className="dim-grid">
        <div>
          <div className="dim-head">
            <i className="bi bi-arrow-up-circle" style={{ color: "var(--red)" }} /> Supporting factors
          </div>
          {(d.supporting_factors ?? []).length > 0 ? (
            <ul className="dim-list">
              {d.supporting_factors!.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          ) : (
            <div className="text-faint" style={{ fontSize: 12.5 }}>None recorded</div>
          )}
        </div>
        <div>
          <div className="dim-head">
            <i className="bi bi-arrow-down-circle" style={{ color: "var(--green)" }} /> Mitigating factors
          </div>
          {(d.mitigating_factors ?? []).length > 0 ? (
            <ul className="dim-list">
              {d.mitigating_factors!.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          ) : (
            <div className="text-faint" style={{ fontSize: 12.5 }}>None recorded</div>
          )}
        </div>
      </div>
      {d.recommended_action && (
        <div className="dim-action">
          <i className="bi bi-lightbulb" /> <b>Recommended:</b> {d.recommended_action}
        </div>
      )}
    </div>
  );
}

export function RisksPage() {
  const { caseId, risks, loading, error, refresh, riskAssessment, setRiskAssessment } = useCase();
  const [running, setRunning] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Manual risk entry (Phase-1/2 risk list, preserved).
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [likelihood, setLikelihood] = useState("medium");
  const [impact, setImpact] = useState("medium");
  const [mitigation, setMitigation] = useState("");
  const [saving, setSaving] = useState(false);

  async function runAnalysis() {
    setRunning(true);
    setFormError(null);
    try {
      const res = await api.post<{ assessment: RiskAssessment }>(`/cases/${caseId}/risk-analysis`);
      setRiskAssessment(res.assessment);
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Risk analysis failed");
    } finally { setRunning(false); }
  }

  async function addRisk(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setFormError("A risk title is required."); return; }
    setSaving(true); setFormError(null);
    try {
      await api.post(`/cases/${caseId}/risks`, { title, description, likelihood, impact, mitigation });
      setTitle(""); setDescription(""); setLikelihood("medium"); setImpact("medium"); setMitigation("");
      refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not add the risk");
    } finally { setSaving(false); }
  }

  async function remove(riskId: number) {
    if (!window.confirm("Remove this risk?")) return;
    await api.del(`/cases/${caseId}/risks/${riskId}`);
    refresh();
  }

  const assessment = riskAssessment;
  const previous = assessment?.previous;
  const prevDims = orderDimensions(previous?.dimensions ?? []);
  const changes: { key: string; label: string; previous_level: string; current_level: string; direction: string }[] = [];
  if (assessment && previous && prevDims.length > 0) {
    const cur = new Map(orderDimensions(assessment.dimensions).map((d) => [d.key, d]));
    for (const p of prevDims) {
      const c = cur.get(p.key);
      if (c && c.level !== p.level) {
        changes.push({ key: p.key, label: p.label, previous_level: p.level, current_level: c.level, direction: "worsened" });
      }
    }
    const order = { low: 0, medium: 1, high: 2, critical: 3 };
    const pl = previous.overall_level ?? "";
    const cl = assessment.overall_level;
    if (pl && cl && pl !== cl) {
      changes.unshift({
        key: "overall", label: "Overall risk",
        previous_level: pl, current_level: cl,
        direction: (order[cl as keyof typeof order] ?? 2) < (order[pl as keyof typeof order] ?? 2) ? "improved" : "worsened",
      });
    }
  }

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Risk analysis</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5 }}>
          Seven explainable risk dimensions, scored from the actual case record — issues,
          evidence verification, deadlines, gaps and preparation. Scores measure the
          strength of the record, never legal probabilities.
        </p>
      </div>

      {formError && <div className="alert-box error mb-3">{formError}</div>}

      {loading && <div className="card"><Loading label="Loading risk analysis…" /></div>}
      {error && <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>}

      {!loading && !error && !assessment && (
        <div className="card">
          <EmptyState icon="bi-shield-exclamation" title="No risk analysis yet">
            Run the risk engine to get an explainable seven-dimension assessment grounded in this
            case's issues, evidence, deadlines and gaps.
          </EmptyState>
          <div style={{ textAlign: "center" }}>
            <button className="btn btn-primary" onClick={runAnalysis} disabled={running}>
              <i className="bi bi-stars" /> {running ? "Analyzing…" : "Run risk analysis"}
            </button>
          </div>
        </div>
      )}

      {assessment && (
        <>
          <div className="card mb-3">
            <div className="flex-between mb-2">
              <h3 className="card-title">Overall risk</h3>
              <button className="btn btn-outline btn-sm" onClick={runAnalysis} disabled={running}>
                <i className="bi bi-arrow-repeat" /> {running ? "Analyzing…" : "Re-run risk analysis"}
              </button>
            </div>
            <div className="risk-overall">
              <div className="risk-gauge">
                <div className="risk-gauge-ring" style={{ borderColor: levelColor(assessment.overall_level) }}>
                  <div className="risk-gauge-score">{assessment.overall_score}</div>
                  <div className="risk-gauge-label">/ 100</div>
                </div>
                <div className="mt-1" style={{ textAlign: "center" }}>
                  <span className={`badge badge-${LEVEL_TONES[assessment.overall_level] ?? "neutral"}`}>
                    {assessment.overall_level.toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="risk-overall-body">
                <p className="risk-summary">{assessment.summary}</p>
                <div className="risk-radar-row">
                  <RiskRadar dimensions={assessment.dimensions} />
                  <div className="risk-radar-legend">
                    <div className="overline mb-1">Risk dimensions</div>
                    {orderDimensions(assessment.dimensions).map((d) => (
                      <div key={d.key} className="legend-row">
                        <span className="legend-dot" style={{ background: levelColor(d.level) }} />
                        <span className="legend-name">{d.label}</span>
                        <span className="legend-score">{d.score}</span>
                        <span className={`badge badge-${LEVEL_TONES[d.level] ?? "neutral"} badge-xs`}>{d.level}</span>
                      </div>
                    ))}
                  </div>
                </div>
                {assessment.note && (
                  <div className="disclaimer disclaimer-info" style={{ fontSize: 12, marginTop: 8 }}>
                    <i className="bi bi-info-circle" /> {assessment.note}
                  </div>
                )}
                <div className="disclaimer disclaimer-warn" style={{ fontSize: 12, marginTop: 6 }}>
                  <i className="bi bi-exclamation-triangle" /> These scores assess how complete and
                  strong the case record is — they are not predictions and not legal probabilities.
                </div>
              </div>
            </div>
          </div>

          {changes.length > 0 && (
            <div className="card mb-3">
              <div className="flex-between mb-2">
                <h3 className="card-title">What changed</h3>
                {previous?.overall_level && (
                  <span className="text-soft" style={{ fontSize: 12.5 }}>
                    Previous: <b>{previous.overall_level.toUpperCase()}</b>
                    {" "}→ Current: <b>{assessment.overall_level.toUpperCase()}</b>
                  </span>
                )}
              </div>
              <div className="change-list">
                {changes.map((c) => (
                  <div key={c.key} className={`change-item ${c.direction}`}>
                    <i className={`bi ${c.direction === "improved" ? "bi-arrow-down-right" : "bi-arrow-up-right"}`} />
                    <span className="change-label">{c.label}</span>
                    <span className="badge badge-neutral badge-xs">{c.previous_level}</span>
                    <span className="text-faint">→</span>
                    <span className={`badge badge-${LEVEL_TONES[c.current_level] ?? "neutral"} badge-xs`}>{c.current_level}</span>
                    <span className="change-dir">{c.direction === "improved" ? "Improved" : "Worsened"}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mb-3">
            <div className="overline mb-2">Dimension breakdown</div>
            <div className="dim-grid-cards">
              {orderDimensions(assessment.dimensions).map((d) => <DimensionCard key={d.key} d={d} />)}
            </div>
          </div>
        </>
      )}

      <div className="card">
        <div className="flex-between mb-2">
          <h3 className="card-title">Individual risks</h3>
        </div>
        <form onSubmit={addRisk} className="mb-3">
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Risk title *</label>
              <input className="form-control" value={title} onChange={(e) => setTitle(e.target.value)}
                     placeholder="e.g. Deposit deadline may have been missed" />
            </div>
            <div className="form-row cols-2" style={{ gridTemplateColumns: "1fr 1fr", margin: 0 }}>
              <div>
                <label className="form-label">Likelihood</label>
                <select className="form-select" value={likelihood} onChange={(e) => setLikelihood(e.target.value)}>
                  <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                </select>
              </div>
              <div>
                <label className="form-label">Impact</label>
                <select className="form-select" value={impact} onChange={(e) => setImpact(e.target.value)}>
                  <option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>
          <div className="form-row cols-2">
            <div>
              <label className="form-label">Description</label>
              <textarea className="form-control" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div>
              <label className="form-label">Mitigation</label>
              <textarea className="form-control" rows={2} value={mitigation} onChange={(e) => setMitigation(e.target.value)}
                        placeholder="What reduces this risk?" />
            </div>
          </div>
          <button className="btn btn-primary" disabled={saving}>
            {saving ? "Adding…" : <><i className="bi bi-plus-lg" /> Add risk</>}
          </button>
        </form>
        {risks.length === 0 ? (
          <EmptyState icon="bi-shield-exclamation" title="No individual risks recorded">
            Individual risks complement the engine assessment above. Add one manually, or run the
            AI risk assessment for issue-by-issue risks.
          </EmptyState>
        ) : (
          <div className="list">
            {risks.map((risk) => (
              <div key={risk.id} className="list-item">
                <div className="li-main">
                  <div className="li-title">{risk.title}</div>
                  {risk.description && <div className="li-desc">{risk.description}</div>}
                  <div className="li-meta">
                    <span className={`badge badge-${risk.overall_risk === "high" ? "red" : risk.overall_risk === "low" ? "green" : "amber"}`}>{risk.overall_risk}</span>
                    <span className="badge badge-neutral">likelihood: {risk.likelihood}</span>
                    <span className="badge badge-neutral">impact: {risk.impact}</span>
                  </div>
                  {risk.mitigation && (
                    <div className="li-desc mt-1" style={{ color: "var(--green)" }}>
                      <i className="bi bi-shield-check" /> {risk.mitigation}
                    </div>
                  )}
                </div>
                <button className="btn btn-danger-ghost btn-sm" onClick={() => remove(risk.id)}>
                  <i className="bi bi-trash" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3"><LegalDisclaimer /></div>
    </div>
  );
}