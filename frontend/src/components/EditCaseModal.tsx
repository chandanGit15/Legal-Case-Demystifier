import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import type { CaseSummary } from "../types";
import { useToast } from "../context/ToastContext";
import { useCase } from "../context/CaseContext";
import {
  CASE_CATEGORIES,
  CASE_STATUS_OPTIONS,
  INDIAN_STATES,
  INDIAN_UNION_TERRITORIES,
  JURISDICTION_COUNTRY,
} from "../utils/constants";
import { Modal } from "./ui";

export function EditCaseModal({ open, onClose, caseData }: {
  open: boolean;
  onClose: () => void;
  caseData: CaseSummary;
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const { setCaseData } = useCase();
  const [title, setTitle] = useState(caseData.title);
  const [caseType, setCaseType] = useState(caseData.case_type);
  const [state, setState] = useState(caseData.state);
  const legacyState = caseData.state && ![INDIAN_STATES, INDIAN_UNION_TERRITORIES].flat().includes(caseData.state);
  const [status, setStatus] = useState(caseData.status);
  const [stage, setStage] = useState(caseData.stage);
  const [parties, setParties] = useState(caseData.parties ?? "");
  const [description, setDescription] = useState(caseData.description);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("A case title is required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.patch<{ case: CaseSummary }>(`/cases/${caseData.id}`, {
        title: title.trim(),
        case_type: caseType,
        country: JURISDICTION_COUNTRY,
        state,
        status,
        stage,
        parties,
        description,
      });
      setCaseData(res.case);
      toast.success("Case updated.");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save changes");
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this case and all of its data? This cannot be undone.")) return;
    setBusy(true);
    try {
      await api.del(`/cases/${caseData.id}`);
      toast.success("Case deleted.");
      navigate("/cases");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the case");
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Edit case">
      <form onSubmit={save}>
        <div className="form-row">
          <div>
            <label className="form-label">Case title *</label>
            <input className="form-control" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
        </div>
        <div className="form-row cols-2">
          <div>
            <label className="form-label">Legal issue category</label>
            <select className="form-select" value={caseType} onChange={(e) => setCaseType(e.target.value)}>
              <option value="">Select…</option>
              {CASE_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="form-label">Status</label>
            <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)}>
              {CASE_STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>
        <div className="form-row cols-2">
          <div>
            <label className="form-label">Jurisdiction</label>
            <input className="form-control" value={JURISDICTION_COUNTRY} readOnly
                   aria-readonly="true" title="The application is India-only" />
            <div className="form-hint">Fixed — India-only application.</div>
          </div>
          <div>
            <label className="form-label" htmlFor="ec-state">State / Union Territory</label>
            {legacyState && (
              <div className="form-hint" style={{ color: "var(--amber, #b45309)" }}>
                Current state “{caseData.state}” is not an Indian state/UT — pick one to update it.
              </div>
            )}
            <select id="ec-state" className="form-select" value={state}
                    onChange={(e) => setState(e.target.value)}>
              <option value="">Select state / UT…</option>
              {legacyState && <option value={state}>{state} (not supported)</option>}
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
            <label className="form-label">Parties</label>
            <input className="form-control" value={parties} onChange={(e) => setParties(e.target.value)}
                   placeholder="e.g. You (tenant) vs. Maple Properties Inc. (landlord)" />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label className="form-label">Stage</label>
            <input className="form-control" value={stage} onChange={(e) => setStage(e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label className="form-label">Description</label>
            <textarea className="form-control" rows={4} value={description}
                      onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>
        {error && <div className="alert-box error">{error}</div>}
        <div className="flex-between">
          <button type="button" className="btn btn-danger-ghost" onClick={remove} disabled={busy}>
            <i className="bi bi-trash" /> Delete case
          </button>
          <div className="flex" style={{ gap: 10 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={busy}>
              {busy ? "Saving…" : "Save changes"}
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
