import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { CaseSummary, DashboardData, DemoCaseMeta } from "../types";
import { useLanguage } from "../context/LanguageContext";
import { useToast } from "../context/ToastContext";
import { formatDate } from "../utils/format";
import { ErrorState, Loading } from "../components/ui";
import { DemoPickerModal } from "../components/DemoPickerModal";

const LEVEL_TONE: Record<string, string> = { low: "green", medium: "amber", high: "red", critical: "red" };
const KIND_ICON: Record<string, string> = {
  issue: "bi-exclamation-circle", risk: "bi-shield-exclamation", gap: "bi-question-circle",
  analysis: "bi-file-earmark-text", deadline: "bi-alarm", action: "bi-list-check",
};
const KIND_LABEL: Record<string, string> = {
  issue: "New issue", risk: "Risk flag", gap: "Information gap", analysis: "Document analysis",
  deadline: "Deadline", action: "Action",
};

const TYPE_ICON: Record<string, string> = {
  Employment: "bi-person-badge", "Tenant/Landlord": "bi-house-door", Consumer: "bi-cart",
  Contract: "bi-file-earmark-text", Property: "bi-signpost-split", Business: "bi-building",
  Criminal: "bi-shield", Civil: "bi-bank", Financial: "bi-cash-stack", Family: "bi-people",
  "Intellectual Property": "bi-lightbulb",
};

