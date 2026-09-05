"""Case management business logic: CRUD, ownership checks, the aggregate
case context for the workspace, dashboard summary, and demo-case seeding."""
from datetime import date, timedelta

from app.extensions import db
from models import (ActionItem, Case, CaseDocument, ChatMessage, ChatSession,
                    Deadline, EvidenceItem, InfoGap, LegalIssue,
                    NegotiationPrep, NegotiationSession, RiskAssessment,
                    RiskFactor, Scenario, TimelineEvent)
from schemas import CaseCreateSchema, CaseUpdateSchema, SchemaError
from utils.india import (DEMO_STATE_BY_CASE_TYPE, INDIAN_STATES_UTS,
                         JURISDICTION_COUNTRY, jurisdiction_string)

# Phase-2 case statuses (non-terminal = "active" for dashboard purposes).
TERMINAL_STATUSES = ("resolved", "archived")


class CaseError(Exception):
    def __init__(self, message: str, status: int = 404):
        super().__init__(message)
        self.message = message
        self.status = status


def get_owned_case(user_id: int, case_id: int) -> Case:
    case = db.session.get(Case, case_id)
    if case is None or case.user_id != user_id:
        raise CaseError("Case not found", 404)
    return case


def list_cases(user_id: int):
    return (Case.query.filter_by(user_id=user_id)
            .order_by(Case.updated_at.desc()).all())


def create_case(user_id: int, data: dict) -> Case:
    try:
        schema = CaseCreateSchema(data).validate()
    except SchemaError as exc:
        raise CaseError(str(exc), 400) from exc
    case = Case(
        user_id=user_id,
        title=schema.title,
        case_type=schema.case_type,
        description=schema.description,
        parties=schema.parties,
        country=schema.country,
        state=schema.state,
        stage=schema.stage,
        status=schema.status,
        jurisdiction=jurisdiction_string(schema.state),
    )
    db.session.add(case)
    db.session.commit()
    return case


def migrate_jurisdiction_to_india() -> None:
    """Idempotent startup migration locking every existing case to India.

    The application is India-only now. Country is set to India for any case
    that lacks it (data is never deleted). Legacy demo cases seeded with a
    non-Indian state get a sensible Indian state so fictional demos stay
    coherent; other cases keep their stored state value untouched and simply
    get the jurisdiction label rebuilt around India.
    """
    changed = 0
    for case in Case.query.all():
        dirty = False
        if case.country != JURISDICTION_COUNTRY:
            case.country = JURISDICTION_COUNTRY
            dirty = True
        if case.is_demo and (case.state or "").strip() not in INDIAN_STATES_UTS:
            mapped = DEMO_STATE_BY_CASE_TYPE.get(case.case_type or "")
            if mapped:
                case.state = mapped
                dirty = True
        expected = jurisdiction_string(case.state)
        if case.jurisdiction != expected:
            case.jurisdiction = expected
            dirty = True
        if dirty:
            changed += 1
    if changed:
        db.session.commit()


def update_case(user_id: int, case_id: int, data: dict) -> Case:
    case = get_owned_case(user_id, case_id)
    try:
        CaseUpdateSchema(data).apply(case)
    except SchemaError as exc:
        raise CaseError(str(exc), 400) from exc
    db.session.commit()
    return case


def delete_case(user_id: int, case_id: int) -> None:
    case = get_owned_case(user_id, case_id)
    # These one-per-case tables have no ORM cascade off Case, so they must be
    # removed explicitly or they orphan and block case-id reuse. Messages are
    # removed before their session so FK order never matters.
    ChatMessage.query.filter_by(case_id=case_id).delete()
    NegotiationPrep.query.filter_by(case_id=case_id).delete()
    ChatSession.query.filter_by(case_id=case_id).delete()
    NegotiationSession.query.filter_by(case_id=case_id).delete()
    db.session.delete(case)
    db.session.commit()


# --------------------------------------------------------------------------
# Case workspace context (single aggregate payload for the CaseDataProvider)
# --------------------------------------------------------------------------

