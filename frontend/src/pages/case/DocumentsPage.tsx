import { useEffect, useRef, useState } from "react";
import { api } from "../../services/api";
import type {
  DocumentAnalysis,
  DocumentClause,
  DocumentContent,
  DocumentDeadline,
  DocumentInfo,
  DocumentObligation,
  DocumentParty,
} from "../../types";
import { useCase } from "../../context/CaseContext";
import { useToast } from "../../context/ToastContext";
import { LegalDisclaimer } from "../../components/LegalDisclaimer";
import { ProvenanceBadge } from "../../components/ProvenanceBadge";
import { Badge, EmptyState, ErrorState, Loading, Modal } from "../../components/ui";
import { formatSize } from "../../utils/format";

const ALLOWED = ".pdf,.docx,.txt,.png,.jpg,.jpeg,.gif,.webp";

export function DocumentsPage() {
  const { caseId, documents, loading, error, refresh } = useCase();
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<string | null>(null); // uploading → extracting…
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [detailDoc, setDetailDoc] = useState<DocumentInfo | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setFormError("Choose a file first (PDF, DOCX, TXT, or an image).");
      return;
    }
    setPhase("uploading");
    setFormError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      setPhase("extracting");
      await api.post<{ document: DocumentInfo }>(`/cases/${caseId}/documents`, undefined, fd);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      await refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setPhase(null);
    }
  }

  async function analyze(doc: DocumentInfo) {
    setAnalyzingId(doc.id);
    setFormError(null);
    try {
      await api.post(`/cases/${caseId}/documents/${doc.id}/analyze`);
      await refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzingId(null);
    }
  }

  async function remove(doc: DocumentInfo) {
    if (!window.confirm(`Delete "${doc.filename}"? The uploaded file, its extracted text and analysis will be removed.`)) return;
    try {
      await api.del(`/cases/${caseId}/documents/${doc.id}`);
      await refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not delete the document");
    }
  }

  return (
    <div>
      <div className="mb-3">
        <div className="overline mb-1">Document intelligence</div>
        <p className="text-soft" style={{ margin: 0, fontSize: 13.5 }}>
          Upload PDF, DOCX, TXT or images. Each file is validated, its text is extracted
          and chunked server-side, then analyzed by the AI — everything stays linked to
          this case (#{caseId}).
        </p>
      </div>

      <div className="card mb-3">
        <h3 className="card-title">Upload a document</h3>
        <form onSubmit={upload}>
          <div className="form-row">
            <div>
              <input ref={inputRef} className="form-control" type="file" accept={ALLOWED}
                     onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                     disabled={phase !== null} />
              <div className="form-hint">
                {file ? `${file.name} (${formatSize(file.size)})`
                  : "Supported: PDF, DOCX, TXT, PNG, JPG, GIF, WEBP — up to 20 MB. TXT preferred for fastest extraction."}
              </div>
            </div>
          </div>
          {phase && (
            <PipelineNote step={phase} label={file ? file.name : ""} />
          )}
          {formError && <div className="alert-box error">{formError}</div>}
          <button className="btn btn-primary" disabled={phase !== null || !file}>
            {phase === null ? <><i className="bi bi-upload" /> Upload</>
              : <><span className="spinner spin-light" /> {phase === "uploading" ? "Uploading…" : "Extracting text…"}</>}
          </button>
        </form>
      </div>

      {loading && <div className="card"><Loading label="Loading documents…" /></div>}
      {error && <div className="card"><ErrorState message={error} onRetry={() => void refresh()} /></div>}
      {!loading && !error && documents.length === 0 && (
        <div className="card">
          <EmptyState icon="bi-file-earmark-text" title="No documents yet">
            Upload a contract, letter, invoice or any relevant file. The AI reads it and
            extracts structured findings that stay attached to this case.
          </EmptyState>
        </div>
      )}

      {!loading && !error && documents.length > 0 && (
        <>
          <div className="card mb-3">
            <p className="text-faint" style={{ margin: 0, fontSize: 13 }}>
              {documents.length} document{documents.length === 1 ? "" : "s"} · analysis is
              automatic after upload — open <b>Details</b> to review findings and connect them to the case.
            </p>
          </div>
          <div className="card">
            <div className="list">
              {documents.map((doc) => (
                <div key={doc.id} className="list-item">
                  <div className={`doc-icon ${doc.file_type}`}>
                    <i className={`bi ${iconFor(doc.file_type)}`} />
                  </div>
                  <div className="li-main">
                    <div className="li-title">{doc.filename}</div>
                    <div className="li-meta">
                      <span className="badge badge-neutral">{doc.file_type}</span>
                      <span className="badge badge-neutral">{formatSize(doc.size_bytes)}</span>
                      <PipelineStatus doc={doc} />
                    </div>
                    <div className="li-meta">
                      {doc.has_text && <span className="badge badge-neutral"><i className="bi bi-file-text" /> content extracted{doc.chunk_count ? ` · ${doc.chunk_count} chunk${doc.chunk_count === 1 ? "" : "s"}` : ""}</span>}
                      {doc.analysis_status === "analyzed" && <Badge tone="neutral"><i className="bi bi-stars" /> findings ready</Badge>}
                    </div>
                  </div>
                  <div className="flex" style={{ gap: 6, alignItems: "center" }}>
                    {doc.analysis_status !== "analyzing" && doc.analysis_status !== "analyzed" && (
                      <button className="btn btn-outline btn-sm" disabled={analyzingId === doc.id}
                              onClick={() => analyze(doc)}>
                        {analyzingId === doc.id ? <><span className="spinner spin-dark" /> Analyzing…</>
                          : <><i className="bi bi-stars" /> Analyze</>}
                      </button>
                    )}
                    {doc.analysis_status === "analyzed" && (
                      <button className="btn btn-outline btn-sm" disabled={analyzingId === doc.id}
                              onClick={() => analyze(doc)}>
                        {analyzingId === doc.id ? <><span className="spinner spin-dark" /> Analyzing…</>
                          : <><i className="bi bi-arrow-repeat" /> Re-run</>}
                      </button>
                    )}
                    <button className="btn btn-primary btn-sm" onClick={() => setDetailDoc(doc)}>
                      <i className="bi bi-search" /> Details
                    </button>
                    <button className="btn btn-danger-ghost btn-sm" onClick={() => remove(doc)}>
                      <i className="bi bi-trash" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-3"><LegalDisclaimer /></div>
        </>
      )}

      {detailDoc && (
        <DocumentDetailModal doc={detailDoc} onClose={() => setDetailDoc(null)}
                             onReanalyze={analyze} />
      )}
    </div>
  );
}

/* ---- Processing states --------------------------------------------------- */

function PipelineNote({ step, label }: { step: string; label: string }) {
  const steps: [string, string][] = [
    ["uploading", "Uploading to secure storage"],
    ["extracting", "Extracting text and chunking content"],
    ["analyzing", "AI is reading the document and structuring findings"],
  ];
  const idx = steps.findIndex(([s]) => s === step);
  return (
    <div className="pipeline-note">
      {steps.map(([s, text], i) => (
        <div key={s} className={`pipe-step ${i === idx ? "active" : i < idx ? "done" : ""}`}>
          {i < idx || (i === idx && s !== "analyzing")
            ? <i className="bi bi-check-circle-fill" />
            : <span className="spinner spin-dark" style={{ width: 13, height: 13 }} />}
          <span>{text}{s === step && label ? ` — ${label}` : ""}</span>
        </div>
      ))}
    </div>
  );
}

function PipelineStatus({ doc }: { doc: DocumentInfo }) {
  // Extraction state
  let ext: { label: string; cls: string; icon: string } = { label: "pending", cls: "badge-neutral", icon: "bi-hourglass-split" };
  if (doc.extraction_status === "extracted") ext = { label: "text extracted", cls: "badge-green", icon: "bi-check-circle" };
  else if (doc.extraction_status === "ocr_pending") ext = { label: "image — OCR via AI", cls: "badge-amber", icon: "bi-image" };
  else if (doc.extraction_status === "failed") ext = { label: "extraction failed", cls: "badge-red", icon: "bi-exclamation-triangle" };

  // Analysis state
  let an: { label: string; cls: string; icon: string } = { label: "not analyzed", cls: "badge-neutral", icon: "bi-dash-circle" };
  if (doc.analysis_status === "analyzing") an = { label: "analyzing…", cls: "badge-amber", icon: "bi-arrow-repeat" };
  else if (doc.analysis_status === "analyzed") an = { label: "analyzed", cls: "badge-green", icon: "bi-check-circle" };
  else if (doc.analysis_status === "failed") an = { label: "analysis failed", cls: "badge-red", icon: "bi-exclamation-triangle" };

  return (
    <>
      <span className={`badge ${ext.cls}`}><i className={`bi ${ext.icon}`} /> {ext.label}</span>
      <span className={`badge ${an.cls}`}><i className={`bi ${an.icon}`} /> {an.label}</span>
    </>
  );
}

/* ---- Document details modal --------------------------------------------- */

function DocumentDetailModal({ doc, onClose, onReanalyze }: {
  doc: DocumentInfo;
  onClose: () => void;
  onReanalyze: (doc: DocumentInfo) => void;
}) {
  const { caseId, refresh } = useCase();
  const toast = useToast();
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [contentErr, setContentErr] = useState<string | null>(null);
  const [importing, setImporting] = useState<string | null>(null);
  const a = doc.analysis ?? {};

  useEffect(() => {
    let cancelled = false;
    api.get<DocumentContent>(`/cases/${caseId}/documents/${doc.id}/content`)
      .then((d) => { if (!cancelled) setContent(d); })
      .catch((e) => { if (!cancelled) setContentErr(e instanceof Error ? e.message : "Could not load content"); });
    return () => { cancelled = true; };
  }, [caseId, doc.id]);

  async function connect(kind: string, data: Record<string, unknown>) {
    setImporting(kind);
    try {
      await api.post(`/cases/${caseId}/documents/${doc.id}/import`, { kind, data });
      toast.success(`${kind === "deadline" ? "Deadline" : kind === "timeline" ? "Date" : kind === "issue" ? "Issue" : "Finding"} connected to the case.`);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not connect this finding");
    } finally {
      setImporting(null);
    }
  }

  return (
    <Modal open onClose={onClose} title={doc.filename}>
      <div className="doc-detail">
        <div className="doc-meta-grid">
          <MetaItem label="Document type" value={doc.file_type.toUpperCase()} icon="bi-file-earmark" />
          <MetaItem label="Size" value={formatSize(doc.size_bytes)} icon="bi-hdd" />
          <MetaItem label="Uploaded" value={new Date(doc.uploaded_at).toLocaleString()} icon="bi-clock-history" />
          <MetaItem label="Chunks" value={content ? String(content.chunk_count) : String(doc.chunk_count ?? 0)} icon="bi-collection" />
        </div>
        <div className="li-meta mb-2" style={{ marginBottom: 14 }}>
          <PipelineStatus doc={doc} />
          {doc.extraction_status === "ocr_pending" && (
            <span className="badge badge-blue"><i className="bi bi-info-circle" /> Text is transcribed during analysis</span>
          )}
          {doc.analysis_status === "analyzed" && (
            <button className="btn btn-outline btn-sm" onClick={() => onReanalyze(doc)}>
              <i className="bi bi-arrow-repeat" /> Re-run analysis
            </button>
          )}
        </div>

        <AnalysisFindings a={a} doc={doc} importing={importing} onConnect={connect} />

        {/* Extracted content */}
        <div className="card" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <div className="flex-between mb-2">
            <h3 className="card-title">Extracted content</h3>
            <span className="overline">
              {content ? `${content.text_length.toLocaleString()} chars` : "…"}
            </span>
          </div>
          {contentErr && <div className="alert-box error">{contentErr}</div>}
          {!content && !contentErr && <Loading label="Loading extracted content…" />}
          {content && !content.has_text && (
            <EmptyState icon="bi-file-earmark-x" title="No extractable text">
              {doc.extraction_status === "ocr_pending"
                ? "This image has no text layer — run analysis so the AI can read it."
                : "Text could not be extracted from this file."}
            </EmptyState>
          )}
          {content?.has_text && (
            <>
              <pre className="doc-text">{content.excerpt}</pre>
              {content.excerpt_truncated && (
                <div className="form-hint" style={{ marginTop: 6 }}>
                  Showing the first 6,000 characters · text is chunked into {content.chunk_count} segment{content.chunk_count === 1 ? "" : "s"} for retrieval.
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </Modal>
  );
}

function MetaItem({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div className="doc-meta-item">
      <i className={`bi ${icon}`} />
      <div>
        <div className="overline" style={{ fontSize: 9.5 }}>{label}</div>
        <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{value}</div>
      </div>
    </div>
  );
}

function AnalysisFindings({ a, doc, importing, onConnect }: {
  a: DocumentAnalysis;
  doc: DocumentInfo;
  importing: string | null;
  onConnect: (kind: string, data: Record<string, unknown>) => void;
}) {
  if (doc.analysis_status !== "analyzed") {
    return (
      <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
        <EmptyState icon="bi-stars" title="Not analyzed yet">
          Run analysis to structure this document into a summary, clauses, dates,
          obligations, deadlines and potential issues — all labeled as extracted.
        </EmptyState>
      </div>
    );
  }

  const parties: DocumentParty[] = a.parties ?? [];
  const obligations: DocumentObligation[] = a.obligations ?? [];
  const clauses: DocumentClause[] = a.important_clauses ?? [];
  const concerning: DocumentClause[] = a.concerning_clauses ?? [];
  const deadlines: DocumentDeadline[] = a.deadlines ?? [];
  const dates: { date?: string; description?: string }[] = a.dates_found ?? [];
  const entities: string[] = a.entities ?? [];
  const issues = a.possible_issues ?? [];
  const warnings = a.warnings ?? [];
  const verify = a.requires_verification ?? [];
  const facts = a.key_facts ?? [];

  return (
    <>
      <div className="doc-analysis" style={{ marginBottom: 14 }}>
        {a.note && <div className="disclaimer disclaimer-info mb-2" style={{ fontSize: 12 }}><i className="bi bi-info-circle" />{a.note}</div>}
        {a.summary && <p style={{ margin: 0 }}><b>AI summary.</b> {a.summary}</p>}
        {a.mode === "demo" && <p className="text-faint" style={{ fontSize: 11.5, margin: "6px 0 0" }}>Demo analysis — structural findings appear when a Gemini key is configured.</p>}
      </div>

      <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
        <h3 className="card-title">Document intelligence</h3>
        <div className="f-grid">
          <FBlock label="Document type">
            {a.document_type ? <span className="badge badge-brand">{a.document_type}</span> : <Muted>Not identified</Muted>}
          </FBlock>
          <FBlock label="Parties">
            {parties.length === 0 ? <Muted>None named</Muted> : parties.map((p, i) => (
              <div key={i} className="f-row">
                <b>{p.name}</b>{p.role ? <span className="text-faint"> — {p.role}</span> : null}
              </div>
            ))}
          </FBlock>
          <FBlock label="Obligations">
            {obligations.length === 0 ? <Muted>None identified</Muted> : obligations.map((o, i) => (
              <div key={i} className="f-row">
                {o.party ? <><b>{o.party}:</b> </> : <><b>Required:</b> </>}{o.obligation}
              </div>
            ))}
          </FBlock>
          <FBlock label="Referenced entities">
            {entities.length === 0 ? <Muted>None referenced</Muted> : entities.map((en, i) => (
              <span key={i} className="badge badge-neutral" style={{ marginRight: 6 }}>{en}</span>
            ))}
          </FBlock>
        </div>
      </div>

      {/* Key facts */}
      {facts.length > 0 && (
        <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <h3 className="card-title">Key facts</h3>
          {facts.map((f, i) => (
            <div key={i} className="flex" style={{ gap: 8, alignItems: "flex-start", marginTop: 6 }}>
              <ProvenanceBadge source="document" />
              <span className="text-soft">{f.text}</span>
            </div>
          ))}
        </div>
      )}

      {/* Important clauses */}
      {clauses.length > 0 && (
        <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <h3 className="card-title">Important clauses</h3>
          {clauses.map((c, i) => (
            <div key={i} className="find-row">
              <div className="li-main">
                {c.section && <span className="badge badge-neutral" style={{ fontSize: 10.5 }}>§ {c.section}</span>}
                <div className="li-desc" style={{ fontStyle: "italic" }}>“{c.quote}”</div>
                {c.meaning && <div className="li-desc mt-1"><b>Meaning:</b> {c.meaning}</div>}
              </div>
              <button className="btn btn-outline btn-sm" disabled={importing !== null}
                      onClick={() => onConnect("evidence", {
                        title: (c.section ? `Clause ${c.section}` : "Important clause excerpt"),
                        text: `${c.quote ?? ""}${c.meaning ? ` — ${c.meaning}` : ""}`,
                      })}>
                {importing === "evidence" ? <span className="spinner spin-dark" /> : <><i className="bi bi-link-45deg" /> Save as evidence</>}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Deadlines + dates */}
      {(deadlines.length > 0 || dates.length > 0) && (
        <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <h3 className="card-title">Deadlines & dates</h3>
          {deadlines.map((d, i) => (
            <div key={`dl${i}`} className="find-row">
              <div className="li-main">
                <div className="li-title" style={{ fontSize: 13.5 }}>
                  <span className="mono" style={{ marginRight: 8 }}>{d.date}</span>{d.title}
                </div>
                {d.description && <div className="li-desc">{d.description}</div>}
              </div>
              <button className="btn btn-outline btn-sm" disabled={importing !== null}
                      onClick={() => onConnect("deadline", { date: d.date, title: d.title, description: d.description })}>
                {importing === "deadline" ? <span className="spinner spin-dark" /> : <><i className="bi bi-alarm" /> Add to Action Plan</>}
              </button>
            </div>
          ))}
          {dates.map((d, i) => (
            <div key={`dt${i}`} className="find-row">
              <div className="li-main">
                <div className="li-title" style={{ fontSize: 13.5 }}>
                  <span className="mono" style={{ marginRight: 8 }}>{d.date}</span>{d.description}
                </div>
              </div>
              <button className="btn btn-outline btn-sm" disabled={importing !== null}
                      onClick={() => onConnect("timeline", { date: d.date, title: d.description })}>
                {importing === "timeline" ? <span className="spinner spin-dark" /> : <><i className="bi bi-calendar-plus" /> Add to Timeline</>}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Concerning clauses */}
      {concerning.length > 0 && (
        <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <h3 className="card-title"><i className="bi bi-shield-exclamation" style={{ color: "var(--amber)" }} /> Potentially concerning clauses</h3>
          {concerning.map((c, i) => (
            <div key={i} className="find-row">
              <div className="li-main">
                <div className="li-desc" style={{ fontStyle: "italic" }}>“{c.quote}”</div>
                {c.reason && <div className="li-desc mt-1"><b>Why it matters:</b> {c.reason}</div>}
                <div className="li-meta">{c.severity && <Badge tone={c.severity}>{c.severity}</Badge>}</div>
              </div>
              <button className="btn btn-outline btn-sm" disabled={importing !== null}
                      onClick={() => onConnect("issue", { title: `Review clause${c.section ? ` ${c.section}` : ""}: ${String(c.reason ?? c.quote ?? "").slice(0, 80)}`, basis: `${c.quote} — ${c.reason ?? ""}`, confidence: c.severity === "high" ? "high" : "medium" })}>
                {importing === "issue" ? <span className="spinner spin-dark" /> : <><i className="bi bi-link-45deg" /> Flag as issue</>}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Potential issues */}
      {issues.length > 0 && (
        <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <h3 className="card-title">Potential issues</h3>
          {issues.map((i, idx) => (
            <div key={idx} className="flex" style={{ gap: 8, alignItems: "flex-start", marginTop: 8 }}>
              <ProvenanceBadge source="document" />
              <div>
                <b style={{ fontSize: 13.5 }}>{i.title}</b>
                {i.basis && <div className="li-desc">{i.basis}</div>}
                <div className="li-meta">
                  {i.confidence && <Badge tone={i.confidence}>confidence: {i.confidence}</Badge>}
                  <span className="badge badge-green"><i className="bi bi-check-circle" /> already added to Legal Issues</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Warnings */}
      {(warnings.length > 0 || verify.length > 0) && (
        <div className="card mb-3" style={{ boxShadow: "none", border: "1px solid var(--line)" }}>
          <h3 className="card-title"><i className="bi bi-exclamation-triangle" style={{ color: "var(--red)" }} /> Warnings</h3>
          {[...warnings, ...verify].map((w, i) => (
            <div key={i} className="flex" style={{ gap: 8, marginTop: 6, alignItems: "flex-start" }}>
              <i className="bi bi-shield-exclamation" style={{ color: "var(--amber)" }} />
              <span className="text-soft" style={{ fontSize: 13 }}>{w}</span>
            </div>
          ))}
          <div className="form-hint" style={{ marginTop: 8, fontSize: 11.5 }}>
            Findings are extracted from {doc.filename} and marked “from document” in the case.
          </div>
        </div>
      )}
    </>
  );
}

function FBlock({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="overline mb-1">{label}</div>
      {children}
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <span className="text-faint" style={{ fontSize: 12.5 }}>{children}</span>;
}

/* ---- helpers ------------------------------------------------------------- */

function iconFor(type: string) {
  if (type === "pdf") return "bi-file-earmark-pdf";
  if (type === "docx") return "bi-file-earmark-word";
  if (type === "txt") return "bi-file-earmark-text";
  if (type === "image") return "bi-file-earmark-image";
  return "bi-file-earmark";
}
