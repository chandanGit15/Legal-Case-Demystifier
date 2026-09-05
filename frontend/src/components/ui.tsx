import { useEffect, useRef } from "react";
import { useFetch } from "../hooks/useFetch";  // re-export for convenience
export { useFetch };
import { caseStatusMeta } from "../utils/constants";

/* ---- Badge ---------------------------------------------------------------- */
const BADGE_TONES: Record<string, string> = {
  // Case statuses (Phase 2)
  draft: "badge-neutral",
  analysis_in_progress: "badge-blue",
  analysis_complete: "badge-green",
  action_required: "badge-amber",
  resolved: "badge-green",
  archived: "badge-neutral",
  // Legacy values tolerated defensively
  active: "badge-green",
  on_hold: "badge-amber",
  closed: "badge-neutral",
  // Entity states
  open: "badge-amber",
  investigating: "badge-blue",
  not_actionable: "badge-neutral",
  found: "badge-green",
  not_applicable: "badge-neutral",
  pending: "badge-amber",
  in_progress: "badge-blue",
  done: "badge-green",
  completed: "badge-green",
  missed: "badge-red",
  high: "badge-red",
  medium: "badge-amber",
  low: "badge-neutral",
  original: "badge-green",
  copy: "badge-blue",
  not_provided: "badge-red",
};

export function Badge({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <span className={`badge ${BADGE_TONES[tone] ?? "badge-neutral"}`}>{children}</span>;
}

export function CaseStatusBadge({ status }: { status: string }) {
  const meta = caseStatusMeta(status);
  return <Badge tone={meta.tone}>{meta.label}</Badge>;
}

export function RiskChip({ level }: { level: string }) {
  const cls = level === "high" ? "risk-high" : level === "low" ? "risk-low" : "risk-medium";
  return <span className={`risk-chip ${cls}`}>{level}</span>;
}

/* ---- States ---------------------------------------------------------------- */
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p style={{ marginTop: 12 }}>{label}</p>
    </div>
  );
}

export function EmptyState({ icon, title, children }: {
  icon: string; title: string; children?: React.ReactNode;
}) {
  return (
    <div className="state" role="status">
      <i className={`bi ${icon}`} aria-hidden="true" />
      <h3>{title}</h3>
      {children && <p>{children}</p>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state err" role="alert">
      <i className="bi bi-exclamation-triangle" aria-hidden="true" />
      <h3>Something went wrong</h3>
      <p>{message}</p>
      {onRetry && <button className="btn btn-outline" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: 64, marginBottom: 12 }} />
      ))}
    </div>
  );
}

/* ---- Modal ----------------------------------------------------------------- */
export function Modal({ open, onClose, title, children }: {
  open: boolean; onClose: () => void; title: string; children: React.ReactNode;
}) {
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    boxRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      previouslyFocused?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" role="dialog" aria-modal="true" aria-label={title}
           tabIndex={-1} ref={boxRef} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close dialog">×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}

/* ---- Section header used inside cards -------------------------------------- */
export function SectionHead({ title, sub, actions }: {
  title: string; sub?: string; actions?: React.ReactNode;
}) {
  return (
    <div className="flex-between mb-2">
      <div>
        <h3 className="card-title">{title}</h3>
        {sub && <p className="text-faint" style={{ fontSize: 13, margin: 0 }}>{sub}</p>}
      </div>
      {actions}
    </div>
  );
}