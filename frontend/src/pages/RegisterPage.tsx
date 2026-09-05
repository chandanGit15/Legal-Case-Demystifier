import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AuthPanel } from "./auth/AuthPanel";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(name, email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <AuthPanel />
      <div className="auth-card-wrap">
        <div className="auth-card">
          <h1>Create your workspace</h1>
          <p className="sub">Organize cases, documents, risks and action plans — with AI guidance at every step.</p>
          <form onSubmit={submit}>
            <div className="form-row">
              <div>
                <label className="form-label" htmlFor="rg-name">Full name</label>
                <input id="rg-name" className="form-control" required value={name}
                       onChange={(e) => setName(e.target.value)} placeholder="Alex Morgan" />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="form-label" htmlFor="rg-email">Email</label>
                <input id="rg-email" type="email" className="form-control" required value={email}
                       onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="form-label" htmlFor="rg-pass">Password</label>
                <input id="rg-pass" type="password" className="form-control" required minLength={8}
                       value={password} onChange={(e) => setPassword(e.target.value)}
                       placeholder="At least 8 characters" />
              </div>
            </div>
            {error && <div className="alert-box error">{error}</div>}
            <button className="btn btn-primary btn-lg" style={{ width: "100%" }} disabled={busy}>
              {busy ? "Creating account…" : "Create account"}
            </button>
          </form>
          <p className="text-soft" style={{ marginTop: 16, fontSize: 13.5 }}>
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}