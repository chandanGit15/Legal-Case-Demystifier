"""Lightweight request schemas. (A full validation library can replace
these later without touching routes.)"""
import re

from utils.india import (INDIAN_STATES_UTS, JURISDICTION_COUNTRY,
                         jurisdiction_string)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAX_NAME_LEN = 120
MAX_EMAIL_LEN = 254
MAX_PASSWORD_LEN = 200
MAX_CASE_TITLE_LEN = 255


def _validate_indian_state(state: str) -> str:
    """Trim a state/UT value and reject anything outside the Indian lists."""
    state = (state or "").strip()
    if state and state not in INDIAN_STATES_UTS:
        raise SchemaError(
            "Select a valid Indian state or union territory.")
    return state


class SchemaError(ValueError):
    pass


def normalize_email(value) -> str:
    """Lowercase + strip an email, rejecting clearly malformed addresses."""
    email = (value or "").strip().lower()
    if len(email) > MAX_EMAIL_LEN or not _EMAIL_RE.match(email):
        raise SchemaError("Enter a valid email address")
    return email


class CaseCreateSchema:
    """Fields for POST /api/cases. Country is fixed to India; the client's
    value is ignored so every case is born in the Indian jurisdiction."""
    FIELDS = ("title", "case_type", "description", "parties", "country", "state", "stage", "status")

    def __init__(self, data: dict):
        self.data = data or {}
        self.title = (self.data.get("title") or "").strip()
        self.case_type = (self.data.get("case_type") or "").strip()
        self.description = (self.data.get("description") or "").strip()
        self.parties = (self.data.get("parties") or "").strip()
        self.country = JURISDICTION_COUNTRY  # always India — never editable
        self.state = (self.data.get("state") or "").strip()
        self.stage = (self.data.get("stage") or "Information gathering").strip()
        self.status = (self.data.get("status") or "draft").strip()

    def validate(self):
        if not self.title:
            raise SchemaError("A case title is required")
        if len(self.title) > MAX_CASE_TITLE_LEN:
            raise SchemaError("Case title is too long")
        self.state = _validate_indian_state(self.state)
        return self


class CaseUpdateSchema:
    """Fields accepted by PATCH /api/cases/:id. Country stays locked to
    India; state/UT must be an Indian state or union territory."""
    FIELDS = ("title", "case_type", "description", "parties", "country", "state", "stage", "status")

    def __init__(self, data: dict):
        self.data = data or {}

    def apply(self, case) -> None:
        for field in self.FIELDS:
            if field in self.data:
                value = self.data[field]
                setattr(case, field, value.strip() if isinstance(value, str) else value)
        if "state" in self.data:
            case.state = _validate_indian_state(case.state)
        # The country is never editable — always India, regardless of payload.
        if case.country != JURISDICTION_COUNTRY or "country" in self.data:
            case.country = JURISDICTION_COUNTRY
        if self.data.get("country") is not None or self.data.get("state") is not None:
            case.jurisdiction = jurisdiction_string(case.state)


class AuthRegisterSchema:
    def __init__(self, data: dict):
        self.data = data or {}
        self.name = (self.data.get("name") or "").strip()
        self.email = (self.data.get("email") or "").strip().lower()
        self.password = self.data.get("password") or ""

    def validate(self):
        if not self.name or not self.email or not self.password:
            raise SchemaError("Name, email and password are required")
        if len(self.name) > MAX_NAME_LEN:
            raise SchemaError("Name is too long")
        if len(self.password) > MAX_PASSWORD_LEN:
            raise SchemaError("Password is too long")
        if len(self.password) < 8:
            raise SchemaError("Password must be at least 8 characters")
        self.email = normalize_email(self.email)
        return self