def get_case_context(user_id: int, case_id: int) -> dict:
    """Return the case plus every workspace collection in one payload.
    All future AI outputs attach to the same case_id."""
    case = get_owned_case(user_id, case_id)
    prep = NegotiationPrep.query.filter_by(case_id=case.id).first()
    return {
        "case": case.to_dict(),
        "documents": [d.to_dict() for d in case.documents.order_by(CaseDocument.uploaded_at.desc()).all()],
        "timeline": [e.to_dict() for e in case.timeline.order_by(TimelineEvent.date.desc()).all()],
        "issues": [i.to_dict() for i in case.issues.order_by(LegalIssue.created_at.desc()).all()],
        "risks": [r.to_dict() for r in case.risks.order_by(RiskFactor.created_at.desc()).all()],
        "gaps": [g.to_dict() for g in case.gaps.order_by(InfoGap.created_at.desc()).all()],
        "scenarios": [s.to_dict() for s in case.scenarios.order_by(Scenario.created_at.desc()).all()],
        "evidence": [e.to_dict() for e in case.evidence.order_by(EvidenceItem.created_at.desc()).all()],
        "actions": [a.to_dict() for a in case.actions.order_by(ActionItem.due_date.asc().nulls_last()).all()],
        "deadlines": [d.to_dict() for d in case.deadlines.order_by(Deadline.due_date.asc()).all()],
        "prep": prep.to_dict() if prep else None,
        "risk_assessment": case.assessment.to_dict() if case.assessment else None,
    }


# --------------------------------------------------------------------------
# Dashboard (real data only — no fake statistics)
# --------------------------------------------------------------------------

def dashboard_summary(user_id: int) -> dict:
    cases = Case.query.filter_by(user_id=user_id).order_by(Case.updated_at.desc()).all()
    today = date.today()

    deadlines = (
        Deadline.query.join(Case)
        .filter(Case.user_id == user_id, Deadline.status != "completed")
        .order_by(Deadline.due_date.asc())
        .all()
    )
    upcoming = [d for d in deadlines if d.due_date >= today][:6]

    recent = []
    for c in cases[:5]:
        d = c.to_dict()
        d["highest_risk"] = max((r.overall_risk for r in c.risks.all()), default=None)
        recent.append(d)

    # "Action required": urgent deadlines, overdue or high-priority actions, high-confidence issues.
    action_required = []
    for d in deadlines:
        if d.due_date < today:
            action_required.append({
                "kind": "deadline",
                "title": d.title,
                "detail": f"Overdue by {(today - d.due_date).days} day(s)",
                "severity": "high",
                "case": {"id": d.case_id, "title": d.case.title},
            })
        elif (d.due_date - today).days <= 7:
            action_required.append({
                "kind": "deadline",
                "title": d.title,
                "detail": f"Due in {(d.due_date - today).days} day(s)",
                "severity": "high" if (d.due_date - today).days <= 3 else "medium",
                "case": {"id": d.case_id, "title": d.case.title},
            })

    actions = (
        ActionItem.query.join(Case)
        .filter(Case.user_id == user_id, ActionItem.status.notin_(("completed", "skipped")))
        .order_by(ActionItem.due_date.asc().nulls_last())
        .all()
    )
    for a in actions:
        if a.due_date and a.due_date < today:
            action_required.append({
                "kind": "action",
                "title": a.title,
                "detail": f"Action overdue (due {a.due_date.isoformat()})",
                "severity": "high",
                "case": {"id": a.case_id, "title": a.case.title},
            })
        elif a.priority == "high":
            action_required.append({
                "kind": "action",
                "title": a.title,
                "detail": "High-priority action",
                "severity": "medium",
                "case": {"id": a.case_id, "title": a.case.title},
            })

    issues = (
        LegalIssue.query.join(Case)
        .filter(Case.user_id == user_id, LegalIssue.status != "resolved",
                LegalIssue.confidence == "high")
        .all()
    )
    for i in issues[:3]:
        action_required.append({
            "kind": "issue",
            "title": i.title,
            "detail": "Open issue (high confidence)",
            "severity": "medium",
            "case": {"id": i.case_id, "title": i.case.title},
        })

    return {
        "kpis": {
            "active_cases": sum(1 for c in cases if c.status not in TERMINAL_STATUSES),
            "documents_analyzed": _documents_analyzed(user_id),
            "pending_actions": len(actions),
            "upcoming_deadlines": len(upcoming),
        },
        "recent_cases": recent,
        "upcoming_deadlines": [{
            "id": d.id,
            "title": d.title,
            "due_date": d.due_date.isoformat(),
            "days_left": (d.due_date - today).days,
            "status": d.status,
            "case": {"id": d.case_id, "title": d.case.title},
        } for d in upcoming],
        "action_required": action_required[:8],
        "analytics": _case_analytics(cases),
        "recent_ai_insights": _recent_ai_insights(cases),
    }


