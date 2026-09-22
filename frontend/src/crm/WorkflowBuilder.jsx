import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Plus, Trash2, Save, Play, ChevronDown, ChevronUp, Zap, GitBranch,
  Activity, ArrowRight, Loader2, CheckCircle2, XCircle, RefreshCw,
  Settings2, AlertTriangle, History, Eye,
} from "lucide-react";
import {
  getWorkflow, createWorkflow, updateWorkflow, validateWorkflow, testWorkflow,
  enableWorkflow, disableWorkflow, listWorkflowExecutions,
} from "./api";

// ── Constants ──────────────────────────────────────────────────────────────

const TRIGGER_OPTIONS = [
  { value: "contact_created",    label: "New Contact Created" },
  { value: "contact_updated",    label: "Contact Updated" },
  { value: "deal_created",       label: "Deal Created" },
  { value: "deal_stage_changed", label: "Deal Stage Changed" },
  { value: "email_received",     label: "Email Received" },
  { value: "email_classified",   label: "Email Classified" },
  { value: "task_completed",     label: "Task Completed" },
  { value: "scheduled",          label: "Scheduled (Time-based)" },
  { value: "webhook_received",   label: "Webhook Received" },
];

const ACTION_OPTIONS = [
  { value: "create_task",    label: "Create Task",        icon: "✅" },
  { value: "update_contact", label: "Update Contact",     icon: "👤" },
  { value: "update_deal",    label: "Update Deal",        icon: "💰" },
  { value: "send_email_draft", label: "Send Email Draft (Requires Approval)", icon: "📧" },
  { value: "assign_user",    label: "Assign User",        icon: "🎯" },
  { value: "add_tag",        label: "Add Tag",            icon: "🏷️" },
  { value: "create_activity", label: "Create Activity",   icon: "📝" },
  { value: "notify_user",    label: "Notify User",        icon: "🔔" },
  { value: "call_webhook",   label: "Call Webhook (HTTPS)", icon: "🔗" },
  { value: "ai_action",      label: "AI Action (Ollama)", icon: "🤖" },
];

const OPERATORS = [
  { value: "eq",           label: "equals" },
  { value: "ne",           label: "not equals" },
  { value: "contains",     label: "contains" },
  { value: "not_contains", label: "doesn't contain" },
  { value: "gt",           label: "greater than" },
  { value: "lt",           label: "less than" },
  { value: "gte",          label: "≥" },
  { value: "lte",          label: "≤" },
  { value: "is_empty",     label: "is empty" },
  { value: "is_not_empty", label: "is not empty" },
];

const STATUS_COLORS = {
  completed: "text-emerald-400", failed: "text-red-400", running: "text-cyan-400",
  pending: "text-slate-400", awaiting_approval: "text-amber-400", canceled: "text-slate-500",
};

// ── Helpers ────────────────────────────────────────────────────────────────

let _nodeCounter = 100;
const newNodeId = () => `node_${++_nodeCounter}`;

function emptyConditionNode() {
  return {
    id: newNodeId(), type: "condition",
    config: { groups: [{ logic: "AND", conditions: [{ field: "", operator: "eq", value: "" }] }] },
  };
}

