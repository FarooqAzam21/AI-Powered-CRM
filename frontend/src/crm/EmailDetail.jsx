import { Bot, Send } from "lucide-react";
import { useEffect, useState } from "react";

import { getEmailBody, requestDraft } from "./api";
import { formatPktFull } from "./time";

export default function EmailDetail({ email, onTask }) {
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!email) return;
      setLoading(true);
      setBody("");
      try {
        const data = await getEmailBody(email.gmail_message_id);
        if (mounted) setBody(data.body || "");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [email?.gmail_message_id]);

  async function draft() {
    const task = await requestDraft({ body, context: email?.snippet, tone: "professional" });
    onTask?.(task.task_id);
  }

  if (!email) {
    return <div className="flex h-[610px] items-center justify-center text-sm text-slate-500">Select an email to lazy-load its body.</div>;
  }

  return (
    <article className="h-[610px] overflow-auto p-5">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate text-xl font-semibold">{email.subject}</h3>
          <p className="text-sm text-slate-400">{email.sender_email}</p>
          <p className="text-xs text-slate-500">Received {formatPktFull(email.internal_date)} PKT</p>
        </div>
        <button onClick={draft} className="inline-flex items-center gap-2 rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-300">
          <Bot size={16} />
          Draft
        </button>
      </div>
      {loading ? (
        <div className="space-y-3">
          <div className="h-4 w-3/4 animate-pulse rounded bg-white/10" />
          <div className="h-4 w-full animate-pulse rounded bg-white/10" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-white/10" />
        </div>
      ) : (
        <pre className="whitespace-pre-wrap rounded-lg border border-white/10 bg-black/20 p-4 text-sm leading-6 text-slate-300">{body || email.snippet}</pre>
      )}
    </article>
  );
}