def _case_analytics(cases: list) -> dict:
    """Phase-13 analytics — every figure derived from real case rows."""
    import json

    open_issues = []
    issue_rows = []
    high_risks = []            # risk factors rated high/critical
    gap_buckets = {"high": 0, "medium": 0, "low": 0}
    evidence_totals = {"items": 0, "verified": 0, "unverified": 0, "disputed": 0}
    linked_issue_ids = set()
    scenarios_total = 0
    scenarios_analyzed = 0
    cases_with_2plus_scenarios = 0
    prep_complete = 0
    prep_cases = []
    risk_area_rows = []        # worst per-dimension level per case (from assessments)
    evidence_by_case = []
    issues_by_case = []

    for c in cases:
        iss_rows = c.issues.all()
        open_iss = [i for i in iss_rows if (i.status or "open") not in ("resolved", "not_actionable")]
        open_issues.extend(open_iss)
        issue_rows.extend(iss_rows)
        issues_by_case.append({"case_id": c.id, "title": c.title,
                               "open": len(open_iss), "total": len(iss_rows)})

        for r in c.risks.all():
            if r.overall_risk in ("high", "critical"):
                high_risks.append({"title": r.title, "level": r.overall_risk,
                                   "case_id": c.id, "case_title": c.title})

        for g in c.gaps.all():
            if (g.status or "open") == "open":
                gap_buckets[g.priority or "medium"] = gap_buckets.get(g.priority or "medium", 0) + 1

        ev_rows = c.evidence.all()
        ev_verified = sum(1 for e in ev_rows if e.verification == "verified")
        ev_unverified = sum(1 for e in ev_rows if e.verification == "unverified")
        ev_disputed = sum(1 for e in ev_rows if e.verification == "disputed")
        evidence_totals["items"] += len(ev_rows)
        evidence_totals["verified"] += ev_verified
        evidence_totals["unverified"] += ev_unverified
        evidence_totals["disputed"] += ev_disputed
        for e in ev_rows:
            for i in e.issues:
                linked_issue_ids.add(i.id)
        if len(ev_rows):
            evidence_by_case.append({
                "case_id": c.id, "title": c.title, "items": len(ev_rows),
                "verified": ev_verified, "verified_pct": round(ev_verified * 100 / len(ev_rows)),
            })

        scen_rows = c.scenarios.all()
        scenarios_total += len(scen_rows)
        for s in scen_rows:
            if s.analysis_json:
                scenarios_analyzed += 1
        if len(scen_rows) >= 2:
            cases_with_2plus_scenarios += 1

        prep = NegotiationPrep.query.filter_by(case_id=c.id).first()
        if prep:
            plan_ready = bool((prep.plan_json or "").strip())
            if prep.strategy and prep.counterpart_analysis and prep.goals:
                prep_complete += 1
            prep_cases.append({"case_id": c.id, "title": c.title,
                               "has_prep": True, "plan_ready": plan_ready})
        else:
            prep_cases.append({"case_id": c.id, "title": c.title,
                               "has_prep": False, "plan_ready": False})

        # Worst dimension level from the Phase-7 assessment, if present.
        if c.assessment:
            level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            dims = []
            try:
                dims = json.loads(c.assessment.dimensions_json or "[]")
            except (ValueError, TypeError):
                dims = []
            worst = max(dims, key=lambda d: level_order.get((d or {}).get("level"), 0), default=None) \
                if dims else None
            risk_area_rows.append({
                "case_id": c.id,
                "title": c.title,
                "overall_score": c.assessment.overall_score or 0,
                "overall_level": c.assessment.overall_level or "medium",
                "worst_dimension": (worst or {}).get("label") or None,
                "worst_level": (worst or {}).get("level") or None,
                "dimensions": [{"label": (d or {}).get("label"), "level": (d or {}).get("level"),
                                "score": (d or {}).get("score", 0)}
                               for d in dims],
            })

    open_issue_ids = {i.id for i in open_issues}
    covered_issue_ids = linked_issue_ids & open_issue_ids
    active_count = sum(1 for c in cases if c.status not in TERMINAL_STATUSES)
    return {
        "issues": {
            "total": len(issue_rows),
            "open": len(open_issues),
            "by_case": issues_by_case,
        },
        "high_risk_factors": high_risks[:10],
        "risk_areas": risk_area_rows,
        "evidence": {
            **evidence_totals,
            "verified_pct": round(evidence_totals["verified"] * 100 / evidence_totals["items"])
            if evidence_totals["items"] else 0,
            "by_case": evidence_by_case,
            "issues_with_evidence": len(covered_issue_ids),
            "open_issues": len(open_issue_ids),
        },
        "gaps": {
            "open": sum(gap_buckets.values()),
            "high": gap_buckets["high"],
            "medium": gap_buckets["medium"],
            "low": gap_buckets["low"],
        },
        "scenarios": {
            "total": scenarios_total,
            "analyzed": scenarios_analyzed,
            "comparable_cases": cases_with_2plus_scenarios,
        },
        "negotiation": {
            "cases": len(prep_cases),
            "prepped": prep_complete,
            "plan_ready": sum(1 for p in prep_cases if p["plan_ready"]),
            "active_cases": active_count,
            "by_case": prep_cases,
        },
    }


