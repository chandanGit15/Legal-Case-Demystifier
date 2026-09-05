"""Authentication helpers: password hashing, JWT issuance/verification,
and the require_auth guard used by every protected route."""
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, request

from config import JWT_EXPIRES_HOURS, JWT_SECRET
from models import User


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return {"error": "Authentication required"}, 401
        token = header[len("Bearer "):]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            user = User.query.get(int(payload["sub"]))
        except (jwt.InvalidTokenError, KeyError, TypeError):
            return {"error": "Invalid or expired token"}, 401
        if user is None:
            return {"error": "Account not found"}, 401
        g.user = user
        return fn(*args, **kwargs)
    return wrapper