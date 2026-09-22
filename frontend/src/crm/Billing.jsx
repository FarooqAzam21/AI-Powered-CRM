import { useState, useEffect } from "react";
import {
  CreditCard,
  Check,
  X,
  Zap,
  Shield,
  AlertTriangle,
  Clock,
  Sparkles,
  ArrowUpRight,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import {
  getBillingPlans,
  getBillingSubscription,
  getBillingUsage,
  subscribePlan,
  cancelSubscription,
  startBillingTrial,
  getBillingHistory,
} from "./api";

export default function Billing() {
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState([]);
  const [subscription, setSubscription] = useState(null);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [usageData, setUsageData] = useState(null);
  const [history, setHistory] = useState([]);
  const [billingCycle, setBillingCycle] = useState("month"); // 'month' or 'year'
  const [actionLoading, setActionLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [plansRes, subRes, usageRes, histRes] = await Promise.all([
        getBillingPlans(),
        getBillingSubscription(),
        getBillingUsage(),
        getBillingHistory().catch(() => []),
      ]);
      setPlans(plansRes);
      setSubscription(subRes.subscription);
      setCurrentPlan(subRes.plan);
      setUsageData(usageRes.usage || {});
      setHistory(histRes);
    } catch (err) {
      console.error("Failed to load billing data", err);
      setMessage({ type: "error", text: "Failed to load billing details." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubscribe = async (planSlug) => {
    try {
      setActionLoading(true);
      setMessage(null);
      const res = await subscribePlan({ plan_slug: planSlug, interval: billingCycle });
      setMessage({ type: "success", text: res.message || "Plan updated successfully!" });
      await loadData();
    } catch (err) {
      const errDetail = err?.response?.data?.detail;
      const msg = typeof errDetail === "string" ? errDetail : "Failed to change subscription plan.";
      setMessage({ type: "error", text: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartTrial = async (planSlug) => {
    try {
      setActionLoading(true);
      setMessage(null);
      const res = await startBillingTrial({ plan_slug: planSlug });
      setMessage({ type: "success", text: res.message || "Trial started successfully!" });
      await loadData();
    } catch (err) {
      const errDetail = err?.response?.data?.detail;
      const msg = typeof errDetail === "string" ? errDetail : "Failed to start trial.";
      setMessage({ type: "error", text: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async () => {
    try {
      setActionLoading(true);
      setMessage(null);
      await cancelSubscription();
      setMessage({ type: "success", text: "Subscription scheduled for cancellation at end of period." });
      setCancelConfirmOpen(false);
      await loadData();
    } catch (err) {
      setMessage({ type: "error", text: "Failed to cancel subscription." });
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[450px] items-center justify-center">
        <div className="flex items-center gap-3 text-cyan-400 font-medium">
          <RefreshCw className="animate-spin" size={20} />
          Loading billing portal...
        </div>
      </div>
    );
  }

  const isTrial = subscription?.status === "trial";
  let trialDaysLeft = 0;
  if (isTrial && subscription?.trial_end) {
    const diffTime = new Date(subscription.trial_end) - new Date();
    trialDaysLeft = Math.max(0, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case "active":
        return <span className="rounded-full bg-emerald-500/15 border border-emerald-500/30 px-3 py-0.5 text-xs font-semibold text-emerald-300">Active</span>;
      case "trial":
        return <span className="rounded-full bg-amber-500/15 border border-amber-500/30 px-3 py-0.5 text-xs font-semibold text-amber-300">Free Trial</span>;
      case "canceled":
        return <span className="rounded-full bg-rose-500/15 border border-rose-500/30 px-3 py-0.5 text-xs font-semibold text-rose-300">Canceled</span>;
      case "expired":
        return <span className="rounded-full bg-red-500/20 border border-red-500/40 px-3 py-0.5 text-xs font-semibold text-red-300">Expired</span>;
      default:
        return <span className="rounded-full bg-slate-500/20 border border-slate-500/30 px-3 py-0.5 text-xs font-semibold text-slate-300">{status}</span>;
    }
  };

  const resourceLabels = {
    contacts: "Contacts Directory",
    users: "Team Members",
    workspaces: "Workspaces",
    deals: "Active Deals",
    emails: "Monthly Emails",
    campaigns: "Marketing Campaigns",
    ai_requests: "AI Requests / Inferences",
    api_requests: "API Calls / min",
    storage_mb: "Cloud Storage (MB)",
    automations: "Active Automations",
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <CreditCard className="text-cyan-400" size={26} />
            Subscription & Enterprise Billing
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Manage organization plan tiers, quotas, feature entitlements, and payment preferences.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={actionLoading}
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-white/10 transition"
        >
          <RefreshCw size={14} className={actionLoading ? "animate-spin" : ""} />
          Refresh Status
        </button>
      </div>

      {/* Messages */}
      {message && (
        <div
          className={`flex items-center gap-3 rounded-xl border p-4 text-sm ${
            message.type === "success"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-200"
              : "border-rose-500/30 bg-rose-500/10 text-rose-200"
          }`}
        >
          {message.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Trial Countdown Alert */}
      {isTrial && trialDaysLeft <= 7 && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-amber-200">
          <div className="flex items-center gap-3">
            <Clock className="text-amber-400" size={22} />
            <div>
              <p className="text-sm font-semibold text-white">
                Free Trial Expiring Soon ({trialDaysLeft} days remaining)
              </p>
              <p className="text-xs text-amber-300/80">
                Upgrade now to avoid interruption of AI models, automations, and team quotas.
              </p>
            </div>
          </div>
          <button
            onClick={() => handleSubscribe("starter")}
            className="rounded-lg bg-amber-500 px-3.5 py-1.5 text-xs font-semibold text-slate-950 hover:bg-amber-400 transition"
          >
            Upgrade Plan
          </button>
        </div>
      )}

      {/* Overview Cards: Current Plan & Quota High-level */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Current Plan Card */}
        <div className="lg:col-span-1 rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-cyan-950/30 to-[#0c111d] p-6 shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
            <Sparkles size={120} className="text-cyan-400" />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-cyan-400">Current Plan</span>
            {getStatusBadge(subscription?.status)}
          </div>

          <h3 className="text-3xl font-extrabold text-white mt-3">{currentPlan?.name || "Free"}</h3>
          <p className="text-xs text-slate-400 mt-1">{currentPlan?.description}</p>

          <div className="mt-6 pt-4 border-t border-white/10 flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">
              ${billingCycle === "year" ? currentPlan?.price_yearly : currentPlan?.price_monthly}
            </span>
            <span className="text-xs text-slate-400">/{billingCycle === "year" ? "yr" : "mo"}</span>
          </div>

          <div className="mt-4 space-y-2 text-xs text-slate-300">
            {subscription?.current_period_end && (
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Renewal Date</span>
                <span>{new Date(subscription.current_period_end).toLocaleDateString()}</span>
              </div>
            )}
            {isTrial && subscription?.trial_end && (
              <div className="flex justify-between py-1 border-b border-white/5">
                <span className="text-slate-400">Trial Ends</span>
                <span className="text-amber-400">{new Date(subscription.trial_end).toLocaleDateString()}</span>
              </div>
            )}
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Billing Admin</span>
              <span className="text-slate-200">Authorized</span>
            </div>
          </div>

          {subscription?.status === "active" && (
            <div className="mt-6">
              <button
                onClick={() => setCancelConfirmOpen(true)}
                className="w-full text-center text-xs text-rose-400 hover:text-rose-300 transition py-1"
              >
                Cancel Subscription
              </button>
            </div>
          )}
        </div>

        {/* Quota Usage Metrics Dashboard */}
        <div className="lg:col-span-2 rounded-2xl border border-white/10 bg-[#0c111d] p-6 shadow-xl">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Zap className="text-amber-400" size={18} />
              Resource Usage & Quotas
            </h3>
            <span className="text-xs text-slate-400">Current cycle limits</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(usageData).map(([resourceKey, metric]) => {
              const label = resourceLabels[resourceKey] || resourceKey;
              const isUnlimited = metric.unlimited || metric.limit === -1;
              const pct = metric.percentage || 0;
              let barColor = "bg-cyan-400";
              if (pct >= 90) barColor = "bg-rose-500";
              else if (pct >= 70) barColor = "bg-amber-400";

              return (
                <div key={resourceKey} className="rounded-xl border border-white/5 bg-white/[0.02] p-3.5 space-y-2">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-slate-300">{label}</span>
                    <span className="text-slate-400">
                      {metric.used.toLocaleString()} /{" "}
                      {isUnlimited ? (
                        <span className="text-cyan-400 font-semibold">∞ Unlimited</span>
                      ) : (
                        metric.limit.toLocaleString()
                      )}
                    </span>
                  </div>

                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${barColor} transition-all duration-500`}
                      style={{ width: isUnlimited ? "15%" : `${Math.min(100, pct)}%` }}
                    />
                  </div>

                  {!isUnlimited && (
                    <div className="flex justify-between text-[11px] text-slate-500">
                      <span>{pct}% utilized</span>
                      <span>{metric.remaining.toLocaleString()} remaining</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Plan Tier Selector */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white">Available Plans</h3>
            <p className="text-xs text-slate-400">Choose the ideal tier for your team size and usage volume.</p>
          </div>

          {/* Monthly / Yearly Switcher */}
          <div className="flex items-center self-start sm:self-auto bg-slate-900 border border-white/10 p-1 rounded-xl">
            <button
              onClick={() => setBillingCycle("month")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                billingCycle === "month" ? "bg-cyan-500 text-slate-950 shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle("year")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
                billingCycle === "year" ? "bg-cyan-500 text-slate-950 shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              Yearly
              <span className="text-[10px] uppercase font-extrabold bg-emerald-400/20 text-emerald-300 px-1.5 py-0.5 rounded-md border border-emerald-400/30">
                Save 17%
              </span>
            </button>
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => {
            const isCurrent = currentPlan?.slug === plan.slug;
            const isPopular = plan.slug === "professional";
            const price = billingCycle === "year" ? plan.price_yearly : plan.price_monthly;

            return (
              <div
                key={plan.slug}
                className={`rounded-2xl border p-6 flex flex-col justify-between transition-all duration-200 relative ${
                  isPopular
                    ? "border-cyan-400/50 bg-gradient-to-b from-cyan-950/20 to-[#0c111d] shadow-lg shadow-cyan-950/30"
                    : "border-white/10 bg-[#0c111d] hover:border-white/20"
                }`}
              >
                {isPopular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-cyan-500 to-blue-500 text-slate-950 text-[10px] font-black uppercase tracking-widest px-3 py-0.5 rounded-full shadow">
                    Most Popular
                  </div>
                )}

                <div>
                  <div className="flex justify-between items-start">
                    <h4 className="text-lg font-bold text-white">{plan.name}</h4>
                    {isCurrent && (
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-cyan-400/10 text-cyan-300 border border-cyan-400/20">
                        Current
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-2 min-h-[36px]">{plan.description}</p>

                  <div className="mt-5 mb-6">
                    <span className="text-3xl font-extrabold text-white">${price}</span>
                    <span className="text-xs text-slate-400">/{billingCycle === "year" ? "yr" : "mo"}</span>
                  </div>

                  <div className="space-y-2.5 pt-4 border-t border-white/10 text-xs">
                    <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Features included:</p>
                    {plan.slug === "enterprise" ? (
                      <div className="flex items-center gap-2 text-slate-200 font-medium">
                        <Check size={14} className="text-cyan-400" />
                        <span>All features & unlimited scale</span>
                      </div>
                    ) : (
                      (plan.features || []).map((feat) => (
                        <div key={feat} className="flex items-center gap-2 text-slate-300">
                          <Check size={14} className="text-cyan-400 shrink-0" />
                          <span>{feat.replace(/_/g, " ")}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-white/5">
                  {isCurrent ? (
                    <button
                      disabled
                      className="w-full rounded-xl bg-white/5 py-2.5 text-xs font-semibold text-slate-400 border border-white/10 cursor-not-allowed"
                    >
                      Active Plan
                    </button>
                  ) : (
                    <div className="space-y-2">
                      <button
                        onClick={() => handleSubscribe(plan.slug)}
                        disabled={actionLoading}
                        className={`w-full rounded-xl py-2.5 text-xs font-semibold transition flex items-center justify-center gap-1.5 ${
                          isPopular
                            ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-md font-bold"
                            : "bg-white/10 text-white hover:bg-white/20 border border-white/10"
                        }`}
                      >
                        <Sparkles size={14} />
                        Upgrade to {plan.name}
                      </button>

                      {plan.slug !== "free" && !subscription?.trial_start && (
                        <button
                          onClick={() => handleStartTrial(plan.slug)}
                          disabled={actionLoading}
                          className="w-full text-center text-[11px] text-cyan-400 hover:text-cyan-300 transition py-1"
                        >
                          Start {plan.trial_days}-Day Trial
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Subscription Audit History */}
      {history.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-[#0c111d] p-6 shadow-xl space-y-4">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Shield className="text-cyan-400" size={18} />
            Subscription Audit Trail
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="border-b border-white/10 text-slate-500 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-2.5 px-3">Event</th>
                  <th className="py-2.5 px-3">Details</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {history.map((item) => (
                  <tr key={item.id} className="hover:bg-white/[0.02]">
                    <td className="py-2.5 px-3 font-semibold text-white uppercase">{item.event_type.replace(/_/g, " ")}</td>
                    <td className="py-2.5 px-3 text-slate-400">{item.notes || "—"}</td>
                    <td className="py-2.5 px-3 text-slate-500">
                      {item.created_at ? new Date(item.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Cancellation Confirmation Modal */}
      {cancelConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-[#0c111d] p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle size={24} />
              <h4 className="text-lg font-bold text-white">Cancel Subscription?</h4>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Your subscription will remain active until the end of your current billing period. After that, your organization will downgrade to the Free tier and excess limits may be constrained.
            </p>
            <div className="flex justify-end gap-3 pt-3">
              <button
                onClick={() => setCancelConfirmOpen(false)}
                className="rounded-lg border border-white/10 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-white/5 transition"
              >
                Keep Subscription
              </button>
              <button
                onClick={handleCancel}
                disabled={actionLoading}
                className="rounded-lg bg-rose-500 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-600 transition"
              >
                Confirm Cancellation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
