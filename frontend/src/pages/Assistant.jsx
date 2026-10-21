import { useWorkspace } from "../workspace";
import {
  Sparkles,
  ShieldCheck,
  ArrowUpRight,
  Send,
  FileText,
  CircleDot,
  Layers,
} from "lucide-react";
export default function Assistant() {
  const {
    user,
    customers,
    tickets,
    busy,
    selected,
    setSelected,
    question,
    setQuestion,
    current,
    ask,
  } = useWorkspace();
  return (
    <div className="agent-layout">
      <section className="panel chat-panel">
        <div className="chat-top">
          <div className="small-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <strong>CustomerOps Assistant</strong>
            <small>
              {user.ai_mode === "demo"
                ? "Deterministic demo · no LLM generation"
                : "LLM + tools + knowledge base"}
            </small>
          </div>
          <span className="badge ready">
            <i />
            Ready
          </span>
        </div>
        <div className="chat-body" aria-live="polite">
          {current ? (
            <>
              <div className="question-bubble">{current.question}</div>
              <div className="answer-label">
                <Sparkles size={17} />
                CUSTOMEROPS<span>{current.latency_ms} ms</span>
              </div>
              <div className="answer-text">{current.answer}</div>
              {current.sources.length > 0 && (
                <div className="sources">
                  <span className="eyebrow">RETRIEVED SOURCES</span>
                  {current.sources.map((s) => (
                    <details key={s.id}>
                      <summary>
                        <FileText size={14} />
                        {s.title}
                        <small>{Math.round(s.score * 100)}% similarity</small>
                      </summary>
                      <p>{s.text}</p>
                    </details>
                  ))}
                </div>
              )}
              <details className="execution">
                <summary>
                  <Layers size={15} />
                  Execution trace · {current.tool_calls.length} tools
                </summary>
                {current.tool_calls.map((c, i) => (
                  <div key={i}>
                    <code>{c.name}</code>
                    <pre>{JSON.stringify(c.arguments, null, 2)}</pre>
                  </div>
                ))}
              </details>
            </>
          ) : (
            <div className="chat-welcome">
              <span className="welcome-icon">
                <Sparkles size={30} />
              </span>
              <h2>What should we investigate?</h2>
              <p>
                Start with an account, a risk signal,
                <br />
                or a policy from your knowledge base.
              </p>
              {[
                "Why is Acme Corp at risk?",
                "What is the Enterprise support SLA?",
                "Propose a follow-up task for Acme Corp.",
              ].map((q) => (
                <button
                  className="suggestion"
                  key={q}
                  disabled={busy}
                  onClick={(e) => ask(e, q)}
                >
                  {q}
                  <ArrowUpRight size={16} />
                </button>
              ))}
            </div>
          )}
          {busy && (
            <p className="thinking">
              <span className="status-dot" />
              Checking tools and evidence…
            </p>
          )}
        </div>
        <form className="composer" onSubmit={ask}>
          <label className="account-select">
            CONTEXT
            <select
              aria-label="Selected customer"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
            >
              <option value="">All accounts</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <div className="input-row">
            <textarea
              aria-label="Ask the assistant"
              placeholder="Ask about an account or propose a next step…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              maxLength={4000}
              required
            />
            <button
              className="send"
              aria-label="Send question"
              disabled={busy || !question.trim()}
            >
              <Send size={19} />
            </button>
          </div>
          <small>
            <ShieldCheck size={12} /> Action proposals always require approval
            in the interface.
          </small>
        </form>
      </section>
      <aside className="agent-context">
        <div className="panel context-panel">
          <span className="eyebrow">HOW IT WORKS</span>
          <h3>From question to evidence.</h3>
          {[
            [
              "01",
              "Authorized access",
              "Only data from the authenticated organization.",
            ],
            [
              "02",
              "Retrieved sources",
              "Documents and tickets provide context for the answer.",
            ],
            [
              "03",
              "Human decision",
              "The assistant proposes. You review and approve.",
            ],
          ].map(([n, t, d]) => (
            <div className="step" key={n}>
              <span>{n}</span>
              <div>
                <strong>{t}</strong>
                <p>{d}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mode-note">
          <CircleDot size={18} />
          <div>
            <strong>
              {user.ai_mode === "demo" ? "Demo mode" : "Live LLM mode"}
            </strong>
            <p>
              {user.ai_mode === "demo"
                ? "Responses follow deterministic rules. Search uses demo lexical vectors, not semantic embeddings."
                : "Responses are generated by the configured model. Always review the evidence."}
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}
