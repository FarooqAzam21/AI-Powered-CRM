import { RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { getEmails, startEmailSync } from "./api";
import EmailDetail from "./EmailDetail";
import EmailListVirtualized from "./EmailListVirtualized";

const PAGE_SIZE = 40;

export default function Inbox() {
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selected, setSelected] = useState(null);
  const [taskId, setTaskId] = useState("");

  const loadPage = useCallback(async (nextOffset, append = false) => {
    try {
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError("");
      const rows = await getEmails({ limit: PAGE_SIZE, offset: nextOffset });
      setHasMore(rows.length === PAGE_SIZE);
      setOffset(nextOffset + rows.length);
      setEmails((prev) => (append ? [...prev, ...rows] : rows));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load emails.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    loadPage(0, false);
  }, [loadPage]);

  async function refresh() {
    await loadPage(0, false);
  }

  async function loadMore() {
    if (!hasMore || loadingMore) return;
    await loadPage(offset, true);
  }

  async function sync() {
    const task = await startEmailSync();
    setTaskId(task.task_id);
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Inbox</h2>
          <p className="text-sm text-slate-400">Metadata-first sync. Bodies load only when selected.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="rounded-md border border-white/10 p-2 text-slate-300 hover:bg-white/5" title="Refresh">
            <RefreshCw size={18} />
          </button>
          <button onClick={sync} className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-300">
            Sync Gmail
          </button>
        </div>
      </div>
      {taskId && <div className="rounded-md border border-cyan-400/20 bg-cyan-400/10 p-3 text-sm text-cyan-100">Queued task: {taskId}</div>}
      {error && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>}
      <div className="grid overflow-hidden rounded-lg border border-white/10 bg-white/[0.03] lg:grid-cols-[420px_1fr]">
        {loading ? (
          <div className="h-[610px] p-4 text-sm text-slate-400">Loading metadata...</div>
        ) : (
          <div className="flex h-[610px] flex-col">
            <EmailListVirtualized emails={emails} selectedId={selected?.gmail_message_id} onSelect={setSelected} />
            {hasMore && (
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="border-t border-white/10 px-4 py-3 text-sm text-cyan-300 hover:bg-white/5 disabled:opacity-50"
              >
                {loadingMore ? "Loading..." : "Load more emails"}
              </button>
            )}
          </div>
        )}
        <EmailDetail email={selected} onTask={setTaskId} />
      </div>
    </section>
  );
}
