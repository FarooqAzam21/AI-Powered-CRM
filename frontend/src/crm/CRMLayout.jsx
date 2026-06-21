import { NavLink, Outlet } from "react-router-dom";
import { BarChart3, Bot, Briefcase, Brain, Inbox, LayoutDashboard, Megaphone, Settings, UserCircle, Users } from "lucide-react";

import { useAuth } from "../context/AuthContext";

const nav = [
  ["Dashboard", "/dashboard", LayoutDashboard],
  ["Inbox", "/inbox", Inbox],
  ["Contacts", "/contacts", Users],
  ["Pipelines", "/pipelines", Briefcase],
  ["Campaigns", "/campaigns", Megaphone],
  ["Lead Profiles", "/lead-profiles", UserCircle],
  ["AI Insights", "/ai-insights", Brain],
  ["Analytics", "/analytics", BarChart3],
  ["AI Tasks", "/ai-tasks", Bot],
  ["Settings", "/settings", Settings],
];

export default function CRMLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[#080b12] text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-white/10 bg-[#0c111d] lg:block">
        <div className="flex h-16 items-center border-b border-white/10 px-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-cyan-300">AI CRM</p>
            <h1 className="text-lg font-semibold">Automation Hub</h1>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          {nav.map(([label, href, Icon]) => (
            <NavLink
              key={href}
              to={href}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                  isActive ? "bg-cyan-400/12 text-cyan-200" : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-[#080b12]/90 px-4 backdrop-blur lg:px-8">
          <div className="min-w-0">
            <p className="truncate text-sm text-slate-400">{user?.email}</p>
            <p className="text-xs text-emerald-300">{user?.gmail_connected ? "Gmail connected" : "Gmail not connected"}</p>
          </div>
          <button onClick={logout} className="rounded-md border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/5">
            Logout
          </button>
        </header>
        <div className="mx-auto max-w-7xl p-4 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
