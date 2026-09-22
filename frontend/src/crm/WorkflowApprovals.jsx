import { useState, useEffect, useCallback } from "react";
import { CheckCircle2, XCircle, Clock, AlertCircle, RefreshCw, MessageSquare } from "lucide-react";
import { listPendingApprovals, approveAction, rejectAction } from "./api";

const STATUS_ICON = {
  pending:  <Clock size={16} className="text-amber-400" />,
  approved: <CheckCircle2 size={16} className="text-emerald-400" />,
  rejected: <XCircle size={16} className="text-red-400" />,
  expired:  <AlertCircle size={16} className="text-slate-500" />,
};

const ACTION_TYPE_LABELS = {
  send_email_draft: "Send Email Draft",
  create_task:      "Create Task",
  update_contact:   "Update Contact",
  update_deal:      "Update Deal",
  call_webhook:     "Call Webhook",
  ai_action:        "AI Action",
};

export default function WorkflowApprovals() {
  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null);
  const [notes, setNotes] = useState({});
  const [showNotes, setShowNotes] = useState({});
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const { approvals: list } = await listPendingApprovals();
      setApprovals(list || []);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDecision(approvalId, decision) {
    setProcessingId(approvalId);
    try {
      if (decision === "approved") {
        await approveAction(approvalId, notes[approvalId] || "");
      } else {
        await rejectAction(approvalId, notes[approvalId] || "");
      }
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || `Failed to ${decision} action`);
    } finally {
      setProcessingId(null);
    }
  }

  const pendingCount = approvals.filter(a => a.status === "pending").length;

  return (
    <section className="space-y-6 p-1">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
            <AlertCircle size={22} className="text-amber-400" />
            Workflow Approvals
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Review and approve AI-generated or sensitive workflow actions before execution.
          </p>
        </div>
        <button onClick={load} className="rounded-lg border border-white/10 p-2 text-slate-400 hover:bg-white/5 hover:text-white transition">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Badge */}
      {pendingCount > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 flex items-center gap-3">
          <AlertCircle size={18} className="text-amber-400 shrink-0" />
          <p className="text-sm text-amber-300">
            <span className="font-semibold">{pendingCount}</span> action{pendingCount !== 1 ? "s" : ""} waiting for your approval.
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw size={24} className="animate-spin text-cyan-400" />
        </div>
      ) : approvals.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-12 text-center">
          <CheckCircle2 size={40} className="mx-auto mb-3 text-emerald-500/40" />
          <p className="text-slate-400">No pending approvals. You're all caught up!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map(approval => (
            <div
              key={approval.id}
              className={`rounded-xl border p-5 transition ${
                approval.status === "pending"
                  ? "border-amber-500/25 bg-amber-500/5"
                  : "border-white/10 bg-white/[0.03] opacity-60"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                {/* Left: action details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    {STATUS_ICON[approval.status]}
                    <span className="font-medium text-white">
                      {ACTION_TYPE_LABELS[approval.action_type] || approval.action_type}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      approval.status === "pending"  ? "bg-amber-500/15 text-amber-300" :
                      approval.status === "approved" ? "bg-emerald-500/15 text-emerald-300" :
                      approval.status === "rejected" ? "bg-red-500/15 text-red-300" :
                      "bg-slate-500/15 text-slate-400"
                    }`}>{approval.status}</span>
                  </div>

                  <div className="mt-2 text-xs text-slate-500">
                    Execution #{approval.execution_id} · Step #{approval.step_id} ·
                    Requested {new Date(approval.created_at).toLocaleString()}
                    {approval.expires_at && (
                      <> · Expires {new Date(approval.expires_at).toLocaleString()}</>
                    )}
                  </div>

                  {/* Action payload preview */}
                  {approval.action_payload && Object.keys(approval.action_payload).length > 0 && (
                    <div className="mt-3 rounded-lg bg-white/5 border border-white/10 p-3">
                      <p className="text-xs font-medium text-slate-400 mb-2">Action Details</p>
                      <div className="space-y-1">
                        {Object.entries(approval.action_payload).map(([k, v]) =>
                          k !== "action_type" && (
                            <div key={k} className="flex gap-2 text-xs">
                              <span className="text-slate-500 shrink-0 w-32 truncate">{k}:</span>
                              <span className="text-slate-300 truncate">
                                {typeof v === "object" ? JSON.stringify(v) : String(v)}
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}

                  {/* Decision notes */}
                  {approval.status !== "pending" && approval.notes && (
                    <p className="mt-2 text-xs text-slate-500 italic">Note: {approval.notes}</p>
                  )}
                </div>

                {/* Right: decision buttons */}
                {approval.status === "pending" && (
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => setShowNotes(s => ({ ...s, [approval.id]: !s[approval.id] }))}
                      className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5 transition"
                    >
                      <MessageSquare size={12} />
                      Notes
                    </button>
                    <button
                      onClick={() => handleDecision(approval.id, "approved")}
                      disabled={processingId === approval.id}
                      className="flex items-center gap-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/30 px-4 py-1.5 text-sm font-medium text-emerald-300 hover:bg-emerald-500/30 transition disabled:opacity-50"
                    >
                      <CheckCircle2 size={14} />
                      Approve
                    </button>
                    <button
                      onClick={() => handleDecision(approval.id, "rejected")}
                      disabled={processingId === approval.id}
                      className="flex items-center gap-1.5 rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-1.5 text-sm font-medium text-red-400 hover:bg-red-500/20 transition disabled:opacity-50"
                    >
                      <XCircle size={14} />
                      Reject
                    </button>
                  </div>
                )}
              </div>

              {/* Notes textarea (shown on toggle) */}
              {approval.status === "pending" && showNotes[approval.id] && (
                <div className="mt-3">
                  <textarea
                    value={notes[approval.id] || ""}
                    onChange={e => setNotes(n => ({ ...n, [approval.id]: e.target.value }))}
                    placeholder="Optional notes for your decision..."
                    rows={2}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-xs text-white placeholder-slate-600 resize-none focus:border-cyan-500/50 focus:outline-none"
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
