import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AuthPanel } from "./auth/AuthPanel";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <AuthPanel />
      <div className="auth-card-wrap">
        <div className="auth-card">
          <h1>Welcome back</h1>
          <p className="sub">Sign in to continue working on your cases.</p>
          <form onSubmit={submit}>
            <div className="form-row">
              <div>
                <label className="form-label" htmlFor="li-email">Email</label>
                <input id="li-email" type="email" className="form-control" required
                       value={email} onChange={(e) => setEmail(e.target.value)}
                       placeholder="you@example.com" />
              </div>
            </div>
            <div className="form-row">
              <div>
                <label className="form-label" htmlFor="li-pass">Password</label>
                <input id="li-pass" type="password" className="form-control" required
                       value={password} onChange={(e) => setPassword(e.target.value)}
                       placeholder="••••••••" />
              </div>
            </div>
            {error && <div className="alert-box error">{error}</div>}
            <button className="btn btn-primary btn-lg" style={{ width: "100%" }} disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="text-soft" style={{ marginTop: 16, fontSize: 13.5 }}>
            New here? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}