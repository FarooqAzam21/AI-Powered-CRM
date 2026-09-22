import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus, Play, Pause, Trash2, ChevronRight, Zap, Clock, CheckCircle2,
  XCircle, AlertCircle, RefreshCw, Eye, ToggleLeft, ToggleRight,
} from "lucide-react";
import {
  listWorkflows, enableWorkflow, disableWorkflow, deleteWorkflow,
  listWorkflowExecutions,
} from "./api";

const STATUS_STYLES = {
  active:   "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30",
  paused:   "bg-amber-500/15 text-amber-300 border border-amber-500/30",
  draft:    "bg-slate-500/15 text-slate-300 border border-slate-500/30",
  archived: "bg-red-500/15 text-red-300 border border-red-500/30",
};

const EXEC_STATUS_ICON = {
  completed: <CheckCircle2 size={14} className="text-emerald-400" />,
  failed:    <XCircle size={14} className="text-red-400" />,
  running:   <RefreshCw size={14} className="text-cyan-400 animate-spin" />,
  pending:   <Clock size={14} className="text-slate-400" />,
  awaiting_approval: <AlertCircle size={14} className="text-amber-400" />,
  canceled:  <XCircle size={14} className="text-slate-500" />,
};

const TRIGGER_LABELS = {
  contact_created:    "New Contact",
  contact_updated:    "Contact Updated",
  deal_created:       "Deal Created",
  deal_stage_changed: "Deal Stage Changed",
  email_received:     "Email Received",
  email_classified:   "Email Classified",
  task_completed:     "Task Completed",
  scheduled:          "Scheduled",
  webhook_received:   "Webhook",
};

export default function Workflows() {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [toggling, setToggling] = useState(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const { workflows: wfs } = await listWorkflows();
      setWorkflows(wfs || []);
      setError(null);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load workflows");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleToggle(wf) {
    setToggling(wf.id);
    try {
      if (wf.status === "active") {
        await disableWorkflow(wf.id);
      } else {
        await enableWorkflow(wf.id);
      }
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to toggle workflow");
    } finally {
      setToggling(null);
    }
  }

  async function handleDelete(wf) {
    if (!confirm(`Archive workflow "${wf.name}"? This cannot be undone.`)) return;
    try {
      await deleteWorkflow(wf.id);
      await load();
    } catch (e) {
      alert(e?.response?.data?.detail || "Failed to archive workflow");
    }
  }

  const stats = {
    active: workflows.filter(w => w.status === "active").length,
    total:  workflows.length,
    draft:  workflows.filter(w => w.status === "draft").length,
  };

  return (
    <section className="space-y-6 p-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white flex items-center gap-2">
            <Zap size={22} className="text-cyan-400" />
            Workflow Automation
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Automate CRM actions with triggers, conditions, and AI agents.
          </p>
        </div>
        <button
          onClick={() => navigate("/workflows/new")}
          className="flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-400 transition"
        >
          <Plus size={16} />
          New Workflow
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Active", value: stats.active, color: "text-emerald-400" },
          { label: "Total", value: stats.total, color: "text-cyan-400" },
          { label: "Draft", value: stats.draft, color: "text-amber-400" },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">{s.label}</p>
            <p className={`mt-1 text-3xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Workflow list */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <RefreshCw size={24} className="animate-spin text-cyan-400" />
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300 text-sm">
          {error}
        </div>
      ) : workflows.length === 0 ? (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-12 text-center">
          <Zap size={40} className="mx-auto mb-3 text-slate-600" />
          <p className="text-slate-400">No workflows yet.</p>
          <button
            onClick={() => navigate("/workflows/new")}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-cyan-500/20 px-4 py-2 text-sm text-cyan-300 hover:bg-cyan-500/30 transition"
          >
            <Plus size={15} />
            Create your first workflow
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {workflows.map(wf => (
            <div
              key={wf.id}
              className="group rounded-xl border border-white/10 bg-white/[0.03] p-5 hover:border-cyan-500/30 hover:bg-white/[0.05] transition"
            >
              <div className="flex items-start justify-between gap-4">
                {/* Left: name + meta */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-medium text-white truncate">{wf.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[wf.status] || STATUS_STYLES.draft}`}>
                      {wf.status}
                    </span>
                    <span className="rounded-full bg-white/5 border border-white/10 px-2 py-0.5 text-xs text-slate-400">
                      {TRIGGER_LABELS[wf.trigger_type] || wf.trigger_type}
                    </span>
                  </div>
                  {wf.description && (
                    <p className="mt-1 text-sm text-slate-500 truncate">{wf.description}</p>
                  )}
                  <p className="mt-1.5 text-xs text-slate-600">
                    {wf.nodes?.length || 0} nodes · Created {new Date(wf.created_at).toLocaleDateString()}
                  </p>
                </div>

                {/* Right: actions */}
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => navigate(`/workflows/${wf.id}`)}
                    className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white transition"
                    title="View & Edit"
                  >
                    <Eye size={16} />
                  </button>
                  <button
                    onClick={() => handleToggle(wf)}
                    disabled={toggling === wf.id || wf.status === "archived"}
                    className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white transition disabled:opacity-40"
                    title={wf.status === "active" ? "Pause" : "Activate"}
                  >
                    {wf.status === "active"
                      ? <Pause size={16} className="text-amber-400" />
                      : <Play size={16} className="text-emerald-400" />
                    }
                  </button>
                  <button
                    onClick={() => handleDelete(wf)}
                    className="rounded-lg p-2 text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition"
                    title="Archive"
                  >
                    <Trash2 size={16} />
                  </button>
                  <button
                    onClick={() => navigate(`/workflows/${wf.id}`)}
                    className="rounded-lg p-2 text-slate-500 hover:text-white transition"
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
