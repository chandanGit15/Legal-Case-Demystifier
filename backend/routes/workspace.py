"""Case workspace: timeline, legal issues, risks, info gaps, scenarios,
negotiation, evidence, actions, deadlines, and the contextual AI assistant.

Handlers stay thin: data marshalling lives here, business logic in
services and the AI service layer."""
import json
from datetime import date, datetime

from flask import Blueprint, g, jsonify, request

from ai import (analyze_case_overview, analyze_case_risks,
                analyze_negotiation_prep, answer_case_question, assess_risks,
                build_case_context, compare_scenarios, detect_information_gaps,
                detect_legal_issues, evaluate_negotiation, explain_simply,
                extract_deadline_dates, extract_timeline_events,
                generate_action_plan, generate_negotiation_message,
                generate_scenario, negotiation_practice, simulation_reply)
from app.extensions import db
from models import (ActionItem, Case, ChatMessage, ChatSession, Deadline,
                    EvidenceItem, InfoGap, LegalIssue, NegotiationPrep,
                    NegotiationSession, RiskAssessment, RiskFactor, Scenario,
                    TimelineEvent)
from services import case_service
from utils.auth import require_auth

workspace_bp = Blueprint("workspace", __name__, url_prefix="/api/cases/<int:case_id>")


def _case_or_404(case_id):
    try:
        return case_service.get_owned_case(g.user.id, case_id), None
    except case_service.CaseError:
        return None, (jsonify({"error": "Case not found"}), 404)


def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _apply_timeline_patch(event, data):
    """Shared update logic for timeline events (PATCH + top-level PUT)."""
    if "title" in data:
        event.title = (data["title"] or "").strip()
    if "description" in data:
        event.description = (data["description"] or "").strip()
    if "category" in data:
        event.category = (data["category"] or "").strip()
    if "event_type" in data:
        event.event_type = (data["event_type"] or "other").strip()
    if "importance" in data:
        event.importance = (data["importance"] or "medium").strip()
    if "date_status" in data:
        event.date_status = (data["date_status"] or "user_confirmed").strip()
    if "source" in data:
        event.source = (data["source"] or "user").strip()
    if "date" in data:
        parsed = _parse_date(data["date"])
        if parsed:
            event.date = parsed


def _apply_evidence_patch(item, data, case=None):
    """Shared update logic for evidence items (PATCH + top-level PUT)."""
    for field in ("title", "description", "item_type", "source", "status", "notes"):
        if field in data:
            setattr(item, field, (data[field] or "").strip())
    for field in ("importance", "verification"):
        if field in data:
            fallback = "medium" if field == "importance" else "unverified"
            setattr(item, field, (data[field] or fallback).strip())
    if "date" in data:
        item.date = _parse_date(data.get("date"))
    if case is not None and "related_issue_ids" in data and isinstance(data["related_issue_ids"], list):
        ids = {int(x) for x in data["related_issue_ids"] if str(x).lstrip("-").isdigit()}
        if ids:
            item.issues = (LegalIssue.query
                           .filter(LegalIssue.id.in_(ids), LegalIssue.case_id == case.id)
                           .all())
        else:
            item.issues = []


# --------------------------------------------------------------------------
# AI case overview (analyze only; no auto-insert)
# --------------------------------------------------------------------------

