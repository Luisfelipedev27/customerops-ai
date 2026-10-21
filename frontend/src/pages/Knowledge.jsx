import { useWorkspace } from "../workspace";
import {
  BookOpen,
  ArrowRight,
  Plus,
  Search,
  RefreshCw,
  FileText,
} from "lucide-react";
import { Badge, Empty } from "../components/ui";
import { post } from "../api";
export default function Knowledge() {
  const {
    user,
    documents,
    busy,
    newDoc,
    setNewDoc,
    docForm,
    setDocForm,
    search,
    setSearch,
    results,
    setResults,
    perform,
  } = useWorkspace();
  return (
    <>
      <div className="knowledge-banner">
        <BookOpen size={25} />
        <div>
          <strong>Better answers start with better sources.</strong>
          <p>
            Add policy documents and playbooks. Indexing runs in the background.
          </p>
        </div>
        {user.role === "admin" && (
          <button className="primary" onClick={() => setNewDoc(!newDoc)}>
            <Plus size={16} />
            Add document
          </button>
        )}
      </div>
      {newDoc && (
        <form
          className="panel inline-form"
          onSubmit={(e) => {
            e.preventDefault();
            perform(async () => {
              await post("/documents", docForm);
              setDocForm({ title: "", content: "" });
              setNewDoc(false);
            });
          }}
        >
          <h3>New text document</h3>
          <label>
            Title
            <input
              required
              minLength={3}
              maxLength={240}
              value={docForm.title}
              onChange={(e) =>
                setDocForm({ ...docForm, title: e.target.value })
              }
            />
          </label>
          <label>
            Content
            <textarea
              required
              minLength={30}
              maxLength={100000}
              rows={8}
              value={docForm.content}
              onChange={(e) =>
                setDocForm({ ...docForm, content: e.target.value })
              }
            />
          </label>
          <button className="primary" disabled={busy}>
            Save and index
            <ArrowRight size={16} />
          </button>
        </form>
      )}
      <div className="document-grid">
        {documents.map((d) => (
          <article className="panel document" key={d.id}>
            <span className="doc-icon">
              <FileText size={25} />
            </span>
            <Badge value={d.status} />
            <h3>{d.title}</h3>
            <p>{d.chunks} indexed chunks</p>
            {d.error && <p className="error">{d.error}</p>}
            {user.role === "admin" && (
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  perform(() => post("/documents/" + d.id + "/reindex", {}))
                }
              >
                Reindex
                <RefreshCw size={14} />
              </button>
            )}
          </article>
        ))}
      </div>
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Try retrieval</h2>
            <p>See the excerpts the assistant will use as context.</p>
          </div>
        </div>
        <form
          className="knowledge-search"
          onSubmit={(e) => {
            e.preventDefault();
            perform(async () =>
              setResults(await post("/knowledge/search", { query: search })),
            );
          }}
        >
          <Search size={18} />
          <input
            required
            minLength={2}
            placeholder="E.g. what is the SLA for critical incidents?"
            aria-label="Search documents"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button className="primary" disabled={busy}>
            Search
          </button>
        </form>
        {results?.map((s) => (
          <div className="search-result" key={s.id}>
            <strong>{s.title}</strong>
            <span>{Math.round(s.score * 100)}% similarity</span>
            <p>{s.text}</p>
          </div>
        ))}
        {results?.length === 0 && <Empty text="No relevant excerpts found." />}
      </section>
    </>
  );
}
