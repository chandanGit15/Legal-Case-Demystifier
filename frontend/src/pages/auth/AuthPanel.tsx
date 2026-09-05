const STEPS = [
  "Capture the situation as a structured case, not a chat thread",
  "Upload documents — facts are extracted and labeled, never invented",
  "Map risks, gaps and what-if scenarios with AI assistance",
  "Prepare and practice negotiation, then act with a clear plan",
];

export function AuthPanel() {
  return (
    <div className="auth-panel">
      <span className="brand">
        <span className="brand-mark"><i className="bi bi-bank2" /></span>
        <span>Legal Case Demystifier<small>Case intelligence workspace</small></span>
      </span>
      <h2>Understand your legal situation — step by step, not in the dark.</h2>
      <p>
        A structured workspace where documents, facts, risks and strategy come together.
        The AI labels what it knows, what it infers, and what still needs verification —
        it never invents laws, citations, or guarantees.
      </p>
      <ul className="auth-steps">
        {STEPS.map((s, i) => (
          <li key={s}>
            <span className="step-num">{i + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}