import { useWorkspace } from "../workspace";
import { Plus, Search, Check, CircleDot } from "lucide-react";
import { Badge } from "../components/ui";
import { api, post } from "../api";
export default function Customers() {
  const {
    user,
    customers,
    tickets,
    busy,
    filter,
    setFilter,
    newCustomer,
    setNewCustomer,
    customerForm,
    setCustomerForm,
    newTicket,
    setNewTicket,
    ticketForm,
    setTicketForm,
    search,
    customerName,
    perform,
    accountTable,
  } = useWorkspace();
  return (
    <>
      <section className="panel">
        <div className="section-heading">
          <div className="search-field">
            <Search size={17} />
            <input
              aria-label="Search customers"
              placeholder="Search customers…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          {user.role === "admin" && (
            <button
              className="primary"
              onClick={() => setNewCustomer(!newCustomer)}
            >
              <Plus size={16} />
              New customer
            </button>
          )}
        </div>
        {newCustomer && (
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              perform(async () => {
                await post("/customers", customerForm);
                setNewCustomer(false);
              });
            }}
          >
            <h3>Create customer</h3>
            {[
              ["name", "Name"],
              ["external_id", "External ID"],
              ["contact", "Contact email"],
            ].map(([k, l]) => (
              <label key={k}>
                {l}
                <input
                  required
                  value={customerForm[k]}
                  onChange={(e) =>
                    setCustomerForm({ ...customerForm, [k]: e.target.value })
                  }
                />
              </label>
            ))}
            <label>
              MRR in USD
              <input
                type="number"
                min="0"
                value={customerForm.mrr}
                onChange={(e) =>
                  setCustomerForm({
                    ...customerForm,
                    mrr: Number(e.target.value),
                  })
                }
              />
            </label>
            <button className="primary" disabled={busy}>
              Save customer
            </button>
          </form>
        )}
        {accountTable(
          customers.filter((c) =>
            c.name.toLowerCase().includes(filter.toLowerCase()),
          ),
        )}
      </section>
      <section className="panel ticket-panel">
        <div className="section-heading">
          <div>
            <h2>Support tickets</h2>
            <p>Customer incidents and requests.</p>
          </div>
          <button
            className="secondary"
            onClick={() => setNewTicket(!newTicket)}
          >
            <Plus size={16} />
            New ticket
          </button>
        </div>
        {newTicket && (
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              perform(async () => {
                await post("/tickets", ticketForm);
                setNewTicket(false);
              });
            }}
          >
            <label>
              Customer
              <select
                required
                value={ticketForm.customer_id}
                onChange={(e) =>
                  setTicketForm({ ...ticketForm, customer_id: e.target.value })
                }
              >
                <option value="">Select</option>
                {customers.map((c) => (
                  <option value={c.id} key={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Title
              <input
                required
                value={ticketForm.title}
                onChange={(e) =>
                  setTicketForm({ ...ticketForm, title: e.target.value })
                }
              />
            </label>
            <label>
              Description
              <textarea
                required
                value={ticketForm.body}
                onChange={(e) =>
                  setTicketForm({ ...ticketForm, body: e.target.value })
                }
              />
            </label>
            <label>
              Priority
              <select
                value={ticketForm.priority}
                onChange={(e) =>
                  setTicketForm({ ...ticketForm, priority: e.target.value })
                }
              >
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            <button className="primary" disabled={busy}>
              Create ticket
            </button>
          </form>
        )}
        {tickets.map((t) => (
          <div className="list-row" key={t.id}>
            <span
              className={
                "small-icon " + (t.priority === "critical" ? "amber" : "")
              }
            >
              <CircleDot size={17} />
            </span>
            <div>
              <strong>{t.title}</strong>
              <small>
                {customerName(t.customer_id)} ·{" "}
                {t.priority === "critical" ? "Critical" : t.priority}
              </small>
            </div>
            <Badge value={t.status} />
            {t.status !== "resolved" && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  perform(() =>
                    api("/tickets/" + t.id, {
                      method: "PATCH",
                      body: JSON.stringify({ status: "resolved" }),
                    }),
                  )
                }
              >
                Resolve
                <Check size={15} />
              </button>
            )}
          </div>
        ))}
      </section>
    </>
  );
}
