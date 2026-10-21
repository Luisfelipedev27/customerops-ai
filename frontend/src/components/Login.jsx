import { useState } from "react";
import { Layers, ShieldCheck, ArrowRight, CircleDot } from "lucide-react";
import { api, post } from "../api";
const TENANT = "11111111-1111-4111-8111-111111111111";
export default function Login({ onLogin }) {
  const [form, setForm] = useState({
    tenant_id: TENANT,
    email: "admin@customerops.local",
    password: "",
  });
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await post("/auth/login", form);
      onLogin(await api("/me"));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <section className="login-story">
        <div className="brand">
          <span className="brand-icon">
            <Layers />
          </span>
          customerops<span className="brand-ai">AI</span>
        </div>
        <div>
          <span className="eyebrow">CUSTOMER INTELLIGENCE, CONNECTED</span>
          <h1>
            Fewer tabs.
            <br />
            More context.
            <br />
            <em>Better decisions.</em>
          </h1>
          <p>
            Connect customers, support, and knowledge in one operation with
            evidence and stay in control of every action.
          </p>
          <div className="login-proof">
            <ShieldCheck size={18} /> Human approval · Traceable sources
          </div>
        </div>
        <small>CustomerOps AI / Demo project</small>
      </section>
      <section className="login-panel">
        <form onSubmit={submit}>
          <span className="eyebrow">YOUR WORKSPACE</span>
          <h2>Welcome back.</h2>
          <p className="muted">Sign in to monitor your accounts.</p>
          <label>
            Organization
            <input
              required
              value={form.tenant_id}
              onChange={(e) => setForm({ ...form, tenant_id: e.target.value })}
            />
          </label>
          <label>
            Email
            <input
              type="email"
              autoComplete="username"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </label>
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
          <button className="primary wide" disabled={busy}>
            {busy ? "Signing in…" : "Sign in to workspace"}
            <ArrowRight size={18} />
          </button>
          <div className="login-note">
            <CircleDot size={16} />
            <span>
              Local environment with fictional data. Your password is configured
              in DEMO_PASSWORD in the .env file.
            </span>
          </div>
        </form>
      </section>
    </main>
  );
}
