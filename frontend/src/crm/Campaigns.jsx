import { BarChart3, Mail, MousePointerClick, Send } from "lucide-react";
import { useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import {
  createCampaign,
  getCampaignAnalytics,
  getCampaignProgress,
  getCampaignSends,
  getCampaigns,
  startCampaign,
} from "./api";
import useApiResource from "./useApiResource";

export default function Campaigns() {
  const { data, refresh } = useApiResource(getCampaigns, []);
  const [form, setForm] = useState({ name: "", subject: "", template: "", recipients: "" });
  const [startingId, setStartingId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [progress, setProgress] = useState(null);
  const [sends, setSends] = useState([]);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  async function submit(event) {
    event.preventDefault();
    await createCampaign({ ...form, recipients: form.recipients.split(/\s*,\s*/).filter(Boolean) });
    setForm({ name: "", subject: "", template: "", recipients: "" });
    refresh();
  }

  async function handleStart(id) {
    setStartingId(id);
    try {
      await startCampaign(id);
      refresh();
      if (selectedId === id) await loadAnalytics(id);
    } finally {
      setStartingId(null);
    }
  }

  async function loadAnalytics(id) {
    setSelectedId(id);
    setLoadingAnalytics(true);
    setAnalyticsError("");
    const campaign = (data || []).find((c) => c.id === id);

    try {
      const [analyticsData, progressData, sendsData] = await Promise.all([
        getCampaignAnalytics(id).catch(() => null),
        getCampaignProgress(id).catch(() => null),
        getCampaignSends(id, { limit: 20 }).catch(() => []),
      ]);
      setAnalytics(
        analyticsData || {
          name: campaign?.name,
          status: campaign?.status,
          sent_count: campaign?.sent_count || 0,
          opened_count: campaign?.open_count || 0,
          clicked_count: 0,
          open_rate: 0,
          click_rate: 0,
          bounce_rate: 0,
        }
      );
      setProgress(progressData);
      setSends(Array.isArray(sendsData) ? sendsData : sendsData?.items || []);
    } catch (err) {
      setAnalyticsError(err.response?.data?.detail || "Analytics unavailable for this campaign.");
      setAnalytics(null);
      setProgress(null);
      setSends([]);
    } finally {
      setLoadingAnalytics(false);
    }
  }

  const chart = analytics
    ? [
        { name: "Sent", value: analytics.sent_count || 0 },
        { name: "Opened", value: analytics.opened_count || 0 },
        { name: "Clicked", value: analytics.clicked_count || 0 },
        { name: "Failed", value: analytics.failed_count || 0 },
      ]
    : [];

  return (
    <section className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <form onSubmit={submit} className="space-y-3 rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <h2 className="text-xl font-semibold">Campaign Builder</h2>
          {["name", "subject", "recipients"].map((field) => (
            <input
              key={field}
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              placeholder={field}
              className="w-full rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
            />
          ))}
          <textarea
            value={form.template}
            onChange={(e) => setForm({ ...form, template: e.target.value })}
            placeholder="Template with {{email}} variables"
            className="h-36 w-full rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
          />
          <button className="w-full rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950">Create Campaign</button>
        </form>

        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <h2 className="mb-4 text-xl font-semibold">Campaigns</h2>
          {(data || []).map((campaign) => (
            <div
              key={campaign.id}
              className={`mb-3 grid gap-2 rounded-md p-3 md:grid-cols-[1fr_90px_90px_90px_100px_100px] ${
                selectedId === campaign.id ? "bg-cyan-400/10" : "bg-black/20"
              }`}
            >
              <button onClick={() => loadAnalytics(campaign.id)} className="text-left">
                <p className="font-medium">{campaign.name}</p>
                <p className="text-xs text-slate-400">Click for Phase 9 analytics</p>
              </button>
              <p className="text-sm text-slate-400">{campaign.status}</p>
              <p className="text-sm text-slate-400">Sent {campaign.sent_count}</p>
              <p className="text-sm text-slate-400">Replies {campaign.reply_count}</p>
              {campaign.status === "draft" && (
                <button
                  onClick={() => handleStart(campaign.id)}
                  disabled={startingId === campaign.id}
                  className="rounded bg-cyan-400 px-2 py-1 text-xs font-medium text-slate-950 disabled:opacity-50"
                >
                  {startingId === campaign.id ? "Starting..." : "Start"}
                </button>
              )}
              <button
                onClick={() => loadAnalytics(campaign.id)}
                className="rounded border border-white/10 px-2 py-1 text-xs text-cyan-300 hover:bg-white/5"
              >
                Analytics
              </button>
            </div>
          ))}
        </div>
      </div>

      {selectedId && (
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="text-cyan-300" size={20} />
            <h2 className="text-xl font-semibold">Phase 9 Campaign Analytics</h2>
          </div>
          {analyticsError && <p className="mb-3 text-sm text-amber-200">{analyticsError}</p>}
          {loadingAnalytics ? (
            <p className="text-sm text-slate-400">Loading analytics...</p>
          ) : analytics ? (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-4">
                <Metric icon={Send} label="Sent" value={analytics.sent_count || 0} />
                <Metric icon={Mail} label="Open Rate" value={`${analytics.open_rate || 0}%`} />
                <Metric icon={MousePointerClick} label="Click Rate" value={`${analytics.click_rate || 0}%`} />
                <Metric icon={BarChart3} label="Bounce Rate" value={`${analytics.bounce_rate || 0}%`} />
              </div>

              {progress && (
                <div className="rounded-md bg-black/20 p-4 text-sm">
                  <p className="text-slate-300">
                    Progress: {progress.progress_percent ?? 0}% · Status: {progress.status || analytics.status}
                  </p>
                  {progress.pending != null && (
                    <p className="text-slate-400">Pending: {progress.pending} · Failed: {progress.failed || 0}</p>
                  )}
                </div>
              )}

              <div className="h-56 min-h-[14rem] min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chart}>
                    <XAxis dataKey="name" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" allowDecimals={false} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,.1)" }} />
                    <Bar dataKey="value" fill="#22d3ee" radius={[5, 5, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {sends.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-slate-300">Recent Sends</h3>
                  <div className="space-y-2">
                    {sends.map((send) => (
                      <div key={send.id} className="flex items-center justify-between rounded-md bg-black/20 px-3 py-2 text-sm">
                        <span className="text-slate-200">{send.recipient_email}</span>
                        <span className="text-slate-400">{send.status?.value || send.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-4">
      <Icon className="mb-3 text-cyan-300" size={18} />
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
