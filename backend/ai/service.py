"""Centralized AI service layer.

Every AI feature in the application must call Gemini through this module.

Guarantees:
  * Never invents laws or citations: the system instruction forbids it.
  * Every response is structured JSON labelled with provenance
    (USER_PROVIDED / EXTRACTED_FROM_DOCUMENT / AI_INTERPRETATION /
    INFORMATION_MISSING / REQUIRES_VERIFICATION).
  * Includes the legal disclaimer.
  * If GEMINI_API_KEY is not configured (or a call fails), returns
    deterministic demo-mode content clearly marked mode="demo" so the
    application remains fully functional for demos and offline development.
"""
import base64
import json
import re

import requests

from config import GEMINI_API_KEY, GEMINI_MODEL, LEGAL_DISCLAIMER
from datetime import date

from models import Case, CaseDocument, NegotiationPrep, TimelineEvent

SYSTEM_INSTRUCTION = (
    "You are the analysis engine of 'Legal Case Demystifier', a structured legal "
    "case workspace. You help users understand their legal situation. You must:\n"
    "1. NEVER invent laws, statutes, regulations, or case citations. If specific "
    "legal provisions are relevant, say the law varies by jurisdiction and that "
    "verification by a legal professional is required. Do NOT cite specific "
    "statute numbers, section numbers, or case names unless the user or their "
    "documents provided them.\n"
    "2. NEVER guarantee outcomes. Use hedged language ('may', 'could', 'likely').\n"
    "3. NEVER present assumptions as facts. Distinguish clearly between facts the "
    "user provided, facts extracted from documents, and your own interpretation.\n"
    "4. NEVER pretend to be a lawyer or give definitive legal advice.\n"
    "5. Flag information that is missing or that requires verification.\n"
    "6. Return ONLY valid JSON matching the requested schema. No markdown fences, "
    "no commentary outside the JSON.\n"
    "7. Be concise, professional, and practical.\n"
    f"Always end structured output with a 'disclaimer' string: {LEGAL_DISCLAIMER}"
)


class AIError(Exception):
    pass


def ai_available() -> bool:
    return bool(GEMINI_API_KEY)


# --------------------------------------------------------------------------
# Low-level Gemini access
# --------------------------------------------------------------------------

