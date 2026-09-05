import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import type { DemoCaseMeta, User } from "../types";
import { Modal } from "./ui";

/** Phase 13 — "Explore Demo Case" picker. Works for signed-in users and
 *  logged-out visitors (one-click demo session) alike. */
export function DemoPickerModal({ open, demos, onClose }: {
  open: boolean;
  demos: DemoCaseMeta[];
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const { setSessionFromPayload } = useAuth();
  const [busyKind, setBusyKind] = useState<string | null>(null);

  if (!open) return null;

  async function choose(kind: string) {
    if (busyKind) return;
    setBusyKind(kind);
    try {
      const res = await api.post<{ token: string; user: User; case: { id: number } }>(
        "/demo/session", { kind });
      // Logged-out visitor: adopt the shared fictional demo session.
      setSessionFromPayload({ token: res.token, user: res.user });
      toast.info("Fictional demo case opened — everything inside is invented.");
      onClose();
      navigate(`/cases/${res.case.id}/overview`);
    } catch {
      toast.error("Could not open the demo case right now.");
    } finally {
      setBusyKind(null);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Explore a demo case">
      <p className="text-faint" style={{ fontSize: 13, marginTop: 0 }}>
        Five fully-populated fictional cases. Every document, date, party, risk and
        plan inside them is invented for exploration only.
      </p>
      <div className="demo-grid">
        {demos.map((d) => (
          <button key={d.kind} className="card demo-card"
                  disabled={busyKind !== null}
                  onClick={() => void choose(d.kind)}>
            <span className="demo-icon"><i className={`bi ${d.icon}`} /></span>
            <b>{d.title}</b>
            <span className="overline" style={{ color: "var(--brand-600)" }}>
              {d.case_type} · {d.jurisdiction}
            </span>
            <span className="tagline">{d.tagline}</span>
            <div className="demo-stack">
              {Object.entries(d.stacks).map(([k, v]) =>
                v > 0 ? <span key={k} className="src-chip"><i className="bi bi-dot" /> {k} {v}</span> : null,
              )}
            </div>
            {busyKind === d.kind
              ? <span className="overline" style={{ color: "var(--brand-600)" }}>Opening…</span>
              : <span className="overline" style={{ color: "var(--brand-600)" }}>Open workspace →</span>}
          </button>
        ))}
      </div>
    </Modal>
  );
}
