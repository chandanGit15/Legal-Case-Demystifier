import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useToast } from "../context/ToastContext";
import type { CaseSummary, DocumentInfo } from "../types";
import {
  CASE_CATEGORIES,
  INDIAN_STATES,
  INDIAN_UNION_TERRITORIES,
  JURISDICTION_COUNTRY,
} from "../utils/constants";
import { Modal } from "./ui";

/** Formats accepted by the New Case uploader (backend accepts the same set). */
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"];
const MAX_FILE_MB = 20;

type Progress = {
  active: boolean;
  label: string;
  detail: string;
  index: number;
  total: number;
};

export function NewCaseModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [caseType, setCaseType] = useState("");
  const [state, setState] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Fresh form each time the modal opens (no stale title/files from a
  // previous session).
  useEffect(() => {
    if (open) {
      setTitle("");
      setCaseType("");
      setState("");
      setDescription("");
      setFiles([]);
      setError(null);
      setSubmitting(false);
      setProgress(null);
    }
  }, [open]);

  function addFiles(list: FileList | null) {
    if (!list || list.length === 0) return;
    setError(null);
    const next = [...files];
    for (const f of Array.from(list)) {
      const ext = f.name.includes(".") ? `.${f.name.split(".").pop()!.toLowerCase()}` : "";
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        setError(`"${f.name}" is not supported. Use PDF, DOCX, TXT, JPG or PNG.`);
        continue;
      }
      if (f.size === 0) {
        setError(`"${f.name}" is empty.`);
        continue;
      }
      if (f.size > MAX_FILE_MB * 1024 * 1024) {
        setError(`"${f.name}" exceeds the ${MAX_FILE_MB} MB limit.`);
        continue;
      }
      if (!next.some((existing) => existing.name === f.name && existing.size === f.size)) {
        next.push(f);
      }
    }
    setFiles(next);
  }

  function removeFile(name: string) {
    setFiles((prev) => prev.filter((f) => f.name !== name));
    setError(null);
  }

  function prettyTitleFromFile(file: File): string {
    const base = file.name.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim();
    return base.replace(/\b\w/g, (ch) => ch.toUpperCase());
  }

  function setStage(label: string, detail: string, index: number, total: number) {
    setProgress({ active: true, label, detail, index, total });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const finalTitle = title.trim() || (files.length > 0 ? prettyTitleFromFile(files[0]) : "");
    if (!finalTitle) {
      setError("Please give the case a title (or upload a document to start from).");
      return;
    }
    setSubmitting(true);
    setError(null);
    setStage("Creating the case…", "", 0, files.length);
    try {
      // 1. Create the case — jurisdiction is always India (backend enforces it too).
      const data = await api.post<{ case: CaseSummary }>("/cases", {
        title: finalTitle,
        case_type: caseType,
        state,
        description: description.trim(),
      });
      const caseId = data.case.id;

      // 2. Upload each file and analyze it through the existing pipeline,
      //    so everything lands in the same Case ID / Documents workspace.
      const uploaded: string[] = [];
      const failed: string[] = [];
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        setStage("Uploading…", `${file.name} (${i + 1} of ${files.length})`, i + 1, files.length);
        try {
          const fd = new FormData();
          fd.append("file", file);
          const up = await api.post<{ document: DocumentInfo }>(
            `/cases/${caseId}/documents`, undefined, fd);
          uploaded.push(file.name);
          setStage("Extracting information…", file.name, i + 1, files.length);
          setStage("Analyzing document…", file.name, i + 1, files.length);
          await api.post(`/cases/${caseId}/documents/${up.document.id}/analyze`);
          setStage("Adding to case…", file.name, i + 1, files.length);
        } catch (err) {
          failed.push(file.name);
          console.error("New-case file processing failed:", err);
        }
      }

      if (failed.length > 0 && uploaded.length === 0) {
        setSubmitting(false);
        setError(
          `The case was created but the file${failed.length > 1 ? "s" : ""} could not be processed. ` +
          "You can retry from the Documents tab.");
        navigate(`/cases/${caseId}/overview`);
        onClose();
        return;
      }
      const withFiles = files.length > 0;
      const analyzed = uploaded.length;
      const skipped = withFiles ? ` ${analyzed} of ${files.length} document${files.length > 1 ? "s" : ""} attached and analyzed.` : "";
      toast.success(
        `Case created — opening the workspace.${skipped}${failed.length > 0 ? ` ${failed.length} upload${failed.length > 1 ? "s" : ""} failed; retry from the Documents tab.` : ""}`);
      onClose();
      navigate(`/cases/${caseId}/overview`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the case.");
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Start a new case">
      <form onSubmit={submit}>
        <div className="form-row">
          <div>
            <label className="form-label" htmlFor="nc-title">Case title *</label>
            <input id="nc-title" className="form-control" value={title}
                   onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Rental deposit dispute"
                   disabled={submitting} />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label className="form-label" htmlFor="nc-type">Legal issue category</label>
            <select id="nc-type" className="form-select" value={caseType}
                    onChange={(e) => setCaseType(e.target.value)} disabled={submitting}>
              <option value="">Select…</option>
              {CASE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div className="form-row cols-2">
          <div>
            <label className="form-label" htmlFor="nc-country">Jurisdiction</label>
            <input id="nc-country" className="form-control" value={JURISDICTION_COUNTRY}
                   readOnly aria-readonly="true" title="The application is India-only" />
            <div className="form-hint">Fixed — this application is for the Indian legal context.</div>
          </div>
          <div>
            <label className="form-label" htmlFor="nc-state">State / Union Territory</label>
            <select id="nc-state" className="form-select" value={state}
                    onChange={(e) => setState(e.target.value)} disabled={submitting}>
              <option value="">Select state / UT…</option>
              <optgroup label="States">
                {INDIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </optgroup>
              <optgroup label="Union Territories">
                {INDIAN_UNION_TERRITORIES.map((s) => <option key={s} value={s}>{s}</option>)}
              </optgroup>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div>
            <label className="form-label" id="nc-upload-label">Upload case documents</label>
            <div className="form-hint" style={{ marginTop: -6, marginBottom: 8 }}>
              Upload a document or image and let AI analyze it automatically. You can also
              describe the situation manually below — both are combined into the case.
            </div>
            <div
              className={`dropzone${dragOver ? " drag" : ""}${submitting ? " disabled" : ""}`}
              role="button"
              tabIndex={submitting ? -1 : 0}
              aria-labelledby="nc-upload-label"
              onClick={() => !submitting && inputRef.current?.click()}
              onKeyDown={(e) => { if (!submitting && (e.key === "Enter" || e.key === " ")) inputRef.current?.click(); }}
              onDragOver={(e) => { if (!submitting) { e.preventDefault(); setDragOver(true); } }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { if (!submitting) { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); } }}
            >
              <i className="bi bi-cloud-arrow-up" aria-hidden="true" />
              <span>Drag &amp; drop files here or <b>Browse</b></span>
              <small>PDF • DOCX • TXT • JPG • PNG</small>
            </div>
            <input
              ref={inputRef}
              id="nc-upload-input"
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
              className="visually-hidden"
              onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }}
            />
            {files.length > 0 && (
              <ul className="file-list" aria-label="Selected files">
                {files.map((f) => (
                  <li key={f.name}>
                    <span className="file-ok" aria-hidden="true"><i className="bi bi-check-lg" /></span>
                    <span className="file-name" title={f.name}>{f.name}</span>
                    <span className="file-size">{formatMB(f.size)}</span>
                    <button type="button" className="file-remove" aria-label={`Remove ${f.name}`}
                            onClick={() => removeFile(f.name)} disabled={submitting}>
                      <i className="bi bi-x-lg" aria-hidden="true" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="form-row">
          <div>
            <label className="form-label" htmlFor="nc-desc">What happened? (facts you know)</label>
            <textarea id="nc-desc" className="form-control" rows={4} value={description}
                      onChange={(e) => setDescription(e.target.value)} disabled={submitting}
                      placeholder="Describe the situation in your own words. The AI combines this with any uploaded documents." />
            <div className="form-hint">Labeled as user-provided facts in later analysis.</div>
          </div>
        </div>

        {progress?.active && (
          <div className="upload-progress" role="status" aria-live="polite">
            <span className="spinner" aria-hidden="true" />
            <div>
              <strong>{progress.label}</strong>
              {progress.detail && <div className="upload-progress-detail">{progress.detail}</div>}
            </div>
          </div>
        )}

        {error && <div className="alert-box error">{error}</div>}
        <div className="flex" style={{ justifyContent: "flex-end", gap: 10 }}>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? (progress?.active ? progress.label : "Creating…") : "Create case"}
          </button>
        </div>
        <div className="form-hint" style={{ marginTop: 10 }}>
          You can provide information manually, upload documents, or use both.
        </div>
      </form>
    </Modal>
  );
}

function formatMB(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}