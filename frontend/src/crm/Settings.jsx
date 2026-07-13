import { useAuth } from "../context/AuthContext";
import { startGoogleAuth } from "../hooks/useGoogleAuth";

export default function Settings() {
  const { user } = useAuth();

  async function connectGoogle() {
    await startGoogleAuth("login");
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Settings</h2>
        <p className="text-sm text-slate-400">OAuth, local AI model, and performance configuration.</p>
      </div>
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
        <p className="text-sm text-slate-400">Gmail status</p>
        <p className="mb-4 text-lg">{user?.gmail_connected ? "Connected" : "Not connected"}</p>
        <button onClick={connectGoogle} className="rounded-md bg-white px-3 py-2 text-sm font-medium text-slate-950">Connect Gmail</button>
      </div>
    </section>
  );
}
