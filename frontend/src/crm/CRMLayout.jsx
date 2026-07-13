import { Menu, Moon, Sun, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { BarChart3, Bot, Briefcase, Brain, DollarSign, Inbox, LayoutDashboard, Megaphone, Settings, UserCircle, Users } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const nav = [
  ["Dashboard", "/dashboard", LayoutDashboard],
  ["Inbox", "/inbox", Inbox],
  ["Contacts", "/contacts", Users],
  ["Pipelines", "/pipelines", Briefcase],
  ["Deals", "/deals", DollarSign],
  ["Campaigns", "/campaigns", Megaphone],
  ["Lead Profiles", "/lead-profiles", UserCircle],
  ["AI Insights", "/ai-insights", Brain],
  ["Analytics", "/analytics", BarChart3],
  ["AI Tasks", "/ai-tasks", Bot],
  ["AI Agents", "/ai-agents", Brain],
  ["Settings", "/settings", Settings],
];

function NavItems({ onNavigate }) {
  return nav.map(([label, href, Icon]) => (
    <NavLink
      key={href}
      to={href}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
          isActive ? "bg-cyan-400/12 text-cyan-200" : "text-slate-400 hover:bg-white/5 hover:text-white"
        }`
      }
    >
      <Icon size={18} />
      {label}
    </NavLink>
  ));
}

export default function CRMLayout() {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="crm-shell min-h-screen bg-[#080b12] text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-white/10 bg-[#0c111d] lg:block">
        <div className="flex h-16 items-center border-b border-white/10 px-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-cyan-300">AI CRM</p>
            <h1 className="text-lg font-semibold">Automation Hub</h1>
          </div>
        </div>
        <nav className="space-y-1 p-3">
          <NavItems />
        </nav>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} aria-label="Close menu" />
          <aside className="absolute left-0 top-0 h-full w-72 border-r border-white/10 bg-[#0c111d] p-4">
            <div className="mb-4 flex items-center justify-between">
              <p className="font-semibold text-cyan-300">AI CRM</p>
              <button onClick={() => setMobileOpen(false)} className="rounded-md p-2 hover:bg-white/5">
                <X size={20} />
              </button>
            </div>
            <nav className="space-y-1">
              <NavItems onNavigate={() => setMobileOpen(false)} />
            </nav>
          </aside>
        </div>
      )}

      <main className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-white/10 bg-[#080b12]/90 px-4 backdrop-blur lg:px-8">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="rounded-md border border-white/10 p-2 lg:hidden" aria-label="Open menu">
              <Menu size={18} />
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm text-slate-400">{user?.email}</p>
              <p className="text-xs text-emerald-300">{user?.gmail_connected ? "Gmail connected" : "Gmail not connected"}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={toggleTheme} className="rounded-md border border-white/10 p-2 text-slate-300 hover:bg-white/5" title="Toggle theme">
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button onClick={logout} className="rounded-md border border-white/10 px-3 py-2 text-sm text-slate-300 hover:bg-white/5">
              Logout
            </button>
          </div>
        </header>
        <div className="mx-auto max-w-7xl p-4 pb-24 lg:p-8 lg:pb-8">
          <Outlet />
        </div>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-20 flex justify-around border-t border-white/10 bg-[#0c111d]/95 px-2 py-2 backdrop-blur lg:hidden">
        {nav.slice(0, 5).map(([label, href, Icon]) => (
          <NavLink key={href} to={href} className={({ isActive }) => `flex flex-col items-center gap-1 px-2 py-1 text-[10px] ${isActive ? "text-cyan-300" : "text-slate-500"}`}>
            <Icon size={18} />
            {label.split(" ")[0]}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
