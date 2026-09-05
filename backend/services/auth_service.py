"""Authentication business logic — routes stay thin and delegate here."""
import config
from app.extensions import db
from utils.india import (INDIAN_STATES_UTS, JURISDICTION_COUNTRY)
from models import User
from schemas import (AuthRegisterSchema, MAX_NAME_LEN, SchemaError,
                    normalize_email)
from utils.auth import create_token


class AuthError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def register(data: dict) -> dict:
    try:
        schema = AuthRegisterSchema(data).validate()
    except SchemaError as exc:
        raise AuthError(str(exc)) from exc
    if User.query.filter_by(email=schema.email).first():
        raise AuthError("An account with this email already exists", 409)
    user = User(email=schema.email, name=schema.name)
    user.set_password(schema.password)
    db.session.add(user)
    db.session.commit()
    return _session_payload(user)


def login(data: dict) -> dict:
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    try:
        email = normalize_email(email)
    except SchemaError:
        raise AuthError("Invalid email or password", 401) from None
    user = User.query.filter_by(email=email).first()
    # Same message whether the account is missing or the password is wrong,
    # so the endpoint cannot be used to enumerate registered addresses.
    if user is None or not user.check_password(password):
        raise AuthError("Invalid email or password", 401)
    return _session_payload(user)


def update_profile(user: User, data: dict) -> dict:
    try:
        if "name" in data and (data["name"] or "").strip():
            name = (data["name"] or "").strip()
            if len(name) > MAX_NAME_LEN:
                raise AuthError("Name is too long")
            user.name = name
        if "email" in data and (data["email"] or "").strip():
            new_email = normalize_email(data["email"])
            existing = User.query.filter(User.email == new_email, User.id != user.id).first()
            if existing:
                raise AuthError("An account with this email already exists", 409)
            user.email = new_email
        # India-only: the default country is never editable; the default
        # state/UT must be an Indian state or union territory.
        if "default_country" in data or user.default_country != JURISDICTION_COUNTRY:
            user.default_country = JURISDICTION_COUNTRY
        if "default_state" in data:
            state = (data["default_state"] or "").strip()[:120]
            if state and state not in INDIAN_STATES_UTS:
                raise AuthError("Select a valid Indian state or union territory.")
            user.default_state = state
        if "language" in data and (data["language"] or "").strip():
            lang = (data["language"] or "").strip().lower()
            user.language = lang if lang in config.SUPPORTED_LANGUAGES else "en"
    except SchemaError as exc:
        raise AuthError(str(exc)) from exc
    db.session.commit()
    return user.to_dict()


def _session_payload(user: User) -> dict:
    return {"user": user.to_dict(), "token": create_token(user.id)}