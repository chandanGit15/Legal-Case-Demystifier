"""User settings routes."""
import config
from flask import Blueprint, g, jsonify, request

from ai import ai_available
from services import auth_service
from utils.auth import require_auth
from utils.http import error

settings_bp = Blueprint("settings", __name__, url_prefix="/api/settings")


@settings_bp.get("")
@require_auth
def get_settings():
    return jsonify({"settings": g.user.to_dict()})


@settings_bp.put("")
@require_auth
def update_settings():
    try:
        settings = auth_service.update_profile(g.user, request.get_json(silent=True) or {})
    except auth_service.AuthError as exc:
        return error(exc.message, exc.status)
    return jsonify({"settings": settings})


@settings_bp.get("/ai-status")
@require_auth
def ai_status():
    return jsonify({
        "configured": ai_available(),
        "demo_mode": not ai_available(),
        "model": config.GEMINI_MODEL,
    })