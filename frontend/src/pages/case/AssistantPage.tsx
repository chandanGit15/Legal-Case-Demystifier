import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../services/api";
import type { ChatMessage, ChatMeta, ChatSource, MessagesResponse } from "../../types";
import { useCase } from "../../context/CaseContext";
import { useLanguage } from "../../context/LanguageContext";
import { useToast } from "../../context/ToastContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { Loading } from "../../components/ui";
import { LANGUAGES } from "../../utils/i18n";

interface QuickAction {
  id: string;
  key: string;
  icon: string;
  hint: string;
  prompt?: string;
  nav?: string;
}

const QUICK_ACTIONS: QuickAction[] = [
  { id: "analyze", key: "qaAnalyze", icon: "bi-stars", hint: "Plain-language read of the situation", prompt: "Analyze the current situation of this case and give me your best plain-language read of where things stand." },
  { id: "explain", key: "qaExplain", icon: "bi-person-lines-fill", hint: "No legal jargon", prompt: "Explain the key parts of my case in simple, everyday language — no legal jargon." },
  { id: "gaps", key: "qaGaps", icon: "bi-question-circle", hint: "What is still unknown", prompt: "What information is still missing in this case and why does each piece matter?" },
  { id: "timeline", key: "qaTimeline", icon: "bi-calendar-plus", hint: "Open the Timeline tab", nav: "timeline" },
  { id: "risk", key: "qaRisk", icon: "bi-shield-exclamation", hint: "Open Risk Analysis", nav: "risks" },
  { id: "negotiate", key: "qaNegotiate", icon: "bi-chat-square-text", hint: "Draft a negotiation message", prompt: "Draft an opening negotiation response I could send, based on the facts in this case." },
  { id: "scenario", key: "qaScenario", icon: "bi-diagram-3", hint: "Open What-If Simulator", nav: "scenarios" },
];

const SOURCE_ICONS: Record<string, string> = {
  case: "bi-briefcase",
  document: "bi-file-earmark-text",
  timeline: "bi-calendar3",
  issue: "bi-exclamation-circle",
  risk: "bi-shield-exclamation",
  evidence: "bi-collection",
};

interface TermResult {
  term?: string;
  simple_meaning?: string;
  technical_meaning?: string;
  why_it_appears?: string;
  example?: string;
  potential_implications?: string;
  related_clauses?: string[];
  related_terms?: string[];
  definition?: string;
  context?: string;
  caveat?: string;
  note?: string;
  mode?: string;
}

interface SimplifyResult {
  original?: string;
  simplified?: string;
  what_was_simplified?: { term?: string; meaning?: string; count?: number }[];
  meaning_preserved?: boolean;
  note?: string;
  mode?: string;
}

