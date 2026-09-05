"""SQLAlchemy models. The schema is PostgreSQL-compatible so switching
DATABASE_URL later requires no code changes.

Phase 1 fully implements User + Case. The remaining tables are wired and
used by the workspace; DocumentChunk and Notification are prepared for
later phases (RAG chunking and in-app notifications)."""
import json
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def _as_list(value):
    """Parse a JSON-array text column, tolerating empty / legacy values."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def _json_text(items):
    """Serialize a Python list into a JSON text column."""
    try:
        return json.dumps(items or [])
    except (TypeError, ValueError):
        return "[]"


evidence_issue_links = db.Table(
    "evidence_issue_links",
    db.Column("evidence_id", db.Integer, db.ForeignKey("evidence_items.id"), primary_key=True),
    db.Column("issue_id", db.Integer, db.ForeignKey("legal_issues.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    default_country = db.Column(db.String(120), default="")
    default_state = db.Column(db.String(120), default="")
    language = db.Column(db.String(16), default="en")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    cases = db.relationship("Case", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic",
                                    cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "default_country": self.default_country or "",
            "default_state": self.default_state or "",
            "language": self.language or "en",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    case_type = db.Column(db.String(120), default="")
    description = db.Column(db.Text, default="")
    parties = db.Column(db.String(500), default="")
    country = db.Column(db.String(120), default="")
    state = db.Column(db.String(120), default="")
    jurisdiction = db.Column(db.String(240), default="")  # derived "country, state" for AI context
    stage = db.Column(db.String(120), default="Information gathering")
    # Phase-2 statuses: draft | analysis_in_progress | analysis_complete |
    # action_required | resolved | archived
    status = db.Column(db.String(40), default="draft")
    is_demo = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    documents = db.relationship("CaseDocument", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    timeline = db.relationship("TimelineEvent", backref="case", lazy="dynamic", cascade="all, delete-orphan",
                               order_by="TimelineEvent.date")
    issues = db.relationship("LegalIssue", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    risks = db.relationship("RiskFactor", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    assessment = db.relationship("RiskAssessment", backref="case", uselist=False,
                                 cascade="all, delete-orphan")
    gaps = db.relationship("InfoGap", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    scenarios = db.relationship("Scenario", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    evidence = db.relationship("EvidenceItem", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    actions = db.relationship("ActionItem", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    deadlines = db.relationship("Deadline", backref="case", lazy="dynamic", cascade="all, delete-orphan")
    messages = db.relationship("ChatMessage", backref="case", lazy="dynamic", cascade="all, delete-orphan")

    def summary_counts(self):
        return {
            "documents": self.documents.count(),
            "documents_analyzed": self.documents.filter(CaseDocument.analysis_status == "analyzed").count(),
            "timeline_events": self.timeline.count(),
            "issues": self.issues.count(),
            "risks": self.risks.count(),
            "scenarios": self.scenarios.count(),
            "evidence_items": self.evidence.count(),
            "open_actions": self.actions.filter(ActionItem.status.notin_(("completed", "skipped"))).count(),
            "upcoming_deadlines": self.deadlines.filter(Deadline.status != "completed").count(),
        }

    def to_dict(self, include_counts=True):
        d = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "case_type": self.case_type or "",
            "description": self.description or "",
            "parties": self.parties or "",
            "country": self.country or "",
            "state": self.state or "",
            "jurisdiction": self.jurisdiction or "",
            "stage": self.stage or "",
            "status": self.status or "draft",
            "is_demo": bool(self.is_demo),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_counts:
            d["counts"] = self.summary_counts()
        return d


class CaseDocument(db.Model):
    __tablename__ = "case_documents"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(40), default="")  # pdf | docx | txt | image
    mime_type = db.Column(db.String(120), default="")
    size_bytes = db.Column(db.Integer, default=0)
    text_content = db.Column(db.Text, default="")
    extraction_status = db.Column(db.String(40), default="pending")  # pending | extracted | ocr_pending | failed
    analysis_json = db.Column(db.Text, default="")  # JSON from AI document analysis
    analysis_status = db.Column(db.String(40), default="not_analyzed")  # not_analyzed | analyzing | analyzed | failed
    uploaded_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    chunks = db.relationship("DocumentChunk", backref="document", lazy="dynamic",
                             cascade="all, delete-orphan")

    def to_dict(self):
        import json

        analysis = {}
        if self.analysis_json:
            try:
                analysis = json.loads(self.analysis_json)
            except (ValueError, TypeError):
                analysis = {}
        return {
            "id": self.id,
            "case_id": self.case_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "extraction_status": self.extraction_status,
            "analysis_status": self.analysis_status,
            "has_text": bool((self.text_content or "").strip()),
            "chunk_count": self.chunks.count(),
            "analysis": analysis,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class DocumentChunk(db.Model):
    """Prepared for later-phase RAG / semantic retrieval over documents."""
    __tablename__ = "document_chunks"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey("case_documents.id"), nullable=False, index=True)
    chunk_index = db.Column(db.Integer, default=0)
    content = db.Column(db.Text, default="")
    token_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "token_count": self.token_count,
        }


class TimelineEvent(db.Model):
    __tablename__ = "timeline_events"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(80), default="")  # legacy free-form category
    event_type = db.Column(db.String(40), default="other")
    # incident|communication|document|deadline|payment|legal_action|other
    importance = db.Column(db.String(20), default="medium")  # high|medium|low
    date_status = db.Column(db.String(40), default="user_confirmed")
    # user_confirmed|extracted|potential (extracted = from source, needs glance;
    # potential = date not stated or conflicting, must not be assumed)
    source = db.Column(db.String(40), default="user")  # user | document | ai
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "date": self.date.isoformat() if self.date else None,
            "title": self.title,
            "description": self.description or "",
            "category": self.category or "",
            "event_type": self.event_type or "other",
            "importance": self.importance or "medium",
            "date_status": self.date_status or "user_confirmed",
            "source": self.source or "user",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LegalIssue(db.Model):
    __tablename__ = "legal_issues"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(120), default="")
    jurisdiction = db.Column(db.String(120), default="")
    confidence = db.Column(db.String(20), default="medium")  # high | medium | low
    provenance = db.Column(db.String(40), default="user")  # user | document | ai
    status = db.Column(db.String(40), default="open")  # open | investigating | resolved | not_actionable
    supporting_facts = db.Column(db.Text, default="[]")   # JSON list of strings
    related_documents = db.Column(db.Text, default="[]")  # JSON list of filenames
    missing_information = db.Column(db.Text, default="[]")  # JSON list of strings
    impact = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description or "",
            "category": self.category or "",
            "jurisdiction": self.jurisdiction or "",
            "confidence": self.confidence or "medium",
            "provenance": self.provenance or "user",
            "status": self.status or "open",
            "supporting_facts": _as_list(self.supporting_facts),
            "related_documents": _as_list(self.related_documents),
            "missing_information": _as_list(self.missing_information),
            "impact": self.impact or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskFactor(db.Model):
    __tablename__ = "risk_factors"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    likelihood = db.Column(db.String(20), default="medium")
    impact = db.Column(db.String(20), default="medium")
    overall_risk = db.Column(db.String(20), default="medium")
    mitigation = db.Column(db.Text, default="")
    provenance = db.Column(db.String(40), default="user")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description or "",
            "likelihood": self.likelihood or "medium",
            "impact": self.impact or "medium",
            "overall_risk": self.overall_risk or "medium",
            "mitigation": self.mitigation or "",
            "provenance": self.provenance or "user",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RiskAssessment(db.Model):
    """Phase-7 explainable risk analysis — one per case.

    Scores are produced by a deterministic engine from the structured case
    record (issues, evidence, deadlines, gaps, negotiation prep); the AI layer
    only explains them. Scores measure the strength of the case record, never
    legal probabilities. previous_json keeps the last snapshot so regeneration
    can show what changed."""
    __tablename__ = "risk_assessments"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, unique=True, index=True)
    overall_score = db.Column(db.Integer, default=0)
    overall_level = db.Column(db.String(20), default="medium")  # low|medium|high|critical
    summary = db.Column(db.Text, default="")
    dimensions_json = db.Column(db.Text, default="")  # JSON list of dimension dicts
    previous_json = db.Column(db.Text, default="")    # JSON snapshot of the prior assessment
    note = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self):
        import json

        dimensions = []
        if self.dimensions_json:
            try:
                dimensions = json.loads(self.dimensions_json)
            except (ValueError, TypeError):
                dimensions = []
        previous = {}
        if self.previous_json:
            try:
                previous = json.loads(self.previous_json)
            except (ValueError, TypeError):
                previous = {}
        return {
            "id": self.id,
            "case_id": self.case_id,
            "overall_score": self.overall_score or 0,
            "overall_level": self.overall_level or "medium",
            "summary": self.summary or "",
            "dimensions": dimensions,
            "previous": previous,
            "note": self.note or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InfoGap(db.Model):
    __tablename__ = "info_gaps"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    question = db.Column(db.String(500), nullable=False)
    why_it_matters = db.Column(db.Text, default="")
    priority = db.Column(db.String(20), default="medium")
    source = db.Column(db.String(40), default="user")
    status = db.Column(db.String(40), default="open")  # open | found | not_applicable
    related_issue = db.Column(db.String(500), default="")  # issue this gap affects
    how_to_find = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "question": self.question,
            "why_it_matters": self.why_it_matters or "",
            "priority": self.priority or "medium",
            "source": self.source or "user",
            "status": self.status or "open",
            "related_issue": self.related_issue or "",
            "how_to_find": self.how_to_find or "",
        }


class Scenario(db.Model):
    __tablename__ = "scenarios"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    parameters = db.Column(db.Text, default="")
    facts_json = db.Column(db.Text, default="[]")  # Phase-8: editable fact list
    analysis_json = db.Column(db.Text, default="")
    risk_level = db.Column(db.String(20), default="medium")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        import json

        analysis = {}
        if self.analysis_json:
            try:
                analysis = json.loads(self.analysis_json)
            except (ValueError, TypeError):
                analysis = {}
        facts = []
        if self.facts_json:
            try:
                facts = json.loads(self.facts_json)
            except (ValueError, TypeError):
                facts = []
        return {
            "id": self.id,
            "case_id": self.case_id,
            "name": self.name,
            "description": self.description or "",
            "parameters": self.parameters or "",
            "facts": facts,
            "analysis": analysis,
            "risk_level": self.risk_level or "medium",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NegotiationPrep(db.Model):
    __tablename__ = "negotiation_prep"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, unique=True)
    # Legacy Phase-2/4 fields (still synced for the risk engine).
    goals = db.Column(db.Text, default="")
    batna = db.Column(db.Text, default="")
    interests = db.Column(db.Text, default="")
    concessions = db.Column(db.Text, default="")
    red_lines = db.Column(db.Text, default="")
    counterpart_analysis = db.Column(db.Text, default="")
    strategy = db.Column(db.Text, default="")
    # Phase-9 input: negotiation objective.
    objective = db.Column(db.Text, default="")
    desired_outcome = db.Column(db.Text, default="")
    minimum_acceptable = db.Column(db.Text, default="")
    key_evidence = db.Column(db.Text, default="")
    counterpart_position = db.Column(db.Text, default="")
    constraints = db.Column(db.Text, default="")
    channel = db.Column(db.String(40), default="")
    # Phase-9 output: the full copilot plan (JSON).
    plan_json = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self):
        import json

        plan = {}
        if self.plan_json:
            try:
                plan = json.loads(self.plan_json)
            except (ValueError, TypeError):
                plan = {}
        return {
            "id": self.id,
            "case_id": self.case_id,
            "goals": self.goals or "",
            "batna": self.batna or "",
            "interests": self.interests or "",
            "concessions": self.concessions or "",
            "red_lines": self.red_lines or "",
            "counterpart_analysis": self.counterpart_analysis or "",
            "strategy": self.strategy or "",
            "objective": self.objective or "",
            "desired_outcome": self.desired_outcome or "",
            "minimum_acceptable": self.minimum_acceptable or "",
            "key_evidence": self.key_evidence or "",
            "counterpart_position": self.counterpart_position or "",
            "constraints": self.constraints or "",
            "channel": self.channel or "",
            "plan": plan,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EvidenceItem(db.Model):
    __tablename__ = "evidence_items"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    item_type = db.Column(db.String(80), default="document")
    # document|email|message|photo|contract|receipt|witness|other
    source = db.Column(db.String(255), default="")
    date = db.Column(db.Date, nullable=True)
    importance = db.Column(db.String(20), default="medium")  # high|medium|low
    verification = db.Column(db.String(40), default="unverified")
    # unverified|verified|disputed
    status = db.Column(db.String(40), default="copy")  # original | copy | not_provided
    notes = db.Column(db.Text, default="")
    provenance = db.Column(db.String(40), default="user")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    issues = db.relationship("LegalIssue", secondary=evidence_issue_links,
                             backref=db.backref("evidence_items", lazy="dynamic"),
                             lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description or "",
            "item_type": self.item_type or "document",
            "source": self.source or "",
            "date": self.date.isoformat() if self.date else None,
            "importance": self.importance or "medium",
            "verification": self.verification or "unverified",
            "status": self.status or "copy",
            "notes": self.notes or "",
            "provenance": self.provenance or "user",
            "related_issues": [{"id": i.id, "title": i.title} for i in self.issues],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ActionItem(db.Model):
    __tablename__ = "action_items"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    priority = db.Column(db.String(20), default="medium")
    # Phase-11: why this action exists, which issue it serves, what proof is needed.
    reason = db.Column(db.Text, default="")
    related_issue = db.Column(db.String(500), default="")
    required_evidence = db.Column(db.Text, default="")
    due_date = db.Column(db.Date, nullable=True)
    # Phase-11 statuses: not_started | in_progress | completed | skipped
    status = db.Column(db.String(40), default="not_started")
    category = db.Column(db.String(80), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description or "",
            "priority": self.priority or "medium",
            "reason": self.reason or "",
            "related_issue": self.related_issue or "",
            "required_evidence": self.required_evidence or "",
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status or "not_started",
            "category": self.category or "",
        }


class Deadline(db.Model):
    __tablename__ = "deadlines"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, default="")
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(40), default="pending")  # pending | completed | missed
    source = db.Column(db.String(40), default="user")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description or "",
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status or "pending",
            "source": self.source or "user",
        }


class ChatSession(db.Model):
    """A conversation thread, scoped to one user + one case. Messages in a
    session are never mixed between cases or users."""
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, unique=True, index=True)
    title = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "case_id": self.case_id,
            "title": self.title or "CaseGuide conversation",
            "message_count": ChatMessage.query.filter_by(session_id=self.id).count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=True, index=True)
    role = db.Column(db.String(40), nullable=False)  # user | assistant
    content = db.Column(db.Text, nullable=False)
    provenance = db.Column(db.Text, default="")  # JSON: {mode, labels}
    meta = db.Column(db.Text, default="")  # JSON: structured CaseGuide payload
    language = db.Column(db.String(16), default="en")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        import json

        provenance = {}
        if self.provenance:
            try:
                provenance = json.loads(self.provenance)
            except (ValueError, TypeError):
                provenance = {}
        meta = {}
        if self.meta:
            try:
                meta = json.loads(self.meta)
            except (ValueError, TypeError):
                meta = {}
        return {
            "id": self.id,
            "case_id": self.case_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "provenance": provenance,
            "meta": meta,
            "language": self.language or "en",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    """Prepared for later-phase in-app notifications (deadline alerts, AI findings)."""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(40), default="info")  # info | deadline | action | ai
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, default="")
    link = db.Column(db.String(255), default="")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kind": self.kind or "info",
            "title": self.title,
            "message": self.message or "",
            "link": self.link or "",
            "is_read": bool(self.is_read),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class NegotiationSession(db.Model):
    """Phase-10 interactive negotiation simulation.

    One session per case: the AI roleplays the opposing party from an explicit
    opponent position, and a completed session stores a structured evaluation
    (seven 1-10 dimension scores plus feedback). Separate from the CaseGuide
    chatbot and from the lightweight practice endpoint.
    """

    __tablename__ = "negotiation_sessions"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("cases.id"), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    opponent_position = db.Column(db.Text, default="")
    language = db.Column(db.String(16), default="en")
    status = db.Column(db.String(20), default="active")  # active | completed
    messages_json = db.Column(db.Text, default="[]")     # [{role, content, label?, note?}]
    evaluation_json = db.Column(db.Text, default="")     # Phase-10 performance evaluation
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def to_dict(self):
        messages = []
        if self.messages_json:
            try:
                messages = json.loads(self.messages_json)
            except (ValueError, TypeError):
                messages = []
        evaluation = {}
        if self.evaluation_json:
            try:
                evaluation = json.loads(self.evaluation_json)
            except (ValueError, TypeError):
                evaluation = {}
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "opponent_position": self.opponent_position or "",
            "language": self.language or "en",
            "status": self.status or "active",
            "messages": messages,
            "evaluation": evaluation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