export function DashboardPage() {
  const { t } = useLanguage();
  const toast = useToast();
  const navigate = useNavigate();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [demos, setDemos] = useState<DemoCaseMeta[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.get<DashboardData>("/dashboard/summary")
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load"); });
    api.get<{ demos: DemoCaseMeta[] }>("/demo-catalog")
      .then((d) => { if (!cancelled) setDemos(d.demos); })
      .catch(() => { /* picker optional */ });
    return () => { cancelled = true; };
  }, []);

  if (error) return <div className="page-wide"><ErrorState message={error} onRetry={() => window.location.reload()} /></div>;
  if (!data) return <div className="page-wide"><Loading label="Loading dashboard…" /></div>;

  const a = data.analytics;
  const nav = (path: string) => navigate(path);

  return (
    <div className="page">
      <div className="flex-between mb-3" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h2 className="page-title" style={{ marginBottom: 2 }}>Dashboard</h2>
          <p className="text-faint" style={{ margin: 0, fontSize: 13 }}>
            Your case portfolio at a glance — real numbers from your cases, no placeholders.
          </p>
        </div>
        <div className="flex" style={{ gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setPickerOpen(true)}>
            <i className="bi bi-briefcase" /> Explore demo case
          </button>
          <button className="btn btn-accent btn-sm" onClick={() => nav("/cases?new=1")}>
            <i className="bi bi-plus-lg" /> {t("newCase")}
          </button>
        </div>
      </div>

      {/* KPI row */}
      <div className="dash-kpis mb-3">
        <Kpi icon="bi-briefcase" value={data.kpis.active_cases} label="ACTIVE CASES" sub="Currently in progress" onClick={() => nav("/cases")} />
        <Kpi icon="bi-file-earmark-check" value={data.kpis.documents_analyzed} label="DOCUMENTS ANALYZED" sub="AI-extracted findings" onClick={() => nav("/cases")} />
        <Kpi icon="bi-list-check" value={data.kpis.pending_actions} label="PENDING ACTIONS" sub="Across all cases" onClick={() => nav("/cases")} />
        <Kpi icon="bi-alarm" value={data.kpis.upcoming_deadlines} label="UPCOMING DEADLINES" sub="Soonest first" onClick={() => nav("/cases")} />
      </div>

      {/* Case analytics — real data visualizations */}
      <div className="mb-3">
        <div className="flex-between mb-2" style={{ alignItems: "baseline" }}>
          <h3 className="section-heading" style={{ margin: 0 }}>Case analytics</h3>
          <span className="overline">every figure derives from your case records</span>
        </div>
        <div className="an-grid">
          <AnalyticCard title="Issues detected" icon="bi-exclamation-circle"
                        body={<IssueBlock total={a.issues.total} open={a.issues.open}
                                          byCase={a.issues.by_case} onClick={nav} />} />
          <AnalyticCard title="High-risk areas" icon="bi-shield-exclamation"
                        body={<RiskBlock riskAreas={a.risk_areas} highFactors={a.high_risk_factors} onClick={nav} />} />
          <AnalyticCard title="Evidence coverage" icon="bi-collection"
                        body={<EvidenceBlock ev={a.evidence} onClick={nav} />} />
          <AnalyticCard title="Information gaps" icon="bi-question-circle"
                        body={<GapBlock gaps={a.gaps} onClick={nav} />} />
          <AnalyticCard title="Scenario comparison" icon="bi-diagram-3"
                        body={<ScenarioBlock sc={a.scenarios} onClick={nav} />} />
          <AnalyticCard title="Negotiation readiness" icon="bi-people"
                        body={<NegotiationBlock neg={a.negotiation} onClick={nav} />} />
        </div>
      </div>

      <div className="mb-3">
        <div className="flex-between mb-2" style={{ alignItems: "baseline" }}>
          <h3 className="section-heading" style={{ margin: 0 }}>Recent AI insights</h3>
          <span className="overline">newest AI findings across cases</span>
        </div>
        {data.recent_ai_insights.length === 0 ? (
          <div className="card"><p className="text-faint" style={{ margin: 0 }}>Run analysis (issues, risks, gaps, document intelligence) and the newest AI findings will appear here.</p></div>
        ) : (
          <div className="insights-row">
            {data.recent_ai_insights.slice(0, 4).map((ins, i) => (
              <Link key={i} className="card insight-card" to={`/cases/${ins.case_id}/overview`}>
                <div className="flex-between">
                  <span className="overline"><i className={`bi ${KIND_ICON[ins.kind] ?? "bi-stars"}`} style={{ marginRight: 4 }} />
                    {KIND_LABEL[ins.kind] ?? ins.kind}</span>
                  {ins.kind === "issue" && ins.confidence && <BadgeText text={ins.confidence} />}
                  {ins.kind === "risk" && ins.level && <BadgeText text={ins.level} />}
                  {ins.kind === "gap" && ins.priority && <BadgeText text={ins.priority} />}
                </div>
                <b className="insight-title">{ins.title}</b>
                <span className="text-faint" style={{ fontSize: 11.5 }}>{ins.case_title}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="mb-3">
        <div className="flex-between mb-2" style={{ alignItems: "baseline" }}>
          <h3 className="section-heading" style={{ margin: 0 }}>Recent cases</h3>
          <Link to="/cases" className="link-muted">View all</Link>
        </div>
        {data.recent_cases.length === 0 ? (
          <div className="card"><p className="text-faint" style={{ margin: 0 }}>No cases yet — create your first case to get started.</p></div>
        ) : (
          <div className="case-row">
            {data.recent_cases.map((c: CaseSummary) => (
              <CaseTile key={c.id} c={c} />
            ))}
          </div>
        )}
      </div>

      <div className="dash-cols">
        <div>
          <h3 className="section-heading">Action required</h3>
          {data.action_required.length === 0 ? (
            <div className="card"><p className="text-faint" style={{ margin: 0 }}>Nothing urgent — overdue and high-priority items will show here.</p></div>
          ) : (
            <div className="card list-card">
              {data.action_required.map((r, i) => (
                <Link key={i} to={`/cases/${r.case.id}/overview`} className="li-row">
                  <span className={`badge badge-${r.severity === "high" ? "red" : "amber"}`}>
                    {r.kind.toUpperCase()}
                  </span>
                  <div className="li-main" style={{ minWidth: 0 }}>
                    <div className="li-title">{r.title}</div>
                    <div className="text-faint" style={{ fontSize: 12 }}>{r.detail} · {r.case.title}</div>
                  </div>
                  <i className="bi bi-chevron-right text-faint" />
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          <h3 className="section-heading">Upcoming deadlines</h3>
          {data.upcoming_deadlines.length === 0 ? (
            <div className="card"><p className="text-faint" style={{ margin: 0 }}>No tracked deadlines approaching.</p></div>
          ) : (
            <div className="card list-card">
              <div className="overline" style={{ marginBottom: 6 }}>Soonest first</div>
              {data.upcoming_deadlines.map((d) => (
                <Link key={d.id} to={`/cases/${d.case.id}/action-plan`} className="li-row">
                  <span className={`dl-dot ${d.days_left <= 3 ? "due" : ""}`} />
                  <div className="li-main">
                    <div className="li-title">{d.title}</div>
                    <div className="text-faint" style={{ fontSize: 12 }}>{d.case.title} · {d.due_date}</div>
                  </div>
                  <span className="text-soft" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {d.days_left <= 0 ? "today" : `${d.days_left}d left`}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <DemoPickerModal open={pickerOpen} demos={demos} onClose={() => setPickerOpen(false)} />
    </div>
  );
}

/* ---- KPI --------------------------------------------------------------- */

function Kpi({ icon, value, label, sub, onClick }: {
  icon: string; value: number; label: string; sub: string; onClick: () => void;
}) {
  return (
    <button className="kpi-card" onClick={onClick}>
      <span className="kpi-icon"><i className={`bi ${icon}`} /></span>
      <div>
        <div className="kpi-value">{value}</div>
        <div className="kpi-label">{label}</div>
        <div className="text-faint" style={{ fontSize: 11 }}>{sub}</div>
      </div>
    </button>
  );
}

function BadgeText({ text }: { text: string }) {
  return <span className={`badge badge-${LEVEL_TONE[text] ?? "neutral"}`} style={{ textTransform: "capitalize" }}>{text}</span>;
}

/* ---- Analytics widgets -------------------------------------------------- */

function AnalyticCard({ title, icon, body }: { title: string; icon: string; body: React.ReactNode }) {
  return (
    <div className="card an-card">
      <div className="an-card-head"><i className={`bi ${icon}`} /> {title}</div>
      {body}
    </div>
  );
}

function IssueBlock({ total, open, byCase, onClick }: {
  total: number; open: number; byCase: { case_id: number; title: string; open: number; total: number }[];
  onClick: (p: string) => void;
}) {
  const by = [...byCase].sort((x, y) => y.open - x.open).slice(0, 4);
  return (
    <div>
      <div className="flex" style={{ gap: 12, alignItems: "baseline" }}>
        <span className="an-big">{total}</span>
        <span className="text-soft" style={{ fontSize: 12.5 }}>
          {open} open across {byCase.length} case{byCase.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="bar-row" style={{ marginTop: 8 }}>
        <div className="bar-fill" style={{ width: `${byCase.length ? (open * 100) / Math.max(total, 1) : 0}%`, background: "var(--amber, #b7791f)" }} />
      </div>
      {by.map((c) => (
        <button key={c.case_id} className="mini-row" onClick={() => onClick(`/cases/${c.case_id}/issues`)}>
          <span className="mini-dot" style={{ background: c.open > 0 ? "var(--amber, #b7791f)" : "var(--green, #1f7a38)" }} />
          <span className="mini-label">{c.title}</span>
          <b style={{ marginLeft: "auto" }}>{c.open}</b>
        </button>
      ))}
    </div>
  );
}

function RiskBlock({ riskAreas, highFactors, onClick }: {
  riskAreas: DashboardData["analytics"]["risk_areas"];
  highFactors: DashboardData["analytics"]["high_risk_factors"];
  onClick: (p: string) => void;
}) {
  if (riskAreas.length === 0 && highFactors.length === 0) {
    return <p className="text-faint" style={{ margin: 0, fontSize: 12.5 }}>Run a risk analysis from a case workspace to populate the radar dimensions.</p>;
  }
  const areas = riskAreas.map((r) => ({
    ...r,
    level: r.overall_level,
    // worst dimension drives the "hotspot" reading
    hotspot: r.worst_dimension ? `${r.worst_dimension} (${r.worst_level})` : null,
  }));
  return (
    <div>
      {areas.slice(0, 4).map((r) => (
        <button key={r.case_id} className="mini-row" onClick={() => onClick(`/cases/${r.case_id}/risks`)}>
          <span className={`badge badge-${LEVEL_TONE[r.level] ?? "neutral"}`}>{r.level}</span>
          <span className="mini-label">{r.title}</span>
          <b style={{ marginLeft: "auto", color: "var(--ink-soft)", fontSize: 12 }}>{r.overall_score}</b>
        </button>
      ))}
      <div className="risk-hot-list">
        {highFactors.slice(0, 3).map((h, i) => (
          <span key={i} className="risk-chip"><i className="bi bi-shield-exclamation" /> {h.title}</span>
        ))}
      </div>
      {areas[0]?.hotspot && <p className="text-faint" style={{ margin: "6px 0 0", fontSize: 11.5 }}>Hotspot: {areas[0].hotspot}</p>}
    </div>
  );
}

function EvidenceBlock({ ev, onClick }: {
  ev: DashboardData["analytics"]["evidence"];
  onClick: (p: string) => void;
}) {
  const covered = ev.open_issues ? Math.round((ev.issues_with_evidence * 100) / ev.open_issues) : 0;
  return (
    <div>
      <div className="flex" style={{ gap: 12, alignItems: "baseline" }}>
        <span className="an-big">{ev.items}</span>
        <span className="text-soft" style={{ fontSize: 12.5 }}>{ev.verified} verified · {ev.unverified} unverified</span>
      </div>
      <div className="ev-stack" style={{ marginTop: 8 }}>
        <div className="bar-row" title={`${ev.verified_pct}% verified`}>
          <div className="bar-fill" style={{ width: `${ev.verified_pct}%`, background: "var(--green, #1f7a38)" }} />
        </div>
        <div className="flex" style={{ gap: 10, fontSize: 11.5, color: "var(--ink-soft)", marginTop: 4 }}>
          <span><i className="bi bi-check-circle" style={{ color: "var(--green)" }} /> {ev.verified_pct}% verified</span>
          <span><i className="bi bi-link-45deg" /> {ev.issues_with_evidence}/{ev.open_issues} open issues have evidence</span>
        </div>
        {ev.by_case.slice(0, 3).map((c) => (
          <button key={c.case_id} className="mini-row" onClick={() => onClick(`/cases/${c.case_id}/evidence`)}>
            <span className="mini-label">{c.title}</span>
            <span className="text-soft" style={{ fontSize: 11.5, marginLeft: "auto" }}>{c.verified}/{c.items} verified</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function GapBlock({ gaps, onClick }: {
  gaps: DashboardData["analytics"]["gaps"];
  onClick: (p: string) => void;
}) {
  const total = Math.max(gaps.open, 1);
  const seg = (n: number, c: string) => ({ n, w: Math.max((n * 100) / total, n ? 4 : 0), c });
  const segs = [seg(gaps.high, "#c0452f"), seg(gaps.medium, "#b7791f"), seg(gaps.low, "#4a6b8f")];
  return (
    <div>
      <div className="flex" style={{ gap: 12, alignItems: "baseline" }}>
        <span className="an-big">{gaps.open}</span>
        <span className="text-soft" style={{ fontSize: 12.5 }}>open gaps</span>
      </div>
      <div className="stack-bar" style={{ marginTop: 10 }}>
        {segs.map((s, i) => s.n > 0 && <div key={i} style={{ width: `${s.w}%`, background: s.c }} />)}
      </div>
      <div className="legend-row" style={{ marginTop: 8 }}>
        {segs.filter((s) => s.n > 0).map((s, i) => (
          <span key={i} style={{ color: s.c }}><i className="bi bi-square-fill" style={{ fontSize: 8 }} /> {s.n} {s.n === 1 ? "high" : ["high", "medium", "low"][i]} priority</span>
        ))}
        {gaps.open === 0 && <span className="text-faint">No open gaps — close detection runs keep this fresh.</span>}
      </div>
    </div>
  );
}

function ScenarioBlock({ sc, onClick }: {
  sc: DashboardData["analytics"]["scenarios"];
  onClick: (p: string) => void;
}) {
  const hasComparison = sc.comparable_cases > 0;
  return (
    <div>
      <div className="flex" style={{ gap: 12, alignItems: "baseline" }}>
        <span className="an-big">{sc.total}</span>
        <span className="text-soft" style={{ fontSize: 12.5 }}>scenarios across cases</span>
      </div>
      <div className="an-callout" style={{ marginTop: 8 }}>
        <i className={`bi ${hasComparison ? "bi-check2-circle" : "bi-info-circle"}`} />
        <span>
          {hasComparison
            ? <>{sc.comparable_cases} case{sc.comparable_cases === 1 ? "" : "s"} with 2+ scenarios — open What-If to run the comparison table.</>
            : "Create at least two scenarios in a case to unlock the current-vs-alternative comparison table."}
        </span>
      </div>
    </div>
  );
}

function NegotiationBlock({ neg, onClick }: {
  neg: DashboardData["analytics"]["negotiation"];
  onClick: (p: string) => void;
}) {
  const pct = neg.active_cases ? Math.round((neg.prepped * 100) / neg.active_cases) : 0;
  return (
    <div>
      <div className="flex" style={{ gap: 12, alignItems: "baseline" }}>
        <span className="an-big">{neg.prepped}<span style={{ fontSize: 14, color: "var(--ink-soft)" }}>/{neg.active_cases}</span></span>
        <span className="text-soft" style={{ fontSize: 12.5 }}>cases with a preparation brief</span>
      </div>
      <div className="bar-row" style={{ marginTop: 8 }}>
        <div className="bar-fill" style={{ width: `${pct}%`, background: "var(--brand-500, #6d4f9e)" }} />
      </div>
      <div className="legend-row" style={{ marginTop: 8 }}>
        <span className="text-faint" style={{ fontSize: 11.5 }}>
          {neg.plan_ready} with generated plan · objective, minimum and counterpart position on file
        </span>
      </div>
      {neg.by_case.slice(0, 3).map((c) => (
        <button key={c.case_id} className="mini-row" onClick={() => onClick(`/cases/${c.case_id}/negotiation`)}>
          <span className={`badge ${c.has_prep ? "badge-green" : "badge-neutral"}`}>{c.has_prep ? "prepped" : "not prepped"}</span>
          <span className="mini-label">{c.title}</span>
        </button>
      ))}
    </div>
  );
}

function CaseTile({ c }: { c: CaseSummary }) {
  return (
    <Link to={`/cases/${c.id}/overview`} className="card case-card">
      <div className="case-card-top">
        <span className="case-card-icon"><i className={`bi ${TYPE_ICON[c.case_type] ?? "bi-briefcase"}`} /></span>
        {c.is_demo && <span className="badge badge-demo"><i className="bi bi-stars" /> Demo</span>}
      </div>
      <b className="case-card-title">{c.title}</b>
      <div className="text-faint" style={{ fontSize: 12 }}>{c.case_type} · {c.jurisdiction}</div>
      <div className="case-card-foot">
        <span className="text-faint">{c.updated_at ? formatDate(c.updated_at) : ""}</span>
        <i className="bi bi-chevron-right" />
      </div>
    </Link>
  );
}
