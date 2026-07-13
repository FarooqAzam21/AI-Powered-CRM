import { useState, useEffect } from "react";
import { Bot, PlayCircle, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import API from "../srevices/api";

export default function AIAgentsPage() {
  const [agents, setAgents] = useState([
    { name: "Email Agent", status: "active", tasks: ["classify_email", "generate_reply", "summarize_thread"] },
    { name: "Sales Agent", status: "active", tasks: ["score_lead", "detect_intent"] },
    { name: "Hiring Agent", status: "idle", tasks: ["parse_resume", "score_candidate"] },
    { name: "Support Agent", status: "active", tasks: ["classify_issue", "suggest_solution"] },
    { name: "Marketing Agent", status: "idle", tasks: ["generate_campaign"] },
    { name: "Analytics Agent", status: "active", tasks: ["summarize_kpis"] },
    { name: "Knowledge Agent", status: "active", tasks: ["search_knowledge"] },
  ]);
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(false);

  // Mock workflows since there's no endpoint to list workflows yet
  useEffect(() => {
    setWorkflows([
      { id: "wf-1", trigger: "new_email", status: "completed", steps: ["Email Agent", "Sales Agent", "Email Agent"], time: "2.1s" },
      { id: "wf-2", trigger: "resume_received", status: "running", steps: ["Hiring Agent", "Knowledge Agent"], time: "1.5s" },
      { id: "wf-3", trigger: "support_ticket", status: "failed", steps: ["Support Agent", "Knowledge Agent"], time: "3.4s" },
    ]);
  }, []);

  const triggerTestWorkflow = async () => {
    setLoading(true);
    try {
      const res = await API.post("/agents/workflow/sync", [
        { task_type: "classify_email", payload: { subject: "Test", body: "Hello" } },
        { task_type: "score_lead", payload: {} }
      ], {
        params: {
          trigger: "manual_test",
          contact_id: 1,
        }
      });
      console.log("Workflow result:", res.data);
      alert("Workflow executed successfully! Check console.");
    } catch (err) {
      console.error(err);
      alert("Failed to run workflow. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white">Multi-Agent AI System</h1>
          <p className="text-slate-400">Orchestrate and monitor specialized AI agents collaborating in real-time.</p>
        </div>
        <button
          onClick={triggerTestWorkflow}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-cyan-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-cyan-400 disabled:opacity-50"
        >
          {loading ? <RefreshCw className="animate-spin" size={16} /> : <PlayCircle size={16} />}
          Test Workflow
        </button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <div key={agent.name} className="rounded-xl border border-white/10 bg-[#121827] p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-400/10 text-cyan-400">
                  <Bot size={20} />
                </div>
                <h3 className="font-medium text-slate-200">{agent.name}</h3>
              </div>
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                agent.status === 'active' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-slate-400/10 text-slate-400'
              }`}>
                {agent.status}
              </span>
            </div>
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Supported Tasks</p>
              <div className="flex flex-wrap gap-2">
                {agent.tasks.map(task => (
                  <span key={task} className="rounded bg-white/5 px-2 py-1 text-[11px] text-slate-300">
                    {task}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-medium text-white mb-4">Recent Workflows</h2>
        <div className="rounded-xl border border-white/10 bg-[#121827] overflow-hidden">
          <table className="min-w-full divide-y divide-white/10">
            <thead className="bg-white/5">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">ID / Trigger</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Agent Chain</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Execution Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {workflows.map((wf) => (
                <tr key={wf.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-slate-200">{wf.trigger}</div>
                    <div className="text-xs text-slate-500">{wf.id}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {wf.status === 'completed' ? (
                      <span className="flex items-center gap-1 text-emerald-400 text-sm"><CheckCircle2 size={16}/> Completed</span>
                    ) : wf.status === 'failed' ? (
                      <span className="flex items-center gap-1 text-red-400 text-sm"><XCircle size={16}/> Failed</span>
                    ) : (
                      <span className="flex items-center gap-1 text-cyan-400 text-sm"><RefreshCw size={16} className="animate-spin"/> Running</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {wf.steps.map((step, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="text-sm text-slate-300 bg-white/5 px-2 py-1 rounded">{step}</span>
                          {idx < wf.steps.length - 1 && <span className="text-slate-600">→</span>}
                        </div>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                    {wf.time}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
