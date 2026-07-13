import { useCallback, useEffect, useMemo, useState } from "react";
import { Bot, Cpu, Mail, RefreshCw, Sparkles } from "lucide-react";

import {
  classifyEmail,
  classifySyncedEmail,
  classifySyncedEmails,
  generateReply,
  getAIHealth,
  getAIStats,
  getCeleryHealth,
  getEmails,
  getTask,
  getTaskStatus,
  getEmailContext,
  manuallyClassifySyncedEmail,
  searchEmails,
  triggerGmailSync,
} from "./api";
import useApiResource from "./useApiResource";
import { formatPktDateTime, utcTime } from "./time";

const PAGE_SIZE = 20;

export default function AITasks() {
  const health = useApiResource(getAIHealth, []);
  const stats = useApiResource(getAIStats, []);
  const celery = useApiResource(getCeleryHealth, []);

  const [taskId, setTaskId] = useState("");
  const [task, setTask] = useState(null);
  const [selectedEmailId, setSelectedEmailId] = useState("");
  const [manualCategory, setManualCategory] = useState("Job");
  const [classifyForm, setClassifyForm] = useState({ subject: "", body: "" });
  const [classifyResult, setClassifyResult] = useState(null);
  const [replyForm, setReplyForm] = useState({ subject: "", body: "", tone: "professional" });
  const [replyResult, setReplyResult] = useState(null);
  const [busy, setBusy] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [emails, setEmails] = useState([]);
  const [emailsLoading, setEmailsLoading] = useState(true);
  const [emailsError, setEmailsError] = useState("");
  const [emailsOffset, setEmailsOffset] = useState(0);
  const [emailsHasMore, setEmailsHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedEmailContext, setSelectedEmailContext] = useState(null);
  const [selectedEmailLoading, setSelectedEmailLoading] = useState(false);

  async function lookup() {
    try {
      setTask(await getTaskStatus(taskId));
    } catch {
      setTask(await getTask(taskId));
    }
  }

  async function runClassify() {
    setBusy("classify");
    try {
      setClassifyResult(await classifyEmail(classifyForm));
    } finally {
      setBusy("");
    }
  }

  async function runSync() {
    setBusy("sync");
    try {
      const res = await triggerGmailSync();
      setTaskId(res.task_id);
      setTask(res);
    } finally {
      setBusy("");
    }
  }

  const selectedEmail = useMemo(
    () => emails.find((email) => email.gmail_message_id === selectedEmailId) || emails[0] || null,
    [emails, selectedEmailId],
  );

  const selectedContext = selectedEmailContext || selectedEmail;

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchQuery.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchQuery]);

  const loadEmailPage = useCallback(
    async (offset, append = false) => {
      try {
        if (append) {
          setLoadingMore(true);
        } else {
          setEmailsLoading(true);
          setEmailsError("");
        }

        const loader = debouncedSearch ? searchEmails : getEmails;
        const params = { limit: PAGE_SIZE, offset, q: debouncedSearch || undefined };
        const rows = await loader(params);
        const sorted = [...rows].sort((a, b) => utcTime(b.internal_date) - utcTime(a.internal_date));

        setEmails((prev) => (append ? [...prev, ...sorted] : sorted));
        setEmailsHasMore(rows.length === PAGE_SIZE);
        setEmailsOffset(offset + rows.length);
        if (!append) {
          setSelectedEmailId(sorted[0]?.gmail_message_id || "");
          if (!sorted[0]) setSelectedEmailContext(null);
        }
      } catch (err) {
        setEmailsError(err?.response?.data?.detail || "Failed to load emails.");
      } finally {
        if (append) {
          setLoadingMore(false);
        } else {
          setEmailsLoading(false);
        }
      }
    },
    [debouncedSearch],
  );

  useEffect(() => {
    loadEmailPage(0, false);
  }, [debouncedSearch, loadEmailPage]);

  useEffect(() => {
    if (!selectedEmail?.gmail_message_id) {
      setSelectedEmailContext(null);
      return;
    }
    loadEmailContext(selectedEmail.gmail_message_id);
  }, [selectedEmail?.gmail_message_id]);

  async function loadEmailContext(gmail_message_id) {
    if (!gmail_message_id) return;
    setSelectedEmailLoading(true);
    try {
      const emailContext = await getEmailContext(gmail_message_id, true);
      setSelectedEmailContext(emailContext);
      setReplyForm((prev) => ({
        subject: emailContext.subject || prev.subject,
        body: prev.body || emailContext.body || emailContext.snippet || "",
        tone: prev.tone,
      }));
    } catch (err) {
      setEmailsError(err?.response?.data?.detail || "Failed to load selected email.");
    } finally {
      setSelectedEmailLoading(false);
    }
  }

  const loadMore = useCallback(async () => {
    if (!emailsHasMore || loadingMore || emailsLoading) return;
    await loadEmailPage(emailsOffset, true);
  }, [emailsHasMore, emailsLoading, emailsOffset, loadEmailPage, loadingMore]);

  async function runClassifySelected() {
    if (!selectedEmail) return;
    setBusy("classify-selected");
    try {
      const result = await classifySyncedEmail(selectedEmail.gmail_message_id);
      setClassifyResult(result);
      await loadEmailPage(0, false);
    } finally {
      setBusy("");
    }
  }

  async function runManualClassify() {
    if (!selectedEmail || !manualCategory.trim()) return;
    setBusy("manual-classify");
    try {
      const result = await manuallyClassifySyncedEmail(selectedEmail.gmail_message_id, {
        category: manualCategory.trim(),
        learn: true,
      });
      setClassifyResult(result);
      await loadEmailPage(0, false);
    } finally {
      setBusy("");
    }
  }

  async function runBatchClassify() {
    setBusy("classify-batch");
    try {
      const result = await classifySyncedEmails({ limit: 10 });
      setClassifyResult(result);
      await loadEmailPage(0, false);
    } finally {
      setBusy("");
    }
  }

  async function runReply() {
    if (!selectedContext) return;
    setBusy("reply");
    try {
      setReplyResult(
        await generateReply({
          contact_id: selectedContext.contact_id || null,
          email_body: replyForm.body || selectedContext.body || selectedContext.snippet || "",
          tone: replyForm.tone,
        }),
      );
    } finally {
      setBusy("");
    }
  }

  const emailPickerStatus = useMemo(() => {
    if (emailsLoading) return "Loading synced emails...";
    if (emailsError) return emailsError;
    if (emails.length === 0) return "No synced emails yet. Queue a Gmail sync first.";
    return `${emails.length}${emailsHasMore ? "+" : ""} emails loaded`;
  }, [emailsError, emailsHasMore, emails.length, emailsLoading]);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">AI Tasks</h2>
        <p className="text-sm text-slate-400">Ollama health, async Celery jobs, and inline AI classify/reply tools.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatusCard icon={Bot} label="Ollama" loading={health.loading} data={health.data} error={health.error} />
        <StatusCard icon={Cpu} label="AI Cache" loading={stats.loading} data={stats.data} error={stats.error} />
        <StatusCard icon={RefreshCw} label="Celery" loading={celery.loading} data={celery.data} error={celery.error} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Email picker" icon={Mail}>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sender, subject, company, email, or contact"
              className="min-w-0 flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            />
            <button onClick={() => loadEmailPage(0, false)} className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-300">
              Refresh
            </button>
          </div>

          {emailsLoading ? (
            <EmailListSkeleton />
          ) : emailsError ? (
            <p className="text-sm text-amber-300">{emailsError}</p>
          ) : emails.length === 0 ? (
            <p className="text-sm text-slate-400">{emailPickerStatus}</p>
          ) : (
            <>
              <div className="mb-3 max-h-72 overflow-auto rounded-md border border-white/10">
                {emails.map((email) => (
                  <button
                    key={email.gmail_message_id}
                    onClick={() => setSelectedEmailId(email.gmail_message_id)}
                    className={`block w-full border-b border-white/10 px-3 py-2 text-left text-sm last:border-b-0 hover:bg-white/[0.04] ${
                      (selectedEmailId || selectedEmail?.gmail_message_id) === email.gmail_message_id ? "bg-cyan-400/10" : ""
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="truncate font-medium text-slate-200">{email.subject || "No subject"}</span>
                      <StatusPill value={email.ai_status} />
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-xs text-slate-500">{email.sender || email.sender_email || "Unknown sender"}</p>
                      <span className="text-[11px] text-slate-500">{formatPktDateTime(email.internal_date)}</span>
                    </div>
                  </button>
                ))}
              </div>
              {emailsHasMore && (
                <div className="mb-3 text-right">
                  <button
                    disabled={loadingMore}
                    onClick={loadMore}
                    className="rounded-md border border-white/10 px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-50"
                  >
                    {loadingMore ? "Loading more…" : "Load more emails"}
                  </button>
                </div>
              )}
            </>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              disabled={!selectedEmail || busy === "classify-selected"}
              onClick={runClassifySelected}
              className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
            >
              Classify Selected
            </button>
            <button
              disabled={busy === "classify-batch"}
              onClick={runBatchClassify}
              className="rounded-md border border-white/10 px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-50"
            >
              Classify 10 Unclassified
            </button>
          </div>

          <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]">
            <input
              value={manualCategory}
              onChange={(event) => setManualCategory(event.target.value)}
              className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
              placeholder="Category, e.g. Job"
            />
            <button
              disabled={!selectedEmail || busy === "manual-classify"}
              onClick={runManualClassify}
              className="rounded-md border border-emerald-400/30 px-3 py-2 text-sm text-emerald-200 hover:bg-emerald-400/10 disabled:opacity-50"
            >
              Save Label + Learn
            </button>
          </div>

          {classifyResult && <ClassificationResult result={classifyResult} />}
        </Panel>

        <Panel title="Generate Reply" icon={Sparkles}>
          <div className="mb-4 rounded-xl border border-white/10 bg-slate-950/80 p-4">
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-xs text-slate-400">Selected email</p>
                  <p className="text-sm font-semibold text-slate-100">{selectedContext?.subject || "No email selected"}</p>
                </div>
                <span className="text-xs text-slate-500">{selectedContext?.internal_date ? formatPktDateTime(selectedContext.internal_date) : ""}</span>
              </div>
              <p className="text-xs text-slate-400">From: {selectedContext?.sender || selectedContext?.sender_email || "Unknown"}</p>
              <p className="text-xs text-slate-400">To: {selectedContext?.recipient || "You"}</p>
              {selectedContext?.company && <p className="text-xs text-slate-400">Company: {selectedContext.company}</p>}
              <div className="grid gap-2 sm:grid-cols-2">
                <span className="rounded-md bg-white/5 px-2 py-1 text-[11px] text-slate-400">Gmail ID: {selectedContext?.gmail_message_id || "—"}</span>
                <span className="rounded-md bg-white/5 px-2 py-1 text-[11px] text-slate-400">Thread ID: {selectedContext?.thread_id || "—"}</span>
              </div>
            </div>
          </div>

          <input
            value={replyForm.subject}
            onChange={(e) => setReplyForm({ ...replyForm, subject: e.target.value })}
            placeholder="Subject"
            className="mb-2 w-full rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm"
          />
          <textarea
            value={replyForm.body}
            onChange={(e) => setReplyForm({ ...replyForm, body: e.target.value })}
            placeholder="Original email"
            rows={4}
            className="mb-2 w-full rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm"
          />
          <select
            value={replyForm.tone}
            onChange={(e) => setReplyForm({ ...replyForm, tone: e.target.value })}
            className="mb-2 w-full rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm"
          >
            {["professional", "friendly", "concise"].map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <button disabled={busy === "reply" || !selectedContext} onClick={runReply} className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">
            Generate Reply
          </button>
          {selectedEmailLoading && <p className="mt-3 text-sm text-slate-400">Loading selected email details...</p>}
          {replyResult && <pre className="mt-3 overflow-auto rounded-md bg-black/30 p-3 text-xs text-slate-300">{JSON.stringify(replyResult, null, 2)}</pre>}
        </Panel>
      </div>

      <Panel title="Manual Classification Test" icon={Mail}>
        <div className="grid gap-2 lg:grid-cols-[1fr_1.5fr_auto]">
          <input
            value={classifyForm.subject}
            onChange={(e) => setClassifyForm({ ...classifyForm, subject: e.target.value })}
            placeholder="Subject"
            className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm"
          />
          <input
            value={classifyForm.body}
            onChange={(e) => setClassifyForm({ ...classifyForm, body: e.target.value })}
            placeholder="Email body or snippet"
            className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm"
          />
          <button disabled={busy === "classify"} onClick={runClassify} className="rounded-md border border-white/10 px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-50">
            Test
          </button>
        </div>
      </Panel>

      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
        <h3 className="mb-3 text-sm font-medium text-slate-300">Async Task Queue</h3>
        <div className="flex flex-wrap gap-2">
          <button disabled={busy === "sync"} onClick={runSync} className="rounded-md border border-white/10 px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-50">
            Queue Gmail Sync
          </button>
        </div>
        <div className="mt-3 flex max-w-xl gap-2">
          <input
            value={taskId}
            onChange={(e) => setTaskId(e.target.value)}
            placeholder="Task ID"
            className="min-w-0 flex-1 rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
          />
          <button onClick={lookup} className="rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950">
            Check
          </button>
        </div>
        {task && <pre className="mt-3 overflow-auto rounded-md bg-black/20 p-4 text-sm text-slate-300">{JSON.stringify(task, null, 2)}</pre>}
      </div>
    </section>
  );
}

function StatusCard({ icon: Icon, label, loading, data, error }) {
  const details = formatStatusDetails(label, data);
  const status = error ? "Issue" : details.status;
  const tone =
    status === "Healthy" || status === "Connected" || status === "Ready"
      ? "text-emerald-300"
      : status === "Issue" || status === "Unavailable"
        ? "text-amber-300"
        : "text-slate-300";

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
      <Icon className="mb-3 text-cyan-300" size={20} />
      <p className="text-xs text-slate-400">{label}</p>
      {loading ? (
        <p className="mt-1 text-sm text-slate-500">Loading...</p>
      ) : error ? (
        <p className="mt-1 text-sm text-amber-300">{friendlyError(error)}</p>
      ) : (
        <div className="mt-2 space-y-2">
          <p className={`text-sm font-medium ${tone}`}>{status}</p>
          {details.rows.map(([name, value]) => (
            <div key={name} className="flex items-center justify-between gap-3 rounded-md bg-black/20 px-3 py-2 text-xs">
              <span className="text-slate-500">{name}</span>
              <span className="min-w-0 truncate text-right text-slate-300">{value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EmailListSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="h-[72px] animate-pulse rounded-md bg-white/[0.06] p-3">
          <div className="mb-3 h-3 w-2/3 rounded bg-white/10" />
          <div className="h-3 w-full rounded bg-white/10" />
        </div>
      ))}
    </div>
  );
}

function StatusPill({ value }) {
  const label = value || "queued";
  const tone =
    label === "queued"
      ? "border-slate-500/20 bg-slate-500/10 text-slate-300"
      : label === "processing"
        ? "border-cyan-400/20 bg-cyan-400/10 text-cyan-200"
        : label === "failed"
          ? "border-amber-400/20 bg-amber-400/10 text-amber-200"
          : "border-emerald-400/20 bg-emerald-400/10 text-emerald-200";

  return <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] ${tone}`}>{label}</span>;
}

function ClassificationResult({ result }) {
  const classification = result?.classification || result?.results?.find((row) => row.classification)?.classification;

  if (result?.results) {
    const successful = result.results.filter((row) => row.status === "classified").length;
    const failed = result.results.length - successful;
    return (
      <div className="mt-3 rounded-md border border-white/10 bg-black/20 p-3 text-sm">
        <p className="font-medium text-slate-200">Batch classification complete</p>
        <p className="mt-1 text-xs text-slate-400">
          {successful} classified · {failed} failed
        </p>
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-md border border-white/10 bg-black/20 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill value={classification?.category || result?.email?.ai_status || "classified"} />
        <span className="text-xs text-slate-400">Confidence {Math.round(Number(classification?.confidence || 0) * 100)}%</span>
      </div>
      <p className="mt-2 text-slate-300">{classification?.action || "Review this email"}</p>
      {classification?.priority && <p className="mt-1 text-xs text-slate-500">Priority: {classification.priority}</p>}
    </div>
  );
}

function formatStatusDetails(label, data) {
  if (label === "Ollama") {
    return {
      status: data?.status === "healthy" ? "Healthy" : "Unavailable",
      rows: [
        ["Model", data?.model || "Not loaded"],
        ["Memory", data?.memory ? `${data.memory.used_mb || 0} MB used` : "Waiting for Ollama"],
      ],
    };
  }

  if (label === "AI Cache") {
    const stats = data?.stats?.cache_stats || data?.stats?.cache || data?.stats || data || {};
    return {
      status: data?.status === "success" ? "Ready" : "Issue",
      rows: [
        ["Cached Items", stats.cached_items ?? 0],
        ["Hit Rate", `${stats.hit_rate ?? 0}%`],
      ],
    };
  }

  if (label === "Celery") {
    return {
      status: data?.status === "healthy" ? "Connected" : data?.status === "degraded" ? "Fallback Active" : "Issue",
      rows: [
        ["Worker", data?.celery || "Unknown"],
        ["Broker", data?.broker || "Unknown"],
      ],
    };
  }

  return { status: data?.status || "Ready", rows: [] };
}

function friendlyError(error) {
  const text = String(error || "");
  if (text.includes("AIResponseCache")) return "Cache service needs backend restart.";
  if (text.includes("AI system unavailable")) return "Ollama is not running.";
  return text.replace(/^Stats retrieval failed:\s*/i, "");
}

function Panel({ title, icon: Icon, children }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-300">
        <Icon size={16} /> {title}
      </h3>
      {children}
    </div>
  );
}
