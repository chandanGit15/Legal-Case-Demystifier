import { useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { CaseProvider, useCase } from "../context/CaseContext";
import { useLanguage } from "../context/LanguageContext";
import type { CaseSummary } from "../types";
import { caseStatusMeta } from "../utils/constants";
import { formatDate } from "../utils/format";
import { Badge, ErrorState, Loading } from "../components/ui";
import { EditCaseModal } from "../components/EditCaseModal";

const SECTIONS: { to: string; key: string; icon: string }[] = [
  { to: "overview", key: "tabOverview", icon: "bi-house" },
  { to: "timeline", key: "tabTimeline", icon: "bi-calendar3" },
  { to: "documents", key: "tabDocuments", icon: "bi-file-earmark-text" },
  { to: "issues", key: "tabIssues", icon: "bi-exclamation-circle" },
  { to: "risks", key: "tabRisks", icon: "bi-shield-exclamation" },
  { to: "scenarios", key: "tabScenarios", icon: "bi-diagram-3" },
  { to: "negotiation", key: "tabNegotiation", icon: "bi-people" },
  { to: "evidence", key: "tabEvidence", icon: "bi-collection" },
  { to: "assistant", key: "tabAssistant", icon: "bi-chat-dots" },
  { to: "action-plan", key: "tabActionPlan", icon: "bi-list-check" },
];

/** Inner shell renders inside the CaseProvider so it can read case state. */
function CaseWorkspace() {
  const { caseData, error, refresh, refreshing } = useCase();
  const [editOpen, setEditOpen] = useState(false);

  if (error) {
    return (
      <div className="page-wide">
        <ErrorState message={error} onRetry={() => void refresh()} />
      </div>
    );
  }
  if (!caseData) {
    return <div className="page-wide"><Loading label="Loading case workspace…" /></div>;
  }

  return (
    <CaseShell caseData={caseData} refreshing={refreshing}
               onEdit={() => setEditOpen(true)}>
      <EditCaseModal open={editOpen} onClose={() => setEditOpen(false)}
                     caseData={caseData} />
    </CaseShell>
  );
}

function CaseShell({ caseData, refreshing, onEdit, children }: {
  caseData: CaseSummary;
  refreshing: boolean;
  onEdit: () => void;
  children: React.ReactNode;
}) {
  const status = caseStatusMeta(caseData.status);
  const { t } = useLanguage();
  const jurisdiction = caseData.jurisdiction
    || [caseData.country, caseData.state].filter(Boolean).join(", ");
  const counts = caseData.counts;

  return (
    <div className="workspace">
      <aside className="workspace-nav" aria-label={t("groupCase")}>
        <div className="wn-group">
          <div className="overline wn-title">{t("groupCase")}</div>
          {SECTIONS.map((s) => (
            <NavLink key={s.to} to={s.to}
                     className={({ isActive }) => `wn-item ${isActive ? "active" : ""}`}>
              <i className={`bi ${s.icon}`} />{t(s.key)}
            </NavLink>
          ))}
        </div>
      </aside>
      <div className="workspace-main">
        <header className="case-header">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="overline mb-1">
              {t("groupCase")} #{caseData.id}
              {caseData.updated_at && <> · {t("caseUpdated")} {formatDate(caseData.updated_at)}</>}
              {refreshing && <span className="text-faint"> · {t("syncing")}</span>}
            </div>
            <h1>{caseData.title}</h1>
            <div className="case-header-meta">
              <span className="meta-chip">
                <i className="bi bi-tag" />
                {caseData.case_type || t("uncategorized")}
              </span>
              <span className="meta-chip">
                <i className="bi bi-geo-alt" />
                {jurisdiction || t("jurisdictionNotSet")}
              </span>
              {counts && (
                <span className="meta-chip text-faint">
                  {counts.documents} {t("docs")} · {counts.issues} {t("issues")} · {counts.risks} {t("risks")}
                </span>
              )}
              {caseData.is_demo && (
                <span className="badge badge-demo"><i className="bi bi-stars" /> {t("demoCase")}</span>
              )}
            </div>
          </div>
          <div className="flex" style={{ gap: 10, alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <div className="flex" style={{ gap: 6, justifyContent: "flex-end", alignItems: "center" }}>
                <Badge tone={status.tone}>{status.label}</Badge>
              </div>
              <div className="overline" style={{ marginTop: 4 }}>
                {caseData.stage || t("infoGathering")}
              </div>
            </div>
            <button className="btn btn-outline btn-sm" onClick={onEdit}>
              <i className="bi bi-pencil" /> {t("edit")}
            </button>
          </div>
        </header>
        {!jurisdiction && (
          <div className="jurisdiction-note" role="status">
            <i className="bi bi-info-circle" />
            <div>
              <b>Jurisdiction not set.</b> Add your country and state/region so the
              analysis and deadlines can be framed correctly — legal rules vary by
              jurisdiction and the AI will flag that uncertainty until it is set.
            </div>
            <button className="btn btn-sm btn-outline" onClick={onEdit}>
              {t("edit")} jurisdiction
            </button>
          </div>
        )}
        <Outlet />
      </div>
      {children}
    </div>
  );
}

export function CaseLayout() {
  const { caseId } = useParams<{ caseId: string }>();
  if (!caseId) return null;
  return (
    <CaseProvider caseId={caseId}>
      <CaseWorkspace />
    </CaseProvider>
  );
}
