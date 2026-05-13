import { useEffect, useState } from "react";
import Sidebar from "../Components/Sidebar";
import API from "../srevices/api";
import { useAuth } from "../context/AuthContext";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from "recharts";
import { Mail, Send, AlertTriangle, FileText, CheckCircle, Chrome } from "lucide-react";
import { useSearchParams, useNavigate } from "react-router-dom";

export default function UserDashboard() {
  const { user, setUser } = useAuth();
  const [emails, setEmails] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();
  const [syncing, setSyncing] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const navigate = useNavigate();

  // Handle Google Callback Status
  useEffect(() => {
    const status = searchParams.get("status");
    if (status === "success") {
      // Update User Context to reflect connection
      const updatedUser = { ...user, gmail_connected: true };
      setUser(updatedUser);
      localStorage.setItem("user", JSON.stringify(updatedUser));
      // Remove query param
      navigate("/dashboard", { replace: true });
    } else if (status === "user_not_found") {
      localStorage.removeItem("user");
      localStorage.removeItem("token");
      setUser(null);
      navigate("/register?error=stale_session");
    }
  }, [searchParams, navigate, user, setUser]);

  // Fetch Data if Connected
  useEffect(() => {
    if (user?.gmail_connected) {
      fetchData();
    } else {
      setLoading(false);
    }
  }, [user]);

  const fetchData = async () => {
    try {
      const [historyRes, draftsRes, notifRes] = await Promise.all([
        API.get("/email/history"),
        API.get("/email/drafts"),
        API.get("/notifications")
      ]);
      setEmails(historyRes.data);
      setDrafts(draftsRes.data);
      setNotifications(notifRes.data);
    } catch (error) {
      console.error("Error fetching email data:", error);
    } finally {
      setLoading(false);
    }
  };

  const syncEmails = async () => {
    if (!user?.gmail_connected) return;
    setSyncing(true);
    try {
      await API.get("/email/sync");
      await fetchData();
    } catch (error) {
      console.error("Error syncing emails:", error);
    } finally {
      setSyncing(false);
    }
  };

  const connectGoogle = async () => {
    try {
      const res = await API.get(`/google/login?email=${user.email}`);
      window.location.href = res.data.url;
    } catch (err) {
      console.error("Failed to get auth url", err);
    }
  }

  // === VIEW: CONNECTED (DASHBOARD) ===

  // Metrics
  const totalEmails = emails.length;
  const sentCount = emails.filter(e => e.status === "SENT").length;
  const draftCount = drafts.length;
  const autoReplyRate = totalEmails > 0 ? ((sentCount / totalEmails) * 100).toFixed(0) : 0;

  const categoryData = Object.entries(emails.reduce((a, c) => (a[c.category] = (a[c.category] || 0) + 1, a), {})).map(([n, v]) => ({ name: n, value: v }));
  const actionData = Object.entries(emails.reduce((a, c) => (a[c.action] = (a[c.action] || 0) + 1, a), {})).map(([n, v]) => ({ name: n, value: v }));
  const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#0088fe"];

  if (loading) return <div className="text-white text-center mt-20">Loading...</div>

  return (
    <Sidebar>
      <div className="p-8 text-white max-w-7xl mx-auto">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">
              Dashboard
            </h1>
            <p className="text-slate-400">Welcome back, {user.name}</p>
          </div>
          <div className="flex items-center gap-4">
            {user?.gmail_connected ? (
              <>
                <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-4 py-2 rounded-full flex items-center gap-2 font-medium shadow-sm">
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_10px_#34d399]" />
                  Gmail Connected
                </span>
                <button
                  onClick={syncEmails}
                  disabled={syncing}
                  className={`px-4 py-2 ${syncing ? 'bg-slate-700' : 'bg-indigo-600 hover:bg-indigo-500'} text-white rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-95 font-medium flex items-center gap-2`}
                >
                  <Chrome size={18} className={syncing ? "animate-spin" : ""} />
                  {syncing ? "Syncing..." : "Sync Gmail"}
                </button>
              </>
            ) : (
              <button
                onClick={connectGoogle}
                className="px-4 py-2 bg-white text-slate-900 rounded-xl flex items-center gap-2 font-bold hover:bg-slate-200 transition-all shadow-lg shadow-white/10 active:scale-95"
              >
                <img src="https://www.svgrepo.com/show/475656/google-color.svg" className="w-5 h-5" alt="G" />
                Connect Gmail
              </button>
            )}
            <button
              onClick={fetchData}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl transition-all border border-slate-700 active:scale-95 font-medium"
            >
              Refresh
            </button>
          </div>
        </header>

        {/* ALERTS */}
        {notifications.length > 0 && (
          <div className="mb-8 space-y-3">
            {notifications.map(notif => (
              <div key={notif.id} className="bg-red-500/10 border border-red-500/20 p-4 rounded-2xl flex items-center justify-between animate-in fade-in slide-in-from-top-4 duration-500">
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-red-500/20 rounded-lg text-red-400">
                    <AlertTriangle size={20} />
                  </div>
                  <div>
                    <h4 className="font-bold text-red-400">{notif.title}</h4>
                    <p className="text-sm text-red-300/70">{notif.message}</p>
                  </div>
                </div>
                <button
                  onClick={() => API.get("/notifications")} // Just a dummy for now since we don't have update read
                  className="text-xs text-red-400/50 hover:text-red-400 underline"
                >
                  Dismiss
                </button>
              </div>
            ))}
          </div>
        )}

        {/* METRICS */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatCard title="Total Emails" value={totalEmails} icon={<Mail className="text-blue-400" size={24} />} color="blue" />
          <StatCard title="Auto-Replied" value={sentCount} icon={<Send className="text-emerald-400" size={24} />} color="green" />
          <StatCard title="Pending Drafts" value={draftCount} icon={<FileText className="text-amber-400" size={24} />} color="yellow" />
          <StatCard title="Automation Rate" value={`${autoReplyRate}%`} icon={<CheckCircle className="text-purple-400" size={24} />} color="purple" />
        </div>

        {/* CHARTS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 p-8 rounded-3xl shadow-xl">
            <h3 className="text-xl font-bold mb-6 text-white">Intent Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "12px", color: "#fff" }}
                  itemStyle={{ color: "#fff" }}
                  cursor={{ fill: '#334155', opacity: 0.2 }}
                />
                <Bar dataKey="value" fill="#6366f1" radius={[6, 6, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 p-8 rounded-3xl shadow-xl">
            <h3 className="text-xl font-bold mb-6 text-white">Action Breakdown</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={actionData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {actionData.map((e, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} stroke="rgba(0,0,0,0)" />)}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "12px", color: "#fff" }} />
                <Legend iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RECENT ACTIVITY */}
        <div className="bg-slate-900/50 backdrop-blur-md border border-slate-800 rounded-3xl p-8 shadow-xl">
          <h3 className="text-xl font-bold mb-6 text-white">Recent Activity</h3>
          <div className="space-y-4">
            {emails.slice(-5).reverse().map((email) => (
              <div key={email.id} className="flex items-center justify-between p-5 bg-slate-800/40 hover:bg-slate-800/60 transition-colors rounded-2xl border border-slate-700/50 group">
                <div className="flex items-center gap-5">
                  <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-slate-400 group-hover:bg-blue-500/20 group-hover:text-blue-400 transition-colors">
                    <Mail size={20} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white mb-1 group-hover:text-blue-400 transition-colors">{email.subject}</h4>
                    <p className="text-sm text-slate-400 flex items-center gap-2">
                      <span className="w-1 h-1 rounded-full bg-slate-500" /> {email.sender}
                      <span className="w-1 h-1 rounded-full bg-slate-500" /> {email.category}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-bold px-3 py-1.5 rounded-full border ${email.status === "SENT"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                    }`}>
                    {email.status}
                  </span>
                </div>
              </div>
            ))}
            {emails.length === 0 && (
              <div className="text-slate-500 text-center py-12 flex flex-col items-center gap-4">
                <div className="w-16 h-16 bg-slate-900 rounded-full flex items-center justify-center">
                  <Mail size={32} className="opacity-20" />
                </div>
                <p>No emails synced yet. Run the simulation script!</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Sidebar>
  );
}

function StatCard({ title, value, icon, color }) {
  const colorStyles = {
    blue: "from-blue-500/20 to-blue-600/5 border-blue-500/20",
    green: "from-emerald-500/20 to-emerald-600/5 border-emerald-500/20",
    yellow: "from-amber-500/20 to-amber-600/5 border-amber-500/20",
    purple: "from-purple-500/20 to-purple-600/5 border-purple-500/20"
  };

  return (
    <div className={`bg-gradient-to-br ${colorStyles[color]} border p-6 rounded-3xl shadow-lg backdrop-blur-sm relative overflow-hidden group`}>
      <div className="absolute top-0 right-0 w-24 h-24 bg-white/5 rounded-bl-[100px] -mr-4 -mt-4 transition-transform group-hover:scale-110" />
      <div className="relative z-10">
        <div className="flex justify-between items-start mb-4">
          <div className="p-3 bg-slate-950/50 rounded-2xl border border-white/5 shadow-inner">{icon}</div>
        </div>
        <h3 className="text-slate-400 text-sm font-medium mb-1">{title}</h3>
        <p className="text-4xl font-bold text-white tracking-tight">{value}</p>
      </div>
    </div>
  );
}
