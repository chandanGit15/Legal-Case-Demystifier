"""Document intelligence business logic.

Pipeline: upload → validate (type/size/name) → extract text → store document
metadata → chunk text where appropriate (DocumentChunk) → send relevant content
to the AI → store structured analysis → apply verified findings back to the
case (evidence, issues, timeline, deadlines) with clear provenance.
"""
import json
import logging
import os
import uuid
from datetime import date as _date

logger = logging.getLogger("lcd.document_service")

from app.extensions import db
from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, UPLOAD_DIR
from document_processing.chunker import chunk_text, count_tokens
from document_processing.extractor import extract_text, file_type_of
from models import (ActionItem, Case, CaseDocument, Deadline, DocumentChunk,
                    EvidenceItem, LegalIssue, TimelineEvent)
from ai import analyze_document as ai_analyze_document
from ai import b64encode, image_payload


class DocumentError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# Listing / ownership
# --------------------------------------------------------------------------

def list_documents(case) -> list:
    return case.documents.order_by(CaseDocument.uploaded_at.desc()).all()


def get_document(case, doc_id: int) -> CaseDocument:
    doc = db.session.get(CaseDocument, doc_id)
    if doc is None or doc.case_id != case.id:
        raise DocumentError("Document not found", 404)
    return doc


def get_owned_document(user_id: int, doc_id: int):
    """Resolve a document by id alone, enforcing ownership through its case."""
    doc = db.session.get(CaseDocument, doc_id)
    if doc is None:
        raise DocumentError("Document not found", 404)
    case = db.session.get(Case, doc.case_id)
    if case is None or case.user_id != user_id:
        raise DocumentError("Document not found", 404)
    return case, doc


# --------------------------------------------------------------------------
# Pipeline: upload → validate → extract → store → chunk
# --------------------------------------------------------------------------

