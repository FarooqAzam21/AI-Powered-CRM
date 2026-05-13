import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { motion } from "framer-motion";
import { Mail, Lock, ChevronRight, AlertCircle } from "lucide-react";
import BackgroundParticles from "../Components/BackgroundParticles";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log("DEBUG: Login attempt for", email);
    setLoading(true);
    setError("");

    try {
      const result = await login(email, password);
      console.log("DEBUG: Login result:", result);

      if (result && result.success) {
        console.log("DEBUG: Login successful, navigating to dashboard...");
        navigate("/dashboard");
      } else {
        console.warn("DEBUG: Login failed:", result?.message);
        setError(result?.message || "Login failed");
        setLoading(false);
      }
    } catch (err) {
      console.error("DEBUG: CRITICAL LOGIN ERROR:", err);
      setError("Network error. Please make sure the backend is running at http://127.0.0.1:8000");
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center p-4">
      <BackgroundParticles />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800 p-8 rounded-3xl shadow-2xl relative overflow-hidden group">
          <div className="absolute -top-24 -left-24 w-48 h-48 bg-blue-500/10 blur-[80px]" />
          <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-green-500/10 blur-[80px]" />

          <div className="relative z-10">
            <h1 className="text-3xl font-bold text-white mb-2 text-center">Welcome Back</h1>
            <p className="text-slate-400 mb-8 text-center">Sign in to your AI Agent</p>

            {error && (
              <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400">
                <AlertCircle size={18} />
                <p className="text-sm font-medium">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300 ml-1">Email Address</label>
                <div className="relative group/input">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within/input:text-green-500 transition-colors">
                    <Mail size={18} />
                  </div>
                  <input
                    required
                    type="email"
                    className="w-full pl-12 pr-4 py-3 bg-slate-950/50 border border-slate-800 rounded-2xl focus:outline-none focus:ring-2 focus:ring-green-500/20 focus:border-green-500 transition-all text-white placeholder:text-slate-600"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-300 ml-1">Password</label>
                <div className="relative group/input">
                  <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within/input:text-green-500 transition-colors">
                    <Lock size={18} />
                  </div>
                  <input
                    required
                    type="password"
                    className="w-full pl-12 pr-4 py-3 bg-slate-950/50 border border-slate-800 rounded-2xl focus:outline-none focus:ring-2 focus:ring-green-500/20 focus:border-green-500 transition-all text-white placeholder:text-slate-600"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>

              <button
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 py-3 rounded-2xl font-bold flex items-center justify-center gap-2 group transition-all active:scale-[0.98] shadow-lg shadow-blue-500/20 disabled:opacity-50"
              >
                {loading ? "Signing in..." : "Sign In"}
                {!loading && <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />}
              </button>
            </form>

            <div className="mt-8 text-center space-y-4">
              <p className="text-slate-400 text-sm">
                Don't have an account?{" "}
                <button
                  type="button"
                  onClick={() => navigate("/register")}
                  className="text-white font-semibold hover:text-green-400 transition-colors underline decoration-slate-700 underline-offset-4"
                >
                  Create Account
                </button>
              </p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