function emptyActionNode(type = "create_task") {
  return {
    id: newNodeId(), type,
    config: {},
    on_failure: "stop",
  };
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function WorkflowBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isNew = !id || id === "new";

  const [name, setName] = useState("My Workflow");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("contact_created");
  const [triggerConfig, setTriggerConfig] = useState({});
  const [nodes, setNodes] = useState([]);
  const [status, setStatus] = useState("draft");

  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);
  const [testing, setTesting] = useState(false);
  const [loadingExec, setLoadingExec] = useState(false);
  const [executions, setExecutions] = useState([]);
  const [validationResult, setValidationResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("builder"); // builder | history

  // Load existing workflow
  useEffect(() => {
    if (!isNew) {
      getWorkflow(id).then(wf => {
        setName(wf.name);
        setDescription(wf.description || "");
        setTriggerType(wf.trigger_type);
        setTriggerConfig(wf.trigger_config || {});
        setNodes(wf.nodes || []);
        setStatus(wf.status);
      }).catch(() => setError("Workflow not found"));
    }
  }, [id, isNew]);

  // Load execution history
  const loadExecutions = useCallback(async () => {
    if (isNew) return;
    setLoadingExec(true);
    try {
      const { executions: exs } = await listWorkflowExecutions(id, { limit: 20 });
      setExecutions(exs || []);
    } catch (_) {}
    finally { setLoadingExec(false); }
  }, [id, isNew]);

  useEffect(() => { if (activeTab === "history") loadExecutions(); }, [activeTab, loadExecutions]);

  // ── Node operations ────────────────────────────────────────────────────

  function addConditionNode() {
    setNodes(prev => [...prev, emptyConditionNode()]);
  }

  function addActionNode(type) {
    setNodes(prev => [...prev, emptyActionNode(type)]);
  }

  function removeNode(nodeId) {
    setNodes(prev => prev.filter(n => n.id !== nodeId));
  }

  function updateNode(nodeId, updater) {
    setNodes(prev => prev.map(n => n.id === nodeId ? { ...n, ...updater(n) } : n));
  }

  function updateCondition(nodeId, groupIdx, condIdx, field, value) {
    updateNode(nodeId, n => {
      const groups = JSON.parse(JSON.stringify(n.config.groups));
      groups[groupIdx].conditions[condIdx][field] = value;
      return { config: { ...n.config, groups } };
    });
  }

  function addConditionRow(nodeId, groupIdx) {
    updateNode(nodeId, n => {
      const groups = JSON.parse(JSON.stringify(n.config.groups));
      groups[groupIdx].conditions.push({ field: "", operator: "eq", value: "" });
      return { config: { ...n.config, groups } };
    });
  }

  function removeConditionRow(nodeId, groupIdx, condIdx) {
    updateNode(nodeId, n => {
      const groups = JSON.parse(JSON.stringify(n.config.groups));
      groups[groupIdx].conditions.splice(condIdx, 1);
      return { config: { ...n.config, groups } };
    });
  }

  function toggleGroupLogic(nodeId, groupIdx) {
    updateNode(nodeId, n => {
      const groups = JSON.parse(JSON.stringify(n.config.groups));
      groups[groupIdx].logic = groups[groupIdx].logic === "AND" ? "OR" : "AND";
      return { config: { ...n.config, groups } };
    });
  }

  function updateNodeConfig(nodeId, configUpdates) {
    updateNode(nodeId, n => ({ config: { ...n.config, ...configUpdates } }));
  }

  // ── Save / validate / test ─────────────────────────────────────────────

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload = {
        name, description, trigger_type: triggerType,
        trigger_config: triggerConfig, nodes,
      };
      if (isNew) {
        const wf = await createWorkflow(payload);
        navigate(`/workflows/${wf.id}`, { replace: true });
      } else {
        await updateWorkflow(id, payload);
      }
    } catch (e) {
      setError(e?.response?.data?.detail?.errors?.join(", ") || e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleValidate() {
    if (isNew) { alert("Save first to validate."); return; }
    setValidating(true);
    try {
      const r = await validateWorkflow(id);
      setValidationResult(r);
    } catch (e) {
      setValidationResult({ valid: false, errors: [e?.response?.data?.detail || "Validation error"] });
    } finally {
      setValidating(false);
    }
  }

  async function handleTest() {
    if (isNew) { alert("Save first to test."); return; }
    setTesting(true);
    try {
      await testWorkflow(id);
      alert("Test dispatch sent! Check execution history.");
      loadExecutions();
    } catch (e) {
      alert(e?.response?.data?.detail || "Test failed");
    } finally {
      setTesting(false);
    }
  }

  async function handleToggleStatus() {
    if (isNew) return;
    try {
      if (status === "active") {
        await disableWorkflow(id);
        setStatus("paused");
      } else {
        await enableWorkflow(id);
        setStatus("active");
      }
    } catch (e) {
      alert(e?.response?.data?.detail || "Toggle failed");
    }
  }

  return (
    <section className="space-y-6 p-1">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white flex items-center gap-2">
            <Zap size={20} className="text-cyan-400" />
            {isNew ? "New Workflow" : "Edit Workflow"}
          </h1>
          {!isNew && (
            <span className={`text-xs px-2 py-0.5 rounded-full mt-1 inline-block ${
              status === "active" ? "bg-emerald-500/15 text-emerald-300" :
              status === "paused" ? "bg-amber-500/15 text-amber-300" :
              "bg-slate-500/15 text-slate-300"
            }`}>{status}</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {!isNew && (
            <>
              <button onClick={handleValidate} disabled={validating}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5 transition disabled:opacity-50">
                {validating ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Validate
              </button>
              <button onClick={handleTest} disabled={testing}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5 transition disabled:opacity-50">
                {testing ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                Test
              </button>
              <button onClick={handleToggleStatus}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                  status === "active"
                    ? "bg-amber-500/20 text-amber-300 hover:bg-amber-500/30"
                    : "bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                }`}>
                {status === "active" ? "Pause" : "Activate"}
              </button>
            </>
          )}
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-cyan-400 transition disabled:opacity-50">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {isNew ? "Create" : "Save"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300 flex items-center gap-2">
          <AlertTriangle size={14} /> {typeof error === "string" ? error : JSON.stringify(error)}
        </div>
      )}

      {validationResult && (
        <div className={`rounded-lg border p-3 text-sm ${
          validationResult.valid
            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
            : "border-red-500/30 bg-red-500/10 text-red-300"
        }`}>
          {validationResult.valid
            ? "✅ Workflow is valid"
            : `❌ ${validationResult.errors?.join(" · ")}`}
        </div>
      )}

      {/* Tabs (only for existing workflows) */}
      {!isNew && (
        <div className="flex border-b border-white/10">
          {[["builder", <Settings2 size={14} />, "Builder"], ["history", <History size={14} />, "Execution History"]].map(([tab, icon, label]) => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 transition ${
                activeTab === tab
                  ? "border-cyan-400 text-cyan-300"
                  : "border-transparent text-slate-400 hover:text-white"
              }`}>
              {icon}{label}
            </button>
          ))}
        </div>
      )}

      {activeTab === "builder" && (
        <div className="space-y-5">
          {/* Basic info */}
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
            <h2 className="text-sm font-medium text-slate-300 uppercase tracking-wider">Workflow Info</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Name *</label>
                <input value={name} onChange={e => setName(e.target.value)}
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-cyan-500/50 focus:outline-none"
                  placeholder="e.g. Hot Lead Follow-up" />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Description</label>
                <input value={description} onChange={e => setDescription(e.target.value)}
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white placeholder-slate-600 focus:border-cyan-500/50 focus:outline-none"
                  placeholder="Optional description" />
              </div>
            </div>
          </div>

          {/* Trigger */}
          <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-full bg-cyan-500/20 flex items-center justify-center">
                <Zap size={14} className="text-cyan-400" />
              </div>
              <h2 className="text-sm font-medium text-cyan-300">Trigger</h2>
              <span className="text-xs text-slate-500">— When should this workflow fire?</span>
            </div>
            <select value={triggerType} onChange={e => setTriggerType(e.target.value)}
              className="w-full rounded-lg bg-[#080b12] border border-white/10 px-3 py-2 text-sm text-white focus:border-cyan-500/50 focus:outline-none">
              {TRIGGER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {triggerType === "scheduled" && (
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Schedule Type</label>
                  <select value={triggerConfig.type || "interval"}
                    onChange={e => setTriggerConfig(c => ({ ...c, type: e.target.value }))}
                    className="w-full rounded-lg bg-[#080b12] border border-white/10 px-3 py-2 text-sm text-white">
                    <option value="interval">Interval (every N minutes)</option>
                    <option value="cron">Cron Expression</option>
                    <option value="once">One-time</option>
                  </select>
                </div>
                {(triggerConfig.type || "interval") === "interval" && (
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Every N minutes</label>
                    <input type="number" min="1" value={triggerConfig.minutes || 60}
                      onChange={e => setTriggerConfig(c => ({ ...c, minutes: parseInt(e.target.value) }))}
                      className="w-full rounded-lg bg-[#080b12] border border-white/10 px-3 py-2 text-sm text-white" />
                  </div>
                )}
                {triggerConfig.type === "cron" && (
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Cron (minute hour dom month dow)</label>
                    <input value={triggerConfig.expression || "0 9 * * 1"}
                      onChange={e => setTriggerConfig(c => ({ ...c, expression: e.target.value }))}
                      className="w-full rounded-lg bg-[#080b12] border border-white/10 px-3 py-2 text-sm text-white font-mono" />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Nodes */}
          {nodes.length > 0 && (
            <div className="space-y-3">
              {nodes.map((node, idx) => (
                <div key={node.id}>
                  <div className="flex items-start gap-2 text-slate-600 text-xs mb-1.5 pl-4">
                    <ArrowRight size={12} className="mt-0.5" />
                    {node.type === "condition" ? "If" : "Then"}
                  </div>
                  {node.type === "condition"
                    ? <ConditionNodeEditor node={node} onRemove={() => removeNode(node.id)}
                        onToggleLogic={(gi) => toggleGroupLogic(node.id, gi)}
                        onUpdateCondition={(gi, ci, f, v) => updateCondition(node.id, gi, ci, f, v)}
                        onAddRow={(gi) => addConditionRow(node.id, gi)}
                        onRemoveRow={(gi, ci) => removeConditionRow(node.id, gi, ci)} />
                    : <ActionNodeEditor node={node} onRemove={() => removeNode(node.id)}
                        onUpdateConfig={(updates) => updateNodeConfig(node.id, updates)}
                        onUpdateFailure={(v) => updateNode(node.id, n => ({ ...n, on_failure: v }))} />
                  }
                </div>
              ))}
            </div>
          )}

          {/* Add node buttons */}
          <div className="flex items-center gap-3 flex-wrap pt-2">
            <span className="text-xs text-slate-500">Add step:</span>
            <button onClick={addConditionNode}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:border-amber-500/30 hover:text-amber-300 transition">
              <GitBranch size={13} />
              Condition
            </button>
            {ACTION_OPTIONS.map(opt => (
              <button key={opt.value} onClick={() => addActionNode(opt.value)}
                className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:border-cyan-500/30 hover:text-cyan-300 transition">
                {opt.icon} {opt.label.split("(")[0].trim()}
              </button>
            ))}
          </div>
        </div>
      )}

      {activeTab === "history" && (
        <ExecutionHistory executions={executions} loading={loadingExec} />
      )}
    </section>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────

function ConditionNodeEditor({ node, onRemove, onToggleLogic, onUpdateCondition, onAddRow, onRemoveRow }) {
  const groups = node.config?.groups || [];
  return (
    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <GitBranch size={15} className="text-amber-400" />
          <span className="text-sm font-medium text-amber-300">Condition</span>
        </div>
        <button onClick={onRemove} className="rounded-lg p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition">
          <Trash2 size={13} />
        </button>
      </div>
      {groups.map((group, gi) => (
        <div key={gi} className="space-y-2 mb-3">
          {group.conditions.map((cond, ci) => (
            <div key={ci} className="flex items-center gap-2 flex-wrap">
              {ci > 0 && (
                <button onClick={() => onToggleLogic(gi)}
                  className="rounded px-2 py-0.5 text-xs font-bold bg-white/10 text-white hover:bg-white/20 transition w-10">
                  {group.logic}
                </button>
              )}
              <input value={cond.field} onChange={e => onUpdateCondition(gi, ci, "field", e.target.value)}
                placeholder="field (e.g. deal.amount)"
                className="flex-1 min-w-[120px] rounded-lg bg-white/5 border border-white/10 px-2 py-1.5 text-xs text-white placeholder-slate-600" />
              <select value={cond.operator} onChange={e => onUpdateCondition(gi, ci, "operator", e.target.value)}
                className="rounded-lg bg-[#080b12] border border-white/10 px-2 py-1.5 text-xs text-white">
                {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              {!["is_empty", "is_not_empty"].includes(cond.operator) && (
                <input value={cond.value} onChange={e => onUpdateCondition(gi, ci, "value", e.target.value)}
                  placeholder="value"
                  className="flex-1 min-w-[100px] rounded-lg bg-white/5 border border-white/10 px-2 py-1.5 text-xs text-white placeholder-slate-600" />
              )}
              <button onClick={() => onRemoveRow(gi, ci)} className="text-slate-600 hover:text-red-400 transition">
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          <button onClick={() => onAddRow(gi)}
            className="text-xs text-slate-500 hover:text-amber-300 transition flex items-center gap-1">
            <Plus size={12} /> Add condition
          </button>
        </div>
      ))}
    </div>
  );
}

function ActionNodeEditor({ node, onRemove, onUpdateConfig, onUpdateFailure }) {
  const opt = ACTION_OPTIONS.find(o => o.value === node.type) || {};
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-base">{opt.icon || "⚡"}</span>
          <span className="text-sm font-medium text-white">{opt.label || node.type}</span>
          {node.type === "send_email_draft" && (
            <span className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-full px-2 py-0.5">
              Requires Approval
            </span>
          )}
        </div>
        <button onClick={onRemove} className="rounded-lg p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition">
          <Trash2 size={13} />
        </button>
      </div>
      <ActionConfigFields node={node} onUpdateConfig={onUpdateConfig} />
      <div className="mt-3 flex items-center gap-2">
        <label className="text-xs text-slate-500">On failure:</label>
        <select value={node.on_failure || "stop"} onChange={e => onUpdateFailure(e.target.value)}
          className="rounded-lg bg-[#080b12] border border-white/10 px-2 py-1 text-xs text-white">
          <option value="stop">Stop workflow</option>
          <option value="continue">Continue anyway</option>
        </select>
      </div>
    </div>
  );
}

function ActionConfigFields({ node, onUpdateConfig }) {
  const c = node.config || {};
  switch (node.type) {
    case "create_task": return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Field label="Title" value={c.title || ""} onChange={v => onUpdateConfig({ title: v })} placeholder="{{contact.name}} Follow-up" />
        <Field label="Priority" value={c.priority || "medium"} onChange={v => onUpdateConfig({ priority: v })} type="select"
          options={["low","medium","high","urgent"]} />
        <Field label="Due in (days)" value={c.due_in_days || 1} onChange={v => onUpdateConfig({ due_in_days: parseInt(v) })} type="number" />
        <Field label="Description" value={c.description || ""} onChange={v => onUpdateConfig({ description: v })} placeholder="Follow up on deal" />
      </div>
    );
    case "update_contact": return (
      <div className="space-y-2">
        <p className="text-xs text-slate-500">Fields to update (key=value):</p>
        {Object.entries(c.fields || {}).map(([k, v]) => (
          <div key={k} className="flex gap-2">
            <span className="text-xs text-slate-400 bg-white/5 rounded px-2 py-1">{k}</span>
            <input value={v} onChange={e => onUpdateConfig({ fields: { ...c.fields, [k]: e.target.value } })}
              className="flex-1 rounded-lg bg-white/5 border border-white/10 px-2 py-1 text-xs text-white" />
          </div>
        ))}
        <select onChange={e => { if(e.target.value) onUpdateConfig({ fields: { ...(c.fields||{}), [e.target.value]: "" }}); e.target.value=""; }}
          className="text-xs rounded-lg bg-[#080b12] border border-white/10 px-2 py-1 text-slate-400 mt-1">
          <option value="">+ Add field</option>
          {["name","company","title","source","sentiment"].map(f => <option key={f} value={f}>{f}</option>)}
        </select>
      </div>
    );
    case "notify_user": return (
      <Field label="Message" value={c.message || ""} onChange={v => onUpdateConfig({ message: v })} placeholder="{{contact.name}} needs attention" />
    );
    case "call_webhook": return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Field label="HTTPS URL *" value={c.url || ""} onChange={v => onUpdateConfig({ url: v })} placeholder="https://hooks.example.com/..." />
        <Field label="Secret (HMAC)" value={c.secret || ""} onChange={v => onUpdateConfig({ secret: v })} placeholder="Optional signing secret" />
      </div>
    );
    case "ai_action": return (
      <div className="space-y-3">
        <Field label="Prompt" value={c.prompt || ""} onChange={v => onUpdateConfig({ prompt: v })}
          placeholder="Classify this lead and suggest next action" />
        <p className="text-xs text-slate-500">Uses Ollama via the approved tool registry. No arbitrary SQL or code.</p>
      </div>
    );
    default: return <p className="text-xs text-slate-500">No configuration needed for this action type.</p>;
  }
}

function Field({ label, value, onChange, placeholder, type = "text", options = [] }) {
  return (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      {type === "select" ? (
        <select value={value} onChange={e => onChange(e.target.value)}
          className="w-full rounded-lg bg-[#080b12] border border-white/10 px-2 py-1.5 text-xs text-white">
          {options.map(o => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input type={type} value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg bg-white/5 border border-white/10 px-2 py-1.5 text-xs text-white placeholder-slate-600 focus:border-cyan-500/50 focus:outline-none" />
      )}
    </div>
  );
}

function ExecutionHistory({ executions, loading }) {
  if (loading) return <div className="flex justify-center py-10"><RefreshCw size={20} className="animate-spin text-cyan-400" /></div>;
  if (!executions.length) return <p className="text-sm text-slate-500 py-8 text-center">No executions yet. Test the workflow to create one.</p>;
  return (
    <div className="space-y-2">
      {executions.map(ex => (
        <div key={ex.id} className="rounded-xl border border-white/10 bg-white/[0.03] p-4 flex items-center justify-between gap-4">
          <div>
            <div className={`text-sm font-medium ${STATUS_COLORS[ex.status] || "text-slate-400"}`}>
              {ex.status}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">
              {new Date(ex.created_at).toLocaleString()}
            </div>
            {ex.error && <div className="text-xs text-red-400 mt-1 truncate max-w-xs">{ex.error}</div>}
          </div>
          <div className="text-xs text-slate-600">#{ex.id}</div>
        </div>
      ))}
    </div>
  );
}
