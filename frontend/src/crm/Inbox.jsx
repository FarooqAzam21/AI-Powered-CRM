import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getEmails, startEmailSync } from "./api";
import EmailDetail from "./EmailDetail";
import EmailListVirtualized from "./EmailListVirtualized";
import { utcTime } from "./time";

const PAGE_SIZE = 20;

export default function Inbox() {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selected, setSelected] = useState(null);
  const [taskId, setTaskId] = useState("");
  const [syncResult, setSyncResult] = useState(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const loadPage = useCallback(async (nextOffset, append = false) => {
    try {
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError("");
      const rows = await getEmails({ limit: PAGE_SIZE, offset: nextOffset, q: debouncedSearch || undefined });
      setHasMore(rows.length === PAGE_SIZE);
      setOffset(nextOffset + rows.length);
      const sortedRows = [...rows].sort((a, b) => utcTime(b.internal_date) - utcTime(a.internal_date));
      setEmails((prev) => (append ? [...prev, ...rows].sort((a, b) => utcTime(b.internal_date) - utcTime(a.internal_date)) : sortedRows));
      if (!append) setSelected(sortedRows[0] || null);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load emails.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [debouncedSearch]);

  useEffect(() => {
    loadPage(0, false);
  }, [loadPage]);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  async function refresh() {
    await loadPage(0, false);
  }

  const loadMore = useCallback(async () => {
    if (!hasMore || loadingMore) return;
    await loadPage(offset, true);
  }, [hasMore, loadPage, loadingMore, offset]);

  const statusText = useMemo(() => {
    if (loading) return "Loading first 20 emails...";
    if (emails.length === 0) return "No emails found";
    return `${emails.length}${hasMore ? "+" : ""} emails loaded`;
  }, [emails.length, hasMore, loading]);

  async function sync() {
    const task = await startEmailSync();
    setTaskId(task.task_id);
    setSyncResult(task.result || null);
    window.setTimeout(() => loadPage(0, false), 1200);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Inbox</h2>
          <p className="text-sm text-slate-400">Metadata-first sync. {statusText}.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="h-10 min-w-64 rounded-md border border-white/10 bg-slate-950 px-3 text-sm text-slate-100 outline-none focus:border-cyan-400/60"
            placeholder="Search sender, subject, or preview"
          />
          <button onClick={refresh} className="rounded-md border border-white/10 p-2 text-slate-300 hover:bg-white/5" title="Refresh">
            <RefreshCw size={18} />
          </button>
          <button onClick={sync} className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-300">
            Sync Gmail
          </button>
        </div>
      </div>
      {taskId && (
        <div className="rounded-md border border-cyan-400/20 bg-cyan-400/10 p-3 text-sm text-cyan-100">
          <p>Sync task: {taskId}</p>
          {syncResult && (
            <p className="mt-1 text-xs text-cyan-200/80">
              Gmail returned {syncResult.seen ?? 0} recent messages
              {syncResult.newest_subject ? `; newest: ${syncResult.newest_subject}` : ""}
              {syncResult.newest_seen ? ` (${syncResult.newest_seen} UTC)` : ""}.
            </p>
          )}
        </div>
      )}
      {error && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>}
      <div className="grid overflow-hidden rounded-lg border border-white/10 bg-white/[0.03] lg:grid-cols-[420px_1fr]">
        {loading ? (
          <EmailListSkeleton />
        ) : (
          <div className="flex h-[610px] flex-col">
            {emails.length === 0 ? (
              <div className="h-[610px] border-r border-white/10 p-4 text-sm text-slate-400">No matching emails.</div>
            ) : (
              <EmailListVirtualized
                emails={emails}
                selectedId={selected?.gmail_message_id}
                onSelect={setSelected}
                onEndReached={loadMore}
                hasMore={hasMore}
                loadingMore={loadingMore}
              />
            )}
          </div>
        )}
        <EmailDetail email={selected} onTask={setTaskId} />
      </div>
    </section>
  );
}

function EmailListSkeleton() {
  return (
    <div className="h-[610px] space-y-3 border-r border-white/10 p-4">
      {Array.from({ length: 8 }).map((_, index) => (
        <div key={index} className="h-[64px] animate-pulse rounded-md bg-white/[0.06] p-3">
          <div className="mb-3 h-3 w-2/3 rounded bg-white/10" />
          <div className="h-3 w-full rounded bg-white/10" />
        </div>
      ))}
    </div>
  );
}
