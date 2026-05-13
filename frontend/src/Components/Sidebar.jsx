import { motion } from "framer-motion";
import { LogOut, LayoutDashboard, Settings, Mail, FileText, Bot } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useNavigate, useLocation } from "react-router-dom";

const Sidebar = ({ children }) => {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { icon: LayoutDashboard, label: "Dashboard", path: "/dashboard" },
    { icon: Mail, label: "Inbox", path: "/inbox" },
    { icon: FileText, label: "Drafts", path: "/drafts" },
    { icon: Bot, label: "Agent Config", path: "/config" },
    { icon: Settings, label: "Settings", path: "/settings" },
  ];

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">

      {/* SIDEBAR CONTAINER */}
      <motion.aside
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-72 bg-slate-900/50 backdrop-blur-2xl border-r border-slate-800/50 flex flex-col justify-between py-8 px-4 shadow-[10px_0_30px_-10px_rgba(0,0,0,0.3)] z-50"
      >
        {/* LOGO AREA */}
        <div>
          <div className="flex items-center gap-3 px-4 mb-10">
            <div className="w-10 h-10 bg-gradient-to-tr from-green-400 to-blue-500 rounded-xl flex items-center justify-center shadow-lg shadow-green-500/20">
              <Bot className="text-white fill-white/20" size={24} />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">AutoAgent</h1>
              <span className="text-xs text-slate-400 font-medium px-2 py-0.5 bg-slate-800 rounded-full border border-slate-700">v2.0 Pro</span>
            </div>
          </div>

          {/* MENU ITEMS */}
          <nav className="space-y-2">
            {menuItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <button
                  key={item.label}
                  onClick={() => navigate(item.path)}
                  className={`w-full flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-200 group relative overflow-hidden ${isActive
                      ? "bg-gradient-to-r from-blue-600/20 to-blue-400/10 text-blue-400 shadow-inner"
                      : "text-slate-400 hover:text-white hover:bg-slate-800/50"
                    }`}
                >
                  {/* Active Indicator Bar */}
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-r-full"
                    />
                  )}

                  <item.icon size={20} className={`transition-colors ${isActive ? "text-blue-400" : "text-slate-500 group-hover:text-white"}`} />
                  <span className="font-medium">{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* BOTTOM USER AREA */}
        <div>
          <div className="mx-2 p-4 bg-gradient-to-br from-slate-800/50 to-slate-900/50 rounded-2xl border border-slate-700/50 mb-4">
            <h4 className="text-white font-medium text-sm mb-1">{user?.name || "User"}</h4>
            <p className="text-xs text-slate-400 truncate">{user?.email}</p>
            <div className="mt-3 flex items-center gap-2 text-xs text-green-400 bg-green-950/30 px-2 py-1 rounded-md w-fit border border-green-900/50">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              Online
            </div>
          </div>

          <button
            onClick={() => {
              logout();
              navigate("/login");
            }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </motion.aside>

      {/* CONTENT WRAPPER */}
      {/* Note: In your previous code, Sidebar wrapped content. Keeping that pattern. */}
      {children && (
        <main className="flex-1 overflow-auto bg-slate-950 relative">
          {/* Background Ambient Glows */}
          <div className="absolute top-0 left-0 w-full h-[500px] bg-blue-900/10 blur-[100px] pointer-events-none" />
          <div className="absolute bottom-0 right-0 w-full h-[500px] bg-green-900/5 blur-[100px] pointer-events-none" />

          <div className="relative z-10 w-full h-full">
            {children}
          </div>
        </main>
      )}
    </div>
  );
};

export default Sidebar;
