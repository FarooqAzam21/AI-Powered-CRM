import { useCallback, useMemo } from "react";
import { Activity, CheckCircle2, Mail, Megaphone, Radio, TrendingUp, Users, Calendar, Ticket, Clock, CheckSquare, Award, DollarSign } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { useAuth } from "../context/AuthContext";
import useSocket from "../hooks/useSocket";
import { getRecommendations, getSummary, getWsConnections, getWsDashboardMetrics } from "./api";
import useApiResource from "./useApiResource";

import { useRole } from "../security/permissionHooks";
import { normalizeRole } from "../security/permissionUtils";
import { ROLES } from "../security/roles";

export default function Dashboard() {
  const { user } = useAuth();
  const rawRole = useRole();
  const role = useMemo(() => normalizeRole(rawRole), [rawRole]);

  const { data, loading, error, refresh } = useApiResource(getSummary, []);
  const wsMetrics = useApiResource(getWsDashboardMetrics, []);
  const wsConnections = useApiResource(getWsConnections, []);
  const recommendations = useApiResource(() => getRecommendations(5), []);
  const { refresh: refreshWs } = wsMetrics;

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
        refreshWs();
      }
    },
    [refresh, refreshWs]
  );

  useSocket(user?.id, onSocketMessage);

  const live = wsMetrics.data?.data;
  const connectionInfo = wsConnections.data?.data || wsConnections.data;
  const recs = recommendations.data || [];

  const isAdmin = role === ROLES.SUPER_ADMIN || role === ROLES.WORKSPACE_ADMIN || role === ROLES.ADMIN;
  const isSales = role === ROLES.SALES;
  const isRecruiter = role === ROLES.RECRUITER;
  const isMarketing = role === ROLES.MARKETING;
  const isSupport = role === ROLES.SUPPORT;
  const isSecurity = role === ROLES.SECURITY_ANALYST;

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="text-sm text-slate-400">Live CRM health, WebSocket metrics, and AI recommendations.</p>
      </div>
      {error && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>}

      {/* Conditional Metric Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        {(isAdmin || isSecurity) && (
          <>
            <Metric icon={Mail} label="Emails" value={loading ? "..." : summary.emails} />
            <Metric icon={Users} label="Contacts" value={loading ? "..." : summary.contacts} />
            <Metric icon={TrendingUp} label="Hot Leads" value={loading ? "..." : summary.hot_leads} />
            <Metric icon={Megaphone} label="Campaigns" value={loading ? "..." : summary.campaigns} />
          </>
        )}

        {isSales && (
          <>
            <Metric icon={TrendingUp} label="Leads" value={loading ? "..." : summary.hot_leads} />
            <Metric icon={CheckSquare} label="Pipeline (Open)" value={wsMetrics.loading ? "..." : (live?.open_deals_count || 0)} />
            <Metric icon={DollarSign} label="Revenue (Won)" value={wsMetrics.loading ? "..." : `$${Number(live?.total_pipeline_value || 0).toLocaleString()}`} />
            <Metric icon={Mail} label="Workspace Emails" value={loading ? "..." : summary.emails} />
          </>
        )}

        {isRecruiter && (
          <>
            <Metric icon={Users} label="Candidates" value="128 Active" />
            <Metric icon={Calendar} label="Interviews" value="12 Scheduled" />
            <Metric icon={Award} label="Offers Extended" value="3 Pending" />
            <Metric icon={CheckSquare} label="Hiring Goal" value="80% Met" />
          </>
        )}

        {isMarketing && (
          <>
            <Metric icon={Megaphone} label="Campaigns" value={loading ? "..." : summary.campaigns} />
            <Metric icon={TrendingUp} label="Open Rates" value="24.5% Avg" />
            <Metric icon={Mail} label="Total Sent" value="12.4K Emails" />
            <Metric icon={Users} label="Subscribers" value="1.8K New" />
          </>
        )}

        {isSupport && (
          <>
            <Metric icon={Ticket} label="Tickets" value="8 Open" />
            <Metric icon={Clock} label="Response Times" value="14m Avg" />
            <Metric icon={CheckCircle2} label="Resolved Today" value="36 Tickets" />
            <Metric icon={Users} label="CSAT Score" value="94%" />
          </>
        )}

        {/* Viewer role default */}
        {role === ROLES.VIEWER && (
          <>
            <Metric icon={Mail} label="Inbox Emails" value={loading ? "..." : summary.emails} />
            <Metric icon={Users} label="CRM Contacts" value={loading ? "..." : summary.contacts} />
            <div className="md:col-span-2 rounded-lg border border-white/10 bg-white/[0.03] p-4 flex items-center justify-center text-slate-400 text-sm">
              Standard Viewer access dashboard
            </div>
          </>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Live Metrics Widget - Restricted to Admin & Sales */}
        {(isAdmin || isSales) && (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 className="flex items-center gap-2 text-sm font-medium text-slate-300">
                <Radio size={16} className="text-cyan-300" /> Live Metrics
              </h3>
              <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-xs text-emerald-200">
                {connectionInfo?.active_connections ? "Connected" : "Ready"}
              </span>
            </div>
            {wsMetrics.loading ? (
              <div className="grid gap-3 sm:grid-cols-2">
                {Array.from({ length: 4 }).map((_, index) => (
                  <div key={index} className="h-20 animate-pulse rounded-md bg-white/[0.06]" />
                ))}
              </div>
            ) : live ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2">
                  <LiveMetric label="Open Deals" value={live.open_deals_count} />
                  <LiveMetric label="Won Deals" value={live.won_deals_count} />
                  <LiveMetric label="Pipeline Value" value={`$${Number(live.total_pipeline_value || 0).toLocaleString()}`} />
                  <LiveMetric label="At-Risk Territories" value={live.territories_at_risk} />
                </div>
                <div className="mt-4 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
                  <StatusLine icon={Activity} label="Forecast Month" value={live.forecast_month || "Current"} />
                  <StatusLine icon={CheckCircle2} label="Last Updated" value={formatTimestamp(live.timestamp)} />
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-400">Connect via WebSocket for live updates.</p>
            )}
            {connectionInfo && (
              <div className="mt-4 rounded-md bg-black/20 px-3 py-2 text-xs text-slate-400">
                <span className="text-slate-300">{connectionInfo.active_connections || 0}</span> active connection
                {(connectionInfo.active_connections || 0) === 1 ? "" : "s"} · Analytics{" "}
                <span className="text-slate-300">{connectionInfo.channels?.analytics || 0}</span> · Deals{" "}
                <span className="text-slate-300">{connectionInfo.channels?.deals || 0}</span>
              </div>
            )}
          </div>
        )}

        {/* Candidates & Interviews widget - Recruiter specific */}
        {isRecruiter && (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <h3 className="mb-4 text-sm font-medium text-slate-300">Upcoming Interviews</h3>
            <div className="space-y-3">
              <div className="rounded-md bg-black/20 px-3 py-2 text-sm flex justify-between items-center">
                <div>
                  <p className="font-medium text-slate-200">Sarah Jenkins — Frontend Dev</p>
                  <p className="text-xs text-slate-400">Technical Interview</p>
                </div>
                <span className="text-xs bg-cyan-400/20 text-cyan-200 px-2 py-1 rounded">10:00 AM</span>
              </div>
              <div className="rounded-md bg-black/20 px-3 py-2 text-sm flex justify-between items-center">
                <div>
                  <p className="font-medium text-slate-200">Michael Chang — Lead Architect</p>
                  <p className="text-xs text-slate-400">System Design Panel</p>
                </div>
                <span className="text-xs bg-cyan-400/20 text-cyan-200 px-2 py-1 rounded">2:30 PM</span>
              </div>
            </div>
          </div>
        )}

        {/* Tickets and Response Time widget - Support specific */}
        {isSupport && (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <h3 className="mb-4 text-sm font-medium text-slate-300">Urgent Support Tickets</h3>
            <div className="space-y-3">
              <div className="rounded-md bg-black/20 px-3 py-2 text-sm flex justify-between items-center">
                <div>
                  <p className="font-medium text-slate-200">Gmail Auth Token Expired</p>
                  <p className="text-xs text-slate-400">Tenant: Workspace 1</p>
                </div>
                <span className="text-xs bg-red-400/20 text-red-200 px-2 py-1 rounded">High Priority</span>
              </div>
              <div className="rounded-md bg-black/20 px-3 py-2 text-sm flex justify-between items-center">
                <div>
                  <p className="font-medium text-slate-200">Webhook Sync Latency</p>
                  <p className="text-xs text-slate-400">Tenant: Workspace 4</p>
                </div>
                <span className="text-xs bg-amber-400/20 text-amber-200 px-2 py-1 rounded">Medium Priority</span>
              </div>
            </div>
          </div>
        )}

        {/* AI Recommendations - Admin, Sales, Marketing */}
        {(isAdmin || isSales || isMarketing) && (
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
            <h3 className="mb-4 text-sm font-medium text-slate-300">AI Recommendations</h3>
            {recommendations.loading ? (
              <p className="text-sm text-slate-400">Loading...</p>
            ) : recs.length === 0 ? (
              <p className="text-sm text-slate-400">No pending recommendations.</p>
            ) : (
              <div className="space-y-2">
                {recs.map((r) => (
                  <div key={r.id} className="rounded-md bg-black/20 px-3 py-2 text-sm">
                    <p className="font-medium text-slate-200">{r.title}</p>
                    <p className="text-xs text-slate-400">{r.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Activity Chart - Restricted to Admin, Sales, Marketing */}
      {(isAdmin || isSales || isMarketing) && (
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <h3 className="mb-4 text-sm font-medium text-slate-300">Workspace Activity</h3>
          <div className="h-72 min-h-[18rem] min-w-0">
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
      )}
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

function LiveMetric({ label, value }) {
  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-100">{value ?? 0}</p>
    </div>
  );
}

function StatusLine({ icon: Icon, label, value }) {
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-md bg-black/20 px-3 py-2">
      <Icon size={14} className="shrink-0 text-cyan-300" />
      <span className="shrink-0 text-slate-500">{label}</span>
      <span className="min-w-0 truncate text-slate-300">{value}</span>
    </div>
  );
}

function formatTimestamp(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Just now";
  return date.toLocaleString();
}

