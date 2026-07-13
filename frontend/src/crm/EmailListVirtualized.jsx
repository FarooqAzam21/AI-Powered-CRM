import { useCallback, useMemo, useState } from "react";

import { formatPktDateTime } from "./time";

const ROW_HEIGHT = 76;
const VIEW_HEIGHT = 610;

export default function EmailListVirtualized({ emails, selectedId, onSelect, onEndReached, hasMore, loadingMore }) {
  const [scrollTop, setScrollTop] = useState(0);
  const visible = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 4);
    const count = Math.ceil(VIEW_HEIGHT / ROW_HEIGHT) + 8;
    return { start, rows: emails.slice(start, start + count) };
  }, [emails, scrollTop]);

  const handleScroll = useCallback(
    (event) => {
      const target = event.currentTarget;
      setScrollTop(target.scrollTop);
      if (hasMore && !loadingMore && target.scrollTop + target.clientHeight >= target.scrollHeight - ROW_HEIGHT * 3) {
        onEndReached?.();
      }
    },
    [hasMore, loadingMore, onEndReached],
  );

  return (
    <div className="relative h-[610px] overflow-auto border-r border-white/10" onScroll={handleScroll}>
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
                <span className="shrink-0 text-xs text-slate-500">{formatPktDateTime(email.internal_date)}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <p className="truncate text-sm text-slate-300">{email.subject}</p>
                <span className="shrink-0 rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-slate-400">{email.ai_status}</span>
              </div>
              <p className="truncate text-xs text-slate-500">{email.snippet}</p>
            </button>
          ))}
        </div>
      </div>
      {loadingMore && (
        <div className="sticky bottom-0 border-t border-white/10 bg-slate-950/90 px-4 py-3 text-sm text-cyan-200 backdrop-blur">
          Loading more emails...
        </div>
      )}
    </div>
  );
}
