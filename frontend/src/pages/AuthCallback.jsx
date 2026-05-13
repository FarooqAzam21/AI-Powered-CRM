import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Loader2 } from "lucide-react";

export default function AuthCallback() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { ssoLogin } = useAuth();

    useEffect(() => {
        const token = searchParams.get("token");
        if (token) {
            const success = ssoLogin(token);
            if (success) {
                navigate("/dashboard");
            } else {
                navigate("/login?error=invalid_token");
            }
        } else {
            navigate("/login?error=no_token");
        }
    }, [searchParams, navigate, ssoLogin]);

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center flex-col gap-4">
            <Loader2 className="animate-spin text-green-500" size={48} />
            <p className="text-slate-400">Authenticating...</p>
        </div>
    );
}
