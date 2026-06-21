import { Activity, BarChart3, TrendingUp, Users } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getActivities, getPipeline, getSummary } from "./api";
import useApiResource from "./useApiResource";

export default function Analytics() {
  const summary = useApiResource(getSummary, []);
  const pipeline = useApiResource(getPipeline, []);
  const activities = useApiResource(getActivities, []);

  const metrics = summary.data || { emails: 0, contacts: 0, hot_leads: 0, campaigns: 0 };
  const chart = [
    { name: "Emails", value: metrics.emails },
    { name: "Contacts", value: metrics.contacts },
    { name: "Hot Leads", value: metrics.hot_leads },
    { name: "Campaigns", value: metrics.campaigns },
  ];
  const stages = pipeline.data || [];
  const timeline = activities.data || [];

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Analytics</h2>
        <p className="text-sm text-slate-400">CRM performance, pipeline value, and recent activity.</p>
      </div>

      {(summary.error || pipeline.error || activities.error) && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          {summary.error || pipeline.error || activities.error}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Metric icon={BarChart3} label="Emails Synced" value={summary.loading ? "..." : metrics.emails} />
        <Metric icon={Users} label="Contacts" value={summary.loading ? "..." : metrics.contacts} />
        <Metric icon={TrendingUp} label="Hot Leads" value={summary.loading ? "..." : metrics.hot_leads} />
        <Metric icon={Activity} label="Campaigns" value={summary.loading ? "..." : metrics.campaigns} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <h3 className="mb-4 text-sm font-medium text-slate-300">Workspace Metrics</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chart}>
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,.1)" }} />
                <Bar dataKey="value" fill="#22d3ee" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <h3 className="mb-4 text-sm font-medium text-slate-300">Deal Pipeline</h3>
          {pipeline.loading ? (
            <p className="text-sm text-slate-400">Loading pipeline...</p>
          ) : stages.length === 0 ? (
            <p className="text-sm text-slate-400">No deals yet. Deals appear here as your pipeline grows.</p>
          ) : (
            <div className="space-y-3">
              {stages.map((stage) => (
                <div key={stage.stage} className="flex items-center justify-between rounded-md bg-black/20 px-3 py-2">
                  <span className="capitalize text-slate-200">{stage.stage}</span>
                  <span className="text-sm text-slate-400">
                    {stage.count} deals · ${Number(stage.value || 0).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
        <h3 className="mb-4 text-sm font-medium text-slate-300">Recent Activity</h3>
        {activities.loading ? (
          <p className="text-sm text-slate-400">Loading activity...</p>
        ) : timeline.length === 0 ? (
          <p className="text-sm text-slate-400">No activity recorded yet.</p>
        ) : (
          <div className="space-y-2">
            {timeline.slice(0, 10).map((item) => (
              <div key={item.id} className="rounded-md bg-black/20 px-3 py-2 text-sm">
                <p className="font-medium text-slate-200">{item.type || "Activity"}</p>
                <p className="text-xs text-slate-400">{item.description || item.title || "CRM event"}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
      <Icon className="mb-5 text-cyan-300" size={22} />
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value}</p>
    </div>
  );
}
