"""Small HTTP helpers for consistent JSON responses."""
from flask import jsonify


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def ok(**payload):
    return jsonify({**payload, "ok": True})