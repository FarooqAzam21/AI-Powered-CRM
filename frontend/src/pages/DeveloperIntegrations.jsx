import React, { useEffect, useState } from 'react';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';

const PROVIDERS = [
  {
    id: 'google',
    name: 'Google / Gmail',
    description: 'Connect your Gmail account to sync emails, read contacts, and send messages directly from the CRM.',
    icon: '🔵',
    color: '#4285f4',
    features: ['Email sync', 'Contact import', 'OAuth 2.0', 'Bi-directional'],
    docsUrl: 'https://developers.google.com/gmail/api',
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Receive CRM notifications, deal alerts, and workflow completion events directly in Slack channels.',
    icon: '💬',
    color: '#4a154b',
    features: ['Notifications', 'Webhook events', 'Channel alerts', 'Coming soon'],
    docsUrl: '#',
    comingSoon: true,
  },
  {
    id: 'microsoft365',
    name: 'Microsoft 365',
    description: 'Sync Outlook emails, Teams notifications, and Calendar events with your CRM workspace.',
    icon: '🪟',
    color: '#0078d4',
    features: ['Outlook sync', 'Teams alerts', 'Calendar', 'Coming soon'],
    docsUrl: '#',
    comingSoon: true,
  },
  {
    id: 'salesforce',
    name: 'Salesforce',
    description: 'Bidirectional contact and deal sync between this CRM and Salesforce org.',
    icon: '☁️',
    color: '#00a1e0',
    features: ['Contact sync', 'Deal mapping', 'Field mapping', 'Coming soon'],
    docsUrl: '#',
    comingSoon: true,
  },
];

