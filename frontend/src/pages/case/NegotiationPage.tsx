import { useEffect, useRef, useState } from "react";
import { api } from "../../services/api";
import type {
  NegotiationMessage,
  NegotiationPrep,
  NegotiationSession,
  SimulationMessage,
} from "../../types";
import { useCase } from "../../context/CaseContext";
import { useToast } from "../../context/ToastContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { ErrorState, Loading } from "../../components/ui";

const CHANNELS: [string, string][] = [
  ["email", "Email"],
  ["letter", "Formal letter"],
  ["whatsapp", "WhatsApp-style message"],
  ["meeting", "Meeting talking points"],
];

const TONES: [string, string][] = [
  ["professional", "Professional"],
  ["firm", "Firm"],
  ["collaborative", "Collaborative"],
  ["neutral", "Neutral"],
];

const OBJECTIVE_FIELDS: { key: "objective" | "desired_outcome" | "minimum_acceptable" | "constraints"; label: string; placeholder: string; rows: number }[] = [
  { key: "objective", label: "Objective", placeholder: "What are you trying to achieve overall?", rows: 2 },
  { key: "desired_outcome", label: "Desired outcome", placeholder: "The best realistic result you want", rows: 2 },
  { key: "minimum_acceptable", label: "Minimum acceptable outcome", placeholder: "The least you will accept — your floor", rows: 2 },
  { key: "constraints", label: "Constraints", placeholder: "Time, money, deadlines, anything fixed", rows: 2 },
];

const EVAL_DIMS: [string, string][] = [
  ["argument_strength", "Argument strength"],
  ["evidence_usage", "Evidence usage"],
  ["clarity", "Clarity"],
  ["tone", "Tone"],
  ["persuasiveness", "Persuasiveness"],
  ["risk_awareness", "Risk awareness"],
  ["missed_opportunities", "Missed opportunities"],
];

const LANGUAGES = [
  ["en", "English"], ["es", "Español"], ["fr", "Français"], ["de", "Deutsch"],
  ["hi", "हिन्दी"], ["zh", "中文"], ["ar", "العربية"], ["pt", "Português"],
];

