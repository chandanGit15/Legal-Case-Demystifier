"""Phase 13 — Demo-case routes.

- GET  /api/demo-catalog : public, FICTIONAL metadata for the picker.
- POST /api/demo/session  : one-click "Explore Demo Case" for logged-out
  visitors — reuses a shared fictional demo account, creates the chosen demo
  case on first visit, and returns a session (token + user + case).
- POST /api/demo-case    : (authed) create a demo case under the caller's
  account; optional {"kind": ...}.
"""
import secrets

import config
from flask import Blueprint, g, jsonify, request

from app.extensions import db
from models import Case, User
from services import auth_service, case_service
from services.demo_catalog import (DEMO_ACCOUNT_EMAIL, DEMO_ACCOUNT_NAME,
                                   DEMO_CATALOG)
from utils.auth import require_auth
from utils.http import error
from utils.ratelimit import rate_limit

demo_bp = Blueprint("demo", __name__, url_prefix="/api")

_SUPPORTED = {d["kind"] for d in DEMO_CATALOG}


def _kind():
    return ((request.get_json(silent=True) or {}).get("kind") or "rental")


@demo_bp.get("/demo-catalog")
def demo_catalog():
    """Public picker metadata — fictional only, no user data."""
    return jsonify({"demos": case_service.list_demo_catalog(),
                    "note": "All demo cases and their contents are fictional."})


@demo_bp.post("/demo/session")
@rate_limit(config.RATE_LIMIT_DEMO_PER_HOUR, "demo.session")
def demo_session():
    """One-click explore: shared fictional account + chosen demo case."""
    kind = _kind()
    if kind not in _SUPPORTED:
        return error("Unknown demo case", 400)

    account = User.query.filter_by(email=DEMO_ACCOUNT_EMAIL).first()
    if account is None:
        account = User(email=DEMO_ACCOUNT_EMAIL, name=DEMO_ACCOUNT_NAME)
        account.set_password(secrets.token_urlsafe(24))
        account.language = "en"
        db.session.add(account)
        db.session.commit()

    # Reuse the demo case of this kind if one already exists for the account.
    case = (Case.query.filter_by(user_id=account.id, is_demo=True)
            .order_by(Case.id.asc()).all())
    target = next((c for c in case if c.title == _title_for(kind)), None)
    if target is None:
        target = case_service.create_demo_case(account.id, kind=kind)

    payload = auth_service._session_payload(account)
    return jsonify({**payload, "case": target.to_dict()}), 200


def _title_for(kind: str) -> str:
    for d in DEMO_CATALOG:
        if d["kind"] == kind:
            return d["title"]
    return kind


@demo_bp.post("/demo-case")
@require_auth
@rate_limit(config.RATE_LIMIT_DEMO_PER_HOUR, "demo.case")
def create_demo_case_route():
    kind = _kind()
    if kind not in _SUPPORTED:
        return error("Unknown demo case", 400)
    case = case_service.create_demo_case(g.user.id, kind=kind)
    return jsonify({"case": case.to_dict()}), 201
