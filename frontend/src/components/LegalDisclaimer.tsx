export function LegalDisclaimer({ note }: { note?: string }) {
  return (
    <div className="disclaimer">
      <i className="bi bi-shield-shaded" />
      <div>
        <b>Not legal advice.</b> This application provides informational and
        decision-support assistance and is not a substitute for advice from a qualified
        legal professional. AI-generated content may contain errors and must be verified
        by a qualified legal professional before any action is taken.
        {note && <div style={{ marginTop: 4 }}>{note}</div>}
      </div>
    </div>
  );
}