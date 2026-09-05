"""Authentication routes — thin handlers over the auth service."""
from flask import Blueprint, g, jsonify, request

import config
from services import auth_service
from utils.auth import require_auth
from utils.http import error
from utils.ratelimit import rate_limit

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
@rate_limit(config.RATE_LIMIT_AUTH_PER_HOUR, "auth.register")
def register():
    try:
        return jsonify(auth_service.register(request.get_json(silent=True) or {})), 201
    except auth_service.AuthError as exc:
        return error(exc.message, exc.status)


@auth_bp.post("/login")
@rate_limit(config.RATE_LIMIT_AUTH_PER_HOUR, "auth.login")
def login():
    try:
        return jsonify(auth_service.login(request.get_json(silent=True) or {}))
    except auth_service.AuthError as exc:
        return error(exc.message, exc.status)


@auth_bp.get("/me")
@require_auth
def me():
    return jsonify({"user": g.user.to_dict()})