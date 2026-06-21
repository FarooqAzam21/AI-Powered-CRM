import { Mail, Megaphone, TrendingUp, Users } from "lucide-react";
import { useCallback } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useAuth } from "../context/AuthContext";
import useSocket from "../hooks/useSocket";
import { getSummary } from "./api";
import useApiResource from "./useApiResource";

export default function Dashboard() {
  const { user } = useAuth();
  const { data, loading, error, refresh } = useApiResource(getSummary, []);
  const summary = data || { emails: 0, contacts: 0, hot_leads: 0, campaigns: 0 };
  const chart = [
    { name: "Emails", value: summary.emails },
    { name: "Contacts", value: summary.contacts },
    { name: "Hot Leads", value: summary.hot_leads },
    { name: "Campaigns", value: summary.campaigns },
  ];

  const onSocketMessage = useCallback(
    (payload) => {
      if (payload?.type === "metrics_update" || payload?.type === "heartbeat") {
        refresh();
      }
    },
    [refresh]
  );

  useSocket(user?.id, onSocketMessage);

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-slate-400">Live CRM health, async AI workload, and email automation overview.</p>
      </div>
      {error && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>}
      <div className="grid gap-4 md:grid-cols-4">
        <Metric icon={Mail} label="Emails" value={loading ? "..." : summary.emails} />
        <Metric icon={Users} label="Contacts" value={loading ? "..." : summary.contacts} />
        <Metric icon={TrendingUp} label="Hot Leads" value={loading ? "..." : summary.hot_leads} />
        <Metric icon={Megaphone} label="Campaigns" value={loading ? "..." : summary.campaigns} />
      </div>
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
        <h3 className="mb-4 text-sm font-medium text-slate-300">Workspace Activity</h3>
        <div className="h-72">
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