def _call_gemini(prompt: str, system: str = SYSTEM_INSTRUCTION,
                 images: list = None, temperature: float = 0.3) -> str:
    """Call the Gemini REST API. Raises AIError on failure."""
    if not GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY is not configured")

    parts = []
    for img in images or []:
        parts.append({
            "inline_data": {
                "mime_type": img.get("mime_type", "image/png"),
                "data": img["b64"],
            }
        })
    parts.append({"text": prompt})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "system_instruction": {"parts": [{"text": system}]},
        "generation_config": {"temperature": temperature, "max_output_tokens": 4096},
    }
    resp = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        raise AIError(f"Gemini API returned {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        candidates = data["candidates"]
        parts_out = candidates[0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts_out)
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError(f"Unexpected Gemini response: {str(data)[:300]}") from exc


def _parse_json(text: str) -> dict:
    """Defensively parse JSON out of a model response (may include fences)."""
    if not text:
        return {}
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except ValueError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except ValueError:
            return {}
    return {}


def _complete(prompt: str, demo: dict, images: list = None, temperature: float = 0.3) -> dict:
    """Call Gemini and merge the result; fall back to demo content on any failure."""
    try:
        raw = _call_gemini(prompt, images=images, temperature=temperature)
        parsed = _parse_json(raw)
        if parsed:
            parsed["mode"] = "ai"
            parsed.setdefault("disclaimer", LEGAL_DISCLAIMER)
            return parsed
        demo["mode"] = "demo"
        demo["note"] = "The AI returned an unparseable response."
        return demo
    except AIError as exc:
        demo["mode"] = "demo"
        demo["note"] = f"Gemini unavailable ({exc}). Showing demo analysis."
        return demo


def _demo_note(kind: str) -> str:
    return (
        f"Demo {kind} — connect a GEMINI_API_KEY in the backend environment for "
        "live AI analysis. Demo content is illustrative and must not be relied upon."
    )


# --------------------------------------------------------------------------
# Structured helpers shared by prompts
# --------------------------------------------------------------------------

# India-only jurisdiction guidance appended to every case-context block.
# The application serves the Indian legal context exclusively, so the AI is
# told the jurisdiction up front and reminded of Indian legal terminology and
# the need to ground any legal statements in facts, dates and jurisdiction.
INDIA_JURISDICTION_GUIDANCE = (
    "Jurisdictional context: this case is in India (country fixed; state/UT "
    "listed above when set). Recognize Indian legal terms and institutions "
    "where relevant, for example: FIR, bail, anticipatory bail, charge sheet, "
    "legal notice, affidavit, plaint, written statement, petition, appeal, "
    "revision, stay order, injunction, limitation, arbitration, mediation, "
    "consumer complaint, labour dispute, employment contract. Never apply "
    "specific Indian laws confidently without considering the relevant facts, "
    "dates and jurisdiction; where a law, period or procedure depends on the "
    "state/UT or on circumstances, say so and recommend verification with an "
    "Indian legal professional."
)


def _case_context(case: dict) -> str:
    parts = [f"Case title: {case.get('title')}"]
    if case.get("case_type"):
        parts.append(f"Case type: {case['case_type']}")
    if case.get("jurisdiction"):
        parts.append(f"Jurisdiction: {case['jurisdiction']}")
    if case.get("parties"):
        parts.append(f"Parties: {case['parties']}")
    if case.get("stage"):
        parts.append(f"Current stage: {case['stage']}")
    if case.get("description"):
        parts.append(f"Facts provided by the user: {case['description']}")
    parts.append(INDIA_JURISDICTION_GUIDANCE)
    return "\n".join(parts)


def _facts_context(case: dict, limit: int = 12) -> str:
    """Build a facts block distinguishing user-provided from document-extracted."""
    lines = []
    facts = case.get("facts") or []
    for f in facts[:limit]:
        label = {
            "user": "FACT PROVIDED BY USER",
            "document": "FACT EXTRACTED FROM DOCUMENT",
        }.get(f.get("source"), "FACT")
        lines.append(f"- {label}: {f.get('text', '')}")
    issues = case.get("issues") or []
    if issues:
        lines.append("Known/potential issues:")
        for i in issues[:8]:
            lines.append(f"- {i.get('title', '')} (confidence: {i.get('confidence', 'medium')})")
    return "\n".join(lines) if lines else "No additional facts provided."


def _stamp(result: dict, mode: str, note: str = None) -> dict:
    result["mode"] = mode
    result["disclaimer"] = LEGAL_DISCLAIMER
    if note:
        result["note"] = note
    return result


def _rich_context(case: dict) -> str:
    """Extra structured context for the chat prompt: documents, timeline,
    risks and information gaps currently attached to the case."""
    blocks = []
    docs = case.get("documents") or []
    if docs:
        lines = [f"Relevant documents in the case ({len(docs)}):"]
        for d in docs[:10]:
            suffix = " (analyzed)" if d.get("analysis_status") == "analyzed" else ""
            line = f"- {d.get('filename', 'document')}{suffix}"
            for kd in (d.get("key_dates") or [])[:6]:
                if kd.get("date"):
                    line += f" | {kd['date']}: {kd.get('description', '')[:80]}"
            lines.append(line)
        blocks.append("\n".join(lines))
    timeline = case.get("timeline") or []
    if timeline:
        lines = [f"Timeline ({len(timeline)} events, latest first):"]
        lines += [f"- {t.get('date', '')}: {t.get('title', '')}" for t in timeline[:12]]
        blocks.append("\n".join(lines))
    risks = case.get("risks") or []
    if risks:
        lines = ["Risks on file:"]
        lines += [f"- {r.get('title', '')} ({r.get('overall_risk', 'medium')})" for r in risks[:8]]
        blocks.append("\n".join(lines))
    gaps = case.get("gaps") or []
    if gaps:
        lines = ["Open information gaps:"]
        lines += [f"- {g.get('question', '')}" for g in gaps[:8]]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "No documents, timeline, risks or gaps recorded yet."


def _sources_from_context(case: dict) -> list:
    """Deterministic source list used by demo replies."""
    sources = [{"type": "case", "label": case.get("title", "this case")}]
    for d in (case.get("documents") or [])[:10]:
        sources.append({"type": "document", "label": d.get("filename", "document")})
    for t in (case.get("timeline") or [])[:4]:
        sources.append({"type": "timeline", "label": t.get("title", "timeline event")})
    for i in (case.get("issues") or [])[:4]:
        sources.append({"type": "issue", "label": i.get("title", "issue")})
    return sources


# --------------------------------------------------------------------------
# 1. Case overview analysis
# --------------------------------------------------------------------------

def analyze_case_overview(case: dict) -> dict:
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Produce a structured case overview as JSON with this schema:
{{
  "summary": "3-5 sentence plain-language summary of the situation",
  "key_facts": [{{"text": "...", "source": "user|document", "label": "FACT PROVIDED BY USER|FACT EXTRACTED FROM DOCUMENT"}}],
  "possible_issues": [{{"title": "...", "category": "...", "confidence": "high|medium|low", "basis": "why it may be an issue"}}],
  "information_gaps": [{{"question": "...", "why_it_matters": "..."}}],
  "suggested_actions": ["...", "..."],
  "risk_notes": ["..."],
  "requires_verification": ["anything that must be verified by a professional"]
}}
Label every fact with its source. Do not invent facts, laws, or citations."""
    demo = _stamp({
        "summary": (
            f"Overview of '{case.get('title', 'this case')}' based on the information "
            "currently in the case file. The core situation is still being assembled; "
            "the key facts below come from what has been recorded so far. Several "
            "details remain unverified and should be confirmed before they are relied upon."
        ),
        "key_facts": [
            {"text": case.get("description", "") or "No description recorded yet.",
             "source": "user",
             "label": "FACT PROVIDED BY USER"},
        ],
        "possible_issues": [
            {"title": "Scope of obligations and possible breach",
             "category": "contract",
             "confidence": "medium",
             "basis": "The case involves an agreement whose performance is in dispute; "
                      "the exact terms and any alleged breach still need to be examined."}
        ] if case.get("case_type") else [],
        "information_gaps": [
            {"question": "What documents evidence the agreement and its terms?",
             "why_it_matters": "The terms define the obligations and any breach."},
            {"question": "When and how did the dispute first arise?",
             "why_it_matters": "Dates can matter for deadlines and limitation periods."},
        ],
        "suggested_actions": [
            "Upload any relevant documents so they can be analyzed.",
            "Add key dates to the case timeline.",
            "List the parties and their roles.",
        ],
        "risk_notes": ["Risk level is unassessed until documents and dates are added."],
        "requires_verification": ["All legal conclusions must be verified by a qualified "
                                  "professional in the relevant jurisdiction."],
        "note": _demo_note("case overview"),
    }, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# 2. Document intelligence
# --------------------------------------------------------------------------

def analyze_document(case: dict, doc_meta: dict, text: str = "", image: dict = None) -> dict:
    context = _case_context(case)
    doc_desc = (
        f"Document: {doc_meta.get('filename', 'uploaded document')} "
        f"(type: {doc_meta.get('file_type', 'unknown')})."
    )
    if text:
        excerpt = text[:14000]
        doc_body = f"Document text follows:\n{excerpt}"
    else:
        doc_body = "The document is an image provided inline. Transcribe and analyze it."
    prompt = f"""{context}

{doc_desc}
{doc_body}

Produce a JSON analysis of this document:
{{
  "summary": "2-4 sentence summary of what the document says",
  "document_type": "e.g. contract, lease agreement, letter, invoice, notice, court filing, report, other — only when inferable from the text",
  "parties": [{{"name": "party as named in the document", "role": "role only if stated, e.g. landlord/tenant, buyer/seller, or empty string"}}],
  "key_facts": [{{"text": "...", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"}}],
  "important_clauses": [{{"quote": "short verbatim excerpt", "meaning": "plain-language explanation of what the clause does", "section": "section/clause reference if present, else empty string"}}],
  "concerning_clauses": [{{"quote": "short verbatim excerpt", "reason": "why this clause may matter for the user's situation", "severity": "high|medium|low"}}],
  "obligations": [{{"party": "who must act, or empty string", "obligation": "what the document requires them to do"}}],
  "deadlines": [{{"date": "YYYY-MM-DD only if stated in the document", "title": "short label", "description": "what happens by this date"}}],
  "dates_found": [{{"date": "YYYY-MM-DD", "description": "what this date refers to"}}],
  "entities": ["names of companies, institutions, properties or other entities named in the document"],
  "possible_issues": [{{"title": "...", "category": "...", "confidence": "high|medium|low", "basis": "..."}}],
  "information_gaps": [{{"question": "...", "why_it_matters": "..."}}],
  "warnings": ["anything ambiguous, risky or that requires verification"],
  "requires_verification": ["..."]
}}
Quote verbatim only from the document text. Only state facts that appear in the "
"document text or image. Never invent document contents, laws, or citations. "
"Leave lists empty when nothing in the document supports an entry."""
    images = [image] if image else None
    demo = _stamp({
        "summary": (
            f"Analysis of '{doc_meta.get('filename', 'document')}'. The document was "
            "reviewed in demo mode; its key content has been summarized at a high level. "
            "Connect a Gemini API key for a full reading."
        ),
        "document_type": "",
        "parties": [],
        "key_facts": [
            {"text": "The document is recorded as a " + (doc_meta.get("file_type") or "document") + " in the case file.",
             "source": "document",
             "label": "FACT EXTRACTED FROM DOCUMENT"},
        ] if text else [],
        "important_clauses": [],
        "concerning_clauses": [],
        "obligations": [],
        "deadlines": [],
        "dates_found": [],
        "entities": [],
        "possible_issues": [],
        "information_gaps": [],
        "warnings": [],
        "requires_verification": ["Any dates or obligations in this document must be verified "
                                  "against the original."],
        "note": _demo_note("document analysis"),
    }, "demo")
    return _complete(prompt, demo, images=images)


# --------------------------------------------------------------------------
# 3. Legal issue detection
# --------------------------------------------------------------------------

def detect_legal_issues(case: dict) -> dict:
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

{_rich_context(case)}

Identify potential legal issues as JSON:
{{
  "issues": [
    {{
      "title": "short issue title",
      "description": "2-3 sentences explaining WHY this may be an issue, grounded in the facts above",
      "category": "contract|employment|property|family|liability|other",
      "confidence": "high|medium|low",
      "supporting_facts": ["facts from the context above that point toward this issue — never invent new facts"],
      "related_documents": ["filenames from the documents above that bear on this issue, or leave empty"],
      "missing_information": ["what would need to be confirmed before this issue could be relied on"],
      "impact": "1-2 sentences on the practical impact if this issue holds (financial, procedural, or otherwise)",
      "provenance": "AI_INTERPRETATION"
    }}
  ],
  "note": "brief note on what was considered"
}}
Only flag issues the context can support. Keep lists empty when nothing supports an "
"entry. Confidence reflects how strongly the available information supports the "
"issue — it is not a statement of legal certainty. Never invent laws or citations; "
"say the law varies by jurisdiction where relevant."""
    supporting = []
    if case.get("description"):
        supporting.append("The user has not yet attached the written agreement or correspondence to the case file.")
    else:
        supporting.append("The obligations in dispute are described only at a high level in the case file.")
    demo_docs = [d.get("filename") for d in (case.get("documents") or [])[:2]]
    demo = _stamp({
        "issues": [
            {
                "title": "Possible dispute over obligations",
                "description": (
                    "Based on the recorded facts, the parties may disagree about what "
                    "each side is required to do. The exact obligations depend on the "
                    "agreement terms and applicable law, which require verification."
                ),
                "category": case.get("case_type") or "contract",
                "confidence": "medium",
                "supporting_facts": supporting,
                "related_documents": demo_docs,
                "missing_information": [
                    "The signed agreement and its key terms",
                    "Any written notice or correspondence between the parties",
                ],
                "impact": "If this issue holds it could affect what each party is owed or "
                           "required to do; how much depends on the verified terms.",
                "provenance": "AI_INTERPRETATION",
            },
        ] if case.get("description") or demo_docs else [],
        "note": _demo_note("issue detection"),
    }, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# 3b. Information gap analysis
# --------------------------------------------------------------------------

_DEMO_GAPS_BY_TYPE = {
    "employment": [
        ("Missing employment agreement or contract", "Its terms define the role, notice period, and any restrictive or payment obligations.", "Employment agreement"),
        ("Missing termination date and reason", "Whether a termination was lawful often turns on the exact date and the stated reason.", "Termination-related claim"),
        ("Missing written notice of termination", "Written notice is commonly required and its absence can change the claim.", "Termination-related claim"),
    ],
    "tenant/landlord": [
        ("Missing signed lease agreement", "Its clauses set rent, notice, deposit and condition obligations.", "Deposit or lease dispute"),
        ("Missing move-in / move-out inspection reports", "They determine who is responsible for any damage or condition dispute.", "Deposit or lease dispute"),
        ("Missing itemized statement of deductions", "Whether deductions were lawful often hinges on a written, itemized statement.", "Deposit or lease dispute"),
    ],
    "consumer": [
        ("Missing purchase receipt or invoice", "It proves what was bought, when, and for how much.", "Consumer claim"),
        ("Missing written warranty or returns policy", "It defines what remedy the seller offered and for how long.", "Consumer claim"),
        ("Missing correspondence with the seller", "It records promises, complaints, and the seller's response.", "Consumer claim"),
    ],
    "contract": [
        ("Missing signed contract and amendments", "Its terms define the obligations allegedly breached.", "Contract dispute"),
        ("Missing written correspondence about the breach", "It shows what each side said and when.", "Contract dispute"),
    ],
}


def detect_information_gaps(case: dict) -> dict:
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

{_rich_context(case)}

Identify missing information that could materially change the analysis of this case.
Return JSON:
{{
  "gaps": [
    {{
      "question": "what is missing, phrased concretely (e.g. 'Missing employment agreement')",
      "why_it_matters": "how this missing item could materially change the analysis",
      "priority": "high|medium|low",
      "related_issue": "title of an issue listed above that this gap affects, or an empty string",
      "how_to_find": "a practical way the user can obtain this information (ask the other party, request records, check documents already uploaded, etc.)"
    }}
  ],
  "note": "brief note on what was considered"
}}
Only list gaps that genuinely matter for this case. Never invent documents, laws, or citations."""
    doc_names = " ".join((d.get("filename") or "").lower()
                         for d in (case.get("documents") or [])).lower()
    demo_gaps = _DEMO_GAPS_BY_TYPE.get((case.get("case_type") or "").strip().lower())
    if not demo_gaps:
        demo_gaps = [
            ("Missing documents that evidence the agreement or dispute", "The documents define the obligations, dates, and amounts at issue.", "Possible dispute over obligations"),
            ("Missing key dates in the timeline", "Dates can matter for deadlines and limitation periods.", "Possible dispute over obligations"),
        ]
    gaps = []
    for question, why, related in demo_gaps:
        # A "missing" item already covered by an uploaded document is not missing.
        subject = question.lower().replace("missing ", "").replace("missing", "")
        words = [w for w in subject.split() if len(w) > 4]
        if words and any(w in doc_names for w in words):
            continue
        gaps.append({
            "question": question,
            "why_it_matters": why,
            "priority": "high" if question.startswith("Missing signed") or question.startswith("Missing employment") else "medium",
            "related_issue": related,
            "how_to_find": "Check the documents already uploaded, ask the other party in writing, or request official records.",
        })
    demo = _stamp({"gaps": gaps, "note": _demo_note("information-gap analysis")}, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# 4. Risk analysis
# --------------------------------------------------------------------------

def assess_risks(case: dict) -> dict:
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Assess risks as JSON:
{{
  "risks": [
    {{
      "title": "...",
      "description": "...",
      "likelihood": "low|medium|high",
      "impact": "low|medium|high",
      "overall_risk": "low|medium|high",
      "mitigation": "practical step to reduce the risk",
      "provenance": "AI_INTERPRETATION"
    }}
  ],
  "overall_risk": "low|medium|high",
  "summary": "2-3 sentences summarizing the risk picture",
  "note": "..."
}}
Be honest about uncertainty. Never invent laws or citations."""
    demo = _stamp({
        "risks": [
            {
                "title": "Unverified factual basis",
                "description": "Several key facts have not been confirmed by documents or "
                               "independent sources, so conclusions built on them may shift.",
                "likelihood": "medium",
                "impact": "medium",
                "overall_risk": "medium",
                "mitigation": "Gather documents that corroborate the key facts.",
                "provenance": "AI_INTERPRETATION",
            },
        ] if case.get("description") else [],
        "overall_risk": "medium",
        "summary": "In demo mode the risk picture is assessed from the limited information "
                   "currently on file; it will change as documents and facts are added.",
        "note": _demo_note("risk assessment"),
    }, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# 4b. Explainable risk engine (Phase 7)
#
# Scores are computed deterministically from the structured case record
# (issues, evidence, deadlines, gaps, negotiation prep, timeline) — they are
# NOT an LLM guess. The AI layer only writes the explanation (reason,
# supporting/mitigating factors, recommended action) grounded in those
# figures. Scores measure the strength of the case record, never legal
# probabilities.
# --------------------------------------------------------------------------

RISK_DIMENSIONS = (
    ("legal", "Legal Risk"),
    ("evidence", "Evidence Risk"),
    ("deadline", "Deadline Risk"),
    ("financial", "Financial Risk"),
    ("negotiation", "Negotiation Risk"),
    ("procedural", "Procedural Risk"),
    ("information_gap", "Information Gap Risk"),
)

RISK_WEIGHTS = {
    "legal": 1.0,
    "evidence": 1.0,
    "deadline": 0.9,
    "financial": 0.8,
    "negotiation": 0.8,
    "procedural": 0.7,
    "information_gap": 0.9,
}

LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _risk_level(score: int) -> str:
    if score >= 75:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _clamp(score: int) -> int:
    return max(0, min(100, score))


def _risk_scores(case: dict) -> dict:
    """Deterministic engine: compute a 0-100 score per dimension from the
    structured case record. Every figure here comes from real case data."""
    issues = case.get("issues") or []
    evidence = case.get("evidence") or []
    gaps = case.get("gaps") or []
    deadlines = case.get("deadlines") or []
    timeline = case.get("timeline") or []
    prep = case.get("prep") or {}
    docs = case.get("documents") or []
    description = (case.get("description") or "").lower()
    status = (case.get("status") or "draft").lower()

    # Legal risk — weighted by issue confidence.
    legal = sum({"high": 14, "medium": 7, "low": 3}.get((i.get("confidence") or "medium"), 7)
                for i in issues)
    if status == "action_required":
        legal += 15
    if not issues:
        legal = 10

    # Evidence risk — unverified/disputed share of the record.
    total = len(evidence)
    verified = sum(1 for e in evidence if e.get("verification") == "verified")
    disputed = sum(1 for e in evidence if e.get("verification") == "disputed")
    unverified_high = sum(1 for e in evidence
                          if e.get("verification") != "verified" and e.get("importance") == "high")
    if total == 0:
        evidence_score = 55 if issues else 20
    else:
        evidence_score = round(((total - verified) / total) * 70) + disputed * 15 + unverified_high * 5

    # Deadline risk — overdue/missed and near-term deadlines.
    deadline_score = 0
    for d in deadlines:
        days_left = d.get("days_left")
        d_status = d.get("status") or "pending"
        if d_status == "missed" or (days_left is not None and days_left < 0):
            deadline_score += 28
        elif days_left is not None and days_left <= 7:
            deadline_score += 18
        elif days_left is not None and days_left <= 30:
            deadline_score += 8
    deadline_score += sum(1 for t in timeline if (t.get("event_type") or "") == "deadline") * 5
    if not deadlines and not any(t.get("event_type") == "deadline" for t in timeline):
        deadline_score = 20  # no known deadlines can hide exposure

    # Financial risk — monetary stakes evidenced in the record.
    money_keywords = ("$", "€", "£", "₹", "deposit", "rent", "salary", "wages", "compensation",
                      "refund", "damages", "fee", "payment", "invoice", "amount")
    hits = sum(1 for kw in money_keywords if kw in description)
    financial = 15 + min(hits, 6) * 8
    financial += min(sum(1 for t in timeline if (t.get("event_type") or "") == "payment"), 4) * 6
    if (case.get("case_type") or "").lower() in ("financial", "consumer", "property",
                                                  "tenant/landlord", "tenant_landlord"):
        financial += 10

    # Negotiation risk — preparedness for the conversation.
    strategy = (prep.get("strategy") or "").strip()
    counterpart = (prep.get("counterpart_analysis") or "").strip()
    if not prep:
        negotiation = 65
    elif not strategy or not counterpart:
        negotiation = 50
    else:
        negotiation = 30
    if prep and (prep.get("goals") or "").strip():
        negotiation = max(10, negotiation - 10)

    # Procedural risk — stage, status, completeness of the record.
    procedural = {"draft": 40, "analysis_in_progress": 45, "analysis_complete": 30,
                  "action_required": 60, "resolved": 15, "archived": 10}.get(status, 40)
    if not docs:
        procedural += 15
    if not (case.get("jurisdiction") or "").strip():
        procedural += 10

    # Information gap risk — open gaps weighted by priority.
    gap_score = sum({"high": 22, "medium": 12, "low": 5}.get((g.get("priority") or "medium"), 10)
                    for g in gaps if (g.get("status") or "open") == "open")
    if not gaps:
        gap_score = 20

    return {
        "legal": _clamp(legal),
        "evidence": _clamp(evidence_score),
        "deadline": _clamp(deadline_score),
        "financial": _clamp(financial),
        "negotiation": _clamp(negotiation),
        "procedural": _clamp(procedural),
        "information_gap": _clamp(gap_score),
    }


def _demo_dimension(case: dict, key: str, score: int):
    """Deterministic, data-grounded demo explanation for one dimension."""
    issues = case.get("issues") or []
    evidence = case.get("evidence") or []
    gaps = case.get("gaps") or []
    deadlines = case.get("deadlines") or []
    timeline = case.get("timeline") or []
    prep = case.get("prep") or {}
    docs = case.get("documents") or []
    description = (case.get("description") or "").lower()
    supporting = []
    mitigating = []

    if key == "legal":
        open_issues = [i for i in issues if (i.get("status") or "open") in ("open", "investigating")]
        supporting = [f"{len(open_issues)} open potential issue(s) on file"]
        supporting += [f"{i.get('title', '')} (confidence: {i.get('confidence', 'medium')})"
                       for i in open_issues[:4]]
        mitigating = [f"{len(issues) - len(open_issues)} issue(s) already closed or resolved"] \
            if len(issues) > len(open_issues) else []
        reason = (
            f"The case record lists {len(issues)} potential issue(s); {len(open_issues)} are "
            "still open. The score reflects how many issues are on file and how confidently "
            "they are assessed — not legal certainty."
        )
        action = "Verify the highest-confidence open issues against documents, then decide which need professional review."
    elif key == "evidence":
        verified = sum(1 for e in evidence if e.get("verification") == "verified")
        disputed = sum(1 for e in evidence if e.get("verification") == "disputed")
        supporting = [f"{len(evidence)} evidence item(s) on file"]
        if evidence:
            supporting.append(f"{len(evidence) - verified - disputed} not yet verified")
        if disputed:
            supporting.append(f"{disputed} disputed")
        mitigating = [f"{verified} verified"] if verified else []
        if not evidence:
            reason = "No evidence has been logged for this case, so the key facts cannot yet be corroborated."
        else:
            reason = (f"{len(evidence) - verified} of {len(evidence)} evidence items are not "
                      "verified. Unverified or disputed evidence weakens every conclusion built on it.")
        action = "Upload the documents behind the key facts and mark each item verified only when you hold the original."
    elif key == "deadline":
        overdue = [d for d in deadlines if (d.get("status") or "pending") == "missed"
                   or (d.get("days_left") is not None and d.get("days_left") < 0)]
        soon = [d for d in deadlines if (d.get("days_left") is not None and 0 <= d.get("days_left") <= 7)]
        supporting = []
        for d in overdue[:3]:
            supporting.append(f"Overdue: {d.get('title', '')}")
        for d in soon[:3]:
            supporting.append(f"Due within 7 days: {d.get('title', '')}")
        if not supporting:
            supporting = ["No overdue or imminent deadlines on file"]
        if not deadlines:
            reason = "No deadlines have been recorded, so time-based exposure is unknown."
        elif overdue or soon:
            reason = (f"{len(overdue)} deadline(s) overdue and {len(soon)} due within a week — "
                      "these carry the most time pressure.")
        else:
            reason = (f"{len(deadlines)} deadline(s) on file; none are overdue or due within a "
                      "week, but they still shape how quickly decisions may need to be made.")
        action = "Confirm every due date against the actual documents and set reminders well before each one."
    elif key == "financial":
        money_keywords = ("$", "€", "£", "₹", "deposit", "rent", "salary", "wages", "compensation",
                          "refund", "damages", "fee", "payment", "invoice", "amount")
        hits = [kw for kw in money_keywords if kw in description]
        payments = sum(1 for t in timeline if (t.get("event_type") or "") == "payment")
        supporting = []
        if hits:
            supporting.append(f"Monetary terms appear in the case description ({', '.join(hits[:5])})")
        if payments:
            supporting.append(f"{payments} payment event(s) on the timeline")
        if not supporting:
            supporting = ["No explicit monetary amounts are recorded yet"]
        reason = (
            "The record shows monetary stakes" if (hits or payments) else
            "The amounts at stake have not been quantified in the record, which makes financial exposure unclear."
        )
        action = "Quantify the amounts at stake and record them (claim, owed sum, deposits) so the exposure is explicit."
    elif key == "negotiation":
        strategy = (prep.get("strategy") or "").strip()
        counterpart = (prep.get("counterpart_analysis") or "").strip()
        if not prep:
            supporting = ["No negotiation preparation has been saved for this case"]
            reason = "Nothing is prepared for a negotiation: objectives, limits and the other side's likely position are undefined."
        elif not strategy or not counterpart:
            supporting = ["Negotiation prep exists but is incomplete"]
            reason = "Some preparation exists, but the strategy or the other side's likely position is still missing."
        else:
            supporting = ["Negotiation strategy and counterpart analysis are on file"]
            reason = "A negotiation plan exists; the residual risk is execution and unknown counterparty moves."
        mitigating = ["Preparation brief saved"] if prep else []
        action = "Define your objective, minimum acceptable outcome and walk-away position before any conversation."
    elif key == "procedural":
        status = (case.get("status") or "draft").lower()
        supporting = [f"Case stage: {case.get('stage') or 'not set'}", f"Status: {status.replace('_', ' ')}"]
        if not docs:
            supporting.append("No documents uploaded")
        if not (case.get("jurisdiction") or "").strip():
            supporting.append("Jurisdiction not set")
        reason = ("The case is early in its procedural life" if status in ("draft", "analysis_in_progress")
                  else f"The case status is '{status.replace('_', ' ')}', which shapes the procedural picture.")
        action = "Complete the jurisdiction and document record; keep the stage and status current as things move."
    else:  # information_gap
        open_gaps = [g for g in gaps if (g.get("status") or "open") == "open"]
        high = sum(1 for g in open_gaps if g.get("priority") == "high")
        supporting = [f"{len(open_gaps)} open information gap(s)"]
        if high:
            supporting.append(f"{high} high priority")
        for g in open_gaps[:3]:
            supporting.append(f"- {g.get('question', '')}")
        mitigating = [f"{len(gaps) - len(open_gaps)} gap(s) already closed"] if len(gaps) > len(open_gaps) else []
        reason = (f"{len(open_gaps)} piece(s) of information that could materially change the analysis "
                  "are still missing" if open_gaps else "No open information gaps recorded.")
        action = "Close the highest-priority gaps first — they can change the whole analysis."

    return {
        "supporting_factors": supporting or [],
        "mitigating_factors": mitigating or [],
        "reason": reason,
        "recommended_action": action,
    }


def _dimension_changes(previous: dict, dimensions: list) -> list:
    """Diff the current assessment against the previous snapshot."""
    if not previous:
        return []
    prev_by_key = {d.get("key"): d for d in (previous.get("dimensions") or [])}
    changes = []
    for d in dimensions:
        prev = prev_by_key.get(d.get("key"))
        if not prev:
            continue
        old_level, new_level = prev.get("level"), d.get("level")
        if old_level == new_level:
            continue
        direction = "improved" if LEVEL_ORDER.get(new_level, 2) < LEVEL_ORDER.get(old_level, 2) else "worsened"
        changes.append({
            "key": d.get("key"),
            "label": d.get("label"),
            "previous_level": old_level,
            "current_level": new_level,
            "direction": direction,
        })
    if dimensions:
        current_overall = _risk_level(round(
            sum(d["score"] * RISK_WEIGHTS.get(d["key"], 1.0) for d in dimensions) /
            sum(RISK_WEIGHTS.get(d["key"], 1.0) for d in dimensions)
        ))
    else:
        current_overall = "low"
    old_overall = previous.get("overall_level")
    if old_overall and old_overall != current_overall:
        changes.append({
            "key": "overall",
            "label": "Overall risk",
            "previous_level": old_overall,
            "current_level": current_overall,
            "direction": "improved" if LEVEL_ORDER.get(current_overall, 2) < LEVEL_ORDER.get(old_overall, 2) else "worsened",
        })
    return changes


def analyze_case_risks(case: dict, previous: dict = None) -> dict:
    """Phase-7 explainable risk analysis.

    The engine computes deterministic scores from the structured case record;
    the AI layer explains them. Returns dimensions with score/level/reason/
    supporting_factors/mitigating_factors/recommended_action plus the diff
    against `previous`."""
    scores = _risk_scores(case)
    overall = round(sum(scores[k] * RISK_WEIGHTS[k] for k in scores) / sum(RISK_WEIGHTS.values()))
    overall_level = _risk_level(overall)

    demo_dims = []
    for key, label in RISK_DIMENSIONS:
        score = scores[key]
        demo_dims.append({
            "key": key,
            "label": label,
            "score": score,
            "level": _risk_level(score),
            **_demo_dimension(case, key, score),
        })

    prompt = f"""{_case_context(case)}

Engine-computed risk scores (0-100) from the structured case record — do not change these:
{json.dumps({d['key']: d['score'] for d in demo_dims}, indent=2)}

For each dimension return an explanation as JSON:
{{
  "dimensions": [
    {{"key": "legal|evidence|deadline|financial|negotiation|procedural|information_gap",
      "reason": "why this level, grounded in the case record",
      "supporting_factors": ["..."],
      "mitigating_factors": ["..."],
      "recommended_action": "one practical step"}}
  ],
  "summary": "2-3 sentences on the overall risk picture",
  "note": "..."
}}
Explain scores as an assessment of the case record, never as legal probabilities.
Never invent laws, citations, or guarantees."""
    demo = _stamp({
        "overall_score": overall,
        "overall_level": overall_level,
        "summary": (
            f"The current record scores {overall}/100 ({overall_level.upper()}). "
            "This reflects the completeness and strength of the case record — "
            "issues on file, evidence verification, deadlines, gaps and preparation "
            "— not the probability of any legal outcome."
        ),
        "dimensions": demo_dims,
        "note": _demo_note("risk analysis"),
    }, "demo")

    result = _complete(prompt, demo)
    dimensions = []
    for base in demo_dims:
        explained = next((d for d in (result.get("dimensions") or [])
                          if d.get("key") == base["key"]), {})
        dimensions.append({
            **base,
            "reason": (explained.get("reason") or base["reason"]).strip(),
            "supporting_factors": explained.get("supporting_factors") or base["supporting_factors"],
            "mitigating_factors": explained.get("mitigating_factors") or base["mitigating_factors"],
            "recommended_action": (explained.get("recommended_action") or base["recommended_action"]).strip(),
        })
    return {
        "overall_score": overall,
        "overall_level": overall_level,
        "summary": (result.get("summary") or demo["summary"]).strip(),
        "dimensions": dimensions,
        "changes": _dimension_changes(previous, dimensions),
        "mode": result.get("mode"),
        "note": result.get("note"),
        "disclaimer": LEGAL_DISCLAIMER,
    }


# --------------------------------------------------------------------------
# 5. What-if scenarios
# --------------------------------------------------------------------------

SCENARIO_ROW_ORDER = ("risk", "evidence", "issues", "advantages", "disadvantages",
                      "information_gaps", "negotiation_position", "next_steps")

SCENARIO_ROW_LABELS = {
    "risk": "Risk",
    "evidence": "Evidence",
    "issues": "Issues",
    "advantages": "Advantages",
    "disadvantages": "Disadvantages",
    "information_gaps": "Information gaps",
    "negotiation_position": "Negotiation position",
    "next_steps": "Next steps",
}


def generate_scenario(case: dict, scenario: dict) -> dict:
    """Phase-8 scenario analysis. Compares the scenario's facts against the
    current case record and labels the result as scenario-based analysis."""
    facts_block = "\n".join(
        f"- {f.get('text', '')}" for f in (scenario.get("facts") or [])[:20]
    ) or "None provided."
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Scenario name: {scenario.get('name', '')}
Scenario description: {scenario.get('description', '')}
Assumptions / parameters: {scenario.get('parameters', '')}
Changed / assumed facts in this scenario:
{facts_block}

Analyze this what-if scenario as JSON:
{{
  "outcome": "3-5 sentences on the most plausible path under these assumptions, hedged",
  "potential_issues": ["new or changed legal issues this scenario would raise"],
  "risk_changes": ["how each relevant risk dimension may move vs the current case"],
  "evidence_requirements": ["documents or proof this scenario would require"],
  "negotiation_leverage": ["how the scenario changes your negotiating position"],
  "next_steps": ["practical steps if this scenario were pursued"],
  "unknown_information": ["facts that would change the analysis"],
  "risk_level": "low|medium|high"
}}
This is Scenario-Based AI Analysis — an exploration, never a guaranteed prediction.
Never guarantee outcomes and never invent laws or citations."""
    open_issues = [i.get("title", "") for i in (case.get("issues") or [])[:4]]
    demo = _stamp({
        "outcome": (
            f"For scenario '{scenario.get('name', 'this scenario')}', the most plausible path "
            "depends on facts not yet verified. Under the stated assumptions the situation may "
            "evolve in several ways; test this scenario against the actual documents and dates "
            "in the case before relying on it."
        ),
        "potential_issues": (
            [f"{t} — remains open unless this scenario resolves it" for t in open_issues]
            or ["No open issues in the case record to carry into this scenario."]
        ),
        "risk_changes": [
            "Risk moves only where the changed facts are verified — unverified assumptions do not reduce risk."
        ],
        "evidence_requirements": [
            "Documents supporting the facts that differ from the current record",
            "Verification of the dates and amounts involved",
        ],
        "negotiation_leverage": [
            "Leverage depends on how the other side values the changed facts — quantify it before negotiating."
        ],
        "next_steps": [
            "Verify each assumption in this scenario against the evidence on file.",
            "Re-run the risk analysis after verification to measure the impact.",
        ],
        "unknown_information": [
            "Which assumptions hold in reality",
            "How the other side would actually respond",
        ],
        "risk_level": "medium",
        "note": _demo_note("scenario analysis"),
    }, "demo")
    return _complete(prompt, demo)


def _case_risk_level(case: dict) -> str:
    """Overall risk level for the current scenario, from the real record."""
    risks = case.get("risks") or []
    if any(r.get("overall_risk") == "critical" for r in risks):
        return "critical"
    if any(r.get("overall_risk") == "high" for r in risks):
        return "high"
    return "medium"


def _current_scenario_rows(case: dict) -> dict:
    """Honest current-scenario column built from the real case record."""
    issues = case.get("issues") or []
    evidence = case.get("evidence") or []
    gaps = case.get("gaps") or []
    open_gaps = [g for g in gaps if (g.get("status") or "open") == "open"]
    verified = sum(1 for e in evidence if e.get("verification") == "verified")
    risk_level = _case_risk_level(case)
    high_risks = sum(1 for r in (case.get("risks") or []) if r.get("overall_risk") == "high")
    return {
        "risk": f"Assessed {risk_level.upper()} from the case record ({high_risks} high-risk item(s)).",
        "evidence": f"{verified} of {len(evidence)} evidence item(s) verified." if evidence
                    else "No evidence logged yet.",
        "issues": f"{len(issues)} potential issue(s) on file." if issues
                  else "No potential issues on file.",
        "advantages": "The position rests on the facts and documents currently on file.",
        "disadvantages": "The record is still developing; unverified items can shift the picture.",
        "information_gaps": f"{len(open_gaps)} open information gap(s).",
        "negotiation_position": "Baseline — the position reflects current preparation only.",
        "next_steps": "Continue gathering and verifying evidence before committing to a path.",
    }


def _scenario_column_rows(s: dict) -> dict:
    """Scenario column from its stored analysis (honest 'not analyzed yet' otherwise)."""
    analysis = s.get("analysis") or {}
    if not analysis:
        return {row: "Run the scenario analysis to populate this row." for row in SCENARIO_ROW_ORDER}
    return {
        "risk": f"Assessed {str(s.get('risk_level') or analysis.get('risk_level') or 'medium').upper()} for this scenario.",
        "evidence": "; ".join(analysis.get("evidence_requirements") or ["Verify the changed facts."]),
        "issues": "; ".join(analysis.get("potential_issues") or ["No scenario-specific issues surfaced."]),
        "advantages": "; ".join(analysis.get("opportunities") or analysis.get("negotiation_leverage")
                                 or ["See the scenario analysis."]),
        "disadvantages": "; ".join(analysis.get("risks") or ["See the scenario analysis."]),
        "information_gaps": "; ".join(analysis.get("unknown_information") or analysis.get("key_unknowns")
                                      or ["Unknowns are listed in the analysis."]),
        "negotiation_position": "; ".join(analysis.get("negotiation_leverage")
                                           or ["Depends on the scenario assumptions."]),
        "next_steps": "; ".join(analysis.get("next_steps") or analysis.get("recommended_steps")
                                 or ["Run the scenario analysis first."]),
    }


def compare_scenarios(case: dict, scenarios: list) -> dict:
    """Phase-8 comparison table: Current scenario + each selected scenario as
    columns, with the eight spec rows. Columns/rows are derived from real case
    data and each scenario's stored analysis — never fabricated."""
    columns = [{
        "id": "current",
        "name": "Current scenario",
        "summary": "Continue with the case exactly as recorded.",
        "risk_level": _case_risk_level(case),
    }]
    for s in scenarios:
        columns.append({
            "id": str(s.get("id", s.get("name", "s"))),
            "name": s.get("name", "Scenario"),
            "summary": (s.get("description") or s.get("parameters") or "")[:200],
            "risk_level": s.get("risk_level") or (s.get("analysis") or {}).get("risk_level") or "medium",
        })
    demo_rows = {"current": _current_scenario_rows(case)}
    for s in scenarios:
        demo_rows[str(s.get("id", s.get("name", "s")))] = _scenario_column_rows(s)

    scenario_block = "\n".join(
        json.dumps({"id": str(s.get("id")), "name": s.get("name"),
                    "description": s.get("description"), "parameters": s.get("parameters"),
                    "facts": s.get("facts")}, indent=2)
        for s in scenarios
    )
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Scenarios to compare:
{scenario_block}

Produce a professional comparison as JSON — rows keyed by column id, and each
column's value keyed by row name. Column ids: 'current' for the case as-is, and
the numeric scenario ids shown above.
{{
  "rows": {{
    "current": {{"risk": "...", "evidence": "...", "issues": "...",
                 "advantages": "...", "disadvantages": "...",
                 "information_gaps": "...", "negotiation_position": "...",
                 "next_steps": "..."}},
    "<scenario id>": {{same keys}}
  }},
  "trade_offs": "2-4 sentences on the key trade-offs",
  "recommendation": "2-3 hedged sentences on which path looks more favorable and why",
  "note": "..."
}}
This is Scenario-Based AI Analysis — exploration, never a guaranteed prediction.
Never guarantee outcomes and never invent laws or citations."""
    names = ", ".join(s.get("name", "unnamed") for s in scenarios) or "the scenarios"
    demo = _stamp({
        "columns": columns,
        "rows": demo_rows,
        "row_labels": SCENARIO_ROW_LABELS,
        "trade_offs": (f"The trade-offs between {names} depend on facts that are not yet "
                       "verified; each path trades certainty for a different outcome profile."),
        "recommendation": ("No reliable recommendation can be made until the case facts and "
                           "documents are complete — verify the assumptions of each scenario first."),
        "note": _demo_note("scenario comparison"),
    }, "demo")
    result = _complete(prompt, demo)
    # Merge AI row text over the deterministic scaffold when it parses.
    rows = demo_rows
    ai_rows = result.get("rows")
    if isinstance(ai_rows, dict):
        for col_id, row_map in ai_rows.items():
            if col_id not in rows or not isinstance(row_map, dict):
                continue
            for row_key, text in row_map.items():
                if row_key in rows[col_id] and isinstance(text, str) and text.strip():
                    rows[col_id][row_key] = text
    result["rows"] = rows
    result["columns"] = columns
    result["row_labels"] = SCENARIO_ROW_LABELS
    return result


# --------------------------------------------------------------------------
# 6. Negotiation
# --------------------------------------------------------------------------

def analyze_negotiation_prep(case: dict, prep: dict = None) -> dict:
    """Phase-9 negotiation copilot: produce the full preparation plan.

    The plan is grounded in the case record plus the user's objective inputs
    (objective, desired outcome, minimum acceptable, constraints, channel).
    """
    prep = prep or {}
    inputs = {
        "objective": (prep.get("objective") or "").strip()[:400],
        "desired_outcome": (prep.get("desired_outcome") or "").strip()[:400],
        "minimum_acceptable": (prep.get("minimum_acceptable") or "").strip()[:400],
        "counterpart_position": (prep.get("counterpart_position") or "").strip()[:400],
        "constraints": (prep.get("constraints") or "").strip()[:400],
        "channel": (prep.get("channel") or "").strip(),
    }
    input_block = "\n".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in inputs.items() if v)
    if not input_block:
        input_block = "(No objective inputs saved yet — draft from the case record.)"

    evidence_titles = [e.get("title", "") for e in (case.get("evidence") or [])[:6]]
    evidence_block = "\n".join(f"- {t}" for t in evidence_titles) or "No evidence items on file."

    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Evidence on file:
{evidence_block}

Negotiation objective inputs from the user:
{input_block}

Produce a complete negotiation preparation plan as JSON:
{{
  "strategy": "overall strategy in 3-4 sentences, anchored on the objective inputs",
  "opening_position": "what to state first, including your opening number or terms if monetary",
  "key_arguments": ["the strongest arguments for your position, tied to the case facts"],
  "supporting_evidence": ["the evidence on file that backs each key argument"],
  "likely_objections": ["the other side's most likely objections"],
  "responses": ["a direct, professional response to each objection, in order"],
  "potential_concessions": ["things you could offer that cost you little"],
  "walk_away": "what should make you walk away — anchored to your minimum acceptable outcome",
  "questions_to_ask": ["questions to ask to learn their real priorities"],
  "goals": ["..."],
  "batna": "best alternative to a negotiated agreement, hedged",
  "interests": ["underlying interests of both sides"],
  "red_lines": ["things to avoid accepting"],
  "counterpart_analysis": "what the other side likely wants, hedged",
  "note": "..."
}}
Never invent laws or citations; never guarantee outcomes. Do not propose deceptive claims or threats."""

    min_line = inputs["minimum_acceptable"] or "your minimum acceptable outcome"
    demo = _stamp({
        "strategy": (
            "Open from interests, present your objective clearly, and anchor your terms on the "
            "evidence on file. Test their priorities with questions before conceding anything. "
            "Keep your minimum acceptable outcome as the floor and your walk-away ready."
        ),
        "opening_position": (
            f"Restate the objective — {inputs['objective'] or 'a fair resolution of the case'} — and "
            "set out your opening terms, referencing the supporting evidence in the case record."
        ),
        "key_arguments": [
            "The record supports the position (see the facts and issues on file).",
            "A negotiated resolution is faster and less costly than escalation.",
        ],
        "supporting_evidence": evidence_titles or ["No evidence logged yet — gather documents first."],
        "likely_objections": [
            "They may dispute the facts or the amounts involved.",
            "They may claim the issue is not worth discussing.",
        ],
        "responses": [
            "Ask which specific fact or figure they dispute and offer to share the supporting record.",
            "Explain the concrete cost and delay of the alternative path, in neutral terms.",
        ],
        "potential_concessions": ["Flexibility on timing or payment structure"],
        "walk_away": (
            f"Walk away rather than accept less than {min_line} — or anything that requires "
            "agreeing to facts that are not true."
        ),
        "questions_to_ask": [
            "What matters most to them in a resolution?",
            "What would make an agreement easy for them to accept?",
        ],
        "goals": ["Resolve the dispute on acceptable terms", "Protect the key interests on file"],
        "batna": "Falling back to formal proceedings, which is likely slower, costlier, and "
                 "more uncertain than negotiation.",
        "interests": ["Certainty and a timely resolution", "Minimizing cost and disruption"],
        "red_lines": ["Agreeing to facts that are not true", "Waiving rights without understanding them"],
        "counterpart_analysis": "The other side likely wants certainty too; their exact "
                                "priorities are not yet known.",
        "note": _demo_note("negotiation prep"),
    }, "demo")
    return _complete(prompt, demo)


def generate_negotiation_message(case: dict, prep: dict, channel: str = "email",
                                 tone: str = "professional", focus: str = "") -> dict:
    """Phase-9 message generator: email / formal letter / WhatsApp-style /
    meeting talking points, in one of four tones. Never deceptive or threatening."""
    prep = prep or {}
    objective = (prep.get("objective") or case.get("description") or "the matter we discussed").strip()[:300]
    channel = (channel or "email").strip()
    tone = (tone or "professional").strip()
    focus = (focus or "").strip()[:300]

    tone_guide = {
        "professional": "courteous, measured, and businesslike",
        "firm": "clear and resolute about your terms, without hostility",
        "collaborative": "warm, solution-oriented, and open to finding common ground",
        "neutral": "plain, factual, and unemotional",
    }.get(tone, "courteous, measured, and businesslike")
    channel_guide = {
        "email": "a concise professional email (with a subject line)",
        "letter": "a formal letter (with a subject line and salutation)",
        "whatsapp": "a short WhatsApp-style message, plain text, no salutation, under 150 words",
        "meeting": "meeting talking points: a short intro line plus bullet talking points",
    }.get(channel, "a concise professional message")

    prompt = f"""{_case_context(case)}

Negotiation objective: {objective}
Tone: {tone_guide}
Channel: {channel_guide}
Additional focus: {focus or 'none'}

Write a draft message as JSON:
{{
  "subject": "subject line (omit for whatsapp/meeting)",
  "message": "the full message text",
  "talking_points": ["bullets"],
  "note": "1 sentence on how this draft stays truthful and non-threatening"
}}
The draft must never contain deceptive claims, threats, or invented laws — it must stay
consistent with the facts on file in the case."""

    demo_subject = f"Regarding: {case.get('title', '')}" if channel in ("email", "letter") else ""
    demo = _stamp({
        "subject": demo_subject,
        "message": (
            f"I am writing about {objective}. I would like to find a fair and practical way "
            "to resolve this, and I believe an open conversation is the best first step. "
            "Would you be available to discuss the terms and the supporting details? "
            "I am confident we can reach an arrangement that works for both of us."
        ) if channel != "meeting" else (
            f"Goal: {objective}. Points to cover: "
            "1) restate the objective and the facts we rely on; 2) ask what matters most to "
            "them; 3) propose a first set of terms; 4) agree on a next step and a timeline."
        ),
        "talking_points": [
            "Restate the objective and the key facts.",
            "Ask what a good outcome looks like for them.",
            "Propose opening terms tied to the evidence on file.",
            "Agree on the next step and a date.",
        ],
        "note": ("Demo draft — stays factual and non-threatening; verify it against the case "
                  "record before sending."),
    }, "demo")
    return _complete(prompt, demo)


def negotiation_practice(case: dict, history: list, language: str = "en") -> dict:
    """history: [{role: user|assistant, content}] — the practice conversation so far."""
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-16:])
    prompt = f"""{_case_context(case)}

You are now roleplaying in a negotiation PRACTICE session. Reply as the counterparty
in a realistic but professional way, staying consistent with the case facts. Keep
responses under 120 words. Respond in language code '{language}'.

Practice transcript so far:
{transcript}

Return JSON: {{
  "reply": "your roleplayed reply",
  "label": "COUNTERPARTY MOVES: 'offer'|'concession'|'pressure'|'question'|'position'",
  "note": "short coaching tip about how to handle this move"
}}
Never invent laws or citations. Do not guarantee outcomes."""
    demo = _stamp({
        "reply": (
            "I understand your position. From our side, we'd want to see the terms "
            "clarified and a timeline we can both work with before we can agree to "
            "anything further."
        ),
        "label": "COUNTERPARTY MOVES: position",
        "note": "They are signalling openness but anchoring on terms. Ask what specific "
                "terms matter most to them.",
    }, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# 6b. Phase-10 interactive negotiation simulation
#
# A dedicated workflow (separate from the CaseGuide chatbot): the AI roleplays
# the opposing party from an explicit position, and the completed session is
# scored across seven dimensions (1-10) with structured feedback.
# --------------------------------------------------------------------------

EVALUATION_DIMENSIONS = (
    ("argument_strength", "Argument strength"),
    ("evidence_usage", "Evidence usage"),
    ("clarity", "Clarity"),
    ("tone", "Tone"),
    ("persuasiveness", "Persuasiveness"),
    ("risk_awareness", "Risk awareness"),
    ("missed_opportunities", "Missed opportunities"),
)


def simulation_reply(case: dict, messages: list, opponent_position: str = "",
                     language: str = "en") -> dict:
    """The AI acts as the opposing party in the practice negotiation,
    consistent with the case facts and their stated position."""
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages[-16:])
    position = opponent_position.strip() or (
        "The other side is not yet prepared to concede anything substantial; they want a "
        "resolution but are holding firm on their stated terms."
    )
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

You are roleplaying the OPPOSING PARTY in a negotiation practice session.
Their position:
{position}

Stay consistent with the case facts, argue for their position convincingly but
professionally, and do not concede major points easily. Keep responses under 130
words. Respond in language code '{language}'.

Practice transcript so far:
{transcript}

Return JSON: {{
  "reply": "your roleplayed reply as the opposing party",
  "label": "OPPONENT MOVES: 'offer'|'concession'|'pressure'|'question'|'position'",
  "note": "short coaching tip about how to handle this move"
}}
Never invent laws or citations. Do not guarantee outcomes."""
    demo = _stamp({
        "reply": (
            "We've reviewed what you're asking, but we see it differently. We believe our "
            "position is justified by the facts as we understand them, and we can't simply "
            "agree to the terms you've proposed. What we could discuss is a compromise on "
            "the details — can you walk us through what matters most to you?"
        ),
        "label": "OPPONENT MOVES: position",
        "note": "They are holding their position but signalling room to talk. Ask a specific "
                "question to pin down what they value.",
    }, "demo")
    return _complete(prompt, demo)


def _clamp10(score: int) -> int:
    return max(1, min(10, score))


def _demo_evaluation(case: dict, messages: list, opponent_position: str) -> dict:
    """Deterministic demo evaluation, grounded in the actual transcript and
    case record (evidence actually cited, issues, risks)."""
    user_msgs = [m for m in messages if m.get("role") == "user"]
    user_text = " ".join((m.get("content") or "").lower() for m in user_msgs)
    evidence_titles = [e.get("title", "") for e in (case.get("evidence") or [])]
    used_evidence = [t for t in evidence_titles if t and t.lower() in user_text]
    evidence_hits = len(used_evidence)

    polite = sum(1 for w in ("please", "thank", "understand", "appreciate", "would", "could", "open") if w in user_text)
    loaded = sum(1 for w in ("threaten", "you must", "never agree", "i demand") if w in user_text)
    lengths = [len(m.get("content") or "") for m in user_msgs]
    avg_len = (sum(lengths) / len(lengths)) if lengths else 0

    scores = {
        "argument_strength": _clamp10(4 + evidence_hits + max(0, len(user_msgs) - 1)),
        "evidence_usage": _clamp10(3 + evidence_hits * 2),
        "clarity": _clamp10(7 if 60 <= avg_len <= 260 else 5),
        "tone": _clamp10(6 + polite - loaded * 2),
        "persuasiveness": _clamp10(4 + min(5, (evidence_hits + len(user_msgs)) // 2)),
        "risk_awareness": _clamp10(4 + (1 if any(w in user_text for w in
            ("risk", "deadline", "verify", "evidence", "document", "signed")) else 0)
            + (1 if len(user_msgs) >= 2 else 0)),
        "missed_opportunities": _clamp10(10 - evidence_hits - min(3, max(0, len(user_msgs) - 1))),
    }

    missing_evidence = [t for t in evidence_titles if t and t not in used_evidence]
    issue_titles = [i.get("title", "") for i in (case.get("issues") or [])[:3]]
    risk_titles = [r.get("title", "") for r in (case.get("risks") or [])[:3]]

    strengths = ["You engaged with the opposing party and kept the conversation moving."]
    if used_evidence:
        strengths.append(f"You anchored part of your argument in evidence on file ({', '.join(used_evidence[:3])}).")
    if len(user_msgs) >= 3:
        strengths.append("You developed your position over several exchanges rather than giving up after one pushback.")

    improvements = []
    if evidence_hits == 0:
        improvements.append("You argued without citing specific evidence — name the actual documents and records behind each claim.")
    if len(user_msgs) < 3:
        improvements.append("The exchange ended early; longer conversations let you test their position and build a case.")
    if loaded:
        improvements.append("Parts of the conversation read as confrontational; firmness works better than pressure or demands.")
    if not improvements:
        improvements.append("Push further on their priorities — one more round of questions could have produced a concrete offer.")

    evidence_should_have_used = missing_evidence[:4] if missing_evidence else [
        "Any documents that corroborate the amounts and dates in the case record"
    ]
    arguments_missed = [
        f"Address '{t}' head-on instead of waiting for them to raise it" for t in issue_titles
    ] or ["The case record lists no open issues to argue — that itself is worth noting."]
    potential_risks = ([
        f"Risk on file: {t}" for t in risk_titles
    ] or ["Repeating claims without documents risks being seen as unserious."])[:3]
    alternative_responses = [
        f"If they hold firm on '{opponent_position[:80]}', ask which single fact or figure would change their answer.",
        "Offer a small, low-cost concession in exchange for something concrete in writing.",
    ]
    overall = (
        f"Over {len(user_msgs)} exchange(s) you showed {('good use of the evidence' if used_evidence else 'limited use of the evidence')}, "
        f"with {scores['argument_strength']}/10 argument strength and {scores['tone']}/10 tone. "
        "The biggest lever now is grounding every claim in the documents on file and asking "
        "more questions about their priorities."
    )
    return {
        "scores": scores,
        "overall": overall,
        "strengths": strengths,
        "improvements": improvements,
        "evidence_should_have_used": evidence_should_have_used,
        "arguments_missed": arguments_missed,
        "potential_risks": potential_risks,
        "alternative_responses": alternative_responses,
    }


def evaluate_negotiation(case: dict, messages: list, opponent_position: str = "") -> dict:
    """Score the completed simulation 1-10 across the seven dimensions and
    produce structured feedback."""
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages[-24:])
    dims = ", ".join(f"\"{k}\": \"{v}\"" for k, v in EVALUATION_DIMENSIONS)
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

The user practiced a negotiation against an opposing party whose position was:
{opponent_position or '(not stated)'}

Transcript:
{transcript}

Evaluate the USER's performance (not the opponent's) as JSON:
{{
  "scores": {{
    {dims}
  }},
  "overall": "2-3 sentences summarizing the performance",
  "strengths": ["what they did well"],
  "improvements": ["what could improve"],
  "evidence_should_have_used": ["specific evidence from the case they should have cited"],
  "arguments_missed": ["arguments they missed"],
  "potential_risks": ["risks in what they said or agreed to"],
  "alternative_responses": ["suggested alternative responses"],
  "note": "..."
}}
Score each dimension 1-10. Be specific and constructive. Never invent laws or citations."""
    demo = _stamp({
        **_demo_evaluation(case, messages, opponent_position),
        "note": _demo_note("negotiation evaluation"),
    }, "demo")
    result = _complete(prompt, demo)
    # Keep every dimension present even if the AI omitted some.
    base = _demo_evaluation(case, messages, opponent_position)
    scores = {}
    for key, _label in EVALUATION_DIMENSIONS:
        ai_val = (result.get("scores") or {}).get(key)
        if isinstance(ai_val, (int, float)):
            scores[key] = _clamp10(int(ai_val))
        else:
            scores[key] = base["scores"][key]
    result["scores"] = scores
    return result


# --------------------------------------------------------------------------
# 6c. Phase-11 action plan & deadline extraction
# --------------------------------------------------------------------------

def generate_action_plan(case: dict) -> dict:
    """Generate concrete, case-grounded actions — never generic tasks.
    Every action traces to a real gap, issue, risk, evidence item, deadline,
    scenario or negotiation gap in the case record."""
    issues = case.get("issues") or []
    gaps = case.get("gaps") or []
    risks = case.get("risks") or []
    evidence = case.get("evidence") or []
    deadlines = case.get("deadlines") or []
    scenarios = case.get("scenarios") or []
    prep = case.get("prep") or {}

    demo = []
    for g in gaps:
        if (g.get("status") or "open") != "open":
            continue
        demo.append({
            "title": f"Obtain: {g.get('question', '')[:90]}",
            "description": f"Close the information gap described as '{g.get('question', '')}'.",
            "reason": g.get("why_it_matters") or "This information could materially change the analysis.",
            "priority": (g.get("priority") or "medium"),
            "related_issue": g.get("related_issue") or "",
            "required_evidence": g.get("how_to_find") or "Ask for it in writing or request official records.",
            "due_date": "",
        })
    for e in evidence:
        if e.get("verification") == "verified":
            continue
        demo.append({
            "title": f"Verify evidence: {e.get('title', '')}",
            "description": f"Confirm the status of '{e.get('title', '')}' and hold the original.",
            "reason": "The item is not yet verified, so conclusions built on it can shift.",
            "priority": "high" if e.get("importance") == "high" else "medium",
            "related_issue": "",
            "required_evidence": f"Original or a clearly identified copy of: {e.get('title', '')}",
            "due_date": "",
        })
    for i in issues:
        if (i.get("status") or "open") in ("resolved", "not_actionable"):
            continue
        demo.append({
            "title": f"Prepare position on: {i.get('title', '')}",
            "description": "Assemble the documents and dates that support your side of this issue.",
            "reason": f"Open issue assessed with {i.get('confidence', 'medium')} confidence — it shapes the whole case.",
            "priority": "high" if i.get("confidence") == "high" else "medium",
            "related_issue": i.get("title", ""),
            "required_evidence": "Documents and timeline entries that corroborate your version of the facts.",
            "due_date": "",
        })
    for r in risks:
        if r.get("overall_risk") not in ("high", "critical"):
            continue
        demo.append({
            "title": f"Mitigate: {r.get('title', '')}",
            "description": "",
            "reason": "Flagged as a high/critical risk in the case record.",
            "priority": "high",
            "related_issue": "",
            "required_evidence": "",
            "due_date": "",
        })
    for d in deadlines:
        if (d.get("status") or "pending") == "completed":
            continue
        demo.append({
            "title": f"Prepare for deadline: {d.get('title', '')}",
            "description": f"Have your response ready before {d.get('due_date', '')}.",
            "reason": "A tracked date that may carry consequences if missed — verify what it applies to.",
            "priority": "high" if (d.get("days_left") is not None and d.get("days_left") <= 7) else "medium",
            "related_issue": "",
            "required_evidence": "",
            "due_date": d.get("due_date") or "",
        })
    for s in scenarios:
        if not s.get("analyzed"):
            continue
        demo.append({
            "title": f"Decide on scenario: {s.get('name', '')}",
            "description": "Review the scenario analysis and choose whether to pursue it.",
            "reason": "The scenario has been analyzed and represents a concrete alternative path.",
            "priority": "medium",
            "related_issue": "",
            "required_evidence": "Facts that would confirm the scenario's assumptions.",
            "due_date": "",
        })
    if not prep:
        demo.append({
            "title": "Define your negotiation objective",
            "description": "Fill in objective, desired outcome and minimum acceptable outcome.",
            "reason": "No negotiation preparation exists yet, so leverage and walk-away are undefined.",
            "priority": "medium",
            "related_issue": "",
            "required_evidence": "",
            "due_date": "",
        })
    demo = demo[:12]

    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Generate a concrete action plan for this case as JSON:
{{
  "actions": [
    {{"title": "specific action", "description": "what exactly to do",
      "reason": "why — tied to the case record", "priority": "high|medium|low",
      "related_issue": "issue title it serves (or '')",
      "required_evidence": "specific evidence to gather (or '')",
      "due_date": "ISO date if a tracked deadline applies (or '')"}}
  ],
  "note": "..."
}}
Every action must trace to a real gap, issue, risk, evidence item, deadline, scenario or
negotiation gap on file. Do not generate generic tasks like 'keep records organized'.
Never invent laws, citations, or dates."""
    demo_payload = _stamp({"actions": demo, "note": _demo_note("action plan")}, "demo")
    return _complete(prompt, demo_payload)


def extract_deadline_dates(case: dict) -> dict:
    """Extract candidate dates that may matter for deadlines.

    Candidates are review-only (nothing is stored automatically), and the
    extractor never asserts that a date is a legally binding deadline unless
    jurisdiction-specific information in the case supports it."""
    candidates = []
    for doc in (case.get("documents") or []):
        for kd in (doc.get("key_dates") or [])[:8]:
            if not kd.get("date"):
                continue
            if kd.get("kind") == "deadline":
                candidates.append({
                    "title": kd.get("description") or "Deadline mentioned in document",
                    "date": kd["date"],
                    "source": doc.get("filename", "document"),
                    "confidence": "extracted",
                    "note": "Stated as a deadline in the document analysis — check what it applies to.",
                })
            else:
                candidates.append({
                    "title": kd.get("description") or "Date mentioned in document",
                    "date": kd["date"],
                    "source": doc.get("filename", "document"),
                    "confidence": "potential",
                    "note": "A date appears in the document — confirm whether it is a deadline before tracking it.",
                })
    candidates = candidates[:12]

    prompt = f"""{_case_context(case)}

{_facts_context(case)}

Relevant documents:
{json.dumps([{"filename": d.get("filename"), "key_dates": d.get("key_dates")} for d in (case.get("documents") or [])], indent=2)[:3000]}

Extract dates that could matter as deadlines as JSON:
{{
  "candidates": [
    {{"title": "what this date relates to", "date": "YYYY-MM-DD",
      "source": "where it came from", "confidence": "extracted|potential",
      "note": "why it matters and any uncertainty"}}
  ],
  "note": "..."
}}
Never assert that any date is a legally binding deadline unless jurisdiction-specific
information in the case supports it — otherwise say the date needs verification.
Never invent dates or laws."""
    demo = _stamp({
        "candidates": candidates,
        "note": (_demo_note("deadline extraction") if candidates else
                 "No dated deadlines found in the document analyses on file. "
                 "Dates in the case description need manual review — add them below if relevant."),
    }, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# Multilingual demo strings (Phase 12). Demo mode has no translation engine, so
# the canned demo outputs are translated here so AI responses respect the
# selected language even without GEMINI_API_KEY. Live Gemini mode translates
# freely via the prompt's language instruction.
# --------------------------------------------------------------------------

L10N = {
    "hi": {
        "chat_s1": "अभी तक के केस रिकॉर्ड के अनुसार, यह मामला अभी भी तैयार हो रहा है: दर्ज तथ्य सीमित हैं और कई अहम विवरण अभी पुष्टि होने बाकी हैं।",
        "chat_s2": "अब तक दर्ज: {docs} दस्तावेज़, {issues} मुद्दे, {gaps} खुले जानकारी-अंतराल।",
        "chat_s3": "इस प्रश्न से जुड़े दस्तावेज़ और तिथियाँ जोड़ने से मैं अधिक विश्वास के साथ उत्तर दे सकूँगा।",
        "chat_why": "अधूरी फाइलों के आधार पर दिए गए उत्तर भ्रामक हो सकते हैं, इसलिए अनुमान लगाने के बजाय कमियों को चिह्नित किया जाता है।",
        "chat_ev1": "इस प्रश्न से संबंधित दस्तावेज़ों की प्रतियाँ",
        "chat_ev2": "टाइमलाइन में दर्ज (या छूटी हुई) प्रासंगिक तिथियाँ",
        "chat_risk": "अंतर्निहित दस्तावेज़ों की समीक्षा होने तक निष्कर्ष असत्यापित तथ्यों पर टिके रहते हैं।",
        "chat_next": "इस प्रश्न में कौन-से दस्तावेज़ या तिथियाँ शामिल हैं?",
        "chat_step": "प्रासंगिक दस्तावेज़ अपलोड करें या जोड़ें, फिर यह प्रश्न दोबारा पूछें।",
        "chat_f1": "इस मामले को सरल भाषा में सारांशित करें",
        "chat_f2": "मेरे पास अभी कौन-से सबूत कमी हैं?",
        "chat_f3": "अभी मेरे मुख्य जोखिम क्या हैं?",
        "term_def": "'{term}' की सटीक परिभाषा संदर्भ और अधिकार-क्षेत्र पर निर्भर करती है; सामान्यतः यह कानूनी कार्यवाही या अनुबंधों में सामने आने वाली अवधारणा है।",
        "term_simple": "रोज़मर्रा की भाषा में, '{term}' एक कानूनी अवधारणा को दर्शाता है जिसका सटीक अर्थ संदर्भ पर निर्भर करता है।",
        "term_tech": "कानूनी दस्तावेज़ों और तर्कों में, '{term}' अपने तकनीकी कानूनी अर्थ के साथ प्रयोग होता है, जो अधिकार-क्षेत्र और विशिष्ट धारा के अनुसार भिन्न हो सकता है।",
        "term_why": "यह शब्द आमतौर पर कानूनी कार्यवाही या अनुबंधों में आता है क्योंकि सटीक अर्थ अधिकारों और दायित्वों को प्रभावित करता है।",
        "term_imp": "यह शब्द प्रभावित कर सकता है कि व्यक्ति को क्या करना है, वह किसका हकदार है, या दायित्व पूरा न होने पर क्या होगा — विशिष्ट प्रभाव मामले पर निर्भर करता है।",
        "term_ctx": "सटीक अर्थ अधिकार-क्षेत्र और दस्तावेज़ों में शब्द के प्रयोग के अनुसार भिन्न हो सकता है।",
        "term_ex": "संदर्भ जाने बिना उदाहरण विश्वसनीय रूप से नहीं दिया जा सकता।",
        "term_cav": "परिभाषाएँ अधिकार-क्षेत्र के अनुसार भिन्न होती हैं — किसी स्थानीय पेशेवर से पुष्टि करें।",
        "sim_note": "डेमो सरलीकरण — इनलाइन व्याख्याएँ अंग्रेज़ी में हैं। पूरी तरह स्थानीयकृत सरलीकरण के लिए GEMINI_API_KEY जोड़ें।",
    },
    "kn": {
        "chat_s1": "ಇಲ್ಲಿಯವರೆಗಿನ ಕೇಸ್ ದಾಖಲೆಗಳ ಪ್ರಕಾರ, ಈ ಪ್ರಕರಣ ಇನ್ನೂ ಸಿದ್ಧವಾಗುತ್ತಿದೆ: ದಾಖಲಾದ ಸಂಗತಿಗಳು ಸೀಮಿತವಾಗಿವೆ ಮತ್ತು ಪ್ರಮುಖ ವಿವರಗಳು ಇನ್ನೂ ಖಚಿತಪಡಿಸಬೇಕಾಗಿವೆ.",
        "chat_s2": "ಇದುವರೆಗೆ ದಾಖಲಾಗಿದೆ: {docs} ದಾಖಲೆಗಳು, {issues} ಸಮಸ್ಯೆಗಳು, {gaps} ತೆರೆದ ಮಾಹಿತಿ ಅಂತರಗಳು.",
        "chat_s3": "ಈ ಪ್ರಶ್ನೆಗೆ ಸಂಬಂಧಿಸಿದ ದಾಖಲೆಗಳು ಮತ್ತು ದಿನಾಂಕಗಳನ್ನು ಸೇರಿಸಿದರೆ ಹೆಚ್ಚು ವಿಶ್ವಾಸದಿಂದ ಉತ್ತರಿಸಬಲ್ಲೆ.",
        "chat_why": "ಅಪೂರ್ಣ ದಾಖಲೆಗಳ ಆಧಾರದ ಮೇಲಿನ ಉತ್ತರಗಳು ದಾರಿತಪ್ಪಿಸಬಹುದು, ಆದ್ದರಿಂದ ಊಹಿಸುವ ಬದಲು ಅಂತರಗಳನ್ನು ಗುರುತಿಸಲಾಗುತ್ತದೆ.",
        "chat_ev1": "ಈ ಪ್ರಶ್ನೆಗೆ ಸಂಬಂಧಿಸಿದ ದಾಖಲೆಗಳ ಪ್ರತಿಗಳು",
        "chat_ev2": "ಟೈಮ್‌ಲೈನ್ನಲ್ಲಿ ದಾಖಲಾದ (ಅಥವಾ ಇಲ್ಲದ) ಸಂಬಂಧಿತ ದಿನಾಂಕಗಳು",
        "chat_risk": "ಆಧಾರ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸುವವರೆಗೆ ತೀರ್ಮಾನಗಳು ಸಾಬೀತಾಗದ ಸಂಗತಿಗಳ ಮೇಲೆ ನಿಂತಿರುತ್ತವೆ.",
        "chat_next": "ಈ ಪ್ರಶ್ನೆಯಲ್ಲಿ ಯಾವ ದಾಖಲೆಗಳು ಅಥವಾ ದಿನಾಂಕಗಳು ಒಳಗೊಂಡಿವೆ?",
        "chat_step": "ಸಂಬಂಧಿತ ದಾಖಲೆಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ ಅಥವಾ ಜೋಡಿಸಿ, ನಂತರ ಈ ಪ್ರಶ್ನೆಯನ್ನು ಮತ್ತೆ ಕೇಳಿ.",
        "chat_f1": "ಈ ಪ್ರಕರಣವನ್ನು ಸರಳ ಭಾಷೆಯಲ್ಲಿ ಸಾರಾಂಶಿಸಿ",
        "chat_f2": "ನನ್ನ ಬಳಿ ಇನ್ನೂ ಯಾವ ಸಾಕ್ಷ್ಯಗಳು ಇಲ್ಲ?",
        "chat_f3": "ಈಗ ನನ್ನ ಮುಖ್ಯ ಅಪಾಯಗಳು ಯಾವುವು?",
        "term_def": "'{term}' ನ ನಿಖರ ವ್ಯಾಖ್ಯಾನವು ಸಂದರ್ಭ ಮತ್ತು ಅಧಿಕಾರ ಕ್ಷೇತ್ರವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ; ಸಾಮಾನ್ಯವಾಗಿ ಇದು ಕಾನೂನು ವ್ಯವಹಾರಗಳಲ್ಲಿ ಅಥವಾ ಒಪ್ಪಂದಗಳಲ್ಲಿ ಬರುವ ಪರಿಕಲ್ಪನೆಯಾಗಿದೆ.",
        "term_simple": "ದೈನಂದಿನ ಭಾಷೆಯಲ್ಲಿ, '{term}' ಒಂದು ಕಾನೂನು ಪರಿಕಲ್ಪನೆಯನ್ನು ಸೂಚಿಸುತ್ತದೆ, ಅದರ ನಿಖರ ಅರ್ಥ ಸಂದರ್ಭವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ.",
        "term_tech": "ಕಾನೂನು ದಾಖಲೆಗಳು ಮತ್ತು ವಾದಗಳಲ್ಲಿ, '{term}' ಅನ್ನು ಅದರ ತಾಂತ್ರಿಕ ಕಾನೂನು ಅರ್ಥದೊಂದಿಗೆ ಬಳಸಲಾಗುತ್ತದೆ, ಅದು ಅಧಿಕಾರ ಕ್ಷೇತ್ರ ಮತ್ತು ನಿರ್ದಿಷ್ಟ ಷರತ್ತಿಗೆ ತಕ್ಕಂತೆ ಬದಲಾಗಬಹುದು.",
        "term_why": "ಈ ಪದ ಸಾಮಾನ್ಯವಾಗಿ ಕಾನೂನು ವ್ಯವಹಾರಗಳಲ್ಲಿ ಅಥವಾ ಒಪ್ಪಂದಗಳಲ್ಲಿ ಬರುತ್ತದೆ, ಏಕೆಂದರೆ ನಿಖರ ಅರ್ಥವು ಹಕ್ಕುಗಳು ಮತ್ತು ಜವಾಬ್ದಾರಿಗಳ ಮೇಲೆ ಪರಿಣಾಮ ಬೀರುತ್ತದೆ.",
        "term_imp": "ಈ ಪದವು ವ್ಯಕ್ತಿ ಏನು ಮಾಡಬೇಕು, ಏನನ್ನು ಪಡೆಯಲು ಅರ್ಹನು, ಅಥವಾ ಜವಾಬ್ದಾರಿ ನೆರವೇರದಿದ್ದರೆ ಏನಾಗುತ್ತದೆ ಎಂಬುದರ ಮೇಲೆ ಪರಿಣಾಮ ಬೀರಬಹುದು — ನಿರ್ದಿಷ್ಟ ಪರಿಣಾಮ ಪ್ರಕರಣವನ್ನು ಅವಲಂಬಿಸಿರುತ್ತದೆ.",
        "term_ctx": "ನಿಖರ ಅರ್ಥವು ಅಧಿಕಾರ ಕ್ಷೇತ್ರ ಮತ್ತು ದಾಖಲೆಗಳಲ್ಲಿ ಪದದ ಬಳಕೆಗೆ ಅನುಸಾರ ಬದಲಾಗಬಹುದು.",
        "term_ex": "ಸಂದರ್ಭ ತಿಳಿಯದೆ ಉದಾಹರಣೆಯನ್ನು ವಿಶ್ವಾಸಾರ್ಹವಾಗಿ ನೀಡಲಾಗುವುದಿಲ್ಲ.",
        "term_cav": "ವ್ಯಾಖ್ಯಾನಗಳು ಅಧಿಕಾರ ಕ್ಷೇತ್ರಕ್ಕೆ ತಕ್ಕಂತೆ ಬದಲಾಗುತ್ತವೆ — ಸ್ಥಳೀಯ ವೃತ್ತಿಪರರಿಂದ ಪರಿಶೀಲಿಸಿ.",
        "sim_note": "ಡೆಮೊ ಸರಳೀಕರಣ — ಇನ್‌ಲೈನ್ ವಿವರಣೆಗಳು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿವೆ. ಸಂಪೂರ್ಣ ಸ್ಥಳೀಯ ಸರಳೀಕರಣಕ್ಕಾಗಿ GEMINI_API_KEY ಸೇರಿಸಿ.",
    },
    "ta": {
        "chat_s1": "இதுவரை உள்ள வழக்கு பதிவுகளின்படி, இந்த வழக்கு இன்னும் உருவாக்கப்பட்டு வருகிறது: பதிவான உண்மைகள் குறைவாக உள்ளன, முக்கிய விவரங்கள் இன்னும் உறுதிப்படுத்தப்பட வேண்டும்.",
        "chat_s2": "இதுவரை பதிவு: {docs} ஆவணங்கள், {issues} பிரச்சினைகள், {gaps} திறந்த தகவல் இடைவெளிகள்.",
        "chat_s3": "இந்தக் கேள்வி தொடர்பான ஆவணங்களையும் தேதிகளையும் சேர்த்தால், அதிக நம்பிக்கையுடன் பதிலளிக்க முடியும்.",
        "chat_why": "முழுமையற்ற பதிவுகளின் அடிப்படையிலான பதில்கள் தவறாக வழிநடத்தலாம், எனவே யூகிப்பதற்குப் பதிலாக இடைவெளிகள் சுட்டிக்காட்டப்படுகின்றன.",
        "chat_ev1": "இந்தக் கேள்வி தொடர்பான ஆவணங்களின் நகல்கள்",
        "chat_ev2": "காலவரிசையில் பதிவு செய்யப்பட்ட (அல்லது இல்லாத) தொடர்புடைய தேதிகள்",
        "chat_risk": "அடிப்படை ஆவணங்கள் பரிசீலிக்கப்படும் வரை, முடிவுகள் சரிபார்க்கப்படாத உண்மைகளை அடிப்படையாகக் கொண்டவை.",
        "chat_next": "இந்தக் கேள்வியில் எந்த ஆவணங்கள் அல்லது தேதிகள் சம்பந்தப்பட்டுள்ளன?",
        "chat_step": "தொடர்புடைய ஆவணங்களைப் பதிவேற்றவும் அல்லது இணைக்கவும், பின்னர் இந்தக் கேள்வியை மீண்டும் கேட்கவும்.",
        "chat_f1": "இந்த வழக்கை எளிய மொழியில் சுருக்கவும்",
        "chat_f2": "என்னிடம் இன்னும் என்ன ஆதாரங்கள் இல்லை?",
        "chat_f3": "இப்போது எனது முக்கிய அபாயங்கள் யாவை?",
        "term_def": "'{term}' இன் துல்லியமான வரையறை சூழல் மற்றும் அதிகார வரம்பைப் பொறுத்தது; பொதுவாக இது சட்ட நடவடிக்கைகளிலோ அல்லது ஒப்பந்தங்களிலோ வரும் ஒரு கருத்தாகும்.",
        "term_simple": "அன்றாட மொழியில், '{term}' ஒரு சட்டக் கருத்தைக் குறிக்கிறது, அதன் சரியான பொருள் சூழலைப் பொறுத்தது.",
        "term_tech": "சட்ட ஆவணங்களிலும் வாதங்களிலும், '{term}' அதன் தொழில்நுட்பச் சட்டப் பொருளுடன் பயன்படுத்தப்படுகிறது, இது அதிகார வரம்பு மற்றும் குறிப்பிட்ட விதியைப் பொறுத்து மாறலாம்.",
        "term_why": "இந்தச் சொல் பொதுவாக சட்ட நடவடிக்கைகளிலோ ஒப்பந்தங்களிலோ வருகிறது, ஏனெனில் துல்லியமான பொருள் உரிமைகளையும் கடமைகளையும் பாதிக்கிறது.",
        "term_imp": "இந்தச் சொல் ஒருவர் என்ன செய்ய வேண்டும், எதற்கு உரிமை உள்ளது, அல்லது கடமை நிறைவேறாவிட்டால் என்ன நடக்கும் என்பதைப் பாதிக்கலாம் — குறிப்பிட்ட விளைவு வழக்கைப் பொறுத்தது.",
        "term_ctx": "துல்லியமான பொருள் அதிகார வரம்பு மற்றும் ஆவணங்களில் சொல்லின் பயன்பாட்டைப் பொறுத்து மாறுபடலாம்.",
        "term_ex": "சூழலை அறியாமல் எடுத்துக்காட்டை நம்பகத்தன்மையுடன் வழங்க முடியாது.",
        "term_cav": "வரையறைகள் அதிகார வரம்புக்கு ஏற்ப வேறுபடும் — உள்ளூர் நிபுணரிடம் சரிபார்க்கவும்.",
        "sim_note": "டெமோ எளிமைப்படுத்தல் — உள்ளடக்க விளக்கங்கள் ஆங்கிலத்தில் உள்ளன. முழுமையாக உள்ளூர்மயமாக்கப்பட்ட எளிமைப்படுத்தலுக்கு GEMINI_API_KEY ஐ இணைக்கவும்.",
    },
    "te": {
        "chat_s1": "ఇప్పటి వరకు ఉన్న కేసు రికార్డు ప్రకారం, ఈ కేసు ఇంకా సిద్ధమవుతోంది: నమోదైన వాస్తవాలు పరిమితంగా ఉన్నాయి, ముఖ్య వివరాలు ఇంకా నిర్ధారించాల్సి ఉంది.",
        "chat_s2": "ఇప్పటివరకు నమోదు: {docs} పత్రాలు, {issues} సమస్యలు, {gaps} తెరిచిన సమాచార లోటులు.",
        "chat_s3": "ఈ ప్రశ్నకు సంబంధించిన పత్రాలు, తేదీలు జోడిస్తే మరింత నమ్మకంగా సమాధానం ఇవ్వగలను.",
        "chat_why": "అసంపూర్ణ ఫైళ్ళ ఆధారంగా ఇచ్చే సమాధానాలు తప్పుదారి పట్టించవచ్చు, కాబట్టి ఊహించే బదులు లోటులను గుర్తించడం జరుగుతుంది.",
        "chat_ev1": "ఈ ప్రశ్నకు సంబంధించిన పత్రాల ప్రతులు",
        "chat_ev2": "టైమ్‌లైన్‌లో నమోదైన (లేదా లేని) సంబంధిత తేదీలు",
        "chat_risk": "అంతర్లీన పత్రాలను సమీక్షించే వరకు తీర్మానాలు ధృవీకరించని వాస్తవాలపై ఆధారపడి ఉంటాయి.",
        "chat_next": "ఈ ప్రశ్నలో ఏ పత్రాలు లేదా తేదీలు ఉన్నాయి?",
        "chat_step": "సంబంధిత పత్రాలను అప్‌లోడ్ చేయండి లేదా జోడించండి, తర్వాత ఈ ప్రశ్నను మళ్లీ అడగండి.",
        "chat_f1": "ఈ కేసును సరళమైన భాషలో సంగ్రహించండి",
        "chat_f2": "నా వద్ద ఇంకా ఏ ఆధారాలు లేవు?",
        "chat_f3": "ఇప్పుడు నా ప్రధాన ప్రమాదాలు ఏమిటి?",
        "term_def": "'{term}' యొక్క ఖచ్చితమైన నిర్వచనం సందర్భం మరియు అధికార పరిధిపై ఆధారపడి ఉంటుంది; సాధారణంగా ఇది చట్టపరమైన వ్యవహారాలలో లేదా ఒప్పందాలలో వచ్చే భావనను సూచిస్తుంది.",
        "term_simple": "రోజువారీ భాషలో, '{term}' ఒక చట్టపరమైన భావనను సూచిస్తుంది, దాని ఖచ్చితమైన అర్థం సందర్భంపై ఆధారపడి ఉంటుంది.",
        "term_tech": "చట్టపరమైన పత్రాలలో మరియు వాదనలలో, '{term}' దాని సాంకేతిక చట్టపరమైన అర్థంతో వాడబడుతుంది, ఇది అధికార పరిధి మరియు నిర్దిష్ట నిబంధనను బట్టి మారవచ్చు.",
        "term_why": "ఈ పదం సాధారణంగా చట్టపరమైన వ్యవహారాలలో లేదా ఒప్పందాలలో వస్తుంది, ఎందుకంటే ఖచ్చితమైన అర్థం హక్కులు మరియు బాధ్యతలను ప్రభావితం చేస్తుంది.",
        "term_imp": "ఈ పదం వ్యక్తి ఏమి చేయాలి, దేనికి అర్హుడు, లేదా బాధ్యత నెరవేరకపోతే ఏమి జరుగుతుంది అనే దానిపై ప్రభావం చూపవచ్చు — నిర్దిష్ట ప్రభావం కేసుపై ఆధారపడి ఉంటుంది.",
        "term_ctx": "ఖచ్చితమైన అర్థం అధికార పరిధిని, పత్రాలలో పదం వాడకాన్ని బట్టి మారవచ్చు.",
        "term_ex": "సందర్భం తెలియకుండా ఉదాహరణను విశ్వసనీయంగా ఇవ్వలేము.",
        "term_cav": "నిర్వచనాలు అధికార పరిధిని బట్టి మారుతాయి — స్థానిక నిపుణుడితో ధృవీకరించండి.",
        "sim_note": "డెమో సరళీకరణ — ఇన్‌లైన్ వివరణలు ఇంగ్లీషులో ఉన్నాయి. పూర్తిగా స్థానికీకరించిన సరళీకరణ కోసం GEMINI_API_KEY ను కనెక్ట్ చేయండి.",
    },
    "ml": {
        "chat_s1": "ഇതുവരെയുള്ള കേസ് രേഖകൾ പ്രകാരം, ഈ കേസ് ഇനിയും ഒരുങ്ങിക്കൊണ്ടിരിക്കുകയാണ്: രേഖപ്പെടുത്തിയ വസ്തുതകൾ പരിമിതമാണ്, പ്രധാന വിവരങ്ങൾ ഇനിയും സ്ഥിരീകരിക്കേണ്ടതുണ്ട്.",
        "chat_s2": "ഇതുവരെ രേഖപ്പെടുത്തിയത്: {docs} രേഖകൾ, {issues} പ്രശ്നങ്ങൾ, {gaps} തുറന്ന വിവര വിടവുകൾ.",
        "chat_s3": "ഈ ചോദ്യവുമായി ബന്ധപ്പെട്ട രേഖകളും തീയതികളും ചേർത്താൽ കൂടുതൽ ആത്മവിശ്വാസത്തോടെ ഉത്തരം നൽകാനാകും.",
        "chat_why": "അപൂർണ്ണമായ രേഖകളെ അടിസ്ഥാനമാക്കിയുള്ള ഉത്തരങ്ങൾ തെറ്റിദ്ധരിപ്പിക്കാം, അതിനാൽ ഊഹിക്കുന്നതിനു പകരം വിടവുകൾ അടയാളപ്പെടുത്തുന്നു.",
        "chat_ev1": "ഈ ചോദ്യവുമായി ബന്ധപ്പെട്ട രേഖകളുടെ പകർപ്പുകൾ",
        "chat_ev2": "ടൈംലൈനിൽ രേഖപ്പെടുത്തിയ (അല്ലെങ്കിൽ ഇല്ലാത്ത) ബന്ധപ്പെട്ട തീയതികൾ",
        "chat_risk": "അടിസ്ഥാന രേഖകൾ പരിശോധിക്കുന്നതുവരെ നിഗമനങ്ങൾ സ്ഥിരീകരിക്കാത്ത വസ്തുതകളെ ആശ്രയിച്ചിരിക്കും.",
        "chat_next": "ഈ ചോദ്യത്തിൽ ഏത് രേഖകളോ തീയതികളോ ഉൾപ്പെട്ടിരിക്കുന്നു?",
        "chat_step": "ബന്ധപ്പെട്ട രേഖകൾ അപ്‌ലോഡ് ചെയ്യുക അല്ലെങ്കിൽ ഘടിപ്പിക്കുക, തുടർന്ന് ഈ ചോദ്യം വീണ്ടും ചോദിക്കുക.",
        "chat_f1": "ഈ കേസ് ലളിതമായ ഭാഷയിൽ സംഗ്രഹിക്കുക",
        "chat_f2": "എന്റെ കയ്യിൽ ഇനിയും ഏത് തെളിവുകൾ ഇല്ല?",
        "chat_f3": "ഇപ്പോൾ എന്റെ പ്രധാന അപകടസാധ്യതകൾ എന്തൊക്കെയാണ്?",
        "term_def": "'{term}' എന്നതിന്റെ കൃത്യമായ നിർവ്വചനം സന്ദർഭത്തെയും അധികാരപരിധിയെയും ആശ്രയിച്ചിരിക്കുന്നു; പൊതുവേ ഇത് നിയമ നടപടികളിലോ കരാറുകളിലോ വരുന്ന ഒരു ആശയത്തെ സൂചിപ്പിക്കുന്നു.",
        "term_simple": "ദൈനംദിന ഭാഷയിൽ, '{term}' ഒരു നിയമ ആശയത്തെ സൂചിപ്പിക്കുന്നു, അതിന്റെ കൃത്യമായ അർത്ഥം സന്ദർഭത്തെ ആശ്രയിച്ചിരിക്കുന്നു.",
        "term_tech": "നിയമ രേഖകളിലും വാദങ്ങളിലും, '{term}' അതിന്റെ സാങ്കേതിക നിയമ അർത്ഥത്തോടെയാണ് ഉപയോഗിക്കുന്നത്, അത് അധികാരപരിധിക്കും പ്രത്യേക വ്യവസ്ഥയ്ക്കും അനുസരിച്ച് വ്യത്യാസപ്പെടാം.",
        "term_why": "ഈ പദം സാധാരണയായി നിയമ നടപടികളിലോ കരാറുകളിലോ വരുന്നു, കാരണം കൃത്യമായ അർത്ഥം അവകാശങ്ങളെയും ബാധ്യതകളെയും ബാധിക്കുന്നു.",
        "term_imp": "ഈ പദം ഒരാൾ എന്തു ചെയ്യണം, എന്തിന് അർഹനാണ്, അല്ലെങ്കിൽ ബാധ്യത നിറവേറ്റിയില്ലെങ്കിൽ എന്തു സംഭവിക്കും എന്നതിനെ ബാധിച്ചേക്കാം — പ്രത്യേക ഫലം കേസിനെ ആശ്രയിച്ചിരിക്കുന്നു.",
        "term_ctx": "കൃത്യമായ അർത്ഥം അധികാരപരിധിക്കനുസരിച്ചും രേഖകളിൽ പദത്തിന്റെ ഉപയോഗത്തിനനുസരിച്ചും വ്യത്യാസപ്പെടാം.",
        "term_ex": "സന്ദർഭം അറിയാതെ ഉദാഹരണം വിശ്വസനീയമായി നൽകാനാവില്ല.",
        "term_cav": "നിർവ്വചനങ്ങൾ അധികാരപരിധിക്കനുസരിച്ച് വ്യത്യാസപ്പെടുന്നു — പ്രാദേശിക വിദഗ്ദ്ധനുമായി സ്ഥിരീകരിക്കുക.",
        "sim_note": "ഡെമോ ലളിതവൽക്കരണം — ഇൻ‌ലൈൻ വിശദീകരണങ്ങൾ ഇംഗ്ലീഷിലാണ്. പൂർണ്ണമായി പ്രാദേശികവൽക്കരിച്ച ലളിതവൽക്കരണത്തിന് GEMINI_API_KEY കണക്റ്റ് ചെയ്യുക.",
    },
    "mr": {
        "chat_s1": "आतापर्यंतच्या केस रेकॉर्डनुसार, हे प्रकरण अजून तयार होत आहे: नोंदवलेली तथ्ये मर्यादित आहेत आणि महत्त्वाचे तपशील अजून पुष्टी करणे बाकी आहे.",
        "chat_s2": "आतापर्यंत नोंद: {docs} दस्तऐवज, {issues} मुद्दे, {gaps} उघडे माहिती-अंतर.",
        "chat_s3": "या प्रश्नाशी संबंधित दस्तऐवज आणि तारखा जोडल्यास मी अधिक खात्रीने उत्तर देऊ शकेन.",
        "chat_why": "अपूर्ण फाईलींवर आधारित उत्तरांची दिशाभूल होऊ शकते, म्हणून अंदाज लावण्याऐवजी कमतरता दाखवल्या जातात.",
        "chat_ev1": "या प्रश्नाशी संबंधित दस्तऐवजांच्या प्रती",
        "chat_ev2": "टाइमलाइनमध्ये नोंदवलेल्या (किंवा नसलेल्या) संबंधित तारखा",
        "chat_risk": "मूळ दस्तऐवजांची तपासणी होईपर्यंत निष्कर्ष असत्यापित तथ्यांवर अवलंबून असतात.",
        "chat_next": "या प्रश्नात कोणते दस्तऐवज किंवा तारखा सामील आहेत?",
        "chat_step": "संबंधित दस्तऐवज अपलोड करा किंवा जोडा, नंतर हा प्रश्न पुन्हा विचारा.",
        "chat_f1": "या प्रकरणाचा सोप्या भाषेत सारांश करा",
        "chat_f2": "माझ्याकडे अजून कोणते पुरावे नाहीत?",
        "chat_f3": "आता माझे मुख्य धोके कोणते आहेत?",
        "term_def": "'{term}' ची अचूक व्याख्या संदर्भ आणि अधिकारक्षेत्रावर अवलंबून असते; साधारणपणे ती कायदेशीर कारवाईत किंवा करारांमध्ये येणारी संकल्पना आहे.",
        "term_simple": "दैनंदिन भाषेत, '{term}' ही एक कायदेशीर संकल्पना आहे जिचा अचूक अर्थ संदर्भावर अवलंबून असतो.",
        "term_tech": "कायदेशीर दस्तऐवज आणि युक्तिवादांमध्ये, '{term}' हा त्याच्या तांत्रिक कायदेशीर अर्थासह वापरला जातो, जो अधिकारक्षेत्र आणि विशिष्ट कलमानुसार बदलू शकतो.",
        "term_why": "हा शब्द सामान्यतः कायदेशीर कारवाईत किंवा करारांमध्ये येतो, कारण अचूक अर्थ हक्कांवर आणि जबाबदाऱ्यांवर परिणाम करतो.",
        "term_imp": "हा शब्द परिणाम करू शकतो की व्यक्तीने काय करावे, तो कशाचा हक्कदार आहे, किंवा जबाबदारी पूर्ण न झाल्यास काय होईल — विशिष्ट परिणाम प्रकरणावर अवलंबून असतो.",
        "term_ctx": "अचूक अर्थ अधिकारक्षेत्र आणि दस्तऐवजांमधील शब्दाच्या वापरानुसार बदलू शकतो.",
        "term_ex": "संदर्भ माहीत नसल्यास उदाहरण विश्वासार्हपणे देता येत नाही.",
        "term_cav": "व्याख्या अधिकारक्षेत्रानुसार बदलतात — स्थानिक व्यावसायिकांकडून पडताळून घ्या.",
        "sim_note": "डेमो सरलीकरण — इनलाइन स्पष्टीकरणे इंग्रजीत आहेत. पूर्णपणे स्थानिकीकृत सरलीकरणासाठी GEMINI_API_KEY जोडा.",
    },
    "bn": {
        "chat_s1": "এখন পর্যন্ত মামলার রেকর্ড অনুযায়ী, এই মামলাটি এখনও তৈরি হচ্ছে: লিপিবদ্ধ তথ্য সীমিত এবং গুরুত্বপূর্ণ বিবরণ এখনও নিশ্চিত করা বাকি।",
        "chat_s2": "এখন পর্যন্ত নথিভুক্ত: {docs} নথি, {issues} সমস্যা, {gaps} খোলা তথ্য-ফাঁক।",
        "chat_s3": "এই প্রশ্নের সাথে যুক্ত নথি ও তারিখ যোগ করলে আমি আরও আত্মবিশ্বাসের সাথে উত্তর দিতে পারব।",
        "chat_why": "অসম্পূর্ণ ফাইলের ভিত্তিতে দেওয়া উত্তর বিভ্রান্তিকর হতে পারে, তাই অনুমান করার পরিবর্তে ফাঁকগুলো চিহ্নিত করা হয়।",
        "chat_ev1": "এই প্রশ্নের সাথে সম্পর্কিত নথিগুলির কপি",
        "chat_ev2": "টাইমলাইনে রেকর্ড করা (বা অনুপস্থিত) প্রাসঙ্গিক তারিখগুলি",
        "chat_risk": "অন্তর্নিহিত নথিগুলি পর্যালোচনা না করা পর্যন্ত সিদ্ধান্তগুলি যাচাই না করা তথ্যের উপর নির্ভর করে।",
        "chat_next": "এই প্রশ্নে কোন নথি বা তারিখ জড়িত?",
        "chat_step": "প্রাসঙ্গিক নথিগুলি আপলোড করুন বা সংযুক্ত করুন, তারপর এই প্রশ্নটি আবার জিজ্ঞাসা করুন।",
        "chat_f1": "এই মামলাটি সহজ ভাষায় সংক্ষিপ্ত করুন",
        "chat_f2": "আমার কাছে এখনও কী কী প্রমাণ নেই?",
        "chat_f3": "এখন আমার প্রধান ঝুঁকিগুলি কী কী?",
        "term_def": "'{term}' এর সঠিক সংজ্ঞা প্রেক্ষাপট ও এখতিয়ারের উপর নির্ভর করে; সাধারণভাবে এটি আইনি কার্যক্রম বা চুক্তিতে আসা একটি ধারণাকে বোঝায়।",
        "term_simple": "সাধারণ ভাষায়, '{term}' একটি আইনি ধারণাকে বোঝায় যার সঠিক অর্থ প্রেক্ষাপটের উপর নির্ভর করে।",
        "term_tech": "আইনি নথি ও যুক্তিতে, '{term}' তার কারিগরি আইনি অর্থসহ ব্যবহৃত হয়, যা এখতিয়ার এবং নির্দিষ্ট ধারা অনুযায়ী ভিন্ন হতে পারে।",
        "term_why": "এই শব্দটি সাধারণত আইনি কার্যক্রম বা চুক্তিতে দেখা যায়, কারণ সঠিক অর্থ অধিকার ও দায়িত্বকে প্রভাবিত করে।",
        "term_imp": "শব্দটি প্রভাবিত করতে পারে একজন ব্যক্তিকে কী করতে হবে, কী পাওয়ার অধিকার আছে, বা বাধ্যবাধকতা পূরণ না হলে কী হবে — নির্দিষ্ট প্রভাব মামলার উপর নির্ভর করে।",
        "term_ctx": "সঠিক অর্থ এখতিয়ার এবং নথিতে শব্দটির ব্যবহার অনুযায়ী ভিন্ন হতে পারে।",
        "term_ex": "প্রসঙ্গ না জেনে নির্ভরযোগ্যভাবে উদাহরণ দেওয়া যায় না।",
        "term_cav": "সংজ্ঞা এখতিয়ারভেদে ভিন্ন হয় — স্থানীয় পেশাদারের সাথে যাচাই করুন।",
        "sim_note": "ডেমো সরলীকরণ — ইনলাইন ব্যাখ্যাগুলি ইংরেজিতে। সম্পূর্ণ স্থানীয়কৃত সরলীকরণের জন্য GEMINI_API_KEY সংযুক্ত করুন।",
    },
}


def _l10n(language: str) -> dict:
    """Translation table for demo-mode canned strings; en is the identity fallback."""
    return L10N.get((language or "en").lower()[:2], {})


def _lstr(language: str, key: str, **kwargs) -> str:
    t = _l10n(language)
    if key not in t:
        return kwargs.get("fallback", "")
    return t[key].format(**kwargs)


# --------------------------------------------------------------------------
# 7. CaseGuide assistant (case-contextual chat)
# --------------------------------------------------------------------------

def answer_case_question(case: dict, history: list, user_message: str,
                         language: str = "en") -> dict:
    """Centralized CaseGuide responder.

    Answers one question strictly inside the given case. The response is a
    structured payload (answer / why it matters / evidence needed / potential
    risk / next question / recommended next step) with provenance labels, the
    sources the model drew from, and follow-up suggestions.
    """
    context = _case_context(case)
    facts = _facts_context(case)
    extra = _rich_context(case)
    transcript = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history[-10:])
    prompt = f"""{context}

Facts and potential issues in the case:
{facts}

{extra}

Conversation so far (same case):
{transcript}

User's question: {user_message}

Answer the question about THIS case only, using the case information above and "
"general legal knowledge. Respond in language code '{language}'. Structure the "
"response as JSON with exactly this schema:
{{
  "answer": "direct, plain-language answer, under 250 words, using inline markers like [USER FACT], [DOCUMENT FACT], [AI INTERPRETATION], [INFORMATION MISSING], [REQUIRES VERIFICATION] where relevant",
  "why_this_matters": "1-2 sentences on why this matters for the case",
  "evidence_needed": ["evidence or documents that would strengthen this answer"],
  "potential_risk": "one sentence naming the main risk or caveat, or empty string",
  "next_question": "one question you would ask next to go deeper, or empty string",
  "recommended_next_step": "one practical, concrete next step the user could take",
  "follow_up_suggestions": ["2-3 short suggested follow-ups the user may want to ask"],
  "sources": [{{"type": "document|timeline|issue|risk|evidence|case", "label": "name of the item used, exactly as listed above"}}],
  "labels": ["USER FACT|DOCUMENT FACT|AI INTERPRETATION|INFORMATION MISSING|REQUIRES VERIFICATION"]
}}
Ground every claim in the case material. NEVER invent laws, citations, statutes, or "
"document contents. State uncertainty explicitly. Never guarantee outcomes. If the "
"case material is thin, say so and ask what is missing."""

    docs = case.get("documents") or []
    issues = case.get("issues") or []
    gaps = case.get("gaps") or []
    en = {
        "s1": "Based on the case file so far [USER FACT], this case is still being assembled: the recorded facts are limited [AI INTERPRETATION] and key details remain to be confirmed [REQUIRES VERIFICATION].",
        "s2": f"Recorded so far: {len(docs)} document(s), {len(issues)} issue(s), {len(gaps)} open information gap(s) [INFORMATION MISSING].",
        "s3": "Adding the documents and dates behind this question would let me answer with more confidence.",
        "why": "Answers built on incomplete files can mislead, so gaps are flagged instead of guessed.",
        "ev1": "Copies of the documents that bear on this question",
        "ev2": "The relevant dates already recorded (or missing) in the timeline",
        "risk": "Conclusions rest on unverified facts until the underlying documents are reviewed.",
        "next": "Which documents or dates are involved in this question?",
        "step": "Upload or connect the relevant documents, then re-ask this question.",
        "f1": "Summarize this case in plain language",
        "f2": "What evidence am I still missing?",
        "f3": "What are my main risks right now?",
    }
    t = _l10n(language)
    s1 = t.get("chat_s1", en["s1"])
    s2 = t.get("chat_s2", en["s2"]).format(docs=len(docs), issues=len(issues), gaps=len(gaps))
    s3 = t.get("chat_s3", en["s3"])
    demo = _stamp({
        "answer": f"{s1} {s2} {s3}",
        "why_this_matters": t.get("chat_why", en["why"]),
        "evidence_needed": [
            t.get("chat_ev1", en["ev1"]),
            t.get("chat_ev2", en["ev2"]),
        ],
        "potential_risk": t.get("chat_risk", en["risk"]),
        "next_question": t.get("chat_next", en["next"]),
        "recommended_next_step": t.get("chat_step", en["step"]),
        "follow_up_suggestions": [
            t.get("chat_f1", en["f1"]),
            t.get("chat_f2", en["f2"]),
            t.get("chat_f3", en["f3"]),
        ],
        "sources": _sources_from_context(case),
        "labels": ["USER FACT", "AI INTERPRETATION", "INFORMATION MISSING", "REQUIRES VERIFICATION"],
        "note": _demo_note("CaseGuide reply"),
    }, "demo")
    return _complete(prompt, demo)


def assistant_chat(case: dict, history: list, user_message: str, language: str = "en") -> dict:
    """Backward-compatible wrapper over the CaseGuide responder."""
    result = answer_case_question(case, history, user_message, language)
    result["reply"] = result.get("answer") or result.get("reply") or ""
    result["follow_up_questions"] = result.get("follow_up_suggestions") or []
    return result


def summarize_case(case: dict) -> dict:
    """Centralized case summarizer (same structured overview used by Overview)."""
    return analyze_case_overview(case)


# --------------------------------------------------------------------------
# 7b. Timeline extraction (Phase 6)
# --------------------------------------------------------------------------

def extract_timeline_events(case: dict) -> dict:
    """Surface dated events from the case description, document analyses and
    recorded material. Returns CANDIDATES — nothing is stored until the user
    explicitly confirms each one. Never silently assumes a date."""
    prompt = f"""{_case_context(case)}

{_facts_context(case)}

{_rich_context(case)}

Extract dated events that belong on this case's timeline as JSON:
{{
  "events": [
    {{
      "date": "YYYY-MM-DD — ONLY when the date is actually stated in the material above",
      "title": "short event title",
      "description": "what happened, in the source's own terms",
      "event_type": "incident|communication|document|deadline|payment|legal_action|other",
      "importance": "high|medium|low",
      "date_status": "extracted|potential",
      "reason": "for potential: why the date is uncertain or conflicts across sources"
    }}
  ],
  "missing_dates": [
    {{"about": "what event or fact has no date", "context": "what is said about it"}}
  ],
  "conflicts": [
    {{"about": "what event", "between": ["source A dating", "source B dating"]}}
  ],
  "note": "brief note on what was considered"
}}
Rules: date_status='extracted' only when the date is stated explicitly in a "
"source; 'potential' when you inferred, approximated, or sources conflict. NEVER "
"invent a date — when no date is stated, put the event in missing_dates instead "
"of events. Skip events already recorded on the timeline above. Skip events that "
"have no date at all."""
    events, seen = [], set()
    for d in (case.get("documents") or []):
        for kd in (d.get("key_dates") or [])[:8]:
            day = kd.get("date")
            if not day:
                continue
            title = (kd.get("description") or "").strip()[:255]
            if not title:
                continue
            dedupe_key = (day, title.lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            events.append({
                "date": day[:10],
                "title": title,
                "description": f"Date recorded in the analysis of {d.get('filename', 'a document')}.",
                "event_type": "deadline" if kd.get("kind") == "deadline" else "document",
                "importance": "high" if kd.get("kind") == "deadline" else "medium",
                "date_status": "extracted",
                "reason": "",
            })
    demo = _stamp({
        "events": events,
        "missing_dates": [],
        "conflicts": [],
        "note": _demo_note("timeline extraction") + (
            " Extracted candidates come only from dates explicitly recorded in "
            "analyzed documents."
        ),
    }, "demo")
    return _complete(prompt, demo)


# --------------------------------------------------------------------------
# 8. Legal term explainer / multilingual
# --------------------------------------------------------------------------

def explain_term(term: str, language: str = "en", jurisdiction: str = "",
                  mode: str = "beginner") -> dict:
    """Legal term explainer (Phase 12).

    Returns the full Phase-12 structure — simple meaning, technical meaning, why
    the term appears, example, potential implications, related clauses — in
    Beginner or Technical mode, always in the requested language. The old keys
    (definition/context) are kept as aliases for backward compatibility.
    """
    mode = (mode or "beginner").lower()
    if mode not in ("beginner", "technical"):
        mode = "beginner"
    mode_desc = {
        "beginner": "Beginner mode: everyday language, no jargon, short sentences.",
        "technical": "Technical mode: precise legal phrasing, more formal, still without inventing statutes.",
    }[mode]
    prompt = f"""Explain the legal term "{term}" for a non-lawyer. Jurisdiction context: {jurisdiction or 'not specified'}.

{mode_desc}

Return JSON exactly:
{{
  "term": "{term}",
  "simple_meaning": "plain everyday meaning, 1-3 sentences",
  "technical_meaning": "how it is used in legal documents and arguments, 1-3 sentences",
  "why_it_appears": "why this term typically appears in cases or agreements like this one",
  "example": "a short illustrative example",
  "potential_implications": "what the term can mean for a person's rights, duties, or risks",
  "related_clauses": ["clause types or related concepts"],
  "related_terms": ["..."],
  "caveat": "jurisdiction/verification caveat"
}}
Answer in language code '{language}'. Never invent specific statutes or citations. Do not "
"make unsupported legal claims."""
    t = _l10n(language)
    demo = _stamp({
        "term": term,
        "mode": "demo",
        "simple_meaning": t.get("term_simple", f"In everyday language, '{term}' refers to a legal concept whose exact sense depends on the context.").format(term=term),
        "technical_meaning": t.get("term_tech", f"In legal documents and arguments, '{term}' is used with its technical legal meaning, which can vary by jurisdiction and by the specific clause.").format(term=term),
        "why_it_appears": t.get("term_why", "This term commonly appears in legal proceedings or agreements because precise meaning affects rights and obligations."),
        "example": t.get("term_ex", "An example cannot be given reliably without knowing the context."),
        "potential_implications": t.get("term_imp", "The term can affect what a person must do, what they are entitled to, or what happens if an obligation is not met — the specific effect depends on the case."),
        "related_clauses": [],
        "related_terms": [],
        # Backward-compatible aliases
        "definition": t.get("term_simple", f"'{term}' is a legal term; a precise definition depends on context and jurisdiction.").format(term=term),
        "context": t.get("term_ctx", "The exact meaning may differ by jurisdiction and by how the term is used in the documents."),
        "caveat": t.get("term_cav", "Definitions vary by jurisdiction — verify with a local professional."),
    }, "demo")
    return _complete(prompt, demo, temperature=0.2)


def explain_simply(case: dict, text: str, language: str = "en") -> dict:
    """Explain Simply (Phase 12): rewrite complex legal text in plain, everyday
    language while preserving the legal meaning exactly."""
    prompt = f"""Rewrite the following legal text in plain, everyday language. Preserve the "
"legal meaning exactly: do not add or remove obligations, rights, conditions, or "
"consequences. Do not invent legal claims. Keep the same structure where possible.

Legal text:\n{text[:8000]}

Return JSON exactly:
{{
  "original": "the input text unchanged",
  "simplified": "the plain-language version, in language code '{language}'",
  "what_was_simplified": ["each jargon term or phrase that was reworded, and its plain meaning"],
  "meaning_preserved": true,
  "note": "one sentence confirming the legal meaning was preserved and nothing was added or removed"
}}"""
    replaced = []
    simplified = text
    # Longest-match-first single pass: avoids double-glossing sub-terms such as
    # "breach" inside "material breach".
    ordered = sorted(SIMPLE_GLOSSARY, key=lambda t: len(t[0]), reverse=True)
    pattern = re.compile(
        r"\b(?:" + r"|".join(re.escape(t) for t, _ in ordered) + r")\b",
        re.IGNORECASE,
    )
    gloss_by = {t.lower(): g for t, g in ordered}

    def _gloss(match):
        return f"{match.group(0)} ({gloss_by[match.group(0).lower()]})"

    new_text = pattern.sub(_gloss, simplified)
    seen, tally = [], {}
    for m in pattern.finditer(text):
        key = m.group(0).lower()
        tally[key] = tally.get(key, 0) + 1
        if key not in [s.lower() for s in seen]:
            seen.append(m.group(0))
    replaced = [{"term": t, "meaning": gloss_by[t.lower()], "count": tally[t.lower()]}
                for t in seen]
    simplified = new_text
    t = _l10n(language)
    demo = _stamp({
        "original": text[:8000],
        "simplified": simplified[:8000] if replaced else text[:8000],
        "what_was_simplified": replaced if replaced else [
            {"term": "(none detected)", "meaning": "No common jargon terms were detected in this text."}
        ],
        "meaning_preserved": True,
        "note": _demo_note("Explain Simply") + " " + (t.get("sim_note", "") or ""),
    }, "demo")
    return _complete(prompt, demo, temperature=0.2)


SIMPLE_GLOSSARY = [
    ("force majeure", "unforeseeable events outside anyone's control that excuse a promise"),
    ("void ab initio", "invalid from the start"),
    ("null and void", "having no legal force"),
    ("indemnify", "compensate for loss or damage"),
    ("indemnification", "compensation for loss or damage"),
    ("consideration", "something of value exchanged for a promise"),
    ("material breach", "a serious breaking of the agreement"),
    ("liquidated damages", "a pre-agreed fixed amount of compensation"),
    ("limitation period", "the time limit for starting legal action"),
    ("joint and several liability", "each party can be held responsible for the whole amount"),
    ("severability", "if one part is invalid, the rest still stands"),
    ("mitigation", "taking reasonable steps to reduce loss"),
    ("termination", "ending the agreement"),
    ("warranty", "a promise about the condition or quality of something"),
    ("liability", "legal responsibility"),
    ("damages", "money paid as compensation"),
    ("breach", "failure to keep a promise or obligation"),
    ("waiver", "giving up a right"),
    ("covenant", "a formal promise in an agreement"),
    ("jurisdiction", "the authority of a court, or the region covered by a law"),
]


# --------------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------------

def image_payload(b64_bytes: str, mime_type: str) -> dict:
    return {"b64": b64_bytes, "mime_type": mime_type}


def b64encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


# --------------------------------------------------------------------------
# Case context assembly (distinguishes fact sources for the AI)
# --------------------------------------------------------------------------

def build_case_context(case: Case) -> dict:
    """Assemble a context dict for AI prompts, labeling facts by source:
    user-provided vs extracted from documents vs timeline/evidence."""
    facts = []
    if case.description.strip():
        facts.append({"text": case.description.strip(), "source": "user"})
    doc_details = []
    for doc in case.documents.all():
        analysis = {}
        if doc.analysis_json:
            try:
                analysis = json.loads(doc.analysis_json)
            except (ValueError, TypeError):
                analysis = {}
        for fact in (analysis.get("key_facts") or [])[:6]:
            facts.append({"text": f"[{doc.filename}] {fact.get('text', '')}", "source": "document"})
        key_dates = [
            {"date": d.get("date"), "description": d.get("description", ""), "kind": "date"}
            for d in (analysis.get("dates_found") or [])
            if d.get("date")
        ]
        key_dates += [
            {"date": d.get("date"), "description": d.get("title") or d.get("description") or "deadline", "kind": "deadline"}
            for d in (analysis.get("deadlines") or [])
            if d.get("date")
        ]
        doc_details.append({
            "filename": doc.filename,
            "analysis_status": doc.analysis_status,
            "key_dates": key_dates[:10],
            "summary": (analysis.get("summary") or "")[:400],
        })
    for ev in case.evidence.all():
        facts.append({"text": f"Evidence: {ev.title}. {ev.description}", "source": "user"})
    for evt in case.timeline.all():
        facts.append({"text": f"On {evt.date}: {evt.title}. {evt.description}", "source": "user"})
    prep = NegotiationPrep.query.filter_by(case_id=case.id).first()

    return {
        "title": case.title,
        "description": case.description or "",
        "case_type": case.case_type or "",
        "jurisdiction": case.jurisdiction or "",
        "parties": case.parties or "",
        "stage": case.stage or "",
        "facts": facts[:20],
        "issues": [{"title": i.title, "confidence": i.confidence, "status": i.status}
                    for i in case.issues.all()[:12]],
        "documents": doc_details,
        "timeline": [{"date": t.date.isoformat() if t.date else "", "title": t.title,
                       "event_type": t.event_type or "other",
                       "importance": t.importance or "medium",
                       "date_status": t.date_status or "user_confirmed"}
                      for t in case.timeline.order_by(TimelineEvent.date.desc()).all()[:25]],
        "risks": [{"title": r.title, "overall_risk": r.overall_risk}
                   for r in case.risks.all()[:10]],
        "gaps": [{"question": g.question, "priority": g.priority or "medium",
                    "status": g.status or "open"} for g in case.gaps.all()[:12]],
        "evidence": [{"title": e.title, "item_type": e.item_type or "document",
                       "importance": e.importance or "medium",
                       "verification": e.verification or "unverified"}
                      for e in case.evidence.all()[:12]],
        "deadlines": [{"title": d.title, "due_date": d.due_date.isoformat(),
                        "status": d.status or "pending",
                        "days_left": (d.due_date - date.today()).days}
                       for d in case.deadlines.all()[:12]],
        "scenarios": [{"name": s.name, "risk_level": s.risk_level or "medium",
                        "analyzed": bool(s.analysis_json)} for s in case.scenarios.all()[:6]],
        "status": case.status or "draft",
        "prep": prep.to_dict() if prep else {},
    }