import { useState, useEffect, useCallback, useRef } from "react";
import { api, post } from "./api";
import { Badge, Empty, money } from "./components/ui";
import Login from "./components/Login";
import { WorkspaceContext } from "./workspace";
import {
  LayoutDashboard,
  Sparkles,
  Users,
  BookOpen,
  ShieldCheck,
  Activity,
  ArrowUpRight,
  LogOut,
  ChevronRight,
  X,
  RefreshCw,
  Layers,
  Menu,
} from "lucide-react";
import Overview from "./pages/Overview";
import Assistant from "./pages/Assistant";
import Customers from "./pages/Customers";
import Knowledge from "./pages/Knowledge";
import Approvals from "./pages/Approvals";
import ActivityPage from "./pages/Activity";
const NAV = [
  ["overview", "Overview", LayoutDashboard],
  ["agent", "Assistant", Sparkles],
  ["customers", "Customers", Users],
  ["knowledge", "Knowledge", BookOpen],
  ["approvals", "Approvals", ShieldCheck],
  ["activity", "Activity", Activity],
];
export default function App() {
  const [user, setUser] = useState(null),
    [loading, setLoading] = useState(true),
    [page, setPage] = useState("overview");
  const [customers, setCustomers] = useState([]),
    [tickets, setTickets] = useState([]),
    [documents, setDocuments] = useState([]),
    [actions, setActions] = useState([]),
    [runs, setRuns] = useState([]),
    [tasks, setTasks] = useState([]),
    [metrics, setMetrics] = useState({});
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [mobile, setMobile] = useState(false),
    [filter, setFilter] = useState("");
  const [question, setQuestion] = useState(""),
    [selected, setSelected] = useState(""),
    [current, setCurrent] = useState(null),
    [newDoc, setNewDoc] = useState(false),
    [docForm, setDocForm] = useState({ title: "", content: "" });
  const [newCustomer, setNewCustomer] = useState(false),
    [customerForm, setCustomerForm] = useState({
      name: "",
      contact: "",
      external_id: "",
      plan: "Enterprise",
      mrr: 0,
      usage_change: 0,
    });
  const [newTicket, setNewTicket] = useState(false),
    [ticketForm, setTicketForm] = useState({
      customer_id: "",
      title: "",
      body: "",
      priority: "normal",
    });
  const [search, setSearch] = useState(""),
    [results, setResults] = useState(null);
  useEffect(() => {
    api("/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);
  const sessionEpoch = useRef(0);
  const refreshVersion = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++refreshVersion.current;
    const data = await Promise.all(
      [
        "/customers",
        "/tickets",
        "/documents",
        "/actions",
        "/runs",
        "/crm/tasks",
        "/metrics",
      ].map((p) => api(p)),
    );
    if (version !== refreshVersion.current) return;
    setCustomers(data[0]);
    setTickets(data[1]);
    setDocuments(data[2]);
    setActions(data[3]);
    setRuns(data[4]);
    setTasks(data[5]);
    setMetrics(data[6]);
  }, []);
  useEffect(() => {
    if (user) refresh().catch((e) => setError(e.message));
  }, [user, refresh]);
  const hasPendingDocuments = documents.some((d) => d.status === "pending");
  useEffect(() => {
    if (!user || !hasPendingDocuments) return;
    const id = setInterval(() => refresh().catch(() => {}), 4000);
    return () => clearInterval(id);
  }, [user, hasPendingDocuments, refresh]);
  function resetWorkspace() {
    sessionEpoch.current += 1;
    refreshVersion.current += 1;
    setCustomers([]);
    setTickets([]);
    setDocuments([]);
    setActions([]);
    setRuns([]);
    setTasks([]);
    setMetrics({});
    setCurrent(null);
    setSelected("");
    setQuestion("");
    setResults(null);
    setSearch("");
    setFilter("");
    setError("");
    setPage("overview");
    setDocForm({ title: "", content: "" });
    setNewDoc(false);
    setNewCustomer(false);
    setNewTicket(false);
    setCustomerForm({
      name: "",
      contact: "",
      external_id: "",
      plan: "Enterprise",
      mrr: 0,
      usage_change: 0,
    });
    setTicketForm({ customer_id: "", title: "", body: "", priority: "normal" });
  }
  function handleLogin(nextUser) {
    resetWorkspace();
    setUser(nextUser);
  }
  async function handleLogout() {
    setBusy(true);
    try {
      await post("/auth/logout", {});
      resetWorkspace();
      setUser(null);
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }
  function go(p) {
    setPage(p);
    setMobile(false);
    setError("");
    setFilter("");
  }
  async function perform(fn) {
    setError("");
    setBusy(true);
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function ask(e, preset) {
    e?.preventDefault();
    const q = preset || question;
    if (!q.trim()) return;
    setPage("agent");
    setError("");
    setBusy(true);
    const epoch = sessionEpoch.current;
    try {
      const result = await post("/chat", {
        question: q,
        customer_id: selected || null,
      });
      if (epoch !== sessionEpoch.current) return;
      setCurrent(result);
      setQuestion("");
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const pending = actions.filter((a) => a.status === "pending");
  const customerName = (id) =>
    customers.find((c) => c.id === id)?.name || "Customer";
  function investigate(c) {
    setSelected(c.id);
    setQuestion(
      `Why is ${c.name} at risk? Check its tickets and the knowledge base.`,
    );
    go("agent");
  }
  function accountTable(items) {
    return (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>CUSTOMER</th>
              <th>ACCOUNT HEALTH</th>
              <th>USAGE</th>
              <th>OPEN TICKETS</th>
              <th>MRR</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((c, i) => (
              <tr key={c.id}>
                <td>
                  <div className="account">
                    <span className={"avatar tone" + (i % 4)}>
                      {c.name
                        .split(" ")
                        .map((s) => s[0])
                        .slice(0, 2)
                        .join("")}
                    </span>
                    <div>
                      <strong>{c.name}</strong>
                      <small>{c.plan}</small>
                    </div>
                  </div>
                </td>
                <td>
                  <Badge value={c.risk} />
                </td>
                <td>
                  <span
                    className={c.usage_change < 0 ? "negative" : "positive"}
                  >
                    {c.usage_change > 0 ? "+" : ""}
                    {c.usage_change}%
                  </span>
                </td>
                <td>
                  {c.open_tickets}
                  <small className="inline-muted">
                    {c.critical_tickets
                      ? ` / ${c.critical_tickets} critical`
                      : ""}
                  </small>
                </td>
                <td>{money(c.mrr)}</td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={"Investigate " + c.name}
                    onClick={() => investigate(c)}
                  >
                    <ArrowUpRight size={19} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!items.length && <Empty text="Nenhum cliente encontrado." />}
      </div>
    );
  }
  if (loading) return <div className="empty">Loading workspace…</div>;
  if (!user) return <Login onLogin={handleLogin} />;
  return (
    <WorkspaceContext.Provider
      value={{
        user,
        customers,
        tickets,
        documents,
        actions,
        runs,
        tasks,
        metrics,
        busy,
        selected,
        setSelected,
        question,
        setQuestion,
        current,
        setCurrent,
        filter,
        setFilter,
        newDoc,
        setNewDoc,
        docForm,
        setDocForm,
        newCustomer,
        setNewCustomer,
        customerForm,
        setCustomerForm,
        newTicket,
        setNewTicket,
        ticketForm,
        setTicketForm,
        search,
        setSearch,
        results,
        setResults,
        pending,
        customerName,
        go,
        perform,
        ask,
        accountTable,
      }}
    >
      <div className="shell">
        <aside className={mobile ? "sidebar visible" : "sidebar"}>
          <a
            className="brand"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              go("overview");
            }}
          >
            <span className="brand-icon">
              <Layers size={20} />
            </span>
            customerops<span className="brand-ai">AI</span>
          </a>
          <div className="workspace">
            <span className="workspace-mark">
              {user.tenant_name?.[0] || "W"}
            </span>
            <div>
              <strong>{user.tenant_name || "Workspace"}</strong>
              <small>Customer operations</small>
            </div>
            <ChevronRight size={16} />
          </div>
          <div className="nav-label">WORKSPACE</div>
          <nav>
            {NAV.map(([id, label, Icon]) => (
              <button
                key={id}
                className={page === id ? "nav active" : "nav"}
                onClick={() => go(id)}
              >
                <Icon size={19} />
                {label}
                {id === "approvals" && pending.length > 0 && (
                  <span className="nav-count">{pending.length}</span>
                )}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="system-status">
              <span className="status-dot" />{" "}
              {user.ai_mode === "demo" ? "Local demo" : "LLM connected"}
              <small>
                {user.ai_mode === "demo"
                  ? "Deterministic workflow · no AI API"
                  : user.model}
              </small>
            </div>
            <div className="profile">
              <span className="profile-avatar">
                {user.role === "admin" ? "AD" : "AN"}
              </span>
              <div>
                <strong>
                  {user.role === "admin" ? "Administrator" : "Analyst"}
                </strong>
                <small>{user.email}</small>
              </div>
              <button
                className="icon-button"
                aria-label="Sign out"
                onClick={handleLogout}
              >
                <LogOut size={17} />
              </button>
            </div>
          </div>
        </aside>
        <div className="main">
          <header className="topbar">
            <button
              className="icon-button mobile-menu"
              aria-label="Open menu"
              onClick={() => setMobile(!mobile)}
            >
              <Menu />
            </button>
            <div className="breadcrumb">
              Workspace <ChevronRight size={14} />{" "}
              <span>{NAV.find((n) => n[0] === page)?.[1]}</span>
            </div>
            <div className="topbar-right">
              <span className="demo-tag">
                {user.ai_mode === "demo"
                  ? "FICTIONAL DATA · DEMO MODE"
                  : "FICTIONAL DATA · LIVE LLM"}
              </span>
              <a href="/docs" target="_blank" rel="noreferrer">
                API docs <ArrowUpRight size={14} />
              </a>
            </div>
          </header>
          <main className="content">
            <div className="page-heading">
              <div>
                <div className="eyebrow">CUSTOMER OPERATIONS</div>
                <h1>
                  {
                    {
                      overview: "Your operations, in perspective.",
                      agent: "Context for better decisions.",
                      customers: "Every account tells a story.",
                      knowledge: "Knowledge that becomes context.",
                      approvals: "You have the final say.",
                      activity: "An operation you can trace.",
                    }[page]
                  }
                </h1>
                <p className="muted">
                  {
                    {
                      overview:
                        "Key signals, connected evidence, and clear next steps.",
                      agent:
                        "Investigate accounts and find answers backed by data and sources.",
                      customers:
                        "Track customer health and investigate signs of risk.",
                      knowledge:
                        "Internal documents to support answers with sources.",
                      approvals:
                        "Review proposals before any task is created in the local CRM.",
                      activity: "Review runs, tools used, and tasks created.",
                    }[page]
                  }
                </p>
              </div>
              <button
                className="secondary refresh"
                onClick={() => perform(refresh)}
                disabled={busy}
              >
                <RefreshCw size={15} />
                Refresh
              </button>
            </div>
            {error && (
              <div role="alert" className="error-banner">
                {error}
                <button
                  className="icon-button"
                  aria-label="Dismiss error"
                  onClick={() => setError("")}
                >
                  <X size={16} />
                </button>
              </div>
            )}
            {page === "overview" && <Overview />}
            {page === "agent" && <Assistant />}
            {page === "customers" && <Customers />}
            {page === "knowledge" && <Knowledge />}
            {page === "approvals" && <Approvals />}
            {page === "activity" && <ActivityPage />}
            <footer>
              <span>CustomerOps AI</span>
              <span>Connected context. Human control.</span>
              <small>Portfolio project · Fictional data</small>
            </footer>
          </main>
        </div>
      </div>
    </WorkspaceContext.Provider>
  );
}