def _recent_ai_insights(cases: list) -> list:
    """Most recent AI-produced findings (issues, risks, gaps, analyses)."""
    items = []
    for c in cases:
        for i in c.issues.all():
            if i.provenance in ("ai", "document"):
                items.append({"kind": "issue", "title": i.title,
                              "confidence": i.confidence or "medium",
                              "created_at": i.created_at.isoformat() if i.created_at else "",
                              "case_id": c.id, "case_title": c.title})
        for r in c.risks.all():
            if r.provenance == "ai":
                items.append({"kind": "risk", "title": r.title,
                              "level": r.overall_risk or "medium",
                              "created_at": r.created_at.isoformat() if r.created_at else "",
                              "case_id": c.id, "case_title": c.title})
        for g in c.gaps.all():
            if g.source == "ai":
                items.append({"kind": "gap", "title": g.question,
                              "priority": g.priority or "medium",
                              "created_at": g.created_at.isoformat() if g.created_at else "",
                              "case_id": c.id, "case_title": c.title})
        for d in c.documents.all():
            if d.analysis_status == "analyzed":
                items.append({"kind": "analysis", "title": d.filename,
                              "detail": "Document analysis available",
                              "created_at": d.uploaded_at.isoformat() if d.uploaded_at else "",
                              "case_id": c.id, "case_title": c.title})
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items[:8]


def _documents_analyzed(user_id: int) -> int:
    from models import CaseDocument

    return (
        CaseDocument.query.join(Case)
        .filter(Case.user_id == user_id, CaseDocument.analysis_status == "analyzed")
        .count()
    )


# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Demo cases (Phase 13) — five fully-populated FICTIONAL cases
# --------------------------------------------------------------------------

def list_demo_catalog() -> list:
    """Fictional metadata for the Explore Demo Case picker (safe to expose)."""
    from services import demo_catalog
    return demo_catalog.demo_catalog_meta()


def create_demo_case(user_id: int, kind: str = "rental") -> Case:
    """Build one fully-populated fictional demo case from the catalog."""
    from services import demo_catalog
    return demo_catalog.create_demo_case(user_id, kind=kind)
