import { getInsights } from "./api";
import useApiResource from "./useApiResource";

export default function AIInsights() {
  const { data, loading, error } = useApiResource(getInsights, []);
  const insights = data || [];

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">AI Insights</h2>
        <p className="text-sm text-slate-400">Automated intelligence generated from CRM activity and email signals.</p>
      </div>
      {error && <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">{error}</div>}
      {loading ? (
        <p className="text-sm text-slate-400">Loading insights...</p>
      ) : insights.length === 0 ? (
        <p className="text-sm text-slate-400">No AI insights yet. Insights appear as the system analyzes contacts and emails.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {insights.map((item) => (
            <div key={item.id} className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs uppercase tracking-wide text-cyan-300">{item.insight_type}</span>
                <span className="text-xs text-slate-400">{Math.round((item.confidence || 0) * 100)}% confidence</span>
              </div>
              <pre className="whitespace-pre-wrap text-sm text-slate-200">{item.payload}</pre>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
