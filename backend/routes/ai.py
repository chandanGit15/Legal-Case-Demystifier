"""Standalone AI endpoints that do not require a specific case:
legal term explainer and multilingual plain-language explanation."""
from flask import Blueprint, g, jsonify, request

from ai import build_case_context, explain_simply, explain_term
from models import Case
from utils.auth import require_auth
from utils.http import error

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.post("/explain-term")
@require_auth
def explain_term_route():
    data = request.get_json(silent=True) or {}
    term = (data.get("term") or "").strip()
    if not term:
        return error("A term is required")
    language = (data.get("language") or g.user.language or "en").strip()[:16]
    jurisdiction = (data.get("jurisdiction") or
                    ", ".join(p for p in (g.user.default_country, g.user.default_state) if p)).strip()
    mode = (data.get("mode") or "beginner").strip()[:16]
    return jsonify(explain_term(term[:200], language=language, jurisdiction=jurisdiction, mode=mode))


@ai_bp.post("/explain-case")
@require_auth
def explain_case():
    """Plain-language, multilingual summary of a case (no citation invention)."""
    data = request.get_json(silent=True) or {}
    case_id = data.get("case_id")
    language = (data.get("language") or g.user.language or "en").strip()[:16]
    case = Case.query.filter_by(id=case_id, user_id=g.user.id).first()
    if case is None:
        return error("Case not found", 404)
    result = explain_term(f"the situation in '{case.title}'",
                          language=language,
                          jurisdiction=case.jurisdiction or "")
    return jsonify({**result, "case_id": case.id})