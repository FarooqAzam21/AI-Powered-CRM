import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, CheckCircle2 } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import API from "../srevices/api";

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { ssoLogin } = useAuth();
  const isNew = searchParams.get("new") === "1";
  const intent = searchParams.get("intent");

  useEffect(() => {
    async function finish() {
      const token = searchParams.get("token");
      const error = searchParams.get("error");

      if (error) {
        navigate(`/login?error=${error}`);
        return;
      }

      if (!token) {
        navigate("/login?error=no_token");
        return;
      }

      const ok = ssoLogin(token);
      if (!ok) {
        navigate("/login?error=invalid_token");
        return;
      }

      try {
        const { data } = await API.get("/auth/me");
        const stored = JSON.parse(localStorage.getItem("user") || "{}");
        localStorage.setItem("user", JSON.stringify({ ...stored, ...data, access_token: token }));
      } catch {
        // JWT payload is enough for session bootstrap
      }

      navigate("/dashboard", { replace: true, state: { welcome: isNew ? "google_signup" : intent } });
    }

    finish();
  }, [searchParams, navigate, ssoLogin, isNew, intent]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-950">
      {isNew ? <CheckCircle2 className="text-emerald-400" size={48} /> : <Loader2 className="animate-spin text-cyan-400" size={48} />}
      <p className="text-slate-400">{isNew ? "Account created — signing you in..." : "Authenticating with Google..."}</p>
    </div>
  );
}
