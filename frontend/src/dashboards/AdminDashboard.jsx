import { useEffect, useState } from "react";
import Sidebar from "../Components/Sidebar";
import API from "../srevices/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { Mail, Send, AlertTriangle, FileText, CheckCircle } from "lucide-react";

export default function AdminDashboard() {
  const [emails, setEmails] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [historyRes, draftsRes] = await Promise.all([
        API.get("/email/history"),
        API.get("/email/drafts"),
      ]);
      setEmails(historyRes.data);
      setDrafts(draftsRes.data);
    } catch (error) {
      console.error("Error fetching email data:", error);
    } finally {
      setLoading(false);
    }
  };

  // Metrics
  const totalEmails = emails.length;
  const sentCount = emails.filter(e => e.status === "SENT").length;
  const draftCount = drafts.length;
  const autoReplyRate = totalEmails > 0 ? ((sentCount / totalEmails) * 100).toFixed(0) : 0;

  // Chart Data
  const categoryData = Object.entries(
    emails.reduce((acc, curr) => {
      acc[curr.category] = (acc[curr.category] || 0) + 1;
      return acc;
    }, {})
  ).map(([name, value]) => ({ name, value }));

  const actionData = Object.entries(
    emails.reduce((acc, curr) => {
      acc[curr.action] = (acc[curr.action] || 0) + 1;
      return acc;
    }, {})
  ).map(([name, value]) => ({ name, value }));

  const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff8042", "#0088fe"];

  if (loading) return <div className="flex h-screen items-center justify-center bg-slate-900 text-white">Loading Agent...</div>;

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      <Sidebar items={["Inbox", "Drafts", "Configuration"]} />

      <div className="flex-1 p-8 overflow-y-auto text-white">
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
              Executive Inbox
            </h1>
            <p className="text-slate-400">AI Agent Overview</p>
          </div>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
          >
            Refresh
          </button>
        </header>

        {/* METRICS */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatCard title="Total Emails" value={totalEmails} icon={<Mail className="text-blue-400" />} color="blue" />
          <StatCard title="Auto-Replied" value={sentCount} icon={<Send className="text-green-400" />} color="green" />
          <StatCard title="Pending Drafts" value={draftCount} icon={<FileText className="text-yellow-400" />} color="yellow" />
          <StatCard title="Automation Rate" value={`${autoReplyRate}%`} icon={<CheckCircle className="text-purple-400" />} color="purple" />
        </div>

        {/* CHARTS */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <ChartContainer title="Intent Distribution">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155" }} />
                <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartContainer>

          <ChartContainer title="Action Breakdown">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={actionData}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {actionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155" }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </ChartContainer>
        </div>

        {/* RECENT ACTIVITY */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
          <h3 className="text-xl font-semibold mb-4 text-slate-200">Recent Activity</h3>
          <div className="space-y-4">
            {emails.slice(-5).reverse().map((email) => (
              <div key={email.id} className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-full ${getActionColor(email.action)}`}>
                    {getActionIcon(email.action)}
                  </div>
                  <div>
                    <h4 className="font-semibold text-white">{email.subject}</h4>
                    <p className="text-sm text-slate-400">{email.category} • {email.sender}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-xs font-bold px-2 py-1 rounded-full ${email.status === "SENT" ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"
                    }`}>
                    {email.status}
                  </span>
                  <p className="text-xs text-slate-500 mt-1">{new Date(email.received_at).toLocaleTimeString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Helpers
function StatCard({ title, value, icon, color }) {
  const colorMap = {
    blue: "border-blue-500/20",
    green: "border-green-500/20",
    yellow: "border-yellow-500/20",
    purple: "border-purple-500/20",
  };
  return (
    <div className={`bg-slate-900 border ${colorMap[color]} p-6 rounded-2xl shadow-xl`}>
      <div className="flex justify-between items-start mb-4">
        <div className="p-2 bg-slate-800 rounded-lg">{icon}</div>
      </div>
      <h3 className="text-slate-400 text-sm font-medium">{title}</h3>
      <p className="text-3xl font-bold mt-1">{value}</p>
    </div>
  );
}

function ChartContainer({ title, children }) {
  return (
    <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl shadow-xl">
      <h3 className="text-xl font-semibold mb-6 text-slate-200">{title}</h3>
      {children}
    </div>
  );
}

function getActionColor(action) {
  switch (action) {
    case "REPLY_IMMEDIATELY": return "bg-green-500/20 text-green-400";
    case "DRAFT_RESPONSE": return "bg-yellow-500/20 text-yellow-400";
    case "ESCALATE": return "bg-red-500/20 text-red-400";
    default: return "bg-slate-700 text-slate-400";
  }
}

function getActionIcon(action) {
  switch (action) {
    case "REPLY_IMMEDIATELY": return <Send size={18} />;
    case "DRAFT_RESPONSE": return <FileText size={18} />;
    case "ESCALATE": return <AlertTriangle size={18} />;
    default: return <Mail size={18} />;
  }
}
