"""Flask application factory for Legal Case Demystifier."""
import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import config
from app.extensions import db
from routes.ai import ai_bp
from routes.auth import auth_bp
from routes.cases import cases_bp
from routes.demo import demo_bp
from routes.documents import document_direct_bp, documents_bp
from routes.settings import settings_bp
from routes.workspace import (action_items_direct_bp, evidence_direct_bp,
                              scenarios_direct_bp, timeline_direct_bp,
                              workspace_bp)
from utils.db import run_migrations

# Friendly, non-technical copy for HTTP-level failures. Werkzeug descriptions
# are never sent to clients.
_HTTP_MESSAGES = {
    400: "The request could not be processed. Check the details and try again.",
    403: "You don't have permission to do that.",
    404: "Not found.",
    405: "That method is not allowed here.",
    406: "The request is not acceptable.",
    408: "The request timed out.",
    409: "The request conflicts with the current state.",
    410: "That resource is no longer available.",
    411: "A content length is required.",
    413: f"The upload exceeds the {config.MAX_UPLOAD_MB} MB limit.",
    414: "The request is too large.",
    415: "Unsupported content type.",
    422: "The request could not be validated.",
    429: "Too many requests. Please wait a while and try again.",
    500: "Something went wrong on our side. Please try again.",
    502: "The upstream service is unavailable. Please try again.",
    503: "The service is temporarily unavailable. Please try again.",
    504: "The upstream service timed out. Please try again.",
}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
    app.config["JSON_SORT_KEYS"] = False
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = False

    if config.JWT_SECRET == config.DEV_JWT_SECRET:
        app.logger.warning(
            "JWT_SECRET is set to the insecure development default. "
            "Set JWT_SECRET in the backend environment before deploying.")

    # Tokens travel in Authorization headers (never cookies), so cross-origin
    # calls need no credentials — origins are restricted to the configured set.
    CORS(app, resources={
        r"/api/*": {"origins": config.CORS_ORIGINS or ["http://localhost:5173"]},
    })

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(document_direct_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(timeline_direct_bp)
    app.register_blueprint(evidence_direct_bp)
    app.register_blueprint(scenarios_direct_bp)
    app.register_blueprint(action_items_direct_bp)
    app.register_blueprint(demo_bp)

    with app.app_context():
        db.create_all()
        run_migrations()
        from services import case_service
        case_service.migrate_jurisdiction_to_india()

    @app.after_request
    def security_headers(response):
        # API responses carry case data — never store them in shared caches.
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()")
        return response

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "legal-case-demystifier"})

    @app.get("/api/ai/status")
    def ai_status():
        return jsonify({
            "configured": bool(config.GEMINI_API_KEY),
            "demo_mode": not config.GEMINI_API_KEY,
        })

    @app.errorhandler(HTTPException)
    def http_error(e):
        # Structured JSON for every HTTP-level failure (405, 415, 429, ...).
        # Explicit handlers below take precedence where one exists.
        message = _HTTP_MESSAGES.get(e.code, "The request could not be completed.")
        if e.code == 429:
            response = jsonify({"error": message})
            response.status_code = 429
            retry = e.response.headers.get("Retry-After") if e.response else None
            if retry:
                response.headers["Retry-After"] = retry
            return response
        return jsonify({"error": message}), e.code

    @app.errorhandler(413)
    def too_large(_e):
        return jsonify({"error": _HTTP_MESSAGES[413]}), 413

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": _HTTP_MESSAGES[404]}), 404

    @app.errorhandler(500)
    def server_error(e):
        # Full traceback stays in the server log; the client only ever sees a
        # generic message — no stack traces or internals are exposed.
        app.logger.exception(e)
        return jsonify({"error": _HTTP_MESSAGES[500]}), 500

    @app.errorhandler(Exception)
    def unhandled_error(e):
        # Final safety net: any uncaught exception becomes a clean 500 JSON
        # response. Detailed logging happens server-side only.
        if isinstance(e, HTTPException):
            return http_error(e)
        app.logger.exception(e)
        return jsonify({"error": _HTTP_MESSAGES[500]}), 500

    return app