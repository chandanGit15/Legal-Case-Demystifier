"""Document routes — thin handlers over the document service.

Two route families:
  * /api/cases/<case_id>/documents/...   (workspace-scoped, used by the UI)
  * /api/documents/<doc_id>/...          (document-id aliases per API spec)
Both enforce ownership; a document is always tied to a Case ID.
"""
from flask import Blueprint, g, jsonify, request

from services import case_service, document_service
from utils.auth import require_auth
from utils.http import error

documents_bp = Blueprint("documents", __name__, url_prefix="/api/cases/<int:case_id>/documents")
document_direct_bp = Blueprint("documents_direct", __name__, url_prefix="/api/documents/<int:doc_id>")


def _case_or_error(case_id):
    try:
        return case_service.get_owned_case(g.user.id, case_id), None
    except case_service.CaseError as exc:
        return None, error(exc.message, exc.status)


# --------------------------------------------------------------------------
# Case-scoped routes
# --------------------------------------------------------------------------

@documents_bp.get("")
@require_auth
def list_documents(case_id):
    case, err = _case_or_error(case_id)
    if err:
        return err
    return jsonify({"documents": [d.to_dict() for d in document_service.list_documents(case)]})


@documents_bp.post("")
@require_auth
def upload_document(case_id):
    case, err = _case_or_error(case_id)
    if err:
        return err
    try:
        doc = document_service.upload(case, request.files.get("file"))
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"document": doc.to_dict()}), 201


@documents_bp.get("/<int:doc_id>")
@require_auth
def get_document(case_id, doc_id):
    case, err = _case_or_error(case_id)
    if err:
        return err
    try:
        doc = document_service.get_document(case, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"document": doc.to_dict()})


@documents_bp.get("/<int:doc_id>/content")
@require_auth
def get_document_content(case_id, doc_id):
    case, err = _case_or_error(case_id)
    if err:
        return err
    try:
        doc = document_service.get_document(case, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify(document_service.get_content(doc))


@documents_bp.delete("/<int:doc_id>")
@require_auth
def delete_document(case_id, doc_id):
    case, err = _case_or_error(case_id)
    if err:
        return err
    try:
        document_service.delete(case, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"ok": True})


@documents_bp.post("/<int:doc_id>/analyze")
@require_auth
def analyze_document(case_id, doc_id):
    case, err = _case_or_error(case_id)
    if err:
        return err
    try:
        analysis = document_service.analyze(case, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"analysis": analysis})


@documents_bp.post("/<int:doc_id>/import")
@require_auth
def import_finding(case_id, doc_id):
    """Connect one analyzed finding into the case (user-initiated import)."""
    case, err = _case_or_error(case_id)
    if err:
        return err
    try:
        doc = document_service.get_document(case, doc_id)
        body = request.get_json(silent=True) or {}
        result = document_service.import_finding(
            case, doc, (body.get("kind") or "").strip(), body.get("data") or {})
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify(result), 201


# --------------------------------------------------------------------------
# Document-id aliases (spec routes)
# --------------------------------------------------------------------------

@document_direct_bp.get("")
@require_auth
def get_document_by_id(doc_id):
    try:
        _case, doc = document_service.get_owned_document(g.user.id, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"document": doc.to_dict()})


@document_direct_bp.get("/content")
@require_auth
def get_content_by_id(doc_id):
    try:
        _case, doc = document_service.get_owned_document(g.user.id, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify(document_service.get_content(doc))


@document_direct_bp.delete("")
@require_auth
def delete_document_by_id(doc_id):
    try:
        document_service.delete_owned(g.user.id, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"ok": True})


@document_direct_bp.post("/analyze")
@require_auth
def analyze_document_by_id(doc_id):
    try:
        analysis = document_service.analyze_owned(g.user.id, doc_id)
    except document_service.DocumentError as exc:
        return error(exc.message, exc.status)
    return jsonify({"analysis": analysis})
