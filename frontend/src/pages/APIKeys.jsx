import React, { useEffect, useState } from 'react';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';
const SCOPES = [
  { value: 'contacts.read',   label: 'Contacts — Read',   desc: 'List and view contacts' },
  { value: 'contacts.write',  label: 'Contacts — Write',  desc: 'Create and update contacts' },
  { value: 'emails.read',     label: 'Emails — Read',     desc: 'View email inbox and threads' },
  { value: 'emails.write',    label: 'Emails — Write',    desc: 'Send and manage emails' },
  { value: 'campaigns.read',  label: 'Campaigns — Read',  desc: 'View campaign data' },
  { value: 'campaigns.write', label: 'Campaigns — Write', desc: 'Create and send campaigns' },
  { value: 'crm.read',        label: 'CRM — Read',        desc: 'Access deals, pipeline, leads' },
  { value: 'crm.write',       label: 'CRM — Write',       desc: 'Modify CRM records' },
  { value: 'analytics.read',  label: 'Analytics — Read',  desc: 'View reports and dashboards' },
  { value: 'ai.reply',        label: 'AI — Reply',        desc: 'Trigger AI email replies' },
  { value: 'ai.classify',     label: 'AI — Classify',     desc: 'Run email classification' },
  { value: 'ai.score',        label: 'AI — Score',        desc: 'Score leads and contacts' },
];

