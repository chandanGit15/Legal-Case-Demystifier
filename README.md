# Legal Case Demystifier

An AI-powered legal decision-support and **case-understanding platform**. Not a chatbot: a
structured case workspace where a situation becomes a case, then documents, facts, a
timeline, legal issues, risks, information gaps, what-if scenarios, negotiation, and a
concrete action plan.

The AI never invents laws, citations, document contents, or guaranteed outcomes. Every
AI output is labeled by **provenance** (user-provided fact / extracted from document /
AI interpretation / information missing / requires verification) and carries a legal
disclaimer.

> **India-only platform update:** the application is now exclusively for the
> Indian legal context. `POST /api/cases` ignores any client-supplied country
> and always stores **India**; the state/region is validated against the 28
> Indian states + 8 union territories (`utils/india.py`, mirrored as the
> frontend `INDIAN_STATES`/`INDIAN_UNION_TERRITORIES` constants) and rejected
> with a 400 if it is not on the list. The New Case / Edit Case / Settings
> forms no longer ask for a country — jurisdiction shows a fixed, read-only
> **India** field and the state/UT is a dropdown (States and Union
> Territories groups). An idempotent startup migration locks every existing
> case to India (country set, jurisdiction rebuilt; legacy demo cases are
> remapped to a sensible Indian state by case type, other stored state values
> are preserved). The demo catalog's five fictional cases now carry Indian
> jurisdictions (Delhi, Karnataka, Maharashtra, Kerala).
>
> The AI context layer is India-aware without touching the AI architecture:
> `_case_context` — the single prompt-context builder shared by every AI
> workflow (chat, document analysis, issues, gaps, risks, scenarios,
> negotiation, action plan, deadlines) — now appends a jurisdictional note
> stating the case is in India, naming the state/UT, recognising Indian legal
> terms and institutions (FIR, bail, anticipatory bail, charge sheet, legal
> notice, affidavit, plaint, written statement, petition, appeal, revision,
> stay order, injunction, limitation, arbitration, mediation, consumer
> complaint, labour dispute, employment contract), and instructing the model
> never to apply Indian laws confidently without the relevant facts, dates and
> jurisdiction.
>
> The **New Case flow now supports file uploads** alongside manual entry (both
> can be combined and neither overrides the other). The modal keeps the manual
> fields (title, category, fixed India jurisdiction, Indian state/UT dropdown,
> facts) and adds a drag-and-drop / browse dropzone for **PDF · DOCX · TXT ·
> JPG · PNG**, multi-file selection with per-file remove, and a live progress
> panel (Creating the case → Uploading → Extracting information → Analyzing
> document → Adding to case). Creating a case uploads each file through the
> existing `POST /cases/<id>/documents` + `.../analyze` pipeline (same
> validation, extraction, chunking and analysis the Documents tab uses — no
> second document system), then opens the Case Workspace where every file
> appears under Documents with its analysis. With no title entered, one is
> derived from the first uploaded file so a purely file-based case works. The
> modal also resets itself between opens (previously it kept stale state).
>
> **Header alignment fixed:** top-nav labels can no longer wrap ("My Cases",
> "AI Assistant", "Action Plan" stay on one line at every width). Nav links are
> `white-space: nowrap` with zero shrink, the brand and the right-side actions
> never compress, and the nav scrolls horizontally (scrollbar revealed on
> hover) whenever the full 9-item navigation outgrows the row — plus tighter
> gap/padding steps at 1280px and 1100px. Below 900px the header wraps to rows
> (brand + actions, then the scrollable nav) with the actions right-aligned;
> verified at mobile width: zero horizontal overflow, every label a single
> line.
>
> **Production hardening:** security and robustness pass over the whole stack
> (no feature changes).
>
> Backend: restricted **CORS** to a configurable origin allowlist
> (`CORS_ORIGINS`), security headers on every response (no-store,
> nosniff, frame/referrer/policy), **JSON-only structured error responses** for
> every HTTP failure (404/405/413/429/500 — never HTML or stack traces), a
> final 500 safety net, a loud startup warning when `JWT_SECRET` is the dev
> default, **email validation** and length caps on registration/profile,
> language allow-list on settings, a generic "analysis failed" message that no
> longer leaks internal exceptions (full detail stays in server logs), and
> lightweight **rate limiting** (`utils/ratelimit.py`, per IP + route, 429 with
> Retry-After) on register/login and the demo endpoints. Ownership was audited
> endpoint-by-endpoint and verified live: a second account receives 404 for
> every read/write on another user's cases, documents, sessions and
> negotiation records.
>
> Frontend: the API client now has **timeouts** (90s, 240s for uploads),
> friendly non-technical fallback messages per status, and a 401 anywhere
> clears the session and signs out (no dead sessions); a new public **Privacy
> page** (`/privacy`, linked from the landing and app footers) explains
> document processing, data handling, case deletion and user control; the
> disclaimer copy now carries the required sentence ("provides informational
> and decision-support assistance and is not a substitute for advice from a
> qualified legal professional") on AI surfaces, case pages, the landing page
> and the new app footer; a **missing-jurisdiction banner** appears in every
> case workspace that has no country/state. Also fixed a real crash: the
> landing page returned before its hooks (conditional `useEffect`) and blew up
> whenever auth state changed while mounted — verified before/after.
>
> Phase 13 recap: a real-data dashboard, case analytics, and five fully
> populated fictional demo cases.
>
> Phase 13 turns the dashboard into a true portfolio view fed entirely by real
> case data: the four KPIs (Active cases, Documents analyzed, Pending actions,
> Upcoming deadlines), **Recent cases**, **Action required** (deadlines +
> high-priority actions per case), **Upcoming deadlines**, **Recent AI
> insights**, and a new **Case analytics** section — issues detected per case,
> high-risk areas (top dimension per case + hotspot), **evidence coverage**
> (verified/unverified per case with an open-issues-with-evidence ratio),
> **information gaps** (open by priority), **scenario comparison** (cases with
> 2+ scenarios for the comparison table), and **negotiation readiness** (cases
> with a brief and a generated plan). Every figure is computed server-side from
> the case records — no vanity or placeholder metrics.
>
> The dashboard, landing page, and top bar now offer **Explore Demo Case**: a
> picker over **five fully populated fictional cases** (rental deposit,
> wrongful termination, consumer warranty, contract milestone, boundary fence)
> with coherent invented summaries, documents, timelines, issues, evidence,
> risk assessments (auto-run by the same Phase-7 engine), scenarios, action
> plans and negotiation strategies. Logged-out visitors get a one-click session
> on a shared fictional account; `POST /api/demo-case` adds a demo under a real
> account. This surfaced and fixed a real delete bug: `negotiation_prep`,
> `chat_sessions` and `negotiation_sessions` rows were orphaned when a case was
> deleted (they now cascade in `delete_case`).
>
> Phase 12 added the multilingual system (recap below).
>
> Phase 12 built a **global language system** (English · Hindi · Kannada · Tamil ·
> Telugu · Malayalam · Marathi · Bengali). A language switcher lives in the top
> bar and the AI Assistant; the choice is persisted to the account settings and
> localStorage, and the workspace chrome (top nav, case tabs, case header,
> shared buttons) translates through a single `t()` helper in `LanguageContext`
> (`utils/i18n.ts`). AI responses respect the selected language: `POST
> /cases/<id>/chat` and `POST /ai/explain-term` already threaded `language`
> through to Gemini, and demo mode now serves **translated canned responses** in
> all seven languages so replies stay localized even without a key.
>
> New Phase-12 AI surfaces:
> - **Explain Simply** — `POST /cases/<id>/explain-simply` rewrites pasted legal
>   wording into plain language while preserving the legal meaning exactly
>   (never adds or removes obligations). Demo mode glosses jargon terms inline
>   via a deterministic glossary; the response flags when the meaning was
>   preserved.
> - **Legal Term Explainer** — `/ai/explain-term` now returns the full structure
>   (simple meaning, technical meaning, why it appears, example, potential
>   implications, related clauses/terms) in **Beginner or Technical mode**, in
>   the selected language, without unsupported legal claims (old keys kept for
>   compatibility).
>
> Phase 11 built the action plan and deadline tracker (recap below).
>
> Phase 11 turned the final product pillar into a real working module: a
> **grounded action plan** (`POST/GET /cases/<id>/action-plan`, `PUT
> /api/action-items/<id>`) where every action carries a title, description,
> priority, **reason (why this matters)**, related issue, required evidence,
> deadline, and status (Not started / In progress / Completed / Skipped).
> `POST /cases/<id>/action-plan/generate` produces actions traced to the actual
> case record — open issues, unverified evidence, open information gaps
> (with where-to-find guidance), high risks, analyzed scenarios, tracked
> deadlines, and negotiation prep — deduplicated by title so re-running never
> duplicates. A **deadline tracker** (`/deadlines`, `POST
> /cases/<id>/deadlines/extract`) buckets dates into Upcoming / Due soon (≤ 7
> days) / Overdue with pending/completed/missed statuses, and explicitly warns
> that extracted dates are **not legally binding deadlines** unless verified
> against jurisdiction-specific rules. The dashboard now surfaces **Pending
> actions**, **Upcoming deadlines**, and **Action required** (high-priority
> actions + high-confidence issues) from this real data.
>
> Phase 10 added the interactive negotiation simulation (recap below).
>
> Phase 9 built the Negotiation Copilot preparation workspace: objective inputs,
> generated plan, and message generator (see the full recap below).
>
> Phase 7 replaces the old risk list with an **explainable risk engine**: seven
> dimensions (Legal, Evidence, Deadline, Financial, Negotiation, Procedural,
> Information Gap) are scored deterministically from the structured case record
> (issue confidence, evidence verification, deadlines, open gaps, negotiation prep,
> stage) — the AI layer only writes the explanation, so scores are never a meaningless
> LLM guess and never legal probabilities. `POST/GET /cases/<id>/risk-analysis`
> returns overall score + level, per-dimension score/level/reason/supporting &
> mitigating factors/recommended action, and a **previous vs current diff** (what
> changed when new evidence, documents or facts arrive). The Risk Analysis tab shows
> `POST /cases/<id>/negotiation/simulation/evaluate` produces a **Negotiation
> Performance** review: seven 1-10 dimension scores (Argument strength, Evidence
> usage, Clarity, Tone, Persuasiveness, Risk awareness, Missed opportunities)
> plus structured feedback — what you did well, what could improve, evidence you
> should have used, arguments you missed, potential risks, and suggested
> alternative responses — grounded in the actual transcript and case record
> (evidence actually cited, issues and risks on file). Sessions live in the
> `negotiation_sessions` table (one per case, scoped to user + case), with
> start / reply / evaluate / reset endpoints.
>
> Phase 9 built the Negotiation Copilot preparation workspace: objective inputs,
> generated plan, and message generator (see the full recap below).
>
> Phase 7 replaces the old risk list with an **explainable risk engine**: seven
> dimensions (Legal, Evidence, Deadline, Financial, Negotiation, Procedural,
> Information Gap) are scored deterministically from the structured case record
> (issue confidence, evidence verification, deadlines, open gaps, negotiation prep,
> stage) — the AI layer only writes the explanation, so scores are never a meaningless
> LLM guess and never legal probabilities. `POST/GET /cases/<id>/risk-analysis`
> returns overall score + level, per-dimension score/level/reason/supporting &
> mitigating factors/recommended action, and a **previous vs current diff** (what
> changed when new evidence, documents or facts arrive). The Risk Analysis tab shows
> an overall gauge, a seven-axis SVG **risk radar**, dimension cards and a "What
> changed" list.
>
> Phase 8 is the **What-If Simulator**: every scenario carries an editable **fact
> list** (change/add/remove facts), and "Scenario-Based AI Analysis" compares the
> scenario against the current case across potential issues, risk changes, evidence
> requirements, negotiation leverage, next steps and unknown information — explicitly
> exploratory, never a guaranteed prediction. A professional **comparison table**
> (columns: Current Scenario + up to three alternatives; rows: Risk, Evidence,
> Issues, Advantages, Disadvantages, Information gaps, Negotiation position, Next
> steps) is produced by `POST /cases/<id>/scenarios/compare`, plus spec routes
> `POST/GET /cases/<id>/scenarios`, `PUT/DELETE /api/scenarios/<id>`.
>
> Phase 9 is the **Negotiation Copilot** — a preparation workspace, not a chatbot.
> It collects your objective, desired outcome, minimum acceptable outcome, key
> evidence, the other party's likely position, constraints and channel
> (`POST/GET /cases/<id>/negotiation`) and generates a full plan: strategy, opening
> position, key arguments paired with supporting evidence, likely objections with
> responses, potential concessions, walk-away considerations and questions to ask.
> The **message generator** (`POST /cases/<id>/negotiation/message`) drafts Email,
> Formal letter, WhatsApp-style message or Meeting talking points in Professional /
> Firm / Collaborative / Neutral tones — never deceptive claims, never threats — and
> the practice simulator is preserved.
>
> Phase 6 upgraded the Timeline into a professional chronological view where every
> event carries a type (Incident / Communication / Document / Deadline / Payment /
> Legal action / Other), an importance level, and an explicit date-confidence label
> (Confirmed / Extracted / Potential). AI extraction
> (`POST /cases/<id>/timeline/extract`) surfaces dated events from the case
> description, document analyses and conversation — nothing is stored until the user
> reviews each candidate, and dates are never silently assumed (undated mentions are
> reported as missing, conflicts are flagged). The Evidence tab becomes a visual
> board: each item shows type, date, importance, verification status
> (Unverified / Verified / Disputed), authenticity (original / copy), and can be
> linked to one or more Legal Issues via an evidence↔issue join table. Spec routes
> GET/POST `/cases/<id>/timeline` &amp; `/evidence` plus top-level
> PUT/DELETE `/api/timeline/<id>` and `/api/evidence/<id>` are all implemented.
>
> Phase 1 delivered the production foundation (landing page, auth, case management,
> workspace shell with the 10 fixed sections, dashboard from real data, design system).
> Phase 2 added the shared **Case Data Context** (one aggregate `/cases/<id>/context`
> payload every module reads and keeps in sync), the six-state case status model with
> idempotent migrations, parties, and the structured Overview with an **AI Case Brief**.
> Phase 3 turned Documents into an intelligence pipeline (validated uploads, text
> extraction + chunking, rich structured analysis, findings detail view, connect-
> findings-to-case actions). Phase 4 added the **CaseGuide** assistant — case-
> contextual, per-case session memory, structured responses, sources, quick actions
> and a term explainer. Phase 5 adds **Legal Issue Detection** (`POST /issues/detect`,
> idempotent) that analyzes facts, documents and timeline to surface potential issues
> with confidence, supporting evidence, related documents, missing information and
> impact — confidence is explicitly presented as an assessment of the available
> information, never legal certainty — and the **Information Gap Analyzer**
> (`POST /gaps/detect` = `POST /information-gaps`) that lists what is missing, why it
> matters, which issue it affects and how to find it. The Legal Issues tab now hosts
> rich per-issue cards plus a **"What's Missing?"** section grouped by high / medium /
> low priority where every gap can be marked Open / Found / Not applicable.

## Tech stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Frontend   | React 18 + TypeScript + Vite, Bootstrap 5 + custom design system |
| Backend    | Python + Flask (thin routes over a services layer) |
| AI         | Google Gemini (REST) via a centralized AI package  |
| Database   | SQLite (SQLAlchemy — PostgreSQL-ready)             |
| Auth       | JWT, hashed passwords (werkzeug)                   |
| Documents  | PDF (pypdf), DOCX (python-docx), TXT, images       |

## Quick start

### Backend (port 5000)

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows
# .venv/bin/pip install -r requirements.txt       # macOS / Linux
.venv/Scripts/python run.py init-db               # create tables (idempotent)
.venv/Scripts/python run.py                       # start server
```

Config comes from environment variables (or a local `backend/.env` — copy
`backend/.env.example`). The database and uploads folder are created automatically.

### Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev                                       # http://localhost:5173
```

In development Vite proxies `/api` to the Flask backend, so no CORS setup is needed.
`frontend/.env.example` documents `VITE_API_BASE_URL` for non-proxied setups.

### Landing page & demo

Open `http://localhost:5173` — the premium landing page greets visitors
(*"Understand Your Case. Explore Your Options. Decide What Comes Next."*).
Register, then either describe your own situation or load the one-click **demo case**
(fully populated across every module).

### Live AI (optional)

Without a `GEMINI_API_KEY` the app runs in demo mode: AI features return deterministic,
clearly-labeled sample analysis so the product is fully usable offline.

```bash
export GEMINI_API_KEY="your-key"                  # backend environment only
```

Keys are never exposed to the frontend — the browser only sees a `configured` status flag.

## Environment variables

Backend (`backend/.env`): `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATABASE_URL` (SQLite by
default, PostgreSQL later), `JWT_SECRET`, `JWT_EXPIRES_HOURS`, `MAX_UPLOAD_MB`, `PORT`.

Frontend (`frontend/.env.local`): `VITE_API_BASE_URL` (empty = Vite proxy).

## Architecture

```
React Frontend ──REST──▶ Flask Routes (thin) ──▶ Services ──▶ AI service layer ──▶ Gemini API
                                                        │
                                                        ▼
                                    SQLAlchemy models ──▶ SQLite (PostgreSQL-ready)

Document Upload ──▶ Text Extraction ──▶ AI Analysis ──▶ Structured Case Data
```

Business logic lives in services (`backend/services/`); Flask route handlers stay thin.
All AI features go through the centralized `backend/ai/` package.

## Project structure

```
backend/
  run.py                  entry point (also: python run.py init-db)
  config/                 environment-driven configuration
  app/                    Flask application factory
  models/                 SQLAlchemy models (all tables)
  schemas/                request/response validation
  services/               business logic: auth, case, document
  ai/                     ★ centralized Gemini service layer
  document_processing/    PDF / DOCX / TXT extraction
  routes/                 thin REST handlers
  utils/                  JWT guard, HTTP helpers

frontend/
  src/
    services/api.ts       ★ centralized API client (JWT, env base URL, errors)
    context/              AuthContext, ToastContext, CaseContext (shared case data)
    hooks/useFetch.ts     loading/error/refetch hook
    layouts/              AppLayout (top nav + global nav), CaseLayout (provider + header)
    components/           UI kit: cards, badges, modals, states, disclaimers, edit-case modal
    pages/                Landing, auth, Dashboard, Cases, Settings, case sections
    utils/                constants (case categories, languages), formatting
    styles/theme.css      premium legal-tech design system
```

## REST API (all under `/api`)

```
Auth         POST /auth/register  POST /auth/login  GET /auth/me
Dashboard    GET  /dashboard/summary
Cases        GET/POST /cases  GET/PATCH/DELETE /cases/<id>  POST /demo-case
Documents    GET/POST /cases/<id>/documents  GET/DELETE .../<doc_id>  GET .../<doc_id>/content
             POST .../<doc_id>/analyze  POST .../<doc_id>/import   (findings → case)
             document-id aliases: GET/DELETE /api/documents/<id>  POST /api/documents/<id>/analyze
Workspace    /cases/<id>/overview/analyze · timeline (+/extract) · issues (+/detect) ·
             risks (+/assess) · risk-analysis (GET/POST, Phase 7) ·
             gaps (+/detect, alias POST /information-gaps) ·
             scenarios (GET/POST/PUT/<id>/analyze, /compare) ·
             negotiation (GET/POST/PUT, /analyze, /message, /practice, ·
             /simulation GET + start/reply/evaluate/reset, Phase 10) ·
             evidence · actions (+/generate, Phase 11) · deadlines (+/extract,
             Phase 11) · explain-simply (Phase 12) · messages · chat (CaseGuide)
Direct       PUT/DELETE /api/timeline/<id>   PUT/DELETE /api/evidence/<id>   PUT/DELETE /api/scenarios/<id>
             PUT/PATCH /api/action-items/<id> (Phase 11)
AI           POST /ai/explain-term (mode beginner|technical, Phase 12)  POST /ai/explain-case
Settings     GET/PUT /settings  GET /settings/ai-status
```

## Database foundation

Tables exist for the full roadmap: `users`, `cases`, `case_documents`,
`document_chunks` (RAG-ready), `timeline_events`, `legal_issues`, `risk_factors`,
`risk_assessments` (Phase-7 explainable engine output with change history),
`info_gaps`, `scenarios` (with editable `facts_json`), `negotiation_prep` (Phase-9
objective inputs + generated plan), `negotiation_sessions` (Phase-10 simulation
with transcript + evaluation), `evidence_items`, `action_items`,
`deadlines`, `chat_messages`, `notifications`. Phase 11 extends `action_items`
with reason / related-issue / required-evidence / deadline fields and a
Not started-In progress-Completed-Skipped status model.

Cases now use the six-state Phase-2 status model (`draft`, `analysis_in_progress`,
`analysis_complete`, `action_required`, `resolved`, `archived`) and carry a `parties`
field. Phase-5 detection adds rich issue fields (supporting evidence, related
documents, missing information, impact) and gap fields (affected issue, how to find
it, Open/Found/Not applicable status) via additive migrations. Additive migrations
run automatically on boot (`backend/utils/db.py`) and remap legacy Phase-1 statuses,
so existing databases upgrade in place.

Each case exposes a single aggregate context endpoint —
`GET /api/cases/<id>/context` — returning the case plus documents, timeline, issues,
risks, gaps, scenarios, evidence, actions, deadlines, and negotiation prep. The
frontend loads it once into `CaseProvider` (frontend `context/CaseContext.tsx`); every
workspace page consumes that context and calls `refresh()` after mutations, so no
module keeps a private copy of case state and all AI outputs attach to the same case id.

## Roadmap

1. ✅ **Phase 1 — Foundation**: landing page, auth, case CRUD, workspace shell, dashboard, design system
2. ✅ **Phase 2 — Case workspace foundation**: shared Case Data Context, AI Case Brief,
   six-state status model + migrations, parties, polished case header, Overview hub
3. ✅ **Phase 3 — Document intelligence**: validated uploads → extraction → chunking
   (DocumentChunk) → AI analysis (type, parties, clauses, obligations, deadlines,
   entities, issues) → findings detail view → connect findings to the case
4. ✅ **Phase 4 — CaseGuide AI**: centralized Gemini service, POST /cases/<id>/chat with
   case context + history, structured responses (answer · why · evidence · risk · next
   question · next step), sources &amp; follow-ups, quick actions, multilingual + legal-term
   explainer, per-case session memory
5. ✅ **Phase 5 — Issue detection &amp; gap analyzer**: rich issue cards (confidence,
   evidence, related documents, missing info, impact) + idempotent detection, and a
   "What's Missing?" analyzer grouped by priority with Open / Found / Not applicable
   statuses and issue linking
6. ✅ **Phase 6 — Timeline builder &amp; evidence organizer**: typed chronological
   timeline with importance + date-confidence labels, explicit AI extraction review
   (no silent date assumptions), and a visual evidence board with verification
   statuses and issue linking
7. ✅ **Phase 7 — Explainable risk analysis**: deterministic seven-dimension risk
   engine (data-grounded scores, never LLM guesses or legal probabilities), overall
   gauge + SVG risk radar + dimension cards, previous-vs-current "what changed" diff
8. ✅ **Phase 8 — What-if simulator**: editable scenario facts (change/add/remove),
   Scenario-Based AI Analysis (issues, risk changes, evidence, leverage, steps,
   unknowns), professional comparison table (Current + A/B/C) and spec routes
   PUT/DELETE /api/scenarios/<id>
9. ✅ **Phase 9 — Negotiation copilot**: objective/position/evidence inputs, full
   generated plan (strategy, opening, arguments+evidence, objections+responses,
   concessions, walk-away, questions), message generator (email/letter/WhatsApp/
   meeting × professional/firm/collaborative/neutral, no deceptive claims)
10. ✅ **Phase 10 — Interactive negotiation simulation**: the AI plays the opposing
    party from an explicit opponent position; end the session to get a scored
    **Negotiation Performance** review (7 dimensions × 1-10) with grounded
    feedback (strengths, improvements, evidence to use, missed arguments, risks,
    alternative responses) — a separate workflow from the CaseGuide chatbot
11. ✅ **Phase 11 — Action plan & deadline tracker**: status-grouped action plan
    (Not started / In progress / Completed / Skipped) with reason, related issue,
    required evidence and deadline per action; `generate` builds actions grounded
    in the case record (issues, evidence, gaps, risks, scenarios, deadlines,
    negotiation) idempotently; deadline tracker buckets Upcoming / Due soon /
    Overdue with the explicit "not a legal deadline without jurisdiction-
    specific verification" warning; dashboard connects Pending actions, Upcoming
    deadlines and Action required
12. ✅ **Phase 12 — Multilingual + simple language**: global language switching
    (EN/HI/KN/TA/TE/ML/MR/BN) with translated workspace chrome and
    language-aware AI replies (demo replies translated too); **Explain Simply**
    (`POST /cases/<id>/explain-simply`) rewrites legal wording into plain
    language preserving the legal meaning; upgraded **legal term explainer**
    (simple/technical meaning, why it appears, example, implications, related
    clauses) with Beginner/Technical modes
13. ✅ **Phase 13 — Real-data dashboard & demos**: dashboard KPIs, Recent cases,
    Action required, Upcoming deadlines and Recent AI insights plus a **Case
    analytics** section (issues detected, high-risk areas, evidence coverage,
    information gaps, scenario comparison, negotiation readiness) — all
    computed from real records with meaningful visualizations, no vanity
    metrics; five **fully populated fictional demo cases** (rental, employment,
    consumer, contract, property) explorable one-click from the landing page
    (case-delete cascade fix for one-per-case tables)
14. ✅ **Production hardening**: CORS allow-list + security headers, JSON-only
    structured errors everywhere (no stack traces leaked; generic 500 net),
    email/length/language validation, rate limiting on auth + demo endpoints,
    per-request timeouts + friendly error copy + auto sign-out on 401 in the
    API client, Privacy page, required disclaimer sentence on all surfaces,
    missing-jurisdiction banner, verified cross-user isolation end-to-end,
    and a landing-page hooks crash fix
15. ✅ **UI/UX refinement pass**: consistent focus-visible rings, skip-to-content
    link, reduced-motion support, modal dialog semantics (aria + Escape +
    focus restore + scroll lock), icon-only control labels/tooltips, stronger
    overline contrast, custom select styling, card/list/table micro-interactions,
    and a responsive pass (two-row top bar with scrollable nav on small screens,
    tightened case-header/workspace spacing and single-column grids on phones)
    — verified at ~440px without horizontal overflow
16. 🔜 Analytics, notifications, collaboration, export, PostgreSQL migration

## Disclaimer

Legal Case Demystifier provides informational analysis only and does not constitute
legal advice. AI-generated content may contain errors and must be verified by a
qualified legal professional before any action is taken.