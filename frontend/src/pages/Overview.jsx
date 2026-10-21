import { useWorkspace } from "../workspace";
import {
  Sparkles,
  Users,
  BookOpen,
  ShieldCheck,
  Activity,
  ArrowRight,
  ChevronRight,
  CircleDot,
} from "lucide-react";
import { Empty, date } from "../components/ui";
export default function Overview() {
  const {
    customers,
    tickets,
    runs,
    metrics,
    question,
    setQuestion,
    setCurrent,
    pending,
    customerName,
    go,
    accountTable,
  } = useWorkspace();
  return (
    <>
      <div className="stat-grid">
        {[
          [
            "Monitored accounts",
            metrics.customers || 0,
            "Consolidated view",
            Users,
          ],
          [
            "High-risk accounts",
            metrics.at_risk || 0,
            "Priority follow-up",
            Activity,
          ],
          [
            "Open tickets",
            metrics.open_tickets || 0,
            "Context to take action",
            CircleDot,
          ],
          [
            "Actions to review",
            metrics.pending_actions || 0,
            "Human approval required",
            ShieldCheck,
          ],
        ].map(([label, value, note, Icon], i) => (
          <div className="stat" key={label}>
            <div>
              <span>{label}</span>
              <Icon size={18} />
            </div>
            <strong className={i === 1 ? "warm" : ""}>
              {value.toString().padStart(2, "0")}
            </strong>
            <small>{note}</small>
          </div>
        ))}
      </div>
      <div className="spotlight">
        <div className="spotlight-copy">
          <span className="eyebrow">
            <Sparkles size={14} /> INTELLIGENCE WITH CONTEXT
          </span>
          <h2>
            One question.
            <br />
            The complete account picture.
          </h2>
          <p>
            Connect CRM signals, support tickets, and internal documents to
            understand what needs attention.
          </p>
          <button
            className="primary"
            onClick={() => {
              go("agent");
              setQuestion("Why is Acme Corp at risk?");
            }}
          >
            Investigate with the assistant
            <ArrowRight size={17} />
          </button>
        </div>
        <div className="signal-map">
          <div className="signal-card signal-one">
            <Users size={18} />
            <div>
              <strong>CRM</strong>
              <small>Customers and product usage</small>
            </div>
            <span className="status-dot" />
          </div>
          <div className="signal-card signal-two">
            <CircleDot size={18} />
            <div>
              <strong>Support</strong>
              <small>Tickets and incidents</small>
            </div>
            <span className="status-dot" />
          </div>
          <div className="signal-card signal-three">
            <BookOpen size={18} />
            <div>
              <strong>Knowledge</strong>
              <small>Playbooks and policies</small>
            </div>
            <span className="status-dot" />
          </div>
          <div className="signal-core">
            <Sparkles size={28} />
          </div>
          <small className="signal-caption">
            Connected evidence. Human decisions.
          </small>
        </div>
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Accounts that need attention</h2>
            <p>Rule-based indicator: critical tickets and changes in usage.</p>
          </div>
          <button className="text-button" onClick={() => go("customers")}>
            View all accounts
            <ArrowRight size={15} />
          </button>
        </div>
        {accountTable(
          [...customers].sort((a, b) => b.risk_score - a.risk_score),
        )}
      </section>
      <div className="bottom-grid">
        <section className="panel">
          <div className="section-heading">
            <h2>Next actions</h2>
            <ShieldCheck size={19} />
          </div>
          {pending.length ? (
            pending.slice(0, 3).map((a) => (
              <div className="list-row" key={a.id}>
                <span className="small-icon amber">
                  <ShieldCheck size={18} />
                </span>
                <div>
                  <strong>{a.title}</strong>
                  <small>
                    {customerName(a.customer_id)} · Awaiting approval
                  </small>
                </div>
                <button className="text-button" onClick={() => go("approvals")}>
                  Review
                  <ChevronRight size={15} />
                </button>
              </div>
            ))
          ) : (
            <Empty text="No pending actions. Ask the assistant to propose a follow-up." />
          )}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>Recent investigations</h2>
            <Activity size={19} />
          </div>
          {runs.length ? (
            runs.slice(0, 3).map((r) => (
              <button
                className="list-row row-button"
                key={r.id}
                onClick={() => {
                  setCurrent(r);
                  go("agent");
                }}
              >
                <span className="small-icon">
                  <Sparkles size={17} />
                </span>
                <div>
                  <strong>{r.question}</strong>
                  <small>
                    {r.tool_calls.length} tools · {date(r.created_at)}
                  </small>
                </div>
                <ChevronRight size={16} />
              </button>
            ))
          ) : (
            <Empty text="Your investigations will appear here." />
          )}
        </section>
      </div>
    </>
  );
}
