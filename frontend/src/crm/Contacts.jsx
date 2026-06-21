import { useEffect, useState } from "react";

import { getContacts, getContactInteractions } from "./api";
import ContactsLeaderboard from "./ContactsLeaderboard";

const PAGE_SIZE = 50;

export default function Contacts() {
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [interactions, setInteractions] = useState([]);
  const [loadingInteractions, setLoadingInteractions] = useState(false);

  async function loadPage(nextOffset, append = false) {
    try {
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError("");
      const rows = await getContacts({ limit: PAGE_SIZE, offset: nextOffset });
      setHasMore(rows.length === PAGE_SIZE);
      setOffset(nextOffset + rows.length);
      setContacts((prev) => (append ? [...prev, ...rows] : rows));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load contacts.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    loadPage(0, false);
  }, []);

  async function showInteractions(contactId) {
    setSelectedId(contactId);
    setLoadingInteractions(true);
    try {
      setInteractions(await getContactInteractions(contactId));
    } catch {
      setInteractions([]);
    } finally {
      setLoadingInteractions(false);
    }
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Contacts</h2>
        <p className="text-sm text-slate-400">Auto-created from email metadata with interaction history.</p>
      </div>
      {error && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div>
          {loading ? (
            <div className="text-sm text-slate-400">Loading contacts...</div>
          ) : (
            <>
              <ContactsLeaderboard contacts={contacts} selectedId={selectedId} onSelect={showInteractions} />
              {hasMore && (
                <button
                  onClick={() => loadPage(offset, true)}
                  disabled={loadingMore}
                  className="mt-3 rounded-md border border-white/10 px-4 py-2 text-sm text-cyan-300 hover:bg-white/5 disabled:opacity-50"
                >
                  {loadingMore ? "Loading..." : "Load more contacts"}
                </button>
              )}
            </>
          )}
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <h3 className="mb-3 text-sm font-medium text-slate-300">Interaction History</h3>
          {!selectedId ? (
            <p className="text-sm text-slate-400">Select a contact to view interactions.</p>
          ) : loadingInteractions ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : interactions.length === 0 ? (
            <p className="text-sm text-slate-400">No interactions recorded.</p>
          ) : (
            interactions.map((item) => (
              <div key={item.id} className="mb-3 rounded-md bg-black/20 p-3 text-sm">
                <p className="font-medium text-slate-200">{item.subject || "Email interaction"}</p>
                <p className="text-xs text-slate-400">{item.snippet}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
