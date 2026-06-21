import { useState } from "react";

import { getLeads, getPipeline } from "./api";
import useApiResource from "./useApiResource";

export default function Pipelines() {
  const [view, setView] = useState("leads");
  const { data: leads, loading: leadsLoading } = useApiResource(getLeads, []);
  const { data: pipeline, loading: pipelineLoading } = useApiResource(getPipeline, []);
  const leadRows = leads || [];
  const stages = pipeline || [];

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Pipelines</h2>
          <p className="text-sm text-slate-400">Lead scoring buckets and deal-stage pipeline from CRM data.</p>
        </div>
        <div className="flex gap-2 rounded-md border border-white/10 p-1">
          {["leads", "deals"].map((tab) => (
            <button
              key={tab}
              onClick={() => setView(tab)}
              className={`rounded px-3 py-1.5 text-sm capitalize ${view === tab ? "bg-cyan-400 text-slate-950" : "text-slate-300 hover:bg-white/5"}`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {view === "leads" ? (
        <div className="grid gap-4 md:grid-cols-3">
          {["hot", "warm", "cold"].map((label) => (
            <div key={label} className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
              <h3 className="mb-3 capitalize text-slate-300">{label}</h3>
              {leadsLoading ? (
                "Loading..."
              ) : (
                leadRows
                  .filter((lead) => lead.label === label)
                  .map((lead) => (
                    <div key={lead.id} className="mb-3 rounded-md bg-black/20 p-3">
                      <p className="text-sm font-medium">Lead #{lead.id}</p>
                      <p className="text-xs text-slate-400">
                        Score {lead.score} - {lead.recommended_next_action}
                      </p>
                    </div>
                  ))
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {pipelineLoading ? (
            <p className="text-sm text-slate-400">Loading deal pipeline...</p>
          ) : stages.length === 0 ? (
            <p className="text-sm text-slate-400">No deals in pipeline yet.</p>
          ) : (
            stages.map((stage) => (
              <div key={stage.stage} className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
                <h3 className="mb-2 capitalize text-slate-300">{stage.stage}</h3>
                <p className="text-2xl font-semibold">{stage.count}</p>
                <p className="text-sm text-slate-400">${Number(stage.value || 0).toLocaleString()} total value</p>
              </div>
            ))
          )}
        </div>
      )}
    </section>
  );
}
