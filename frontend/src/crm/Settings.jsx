import { useState, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { startGoogleAuth } from "../hooks/useGoogleAuth";
import { useCan, useRole } from "../security/permissionHooks";
import { PERMISSIONS } from "../security/permissions";
import { Shield, Key, CreditCard, Users, History, Mail, Settings as GearIcon, Check } from "lucide-react";

export default function Settings() {
  const { user } = useAuth();
  const rawRole = useRole();
  const [activeTab, setActiveTab] = useState("general");

  // Permissions checks
  const canWorkspace = useCan(PERMISSIONS.SETTINGS_WORKSPACE);
  const canBilling = useCan(PERMISSIONS.SETTINGS_BILLING);
  const canApiKeys = useCan(PERMISSIONS.SETTINGS_API_KEYS);
  const canSecurity = useCan(PERMISSIONS.SETTINGS_SECURITY);
  const canAuditLogs = useCan(PERMISSIONS.SETTINGS_AUDIT_LOGS);
  const canUsers = useCan(PERMISSIONS.SETTINGS_USERS);

  // Tabs configuration
  const tabs = useMemo(() => {
    const list = [
      { id: "general", label: "General & OAuth", icon: GearIcon, allowed: true },
      { id: "workspace", label: "Workspace", icon: Shield, allowed: canWorkspace },
      { id: "billing", label: "Billing", icon: CreditCard, allowed: canWorkspace || canBilling },
      { id: "apikeys", label: "API Keys", icon: Key, allowed: canApiKeys },
      { id: "audit", label: "Audit Logs & Security", icon: History, allowed: canSecurity || canAuditLogs },
      { id: "users", label: "Team Management", icon: Users, allowed: canUsers },
    ];
    return list.filter(tab => tab.allowed);
  }, [canWorkspace, canBilling, canApiKeys, canSecurity, canAuditLogs, canUsers]);

  // Adjust active tab if it becomes restricted
  useMemo(() => {
    if (tabs.length > 0 && !tabs.find(t => t.id === activeTab)) {
      setActiveTab(tabs[0].id);
    }
  }, [tabs, activeTab]);

  async function connectGoogle() {
    await startGoogleAuth("login");
  }

  // State mocks for Settings page interactions
  const [wsName, setWsName] = useState("Default Workspace");
  const [apiKeys, setApiKeys] = useState([
    { id: 1, name: "Production Analytics Key", key: "sk-•••••••••••••12345", created: "2026-07-01", active: true },
    { id: 2, name: "Development Ingestion Key", key: "sk-•••••••••••••abcde", created: "2026-07-15", active: true }
  ]);
  const [newKeyName, setNewKeyName] = useState("");
  const [showKeySuccess, setShowKeySuccess] = useState("");

  const handleGenerateKey = (e) => {
    e.preventDefault();
    if (!newKeyName) return;
    const generated = "sk-test-live-" + Math.random().toString(36).substring(2, 15);
    const newKey = {
      id: Date.now(),
      name: newKeyName,
      key: generated,
      created: new Date().toISOString().split('T')[0],
      active: true
    };
    setApiKeys([...apiKeys, newKey]);
    setShowKeySuccess(generated);
    setNewKeyName("");
  };

  const handleRevokeKey = (id) => {
    setApiKeys(apiKeys.filter(k => k.id !== id));
  };

  const mockUsers = [
    { name: "System Admin", email: "admin@company.com", role: "Super Admin" },
    { name: "John Sales", email: "sales@company.com", role: "Sales" },
    { name: "Marketing Lead", email: "marketing@company.com", role: "Marketing" },
    { name: "Viewer User", email: "viewer@company.com", role: "Viewer" }
  ];

  const mockLogs = [
    { action: "API_KEY_AUTH", path: "/api/health", user: "API Key", status: "ALLOWED", ip: "127.0.0.1", time: "Just now" },
    { action: "USER_LOGIN", path: "/auth/login", user: "admin@company.com", status: "ALLOWED", ip: "192.168.1.42", time: "5 mins ago" },
    { action: "CONTACT_DELETE", path: "/contacts/23", user: "sales@company.com", status: "DENIED", ip: "192.168.1.101", time: "1 hour ago" },
    { action: "SETTINGS_WORKSPACE", path: "/settings/workspace", user: "viewer@company.com", status: "DENIED", ip: "127.0.0.1", time: "3 hours ago" }
  ];

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Settings</h2>
        <p className="text-sm text-slate-400">Manage OAuth credentials, team members, billing details, and workspace security.</p>
      </div>

      <div className="flex flex-col gap-6 lg:flex-row">
        {/* Navigation Sidebar inside Settings */}
        <aside className="w-full shrink-0 space-y-1 lg:w-64">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setShowKeySuccess("");
                }}
                className={`w-full flex items-center gap-3 rounded-lg px-4 py-2.5 text-sm font-medium transition ${
                  isActive ? "bg-cyan-400/12 text-cyan-200" : "text-slate-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            );
          })}
        </aside>

        {/* Tab content panel */}
        <div className="flex-1 rounded-xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur">
          {activeTab === "general" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white">General & Integrations</h3>
                <p className="text-sm text-slate-400">Configure email integrations and OAuth credentials.</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-5">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Gmail API Integration</p>
                <div className="flex items-center justify-between gap-4 flex-wrap">
                  <div>
                    <p className="text-sm font-medium text-slate-200">
                      Gmail Connection Status: <span className={user?.gmail_connected ? "text-emerald-400" : "text-amber-400"}>
                        {user?.gmail_connected ? "Connected" : "Disconnected"}
                      </span>
                    </p>
                    <p className="text-xs text-slate-400 mt-1">Connect Gmail to automate responses and track incoming sales leads.</p>
                  </div>
                  <button
                    onClick={connectGoogle}
                    className="rounded-lg bg-white hover:bg-slate-200 text-slate-950 px-4 py-2 text-sm font-semibold transition"
                  >
                    {user?.gmail_connected ? "Reconnect Gmail" : "Connect Gmail"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === "workspace" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white">Workspace Configuration</h3>
                <p className="text-sm text-slate-400">Customize the workspace defaults and options.</p>
              </div>
              <form className="space-y-4" onSubmit={e => e.preventDefault()}>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Workspace Name</label>
                  <input
                    type="text"
                    value={wsName}
                    onChange={(e) => setWsName(e.target.value)}
                    className="w-full max-w-md rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-lg bg-cyan-400/20 text-cyan-200 hover:bg-cyan-400/30 border border-cyan-400/30 px-4 py-2 text-sm font-semibold transition"
                >
                  Save Changes
                </button>
              </form>
            </div>
          )}

          {activeTab === "billing" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white">Billing & Subscription</h3>
                <p className="text-sm text-slate-400">Monitor usage metrics and plan tier upgrades.</p>
              </div>
              <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-5">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <h4 className="font-semibold text-white">Enterprise Plan</h4>
                    <p className="text-xs text-cyan-300 font-medium">Auto-renewing on August 1, 2026</p>
                  </div>
                  <span className="bg-cyan-400/20 text-cyan-200 border border-cyan-400/30 rounded-full px-3 py-0.5 text-xs font-semibold uppercase">Active</span>
                </div>
                <p className="text-xs text-slate-400 mt-4">API Requests usage: <strong>45,201 / 100,000</strong></p>
                <div className="mt-2 h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-400" style={{ width: "45%" }} />
                </div>
              </div>
            </div>
          )}

          {activeTab === "apikeys" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white">API Credentials</h3>
                <p className="text-sm text-slate-400">Manage secure credentials for backend CRM access.</p>
              </div>

              {showKeySuccess && (
                <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-200">
                  <div className="flex items-center gap-2 font-medium mb-1 text-white">
                    <Check size={18} className="text-emerald-400" />
                    API Key Created Successfully!
                  </div>
                  <p className="text-xs mb-3 text-slate-300">Copy this key now. It will not be shown again for security reasons.</p>
                  <code className="block bg-slate-950 p-2.5 rounded border border-white/10 select-all font-mono break-all text-emerald-300">{showKeySuccess}</code>
                </div>
              )}

              <form onSubmit={handleGenerateKey} className="flex gap-2 max-w-md items-end">
                <div className="flex-1 space-y-1">
                  <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">New API Key Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Sales Dataform Sync"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <button
                  type="submit"
                  className="rounded-lg bg-cyan-400/20 hover:bg-cyan-400/30 text-cyan-200 border border-cyan-400/30 px-4 py-2.5 text-sm font-semibold transition"
                >
                  Generate
                </button>
              </form>

              <div className="space-y-2">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Workspace Keys</p>
                {apiKeys.length === 0 ? (
                  <p className="text-sm text-slate-400">No active keys generated.</p>
                ) : (
                  <div className="divide-y divide-white/5 border-y border-white/5">
                    {apiKeys.map((key) => (
                      <div key={key.id} className="flex justify-between items-center py-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-200">{key.name}</p>
                          <code className="text-xs font-mono text-slate-400">{key.key}</code>
                        </div>
                        <button
                          onClick={() => handleRevokeKey(key.id)}
                          className="text-xs text-red-400 hover:text-red-300 transition"
                        >
                          Revoke
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === "audit" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white">Security & Audit Logs</h3>
                <p className="text-sm text-slate-400">Trace authorization events and system configuration changes.</p>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Recent Audit History</p>
                <div className="overflow-x-auto rounded-lg border border-white/5 bg-black/20">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-white/5 bg-white/[0.02] text-slate-400">
                        <th className="p-3">Action</th>
                        <th className="p-3">Resource Path</th>
                        <th className="p-3">Initiated By</th>
                        <th className="p-3 text-center">Status</th>
                        <th className="p-3">IP Address</th>
                        <th className="p-3 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-slate-300">
                      {mockLogs.map((log, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.01]">
                          <td className="p-3 font-semibold font-mono text-slate-200">{log.action}</td>
                          <td className="p-3 font-mono text-slate-400">{log.path}</td>
                          <td className="p-3">{log.user}</td>
                          <td className="p-3 text-center">
                            <span className={`px-2 py-0.5 rounded-full font-semibold ${
                              log.status === "ALLOWED" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                            }`}>
                              {log.status}
                            </span>
                          </td>
                          <td className="p-3 font-mono text-slate-400">{log.ip}</td>
                          <td className="p-3 text-right text-slate-400">{log.time}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === "users" && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-white">Team & Roles</h3>
                <p className="text-sm text-slate-400">Audit user memberships and verify active directory permissions.</p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {mockUsers.map((u, idx) => (
                  <div key={idx} className="flex justify-between items-center rounded-lg border border-white/5 bg-black/20 p-4">
                    <div>
                      <p className="text-sm font-semibold text-slate-200">{u.name}</p>
                      <p className="text-xs text-slate-400">{u.email}</p>
                    </div>
                    <span className="text-xs font-semibold bg-cyan-400/10 text-cyan-300 border border-cyan-400/20 px-2.5 py-1 rounded">
                      {u.role}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