export default function DeveloperIntegrations() {
  const [connections, setConnections] = useState({});
  const [loading, setLoading] = useState(true);
  const [disconnecting, setDisconnecting] = useState(null);
  const [toast, setToast] = useState(null);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const fetchConnections = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/api/v1/developer/integrations`, { headers });
      if (r.ok) {
        const data = await r.json();
        // Index by provider
        const map = {};
        (Array.isArray(data) ? data : []).forEach(c => { map[c.provider] = c; });
        setConnections(map);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConnections(); }, []);

  const handleConnect = (provider) => {
    if (provider.id === 'google') {
      // Redirect to existing Google OAuth flow
      window.location.href = `${API_BASE}/auth/google`;
    } else {
      showToast(`${provider.name} integration coming soon!`, 'info');
    }
  };

  const handleDisconnect = async (providerId) => {
    setDisconnecting(providerId);
    try {
      const r = await fetch(`${API_BASE}/api/v1/developer/integrations/${providerId}/disconnect`, {
        method: 'DELETE',
        headers,
      });
      if (r.ok) {
        showToast('Integration disconnected successfully.');
        fetchConnections();
      } else {
        const err = await r.json().catch(() => ({}));
        showToast(err.detail || 'Failed to disconnect integration.', 'error');
      }
    } catch (e) {
      showToast('Network error. Please try again.', 'error');
    } finally {
      setDisconnecting(null);
    }
  };

  return (
    <RoleGuard roles={['Admin', 'Workspace Admin', 'Super Admin']}>
      <div style={styles.page}>
        {/* Toast */}
        {toast && (
          <div style={{
            ...styles.toast,
            background: toast.type === 'error' ? 'rgba(239,68,68,0.15)' : toast.type === 'info' ? 'rgba(99,102,241,0.15)' : 'rgba(16,185,129,0.15)',
            border: `1px solid ${toast.type === 'error' ? 'rgba(239,68,68,0.3)' : toast.type === 'info' ? 'rgba(99,102,241,0.3)' : 'rgba(16,185,129,0.3)'}`,
            color: toast.type === 'error' ? '#f87171' : toast.type === 'info' ? '#818cf8' : '#34d399',
          }}>
            {toast.message}
          </div>
        )}

        {/* Header */}
        <div style={styles.header}>
          <div>
            <span style={styles.badge}>Developer Platform</span>
            <h1 style={styles.title}>Integrations</h1>
            <p style={styles.subtitle}>Connect external services to enhance your CRM workflow. OAuth tokens are encrypted at rest.</p>
          </div>
          <button style={styles.btnSecondary} onClick={fetchConnections}>🔄 Refresh</button>
        </div>

        {/* Stats Row */}
        <div style={styles.statsRow}>
          <div style={styles.statCard}>
            <p style={styles.statLabel}>Connected</p>
            <p style={styles.statValue}>{Object.keys(connections).length}</p>
          </div>
          <div style={styles.statCard}>
            <p style={styles.statLabel}>Available</p>
            <p style={styles.statValue}>{PROVIDERS.length}</p>
          </div>
          <div style={styles.statCard}>
            <p style={styles.statLabel}>Token Security</p>
            <p style={{ ...styles.statValue, fontSize: 14, color: '#34d399' }}>AES-256 Encrypted</p>
          </div>
          <div style={styles.statCard}>
            <p style={styles.statLabel}>OAuth Standard</p>
            <p style={{ ...styles.statValue, fontSize: 14, color: '#818cf8' }}>2.0 / PKCE</p>
          </div>
        </div>

        {/* Provider Cards */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#64748b' }}>Loading integrations...</div>
        ) : (
          <div style={styles.grid}>
            {PROVIDERS.map(provider => {
              const conn = connections[provider.id];
              const isConnected = !!conn;
              const isDisconnecting = disconnecting === provider.id;

              return (
                <div key={provider.id} style={{
                  ...styles.card,
                  borderColor: isConnected ? 'rgba(52,211,153,0.3)' : 'rgba(255,255,255,0.06)',
                  boxShadow: isConnected ? '0 0 0 1px rgba(52,211,153,0.15), 0 4px 24px rgba(0,0,0,0.3)' : '0 4px 24px rgba(0,0,0,0.3)',
                }}>
                  {/* Card Header */}
                  <div style={styles.cardHeader}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                      <div style={{ ...styles.providerIcon, background: `${provider.color}22` }}>
                        <span style={{ fontSize: 24 }}>{provider.icon}</span>
                      </div>
                      <div>
                        <h3 style={styles.providerName}>{provider.name}</h3>
                        {isConnected && conn.account_email && (
                          <p style={styles.accountEmail}>📧 {conn.account_email}</p>
                        )}
                      </div>
                    </div>
                    <span style={{
                      ...styles.statusBadge,
                      background: isConnected ? 'rgba(52,211,153,0.12)' : provider.comingSoon ? 'rgba(251,191,36,0.12)' : 'rgba(100,116,139,0.12)',
                      color: isConnected ? '#34d399' : provider.comingSoon ? '#fbbf24' : '#64748b',
                    }}>
                      {isConnected ? '● Connected' : provider.comingSoon ? '⏳ Soon' : '○ Available'}
                    </span>
                  </div>

                  {/* Description */}
                  <p style={styles.description}>{provider.description}</p>

                  {/* Features */}
                  <div style={styles.featureRow}>
                    {provider.features.map(f => (
                      <span key={f} style={styles.featureTag}>{f}</span>
                    ))}
                  </div>

                  {/* Connected Details */}
                  {isConnected && (
                    <div style={styles.connectedInfo}>
                      <div style={styles.infoRow}>
                        <span style={styles.infoLabel}>Status</span>
                        <span style={{ color: '#34d399', fontSize: 13 }}>{conn.status || 'active'}</span>
                      </div>
                      {conn.token_expires_at && (
                        <div style={styles.infoRow}>
                          <span style={styles.infoLabel}>Token Expires</span>
                          <span style={{ color: '#94a3b8', fontSize: 13 }}>{new Date(conn.token_expires_at).toLocaleDateString()}</span>
                        </div>
                      )}
                      {conn.scopes && (
                        <div style={styles.infoRow}>
                          <span style={styles.infoLabel}>Scopes</span>
                          <span style={{ color: '#94a3b8', fontSize: 12, fontFamily: 'monospace' }}>
                            {Array.isArray(conn.scopes) ? conn.scopes.slice(0, 3).join(', ') : conn.scopes}
                            {Array.isArray(conn.scopes) && conn.scopes.length > 3 && ` +${conn.scopes.length - 3} more`}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div style={styles.cardActions}>
                    {isConnected ? (
                      <>
                        <button
                          style={styles.btnReconnect}
                          onClick={() => handleConnect(provider)}
                          disabled={provider.comingSoon}
                        >
                          🔁 Reconnect
                        </button>
                        <button
                          style={{ ...styles.btnDisconnect, opacity: isDisconnecting ? 0.6 : 1 }}
                          onClick={() => handleDisconnect(provider.id)}
                          disabled={isDisconnecting}
                        >
                          {isDisconnecting ? 'Disconnecting...' : '🔌 Disconnect'}
                        </button>
                      </>
                    ) : (
                      <button
                        style={{
                          ...styles.btnConnect,
                          opacity: provider.comingSoon ? 0.5 : 1,
                          cursor: provider.comingSoon ? 'not-allowed' : 'pointer',
                        }}
                        onClick={() => handleConnect(provider)}
                        disabled={provider.comingSoon}
                      >
                        {provider.comingSoon ? '⏳ Coming Soon' : '🔗 Connect'}
                      </button>
                    )}
                    {!provider.comingSoon && (
                      <a href={provider.docsUrl} target="_blank" rel="noreferrer" style={styles.docsLink}>
                        📄 Docs ↗
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Security Notice */}
        <div style={styles.securityNotice}>
          <span style={styles.securityIcon}>🔐</span>
          <div>
            <p style={styles.securityTitle}>Enterprise-Grade Token Security</p>
            <p style={styles.securityText}>
              All OAuth access tokens and refresh tokens are encrypted at rest using AES-256 / Fernet encryption before being stored.
              Raw tokens are never persisted to the database. Tokens are decrypted only in-memory when needed for API calls.
            </p>
          </div>
        </div>
      </div>
    </RoleGuard>
  );
}

const styles = {
  page: { padding: '32px', maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  toast: { position: 'fixed', top: 24, right: 24, zIndex: 9999, padding: '14px 20px', borderRadius: 10, fontSize: 14, fontWeight: 600, backdropFilter: 'blur(8px)' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 24, flexWrap: 'wrap', gap: 16 },
  badge: { display: 'inline-block', background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  subtitle: { fontSize: 14, color: '#94a3b8', margin: 0 },
  btnSecondary: { background: 'rgba(99,102,241,0.1)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8, padding: '10px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 28 },
  statCard: { background: '#1e293b', borderRadius: 12, padding: '18px 20px', border: '1px solid rgba(255,255,255,0.06)' },
  statLabel: { fontSize: 12, color: '#64748b', margin: '0 0 6px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 },
  statValue: { fontSize: 22, fontWeight: 700, color: '#f1f5f9', margin: 0 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(480px, 1fr))', gap: 20, marginBottom: 28 },
  card: { background: '#1e293b', borderRadius: 16, padding: '24px', border: '1px solid rgba(255,255,255,0.06)', transition: 'all 0.2s' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 },
  providerIcon: { width: 52, height: 52, borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  providerName: { fontSize: 17, fontWeight: 700, color: '#f1f5f9', margin: '0 0 4px' },
  accountEmail: { fontSize: 13, color: '#34d399', margin: 0 },
  statusBadge: { padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 700, whiteSpace: 'nowrap', flexShrink: 0 },
  description: { fontSize: 14, color: '#94a3b8', marginBottom: 16, lineHeight: 1.6 },
  featureRow: { display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 18 },
  featureTag: { background: 'rgba(99,102,241,0.1)', color: '#818cf8', padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600 },
  connectedInfo: { background: 'rgba(52,211,153,0.05)', border: '1px solid rgba(52,211,153,0.15)', borderRadius: 10, padding: '12px 16px', marginBottom: 18 },
  infoRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' },
  infoLabel: { fontSize: 12, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' },
  cardActions: { display: 'flex', gap: 10, alignItems: 'center' },
  btnConnect: { background: 'linear-gradient(135deg, #6366f1, #4f46e5)', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'opacity 0.2s' },
  btnReconnect: { background: 'rgba(99,102,241,0.1)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8, padding: '10px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnDisconnect: { background: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 8, padding: '10px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'opacity 0.2s' },
  docsLink: { color: '#64748b', fontSize: 13, textDecoration: 'none', fontWeight: 600 },
  securityNotice: { display: 'flex', gap: 16, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', borderRadius: 12, padding: '20px 24px', alignItems: 'flex-start' },
  securityIcon: { fontSize: 28, flexShrink: 0 },
  securityTitle: { fontSize: 15, fontWeight: 700, color: '#e2e8f0', margin: '0 0 6px' },
  securityText: { fontSize: 13, color: '#94a3b8', margin: 0, lineHeight: 1.6 },
};
