import { useState } from "react";
import { Activity, BarChart3, Gauge, MapPin, TrendingUp, Users } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  getActivities,
  getAnalyticsEngine,
  getBottlenecks,
  getForecastAccuracy,
  getOptimizationRecommendations,
  getPipeline,
  getSalesVelocity,
  getSummary,
  getTerritories,
  getWinLossSummary,
} from "./api";
import useApiResource from "./useApiResource";

const TABS = [
  ["overview", "Overview"],
  ["winloss", "Win/Loss"],
  ["velocity", "Velocity"],
  ["forecast", "Forecast"],
  ["territories", "Territories"],
];

export default function Analytics() {
  const [tab, setTab] = useState("overview");
  const summary = useApiResource(getSummary, []);
  const engine = useApiResource(getAnalyticsEngine, []);
  const pipeline = useApiResource(getPipeline, []);
  const activities = useApiResource(getActivities, []);
  const winLoss = useApiResource(() => getWinLossSummary(90), []);
  const velocity = useApiResource(getSalesVelocity, []);
  const bottlenecks = useApiResource(getBottlenecks, []);
  const forecast = useApiResource(getForecastAccuracy, []);
  const territories = useApiResource(getTerritories, []);
  const optimization = useApiResource(getOptimizationRecommendations, []);

  const metrics = summary.data || { emails: 0, contacts: 0, hot_leads: 0, campaigns: 0 };
  const chart = [
    { name: "Emails", value: metrics.emails },
    { name: "Contacts", value: metrics.contacts },
    { name: "Hot Leads", value: metrics.hot_leads },
    { name: "Campaigns", value: metrics.campaigns },
  ];
  const stages = pipeline.data || [];
  const analytics = engine.data || {};
  const timeline = activities.data || [];

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Analytics</h2>
          <p className="text-sm text-slate-400">CRM overview plus Phase 7 win-loss, velocity, forecast, and territory insights.</p>
        </div>
        <div className="flex flex-wrap gap-2 rounded-md border border-white/10 p-1">
          {TABS.map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`rounded px-3 py-1.5 text-sm ${tab === id ? "bg-cyan-400 text-slate-950" : "text-slate-300 hover:bg-white/5"}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {(summary.error || pipeline.error) && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          {summary.error || pipeline.error}
        </div>
      )}

      {tab === "overview" && (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Metric icon={BarChart3} label="Emails Synced" value={summary.loading ? "..." : metrics.emails} />
            <Metric icon={Users} label="Contacts" value={summary.loading ? "..." : metrics.contacts} />
            <Metric icon={TrendingUp} label="Hot Leads" value={summary.loading ? "..." : metrics.hot_leads} />
            <Metric icon={Activity} label="Campaigns" value={summary.loading ? "..." : metrics.campaigns} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
              <h3 className="mb-4 text-sm font-medium text-slate-300">Workspace Metrics</h3>
              <div className="h-64 min-h-[16rem] min-w-0">
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
                <p className="text-sm text-slate-400">No deals yet.</p>
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

          <div className="grid gap-4 lg:grid-cols-2">
            <ChartPanel title="Email Categories" data={analytics.email_categories} loading={engine.loading} />
            <ChartPanel title="Lead Temperature" data={analytics.lead_labels} loading={engine.loading} />
            <ChartPanel title="Campaign Delivery" data={analytics.campaign_statuses} loading={engine.loading} />
            <ChartPanel title="AI Activity" data={analytics.ai_activity} loading={engine.loading} />
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
        </>
      )}

      {tab === "winloss" && <InsightPanel title="Win/Loss Summary (90 days)" icon={Gauge} loading={winLoss.loading} error={winLoss.error} data={winLoss.data} />}
      {tab === "velocity" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <InsightPanel title="Sales Velocity" icon={TrendingUp} loading={velocity.loading} error={velocity.error} data={velocity.data} />
          <InsightPanel title="Pipeline Bottlenecks" icon={Gauge} loading={bottlenecks.loading} error={bottlenecks.error} data={bottlenecks.data} />
        </div>
      )}
      {tab === "forecast" && <InsightPanel title="Forecast Accuracy" icon={BarChart3} loading={forecast.loading} error={forecast.error} data={forecast.data} />}
      {tab === "territories" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <InsightPanel title="Territory Performance" icon={MapPin} loading={territories.loading} error={territories.error} data={territories.data} />
          <InsightPanel title="Optimization Tips" icon={TrendingUp} loading={optimization.loading} error={optimization.error} data={optimization.data} />
        </div>
      )}
    </section>
  );
}

function ChartPanel({ title, data = [], loading }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <h3 className="mb-4 text-sm font-medium text-slate-300">{title}</h3>
      {loading ? (
        <div className="h-48 animate-pulse rounded-md bg-white/[0.06]" />
      ) : data.length === 0 ? (
        <p className="text-sm text-slate-400">No data yet.</p>
      ) : (
        <div className="h-48 min-h-[12rem] min-w-0">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,.1)" }} />
              <Bar dataKey="value" fill="#38bdf8" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
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

function JsonPanel({ title, icon: Icon, loading, error, data }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <h3 className="mb-4 flex items-center gap-2 text-sm font-medium text-slate-300">
        <Icon size={16} /> {title}
      </h3>
      {loading ? (
        <p className="text-sm text-slate-400">Loading...</p>
      ) : error ? (
        <p className="text-sm text-amber-300">{error}</p>
      ) : !data || (typeof data === "object" && Object.keys(data).length === 0) ? (
        <p className="text-sm text-slate-400">No data yet — add deals and close outcomes to populate analytics.</p>
      ) : (
        <pre className="max-h-96 overflow-auto rounded-md bg-black/20 p-4 text-xs text-slate-300">{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
}

function InsightPanel({ title, icon: Icon, loading, error, data }) {
  const rows = toDisplayRows(data);

  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
      <h3 className="mb-4 flex items-center gap-2 text-sm font-medium text-slate-300">
        <Icon size={16} /> {title}
      </h3>
      {loading ? (
        <p className="text-sm text-slate-400">Loading...</p>
      ) : error ? (
        <p className="text-sm text-amber-300">{error}</p>
      ) : rows.length === 0 ? (
        <p className="text-sm text-slate-400">No data yet. Add deals and close outcomes to populate analytics.</p>
      ) : (
        <div className="space-y-2">
          {rows.map((row) => (
            <DisplayRow key={row.label} row={row} />
          ))}
        </div>
      )}
    </div>
  );
}

function DisplayRow({ row }) {
  if (Array.isArray(row.value)) {
    return (
      <div className="rounded-md bg-black/20 px-3 py-2 text-sm">
        <p className="mb-2 text-xs uppercase text-slate-500">{row.label}</p>
        {row.value.length === 0 ? (
          <p className="text-slate-400">None recorded</p>
        ) : (
          <div className="space-y-1">
            {row.value.slice(0, 6).map((item, index) => (
              <p key={`${row.label}-${index}`} className="text-slate-300">
                {formatValue(item)}
              </p>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-black/20 px-3 py-2 text-sm">
      <span className="text-slate-500">{row.label}</span>
      <span className="min-w-0 truncate text-right text-slate-200">{formatValue(row.value)}</span>
    </div>
  );
}

function toDisplayRows(data) {
  if (!data) return [];
  if (Array.isArray(data)) {
    return data.slice(0, 8).map((item, index) => ({ label: item.name || item.title || `Item ${index + 1}`, value: item }));
  }
  if (typeof data !== "object") return [{ label: "Value", value: data }];
  return Object.entries(data)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => ({ label: titleize(key), value }));
}

function titleize(value) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatValue(value) {
  if (Array.isArray(value)) return value.map(formatValue).join(", ");
  if (value && typeof value === "object") {
    const preferred = ["name", "title", "stage", "status", "recommendation", "message", "description", "value", "count"];
    const parts = preferred
      .filter((key) => value[key] !== undefined && value[key] !== null && value[key] !== "")
      .map((key) => `${titleize(key)}: ${formatValue(value[key])}`);
    return parts.length ? parts.join(" · ") : "Details available";
  }
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}
