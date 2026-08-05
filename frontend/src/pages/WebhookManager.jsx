import React, { useEffect, useState } from 'react';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';

const ALL_EVENTS = [
  { value: 'contact.created',   label: 'Contact Created',   desc: 'Fires when a new contact is added' },
  { value: 'contact.updated',   label: 'Contact Updated',   desc: 'Fires when a contact record is modified' },
  { value: 'deal.created',      label: 'Deal Created',      desc: 'New deal added to pipeline' },
  { value: 'deal.updated',      label: 'Deal Updated',      desc: 'Deal stage or value changed' },
  { value: 'deal.won',          label: 'Deal Won',          desc: 'Deal marked as closed won' },
  { value: 'deal.lost',         label: 'Deal Lost',         desc: 'Deal marked as closed lost' },
  { value: 'campaign.started',  label: 'Campaign Started',  desc: 'Email campaign launched' },
  { value: 'email.received',    label: 'Email Received',    desc: 'Inbound email received' },
];

function StatusDot({ status }) {
  return <span style={{ width: 8, height: 8, borderRadius: '50%', display: 'inline-block', background: status === 'success' ? '#10b981' : '#ef4444', marginRight: 6 }} />;
}

export default function WebhookManager() {
  const [webhooks, setWebhooks] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selectedWebhook, setSelectedWebhook] = useState(null);
  const [form, setForm] = useState({ url: '', events: [], is_active: true });
  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchData = () => {
    setLoading(true);
    Promise.all([
      fetch(`${API_BASE}/api/v1/developer/webhooks`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/developer/webhooks/deliveries`, { headers }).then(r => r.json()),
    ]).then(([wh, del]) => {
      setWebhooks(Array.isArray(wh) ? wh : []);
      setDeliveries(Array.isArray(del) ? del : []);
    }).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  const createWebhook = async () => {
    if (!form.url || form.events.length === 0) return alert('URL and at least one event required');
    setCreating(true);
    const res = await fetch(`${API_BASE}/api/v1/developer/webhooks`, { method: 'POST', headers, body: JSON.stringify(form) });
    const data = await res.json();
    if (res.ok) {
      setShowCreate(false);
      setForm({ url: '', events: [], is_active: true });
      fetchData();
    } else alert(data.detail || 'Failed to create webhook');
    setCreating(false);
  };

  const deleteWebhook = async (id) => {
    if (!window.confirm('Delete this webhook subscription?')) return;
    await fetch(`${API_BASE}/api/v1/developer/webhooks/${id}`, { method: 'DELETE', headers });
    fetchData();
  };

  const toggleEvent = (evt) => {
    setForm(f => ({ ...f, events: f.events.includes(evt) ? f.events.filter(e => e !== evt) : [...f.events, evt] }));
  };

  const webhookDeliveries = selectedWebhook ? deliveries.filter(d => d.subscription_id === selectedWebhook) : deliveries;

  return (
    <RoleGuard roles={['Admin', 'Workspace Admin', 'Super Admin']}>
      <div style={s.page}>
        <div style={s.header}>
          <div>
            <h1 style={s.title}>🔗 Webhook Manager</h1>
            <p style={s.sub}>Subscribe to real-time CRM events. All payloads are signed with HMAC-SHA256.</p>
          </div>
          <button style={s.btnPrimary} onClick={() => setShowCreate(true)}>＋ New Webhook</button>
        </div>

        <div style={s.twoCol}>
          {/* Subscriptions */}
          <div style={s.panel}>
            <div style={s.panelHeader}><span style={s.panelTitle}>Subscriptions ({webhooks.length})</span></div>
            {loading ? <div style={s.loading}>Loading…</div> : webhooks.length === 0 ? (
              <div style={s.empty}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>🔗</div>
                <div style={{ color: '#64748b', fontSize: 13 }}>No webhooks registered yet</div>
              </div>
            ) : (
              <div style={s.webhookList}>
                {webhooks.map(wh => (
                  <div key={wh.id} style={{ ...s.webhookCard, borderColor: selectedWebhook === wh.id ? '#6366f1' : 'rgba(255,255,255,0.06)' }} onClick={() => setSelectedWebhook(selectedWebhook === wh.id ? null : wh.id)}>
                    <div style={s.webhookTop}>
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <div style={s.webhookUrl}>{wh.url}</div>
                        <div style={s.eventsRow}>
                          {wh.events.slice(0, 3).map(e => <span key={e} style={s.evtTag}>{e}</span>)}
                          {wh.events.length > 3 && <span style={s.evtTag}>+{wh.events.length - 3}</span>}
                        </div>
                      </div>
                      <div style={s.webhookActions}>
                        <span style={{ ...s.statusBadge, background: wh.is_active ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: wh.is_active ? '#10b981' : '#ef4444' }}>
                          {wh.is_active ? 'Active' : 'Paused'}
                        </span>
                        <button style={s.btnDanger} onClick={e => { e.stopPropagation(); deleteWebhook(wh.id); }}>Delete</button>
                      </div>
                    </div>
                    <div style={s.secretRow}>
                      <span style={s.secretLabel}>Secret:</span>
                      <code style={s.secretCode}>{wh.secret_key.slice(0, 20)}•••</code>
                      <button style={s.copyMiniBtn} onClick={e => { e.stopPropagation(); navigator.clipboard.writeText(wh.secret_key); alert('Secret copied!'); }}>Copy</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Delivery Log */}
          <div style={s.panel}>
            <div style={s.panelHeader}>
              <span style={s.panelTitle}>Delivery Log {selectedWebhook ? '(Filtered)' : '(All)'}</span>
              {selectedWebhook && <button style={s.linkBtn} onClick={() => setSelectedWebhook(null)}>Clear Filter</button>}
            </div>
            {loading ? <div style={s.loading}>Loading…</div> : webhookDeliveries.length === 0 ? (
              <div style={s.empty}>
                <div style={{ fontSize: 40, marginBottom: 12 }}>📭</div>
                <div style={{ color: '#64748b', fontSize: 13 }}>No deliveries recorded yet</div>
              </div>
            ) : (
              <div style={s.deliveryList}>
                {webhookDeliveries.slice(0, 30).map(d => (
                  <div key={d.id} style={s.deliveryRow}>
                    <div style={s.deliveryLeft}>
                      <StatusDot status={d.status} />
                      <div>
                        <span style={s.evtBadge}>{d.event}</span>
                        <div style={s.deliveryMeta}>Attempt #{d.attempt_number} · {d.response_code ? `HTTP ${d.response_code}` : 'No response'}</div>
                      </div>
                    </div>
                    <div style={s.deliveryRight}>
                      <span style={{ ...s.dlStatusBadge, color: d.status === 'success' ? '#10b981' : '#ef4444' }}>{d.status}</span>
                      <span style={s.deliveryDate}>{new Date(d.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Signature Info */}
        <div style={s.infoBox}>
          <div style={s.infoTitle}>🛡️ Signature Verification</div>
          <p style={s.infoText}>Every webhook payload includes an <code style={s.icode}>X-Webhook-Signature</code> header — an HMAC-SHA256 digest of the body using your webhook's secret key. Always verify this on your server before processing events.</p>
          <code style={s.codeBlock}>{`import hmac, hashlib\n\ndef verify(secret, payload_bytes, signature):\n    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()\n    return hmac.compare_digest(expected, signature)`}</code>
        </div>

        {/* Create Modal */}
        {showCreate && (
          <div style={s.overlay}>
            <div style={s.modal}>
              <div style={s.modalHeader}>
                <h2 style={s.modalTitle}>Register Webhook</h2>
                <button style={s.closeX} onClick={() => setShowCreate(false)}>✕</button>
              </div>
              <div style={s.field}>
                <label style={s.label}>Endpoint URL *</label>
                <input style={s.input} placeholder="https://your-app.com/webhooks/crm" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />
              </div>
              <div style={s.field}>
                <label style={s.label}>Events to Subscribe *</label>
                <div style={s.evtGrid}>
                  {ALL_EVENTS.map(evt => (
                    <label key={evt.value} style={{ ...s.evtOption, background: form.events.includes(evt.value) ? 'rgba(99,102,241,0.18)' : '#0f172a', borderColor: form.events.includes(evt.value) ? '#6366f1' : 'rgba(255,255,255,0.07)' }}>
                      <input type="checkbox" checked={form.events.includes(evt.value)} onChange={() => toggleEvent(evt.value)} style={{ accentColor: '#6366f1' }} />
                      <div>
                        <div style={s.evtLabel}>{evt.label}</div>
                        <div style={s.evtDesc}>{evt.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
              <div style={s.modalFooter}>
                <button style={s.btnGhost} onClick={() => setShowCreate(false)}>Cancel</button>
                <button style={s.btnPrimary} onClick={createWebhook} disabled={creating}>{creating ? 'Registering…' : '🔗 Register Webhook'}</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </RoleGuard>
  );
}

const s = {
  page: { padding: 32, maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 28, flexWrap: 'wrap', gap: 16 },
  title: { fontSize: 26, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  sub: { color: '#64748b', fontSize: 14, margin: 0 },
  btnPrimary: { background: 'linear-gradient(135deg, #6366f1, #818cf8)', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnGhost: { background: 'transparent', color: '#94a3b8', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '10px 20px', fontSize: 13, cursor: 'pointer' },
  btnDanger: { background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)', borderRadius: 6, padding: '5px 10px', fontSize: 11, cursor: 'pointer', fontWeight: 600 },
  linkBtn: { background: 'none', border: 'none', color: '#818cf8', fontSize: 12, cursor: 'pointer', fontWeight: 600 },
  twoCol: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 },
  panel: { background: '#1e293b', borderRadius: 12, padding: '20px', boxShadow: '0 4px 20px rgba(0,0,0,0.2)', minHeight: 300 },
  panelHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  panelTitle: { fontSize: 14, fontWeight: 700, color: '#e2e8f0' },
  loading: { textAlign: 'center', color: '#64748b', padding: 40 },
  empty: { textAlign: 'center', padding: '40px 20px' },
  webhookList: { display: 'flex', flexDirection: 'column', gap: 10 },
  webhookCard: { background: '#0f172a', border: '1px solid', borderRadius: 10, padding: '14px', cursor: 'pointer', transition: 'border-color 0.2s' },
  webhookTop: { display: 'flex', gap: 12, alignItems: 'flex-start', marginBottom: 10 },
  webhookUrl: { fontSize: 12, fontWeight: 600, color: '#94a3b8', wordBreak: 'break-all', marginBottom: 6 },
  eventsRow: { display: 'flex', gap: 4, flexWrap: 'wrap' },
  evtTag: { background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600 },
  webhookActions: { display: 'flex', gap: 8, flexShrink: 0, flexDirection: 'column', alignItems: 'flex-end' },
  statusBadge: { padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700 },
  secretRow: { display: 'flex', gap: 8, alignItems: 'center', background: 'rgba(255,255,255,0.03)', padding: '8px 10px', borderRadius: 6 },
  secretLabel: { fontSize: 11, color: '#64748b' },
  secretCode: { fontSize: 11, color: '#94a3b8', flex: 1 },
  copyMiniBtn: { background: 'rgba(99,102,241,0.15)', color: '#818cf8', border: 'none', borderRadius: 4, padding: '3px 8px', fontSize: 10, cursor: 'pointer' },
  deliveryList: { display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 400, overflowY: 'auto' },
  deliveryRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px', background: '#0f172a', borderRadius: 8 },
  deliveryLeft: { display: 'flex', gap: 10, alignItems: 'center' },
  evtBadge: { fontSize: 11, fontWeight: 700, color: '#e2e8f0', display: 'block', marginBottom: 2 },
  deliveryMeta: { fontSize: 10, color: '#64748b' },
  deliveryRight: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 3 },
  dlStatusBadge: { fontSize: 10, fontWeight: 700 },
  deliveryDate: { fontSize: 10, color: '#64748b' },
  infoBox: { background: '#1e293b', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 12, padding: 24 },
  infoTitle: { fontSize: 14, fontWeight: 700, color: '#818cf8', marginBottom: 10 },
  infoText: { fontSize: 13, color: '#94a3b8', marginBottom: 16, lineHeight: 1.6 },
  icode: { background: 'rgba(255,255,255,0.08)', padding: '1px 6px', borderRadius: 4, fontSize: 12 },
  codeBlock: { display: 'block', background: '#0f172a', padding: '16px 20px', borderRadius: 10, fontSize: 12, color: '#e2e8f0', lineHeight: 1.7, whiteSpace: 'pre', overflowX: 'auto' },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 },
  modal: { background: '#1e293b', borderRadius: 16, padding: 28, width: '100%', maxWidth: 600, maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 25px 60px rgba(0,0,0,0.5)' },
  modalHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  modalTitle: { fontSize: 18, fontWeight: 700, color: '#f1f5f9', margin: 0 },
  modalFooter: { display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 24, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,0.06)' },
  closeX: { background: 'none', border: 'none', color: '#64748b', fontSize: 18, cursor: 'pointer' },
  field: { marginBottom: 18 },
  label: { display: 'block', fontSize: 12, fontWeight: 700, color: '#94a3b8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' },
  input: { width: '100%', background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '10px 14px', color: '#e2e8f0', fontSize: 14, boxSizing: 'border-box', outline: 'none' },
  evtGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, maxHeight: 280, overflowY: 'auto' },
  evtOption: { display: 'flex', gap: 10, alignItems: 'flex-start', border: '1px solid', borderRadius: 8, padding: '10px 12px', cursor: 'pointer', transition: 'all 0.15s' },
  evtLabel: { fontSize: 12, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 },
  evtDesc: { fontSize: 11, color: '#64748b' },
};
