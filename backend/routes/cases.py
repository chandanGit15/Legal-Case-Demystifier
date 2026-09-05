"""Case management routes — thin handlers over the case service."""
from flask import Blueprint, g, jsonify, request

from services import case_service
from utils.auth import require_auth
from utils.http import error

cases_bp = Blueprint("cases", __name__, url_prefix="/api")


@cases_bp.get("/dashboard/summary")
@require_auth
def dashboard_summary():
    return jsonify(case_service.dashboard_summary(g.user.id))


@cases_bp.get("/cases")
@require_auth
def list_cases():
    return jsonify({"cases": [c.to_dict() for c in case_service.list_cases(g.user.id)]})


@cases_bp.post("/cases")
@require_auth
def create_case():
    try:
        case = case_service.create_case(g.user.id, request.get_json(silent=True) or {})
    except case_service.CaseError as exc:
        return error(exc.message, exc.status)
    return jsonify({"case": case.to_dict()}), 201


@cases_bp.get("/cases/<int:case_id>")
@require_auth
def get_case(case_id):
    try:
        case = case_service.get_owned_case(g.user.id, case_id)
    except case_service.CaseError as exc:
        return error(exc.message, exc.status)
    return jsonify({"case": case.to_dict()})


@cases_bp.get("/cases/<int:case_id>/context")
@require_auth
def get_case_context(case_id):
    try:
        context = case_service.get_case_context(g.user.id, case_id)
    except case_service.CaseError as exc:
        return error(exc.message, exc.status)
    return jsonify(context)


@cases_bp.patch("/cases/<int:case_id>")
@require_auth
def update_case(case_id):
    try:
        case = case_service.update_case(g.user.id, case_id, request.get_json(silent=True) or {})
    except case_service.CaseError as exc:
        return error(exc.message, exc.status)
    return jsonify({"case": case.to_dict()})


@cases_bp.delete("/cases/<int:case_id>")
@require_auth
def delete_case(case_id):
    try:
        case_service.delete_case(g.user.id, case_id)
    except case_service.CaseError as exc:
        return error(exc.message, exc.status)
    return jsonify({"ok": True})
