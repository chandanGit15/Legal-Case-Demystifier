export const PROVENANCE_META: Record<string, { label: string; cls: string; icon: string }> = {
  user: { label: "User-provided fact", cls: "prov-user", icon: "bi-person" },
  document: { label: "Extracted from document", cls: "prov-document", icon: "bi-file-earmark-text" },
  ai: { label: "AI interpretation", cls: "prov-ai", icon: "bi-stars" },
  gap: { label: "Information missing", cls: "prov-gap", icon: "bi-question-circle" },
  verify: { label: "Requires verification", cls: "prov-verify", icon: "bi-shield-exclamation" },
};

export function ProvenanceBadge({ source }: { source: string }) {
  const meta = PROVENANCE_META[source] ?? PROVENANCE_META.user;
  return (
    <span className={`badge ${meta.cls}`} title={meta.label}>
      <i className={`bi ${meta.icon}`} />
      {meta.label}
    </span>
  );
}

export function ProvenanceLegend() {
  return (
    <div className="legend">
      {Object.entries(PROVENANCE_META).map(([key, m]) => (
        <span key={key}>
          <i className={`bi ${m.icon}`} style={{ marginRight: 4 }} />
          <b>{m.label}</b>
        </span>
      ))}
    </div>
  );
}