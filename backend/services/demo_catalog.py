"""Phase 13 — Fictional demo case catalog.

Five fully-populated, entirely FICTIONAL cases so reviewers can explore every
module (documents, timeline, issues, evidence, risks, scenarios, negotiation,
action plan) without entering real data. Names, companies, addresses, amounts
and events are invented. Each definition is rendered by ``create_demo_case``.

Dates may be given as an ISO string (absolute) or an integer (offset in days
from *today* at creation time, so demo deadlines always look fresh).
"""
import json
import uuid

from app.extensions import db
from models import (ActionItem, Case, CaseDocument, Deadline, EvidenceItem,
                    InfoGap, LegalIssue, NegotiationPrep, RiskAssessment,
                    RiskFactor, Scenario, TimelineEvent)

# Well-known demo account used by the one-click "Explore Demo Case" flow.
DEMO_ACCOUNT_EMAIL = "demo.explorer@legalcase.local"
DEMO_ACCOUNT_NAME = "Demo Explorer"

# Ordered, deterministic kinds shown in the picker.
DEMO_ORDER = ["rental", "employment", "consumer", "contract", "property"]

DEMO_CATALOG = [
    # ------------------------------------------------------------------ 1
    {
        "kind": "rental",
        "icon": "bi-house-door",
        "title": "Rental Deposit Dispute",
        "case_type": "Tenant/Landlord",
        "country": "India",
        "state": "Delhi",
        "jurisdiction": "India, Delhi",
        "status": "analysis_in_progress",
        "stage": "Information gathering",
        "parties": "You (tenant) — vs — Maple Crest Properties Ltd. (landlord)",
        "tagline": "Landlord withheld the full security deposit; the itemized statement may never have arrived in time.",
        "description": (
            "I rented an apartment at 14 Maple Street for 24 months under a written lease. "
            "When I moved out I gave 30 days' notice as required. The landlord kept my full "
            "deposit of $2,800, claiming damage to the parquet floor in the living room and "
            "unpaid utilities. The floor had minor wear that was already present when I moved "
            "in (noted on the move-in inspection report), and I have receipts showing all "
            "utilities were paid. The landlord did not provide an itemized statement of "
            "deductions within the timeframe required by local law."
        ),
        "documents": [
            {
                "filename": "rental-lease.txt",
                "content": (
                    "RESIDENTIAL TENANCY AGREEMENT between Maple Crest Properties Ltd. and "
                    "the Tenant for the premises at 14 Maple Street, Toronto, Ontario.\n\n"
                    "1. TERM: 24 months beginning 2024-03-01. Monthly rent $1,400 payable on "
                    "the first of each month.\n"
                    "2. SECURITY DEPOSIT: A deposit of $2,800 (two months' rent) is held for "
                    "the term. The deposit must be returned within the timeframe required by "
                    "law, together with an itemized statement of any lawful deductions.\n"
                    "3. CONDITION: The premises are rented in their condition at move-in, "
                    "recorded in the move-in inspection report. Ordinary wear and tear is the "
                    "landlord's responsibility.\n"
                    "4. UTILITIES: The Tenant pays all utilities billed to the premises "
                    "during the tenancy.\n"
                    "5. NOTICE: Either party may end the tenancy with 30 days' written notice."
                ),
                "analysis": {
                    "summary": "A 24-month residential lease for 14 Maple Street at $1,400 "
                               "monthly. It requires a $2,800 security deposit returned with "
                               "an itemized statement within the legally required timeframe, "
                               "assigns ordinary wear and tear to the landlord, and requires "
                               "30 days' written notice to end the tenancy.",
                    "document_type": "lease agreement",
                    "parties": [
                        {"name": "Maple Crest Properties Ltd.", "role": "landlord"},
                        {"name": "the Tenant", "role": "tenant"},
                    ],
                    "key_facts": [
                        {"text": "The lease term began 2024-03-01 and ran 24 months at $1,400/month.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "A $2,800 security deposit is held and must be returned with an itemized statement of lawful deductions.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "Ordinary wear and tear is the landlord's responsibility.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "Either party may end the tenancy with 30 days' written notice.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                    ],
                    "important_clauses": [
                        {"quote": "The deposit must be returned within the timeframe required by law, together with an itemized statement of any lawful deductions.", "meaning": "Returning the deposit late, or without an itemized statement, may make the deductions unlawful.", "section": "2"},
                        {"quote": "Ordinary wear and tear is the landlord's responsibility.", "meaning": "Routine wear cannot be deducted from the deposit; the landlord must prove damage beyond wear.", "section": "3"},
                    ],
                    "concerning_clauses": [
                        {"quote": "The deposit must be returned within the timeframe required by law", "reason": "Whether the landlord ever sent an itemized statement within the window is the central question of the case.", "severity": "high"},
                    ],
                    "obligations": [
                        {"party": "Landlord", "obligation": "Return the deposit with an itemized statement of lawful deductions within the required timeframe."},
                        {"party": "Tenant", "obligation": "Pay rent and utilities during the term and give 30 days' written notice to end the tenancy."},
                    ],
                    "deadlines": [],
                    "dates_found": [
                        {"date": "2024-03-01", "description": "Lease term began"},
                    ],
                    "entities": ["Maple Crest Properties Ltd.", "14 Maple Street, Toronto"],
                    "possible_issues": [],
                    "information_gaps": [],
                    "warnings": [],
                    "requires_verification": [],
                    "note": "",
                },
            },
        ],
        "timeline": [
            {"date": "2024-03-01", "title": "Lease signed", "description": "24-month written lease for 14 Maple Street, monthly rent $1,400.", "event_type": "document", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2024-03-02", "title": "Deposit paid", "description": "Security deposit of $2,800 (two months' rent) paid on move-in.", "event_type": "payment", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2024-03-03", "title": "Move-in inspection", "description": "Move-in inspection report notes 'minor wear on living room floor'.", "event_type": "document", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -60, "title": "30-day notice given", "description": "Written notice of move-out served to landlord.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -30, "title": "Move-out inspection", "description": "Landlord claims parquet damage; tenant disputes, citing move-in report.", "event_type": "incident", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -18, "title": "Deposit withheld", "description": "Landlord withholds entire deposit citing damage and 'unpaid utilities'.", "event_type": "incident", "importance": "high", "date_status": "user_confirmed", "source": "user"},
        ],
        "issues": [
            {
                "title": "Unlawful deduction of security deposit",
                "description": "Landlord withheld the deposit without an itemized statement of deductions within the legally required timeframe.",
                "category": "Tenant/Landlord", "jurisdiction": "Delhi", "confidence": "high",
                "provenance": "ai", "status": "investigating",
                "supporting_facts": ["Move-in report notes pre-existing floor wear", "Deposit of $2,800 fully withheld on move-out"],
                "related_documents": ["rental-lease.txt"],
                "missing_information": ["Whether an itemized statement was sent within the required window"],
                "impact": "If the statement deadline was missed, the withheld portion may be recoverable in full.",
            },
            {
                "title": "Pre-existing damage vs. new damage",
                "description": "Move-in inspection report shows pre-existing floor wear; landlord attributes all wear to the tenant.",
                "category": "Tenant/Landlord", "jurisdiction": "Delhi", "confidence": "medium",
                "provenance": "document", "status": "open",
                "supporting_facts": ["Move-in inspection notes 'minor wear on living room floor'", "Move-out photos show floor condition"],
                "related_documents": ["rental-lease.txt"],
                "missing_information": ["Comparative move-in/move-out photos dated the same way"],
                "impact": "Determines how much of the $2,800 can lawfully be kept for floor work.",
            },
        ],
        "gaps": [
            {"question": "Did the landlord send an itemized statement of deductions?", "why_it_matters": "The deadline for the statement may determine whether the deduction is lawful.", "priority": "high", "source": "ai", "how_to_find": "Check email and postal records around move-out; request a copy in writing.", "related_issue": "Unlawful deduction of security deposit"},
            {"question": "Are there photos of the floor from move-in and move-out?", "why_it_matters": "Photos would resolve the factual dispute about pre-existing wear.", "priority": "medium", "source": "ai", "how_to_find": "Recover photos from your phone and the landlord's inspection file.", "related_issue": "Pre-existing damage vs. new damage"},
        ],
        "risks": [
            {"title": "Missing itemized deduction statement", "description": "If the landlord never produced an itemized statement in time, the deduction may be recoverable.", "likelihood": "high", "impact": "medium", "overall_risk": "high", "mitigation": "Confirm the statutory window and whether the statement was ever sent.", "provenance": "ai"},
            {"title": "Disputed condition of flooring", "description": "The move-in report supports the tenant's version but photos would strengthen it.", "likelihood": "medium", "impact": "low", "overall_risk": "medium", "mitigation": "Attach dated move-in and move-out photos as evidence.", "provenance": "ai"},
        ],
        "evidence": [
            {"title": "Move-in inspection report", "description": "Signed report noting minor pre-existing wear on living room floor.", "item_type": "document", "source": "Tenant file", "date": "2024-03-03", "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Pre-existing damage vs. new damage", "Unlawful deduction of security deposit"]},
            {"title": "Utility receipts", "description": "Receipts covering the full tenancy period.", "item_type": "receipt", "source": "Email archive", "date": -10, "importance": "medium", "verification": "unverified", "status": "copy", "provenance": "user", "issues": ["Unlawful deduction of security deposit"]},
            {"title": "Move-out photos", "description": "Photos of the living room floor taken at move-out.", "item_type": "photo", "source": "Phone", "date": -30, "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Pre-existing damage vs. new damage"]},
            {"title": "Rental lease agreement", "description": "Signed 24-month lease for 14 Maple Street.", "item_type": "contract", "source": "Tenant file", "date": "2024-03-01", "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Unlawful deduction of security deposit"]},
        ],
        "scenarios": [
            {"name": "Landlord sends itemized statement late", "description": "Landlord provides the statement now, after the statutory window.", "parameters": "Assume the statement arrives 20 days after move-out and lists repainting and floor refinishing.", "risk_level": "medium", "facts": ["Landlord sends itemized statement 20 days after move-out", "Statement lists $2,300 of repainting and floor work", "Landlord keeps $500 for 'unpaid utilities'"]},
            {"name": "Negotiated partial return", "description": "Settle for a partial deposit return without a hearing.", "parameters": "Assume the landlord offers $1,800 of the $2,800.", "risk_level": "low", "facts": ["Landlord offers to return $1,800", "Tenant gives a release of further claims", "Landlord keeps $1,000"]},
        ],
        "prep": {
            "objective": "Return of the full $2,800 deposit, or only documented lawful deductions",
            "desired_outcome": "Full return without a hearing",
            "minimum_acceptable": "$2,300 returned (only the $500 utilities claim conceded if documented)",
            "key_evidence": "Move-in inspection report; utility receipts; rental lease; move-out photos",
            "counterpart_position": "Landlord claims floor damage and unpaid utilities justify keeping the deposit",
            "constraints": "Want to avoid a tribunal record; moving soon",
            "channel": "email",
            "goals": "Full return of the deposit, or the maximum lawful deduction only",
            "batna": "File at the residential tenancy tribunal; slow but favorable given the itemization failure",
            "interests": "Recover the deposit, avoid a legal record, settle quickly",
            "concessions": "Accept a small deduction if documented with invoices",
            "red_lines": "No admission that the wear was caused by me",
            "counterpart_analysis": "Landlord likely wants to avoid a tribunal and may fold if the itemization deadline was missed",
            "strategy": "Lead with the itemization deadline, present the move-in report, then ask what the landlord needs to settle",
        },
        "actions": [
            {"title": "Request itemized deduction statement in writing", "description": "Send a formal written request with a 7-day response deadline.", "priority": "high", "due": 3, "reason": "The statement deadline may decide whether the deduction is lawful.", "related_issue": "Unlawful deduction of security deposit", "required_evidence": "Copy of the written request and proof of delivery"},
            {"title": "Compile evidence pack", "description": "Assemble inspection report, receipts, photos, and lease into one PDF.", "priority": "medium", "due": 7, "reason": "A single pack makes both negotiation and any tribunal filing faster.", "required_evidence": "Inspection report, utility receipts, move-out photos, lease"},
            {"title": "Locate move-in photos of the living room floor", "description": "Search phone backups for March 2024 photos.", "priority": "medium", "reason": "Dated move-in photos directly support the wear-and-tear position.", "related_issue": "Pre-existing damage vs. new damage", "required_evidence": "Dated photos with metadata"},
        ],
        "deadlines": [
            {"title": "Deposit return deadline (statutory)", "description": "Deadline by which the landlord must return the deposit or provide an itemized statement.", "due": 14, "status": "pending", "source": "ai"},
        ],
    },
    # ------------------------------------------------------------------ 2
    {
        "kind": "employment",
        "icon": "bi-person-badge",
        "title": "Wrongful Termination Dispute",
        "case_type": "Employment",
        "country": "India",
        "state": "Karnataka",
        "jurisdiction": "India, Karnataka",
        "status": "analysis_in_progress",
        "stage": "Information gathering",
        "parties": "You (former sales supervisor) — vs — Northgate Retail Group Ltd. (employer)",
        "tagline": "Terminated 'effective immediately' by email after four years, with only two weeks offered instead of notice.",
        "description": (
            "I worked as a sales supervisor for Northgate Retail Group for four years. Last "
            "month I was told in a short email that my position was being eliminated in a "
            "'restructuring' and that I was terminated effective immediately. Two weeks' pay "
            "was offered as severance. I never signed a written employment agreement, no "
            "severance policy was ever shown to me, and in the same week two junior staff "
            "were assigned my duties, which makes me doubt the restructuring explanation. "
            "I believe the notice and severance offered are far below what I am entitled to "
            "after four years of service, but I have not been able to confirm my entitlements."
        ),
        "documents": [
            {
                "filename": "termination-email.txt",
                "content": (
                    "Subject: Position eliminated — next steps\n"
                    "From: h.r@northgateretail.example\n"
                    "To: you@example.com\n\n"
                    "Dear [Employee],\n\n"
                    "As part of a restructuring of store operations, your role of Sales "
                    "Supervisor, Store #12, is being eliminated effective immediately. "
                    "Your last working day is today. You will receive two weeks' base pay "
                    "as severance, plus pay for accrued vacation. A final statement will "
                    "follow by mail. Please return your store keys and laptop to the "
                    "office by end of day.\n\n"
                    "We thank you for your four years of service.\n"
                    "Northgate Retail Group Ltd."
                ),
                "analysis": {
                    "summary": "An email from Northgate's HR terminating the employee 'effective immediately' due to a restructuring, offering two weeks' base pay as severance and asking for keys and laptop the same day.",
                    "document_type": "termination letter / email",
                    "parties": [{"name": "Northgate Retail Group Ltd.", "role": "employer"}, {"name": "[Employee]", "role": "employee"}],
                    "key_facts": [
                        {"text": "The role of Sales Supervisor, Store #12 was 'eliminated effective immediately'.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "Two weeks' base pay was offered as severance.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "No notice period or reason beyond 'restructuring' is stated.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                    ],
                    "important_clauses": [],
                    "concerning_clauses": [
                        {"quote": "being eliminated effective immediately", "reason": "No working notice was given; whether the offered two weeks is adequate depends on service and role.", "severity": "high"},
                    ],
                    "obligations": [],
                    "deadlines": [],
                    "dates_found": [],
                    "entities": ["Northgate Retail Group Ltd.", "Store #12"],
                    "possible_issues": [],
                    "information_gaps": [],
                    "warnings": [],
                    "requires_verification": [],
                    "note": "",
                },
            },
        ],
        "timeline": [
            {"date": "2022-08-15", "title": "Hired as sales supervisor", "description": "Started at Northgate Retail Store #12 as a sales supervisor.", "event_type": "document", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2023-01-10", "title": "First annual raise", "description": "Raise to $62,000/year after positive first-year review.", "event_type": "payment", "importance": "low", "date_status": "user_confirmed", "source": "user"},
            {"date": "2025-09-01", "title": "New regional manager appointed", "description": "A new regional manager took over store operations.", "event_type": "communication", "importance": "medium", "date_status": "user_confirmed", "source": "user"},
            {"date": -42, "title": "Performance review", "description": "Review rated performance 'meets expectations' with no warnings.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -38, "title": "Termination email sent", "description": "Position eliminated 'effective immediately'; two weeks' pay offered.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "document"},
            {"date": -37, "title": "Keys and laptop returned", "description": "Returned equipment the day after termination.", "event_type": "other", "importance": "low", "date_status": "user_confirmed", "source": "user"},
            {"date": -10, "title": "Severance offer rejected in writing", "description": "Replied asking for the full entitlement and the restructuring evidence.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
        ],
        "issues": [
            {
                "title": "Inadequate notice and severance",
                "description": "Four years of service ended without working notice; two weeks' pay was offered as the only severance.",
                "category": "Employment", "jurisdiction": "Karnataka", "confidence": "high",
                "provenance": "ai", "status": "investigating",
                "supporting_facts": ["Four years of continuous service", "Termination email offered two weeks' pay with no working notice"],
                "related_documents": ["termination-email.txt"],
                "missing_information": ["Whether a written employment agreement or enforceable severance policy exists"],
                "impact": "The difference between two weeks offered and any greater entitlement is the direct financial stake.",
            },
            {
                "title": "Bad-faith / restructuring credibility",
                "description": "Duties were reassigned to two junior staff days after the claimed restructuring.",
                "category": "Employment", "jurisdiction": "Karnataka", "confidence": "low",
                "provenance": "user", "status": "open",
                "supporting_facts": ["Termination cited restructuring", "Two junior staff took over the duties within a week"],
                "related_documents": ["termination-email.txt"],
                "missing_information": ["Organization charts or hiring records around the termination date"],
                "impact": "If the restructuring was not genuine, notice and damages calculations could increase.",
            },
        ],
        "gaps": [
            {"question": "Was there a signed employment agreement or enforceable severance policy?", "why_it_matters": "A written agreement could cap or define what notice applies.", "priority": "high", "source": "ai", "how_to_find": "Check onboarding documents from 2022 and the employee handbook.", "related_issue": "Inadequate notice and severance"},
            {"question": "What were the actual termination date and offered amounts in writing?", "why_it_matters": "Precise dates anchor the notice-period calculation.", "priority": "medium", "source": "ai", "how_to_find": "The termination email and any final statement of pay.", "related_issue": "Inadequate notice and severance"},
            {"question": "Were duties really reassigned within the company?", "why_it_matters": "Reassignment can undermine the restructuring explanation.", "priority": "medium", "source": "ai", "how_to_find": "Job postings, internal announcements, or former colleagues.", "related_issue": "Bad-faith / restructuring credibility"},
        ],
        "risks": [
            {"title": "No written employment agreement", "description": "Without a signed agreement, entitlement is assessed on common-law principles; the employer may still argue otherwise.", "likelihood": "high", "impact": "high", "overall_risk": "high", "mitigation": "Locate onboarding documents and any handbook severance language.", "provenance": "ai"},
            {"title": "Evidence of reassignment is anecdotal", "description": "The restructuring challenge currently rests on word-of-mouth.", "likelihood": "medium", "impact": "medium", "overall_risk": "medium", "mitigation": "Collect postings or announcements showing the duties were filled.", "provenance": "ai"},
        ],
        "evidence": [
            {"title": "Termination email", "description": "Email eliminating the role 'effective immediately' with a two-week offer.", "item_type": "email", "source": "Personal inbox", "date": -38, "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Inadequate notice and severance"]},
            {"title": "Pay stubs (last 12 months)", "description": "Pay stubs showing base pay, no commission clawbacks.", "item_type": "document", "source": "Payroll portal", "date": -5, "importance": "high", "verification": "verified", "status": "copy", "provenance": "user", "issues": ["Inadequate notice and severance"]},
            {"title": "2025 performance review", "description": "Review rating 'meets expectations' with no warnings.", "item_type": "document", "source": "Manager file", "date": -42, "importance": "medium", "verification": "unverified", "status": "copy", "provenance": "user", "issues": ["Bad-faith / restructuring credibility"]},
            {"title": "Job posting for sales supervisor duties", "description": "Internal posting showing the duties being filled after termination.", "item_type": "message", "source": "Colleague screenshot", "date": -6, "importance": "medium", "verification": "unverified", "status": "copy", "provenance": "user", "issues": ["Bad-faith / restructuring credibility"]},
        ],
        "scenarios": [
            {"name": "Severance negotiation to statutory floor", "description": "Negotiate a higher severance package without litigation.", "parameters": "Assume employer moves from two weeks to eight weeks plus outplacement.", "risk_level": "medium", "facts": ["Employer increases offer from 2 to 8 weeks", "Outplacement support included", "Mutual release signed"]},
            {"name": "Wrongful dismissal claim", "description": "Pursue a claim for reasonable notice and any bad-faith component.", "parameters": "Assume no written agreement is found and duties were demonstrably reassigned.", "risk_level": "high", "facts": ["No employment agreement located", "Reassignment documented", "Claim filed for reasonable-notice damages"]},
        ],
        "prep": {
            "objective": "Fair notice/severance reflecting four years of service",
            "desired_outcome": "Eight to twelve weeks' pay plus outplacement, no litigation",
            "minimum_acceptable": "Six weeks' pay and a clean reference letter",
            "key_evidence": "Termination email; pay stubs; 2025 performance review; reassignment evidence",
            "counterpart_position": "Company treats two weeks as full and final under its 'restructuring' framing",
            "constraints": "Need a reference letter; employer controls records",
            "channel": "email then meeting",
            "goals": "Fair severance without litigation; protect the reference",
            "batna": "Statutory/legal claim for reasonable notice, which is slower and adversarial",
            "interests": "Cash runway while job-hunting; clean reference; no drawn-out dispute",
            "concessions": "Accept less cash if outplacement and reference are strong",
            "red_lines": "No signing a full release for two weeks' pay",
            "counterpart_analysis": "Employer likely standardized the two-week offer to close files cheaply; may raise it if documents are missing",
            "strategy": "Open by citing four years and the strong review, present pay stubs, then ask what they can offer before discussing a release",
        },
        "actions": [
            {"title": "Request the personnel file and employment records", "description": "Formally ask for the file, handbook, and any signed agreement.", "priority": "high", "due": 3, "reason": "Whether a written agreement exists drives the whole analysis.", "related_issue": "Inadequate notice and severance", "required_evidence": "Personnel file, handbook, signed agreement (if any)"},
            {"title": "Collect reassignment evidence", "description": "Screenshot postings and note who took over the duties.", "priority": "medium", "due": 10, "reason": "Reassignment undermines the restructuring explanation.", "related_issue": "Bad-faith / restructuring credibility", "required_evidence": "Postings, announcements, colleague notes"},
            {"title": "Preserve pay records", "description": "Export 12+ months of pay stubs and any bonus documents.", "priority": "high", "due": 5, "reason": "Compensation records anchor any notice calculation.", "required_evidence": "Pay stubs, tax slips, bonus statements"},
        ],
        "deadlines": [
            {"title": "Deadline to respond to severance offer", "description": "Employer's stated deadline for accepting the two-week offer.", "due": 6, "status": "pending", "source": "user"},
        ],
    },
    # ------------------------------------------------------------------ 3
    {
        "kind": "consumer",
        "icon": "bi-cart",
        "title": "Faulty Refrigerator Complaint",
        "case_type": "Consumer",
        "country": "India",
        "state": "Delhi",
        "jurisdiction": "India, Delhi",
        "status": "analysis_in_progress",
        "stage": "Information gathering",
        "parties": "You (buyer) — vs — MetroHome Appliances Pvt. Ltd. (retailer)",
        "tagline": "A ₹48,000 refrigerator failed within the warranty year; the retailer refuses a refund or replacement.",
        "description": (
            "I bought a double-door refrigerator from MetroHome Appliances for ₹48,000 in "
            "January. The unit stopped cooling in August, still inside the one-year "
            "warranty. The technician's report confirmed a compressor fault and said the "
            "part would take '6–8 weeks' to arrive. I asked for a replacement or refund; "
            "the store says warranty covers 'repair only', and the brand says the delay is "
            "not their problem. The invoice lists the store as the seller, and the warranty "
            "card was never given to me at purchase."
        ),
        "documents": [
            {
                "filename": "purchase-invoice.txt",
                "content": (
                    "TAX INVOICE — MetroHome Appliances Pvt. Ltd., Shop 12, Central Market, "
                    "New Delhi\n"
                    "Invoice No: MH-88231  Date: 2026-01-12\n"
                    "Item: FrostFree Double-Door Refrigerator 285L (Model FZ-285)\n"
                    "Qty: 1   Unit Price: ₹48,000   Total: ₹48,000\n"
                    "Payment: Paid in full by card\n"
                    "Seller: MetroHome Appliances Pvt. Ltd.\n"
                    "Warranty: 1 year manufacturer warranty on compressor and parts."
                ),
                "analysis": {
                    "summary": "A tax invoice showing the ₹48,000 purchase of a Model FZ-285 refrigerator from MetroHome Appliances on 2026-01-12, paid in full, with a one-year manufacturer warranty on compressor and parts.",
                    "document_type": "invoice / receipt",
                    "parties": [{"name": "MetroHome Appliances Pvt. Ltd.", "role": "seller"}, {"name": "the Buyer", "role": "buyer"}],
                    "key_facts": [
                        {"text": "The refrigerator (Model FZ-285) was bought for ₹48,000 on 2026-01-12.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "Payment was made in full by card.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "A one-year manufacturer warranty covers the compressor and parts.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                    ],
                    "important_clauses": [],
                    "concerning_clauses": [
                        {"quote": "1 year manufacturer warranty on compressor and parts", "reason": "The wording does not say what happens if parts are unavailable for weeks — repair-only could be disputed.", "severity": "medium"},
                    ],
                    "obligations": [],
                    "deadlines": [],
                    "dates_found": [{"date": "2026-01-12", "description": "Purchase date"}],
                    "entities": ["MetroHome Appliances Pvt. Ltd.", "Model FZ-285"],
                    "possible_issues": [],
                    "information_gaps": [],
                    "warnings": [],
                    "requires_verification": [],
                    "note": "",
                },
            },
        ],
        "timeline": [
            {"date": "2026-01-12", "title": "Purchased refrigerator", "description": "Bought Model FZ-285 for ₹48,000 from MetroHome Appliances.", "event_type": "payment", "importance": "high", "date_status": "user_confirmed", "source": "document"},
            {"date": "2026-08-04", "title": "Unit stopped cooling", "description": "Refrigerator stopped cooling; food spoiled.", "event_type": "incident", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2026-08-11", "title": "Technician diagnosis", "description": "Service report confirms compressor fault; part lead time '6–8 weeks'.", "event_type": "document", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2026-08-20", "title": "Refund/replacement refused", "description": "Store says warranty is 'repair only'; brand blames the store.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -3, "title": "Written complaint to store", "description": "Sent a formal complaint asking for replacement or refund.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
        ],
        "issues": [
            {
                "title": "Defective goods — replacement or refund",
                "description": "A major appliance failed inside the warranty year and the seller refuses a replacement or refund, offering only a slow repair.",
                "category": "Consumer", "jurisdiction": "Delhi", "confidence": "high",
                "provenance": "ai", "status": "investigating",
                "supporting_facts": ["Compressor fault confirmed by technician within warranty year", "₹48,000 paid in full"],
                "related_documents": ["purchase-invoice.txt"],
                "missing_information": ["Warranty card terms and whether repair-only language is enforceable"],
                "impact": "A non-working ₹48,000 appliance plus food-loss costs are at stake.",
            },
            {
                "title": "Unreasonable repair delay", "description": "A 6–8 week parts delay leaves the household without a working refrigerator.",
                "category": "Consumer", "jurisdiction": "Delhi", "confidence": "medium",
                "provenance": "ai", "status": "open",
                "supporting_facts": ["Technician confirmed the part lead time", "Refrigerator essential to household food storage"],
                "related_documents": [],
                "missing_information": ["Whether the retailer or brand can supply the part sooner"],
                "impact": "Supports treating the warranty remedy as commercially unreasonable.",
            },
        ],
        "gaps": [
            {"question": "What does the warranty card actually say about replacement?", "why_it_matters": "The card was withheld at purchase; its terms may support or block a replacement.", "priority": "high", "source": "ai", "how_to_find": "Ask for the warranty card or registration documents from the store.", "related_issue": "Defective goods — replacement or refund"},
            {"question": "Was there a cooling-performance complaint record in the first days?", "why_it_matters": "Early complaints could support a 'not of merchantable quality' position.", "priority": "low", "source": "ai", "how_to_find": "Call logs and messages to the store in the first week."},
        ],
        "risks": [
            {"title": "Repair-only warranty wording", "description": "If the warranty genuinely limits the remedy to repair, the refund argument rests on how unreasonable the delay is.", "likelihood": "medium", "impact": "high", "overall_risk": "high", "mitigation": "Obtain the warranty card and the technician report in writing.", "provenance": "ai"},
            {"title": "Evidence of the fault is oral so far", "description": "The technician's findings should be captured in a dated written report.", "likelihood": "medium", "impact": "medium", "overall_risk": "medium", "mitigation": "Request a signed service report and photos of the compressor unit.", "provenance": "ai"},
        ],
        "evidence": [
            {"title": "Purchase invoice", "description": "Tax invoice for ₹48,000, paid in full by card.", "item_type": "receipt", "source": "Email", "date": "2026-01-12", "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Defective goods — replacement or refund"]},
            {"title": "Technician service report", "description": "Written diagnosis confirming compressor fault and 6–8 week parts delay.", "item_type": "document", "source": "Service centre", "date": "2026-08-11", "importance": "high", "verification": "unverified", "status": "copy", "provenance": "user", "issues": ["Defective goods — replacement or refund", "Unreasonable repair delay"]},
            {"title": "Photo of fault code display", "description": "Photo of the error code shown on the unit when it failed.", "item_type": "photo", "source": "Phone", "date": "2026-08-04", "importance": "medium", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Defective goods — replacement or refund"]},
            {"title": "Written complaint to store", "description": "Formal complaint email asking for replacement or refund.", "item_type": "email", "source": "Sent folder", "date": -3, "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Defective goods — replacement or refund"]},
        ],
        "scenarios": [
            {"name": "Escalation to consumer forum", "description": "File a consumer complaint if the store keeps refusing.", "parameters": "Assume the store does not respond to the complaint within 15 days.", "risk_level": "high", "facts": ["Store does not respond in 15 days", "Consumer complaint filed", "Relief sought: replacement or refund plus compensation"]},
            {"name": "Replacement negotiated with brand", "description": "Approach the brand directly for a replacement unit.", "parameters": "Assume the brand offers a comparable replacement within 3 weeks.", "risk_level": "low", "facts": ["Brand offers comparable replacement", "Delivery within 3 weeks", "Original warranty continues on the new unit"]},
        ],
        "prep": {
            "objective": "Replacement unit or full refund for the faulty refrigerator",
            "desired_outcome": "Replacement delivered within three weeks",
            "minimum_acceptable": "Full refund on return of the unit",
            "key_evidence": "Purchase invoice; technician service report; photos of the fault",
            "counterpart_position": "Store: warranty covers repair only; Brand: delay is not their problem",
            "constraints": "Need a working refrigerator now; no appetite for months of process",
            "channel": "email then phone",
            "goals": "Working refrigerator promptly, zero extra cost",
            "batna": "Consumer forum complaint; slower but typically effective for major appliances",
            "interests": "Food storage restored; no extra expense; principle about paid warranty",
            "concessions": "Accept a comparable model rather than the identical one",
            "red_lines": "No paying for the replacement part or labour",
            "counterpart_analysis": "The store quotes a blanket policy; the brand deflects to the store — playing them against each other may unlock a replacement",
            "strategy": "Send both parties the complaint with the service report, name a 7-day response window, then escalate to the brand's regional office",
        },
        "actions": [
            {"title": "Obtain the warranty card", "description": "Request the warranty card and registration terms from the store.", "priority": "high", "due": 4, "reason": "Its exact wording decides whether 'repair only' can block a replacement.", "related_issue": "Defective goods — replacement or refund", "required_evidence": "Warranty card or registration terms"},
            {"title": "Get a signed service report", "description": "Ask the technician for a dated, signed copy of the diagnosis.", "priority": "high", "due": 7, "reason": "A signed report is the core proof of the defect.", "related_issue": "Defective goods — replacement or refund", "required_evidence": "Signed service report with the model and fault code"},
            {"title": "Track food-loss costs", "description": "List spoiled food and any temporary cooling costs.", "priority": "low", "due": 14, "reason": "Quantifies the loss should you seek compensation.", "required_evidence": "Receipts and a dated loss list"},
        ],
        "deadlines": [
            {"title": "Response window for store complaint", "description": "Deadline set in the formal complaint for a response before escalation.", "due": 12, "status": "pending", "source": "user"},
        ],
    },
    # ------------------------------------------------------------------ 4
    {
        "kind": "contract",
        "icon": "bi-file-earmark-text",
        "title": "Software Delivery Contract Dispute",
        "case_type": "Contract",
        "country": "India",
        "state": "Maharashtra",
        "jurisdiction": "India, Maharashtra",
        "status": "analysis_in_progress",
        "stage": "Information gathering",
        "parties": "NovaPay Systems LLC — vs — FinBridge Inc.",
        "tagline": "A $180,000 services agreement went live late; FinBridge withheld payment, NovaPay calls it scope creep.",
        "description": (
            "NovaPay Systems agreed to deliver a payments-integration module for FinBridge "
            "under a $180,000 fixed-fee services agreement. The contract set a go-live date "
            "and a defined scope. During delivery, FinBridge requested eleven changes that "
            "NovaPay says were outside scope; FinBridge says they were always included. "
            "Go-live slipped by six weeks. FinBridge now withholds the final $60,000 "
            "milestone and threatens to claim delay damages. NovaPay has emails agreeing to "
            "each change but no signed change orders. The contract contains no explicit "
            "change-control clause."
        ),
        "documents": [
            {
                "filename": "services-agreement.txt",
                "content": (
                    "SERVICES AGREEMENT between NovaPay Systems LLC ('Vendor') and FinBridge "
                    "Inc. ('Client'), effective 2025-11-03.\n\n"
                    "SCOPE: Vendor will deliver the payments-integration module described in "
                    "Exhibit A, including API connectivity, reconciliation reporting, and "
                    "user acceptance testing support.\n"
                    "FEES: Fixed fee of $180,000 payable in three milestones: $60,000 on "
                    "signing, $60,000 on acceptance, $60,000 on go-live.\n"
                    "SCHEDULE: Go-live target 2026-04-15. Time is of the essence for the "
                    "April release window.\n"
                    "ACCEPTANCE: Client will test and either accept or provide a written "
                    "defect list within 15 business days of delivery.\n"
                    "WARRANTY: Vendor warrants the module will materially conform to "
                    "Exhibit A for 90 days after go-live."
                ),
                "analysis": {
                    "summary": "A fixed-fee services agreement for a payments-integration module: $180,000 in three milestones, an April 15 go-live target described as time-sensitive, a 15-business-day acceptance process, and a 90-day warranty.",
                    "document_type": "services agreement",
                    "parties": [{"name": "NovaPay Systems LLC", "role": "vendor"}, {"name": "FinBridge Inc.", "role": "client"}],
                    "key_facts": [
                        {"text": "Fixed fee of $180,000 payable in three $60,000 milestones.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "Go-live target was 2026-04-15 and 'time is of the essence'.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "No change-control clause appears in the agreement text.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                    ],
                    "important_clauses": [
                        {"quote": "Time is of the essence for the April release window.", "meaning": "Schedule language strengthens a delay-damages argument if the slip is material.", "section": "SCHEDULE"},
                        {"quote": "Fixed fee of $180,000 payable in three milestones: $60,000 on signing, $60,000 on acceptance, $60,000 on go-live.", "meaning": "The final milestone is payable on go-live, not on the client's satisfaction with extra changes.", "section": "FEES"},
                    ],
                    "concerning_clauses": [
                        {"quote": "Time is of the essence", "reason": "The six-week slip could be framed as a material breach by the client.", "severity": "high"},
                        {"quote": "the payments-integration module described in Exhibit A", "reason": "Whether the eleven changes were inside Exhibit A is the core dispute.", "severity": "high"},
                    ],
                    "obligations": [
                        {"party": "Vendor", "obligation": "Deliver the module per Exhibit A and reach go-live."},
                        {"party": "Client", "obligation": "Pay each milestone on schedule and test/accept within 15 business days."},
                    ],
                    "deadlines": [],
                    "dates_found": [{"date": "2026-04-15", "description": "Go-live target date"}],
                    "entities": ["NovaPay Systems LLC", "FinBridge Inc.", "Exhibit A"],
                    "possible_issues": [],
                    "information_gaps": [],
                    "warnings": [],
                    "requires_verification": [],
                    "note": "",
                },
            },
        ],
        "timeline": [
            {"date": "2025-11-03", "title": "Agreement signed", "description": "Fixed-fee $180,000 services agreement effective.", "event_type": "document", "importance": "high", "date_status": "user_confirmed", "source": "document"},
            {"date": "2025-11-10", "title": "First milestone paid", "description": "$60,000 signing milestone received.", "event_type": "payment", "importance": "medium", "date_status": "user_confirmed", "source": "user"},
            {"date": "2026-02-09", "title": "Second milestone paid", "description": "$60,000 acceptance milestone received after initial testing.", "event_type": "payment", "importance": "medium", "date_status": "user_confirmed", "source": "user"},
            {"date": -80, "title": "Change requests begin", "description": "FinBridge emails eleven change requests that NovaPay treats as out of scope.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -42, "title": "Go-live slipped six weeks", "description": "New go-live agreed by email; no change order signed.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -20, "title": "Final milestone withheld", "description": "FinBridge withholds the $60,000 go-live milestone and threatens delay damages.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
        ],
        "issues": [
            {
                "title": "Withheld final milestone payment",
                "description": "The $60,000 go-live milestone is unpaid although the module reached go-live.",
                "category": "Contract", "jurisdiction": "Maharashtra", "confidence": "high",
                "provenance": "ai", "status": "investigating",
                "supporting_facts": ["Agreement ties the final milestone to go-live", "Module reached go-live six weeks late"],
                "related_documents": ["services-agreement.txt"],
                "missing_information": ["Whether the changes were inside Exhibit A scope"],
                "impact": "$60,000 plus any agreed interest is the direct exposure.",
            },
            {
                "title": "Unscoped change requests",
                "description": "Eleven changes were delivered without signed change orders; the client now calls them in-scope.",
                "category": "Contract", "jurisdiction": "Maharashtra", "confidence": "medium",
                "provenance": "ai", "status": "open",
                "supporting_facts": ["Eleven change requests delivered by email", "No change-control clause in the agreement"],
                "related_documents": ["services-agreement.txt"],
                "missing_information": ["Exhibit A scope wording and the emails agreeing to changes"],
                "impact": "Determines who bears the cost of the changes and who caused the delay.",
            },
        ],
        "gaps": [
            {"question": "What exactly does Exhibit A list as in-scope?", "why_it_matters": "It decides whether the eleven changes were extras or always included.", "priority": "high", "source": "ai", "how_to_find": "Exhibit A is attached to the signed agreement.", "related_issue": "Unscoped change requests"},
            {"question": "Which party caused each week of the delay?", "why_it_matters": "Delay damages depend on fault; contemporaneous emails matter.", "priority": "high", "source": "ai", "how_to_find": "Project emails and standup notes between February and April.", "related_issue": "Withheld final milestone payment"},
            {"question": "Did FinBridge ever issue a written defect list?", "why_it_matters": "Acceptance terms require a written defect list within 15 business days.", "priority": "medium", "source": "ai", "how_to_find": "Check the acceptance-period correspondence."},
        ],
        "risks": [
            {"title": "No change-control clause", "description": "Without a written change order, scope disputes rest on emails and Exhibit A wording.", "likelihood": "high", "impact": "high", "overall_risk": "high", "mitigation": "Assemble the full email chain agreeing to each change.", "provenance": "ai"},
            {"title": "Time-is-of-the-essence clause", "description": "The six-week slip gives the client a hook for delay-damages claims.", "likelihood": "medium", "impact": "high", "overall_risk": "high", "mitigation": "Document client-driven delays and the absence of signed change orders.", "provenance": "ai"},
        ],
        "evidence": [
            {"title": "Signed services agreement", "description": "$180,000 fixed-fee agreement with milestone schedule.", "item_type": "contract", "source": "Legal file", "date": "2025-11-03", "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Withheld final milestone payment", "Unscoped change requests"]},
            {"title": "Change-request email chain", "description": "Eleven change requests with NovaPay's acceptances.", "item_type": "email", "source": "Project inbox", "date": -80, "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Unscoped change requests"]},
            {"title": "Go-live sign-off email", "description": "Client confirmation that the module went live (with the new date).", "item_type": "email", "source": "Project inbox", "date": -38, "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Withheld final milestone payment"]},
            {"title": "Milestone payment records", "description": "Bank records of the first two $60,000 payments.", "item_type": "receipt", "source": "Bank statements", "date": -120, "importance": "medium", "verification": "verified", "status": "copy", "provenance": "user", "issues": ["Withheld final milestone payment"]},
        ],
        "scenarios": [
            {"name": "Demand letter then negotiation", "description": "Send a formal demand for the final milestone and negotiate.", "parameters": "Assume FinBridge counters with a $20,000 deduction for delay.", "risk_level": "medium", "facts": ["Demand letter issued for $60,000", "Client counters at $40,000 settlement", "Mutual release of delay claims"]},
            {"name": "Litigation over the milestone", "description": "File a breach-of-contract claim for the withheld milestone.", "parameters": "Assume scope and delay fault are genuinely disputed.", "risk_level": "high", "facts": ["Claim filed for $60,000 plus interest", "Client counterclaims delay damages", "Discovery focuses on emails and Exhibit A"]},
        ],
        "prep": {
            "objective": "Payment of the $60,000 go-live milestone",
            "desired_outcome": "Full milestone paid without discounting the change work",
            "minimum_acceptable": "$50,000 with a mutual release of delay claims",
            "key_evidence": "Signed agreement; go-live sign-off email; change-request email chain; payment records",
            "counterpart_position": "Client treats late delivery as the issue and the changes as in-scope",
            "constraints": "Ongoing business relationship; avoid burning the account",
            "channel": "email",
            "goals": "Cash flow; preserve the client for future work if possible",
            "batna": "Breach-of-contract claim for the milestone plus interest",
            "interests": "Get paid; keep a reference; avoid discovery costs",
            "concessions": "Small discount if paired with a mutual release",
            "red_lines": "No admission that the changes were in-scope or that delay damages are owed",
            "counterpart_analysis": "FinBridge likely wants to avoid a suit but will use the schedule clause as leverage for a discount",
            "strategy": "Lead with the go-live sign-off and the milestone wording, table the change-request emails, then offer a small discount for a same-week resolution",
        },
        "actions": [
            {"title": "Assemble the change-request chain", "description": "Export the full email chain for all eleven changes with dates.", "priority": "high", "due": 3, "reason": "Proves the changes were requested and accepted, undermining the in-scope claim.", "related_issue": "Unscoped change requests", "required_evidence": "Email chain export with headers"},
            {"title": "Map the six-week delay to causes", "description": "Build a week-by-week delay log from project notes.", "priority": "medium", "due": 7, "reason": "Shifts the delay-damages narrative from blanket lateness to client-driven causes.", "related_issue": "Withheld final milestone payment", "required_evidence": "Project notes, standup logs, change dates"},
            {"title": "Draft the demand letter", "description": "Set out the milestone, the go-live sign-off, and a response window.", "priority": "high", "due": 5, "reason": "A clear demand often unlocks payment before litigation.", "related_issue": "Withheld final milestone payment", "required_evidence": "Signed agreement and sign-off email"},
        ],
        "deadlines": [
            {"title": "Response window in demand letter", "description": "Deadline for FinBridge to respond before escalation.", "due": 10, "status": "pending", "source": "user"},
        ],
    },
    # ------------------------------------------------------------------ 5
    {
        "kind": "property",
        "icon": "bi-signpost-split",
        "title": "Fence Encroachment Dispute",
        "case_type": "Property",
        "country": "India",
        "state": "Kerala",
        "jurisdiction": "India, Kerala",
        "status": "analysis_in_progress",
        "stage": "Information gathering",
        "parties": "You (owner, 8 Lakeside Drive) — vs — the adjoining owner of 10 Lakeside Drive",
        "tagline": "A new boundary fence and gate sit almost a metre over the line, blocking the driveway easement.",
        "description": (
            "The owner of the neighbouring property replaced the shared boundary fence and "
            "installed a gate that encroaches roughly 0.8 metres onto my land, according to "
            "a licensed survey I paid for. The gate also blocks part of a long-standing "
            "driveway easement I use to reach my rear garage. I asked them to move the fence "
            "back to the surveyed boundary; they refused, saying the fence has 'always been "
            "where it is'. The previous fence was on the boundary, and I have photos from "
            "the renovation showing the original posts."
        ),
        "documents": [
            {
                "filename": "boundary-survey.txt",
                "content": (
                    "BOUNDARY SURVEY REPORT — Lot 41 DP 88213, 8 Lakeside Drive\n"
                    "Surveyor: Coastal Land Surveys Pty Ltd   Report date: 2026-06-02\n\n"
                    "The survey confirms the registered boundary between 8 and 10 Lakeside "
                    "Drive. The recently installed fence and gate on the western boundary "
                    "of Lot 41 encroach approximately 0.8 metres onto Lot 41 at the widest "
                    "point. The encroaching structure also crosses the alignment of the "
                    "registered carriageway easement benefiting Lot 41.\n\n"
                    "Plan reference: Plan 88213 deposited 1978. Survey marks: boundary pegs "
                    "were recovered at the north-east and south-west corners."
                ),
                "analysis": {
                    "summary": "A licensed survey of 8 Lakeside Drive confirming that the newly installed fence and gate encroach about 0.8 metres onto the lot and cross the registered driveway easement alignment.",
                    "document_type": "survey report",
                    "parties": [{"name": "Coastal Land Surveys Pty Ltd", "role": "surveyor"}],
                    "key_facts": [
                        {"text": "The fence and gate encroach approximately 0.8 metres onto Lot 41.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "The encroaching structure crosses the registered carriageway easement benefiting 8 Lakeside Drive.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                        {"text": "Boundary pegs were recovered at both corners of the boundary.", "source": "document", "label": "FACT EXTRACTED FROM DOCUMENT"},
                    ],
                    "important_clauses": [],
                    "concerning_clauses": [],
                    "obligations": [],
                    "deadlines": [],
                    "dates_found": [{"date": "2026-06-02", "description": "Survey report date"}],
                    "entities": ["Coastal Land Surveys Pty Ltd", "Lot 41 DP 88213", "8 Lakeside Drive"],
                    "possible_issues": [],
                    "information_gaps": [],
                    "warnings": [],
                    "requires_verification": [],
                    "note": "",
                },
            },
        ],
        "timeline": [
            {"date": "2025-11-18", "title": "Neighbour installed new fence", "description": "Boundary fence replaced without prior discussion; gate installed at the rear.", "event_type": "incident", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2025-11-25", "title": "Gate blocked driveway access", "description": "Discovered the gate obstructed the rear driveway used for the garage.", "event_type": "incident", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": "2026-06-02", "title": "Boundary survey completed", "description": "Licensed survey confirms ~0.8 m encroachment over the easement line.", "event_type": "document", "importance": "high", "date_status": "user_confirmed", "source": "document"},
            {"date": "2026-06-15", "title": "Removal request refused", "description": "Neighbour refused, claiming the fence was 'always' in its current position.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
            {"date": -8, "title": "Solicitor's letter sent", "description": "Letter citing the survey asked for removal within 21 days.", "event_type": "communication", "importance": "high", "date_status": "user_confirmed", "source": "user"},
        ],
        "issues": [
            {
                "title": "Encroachment onto the boundary line",
                "description": "A newly installed fence and gate encroach ~0.8 m onto the surveyed boundary.",
                "category": "Property", "jurisdiction": "Kerala", "confidence": "high",
                "provenance": "ai", "status": "investigating",
                "supporting_facts": ["Licensed survey confirms the encroachment", "Boundary pegs recovered at both corners"],
                "related_documents": ["boundary-survey.txt"],
                "missing_information": ["Whether the neighbour disputes the survey or the fence's age"],
                "impact": "Loss of land and continuing trespass until the fence is moved.",
            },
            {
                "title": "Obstruction of the driveway easement",
                "description": "The gate blocks part of the registered carriageway easement used to reach the garage.",
                "category": "Property", "jurisdiction": "Kerala", "confidence": "high",
                "provenance": "ai", "status": "investigating",
                "supporting_facts": ["Survey confirms the gate crosses the easement alignment", "Garage access is materially hindered"],
                "related_documents": ["boundary-survey.txt"],
                "missing_information": ["Title search confirming the easement instrument"],
                "impact": "Interference with a registered right of way may support an order to remove the gate.",
            },
        ],
        "gaps": [
            {"question": "What does the title register say about the easement?", "why_it_matters": "The registered easement instrument defines its width and terms.", "priority": "high", "source": "ai", "how_to_find": "Order a title search and the deposited plan from the land registry.", "related_issue": "Obstruction of the driveway easement"},
            {"question": "How old is the neighbour's claimed fence line?", "why_it_matters": "Adverse-possession style claims can be raised for longstanding boundary features.", "priority": "medium", "source": "ai", "how_to_find": "Historic aerial photos and council records of the properties."},
        ],
        "risks": [
            {"title": "Neighbour claims longstanding boundary", "description": "If the fence line were treated as long-established, remedies could shift.", "likelihood": "low", "impact": "high", "overall_risk": "medium", "mitigation": "Keep the pre-works photos and any council approvals showing the original posts on the boundary.", "provenance": "ai"},
            {"title": "Cost of boundary litigation", "description": "Formal proceedings are expensive relative to the strip of land.", "likelihood": "medium", "impact": "medium", "overall_risk": "medium", "mitigation": "Exhaust negotiation and statutory notices before any hearing.", "provenance": "ai"},
        ],
        "evidence": [
            {"title": "Licensed boundary survey", "description": "Survey report confirming the encroachment and easement obstruction.", "item_type": "document", "source": "Coastal Land Surveys", "date": "2026-06-02", "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Encroachment onto the boundary line", "Obstruction of the driveway easement"]},
            {"title": "Pre-works photos of original fence", "description": "Photos from the 2024 renovation showing the original posts on the boundary line.", "item_type": "photo", "source": "Phone / renovation file", "date": "2024-04-10", "importance": "high", "verification": "verified", "status": "original", "provenance": "user", "issues": ["Encroachment onto the boundary line"]},
            {"title": "Solicitor's removal letter", "description": "Letter to the neighbour citing the survey with a 21-day window.", "item_type": "document", "source": "Solicitor", "date": -8, "importance": "high", "verification": "verified", "status": "copy", "provenance": "user", "issues": ["Encroachment onto the boundary line"]},
            {"title": "Neighbour's refusal reply", "description": "Written reply refusing to move the fence.", "item_type": "email", "source": "Correspondence file", "date": -120, "importance": "medium", "verification": "unverified", "status": "copy", "provenance": "user", "issues": ["Encroachment onto the boundary line"]},
        ],
        "scenarios": [
            {"name": "Negotiated fence relocation", "description": "Neighbour agrees to move the fence back after the statutory notice.", "parameters": "Assume the neighbour concedes on the survey and splits the removal cost.", "risk_level": "low", "facts": ["Neighbour agrees to move the fence to the boundary", "Removal cost shared", "Gate relocated clear of the easement"]},
            {"name": "Statutory boundary order", "description": "Apply for an order to remove the encroaching fence and restore the easement.", "parameters": "Assume the neighbour refuses to engage after the notice expires.", "risk_level": "medium", "facts": ["Statutory application filed", "Survey tendered as evidence", "Order sought for removal within 60 days"]},
        ],
        "prep": {
            "objective": "Fence and gate moved back to the surveyed boundary, easement unobstructed",
            "desired_outcome": "Neighbour agrees to relocate within 60 days, costs shared fairly",
            "minimum_acceptable": "Relocation on the neighbour's cost if the encroachment is admitted",
            "key_evidence": "Boundary survey; pre-works photos; title search showing the easement",
            "counterpart_position": "Neighbour believes the fence was always on the current line and will resist moving it",
            "constraints": "Neighbourly relationship; avoiding litigation costs on a small strip of land",
            "channel": "email then in person",
            "goals": "Boundary restored without a hearing; preserve neighbourly relations",
            "batna": "Statutory boundary/easement application backed by the survey",
            "interests": "Full use of the driveway; clear title line; low conflict",
            "concessions": "Share removal costs if the fence is moved promptly",
            "red_lines": "No acceptance that the current line is the boundary",
            "counterpart_analysis": "The neighbour likely values avoiding legal cost more than the half-metre strip and may move if removal is framed as the cheapest option",
            "strategy": "Present the survey and photos calmly, offer cost-sharing for a prompt move, and name the statutory route only as a fallback",
        },
        "actions": [
            {"title": "Order the title search", "description": "Obtain the title and registered easement instrument from the land registry.", "priority": "high", "due": 7, "reason": "Defines the easement width and the registered boundary.", "related_issue": "Obstruction of the driveway easement", "required_evidence": "Title search and deposited plan"},
            {"title": "Collect pre-works photos and approvals", "description": "Gather renovation photos and any council approvals showing the original posts.", "priority": "high", "due": 5, "reason": "Directly rebuts the 'always been there' claim.", "related_issue": "Encroachment onto the boundary line", "required_evidence": "Dated photos, approvals, fencing invoices"},
            {"title": "Track the 21-day notice window", "description": "Note when the solicitor's letter deadline expires and next steps.", "priority": "medium", "due": 13, "reason": "A clear expiry date creates the option to escalate cleanly.", "required_evidence": "Copy of the solicitor's letter and proof of delivery"},
        ],
        "deadlines": [
            {"title": "21-day notice to remove the fence", "description": "Deadline in the solicitor's letter before statutory steps are considered.", "due": 13, "status": "pending", "source": "user"},
        ],
    },
]


def demo_catalog_meta():
    """Public, fictional metadata for the Explore Demo Case picker."""
    ordered = [d for d in DEMO_CATALOG if d["kind"] in DEMO_ORDER]
    ordered.sort(key=lambda d: DEMO_ORDER.index(d["kind"]))
    return [
        {
            "kind": d["kind"],
            "title": d["title"],
            "case_type": d["case_type"],
            "jurisdiction": d["jurisdiction"],
            "tagline": d["tagline"],
            "icon": d.get("icon", "bi-briefcase"),
            "stacks": _stack_summary(d),
        }
        for d in ordered
    ]


def _stack_summary(defn) -> dict:
    return {
        "documents": len(defn.get("documents", [])),
        "timeline": len(defn.get("timeline", [])),
        "issues": len(defn.get("issues", [])),
        "evidence": len(defn.get("evidence", [])),
        "risks": len(defn.get("risks", [])),
        "scenarios": len(defn.get("scenarios", [])),
        "actions": len(defn.get("actions", [])),
    }


def _resolve_date(value):
    if isinstance(value, int):
        from datetime import date, timedelta
        return date.today() + timedelta(days=value)
    from datetime import date
    return date.fromisoformat(value)


def _defn(kind: str) -> dict:
    for d in DEMO_CATALOG:
        if d["kind"] == kind:
            return d
    raise KeyError(f"Unknown demo kind: {kind}")


def create_demo_case(user_id: int, kind: str = "rental") -> Case:
    """Build one fully-populated fictional demo case for a user."""
    defn = _defn(kind)
    case = Case(
        user_id=user_id,
        title=defn["title"],
        case_type=defn["case_type"],
        description=defn["description"],
        parties=defn.get("parties", ""),
        country=defn["country"],
        state=defn["state"],
        jurisdiction=defn["jurisdiction"],
        stage=defn.get("stage", "Information gathering"),
        status=defn.get("status", "analysis_in_progress"),
        is_demo=True,
    )
    db.session.add(case)
    db.session.flush()

    # Documents (with fictional content + ready-made analyses).
    issue_by_title = {i["title"]: i for i in defn.get("issues", [])}
    for doc in defn.get("documents", []):
        stored = uuid.uuid4().hex + ".txt"
        db.session.add(CaseDocument(
            case_id=case.id,
            filename=doc["filename"],
            stored_name=stored,
            file_type="txt",
            mime_type="text/plain",
            size_bytes=len(doc["content"].encode("utf-8")),
            text_content=doc["content"],
            extraction_status="extracted",
            analysis_status="analyzed",
            analysis_json=json.dumps(doc.get("analysis", {})),
        ))

    for ev in defn.get("timeline", []):
        db.session.add(TimelineEvent(
            case_id=case.id,
            date=_resolve_date(ev["date"]),
            title=ev["title"],
            description=ev.get("description", ""),
            event_type=ev.get("event_type", "other"),
            importance=ev.get("importance", "medium"),
            date_status=ev.get("date_status", "user_confirmed"),
            source=ev.get("source", "user"),
        ))

    for iss in defn.get("issues", []):
        db.session.add(LegalIssue(
            case_id=case.id,
            title=iss["title"],
            description=iss.get("description", ""),
            category=iss.get("category", ""),
            jurisdiction=iss.get("jurisdiction", ""),
            confidence=iss.get("confidence", "medium"),
            provenance=iss.get("provenance", "ai"),
            status=iss.get("status", "open"),
            supporting_facts=json.dumps(iss.get("supporting_facts", [])),
            related_documents=json.dumps(iss.get("related_documents", [])),
            missing_information=json.dumps(iss.get("missing_information", [])),
            impact=iss.get("impact", ""),
        ))

    for gap in defn.get("gaps", []):
        db.session.add(InfoGap(
            case_id=case.id,
            question=gap["question"],
            why_it_matters=gap.get("why_it_matters", ""),
            priority=gap.get("priority", "medium"),
            source=gap.get("source", "ai"),
            status=gap.get("status", "open"),
            related_issue=gap.get("related_issue", ""),
            how_to_find=gap.get("how_to_find", ""),
        ))

    for risk in defn.get("risks", []):
        db.session.add(RiskFactor(
            case_id=case.id,
            title=risk["title"],
            description=risk.get("description", ""),
            likelihood=risk.get("likelihood", "medium"),
            impact=risk.get("impact", "medium"),
            overall_risk=risk.get("overall_risk", "medium"),
            mitigation=risk.get("mitigation", ""),
            provenance=risk.get("provenance", "ai"),
        ))

    # Evidence + issue links.
    created_issues = {i.title: i for i in case.issues.all()}
    evidence_rows = []
    for ev in defn.get("evidence", []):
        row = EvidenceItem(
            case_id=case.id,
            title=ev["title"],
            description=ev.get("description", ""),
            item_type=ev.get("item_type", "document"),
            source=ev.get("source", ""),
            date=_resolve_date(ev["date"]) if ev.get("date") else None,
            importance=ev.get("importance", "medium"),
            verification=ev.get("verification", "unverified"),
            status=ev.get("status", "copy"),
            provenance=ev.get("provenance", "user"),
        )
        for it in ev.get("issues", []):
            linked = created_issues.get(it)
            if linked:
                row.issues.append(linked)
        db.session.add(row)
        evidence_rows.append(row)

    for scen in defn.get("scenarios", []):
        db.session.add(Scenario(
            case_id=case.id,
            name=scen["name"],
            description=scen.get("description", ""),
            parameters=scen.get("parameters", ""),
            facts_json=json.dumps(scen.get("facts", [])),
            risk_level=scen.get("risk_level", "medium"),
        ))

    prep = defn.get("prep") or {}
    db.session.add(NegotiationPrep(
        case_id=case.id,
        goals=prep.get("goals", ""),
        batna=prep.get("batna", ""),
        interests=prep.get("interests", ""),
        concessions=prep.get("concessions", ""),
        red_lines=prep.get("red_lines", ""),
        counterpart_analysis=prep.get("counterpart_analysis", ""),
        strategy=prep.get("strategy", ""),
        objective=prep.get("objective", ""),
        desired_outcome=prep.get("desired_outcome", ""),
        minimum_acceptable=prep.get("minimum_acceptable", ""),
        key_evidence=prep.get("key_evidence", ""),
        counterpart_position=prep.get("counterpart_position", ""),
        constraints=prep.get("constraints", ""),
        channel=prep.get("channel", ""),
    ))

    for act in defn.get("actions", []):
        db.session.add(ActionItem(
            case_id=case.id,
            title=act["title"],
            description=act.get("description", ""),
            priority=act.get("priority", "medium"),
            reason=act.get("reason", ""),
            related_issue=act.get("related_issue", ""),
            required_evidence=act.get("required_evidence", ""),
            due_date=_resolve_date(act["due"]) if act.get("due") else None,
            status="not_started",
        ))

    for dl in defn.get("deadlines", []):
        db.session.add(Deadline(
            case_id=case.id,
            title=dl["title"],
            description=dl.get("description", ""),
            due_date=_resolve_date(dl["due"]),
            status=dl.get("status", "pending"),
            source=dl.get("source", "user"),
        ))

    db.session.commit()

    # Deterministic risk analysis (same engine the Risk tab uses) so the demo
    # opens with a real assessment already on file.
    try:
        from ai import analyze_case_risks, build_case_context  # noqa: E402
        context = build_case_context(case)
        assessment = analyze_case_risks(context)
        db.session.add(RiskAssessment(
            case_id=case.id,
            overall_score=int(assessment.get("overall_score") or 0),
            overall_level=assessment.get("overall_level") or "medium",
            summary=assessment.get("summary") or "",
            dimensions_json=json.dumps(assessment.get("dimensions") or []),
            previous_json="",
            note=assessment.get("note") or "",
        ))
        db.session.commit()
    except Exception:
        # Assessment is a convenience; the Risk tab can still generate one.
        db.session.rollback()

    # Deterministic negotiation copilot plan (same engine as the Negotiation
    # tab's "Build plan") so each demo opens with a real strategy on file.
    try:
        from ai import analyze_negotiation_prep, build_case_context  # noqa: E402
        prep = NegotiationPrep.query.filter_by(case_id=case.id).first()
        if prep is not None:
            result = analyze_negotiation_prep(build_case_context(case),
                                              prep.to_dict())
            plan_keys = ("opening_position", "key_arguments",
                         "supporting_evidence", "likely_objections",
                         "responses", "potential_concessions", "walk_away",
                         "questions_to_ask")
            prep.plan_json = json.dumps(
                {k: result.get(k) for k in plan_keys if result.get(k)})
            db.session.commit()
    except Exception:
        # The plan is a convenience; the Negotiation tab can still build one.
        db.session.rollback()

    return case