def upload(case, file) -> CaseDocument:
    if file is None or not file.filename:
        raise DocumentError("No file provided")
    filename = os.path.basename(file.filename)
    if not _valid_filename(filename):
        raise DocumentError(
            "Invalid filename — use a plain name ending in .pdf, .docx or .txt "
            "(images are supported too).")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentError(
            f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size == 0:
        raise DocumentError("The file is empty")
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        raise DocumentError(f"File exceeds the {MAX_UPLOAD_MB} MB limit")

    file_type = file_type_of(filename)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    case_dir = os.path.join(UPLOAD_DIR, str(case.id))
    os.makedirs(case_dir, exist_ok=True)
    path = os.path.join(case_dir, stored_name)
    try:
        file.save(path)
    except OSError as exc:
        raise DocumentError("Could not store the uploaded file", 500) from exc

    # Extract text server-side (images are OCR'd by the AI at analysis time).
    text, _tool = extract_text(file_type, path)
    has_text = bool(text.strip())
    extraction_status = (
        "extracted" if has_text else
        ("ocr_pending" if file_type == "image" else "failed"))

    doc = CaseDocument(
        case_id=case.id,
        filename=filename,
        stored_name=stored_name,
        file_type=file_type,
        mime_type=file.mimetype or "",
        size_bytes=size,
        text_content=text[:200000],
        extraction_status=extraction_status,
        analysis_status="not_analyzed",
    )
    db.session.add(doc)
    db.session.flush()
    _store_chunks(doc, text)
    db.session.commit()
    return doc


def _valid_filename(filename: str) -> bool:
    if len(filename) > 200 or filename.startswith("."):
        return False
    # Reject control characters and anything that would traverse paths.
    if any(ord(ch) < 32 for ch in filename):
        return False
    if "\\" in filename or filename.startswith("/"):
        return False
    return True


def _store_chunks(doc: CaseDocument, text: str) -> None:
    """Replace this document's chunks with fresh ones derived from its text."""
    DocumentChunk.query.filter_by(document_id=doc.id).delete()
    chunks = chunk_text(text)
    for index, content in enumerate(chunks):
        db.session.add(DocumentChunk(
            document_id=doc.id,
            chunk_index=index,
            content=content,
            token_count=count_tokens(content),
        ))


def get_content(doc: CaseDocument) -> dict:
    """Return extracted content preview + chunk metadata for the UI."""
    chunks = (DocumentChunk.query
              .filter_by(document_id=doc.id)
              .order_by(DocumentChunk.chunk_index.asc()).all())
    text = doc.text_content or ""
    return {
        "document_id": doc.id,
        "has_text": bool(text.strip()),
        "text_length": len(text),
        "excerpt": text[:6000],
        "excerpt_truncated": len(text) > 6000,
        "chunks": [c.to_dict() for c in chunks],
        "chunk_count": len(chunks),
    }


# --------------------------------------------------------------------------
# Delete
# --------------------------------------------------------------------------

def delete(case, doc_id: int) -> None:
    doc = get_document(case, doc_id)
    _remove_file(case, doc)
    db.session.delete(doc)
    db.session.commit()


def delete_owned(user_id: int, doc_id: int) -> None:
    case, doc = get_owned_document(user_id, doc_id)
    delete(case, doc.id)


def _remove_file(case, doc: CaseDocument) -> None:
    try:
        path = os.path.join(UPLOAD_DIR, str(case.id), doc.stored_name)
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# --------------------------------------------------------------------------
# Analysis: AI + chunking + applying findings to the case (idempotent)
# --------------------------------------------------------------------------

def analyze(case, doc_id: int) -> dict:
    doc = get_document(case, doc_id)
    return analyze_document(case, doc)


def analyze_owned(user_id: int, doc_id: int) -> dict:
    case, doc = get_owned_document(user_id, doc_id)
    return analyze_document(case, doc)


def analyze_document(case, doc: CaseDocument) -> dict:
    """Run AI analysis on a document, store the JSON, and apply structured
    findings back into the case. Re-running is safe: deduplicated by content."""
    doc.analysis_status = "analyzing"
    db.session.commit()
    try:
        image = None
        text = doc.text_content or ""
        if doc.file_type == "image" and not text.strip():
            path = os.path.join(UPLOAD_DIR, str(case.id), doc.stored_name)
            if os.path.exists(path):
                with open(path, "rb") as fh:
                    image = image_payload(b64encode(fh.read()), doc.mime_type or "image/png")

        analysis = ai_analyze_document(case.to_dict(), doc.to_dict(), text=text, image=image)

        doc.analysis_json = json.dumps(analysis)
        doc.analysis_status = "analyzed"
        # Images become fully extracted once the AI transcribes them.
        if doc.extraction_status == "ocr_pending" and (text.strip() or analysis.get("summary")):
            doc.extraction_status = "extracted"
        db.session.flush()
        if not doc.chunks.count() and text.strip():
            _store_chunks(doc, text)
        db.session.commit()

        _apply_analysis(case, doc, analysis)
        return analysis
    except Exception:  # noqa: BLE001
        # Log the full detail server-side; the client only ever sees a clean,
        # non-technical message (no stack traces, no exception internals).
        logger.exception("Document analysis failed for document %s (case %s)",
                         doc.id, case.id)
        db.session.rollback()
        doc.analysis_status = "failed"
        db.session.commit()
        raise DocumentError(
            "Document analysis failed. Please try again in a moment.", 500) from None


def _apply_analysis(case, doc: CaseDocument, analysis: dict) -> None:
    """Import structured findings into the case with 'document' provenance.
    Each import is deduplicated so re-running analysis never duplicates rows."""
    # Key facts → evidence items
    for fact in analysis.get("key_facts") or []:
        fact_text = (fact.get("text") or "").strip()
        if not fact_text:
            continue
        exists = EvidenceItem.query.filter_by(
            case_id=case.id, description=fact_text).first()
        if exists:
            continue
        db.session.add(EvidenceItem(
            case_id=case.id,
            title=fact_text[:120],
            description=fact_text,
            item_type="document",
            source=f"From document: {doc.filename}",
            status="copy",
            provenance="document",
        ))

    # Potential issues → legal issues
    for issue in analysis.get("possible_issues") or []:
        title = (issue.get("title") or "").strip()[:255]
        if not title:
            continue
        exists = LegalIssue.query.filter_by(case_id=case.id, title=title).first()
        if exists:
            continue
        db.session.add(LegalIssue(
            case_id=case.id,
            title=title,
            description=(issue.get("basis") or issue.get("description") or "").strip(),
            category=(issue.get("category") or "").strip(),
            confidence=(issue.get("confidence") or "medium").strip(),
            provenance="document",
            status="open",
        ))

    # Dates found → timeline events (only concrete, meaningful dates)
    for d in analysis.get("dates_found") or []:
        ds = d.get("date")
        parsed = _try_date(ds)
        if parsed is None:
            continue
        title = (d.get("description") or "").strip()[:255]
        if not title:
            continue
        exists = TimelineEvent.query.filter_by(
            case_id=case.id, date=parsed, title=title).first()
        if exists:
            continue
        db.session.add(TimelineEvent(
            case_id=case.id, date=parsed, title=title,
            description=f"Extracted from {doc.filename}.",
            category="document", source="document",
        ))

    # Deadlines → deadline tracker (dedupe on title + due date)
    for dl in analysis.get("deadlines") or []:
        due = _try_date(dl.get("date"))
        if due is None:
            continue
        title = (dl.get("title") or "Document deadline").strip()[:255]
        exists = Deadline.query.filter_by(
            case_id=case.id, title=title, due_date=due).first()
        if exists:
            continue
        db.session.add(Deadline(
            case_id=case.id, title=title,
            description=(dl.get("description") or
                         f"Deadline identified in {doc.filename}.").strip(),
            due_date=due, status="pending", source="document",
        ))

    db.session.commit()


def _try_date(value):
    if not value:
        return None
    try:
        return _date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Connect document findings to the case (user-initiated)
# --------------------------------------------------------------------------

def import_finding(case, doc: CaseDocument, kind: str, data: dict) -> dict:
    """Import one analyzed finding into the case on user request.

    kind: timeline | deadline | issue | evidence
    Returns a small {ok, entity} dict so the UI can toast and refresh.
    """
    data = data or {}
    if kind == "timeline":
        parsed = _try_date(data.get("date"))
        title = (data.get("title") or "").strip()
        if parsed is None or not title:
            raise DocumentError("A valid date and title are required to add a timeline event", 400)
        row = TimelineEvent(case_id=case.id, date=parsed, title=title[:255],
                            description=f"Connected from {doc.filename}.",
                            category="document", source="document")
        db.session.add(row)
        db.session.commit()
        return {"ok": True, "entity": row.to_dict()}

    if kind == "deadline":
        due = _try_date(data.get("date"))
        title = (data.get("title") or "").strip()
        if due is None or not title:
            raise DocumentError("A valid date and title are required to add a deadline", 400)
        row = Deadline(case_id=case.id, title=title[:255],
                       description=(data.get("description") or
                                    f"Deadline from {doc.filename}.").strip(),
                       due_date=due, status="pending", source="document")
        db.session.add(row)
        db.session.commit()
        return {"ok": True, "entity": row.to_dict()}

    if kind == "issue":
        title = (data.get("title") or "").strip()
        if not title:
            raise DocumentError("An issue title is required", 400)
        row = LegalIssue(case_id=case.id, title=title[:255],
                         description=(data.get("basis") or data.get("description") or "").strip(),
                         category=(data.get("category") or "").strip(),
                         confidence=(data.get("confidence") or "medium").strip(),
                         provenance="document", status="open")
        db.session.add(row)
        db.session.commit()
        return {"ok": True, "entity": row.to_dict()}

    if kind == "evidence":
        text = (data.get("text") or data.get("description") or "").strip()
        if not text:
            raise DocumentError("Evidence content is required", 400)
        row = EvidenceItem(case_id=case.id, title=(data.get("title") or text[:120]).strip()[:255],
                           description=text, item_type="document",
                           source=f"From document: {doc.filename}",
                           status="copy", provenance="document")
        db.session.add(row)
        db.session.commit()
        return {"ok": True, "entity": row.to_dict()}

    if kind == "action":
        title = (data.get("title") or "").strip()
        if not title:
            raise DocumentError("An action title is required", 400)
        row = ActionItem(case_id=case.id, title=title[:255],
                         description=(data.get("description") or
                                      f"Suggested by {doc.filename}.").strip(),
                         priority=(data.get("priority") or "medium").strip(),
                         due_date=_try_date(data.get("due_date")),
                         category="document")
        db.session.add(row)
        db.session.commit()
        return {"ok": True, "entity": row.to_dict()}

    raise DocumentError(f"Unknown finding kind: {kind}", 400)
