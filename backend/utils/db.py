"""Lightweight, idempotent migrations.

SQLAlchemy's create_all() adds new *tables* but not new *columns*, so this
module performs additive column migrations and one-time data migrations at
startup. Safe to run on every boot; each step guards on what already exists.
"""
from sqlalchemy import inspect, text

from app.extensions import db

# Legacy Phase-1 case statuses → Phase-2 status model.
LEGACY_CASE_STATUS_MAP = {
    "active": "analysis_in_progress",
    "on_hold": "action_required",
    "closed": "resolved",
}

# Legacy free-form timeline categories → Phase-6 event types.
LEGACY_EVENT_TYPE_MAP = {
    "agreement": "document",
    "document": "document",
    "payment": "payment",
    "notice": "communication",
    "communication": "communication",
    "incident": "incident",
    "court": "legal_action",
    "deadline": "deadline",
}


def _columns(table: str) -> set[str]:
    return {c["name"] for c in inspect(db.engine).get_columns(table)}


def _add_column(table: str, column: str, ddl: str) -> bool:
    if column in _columns(table):
        return False
    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    db.session.commit()
    return True


def ensure_case_columns():
    """Additive migrations for the cases table across phases."""
    _add_column("cases", "parties", "parties VARCHAR(500) DEFAULT ''")


def ensure_chat_columns():
    """Phase-4: sessions attach messages to one user + one case."""
    _add_column("chat_messages", "session_id", "session_id INTEGER")
    _add_column("chat_messages", "meta", "meta TEXT DEFAULT ''")


def ensure_issue_columns():
    """Phase-5: richer issue intelligence (evidence, documents, gaps, impact)."""
    _add_column("legal_issues", "supporting_facts", "supporting_facts TEXT DEFAULT '[]'")
    _add_column("legal_issues", "related_documents", "related_documents TEXT DEFAULT '[]'")
    _add_column("legal_issues", "missing_information", "missing_information TEXT DEFAULT '[]'")
    _add_column("legal_issues", "impact", "impact TEXT DEFAULT ''")


def ensure_gap_columns():
    """Phase-5: gap analyzer — which issue it affects and how to find it."""
    _add_column("info_gaps", "related_issue", "related_issue VARCHAR(500) DEFAULT ''")
    _add_column("info_gaps", "how_to_find", "how_to_find TEXT DEFAULT ''")


def ensure_timeline_columns():
    """Phase-6: timeline builder — event type, importance, date confidence."""
    _add_column("timeline_events", "event_type", "event_type VARCHAR(40) DEFAULT 'other'")
    _add_column("timeline_events", "importance", "importance VARCHAR(20) DEFAULT 'medium'")
    _add_column("timeline_events", "date_status", "date_status VARCHAR(40) DEFAULT 'user_confirmed'")


def ensure_evidence_columns():
    """Phase-6: evidence organizer — importance and verification status."""
    _add_column("evidence_items", "importance", "importance VARCHAR(20) DEFAULT 'medium'")
    _add_column("evidence_items", "verification", "verification VARCHAR(40) DEFAULT 'unverified'")


def ensure_action_columns():
    """Phase-11: action plan — reason, related issue, required evidence."""
    _add_column("action_items", "reason", "reason TEXT DEFAULT ''")
    _add_column("action_items", "related_issue", "related_issue VARCHAR(500) DEFAULT ''")
    _add_column("action_items", "required_evidence", "required_evidence TEXT DEFAULT ''")


def migrate_legacy_action_statuses():
    """Map pre-Phase-11 action statuses onto the four-state model."""
    db.session.execute(
        text("UPDATE action_items SET status = 'not_started' WHERE status = 'pending'")
    )
    db.session.execute(
        text("UPDATE action_items SET status = 'completed' WHERE status = 'done'")
    )
    db.session.commit()


def ensure_negotiation_columns():
    """Phase-9: negotiation copilot — objective inputs and the generated plan."""
    _add_column("negotiation_prep", "objective", "objective TEXT DEFAULT ''")
    _add_column("negotiation_prep", "desired_outcome", "desired_outcome TEXT DEFAULT ''")
    _add_column("negotiation_prep", "minimum_acceptable", "minimum_acceptable TEXT DEFAULT ''")
    _add_column("negotiation_prep", "key_evidence", "key_evidence TEXT DEFAULT ''")
    _add_column("negotiation_prep", "counterpart_position", "counterpart_position TEXT DEFAULT ''")
    _add_column("negotiation_prep", "constraints", "constraints TEXT DEFAULT ''")
    _add_column("negotiation_prep", "channel", "channel VARCHAR(40) DEFAULT ''")
    _add_column("negotiation_prep", "plan_json", "plan_json TEXT DEFAULT ''")


def ensure_scenario_columns():
    """Phase-8: what-if simulator — editable fact list per scenario."""
    _add_column("scenarios", "facts_json", "facts_json TEXT DEFAULT '[]'")


def migrate_legacy_event_types():
    """Map pre-Phase-6 timeline categories onto the new event_type values."""
    result = db.session.execute(
        text("SELECT DISTINCT category FROM timeline_events "
             "WHERE event_type IN ('', 'other') AND category != ''")
    ).fetchall()
    if not result:
        return
    for (category,) in result:
        new_type = LEGACY_EVENT_TYPE_MAP.get((category or "").strip().lower())
        if new_type:
            db.session.execute(
                text("UPDATE timeline_events SET event_type = :et "
                     "WHERE category = :cat AND event_type IN ('', 'other')"),
                {"et": new_type, "cat": category},
            )
    db.session.commit()


def migrate_case_statuses():
    """One-time remap of legacy status values to the Phase-2 status model."""
    result = db.session.execute(
        text("SELECT DISTINCT status FROM cases WHERE status IN "
             "('active', 'on_hold', 'closed')")
    ).fetchall()
    if not result:
        return
    for (old_value,) in result:
        new_value = LEGACY_CASE_STATUS_MAP.get(old_value)
        if new_value:
            db.session.execute(
                text("UPDATE cases SET status = :new_value WHERE status = :old_value"),
                {"new_value": new_value, "old_value": old_value},
            )
    db.session.commit()


def run_migrations():
    ensure_case_columns()
    ensure_chat_columns()
    ensure_issue_columns()
    ensure_gap_columns()
    ensure_timeline_columns()
    ensure_evidence_columns()
    ensure_scenario_columns()
    ensure_negotiation_columns()
    ensure_action_columns()
    migrate_legacy_action_statuses()
    migrate_legacy_event_types()
    migrate_case_statuses()