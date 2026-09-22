import { useState, useEffect } from "react";
import { Lock, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { getBillingFeatures } from "../api";

export default function FeatureGate({
  feature,
  requiredPlan = "Starter",
  children,
  fallback = null,
  showUpgradePrompt = true,
}) {
  const [features, setFeatures] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    getBillingFeatures()
      .then((data) => {
        if (isMounted) {
          setFeatures(data.features || []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setFeatures([]);
          setLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return <div className="opacity-50 pointer-events-none">{children}</div>;
  }

  const hasAccess = features && (features.includes("*") || features.includes(feature));

  if (hasAccess) {
    return children;
  }

  if (fallback) {
    return fallback;
  }

  if (!showUpgradePrompt) {
    return null;
  }

  return (
    <div className="relative rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 backdrop-blur-md">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Lock size={18} />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              Feature Locked
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                Requires {requiredPlan}
              </span>
            </h4>
            <p className="text-xs text-slate-400 mt-0.5">
              The <span className="text-amber-200 font-medium">{feature}</span> feature is available on the {requiredPlan} plan and above.
            </p>
          </div>
        </div>
        <button
          onClick={() => navigate("/billing")}
          className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 px-3 py-1.5 text-xs font-semibold text-white shadow-md hover:brightness-110 transition"
        >
          <Sparkles size={14} />
          Upgrade Plan
        </button>
      </div>
    </div>
  );
}
