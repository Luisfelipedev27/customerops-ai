import { useWorkspace } from "../workspace";
import { ShieldCheck, Check, X } from "lucide-react";
import { Badge, Empty, date } from "../components/ui";
import { post } from "../api";
export default function Approvals() {
  const { user, actions, busy, pending, customerName, perform } =
    useWorkspace();
  return (
    <>
      <div className="approval-note">
        <ShieldCheck size={21} />
        <p>
          <strong>Human control by default.</strong> Approving creates a task
          only in the local demo CRM. Repeating an approval will not duplicate
          the task.
        </p>
      </div>
      {!actions.length ? (
        <section className="panel">
          <Empty text="No proposals yet. Ask the assistant to propose a task." />
        </section>
      ) : (
        actions.map((a) => (
          <article className="panel approval-card" key={a.id}>
            <div className="approval-icon">
              <ShieldCheck size={23} />
            </div>
            <div className="approval-content">
              <div className="approval-meta">
                <span>{customerName(a.customer_id)}</span>
                <small>{date(a.created_at)}</small>
              </div>
              <h3>{a.title}</h3>
              <p>Create a follow-up task in the local CRM</p>
              <Badge value={a.status} />
            </div>
            {a.status === "pending" && user.role === "admin" && (
              <div className="approval-buttons">
                <button
                  className="secondary"
                  disabled={busy}
                  onClick={() =>
                    perform(() =>
                      post("/actions/" + a.id + "/decision", {
                        decision: "reject",
                      }),
                    )
                  }
                >
                  <X size={16} />
                  Reject
                </button>
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    perform(() =>
                      post("/actions/" + a.id + "/decision", {
                        decision: "approve",
                      }),
                    )
                  }
                >
                  <Check size={16} />
                  Approve task
                </button>
              </div>
            )}
            {a.status === "pending" && user.role !== "admin" && (
              <small>Only administrators can approve or reject actions.</small>
            )}
          </article>
        ))
      )}
    </>
  );
}