@workspace_bp.post("/overview/analyze")
@require_auth
def overview_analyze(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    return jsonify(analyze_case_overview(build_case_context(case)))


# --------------------------------------------------------------------------
# Timeline
# --------------------------------------------------------------------------

@workspace_bp.get("/timeline")
@require_auth
def list_timeline(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    events = case.timeline.order_by(TimelineEvent.date.desc()).all()
    return jsonify({"events": [e.to_dict() for e in events]})


@workspace_bp.post("/timeline")
@require_auth
def add_timeline_event(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    if not (data.get("title") or "").strip():
        return jsonify({"error": "A title is required"}), 400
    evt_date = _parse_date(data.get("date"))
    if evt_date is None:
        return jsonify({"error": "A valid date is required"}), 400
    event = TimelineEvent(
        case_id=case.id, date=evt_date,
        title=(data.get("title") or "").strip()[:255],
        description=(data.get("description") or "").strip(),
        category=(data.get("category") or "").strip(),
        event_type=(data.get("event_type") or "other").strip(),
        importance=(data.get("importance") or "medium").strip(),
        date_status=(data.get("date_status") or "user_confirmed").strip(),
        source=(data.get("source") or "user").strip(),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({"event": event.to_dict()}), 201


@workspace_bp.post("/timeline/extract")
@require_auth
def extract_timeline(case_id):
    """AI timeline extraction: surfaces dated events from the case description,
    uploaded document analyses and prior conversation. Nothing is saved — the
    frontend shows candidates marked extracted/potential for explicit review."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    result = extract_timeline_events(build_case_context(case))
    result["saved_count"] = 0  # candidates only; confirmed via POST /timeline
    return jsonify(result)


@workspace_bp.patch("/timeline/<int:event_id>")
@require_auth
def update_timeline_event(case_id, event_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    event = db.session.get(TimelineEvent, event_id)
    if event is None or event.case_id != case.id:
        return jsonify({"error": "Event not found"}), 404
    data = request.get_json(silent=True) or {}
    _apply_timeline_patch(event, data)
    db.session.commit()
    return jsonify({"event": event.to_dict()})


@workspace_bp.delete("/timeline/<int:event_id>")
@require_auth
def delete_timeline_event(case_id, event_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    event = db.session.get(TimelineEvent, event_id)
    if event is None or event.case_id != case.id:
        return jsonify({"error": "Event not found"}), 404
    db.session.delete(event)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Legal issues
# --------------------------------------------------------------------------

@workspace_bp.get("/issues")
@require_auth
def list_issues(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    issues = case.issues.order_by(LegalIssue.created_at.desc()).all()
    return jsonify({"issues": [i.to_dict() for i in issues]})


@workspace_bp.post("/issues")
@require_auth
def add_issue(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "An issue title is required"}), 400
    issue = LegalIssue(
        case_id=case.id, title=title[:255],
        description=(data.get("description") or "").strip(),
        category=(data.get("category") or "").strip(),
        jurisdiction=(data.get("jurisdiction") or "").strip() or case.jurisdiction or "",
        confidence=(data.get("confidence") or "medium").strip(),
        provenance=(data.get("provenance") or "user").strip(),
        supporting_facts=json.dumps(data.get("supporting_facts") or []),
        related_documents=json.dumps(data.get("related_documents") or []),
        missing_information=json.dumps(data.get("missing_information") or []),
        impact=(data.get("impact") or "").strip(),
    )
    db.session.add(issue)
    db.session.commit()
    return jsonify({"issue": issue.to_dict()}), 201


@workspace_bp.post("/issues/detect")
@require_auth
def detect_issues(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    result = detect_legal_issues(build_case_context(case))
    existing = {i.title.strip().lower() for i in case.issues.all()}
    added, skipped = [], 0
    for issue in result.get("issues") or []:
        title = (issue.get("title") or "").strip()[:255]
        if not title or title.lower() in existing:
            skipped += 1
            continue
        existing.add(title.lower())
        row = LegalIssue(
            case_id=case.id, title=title,
            description=(issue.get("description") or "").strip(),
            category=(issue.get("category") or "").strip(),
            jurisdiction=case.jurisdiction or "",
            confidence=(issue.get("confidence") or "medium").strip(),
            provenance="ai",
            supporting_facts=json.dumps(issue.get("supporting_facts") or []),
            related_documents=json.dumps(issue.get("related_documents") or []),
            missing_information=json.dumps(issue.get("missing_information") or []),
            impact=(issue.get("impact") or "").strip(),
        )
        db.session.add(row)
        added.append(row)
    db.session.commit()
    result["added_issues"] = [i.to_dict() for i in added]
    result["duplicates_skipped"] = skipped
    return jsonify(result)


@workspace_bp.patch("/issues/<int:issue_id>")
@require_auth
def update_issue(case_id, issue_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    issue = db.session.get(LegalIssue, issue_id)
    if issue is None or issue.case_id != case.id:
        return jsonify({"error": "Issue not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "category", "confidence", "status", "impact"):
        if field in data and isinstance(data[field], str):
            setattr(issue, field, data[field].strip())
    for field in ("supporting_facts", "related_documents", "missing_information"):
        if field in data and isinstance(data[field], list):
            setattr(issue, field, json.dumps(data[field]))
    db.session.commit()
    return jsonify({"issue": issue.to_dict()})


@workspace_bp.delete("/issues/<int:issue_id>")
@require_auth
def delete_issue(case_id, issue_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    issue = db.session.get(LegalIssue, issue_id)
    if issue is None or issue.case_id != case.id:
        return jsonify({"error": "Issue not found"}), 404
    db.session.delete(issue)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Risk analysis
# --------------------------------------------------------------------------

@workspace_bp.get("/risks")
@require_auth
def list_risks(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    risks = case.risks.order_by(RiskFactor.created_at.desc()).all()
    return jsonify({"risks": [r.to_dict() for r in risks]})


@workspace_bp.post("/risks")
@require_auth
def add_risk(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "A risk title is required"}), 400
    risk = RiskFactor(
        case_id=case.id, title=title[:255],
        description=(data.get("description") or "").strip(),
        likelihood=(data.get("likelihood") or "medium").strip(),
        impact=(data.get("impact") or "medium").strip(),
        overall_risk=(data.get("overall_risk") or "").strip() or "medium",
        mitigation=(data.get("mitigation") or "").strip(),
        provenance=(data.get("provenance") or "user").strip(),
    )
    db.session.add(risk)
    db.session.commit()
    return jsonify({"risk": risk.to_dict()}), 201


@workspace_bp.post("/risks/assess")
@require_auth
def run_risk_assessment(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    result = assess_risks(build_case_context(case))
    added = []
    for risk in result.get("risks") or []:
        title = (risk.get("title") or "").strip()[:255]
        if not title:
            continue
        row = RiskFactor(
            case_id=case.id, title=title,
            description=(risk.get("description") or "").strip(),
            likelihood=(risk.get("likelihood") or "medium").strip(),
            impact=(risk.get("impact") or "medium").strip(),
            overall_risk=(risk.get("overall_risk") or "medium").strip(),
            mitigation=(risk.get("mitigation") or "").strip(),
            provenance="ai",
        )
        db.session.add(row)
        added.append(row)
    db.session.commit()
    result["added_risks"] = [r.to_dict() for r in added]
    return jsonify(result)


@workspace_bp.patch("/risks/<int:risk_id>")
@require_auth
def update_risk(case_id, risk_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    risk = db.session.get(RiskFactor, risk_id)
    if risk is None or risk.case_id != case.id:
        return jsonify({"error": "Risk not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "likelihood", "impact", "overall_risk", "mitigation"):
        if field in data:
            setattr(risk, field, (data[field] or "").strip())
    db.session.commit()
    return jsonify({"risk": risk.to_dict()})


@workspace_bp.delete("/risks/<int:risk_id>")
@require_auth
def delete_risk(case_id, risk_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    risk = db.session.get(RiskFactor, risk_id)
    if risk is None or risk.case_id != case.id:
        return jsonify({"error": "Risk not found"}), 404
    db.session.delete(risk)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Phase-7 explainable risk analysis
# --------------------------------------------------------------------------

@workspace_bp.post("/risk-analysis")
@require_auth
def run_risk_analysis(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    previous = case.assessment
    result = analyze_case_risks(build_case_context(case),
                                previous.to_dict() if previous else None)
    assessment = previous or RiskAssessment(case_id=case.id)
    if previous is not None:
        assessment.previous_json = json.dumps(previous.to_dict())
    assessment.overall_score = result["overall_score"]
    assessment.overall_level = result["overall_level"]
    assessment.summary = result.get("summary") or ""
    assessment.dimensions_json = json.dumps(result["dimensions"])
    assessment.note = result.get("note") or ""
    db.session.add(assessment)
    db.session.commit()
    return jsonify({"assessment": assessment.to_dict(),
                    "changes": result.get("changes") or []})


@workspace_bp.get("/risk-analysis")
@require_auth
def get_risk_analysis(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    assessment = case.assessment
    return jsonify({"assessment": assessment.to_dict() if assessment else None})


# --------------------------------------------------------------------------
# Information gaps
# --------------------------------------------------------------------------

@workspace_bp.get("/gaps")
@require_auth
def list_gaps(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    gaps = case.gaps.order_by(InfoGap.created_at.desc()).all()
    return jsonify({"gaps": [g.to_dict() for g in gaps]})


@workspace_bp.post("/gaps")
@require_auth
def add_gap(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "A question is required"}), 400
    gap = InfoGap(
        case_id=case.id, question=question[:500],
        why_it_matters=(data.get("why_it_matters") or "").strip(),
        priority=(data.get("priority") or "medium").strip(),
        source=(data.get("source") or "user").strip(),
        related_issue=(data.get("related_issue") or "").strip()[:500],
        how_to_find=(data.get("how_to_find") or "").strip(),
        status=(data.get("status") or "open").strip(),
    )
    db.session.add(gap)
    db.session.commit()
    return jsonify({"gap": gap.to_dict()}), 201


@workspace_bp.post("/gaps/detect")
@workspace_bp.post("/information-gaps")
@require_auth
def detect_gaps(case_id):
    """Information Gap Analyzer: surface missing information that could
    materially change the analysis. Also exposed as POST /information-gaps."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    result = detect_information_gaps(build_case_context(case))
    existing = {g.question.strip().lower() for g in case.gaps.all()}
    added, skipped = [], 0
    for gap in result.get("gaps") or []:
        question = (gap.get("question") or "").strip()[:500]
        if not question or question.lower() in existing:
            skipped += 1
            continue
        existing.add(question.lower())
        row = InfoGap(
            case_id=case.id, question=question,
            why_it_matters=(gap.get("why_it_matters") or "").strip(),
            priority=(gap.get("priority") or "medium").strip(),
            source="ai",
            related_issue=(gap.get("related_issue") or "").strip()[:500],
            how_to_find=(gap.get("how_to_find") or "").strip(),
        )
        db.session.add(row)
        added.append(row)
    db.session.commit()
    result["added_gaps"] = [g.to_dict() for g in added]
    result["duplicates_skipped"] = skipped
    return jsonify(result)


@workspace_bp.patch("/gaps/<int:gap_id>")
@require_auth
def update_gap(case_id, gap_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    gap = db.session.get(InfoGap, gap_id)
    if gap is None or gap.case_id != case.id:
        return jsonify({"error": "Gap not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("question", "why_it_matters", "priority", "status",
                  "related_issue", "how_to_find"):
        if field in data and isinstance(data[field], str):
            setattr(gap, field, data[field].strip())
    db.session.commit()
    return jsonify({"gap": gap.to_dict()})


@workspace_bp.delete("/gaps/<int:gap_id>")
@require_auth
def delete_gap(case_id, gap_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    gap = db.session.get(InfoGap, gap_id)
    if gap is None or gap.case_id != case.id:
        return jsonify({"error": "Gap not found"}), 404
    db.session.delete(gap)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# What-if scenarios
# --------------------------------------------------------------------------

@workspace_bp.get("/scenarios")
@require_auth
def list_scenarios(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    scenarios = case.scenarios.order_by(Scenario.created_at.desc()).all()
    return jsonify({"scenarios": [s.to_dict() for s in scenarios]})


@workspace_bp.post("/scenarios")
@require_auth
def add_scenario(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "A scenario name is required"}), 400
    facts = data.get("facts") or []
    if not isinstance(facts, list):
        facts = []
    scenario = Scenario(
        case_id=case.id, name=name[:255],
        description=(data.get("description") or "").strip(),
        parameters=(data.get("parameters") or "").strip(),
        facts_json=json.dumps([{"text": str(f.get("text", ""))[:500]}
                               for f in facts if isinstance(f, dict) and str(f.get("text", "")).strip()]),
        risk_level=(data.get("risk_level") or "medium").strip(),
    )
    db.session.add(scenario)
    db.session.commit()
    return jsonify({"scenario": scenario.to_dict()}), 201


@workspace_bp.put("/scenarios/<int:scenario_id>")
@require_auth
def update_scenario(case_id, scenario_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    scenario = db.session.get(Scenario, scenario_id)
    if scenario is None or scenario.case_id != case.id:
        return jsonify({"error": "Scenario not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "parameters"):
        if field in data:
            setattr(scenario, field, (data[field] or "").strip())
    if "facts" in data:
        facts = data["facts"] or []
        scenario.facts_json = json.dumps(
            [{"text": str(f.get("text", ""))[:500]}
             for f in facts if isinstance(f, dict) and str(f.get("text", "")).strip()]
        ) if isinstance(facts, list) else "[]"
        # facts changed → stale analysis
        scenario.analysis_json = ""
    db.session.commit()
    return jsonify({"scenario": scenario.to_dict()})


@workspace_bp.post("/scenarios/<int:scenario_id>/analyze")
@require_auth
def analyze_scenario(case_id, scenario_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    scenario = db.session.get(Scenario, scenario_id)
    if scenario is None or scenario.case_id != case.id:
        return jsonify({"error": "Scenario not found"}), 404
    analysis = generate_scenario(build_case_context(case), scenario.to_dict())
    scenario.analysis_json = json.dumps(analysis)
    scenario.risk_level = (analysis.get("risk_level") or scenario.risk_level or "medium")
    db.session.commit()
    return jsonify({"analysis": analysis, "scenario": scenario.to_dict()})


@workspace_bp.post("/scenarios/compare")
@require_auth
def scenario_comparison(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    ids = data.get("scenario_ids") or []
    scenarios = [s for s in (db.session.get(Scenario, i) for i in ids)
                 if s is not None and s.case_id == case.id]
    if len(scenarios) < 2:
        return jsonify({"error": "Select at least two scenarios to compare"}), 400
    result = compare_scenarios(build_case_context(case), [s.to_dict() for s in scenarios])
    return jsonify(result)


@workspace_bp.delete("/scenarios/<int:scenario_id>")
@require_auth
def delete_scenario(case_id, scenario_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    scenario = db.session.get(Scenario, scenario_id)
    if scenario is None or scenario.case_id != case.id:
        return jsonify({"error": "Scenario not found"}), 404
    db.session.delete(scenario)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Negotiation
# --------------------------------------------------------------------------

@workspace_bp.get("/negotiation")
@require_auth
def get_negotiation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    prep = NegotiationPrep.query.filter_by(case_id=case.id).first()
    if prep is None:
        prep = NegotiationPrep(case_id=case.id)
        db.session.add(prep)
        db.session.commit()
    return jsonify({"prep": prep.to_dict()})


NEGOTIATION_INPUT_FIELDS = ("objective", "desired_outcome", "minimum_acceptable",
                            "key_evidence", "counterpart_position", "constraints", "channel")
NEGOTIATION_LEGACY_FIELDS = ("goals", "batna", "interests", "concessions", "red_lines",
                             "counterpart_analysis", "strategy")


def _get_or_create_prep(case_id: int) -> NegotiationPrep:
    prep = NegotiationPrep.query.filter_by(case_id=case_id).first()
    if prep is None:
        prep = NegotiationPrep(case_id=case_id)
        db.session.add(prep)
    return prep


@workspace_bp.post("/negotiation")
@require_auth
def create_negotiation(case_id):
    """Phase-9: upsert the negotiation objective inputs (spec POST)."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    prep = _get_or_create_prep(case.id)
    data = request.get_json(silent=True) or {}
    for field in NEGOTIATION_INPUT_FIELDS + NEGOTIATION_LEGACY_FIELDS:
        if field in data:
            setattr(prep, field, (data[field] or "").strip())
    db.session.commit()
    return jsonify({"prep": prep.to_dict()}), 201


@workspace_bp.put("/negotiation")
@require_auth
def update_negotiation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    prep = _get_or_create_prep(case.id)
    data = request.get_json(silent=True) or {}
    for field in NEGOTIATION_INPUT_FIELDS + NEGOTIATION_LEGACY_FIELDS:
        if field in data:
            setattr(prep, field, (data[field] or "").strip())
    db.session.commit()
    return jsonify({"prep": prep.to_dict()})


@workspace_bp.post("/negotiation/analyze")
@require_auth
def analyze_negotiation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    prep = _get_or_create_prep(case.id)
    result = analyze_negotiation_prep(build_case_context(case), prep.to_dict())
    prep.goals = "\n".join(result.get("goals") or [])
    prep.batna = result.get("batna") or ""
    prep.interests = "\n".join(result.get("interests") or [])
    prep.concessions = "\n".join(result.get("concessions") or [])
    prep.red_lines = "\n".join(result.get("red_lines") or [])
    prep.counterpart_analysis = result.get("counterpart_analysis") or ""
    prep.strategy = result.get("strategy") or ""
    plan_keys = ("opening_position", "key_arguments", "supporting_evidence",
                 "likely_objections", "responses", "potential_concessions",
                 "walk_away", "questions_to_ask")
    prep.plan_json = json.dumps({k: result.get(k) for k in plan_keys if result.get(k)})
    db.session.commit()
    return jsonify({"result": result, "prep": prep.to_dict()})


@workspace_bp.post("/negotiation/message")
@require_auth
def generate_message(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    prep = NegotiationPrep.query.filter_by(case_id=case.id).first()
    result = generate_negotiation_message(
        build_case_context(case),
        prep.to_dict() if prep else {},
        channel=(data.get("channel") or "email").strip(),
        tone=(data.get("tone") or "professional").strip(),
        focus=(data.get("focus") or "").strip(),
    )
    return jsonify(result)


@workspace_bp.post("/negotiation/practice")
@require_auth
def practice_negotiation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    messages = data.get("messages") or []
    language = (data.get("language") or "en").strip()[:16]
    result = negotiation_practice(build_case_context(case), messages, language)
    return jsonify(result)


@workspace_bp.get("/negotiation/simulation")
@require_auth
def get_simulation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    session = NegotiationSession.query.filter_by(case_id=case.id).first()
    return jsonify({"session": session.to_dict() if session else None})


@workspace_bp.post("/negotiation/simulation/start")
@require_auth
def start_simulation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    prep = NegotiationPrep.query.filter_by(case_id=case.id).first()
    position = (data.get("opponent_position") or "").strip() or (
        (prep.counterpart_position or "").strip() if prep else ""
    ) or (
        f"The other side is holding to its position and does not want to concede anything "
        f"substantial; it expects the user to justify every point with evidence."
    )
    session = NegotiationSession.query.filter_by(case_id=case.id).first()
    if session is None:
        session = NegotiationSession(case_id=case.id, user_id=g.user.id)
        db.session.add(session)
    session.user_id = g.user.id
    session.opponent_position = position[:1000]
    session.language = (data.get("language") or "en").strip()[:16]
    session.status = "active"
    session.messages_json = "[]"
    session.evaluation_json = ""
    db.session.commit()
    return jsonify({"session": session.to_dict()})


@workspace_bp.post("/negotiation/simulation/reply")
@require_auth
def simulation_reply_route(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    session = NegotiationSession.query.filter_by(case_id=case.id).first()
    if session is None or session.status != "active":
        return jsonify({"error": "No active simulation — start one first"}), 400
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "A message is required"}), 400
    if data.get("language"):
        session.language = (data["language"] or "en").strip()[:16]
    try:
        messages = json.loads(session.messages_json or "[]")
    except (ValueError, TypeError):
        messages = []
    messages.append({"role": "user", "content": message[:2000]})
    result = simulation_reply(build_case_context(case), messages, session.opponent_position,
                              session.language)
    messages.append({"role": "assistant", "content": (result.get("reply") or ""),
                     "label": result.get("label"), "note": result.get("note")})
    session.messages_json = json.dumps(messages)
    db.session.commit()
    return jsonify({"session": session.to_dict(), "reply": result})


@workspace_bp.post("/negotiation/simulation/evaluate")
@require_auth
def evaluate_simulation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    session = NegotiationSession.query.filter_by(case_id=case.id).first()
    if session is None:
        return jsonify({"error": "No simulation found"}), 404
    try:
        messages = json.loads(session.messages_json or "[]")
    except (ValueError, TypeError):
        messages = []
    if not messages:
        return jsonify({"error": "Nothing to evaluate — the conversation is empty"}), 400
    evaluation = evaluate_negotiation(build_case_context(case), messages,
                                      session.opponent_position)
    session.evaluation_json = json.dumps(evaluation)
    session.status = "completed"
    db.session.commit()
    return jsonify({"session": session.to_dict()})


@workspace_bp.post("/negotiation/simulation/reset")
@require_auth
def reset_simulation(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    session = NegotiationSession.query.filter_by(case_id=case.id).first()
    if session is None:
        session = NegotiationSession(case_id=case.id, user_id=g.user.id)
        db.session.add(session)
    session.status = "active"
    session.messages_json = "[]"
    session.evaluation_json = ""
    db.session.commit()
    return jsonify({"session": session.to_dict()})


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------

@workspace_bp.get("/evidence")
@require_auth
def list_evidence(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    items = case.evidence.order_by(EvidenceItem.created_at.desc()).all()
    return jsonify({"evidence": [e.to_dict() for e in items]})


@workspace_bp.post("/evidence")
@require_auth
def add_evidence(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "A title is required"}), 400
    item = EvidenceItem(
        case_id=case.id, title=title[:255],
        description=(data.get("description") or "").strip(),
        item_type=(data.get("item_type") or "document").strip(),
        source=(data.get("source") or "").strip(),
        date=_parse_date(data.get("date")),
        importance=(data.get("importance") or "medium").strip(),
        verification=(data.get("verification") or "unverified").strip(),
        status=(data.get("status") or "copy").strip(),
        notes=(data.get("notes") or "").strip(),
        provenance=(data.get("provenance") or "user").strip(),
    )
    if data.get("related_issue_ids") and isinstance(data["related_issue_ids"], list):
        ids = {int(x) for x in data["related_issue_ids"] if str(x).lstrip("-").isdigit()}
        if ids:
            item.issues = (LegalIssue.query
                           .filter(LegalIssue.id.in_(ids), LegalIssue.case_id == case.id)
                           .all())
    db.session.add(item)
    db.session.commit()
    return jsonify({"item": item.to_dict()}), 201


@workspace_bp.patch("/evidence/<int:item_id>")
@require_auth
def update_evidence(case_id, item_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    item = db.session.get(EvidenceItem, item_id)
    if item is None or item.case_id != case.id:
        return jsonify({"error": "Evidence item not found"}), 404
    data = request.get_json(silent=True) or {}
    _apply_evidence_patch(item, data, case=case)
    db.session.commit()
    return jsonify({"item": item.to_dict()})


@workspace_bp.delete("/evidence/<int:item_id>")
@require_auth
def delete_evidence(case_id, item_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    item = db.session.get(EvidenceItem, item_id)
    if item is None or item.case_id != case.id:
        return jsonify({"error": "Evidence item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------
# Action plan
# --------------------------------------------------------------------------

@workspace_bp.get("/actions")
@require_auth
def list_actions(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    actions = case.actions.order_by(ActionItem.due_date.asc().nulls_last(),
                                   ActionItem.created_at.desc()).all()
    return jsonify({"actions": [a.to_dict() for a in actions]})


@workspace_bp.post("/actions")
@require_auth
def add_action(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "An action title is required"}), 400
    action = ActionItem(
        case_id=case.id, title=title[:255],
        description=(data.get("description") or "").strip(),
        priority=(data.get("priority") or "medium").strip(),
        reason=(data.get("reason") or "").strip(),
        related_issue=(data.get("related_issue") or "").strip()[:500],
        required_evidence=(data.get("required_evidence") or "").strip(),
        due_date=_parse_date(data.get("due_date")),
        status=(data.get("status") or "not_started").strip(),
        category=(data.get("category") or "").strip(),
    )
    db.session.add(action)
    db.session.commit()
    return jsonify({"action": action.to_dict()}), 201


@workspace_bp.patch("/actions/<int:action_id>")
@require_auth
def update_action(case_id, action_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    action = db.session.get(ActionItem, action_id)
    if action is None or action.case_id != case.id:
        return jsonify({"error": "Action not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "priority", "status", "category",
                  "reason", "related_issue", "required_evidence"):
        if field in data:
            setattr(action, field, (data[field] or "").strip())
    if "due_date" in data:
        action.due_date = _parse_date(data.get("due_date"))
    db.session.commit()
    return jsonify({"action": action.to_dict()})


@workspace_bp.delete("/actions/<int:action_id>")
@require_auth
def delete_action(case_id, action_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    action = db.session.get(ActionItem, action_id)
    if action is None or action.case_id != case.id:
        return jsonify({"error": "Action not found"}), 404
    db.session.delete(action)
    db.session.commit()
    return jsonify({"ok": True})


@workspace_bp.get("/action-plan")
@require_auth
def list_action_plan(case_id):
    """Phase-11 spec alias of GET /actions."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    actions = case.actions.order_by(ActionItem.due_date.asc().nulls_last(),
                                   ActionItem.created_at.desc()).all()
    return jsonify({"actions": [a.to_dict() for a in actions]})


@workspace_bp.post("/action-plan")
@require_auth
def create_action_plan_item(case_id):
    """Phase-11 spec alias of POST /actions."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "An action title is required"}), 400
    action = ActionItem(
        case_id=case.id, title=title[:255],
        description=(data.get("description") or "").strip(),
        priority=(data.get("priority") or "medium").strip(),
        reason=(data.get("reason") or "").strip(),
        related_issue=(data.get("related_issue") or "").strip()[:500],
        required_evidence=(data.get("required_evidence") or "").strip(),
        due_date=_parse_date(data.get("due_date")),
        status=(data.get("status") or "not_started").strip(),
        category=(data.get("category") or "").strip(),
    )
    db.session.add(action)
    db.session.commit()
    return jsonify({"action": action.to_dict()}), 201


@workspace_bp.post("/action-plan/generate")
@require_auth
def generate_action_plan_route(case_id):
    """AI action plan grounded in the case record — never generic tasks."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    result = generate_action_plan(build_case_context(case))
    existing = {a.title.strip().lower() for a in case.actions.all()}
    added, skipped = [], 0
    for act in result.get("actions") or []:
        title = (act.get("title") or "").strip()[:255]
        if not title or title.lower() in existing:
            skipped += 1
            continue
        existing.add(title.lower())
        row = ActionItem(
            case_id=case.id, title=title,
            description=(act.get("description") or "").strip(),
            priority=(act.get("priority") or "medium").strip(),
            reason=(act.get("reason") or "").strip(),
            related_issue=(act.get("related_issue") or "").strip()[:500],
            required_evidence=(act.get("required_evidence") or "").strip(),
            due_date=_parse_date(act.get("due_date")),
            category="ai_plan",
        )
        db.session.add(row)
        added.append(row)
    db.session.commit()
    result["added_actions"] = [a.to_dict() for a in added]
    result["duplicates_skipped"] = skipped
    return jsonify(result)


# --------------------------------------------------------------------------
# Deadlines
# --------------------------------------------------------------------------

@workspace_bp.get("/deadlines")
@require_auth
def list_deadlines(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    deadlines = case.deadlines.order_by(Deadline.due_date.asc()).all()
    return jsonify({"deadlines": [d.to_dict() for d in deadlines]})


@workspace_bp.post("/deadlines")
@require_auth
def add_deadline(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    due = _parse_date(data.get("due_date"))
    if not title or due is None:
        return jsonify({"error": "A title and a valid due date are required"}), 400
    deadline = Deadline(
        case_id=case.id, title=title[:255],
        description=(data.get("description") or "").strip(),
        due_date=due,
        status=(data.get("status") or "pending").strip(),
        source=(data.get("source") or "user").strip(),
    )
    db.session.add(deadline)
    db.session.commit()
    return jsonify({"deadline": deadline.to_dict()}), 201


@workspace_bp.patch("/deadlines/<int:deadline_id>")
@require_auth
def update_deadline(case_id, deadline_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    deadline = db.session.get(Deadline, deadline_id)
    if deadline is None or deadline.case_id != case.id:
        return jsonify({"error": "Deadline not found"}), 404
    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "status"):
        if field in data:
            setattr(deadline, field, (data[field] or "").strip())
    if "due_date" in data:
        parsed = _parse_date(data.get("due_date"))
        if parsed:
            deadline.due_date = parsed
    db.session.commit()
    return jsonify({"deadline": deadline.to_dict()})


@workspace_bp.delete("/deadlines/<int:deadline_id>")
@require_auth
def delete_deadline(case_id, deadline_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    deadline = db.session.get(Deadline, deadline_id)
    if deadline is None or deadline.case_id != case.id:
        return jsonify({"error": "Deadline not found"}), 404
    db.session.delete(deadline)
    db.session.commit()
    return jsonify({"ok": True})


@workspace_bp.post("/deadlines/extract")
@require_auth
def extract_deadlines(case_id):
    """AI date extraction — review-only candidates; nothing is stored until the
    user accepts. Never asserts legally binding deadlines without jurisdiction
    support."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    result = extract_deadline_dates(build_case_context(case))
    return jsonify(result)


# --------------------------------------------------------------------------
# CaseGuide assistant chat (per-case session, never mixed)
# --------------------------------------------------------------------------

def _get_or_create_session(case) -> ChatSession:
    """One CaseGuide session per case. Messages are scoped to case + owner."""
    session = ChatSession.query.filter_by(case_id=case.id).first()
    if session is None:
        session = ChatSession(user_id=case.user_id, case_id=case.id,
                              title="CaseGuide conversation")
        db.session.add(session)
        db.session.commit()
    return session


@workspace_bp.get("/messages")
@require_auth
def list_messages(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    session = _get_or_create_session(case)
    messages = case.messages.order_by(ChatMessage.created_at.asc()).all()
    return jsonify({"messages": [m.to_dict() for m in messages],
                    "session": session.to_dict()})


@workspace_bp.post("/chat")
@require_auth
def chat(case_id):
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    language = (data.get("language") or "en").strip()[:16]
    if not user_message:
        return jsonify({"error": "A message is required"}), 400

    session = _get_or_create_session(case)
    if not session.title or session.title == "CaseGuide conversation":
        session.title = user_message[:60] + ("…" if len(user_message) > 60 else "")

    user_msg = ChatMessage(case_id=case.id, session_id=session.id, role="user",
                           content=user_message[:4000], language=language)
    db.session.add(user_msg)
    db.session.commit()

    history = [{"role": m.role, "content": m.content}
               for m in case.messages.order_by(ChatMessage.created_at.asc()).all()[-16:]]
    result = answer_case_question(build_case_context(case), history, user_message, language)

    answer = (result.get("answer") or result.get("reply") or "").strip()
    if not answer:
        answer = "I wasn't able to generate a response. Please try rephrasing your question."
    structured = {
        "answer": answer[:8000],
        "why_this_matters": result.get("why_this_matters") or "",
        "evidence_needed": result.get("evidence_needed") or [],
        "potential_risk": result.get("potential_risk") or "",
        "next_question": result.get("next_question") or "",
        "recommended_next_step": result.get("recommended_next_step") or "",
        "follow_up_suggestions": result.get("follow_up_suggestions") or [],
        "sources": result.get("sources") or [],
        "labels": result.get("labels") or [],
        "mode": result.get("mode", "demo"),
        "note": result.get("note") or "",
    }
    assistant_msg = ChatMessage(
        case_id=case.id, session_id=session.id, role="assistant",
        content=answer[:8000],
        provenance=json.dumps({"mode": result.get("mode", "demo"),
                               "labels": structured["labels"],
                               "note": result.get("note") or ""}),
        meta=json.dumps(structured),
        language=language,
    )
    db.session.add(assistant_msg)
    db.session.commit()
    return jsonify({"user_message": user_message,
                    "session": session.to_dict(),
                    "assistant": assistant_msg.to_dict(),
                    "result": result}), 201


@workspace_bp.post("/explain-simply")
@require_auth
def explain_simply_route(case_id):
    """Phase 12 — Explain Simply: rewrite legal text in plain language while
    preserving the legal meaning (language-aware)."""
    case, err = _case_or_404(case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Some legal text is required"}), 400
    language = (data.get("language") or g.user.language or "en").strip()[:16]
    result = explain_simply(build_case_context(case), text, language)
    return jsonify({**result, "case_id": case.id})


# --------------------------------------------------------------------------
# Shared small helpers (used by other blueprints)
# --------------------------------------------------------------------------

def serialize_deadline(d: Deadline) -> dict:
    today = date.today()
    return {
        "id": d.id,
        "title": d.title,
        "description": d.description or "",
        "due_date": d.due_date.isoformat(),
        "days_left": (d.due_date - today).days,
        "status": d.status,
        "source": d.source,
        "case_id": d.case_id,
    }

# --------------------------------------------------------------------------
# Top-level aliases (Phase 6): PUT /api/timeline/<id>, PUT/DELETE /api/evidence/<id>
# --------------------------------------------------------------------------
# Case-scoped PATCH/DELETE live above; these mirror the spec's direct routes.
# Ownership is enforced the same way (case must belong to g.user).

timeline_direct_bp = Blueprint("timeline_direct", __name__,
                               url_prefix="/api/timeline/<int:event_id>")


@timeline_direct_bp.put("")
@timeline_direct_bp.patch("")
@require_auth
def put_timeline_event(event_id):
    event = db.session.get(TimelineEvent, event_id)
    if event is None:
        return jsonify({"error": "Event not found"}), 404
    case, err = _case_or_404(event.case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    _apply_timeline_patch(event, data)
    db.session.commit()
    return jsonify({"event": event.to_dict()})


@timeline_direct_bp.delete("")
@require_auth
def delete_timeline_direct(event_id):
    event = db.session.get(TimelineEvent, event_id)
    if event is None:
        return jsonify({"error": "Event not found"}), 404
    case, err = _case_or_404(event.case_id)
    if err:
        return err
    db.session.delete(event)
    db.session.commit()
    return jsonify({"ok": True})


evidence_direct_bp = Blueprint("evidence_direct", __name__,
                               url_prefix="/api/evidence/<int:item_id>")


@evidence_direct_bp.put("")
@evidence_direct_bp.patch("")
@require_auth
def put_evidence_item(item_id):
    item = db.session.get(EvidenceItem, item_id)
    if item is None:
        return jsonify({"error": "Evidence item not found"}), 404
    case, err = _case_or_404(item.case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    _apply_evidence_patch(item, data, case=case)
    db.session.commit()
    return jsonify({"item": item.to_dict()})


@evidence_direct_bp.delete("")
@require_auth
def delete_evidence_direct(item_id):
    item = db.session.get(EvidenceItem, item_id)
    if item is None:
        return jsonify({"error": "Evidence item not found"}), 404
    case, err = _case_or_404(item.case_id)
    if err:
        return err
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


action_items_direct_bp = Blueprint("action_items_direct", __name__,
                                   url_prefix="/api/action-items/<int:action_id>")


@action_items_direct_bp.put("")
@action_items_direct_bp.patch("")
@require_auth
def put_action_item_direct(action_id):
    action = db.session.get(ActionItem, action_id)
    if action is None:
        return jsonify({"error": "Action not found"}), 404
    case, err = _case_or_404(action.case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("title", "description", "priority", "status", "category",
                  "reason", "related_issue", "required_evidence"):
        if field in data:
            setattr(action, field, (data[field] or "").strip())
    if "due_date" in data:
        action.due_date = _parse_date(data.get("due_date"))
    db.session.commit()
    return jsonify({"action": action.to_dict()})


scenarios_direct_bp = Blueprint("scenarios_direct", __name__,
                                url_prefix="/api/scenarios/<int:scenario_id>")


@scenarios_direct_bp.put("")
@scenarios_direct_bp.patch("")
@require_auth
def put_scenario_direct(scenario_id):
    scenario = db.session.get(Scenario, scenario_id)
    if scenario is None:
        return jsonify({"error": "Scenario not found"}), 404
    case, err = _case_or_404(scenario.case_id)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    for field in ("name", "description", "parameters"):
        if field in data:
            setattr(scenario, field, (data[field] or "").strip())
    if "facts" in data:
        facts = data["facts"] or []
        scenario.facts_json = json.dumps(
            [{"text": str(f.get("text", ""))[:500]}
             for f in facts if isinstance(f, dict) and str(f.get("text", "")).strip()]
        ) if isinstance(facts, list) else "[]"
        scenario.analysis_json = ""
    db.session.commit()
    return jsonify({"scenario": scenario.to_dict()})


@scenarios_direct_bp.delete("")
@require_auth
def delete_scenario_direct(scenario_id):
    scenario = db.session.get(Scenario, scenario_id)
    if scenario is None:
        return jsonify({"error": "Scenario not found"}), 404
    case, err = _case_or_404(scenario.case_id)
    if err:
        return err
    db.session.delete(scenario)
    db.session.commit()
    return jsonify({"ok": True})
