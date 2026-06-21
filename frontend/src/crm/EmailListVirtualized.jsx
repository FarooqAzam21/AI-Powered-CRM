import { useMemo, useState } from "react";

const ROW_HEIGHT = 76;
const VIEW_HEIGHT = 610;

export default function EmailListVirtualized({ emails, selectedId, onSelect }) {
  const [scrollTop, setScrollTop] = useState(0);
  const visible = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 4);
    const count = Math.ceil(VIEW_HEIGHT / ROW_HEIGHT) + 8;
    return { start, rows: emails.slice(start, start + count) };
  }, [emails, scrollTop]);

  return (
    <div className="relative h-[610px] overflow-auto border-r border-white/10" onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}>
      <div style={{ height: emails.length * ROW_HEIGHT }}>
        <div style={{ transform: `translateY(${visible.start * ROW_HEIGHT}px)` }}>
          {visible.rows.map((email) => (
            <button
              key={email.gmail_message_id}
              onClick={() => onSelect(email)}
              className={`block h-[76px] w-full border-b border-white/10 px-4 py-3 text-left hover:bg-white/[0.04] ${
                selectedId === email.gmail_message_id ? "bg-cyan-400/10" : ""
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="truncate text-sm font-medium text-slate-100">{email.sender || email.sender_email}</p>
                <span className="shrink-0 text-xs text-slate-500">{email.ai_status}</span>
              </div>
              <p className="truncate text-sm text-slate-300">{email.subject}</p>
              <p className="truncate text-xs text-slate-500">{email.snippet}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