export function NegotiationPage() {
  const { caseId, prep, loading, error: contextError, refresh, setPrep } = useCase();
  const toast = useToast();

  const [draft, setDraft] = useState<NegotiationPrep | null>(null);
  const [saving, setSaving] = useState(false);
  const [drafting, setDrafting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Message generator.
  const [msgChannel, setMsgChannel] = useState("email");
  const [msgTone, setMsgTone] = useState("professional");
  const [msgFocus, setMsgFocus] = useState("");
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState<NegotiationMessage | null>(null);

  // Phase-10 negotiation simulation (separate workflow).
  const [session, setSession] = useState<NegotiationSession | null>(null);
  const [simStarted, setSimStarted] = useState(false);
  const [simLoading, setSimLoading] = useState(true);
  const [simStarting, setSimStarting] = useState(false);
  const [simSending, setSimSending] = useState(false);
  const [simEvaluating, setSimEvaluating] = useState(false);
  const [simInput, setSimInput] = useState("");
  const [simLang, setSimLang] = useState("en");
  const simEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prep) setDraft(prep);
  }, [prep]);

  useEffect(() => {
    let cancelled = false;
    api.get<{ session: NegotiationSession | null }>(`/cases/${caseId}/negotiation/simulation`)
      .then((res) => { if (!cancelled) setSession(res.session); })
      .catch(() => { if (!cancelled) setFormError("Could not load the simulation"); })
      .finally(() => { if (!cancelled) setSimLoading(false); });
    return () => { cancelled = true; };
  }, [caseId]);

  useEffect(() => {
    simEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!draft) return;
    setSaving(true); setFormError(null);
    try {
      const d = await api.put<{ prep: NegotiationPrep }>(`/cases/${caseId}/negotiation`, draft);
      setPrep(d.prep);
      setDraft(d.prep);
      toast.success("Negotiation objective saved.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not save");
    } finally { setSaving(false); }
  }

  async function buildPlan() {
    setDrafting(true); setFormError(null);
    try {
      const d = await api.post<{ prep: NegotiationPrep }>(`/cases/${caseId}/negotiation/analyze`);
      setPrep(d.prep);
      setDraft(d.prep);
      toast.success("Negotiation plan generated.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not draft the plan");
    } finally { setDrafting(false); }
  }

  async function generateMessage() {
    setGenerating(true); setFormError(null);
    try {
      const res = await api.post<NegotiationMessage>(`/cases/${caseId}/negotiation/message`, {
        channel: msgChannel, tone: msgTone, focus: msgFocus,
      });
      setMessage(res);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not generate the message");
    } finally { setGenerating(false); }
  }

  async function copyMessage() {
    if (!message?.message) return;
    try {
      await navigator.clipboard.writeText(message.message);
      toast.success("Message copied to clipboard.");
    } catch {
      toast.error("Could not copy — select the text manually.");
    }
  }

  async function startSimulation() {
    setSimStarting(true); setFormError(null);
    try {
      const res = await api.post<{ session: NegotiationSession }>(`/cases/${caseId}/negotiation/simulation/start`, {
        language: simLang,
      });
      setSession(res.session);
      setSimStarted(true);
      toast.success("Simulation started — the opponent is ready.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not start the simulation");
    } finally { setSimStarting(false); }
  }

  async function sendSim(e: React.FormEvent) {
    e.preventDefault();
    const msg = simInput.trim();
    if (!msg || simSending || !session) return;
    setSimSending(true); setFormError(null);
    try {
      const res = await api.post<{ session: NegotiationSession }>(`/cases/${caseId}/negotiation/simulation/reply`, {
        message: msg, language: simLang,
      });
      setSession(res.session);
      setSimInput("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Reply failed");
    } finally { setSimSending(false); }
  }

  async function evaluateSim() {
    if (!session) return;
    setSimEvaluating(true); setFormError(null);
    try {
      const res = await api.post<{ session: NegotiationSession }>(`/cases/${caseId}/negotiation/simulation/evaluate`);
      setSession(res.session);
      toast.success("Negotiation performance evaluated.");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Evaluation failed");
    } finally { setSimEvaluating(false); }
  }

  async function resetSim() {
    if (!window.confirm("Start a fresh practice session? The current transcript will be cleared.")) return;
    setFormError(null);
    try {
      const res = await api.post<{ session: NegotiationSession }>(`/cases/${caseId}/negotiation/simulation/reset`);
      setSession(res.session);
      setSimStarted(false);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not reset");
    }
  }

  const visibleError = formError || contextError;
  if (visibleError && !draft && !loading) {
    return <div className="page"><ErrorState message={visibleError} onRetry={() => void refresh()} /></div>;
  }
  if (loading && !draft) return <Loading label="Loading negotiation workspace…" />;
  if (!draft) return null;

  const plan = draft.plan ?? {};
  const hasPlan = Object.keys(plan).length > 0;
  const update = (key: keyof NegotiationPrep, value: string) => setDraft({ ...draft, [key]: value });

  const userTurns = (session?.messages ?? []).filter((m) => m.role === "user").length;
  const evaluation = session?.evaluation ?? null;
  const sessionMessages: SimulationMessage[] = session?.messages ?? [];

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Negotiation copilot</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5 }}>
          Define your objective, build a strategy, rehearse the likely counterarguments,
          draft a message, and practice live against a simulated opposing party.
        </p>
      </div>

      {visibleError && <div className="alert-box error mb-3">{visibleError}</div>}

      <div className="card mb-3">
        <div className="flex-between mb-2">
          <h3 className="card-title">Negotiation objective</h3>
          <button className="btn btn-outline btn-sm" onClick={buildPlan} disabled={drafting}>
            <i className="bi bi-stars" /> {drafting ? "Building…" : hasPlan ? "Rebuild plan" : "Build plan with AI"}
          </button>
        </div>
        <form onSubmit={save}>
          <div className="form-row cols-2">
            {OBJECTIVE_FIELDS.map((f) => (
              <div key={f.key}>
                <label className="form-label">{f.label}</label>
                <textarea className="form-control" rows={f.rows} value={String(draft[f.key] ?? "")}
                          placeholder={f.placeholder}
                          onChange={(e) => update(f.key, e.target.value)} />
              </div>
            ))}
            <div>
              <label className="form-label">Preferred communication channel</label>
              <select className="form-select" value={draft.channel || "email"}
                      onChange={(e) => update("channel", e.target.value)}>
                {CHANNELS.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex mt-2" style={{ gap: 8 }}>
            <button className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : <><i className="bi bi-save" /> Save objective</>}
            </button>
            {hasPlan && <span className="badge badge-green"><i className="bi bi-check-circle" /> Plan generated</span>}
          </div>
        </form>
      </div>

      <div className="card mb-3">
        <h3 className="card-title">Your position &amp; the other side</h3>
        <div className="form-row cols-2">
          <div>
            <label className="form-label">Other party's likely position</label>
            <textarea className="form-control" rows={3} value={String(draft.counterpart_position ?? "")}
                      placeholder="What they will probably claim or want"
                      onChange={(e) => update("counterpart_position", e.target.value)} />
          </div>
          <div>
            <label className="form-label">Key evidence</label>
            <textarea className="form-control" rows={3} value={String(draft.key_evidence ?? "")}
                      placeholder="The documents and records that back your position"
                      onChange={(e) => update("key_evidence", e.target.value)} />
          </div>
        </div>
        <div className="text-faint" style={{ fontSize: 12 }}>
          <i className="bi bi-info-circle" /> These feed the plan and the practice opponent.
          Save the objective card above, then rebuild the plan.
        </div>
      </div>

      {!hasPlan && (
        <div className="card mb-3">
          <div className="state">
            <i className="bi bi-briefcase" />
            <h3>No negotiation plan yet</h3>
            <p>Fill in your objective and position, then build the plan to get an opening position,
              key arguments, objections with responses, and walk-away guidance.</p>
            <button className="btn btn-primary" onClick={buildPlan} disabled={drafting}>
              <i className="bi bi-stars" /> {drafting ? "Building…" : "Build plan with AI"}
            </button>
          </div>
        </div>
      )}

      {hasPlan && (
        <>
          <div className="card mb-3">
            <div className="overline mb-2">Strategy</div>
            <div className="neg-block">
              <div className="dim-head"><i className="bi bi-flag" /> Opening position</div>
              <p className="neg-quote">{plan.opening_position}</p>
            </div>
            {draft.strategy && (
              <div className="neg-block">
                <div className="dim-head"><i className="bi bi-compass" /> Strategy</div>
                <p className="text-soft" style={{ margin: 0 }}>{draft.strategy}</p>
              </div>
            )}
            {plan.walk_away && (
              <div className="neg-block">
                <div className="dim-head"><i className="bi bi-door-closed" style={{ color: "var(--red)" }} /> Walk-away considerations</div>
                <p className="neg-walk">{plan.walk_away}</p>
              </div>
            )}
            <div className="card-grid cols-2" style={{ marginTop: 12 }}>
              <div>
                <div className="dim-head"><i className="bi bi-hand-thumbs-up" /> Potential concessions</div>
                {(plan.potential_concessions ?? []).length > 0 ? (
                  <ul className="dim-list">
                    {(plan.potential_concessions ?? []).map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                ) : <div className="text-faint" style={{ fontSize: 12.5 }}>None listed.</div>}
              </div>
              <div>
                <div className="dim-head"><i className="bi bi-question-diamond" /> Questions to ask</div>
                {(plan.questions_to_ask ?? []).length > 0 ? (
                  <ul className="dim-list">
                    {(plan.questions_to_ask ?? []).map((q, i) => <li key={i}>{q}</li>)}
                  </ul>
                ) : <div className="text-faint" style={{ fontSize: 12.5 }}>None listed.</div>}
              </div>
            </div>
          </div>

          <div className="card mb-3">
            <div className="overline mb-2">Key arguments &amp; supporting evidence</div>
            {(plan.key_arguments ?? []).length > 0 ? (
              <div className="dim-grid-cards" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))" }}>
                {(plan.key_arguments ?? []).map((a, i) => (
                  <div key={i} className="scen-block">
                    <div className="dim-head"><i className="bi bi-chat-square-text" /> Argument {i + 1}</div>
                    <div className="text-soft" style={{ fontSize: 13 }}>{a}</div>
                    {(plan.supporting_evidence ?? [])[i] && (
                      <div className="neg-evidence"><i className="bi bi-paperclip" /> {plan.supporting_evidence![i]}</div>
                    )}
                  </div>
                ))}
              </div>
            ) : <div className="text-faint">No arguments listed.</div>}
            {(plan.supporting_evidence ?? []).length > (plan.key_arguments ?? []).length && (
              <div className="mt-2">
                <div className="dim-head"><i className="bi bi-paperclip" /> Supporting evidence on file</div>
                <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
                  {(plan.supporting_evidence ?? []).slice((plan.key_arguments ?? []).length).map((e, i) => (
                    <span key={i} className="badge badge-neutral">{e}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="card mb-3">
            <div className="overline mb-2">Likely counterarguments &amp; responses</div>
            {(plan.likely_objections ?? []).length > 0 ? (
              <div className="obj-list">
                {(plan.likely_objections ?? []).map((o, i) => (
                  <div key={i} className="obj-pair">
                    <div className="obj-side">
                      <span className="badge badge-red badge-xs">Their objection</span>
                      <div className="obj-text">{o}</div>
                    </div>
                    <div className="obj-arrow"><i className="bi bi-arrow-down" /></div>
                    <div className="obj-side">
                      <span className="badge badge-green badge-xs">Your response</span>
                      <div className="obj-text">{(plan.responses ?? [])[i] ?? "—"}</div>
                    </div>
                  </div>
                ))}
              </div>
            ) : <div className="text-faint">No counterarguments listed.</div>}
          </div>
        </>
      )}

      <div className="card mb-3">
        <h3 className="card-title">Suggested message</h3>
        <p className="text-faint" style={{ fontSize: 12.5, marginTop: 0 }}>
          Draft a message in your chosen channel and tone. Drafts stay consistent with the case
          facts — no deceptive claims, no threats.
        </p>
        <div className="form-row cols-3">
          <div>
            <label className="form-label">Channel</label>
            <select className="form-select" value={msgChannel} onChange={(e) => setMsgChannel(e.target.value)}>
              {CHANNELS.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="form-label">Tone</label>
            <select className="form-select" value={msgTone} onChange={(e) => setMsgTone(e.target.value)}>
              {TONES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
          </div>
          <div>
            <label className="form-label">Focus (optional)</label>
            <input className="form-control" value={msgFocus} onChange={(e) => setMsgFocus(e.target.value)}
                   placeholder="e.g. request the itemized statement" />
          </div>
        </div>
        <button className="btn btn-primary mt-2" onClick={generateMessage} disabled={generating}>
          <i className="bi bi-envelope-paper" /> {generating ? "Generating…" : "Generate message"}
        </button>
        {message && (
          <div className="doc-analysis mt-2">
            {message.note && <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}><i className="bi bi-info-circle" />{message.note}</div>}
            {message.subject && <div className="neg-subject"><b>Subject:</b> {message.subject}</div>}
            <textarea className="form-control" rows={7} readOnly value={message.message} style={{ fontFamily: "var(--font-sans)", fontSize: 13 }} />
            {(message.talking_points ?? []).length > 0 && (
              <div className="mt-2">
                <div className="dim-head"><i className="bi bi-list-check" /> Talking points</div>
                <ul className="dim-list">
                  {(message.talking_points ?? []).map((t, i) => <li key={i}>{t}</li>)}
                </ul>
              </div>
            )}
            <button className="btn btn-outline btn-sm mt-2" onClick={copyMessage}>
              <i className="bi bi-clipboard" /> Copy message
            </button>
          </div>
        )}
      </div>

      <div className="card mb-3">
        <div className="flex-between mb-2">
          <h3 className="card-title">Practice negotiation</h3>
          <div className="flex" style={{ gap: 8 }}>
            <select className="form-select" style={{ width: 150 }} value={simLang}
                    onChange={(e) => setSimLang(e.target.value)} disabled={session?.status === "active"}>
              {LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}
            </select>
            {(session?.status === "active" || session?.status === "completed") && (
              <button className="btn btn-ghost btn-sm" onClick={resetSim}>
                <i className="bi bi-arrow-counterclockwise" /> Start over
              </button>
            )}
          </div>
        </div>
        <p className="text-faint" style={{ fontSize: 12.5, marginTop: 0 }}>
          The AI plays the opposing party. Negotiate a few exchanges, then end the session to get
          a scored performance review. This is a separate workflow from the CaseGuide assistant.
        </p>

        {simLoading ? (
          <Loading label="Loading simulation…" />
        ) : !session || (!simStarted && sessionMessages.length === 0) ? (
          <div className="state">
            <i className="bi bi-person-bounding-box" />
            <h3>Prepare to negotiate</h3>
            <p style={{ maxWidth: 560, margin: "0 auto 12px" }}>
              Opponent position: <b>{draft.counterpart_position || "The other side is holding firm and wants evidence before conceding anything."}</b>
            </p>
            <button className="btn btn-primary" onClick={startSimulation} disabled={simStarting}>
              <i className="bi bi-play-fill" /> {simStarting ? "Starting…" : "Start practice"}
            </button>
          </div>
        ) : (
          <>
            {session.status === "active" && (
              <div className="opponent-banner">
                <span className="badge badge-violet"><i className="bi bi-person-bounding-box" /> Opponent's position</span>
                <div className="text-soft" style={{ fontSize: 13, marginTop: 6 }}>{session.opponent_position}</div>
              </div>
            )}

            <div className="chat-scroll" style={{ maxHeight: 400, overflowY: "auto" }}>
              {sessionMessages.map((m, i) => (
                <div key={i} className={`chat-msg ${m.role}`}>
                  <div className="chat-bubble">{m.content}</div>
                  <div className="chat-meta">
                    {m.role === "assistant" && m.label && <span className="badge badge-violet">{m.label}</span>}
                    {m.role === "assistant" && m.note && <span><i className="bi bi-lightbulb" /> {m.note}</span>}
                  </div>
                </div>
              ))}
              <div ref={simEndRef} />
            </div>

            {session.status === "active" ? (
              <>
                <form onSubmit={sendSim} className="chat-input mt-2">
                  <input className="form-control" value={simInput} onChange={(e) => setSimInput(e.target.value)}
                         placeholder="Your move in the negotiation…" disabled={simSending} />
                  <button className="btn btn-primary" disabled={simSending || !simInput.trim()}>
                    {simSending ? <span className="spinner" style={{ borderTopColor: "#fff", borderColor: "rgba(255,255,255,0.4)" }} /> : <><i className="bi bi-send" /> Send</>}
                  </button>
                </form>
                <div className="flex mt-2" style={{ gap: 8, alignItems: "center" }}>
                  <button className="btn btn-outline btn-sm" disabled={simEvaluating || userTurns < 1}
                          onClick={evaluateSim} title={userTurns < 1 ? "Send at least one message first" : "Finish and score the session"}>
                    <i className="bi bi-flag" /> {simEvaluating ? "Evaluating…" : "End & evaluate"}
                  </button>
                  {userTurns < 1 && <span className="text-faint" style={{ fontSize: 12 }}>Send at least one message before ending.</span>}
                </div>
              </>
            ) : (
              evaluation && (
                <div className="doc-analysis mt-2">
                  <div className="flex-between mb-1">
                    <span className="badge badge-violet"><i className="bi bi-trophy" /> Negotiation performance</span>
                    <button className="btn btn-primary btn-sm" onClick={resetSim}>
                      <i className="bi bi-arrow-counterclockwise" /> Practice again
                    </button>
                  </div>
                  {evaluation.note && <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}><i className="bi bi-info-circle" />{evaluation.note}</div>}
                  {evaluation.overall && <p className="risk-summary" style={{ margin: "0 0 10px" }}>{evaluation.overall}</p>}
                  <div className="eval-scores">
                    {EVAL_DIMS.map(([key, label]) => {
                      const score = evaluation.scores?.[key] ?? null;
                      return (
                        <div key={key} className="eval-score">
                          <div className="flex-between">
                            <span className="eval-label">{label}</span>
                            <span className="eval-value">{score ?? "—"}<span className="text-faint">/10</span></span>
                          </div>
                          <div className="score-bar">
                            <div className="score-bar-fill" style={{
                              width: `${(score ?? 0) * 10}%`,
                              background: (score ?? 0) >= 8 ? "var(--green)" : (score ?? 0) >= 5 ? "var(--amber)" : "var(--red)",
                            }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <FeedbackSection icon="bi-check-circle" tone="green" title="What you did well" items={evaluation.strengths} />
                  <FeedbackSection icon="bi-arrow-up-circle" tone="amber" title="What could improve" items={evaluation.improvements} />
                  <FeedbackSection icon="bi-paperclip" tone="blue" title="Evidence you should have used" items={evaluation.evidence_should_have_used} />
                  <FeedbackSection icon="bi-lightbulb" tone="violet" title="Arguments you missed" items={evaluation.arguments_missed} />
                  <FeedbackSection icon="bi-exclamation-triangle" tone="red" title="Potential risks" items={evaluation.potential_risks} />
                  <FeedbackSection icon="bi-chat-quote" tone="green" title="Suggested alternative responses" items={evaluation.alternative_responses} />
                </div>
              )
            )}
          </>
        )}
      </div>

      <div className="mt-3"><LegalDisclaimer /></div>
    </div>
  );
}

function FeedbackSection({ icon, tone, title, items }: {
  icon: string; tone: string; title: string; items?: string[];
}) {
  const tones: Record<string, string> = {
    green: "var(--green)", amber: "var(--amber)", blue: "var(--blue)",
    violet: "var(--violet)", red: "var(--red)",
  };
  if (!items || items.length === 0) return null;
  return (
    <div className="eval-section">
      <div className="dim-head"><i className={`bi ${icon}`} style={{ color: tones[tone] ?? "var(--brand-600)" }} /> {title}</div>
      <ul className="dim-list">
        {items.map((it, i) => <li key={i}>{it}</li>)}
      </ul>
    </div>
  );
}