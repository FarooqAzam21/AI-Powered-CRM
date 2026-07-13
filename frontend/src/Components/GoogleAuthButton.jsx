import { Loader2 } from "lucide-react";
import { useState } from "react";

import { startGoogleAuth } from "../hooks/useGoogleAuth";

export default function GoogleAuthButton({ intent = "login", label }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const text = label || (intent === "signup" ? "Sign up with Google" : "Continue with Google");

  async function handleClick() {
    setLoading(true);
    setError("");
    try {
      await startGoogleAuth(intent);
    } catch (err) {
      setError(err.response?.data?.detail || "Google sign-in is unavailable. Check GOOGLE_CLIENT_ID in backend .env");
      setLoading(false);
    }
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className="flex w-full items-center justify-center gap-3 rounded-2xl border border-slate-700 bg-white py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-100 disabled:opacity-50"
      >
        {loading ? (
          <Loader2 className="animate-spin" size={18} />
        ) : (
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303C33.654 32.657 29.223 36 24 36c-5.522 0-10-4.477-10-10s4.478-10 10-10c2.837 0 5.402 1.192 7.207 3.093l5.657-5.657C33.64 6.053 29.082 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z" />
            <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c2.837 0 5.402 1.192 7.207 3.093l5.657-5.657C33.64 6.053 29.082 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" />
            <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" />
            <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z" />
          </svg>
        )}
        {loading ? "Redirecting..." : text}
      </button>
      {error && <p className="text-center text-xs text-red-400">{error}</p>}
    </div>
  );
}