export default function APIKeys() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newKey, setNewKey] = useState(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: '', permissions: [], rate_limit: 60, daily_limit: 1000, expires_in_days: 30, is_live: true, description: '' });
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchKeys = () => {
    setLoading(true);
    fetch(`${API_BASE}/api/v1/developer/keys`, { headers })
      .then(r => r.json()).then(d => setKeys(Array.isArray(d) ? d : []))
      .catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { fetchKeys(); }, []);

  const createKey = async () => {
    if (!form.name || form.permissions.length === 0) return alert('Name and at least one scope required');
    setCreating(true);
    const res = await fetch(`${API_BASE}/api/v1/developer/keys`, { method: 'POST', headers, body: JSON.stringify(form) });
    const data = await res.json();
    if (res.ok) {
      setNewKey(data.plaintext_key);
      setShowCreate(false);
      setForm({ name: '', permissions: [], rate_limit: 60, daily_limit: 1000, expires_in_days: 30, is_live: true, description: '' });
      fetchKeys();
    } else alert(data.detail || 'Failed to create key');
    setCreating(false);
  };

  const revokeKey = async (id) => {
    if (!window.confirm('Revoke this API key? This cannot be undone.')) return;
    await fetch(`${API_BASE}/api/v1/developer/keys/${id}`, { method: 'DELETE', headers });
    fetchKeys();
  };

  const toggleScope = (scope) => {
    setForm(f => ({ ...f, permissions: f.permissions.includes(scope) ? f.permissions.filter(s => s !== scope) : [...f.permissions, scope] }));
  };

  return (
    <RoleGuard roles={['Admin', 'Workspace Admin', 'Super Admin']}>
      <div style={s.page}>
        <div style={s.header}>
          <div>
            <h1 style={s.title}>🔑 API Keys</h1>
            <p style={s.sub}>Create scoped API keys for your external systems to integrate with this workspace.</p>
          </div>
          <button style={s.btnPrimary} onClick={() => setShowCreate(true)}>＋ Generate Key</button>
        </div>

        {/* Revealed Key Banner */}
        {newKey && (
          <div style={s.revealBanner}>
            <div style={s.revealTop}>
              <span>✅ Key created! Copy it now — it will never be shown again.</span>
              <button style={s.closeX} onClick={() => setNewKey(null)}>✕</button>
            </div>
            <div style={s.revealKey}>
              <code style={s.keyCode}>{newKey}</code>
              <button style={s.copyBtn} onClick={() => { navigator.clipboard.writeText(newKey); alert('Copied!'); }}>Copy</button>
            </div>
          </div>
        )}

        {/* Keys Table */}
        <div style={s.tableWrap}>
          {loading ? (
            <div style={s.loading}>Loading API Keys…</div>
          ) : keys.length === 0 ? (
            <div style={s.empty}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🔑</div>
              <div style={{ color: '#94a3b8', marginBottom: 16 }}>No API keys yet. Generate one to start integrating.</div>
              <button style={s.btnPrimary} onClick={() => setShowCreate(true)}>＋ Generate First Key</button>
            </div>
          ) : (
            <table style={s.table}>
              <thead>
                <tr>
                  {['Name', 'Prefix', 'Status', 'Scopes', 'Rate Limit', 'Last Used', 'Expires', 'Actions'].map(h => (
                    <th key={h} style={s.th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {keys.map(k => (
                  <tr key={k.id} style={s.tr}>
                    <td style={s.td}>
                      <div style={s.keyNameCell}>{k.name}</div>
                      {k.description && <div style={s.keyDesc}>{k.description}</div>}
                    </td>
                    <td style={s.td}><code style={s.prefixCode}>{k.key_prefix}••••••</code></td>
                    <td style={s.td}>
                      <span style={{ ...s.statusBadge, background: k.status === 'active' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: k.status === 'active' ? '#10b981' : '#ef4444' }}>
                        {k.status}
                      </span>
                    </td>
                    <td style={s.td}>
                      <div style={s.scopeWrap}>
                        {(k.permissions || []).slice(0, 3).map(p => <span key={p} style={s.scopeBadge}>{p}</span>)}
                        {(k.permissions || []).length > 3 && <span style={s.scopeBadge}>+{k.permissions.length - 3} more</span>}
                      </div>
                    </td>
                    <td style={s.td}><span style={s.dimText}>{k.rate_limit}/min · {k.daily_limit}/day</span></td>
                    <td style={s.td}><span style={s.dimText}>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}</span></td>
                    <td style={s.td}><span style={s.dimText}>{k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'}</span></td>
                    <td style={s.td}>
                      <div style={s.actions}>
                        <button style={s.btnDanger} onClick={() => revokeKey(k.id)}>Revoke</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Create Modal */}
        {showCreate && (
          <div style={s.overlay}>
            <div style={s.modal}>
              <div style={s.modalHeader}>
                <h2 style={s.modalTitle}>Generate New API Key</h2>
                <button style={s.closeX} onClick={() => setShowCreate(false)}>✕</button>
              </div>
              <div style={s.field}>
                <label style={s.label}>Key Name *</label>
                <input style={s.input} placeholder="e.g. Production ERP Integration" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div style={s.field}>
                <label style={s.label}>Description</label>
                <input style={s.input} placeholder="Optional description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
              </div>
              <div style={s.inlineFields}>
                <div style={s.field}>
                  <label style={s.label}>Rate Limit (per minute)</label>
                  <input style={s.input} type="number" value={form.rate_limit} onChange={e => setForm(f => ({ ...f, rate_limit: +e.target.value }))} />
                </div>
                <div style={s.field}>
                  <label style={s.label}>Daily Limit</label>
                  <input style={s.input} type="number" value={form.daily_limit} onChange={e => setForm(f => ({ ...f, daily_limit: +e.target.value }))} />
                </div>
                <div style={s.field}>
                  <label style={s.label}>Expires In (days)</label>
                  <input style={s.input} type="number" value={form.expires_in_days} onChange={e => setForm(f => ({ ...f, expires_in_days: +e.target.value }))} />
                </div>
              </div>
              <div style={s.field}>
                <label style={s.label}>Environment</label>
                <div style={s.envToggle}>
                  <button style={{ ...s.envBtn, background: form.is_live ? '#6366f1' : '#1e293b', color: form.is_live ? '#fff' : '#94a3b8' }} onClick={() => setForm(f => ({ ...f, is_live: true }))}>🔴 Live</button>
                  <button style={{ ...s.envBtn, background: !form.is_live ? '#6366f1' : '#1e293b', color: !form.is_live ? '#fff' : '#94a3b8' }} onClick={() => setForm(f => ({ ...f, is_live: false }))}>🧪 Test</button>
                </div>
              </div>
              <div style={s.field}>
                <label style={s.label}>Permissions (Scopes) *</label>
                <div style={s.scopeGrid}>
                  {SCOPES.map(sc => (
                    <label key={sc.value} style={{ ...s.scopeOption, background: form.permissions.includes(sc.value) ? 'rgba(99,102,241,0.2)' : '#0f172a', borderColor: form.permissions.includes(sc.value) ? '#6366f1' : 'rgba(255,255,255,0.07)' }}>
                      <input type="checkbox" checked={form.permissions.includes(sc.value)} onChange={() => toggleScope(sc.value)} style={{ accentColor: '#6366f1' }} />
                      <div>
                        <div style={s.scopeLabel}>{sc.label}</div>
                        <div style={s.scopeDesc}>{sc.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              <div style={s.modalFooter}>
                <button style={s.btnGhost} onClick={() => setShowCreate(false)}>Cancel</button>
                <button style={s.btnPrimary} onClick={createKey} disabled={creating}>{creating ? 'Generating…' : '🔑 Generate Key'}</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </RoleGuard>
  );
}

const s = {
  page: { padding: 32, maxWidth: 1100, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 28, flexWrap: 'wrap', gap: 16 },
  title: { fontSize: 26, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  sub: { color: '#64748b', fontSize: 14, margin: 0 },
  btnPrimary: { background: 'linear-gradient(135deg, #6366f1, #818cf8)', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnGhost: { background: 'transparent', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '10px 20px', fontSize: 13, cursor: 'pointer' },
  btnDanger: { background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '6px 12px', fontSize: 12, cursor: 'pointer', fontWeight: 600 },
  revealBanner: { background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: 12, padding: 20, marginBottom: 24 },
  revealTop: { display: 'flex', justifyContent: 'space-between', color: '#10b981', fontWeight: 600, marginBottom: 12, fontSize: 13 },
  revealKey: { display: 'flex', gap: 12, alignItems: 'center' },
  keyCode: { flex: 1, background: '#0f172a', padding: '10px 14px', borderRadius: 8, fontSize: 13, color: '#e2e8f0', border: '1px solid rgba(255,255,255,0.07)', wordBreak: 'break-all' },
  copyBtn: { background: '#10b981', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 16px', fontWeight: 700, cursor: 'pointer', fontSize: 13, flexShrink: 0 },
  closeX: { background: 'none', border: 'none', color: '#64748b', fontSize: 18, cursor: 'pointer' },
  tableWrap: { background: '#1e293b', borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' },
  loading: { textAlign: 'center', padding: 48, color: '#64748b' },
  empty: { textAlign: 'center', padding: 60 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '12px 16px', fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', borderBottom: '1px solid rgba(255,255,255,0.06)', background: '#0f172a' },
  tr: { borderBottom: '1px solid rgba(255,255,255,0.04)' },
  td: { padding: '14px 16px', verticalAlign: 'middle' },
  keyNameCell: { fontSize: 13, fontWeight: 600, color: '#e2e8f0' },
  keyDesc: { fontSize: 11, color: '#64748b', marginTop: 3 },
  prefixCode: { fontSize: 11, background: 'rgba(255,255,255,0.06)', padding: '3px 8px', borderRadius: 4, color: '#94a3b8' },
  statusBadge: { padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700 },
  scopeWrap: { display: 'flex', gap: 4, flexWrap: 'wrap' },
  scopeBadge: { background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600 },
  dimText: { fontSize: 12, color: '#64748b' },
  actions: { display: 'flex', gap: 8 },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 },
  modal: { background: '#1e293b', borderRadius: 16, padding: 28, width: '100%', maxWidth: 680, maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 25px 60px rgba(0,0,0,0.5)' },
  modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  modalTitle: { fontSize: 18, fontWeight: 700, color: '#f1f5f9', margin: 0 },
  modalFooter: { display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,0.06)' },
  field: { marginBottom: 18 },
  label: { display: 'block', fontSize: 12, fontWeight: 700, color: '#94a3b8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' },
  input: { width: '100%', background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '10px 14px', color: '#e2e8f0', fontSize: 14, boxSizing: 'border-box', outline: 'none' },
  inlineFields: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 },
  envToggle: { display: 'flex', gap: 8 },
  envBtn: { flex: 1, padding: '10px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: 13, transition: 'all 0.2s' },
  scopeGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, maxHeight: 240, overflowY: 'auto', paddingRight: 4 },
  scopeOption: { display: 'flex', gap: 10, alignItems: 'flex-start', border: '1px solid', borderRadius: 8, padding: '10px 12px', cursor: 'pointer', transition: 'all 0.15s' },
  scopeLabel: { fontSize: 12, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 },
  scopeDesc: { fontSize: 11, color: '#64748b' },
};
