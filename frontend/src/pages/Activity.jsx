import { useWorkspace } from "../workspace";
import { Sparkles, ChevronRight, Check } from "lucide-react";
import { Badge, Empty, date } from "../components/ui";
export default function Activity() {
  const { user, runs, tasks, metrics, question, setCurrent, customerName, go } =
    useWorkspace();
  return (
    <>
      <div className="stat-grid three">
        {[
          ["Investigations", metrics.runs || 0],
          ["Average latency", `${metrics.avg_latency_ms || 0} ms`],
          ["Generation tokens", metrics.tokens || 0],
        ].map(([label, value]) => (
          <div className="stat" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>
              {user.ai_mode === "demo"
                ? "Demo mode · no LLM usage"
                : "Runs for your organization"}
            </small>
          </div>
        ))}
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Run history</h2>
            <p>Tools, sources, and status for every investigation.</p>
          </div>
          <span className="muted">
            Estimated cost:{" "}
            {user.cost_configured
              ? `US$ ${(metrics.estimated_cost || 0).toFixed(4)}`
              : "rates not configured"}
          </span>
        </div>
        {runs.length ? (
          runs.map((r) => (
            <button
              className="list-row row-button"
              key={r.id}
              onClick={() => {
                setCurrent(r);
                go("agent");
              }}
            >
              <span className="small-icon">
                <Sparkles size={18} />
              </span>
              <div>
                <strong>{r.question}</strong>
                <small>
                  {date(r.created_at)} · {r.mode} · {r.tool_calls.length} tools
                  · {r.latency_ms} ms
                </small>
              </div>
              <Badge value={r.status} />
              <ChevronRight size={17} />
            </button>
          ))
        ) : (
          <Empty text="No investigations yet." />
        )}
      </section>
      <section className="panel ticket-panel">
        <div className="section-heading">
          <h2>Tasks created in the local CRM</h2>
        </div>
        {tasks.length ? (
          tasks.map((t) => (
            <div className="list-row" key={t.id}>
              <span className="small-icon">
                <Check size={18} />
              </span>
              <div>
                <strong>{t.title}</strong>
                <small>
                  {customerName(t.customer_id)} · Created after approval
                </small>
              </div>
            </div>
          ))
        ) : (
          <Empty text="No tasks have been executed." />
        )}
      </section>
    </>
  );
}
