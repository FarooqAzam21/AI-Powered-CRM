import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';

export default function DeveloperDashboard() {
  const [usage, setUsage] = useState(null);
  const [keys, setKeys] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };

    Promise.all([
      fetch(`${API_BASE}/api/v1/developer/usage`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/developer/keys`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/developer/webhooks`, { headers }).then(r => r.json()),
    ]).then(([usageData, keysData, webhooksData]) => {
      setUsage(usageData);
      setKeys(Array.isArray(keysData) ? keysData : []);
      setWebhooks(Array.isArray(webhooksData) ? webhooksData : []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const statCards = [
    {
      label: 'Total API Keys',
      value: usage?.keys_count ?? '—',
      active: usage?.active_keys ?? '—',
      icon: '🔑',
      color: '#6366f1',
      bg: 'rgba(99,102,241,0.12)',
      sub: 'Active keys',
    },
    {
      label: 'Total Requests',
      value: usage?.total_requests ?? '—',
      icon: '📡',
      color: '#06b6d4',
      bg: 'rgba(6,182,212,0.12)',
      sub: `${usage?.success_requests ?? 0} successful`,
    },
    {
      label: 'Webhook Endpoints',
      value: webhooks.length,
      icon: '🔗',
      color: '#10b981',
      bg: 'rgba(16,185,129,0.12)',
      sub: `${webhooks.filter(w => w.is_active).length} active`,
    },
    {
      label: 'Failed Requests',
      value: usage?.failed_requests ?? '—',
      icon: '⚠️',
      color: '#f59e0b',
      bg: 'rgba(245,158,11,0.12)',
      sub: 'Errors / Rate limited',
    },
  ];

  const endpoints = usage?.endpoints_breakdown
    ? Object.entries(usage.endpoints_breakdown).sort((a, b) => b[1] - a[1]).slice(0, 6)
    : [];

  return (
    <RoleGuard roles={['Admin', 'Workspace Admin', 'Super Admin']}>
      <div style={styles.page}>
        {/* Header */}
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>Developer Platform</div>
            <h1 style={styles.title}>Developer Console</h1>
            <p style={styles.subtitle}>Manage API access, webhooks, and monitor integrations for your workspace.</p>
          </div>
          <div style={styles.headerActions}>
            <button style={styles.btnSecondary} onClick={() => navigate('/developer/docs')}>📖 Documentation</button>
            <button style={styles.btnPrimary} onClick={() => navigate('/developer/keys')}>＋ New API Key</button>
          </div>
        </div>

        {/* Stat Cards */}
        <div style={styles.statsGrid}>
          {statCards.map((s, i) => (
            <div key={i} style={{ ...styles.card, borderTop: `3px solid ${s.color}` }}>
              <div style={styles.cardTop}>
                <div style={{ ...styles.iconBox, background: s.bg }}>
                  <span style={{ fontSize: 22 }}>{s.icon}</span>
                </div>
                <div>
                  <div style={{ ...styles.statVal, color: s.color }}>{loading ? '...' : s.value}</div>
                  <div style={styles.cardLabel}>{s.label}</div>
                </div>
              </div>
              <div style={{ ...styles.cardSub, color: s.color }}>{loading ? '' : s.sub}</div>
            </div>
          ))}
        </div>

        {/* Two-column layout */}
        <div style={styles.twoCol}>
          {/* API Keys List */}
          <div style={styles.panel}>
            <div style={styles.panelHeader}>
              <span style={styles.panelTitle}>🔑 Recent API Keys</span>
              <button style={styles.linkBtn} onClick={() => navigate('/developer/keys')}>Manage All →</button>
            </div>
            {loading ? (
              <div style={styles.loading}>Loading…</div>
            ) : keys.length === 0 ? (
              <EmptyState icon="🔑" message="No API keys yet" action="Create Key" onAction={() => navigate('/developer/keys')} />
            ) : (
              <div style={styles.keyList}>
                {keys.slice(0, 5).map(k => (
                  <div key={k.id} style={styles.keyRow}>
                    <div style={styles.keyMeta}>
                      <span style={styles.keyName}>{k.name}</span>
                      <code style={styles.keyPrefix}>{k.key_prefix}••••••••</code>
                    </div>
                    <span style={{ ...styles.badge2, background: k.status === 'active' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)', color: k.status === 'active' ? '#10b981' : '#ef4444' }}>
                      {k.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Endpoint Breakdown */}
          <div style={styles.panel}>
            <div style={styles.panelHeader}>
              <span style={styles.panelTitle}>📊 Top Endpoints</span>
              <button style={styles.linkBtn} onClick={() => navigate('/developer/logs')}>View Logs →</button>
            </div>
            {loading ? (
              <div style={styles.loading}>Loading…</div>
            ) : endpoints.length === 0 ? (
              <EmptyState icon="📡" message="No requests yet. Start calling the API." />
            ) : (
              <div>
                {endpoints.map(([path, count], i) => {
                  const maxCount = endpoints[0][1];
                  const pct = Math.round((count / maxCount) * 100);
                  return (
                    <div key={i} style={styles.endpointRow}>
                      <div style={styles.endpointMeta}>
                        <code style={styles.endpointPath}>{path}</code>
                        <span style={styles.endpointCount}>{count.toLocaleString()} req</span>
                      </div>
                      <div style={styles.barBg}>
                        <div style={{ ...styles.barFill, width: `${pct}%`, background: `hsl(${240 - i * 30}, 80%, 65%)` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div style={styles.panel}>
          <div style={styles.panelHeader}>
            <span style={styles.panelTitle}>⚡ Quick Actions</span>
          </div>
          <div style={styles.quickGrid}>
            {[
              { icon: '🔑', label: 'Create API Key', desc: 'Generate a new scoped access key', path: '/developer/keys' },
              { icon: '🔗', label: 'Add Webhook', desc: 'Subscribe to real-time CRM events', path: '/developer/webhooks' },
              { icon: '🧪', label: 'API Explorer', desc: 'Live-test endpoints in your browser', path: '/developer/explorer' },
              { icon: '📖', label: 'Documentation', desc: 'Authentication, rate limits, SDKs', path: '/developer/docs' },
            ].map((action, i) => (
              <button key={i} style={styles.quickBtn} onClick={() => navigate(action.path)}>
                <span style={styles.quickIcon}>{action.icon}</span>
                <div>
                  <div style={styles.quickLabel}>{action.label}</div>
                  <div style={styles.quickDesc}>{action.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </RoleGuard>
  );
}

function EmptyState({ icon, message, action, onAction }) {
  return (
    <div style={{ textAlign: 'center', padding: '32px 16px', color: '#94a3b8' }}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 14, marginBottom: action ? 12 : 0 }}>{message}</div>
      {action && (
        <button style={styles.btnPrimary} onClick={onAction}>{action}</button>
      )}
    </div>
  );
}

const styles = {
  page: { padding: '32px', maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 32, flexWrap: 'wrap', gap: 16 },
  badge: { display: 'inline-block', background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  subtitle: { fontSize: 14, color: '#94a3b8', margin: 0 },
  headerActions: { display: 'flex', gap: 12 },
  btnPrimary: { background: 'linear-gradient(135deg, #6366f1, #818cf8)', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnSecondary: { background: 'rgba(99,102,241,0.1)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  statsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20, marginBottom: 24 },
  card: { background: '#1e293b', borderRadius: 12, padding: '20px', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' },
  cardTop: { display: 'flex', gap: 16, alignItems: 'center', marginBottom: 12 },
  iconBox: { width: 48, height: 48, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  statVal: { fontSize: 28, fontWeight: 700, lineHeight: 1 },
  cardLabel: { fontSize: 12, color: '#64748b', marginTop: 4 },
  cardSub: { fontSize: 12, fontWeight: 600 },
  twoCol: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 },
  panel: { background: '#1e293b', borderRadius: 12, padding: '20px', boxShadow: '0 4px 20px rgba(0,0,0,0.2)', marginBottom: 24 },
  panelHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  panelTitle: { fontSize: 14, fontWeight: 700, color: '#e2e8f0' },
  linkBtn: { background: 'none', border: 'none', color: '#818cf8', fontSize: 12, cursor: 'pointer', fontWeight: 600 },
  loading: { textAlign: 'center', color: '#64748b', padding: 24 },
  keyList: { display: 'flex', flexDirection: 'column', gap: 10 },
  keyRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: '#0f172a', borderRadius: 8 },
  keyMeta: { display: 'flex', flexDirection: 'column', gap: 3 },
  keyName: { fontSize: 13, fontWeight: 600, color: '#e2e8f0' },
  keyPrefix: { fontSize: 11, color: '#64748b', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: 4 },
  badge2: { padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 700 },
  endpointRow: { marginBottom: 12 },
  endpointMeta: { display: 'flex', justifyContent: 'space-between', marginBottom: 4 },
  endpointPath: { fontSize: 11, color: '#94a3b8', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: 4 },
  endpointCount: { fontSize: 11, color: '#64748b' },
  barBg: { background: 'rgba(255,255,255,0.06)', borderRadius: 4, height: 6, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4, transition: 'width 0.5s ease' },
  quickGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 },
  quickBtn: { display: 'flex', gap: 14, alignItems: 'center', background: '#0f172a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: 10, padding: '14px 16px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.2s' },
  quickIcon: { fontSize: 24, flexShrink: 0 },
  quickLabel: { fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 },
  quickDesc: { fontSize: 11, color: '#64748b' },
};
