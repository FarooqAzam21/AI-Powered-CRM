import React from "react";
import { useNavigate } from "react-router-dom";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import BackgroundParticles from "../Components/BackgroundParticles";

export default function AccessDenied() {
  const navigate = useNavigate();

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4 bg-[#080b12] text-slate-100">
      <BackgroundParticles />
      
      <div className="w-full max-w-md bg-slate-900/50 backdrop-blur-xl border border-slate-800 p-8 rounded-3xl shadow-2xl text-center relative overflow-hidden group z-10">
        {/* Subtle red glow */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-red-500/10 blur-[80px] group-hover:bg-red-500/20 transition-colors duration-500" />
        
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-red-500/10 border border-red-500/30 rounded-2xl flex items-center justify-center text-red-400 shadow-lg shadow-red-500/10">
            <ShieldAlert size={36} />
          </div>
        </div>

        <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
        <p className="text-slate-400 text-sm mb-8 leading-relaxed">
          You do not have the required permissions to view this resource. 
          Please contact your workspace administrator if you believe this is an error.
        </p>

        <button
          onClick={() => navigate("/dashboard")}
          className="w-full bg-slate-800 hover:bg-slate-700 text-white py-3 rounded-2xl font-semibold flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
        >
          <ArrowLeft size={18} />
          Return to Dashboard
        </button>
      </div>
    </div>
  );
}
