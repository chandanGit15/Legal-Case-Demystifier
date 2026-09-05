import { Link } from "react-router-dom";

const SECTIONS: { h: string; body: React.ReactNode }[] = [
  {
    h: "What data the platform stores",
    body: (
      <>
        <p>
          Your account details (name, email, preferred language and jurisdiction defaults),
          plus everything you add to a case: case descriptions, uploaded documents, extracted
          text, AI analyses, timeline events, evidence records, issues, risks, scenarios,
          negotiation briefs, practice transcripts, and action plans.
        </p>
        <p>
          Demo cases and the shared demo account contain entirely fictional information —
          they never mix with your own accounts or cases.
        </p>
      </>
    ),
  },
  {
    h: "Document processing",
    body: (
      <>
        <p>
          Uploaded files (PDF, DOCX, TXT and images) are stored on the application&apos;s own
          server and their text is extracted and analyzed there. Documents are associated with
          exactly one case, and cases belong to exactly one account. No other account can list,
          read, or delete your documents.
        </p>
        <p>
          When the AI provider is configured, relevant document text is sent to it solely to
          produce the analysis shown in your case workspace. Without a configured key the app
          runs entirely on-device demo analysis and nothing is sent anywhere. Extracted text is
          used only to build your case&apos;s insights — it is never published or shared.
        </p>
      </>
    ),
  },
  {
    h: "How the data is handled",
    body: (
      <>
        <p>
          Data is stored in the application&apos;s own database (SQLite locally, PostgreSQL-ready).
          Passwords are stored only as salted hashes. Sessions use signed, expiring tokens; the
          signing key and any AI API keys exist only in backend environment variables — never in
          browser code, logs, or API responses. API responses are served with no-store caching
          and are only accessible to the signed-in account that owns them.
        </p>
      </>
    ),
  },
  {
    h: "Deleting cases and documents",
    body: (
      <>
        <p>
          You can delete a document or an entire case at any time from the case workspace.
          Deleting a case removes its documents, extracted text, analyses, timeline, issues,
          risks, evidence, scenarios, negotiation records and action plan. Where stored files
          exist, they are removed from the server as well.
        </p>
      </>
    ),
  },
  {
    h: "Your control and your rights",
    body: (
      <>
        <ul>
          <li>Every AI output is labeled — facts, interpretation and missing information are kept separate.</li>
          <li>AI findings are reviewable and you decide whether to import them into your case.</li>
          <li>You choose the language, jurisdiction defaults, and what to upload in the first place.</li>
          <li>You can sign out at any time, and deleting your own records is always available in-app.</li>
        </ul>
        <p>
          This platform provides informational and decision-support assistance only. Nothing
          here is legal advice, and no data you store here is shared with any third party for
          marketing or advertising purposes.
        </p>
      </>
    ),
  },
];

export function PrivacyPage() {
  return (
    <div className="privacy-page">
      <div className="overline" style={{ marginBottom: 6 }}>Privacy</div>
      <h1>How Legal Case Demystifier handles your data</h1>
      <p>
        Your cases contain sensitive personal and legal material. This page explains what the
        platform stores, how documents are processed, and the control you keep over your data.
      </p>
      {SECTIONS.map((s) => (
        <section key={s.h}>
          <h2>{s.h}</h2>
          {s.body}
        </section>
      ))}
      <div className="disclaimer">
        <i className="bi bi-shield-shaded" />
        <div>
          <b>Not legal advice.</b> This application provides informational and
          decision-support assistance and is not a substitute for advice from a qualified
          legal professional.
        </div>
      </div>
      <p style={{ marginTop: 22 }}>
        <Link to="/">← Back to the home page</Link>
      </p>
    </div>
  );
}