export function AssistantPage() {
  const { caseId, caseData, documents, timeline, issues } = useCase();
  const { language, setLanguage, t } = useLanguage();
  const navigate = useNavigate();
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [sessionTitle, setSessionTitle] = useState("CaseGuide conversation");
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  // Legal term explainer
  const [termMode, setTermMode] = useState<"beginner" | "technical">("beginner");
  const [explainer, setExplainer] = useState<TermResult | null>(null);
  const [termInput, setTermInput] = useState("");
  const [termBusy, setTermBusy] = useState(false);

  // Explain Simply
  const [simpleText, setSimpleText] = useState("");
  const [simpleBusy, setSimpleBusy] = useState(false);
  const [simpleResult, setSimpleResult] = useState<SimplifyResult | null>(null);

  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    api.get<MessagesResponse>(`/cases/${caseId}/messages`)
      .then((d) => {
        if (cancelled) return;
        setMessages(d.messages);
        if (d.session && d.session.title) setSessionTitle(d.session.title);
      })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load"); });
    return () => { cancelled = true; };
  }, [caseId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    setBusy(true);
    setError(null);
    const optimistic: ChatMessage = {
      id: Date.now(), case_id: Number(caseId), role: "user", content: msg,
      provenance: {}, meta: {}, language, created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...(prev ?? []), optimistic]);
    try {
      const res = await api.post<{ assistant: ChatMessage; session: { title: string } }>(
        `/cases/${caseId}/chat`, { message: msg, language });
      setMessages((prev) => {
        const withoutPending = (prev ?? []).filter((m) => !(m.id === optimistic.id));
        return [...withoutPending, res.assistant];
      });
      if (res.session && res.session.title) setSessionTitle(res.session.title);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message failed");
      setInput(msg);
      setMessages((prev) => (prev ?? []).filter((m) => !(m.id === optimistic.id)));
    } finally {
      setBusy(false);
    }
  }

  async function runQuickAction(a: QuickAction) {
    if (a.prompt) {
      await send(a.prompt);
      return;
    }
    if (a.nav) {
      toast.info(`${t(a.key)} — ${t("tabDocuments")} → ${a.nav}`);
      navigate(`/cases/${caseId}/${a.nav}`);
    }
  }

  async function explain(e: React.FormEvent) {
    e.preventDefault();
    const term = termInput.trim();
    if (!term || termBusy) return;
    setTermBusy(true);
    setError(null);
    try {
      const res = await api.post<TermResult>("/ai/explain-term",
        { term, language, mode: termMode });
      setExplainer(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Explanation failed");
    } finally {
      setTermBusy(false);
    }
  }

  async function simplify(e: React.FormEvent) {
    e.preventDefault();
    const text = simpleText.trim();
    if (!text || simpleBusy) return;
    setSimpleBusy(true);
    setError(null);
    try {
      const res = await api.post<SimplifyResult>(`/cases/${caseId}/explain-simply`,
        { text, language });
      setSimpleResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Conversion failed");
    } finally {
      setSimpleBusy(false);
    }
  }

  const counts = caseData?.counts;

  return (
    <div>
      <div className="flex-between mb-3" style={{ alignItems: "flex-end", flexWrap: "wrap", gap: 8 }}>
        <div>
          <div className="overline mb-1">{t("assistantEyebrow")}</div>
          <p className="text-soft" style={{ margin: 0, fontSize: 13.5, maxWidth: 680 }}>
            {t("assistantTagline")}
          </p>
        </div>
        <select className="form-select lang-select" style={{ width: 158 }}
                value={language}
                title={t("language")}
                onChange={(e) => setLanguage(e.target.value)}>
          {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.native} · {l.name}</option>)}
        </select>
      </div>

      {/* Case context strip */}
      <div className="card mb-3 cg-context">
        <i className="bi bi-briefcase" />
        <div className="li-main">
          <div className="cg-context-title">
            {caseData?.title || "This case"}
            {caseData?.jurisdiction && <span className="badge badge-neutral">{caseData.jurisdiction}</span>}
            {caseData?.case_type && <span className="badge badge-neutral">{caseData.case_type}</span>}
          </div>
          <div className="text-faint" style={{ fontSize: 12 }}>
            {t("sessionLabel")}: {sessionTitle} · context in scope —
            {counts?.documents ?? documents.length} {t("docs")} ·
            {counts?.timeline_events ?? timeline.length} timeline ·
            {counts?.issues ?? issues.length} {t("issues")}
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="qa-grid mb-3">
        {QUICK_ACTIONS.map((a) => (
          <button key={a.id} className="qa-card" onClick={() => void runQuickAction(a)} disabled={busy}>
            <i className={`bi ${a.icon}`} />
            <div>
              <b>{t(a.key)}</b>
              <span>{a.hint}</span>
            </div>
          </button>
        ))}
      </div>

      {/* Conversation */}
      <div className="card cg-shell">
        <div className="flex-between mb-2">
          <h3 className="card-title"><i className="bi bi-chat-dots" style={{ color: "var(--brand-500)" }} /> {t("convTitle")}</h3>
          {messages && messages.length > 0 && (
            <span className="overline">contextual · {messages.length} {t("msgCount")}</span>
          )}
        </div>

        {error && <div className="alert-box error">{error}</div>}

        {messages === null ? (
          <Loading label="Loading conversation…" />
        ) : messages.length === 0 ? (
          <div className="cg-hero">
            <div className="cg-hero-icon"><i className="bi bi-stars" /></div>
            <h2>{t("heroTitle")}</h2>
            <p>{t("heroBody", { case: caseData?.title || "this case" })}</p>
            <div className="flex" style={{ gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
              {QUICK_ACTIONS.filter((a) => a.prompt).slice(0, 4).map((a) => (
                <button key={a.id} className="btn btn-ghost btn-sm" onClick={() => void send(a.prompt)}>
                  <i className={`bi ${a.icon}`} /> {t(a.key)}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-scroll" style={{ maxHeight: 480, overflowY: "auto", paddingRight: 4 }}>
            {messages.map((m) =>
              m.role === "user" ? <UserBubble key={m.id} msg={m} t={t} />
                : <GuideCard key={m.id} msg={m} onFollowUp={(q) => void send(q)} t={t} />,
            )}
            {busy && <ThinkingRow t={t} />}
            <div ref={endRef} />
          </div>
        )}

        <form onSubmit={(e) => { e.preventDefault(); void send(); }} className="chat-input" style={{ marginTop: 12 }}>
          <input className="form-control" value={input} onChange={(e) => setInput(e.target.value)}
                 placeholder={`${t("askPlaceholder")}${language !== "en" ? ` (${language})` : ""}`}
                 disabled={busy} />
          <button className="btn btn-primary" disabled={busy || !input.trim()}>
            {busy ? <span className="spinner" style={{ borderTopColor: "#fff", borderColor: "rgba(255,255,255,0.4)", width: 15, height: 15 }} /> : t("send")}
          </button>
        </form>
      </div>

      {/* Explain Simply (Phase 12) */}
      <div className="card mb-3">
        <h3 className="card-title"><i className="bi bi-person-lines-fill" style={{ color: "var(--brand-500)" }} /> {t("simpleTitle")}</h3>
        <p className="text-faint" style={{ fontSize: 12.5, marginTop: 0 }}>{t("simpleSub")}</p>
        <form onSubmit={simplify}>
          <textarea className="form-control" rows={4} value={simpleText}
                    onChange={(e) => setSimpleText(e.target.value)}
                    placeholder={t("simplePlaceholder")} disabled={simpleBusy}
                    style={{ resize: "vertical" }} />
          <div className="flex" style={{ gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
            <button className="btn btn-outline" disabled={simpleBusy || !simpleText.trim()}>
              {simpleBusy ? t("simpleWorking") : t("simpleConvert")}
            </button>
          </div>
        </form>
        {simpleResult && (
          <div className="doc-analysis mt-3">
            {simpleResult.note && (
              <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}>
                <i className="bi bi-info-circle" />{simpleResult.note}
              </div>
            )}
            {simpleResult.meaning_preserved === false && (
              <div className="alert-box error mb-2" style={{ fontSize: 12.5 }}>
                <i className="bi bi-exclamation-triangle" /> Meaning not preserved — review before use.
              </div>
            )}
            {simpleResult.meaning_preserved && (
              <span className="badge badge-green mb-2"><i className="bi bi-check-circle" /> {t("simplePreserved")}</span>
            )}
            {simpleResult.original && simpleResult.original !== simpleResult.simplified && (
              <>
                <div className="li-title" style={{ marginTop: 8 }}><i className="bi bi-file-earmark-text" /> {t("simpleOriginal")}</div>
                <p className="text-soft" style={{ margin: "4px 0 10px", fontSize: 13, opacity: 0.85 }}>{simpleResult.original}</p>
              </>
            )}
            {simpleResult.simplified && (
              <>
                <div className="li-title"><i className="bi bi-lightbulb" /> {t("simpleSimplified")}</div>
                <p className="text-soft" style={{ margin: "6px 0", fontSize: 13.5, lineHeight: 1.6 }}>{simpleResult.simplified}</p>
              </>
            )}
            {simpleResult.what_was_simplified && simpleResult.what_was_simplified.length > 0 && (
              <>
                <div className="overline" style={{ margin: "10px 0 6px" }}><i className="bi bi-arrow-repeat" /> {t("simpleWhat")}</div>
                <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
                  {simpleResult.what_was_simplified.map((w, i) => (
                    <span key={i} className="src-chip" title={w.meaning}>
                      <i className="bi bi-quote" /> {w.term}
                      {typeof w.count === "number" && w.count > 1 ? ` ×${w.count}` : ""}
                    </span>
                  ))}
                </div>
                {simpleResult.what_was_simplified[0]?.term === "(none detected)" && (
                  <p className="text-faint" style={{ fontSize: 12.5, margin: "6px 0 0" }}>{t("simpleNone")}</p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Legal term explainer (Phase 12 — Beginner/Technical modes) */}
      <div className="card mb-3">
        <div className="flex-between mb-1" style={{ alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <h3 className="card-title" style={{ margin: 0 }}>
            <i className="bi bi-book" style={{ color: "var(--brand-500)" }} /> {t("termTitle")}
          </h3>
          <div className="seg" role="group" aria-label="explanation mode">
            <button className={termMode === "beginner" ? "on" : ""}
                    onClick={() => { setTermMode("beginner"); setExplainer(null); }}>
              <i className="bi bi-emoji-smile" /> {t("termBeginner")}
            </button>
            <button className={termMode === "technical" ? "on" : ""}
                    onClick={() => { setTermMode("technical"); setExplainer(null); }}>
              <i className="bi bi-braces" /> {t("termTechnical")}
            </button>
          </div>
        </div>
        <p className="text-faint" style={{ fontSize: 12.5, marginTop: 0 }}>{t("termSub")}</p>
        <form onSubmit={explain} className="chat-input">
          <input className="form-control" value={termInput} onChange={(e) => setTermInput(e.target.value)}
                 placeholder={t("termPlaceholder")} disabled={termBusy} />
          <button className="btn btn-outline" disabled={termBusy || !termInput.trim()}>
            {termBusy ? "…" : t("explain")}
          </button>
        </form>
        {explainer && (
          <div className="doc-analysis mt-3">
            {explainer.note && <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}><i className="bi bi-info-circle" />{explainer.note}</div>}
            <div className="li-title">{explainer.term}</div>
            {termMode === "beginner" && (
              <p className="text-soft" style={{ margin: "6px 0" }}>{explainer.simple_meaning || explainer.definition}</p>
            )}
            {termMode === "technical" && (
              <p className="text-soft" style={{ margin: "6px 0" }}>{explainer.technical_meaning}</p>
            )}
            <div className="flex" style={{ gap: 8, flexWrap: "wrap", margin: "4px 0" }}>
              <span className="badge badge-brand" style={{ fontSize: 10 }}>
                {termMode === "beginner" ? t("termSimple") : t("termTech")}
              </span>
              {termMode === "beginner" && explainer.technical_meaning && (
                <span className="badge badge-neutral" style={{ fontSize: 10 }}>{t("termTech")}</span>
              )}
            </div>
            <TermField icon="bi-question-circle" label={t("termWhy")} value={explainer.why_it_appears} />
            <TermField icon="bi-lightbulb" label={t("termExample")} value={explainer.example} />
            <TermField icon="bi-shield-exclamation" label={t("termImplications")} value={explainer.potential_implications} />
            {explainer.related_clauses && explainer.related_clauses.length > 0 && (
              <p className="text-soft" style={{ margin: "4px 0" }}>
                <b>{t("termRelatedClauses")}:</b> {explainer.related_clauses.join(", ")}
              </p>
            )}
            {explainer.related_terms && explainer.related_terms.length > 0 && (
              <p className="text-soft" style={{ margin: "4px 0" }}>
                <b>{t("termRelatedTerms")}:</b> {explainer.related_terms.join(", ")}
              </p>
            )}
            {explainer.context && (
              <p className="text-soft" style={{ margin: "4px 0" }}><b>{t("termContext")}:</b> {explainer.context}</p>
            )}
            {explainer.caveat && <p className="text-faint" style={{ margin: "4px 0 0", fontSize: 12 }}>{explainer.caveat}</p>}
          </div>
        )}
      </div>

      <LegalDisclaimer />
    </div>
  );
}

/* ---- small helpers ------------------------------------------------------- */

function TermField({ icon, label, value }: { icon: string; label: string; value?: string }) {
  if (!value) return null;
  return (
    <p className="text-soft" style={{ margin: "4px 0" }}>
      <b><i className={`bi ${icon}`} style={{ marginRight: 3 }} />{label}:</b> {value}
    </p>
  );
}

/* ---- Bubbles ------------------------------------------------------------- */

type T = (key: string, vars?: Record<string, string | number>) => string;

function UserBubble({ msg, t }: { msg: ChatMessage; t: T }) {
  return (
    <div className="chat-msg user">
      <div className="chat-bubble cg-user-bubble">{msg.content}</div>
      <div className="chat-meta">
        <span className="badge badge-blue">{t("you")}</span>
        <span className="text-faint">{formatTime(msg.created_at)}</span>
      </div>
    </div>
  );
}

function GuideCard({ msg, onFollowUp, t }: { msg: ChatMessage; onFollowUp: (q: string) => void; t: T }) {
  const meta: ChatMeta = msg.meta ?? {};
  const hasStructured = Object.keys(meta).length > 0 && !!meta.answer;
  const text = hasStructured ? meta.answer || "" : msg.content;
  const sources = (meta.sources ?? []).slice(0, 8);
  const labels = meta.labels ?? msg.provenance?.labels ?? [];
  const note = meta.note ?? msg.provenance?.note ?? "";

  return (
    <div className="chat-msg guide">
      <div className="cg-avatar"><i className="bi bi-stars" /></div>
      <div className="cg-bubble">
        <div className="cg-bubble-head">
          <b>CaseGuide</b>
          {(meta.mode ?? msg.provenance?.mode) === "demo"
            ? <span className="badge badge-demo"><i className="bi bi-stars" /> {t("demoReply")}</span>
            : <span className="badge badge-green"><i className="bi bi-check-circle" /> {t("liveAi")}</span>}
          <span className="text-faint" style={{ fontSize: 11, marginLeft: "auto" }}>{formatTime(msg.created_at)}</span>
        </div>

        {note && <div className="disclaimer disclaimer-info mb-1" style={{ fontSize: 11.5 }}><i className="bi bi-info-circle" />{note}</div>}
        {labels.length > 0 && (
          <div className="flex" style={{ gap: 5, flexWrap: "wrap", marginBottom: 8 }}>
            {labels.slice(0, 4).map((l) => <span key={l} className="badge badge-brand" style={{ fontSize: 10 }}>{l}</span>)}
          </div>
        )}

        <p className="cg-answer">{text}</p>

        {hasStructured && (
          <>
            <div className="cg-grid">
              {meta.why_this_matters && (
                <GuideTile icon="bi-lightbulb" title={t("whyMatters")}>{meta.why_this_matters}</GuideTile>
              )}
              {meta.potential_risk && (
                <GuideTile icon="bi-shield-exclamation" title={t("potentialRisk")} tone="red">{meta.potential_risk}</GuideTile>
              )}
              {meta.next_question && (
                <GuideTile icon="bi-question-circle" title={t("nextQuestion")}>{meta.next_question}</GuideTile>
              )}
              {meta.recommended_next_step && (
                <GuideTile icon="bi-list-check" title={t("nextStep")} tone="green">{meta.recommended_next_step}</GuideTile>
              )}
            </div>

            {meta.evidence_needed && meta.evidence_needed.length > 0 && (
              <div className="cg-block">
                <div className="overline" style={{ marginBottom: 4 }}><i className="bi bi-paperclip" /> {t("evidenceNeeded")}</div>
                {meta.evidence_needed.map((e, i) => (
                  <div key={i} className="text-soft" style={{ fontSize: 12.5, display: "flex", gap: 6 }}>
                    <i className="bi bi-dot" />{e}
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {sources.length > 0 && (
          <div className="cg-block">
            <div className="overline" style={{ marginBottom: 4 }}><i className="bi bi-link-45deg" /> {t("sourcesUsed")}</div>
            <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
              {sources.map((s: ChatSource, i: number) => (
                <span key={i} className="src-chip">
                  <i className={`bi ${SOURCE_ICONS[s.type] ?? "bi-file-earmark"}`} /> {s.label}
                </span>
              ))}
            </div>
          </div>
        )}

        {hasStructured && meta.follow_up_suggestions && meta.follow_up_suggestions.length > 0 && (
          <div className="cg-block">
            <div className="overline" style={{ marginBottom: 4 }}>{t("followUp")}</div>
            <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
              {meta.follow_up_suggestions.map((q, i) => (
                <button key={i} className="btn btn-ghost btn-sm" onClick={() => onFollowUp(q)}>
                  {q} <i className="bi bi-arrow-right" style={{ fontSize: 10 }} />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GuideTile({ icon, title, tone, children }: {
  icon: string; title: string; tone?: string; children: React.ReactNode;
}) {
  const color = tone === "red" ? "var(--red)" : tone === "green" ? "var(--green)" : "var(--brand-600)";
  return (
    <div className="cg-tile">
      <div className="cg-tile-title"><i className={`bi ${icon}`} style={{ color }} /> {title}</div>
      <p>{children}</p>
    </div>
  );
}

function ThinkingRow({ t }: { t: T }) {
  return (
    <div className="chat-msg guide">
      <div className="cg-avatar"><i className="bi bi-stars" /></div>
      <div className="cg-bubble cg-thinking">
        <span className="spinner" style={{ width: 14, height: 14 }} /> {t("thinking")}
      </div>
    </div>
  );
}

function formatTime(iso?: string) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
