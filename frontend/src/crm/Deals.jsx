import { useState } from "react";
import { DollarSign, Plus, TrendingUp } from "lucide-react";

import {
  closeDeal,
  createDeal,
  getDealPipelineSummary,
  getDeals,
  updateDeal,
} from "./api";
import useApiResource from "./useApiResource";

const STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"];

export default function Deals() {
  const { data: deals, loading, error, refresh } = useApiResource(getDeals, []);
  const { data: summary, loading: summaryLoading } = useApiResource(getDealPipelineSummary, []);
  const [form, setForm] = useState({ name: "", value: "", stage: "prospecting" });
  const [busy, setBusy] = useState(false);

  const rows = deals || [];
  const pipe = summary || {};

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.name || !form.value) return;
    setBusy(true);
    try {
      await createDeal({ name: form.name, value: Number(form.value), stage: form.stage });
      setForm({ name: "", value: "", stage: "prospecting" });
      refresh();
    } finally {
      setBusy(false);
    }
  }

  async function moveStage(id, stage) {
    await updateDeal(id, { stage });
    refresh();
  }

  async function handleClose(id, won) {
    await closeDeal(id, won);
    refresh();
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Deals</h2>
        <p className="text-sm text-slate-400">Create, track, and close deals via the Phase 6 pipeline API.</p>
      </div>

      {error && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <Stat icon={TrendingUp} label="Total Deals" value={summaryLoading ? "..." : pipe.total_deals ?? 0} />
        <Stat icon={DollarSign} label="Pipeline Value" value={summaryLoading ? "..." : `$${Number(pipe.total_pipeline_value || 0).toLocaleString()}`} />
        <Stat icon={DollarSign} label="Avg Deal" value={summaryLoading ? "..." : `$${Number(pipe.avg_deal_value || 0).toLocaleString()}`} />
        <Stat icon={TrendingUp} label="Weighted Forecast" value={summaryLoading ? "..." : `$${Number(pipe.weighted_forecast || 0).toLocaleString()}`} />
      </div>

      <form onSubmit={handleCreate} className="grid gap-3 rounded-lg border border-white/10 bg-white/[0.03] p-4 md:grid-cols-4">
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Deal name"
          className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
        />
        <input
          type="number"
          value={form.value}
          onChange={(e) => setForm({ ...form, value: e.target.value })}
          placeholder="Value ($)"
          className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
        />
        <select
          value={form.stage}
          onChange={(e) => setForm({ ...form, stage: e.target.value })}
          className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none focus:border-cyan-400"
        >
          {STAGES.map((s) => (
            <option key={s} value={s}>{s.replace("_", " ")}</option>
          ))}
        </select>
        <button disabled={busy} type="submit" className="flex items-center justify-center gap-2 rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">
          <Plus size={16} /> Add Deal
        </button>
      </form>

      <div className="rounded-lg border border-white/10 bg-white/[0.03]">
        {loading ? (
          <p className="p-4 text-sm text-slate-400">Loading deals...</p>
        ) : rows.length === 0 ? (
          <p className="p-4 text-sm text-slate-400">No deals yet. Create your first deal above.</p>
        ) : (
          <div className="divide-y divide-white/5">
            {rows.map((deal) => (
              <div key={deal.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <p className="font-medium text-slate-100">{deal.name}</p>
                  <p className="text-xs text-slate-400">
                    ${Number(deal.value).toLocaleString()} · {deal.status} · {Math.round(deal.probability * 100)}% prob
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={deal.stage}
                    onChange={(e) => moveStage(deal.id, e.target.value)}
                    className="rounded-md border border-white/10 bg-black/20 px-2 py-1 text-xs"
                  >
                    {STAGES.map((s) => (
                      <option key={s} value={s}>{s.replace("_", " ")}</option>
                    ))}
                  </select>
                  {deal.status === "open" && (
                    <>
                      <button onClick={() => handleClose(deal.id, true)} className="rounded-md bg-emerald-500/20 px-2 py-1 text-xs text-emerald-300">Won</button>
                      <button onClick={() => handleClose(deal.id, false)} className="rounded-md bg-rose-500/20 px-2 py-1 text-xs text-rose-300">Lost</button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Stat({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
      <Icon className="mb-3 text-cyan-300" size={20} />
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}
