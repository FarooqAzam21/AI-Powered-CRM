import React, { useEffect, useState } from 'react';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';

export default function DeveloperLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  const fetchLogs = () => {
    setLoading(true);
    fetch(`${API_BASE}/api/v1/developer/logs?limit=100`, { headers })
      .then(r => r.json())
      .then(data => setLogs(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchLogs(); }, []);

  const filteredLogs = logs.filter(log => {
    if (filterStatus !== 'ALL' && log.status !== filterStatus) return false;
    if (searchTerm && !log.resource.toLowerCase().includes(searchTerm.toLowerCase()) && !log.details?.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  return (
    <RoleGuard roles={['Admin', 'Workspace Admin', 'Super Admin']}>
      <div style={styles.page}>
        <div style={styles.header}>
          <div>
            <span style={styles.badge}>Developer Platform</span>
            <h1 style={styles.title}>API Request Logs</h1>
            <p style={styles.subtitle}>Audit trail of authenticated API requests, execution status, and latencies.</p>
          </div>
          <button style={styles.btnSecondary} onClick={fetchLogs}>🔄 Refresh Logs</button>
        </div>

        {/* Filters */}
        <div style={styles.filterRow}>
          <input
            type="text"
            placeholder="Filter by endpoint or details..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={styles.searchInput}
          />
          <div style={styles.pillGroup}>
            {['ALL', 'ALLOWED', 'DENIED'].map(st => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                style={{
                  ...styles.pill,
                  background: filterStatus === st ? '#6366f1' : '#1e293b',
                  color: filterStatus === st ? '#fff' : '#94a3b8',
                }}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Logs Table */}
        <div style={styles.tableCard}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 32, color: '#64748b' }}>Loading request logs...</div>
          ) : filteredLogs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 32, color: '#64748b' }}>No matching API requests found.</div>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr style={styles.thRow}>
                  <th style={styles.th}>Timestamp</th>
                  <th style={styles.th}>Status</th>
                  <th style={styles.th}>Endpoint / Resource</th>
                  <th style={styles.th}>Client IP</th>
                  <th style={styles.th}>Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map(log => {
                  const isSuccess = log.status === 'ALLOWED';
                  return (
                    <tr key={log.id} style={styles.tr}>
                      <td style={styles.tdTime}>{new Date(log.created_at).toLocaleString()}</td>
                      <td style={styles.td}>
                        <span style={{
                          ...styles.statusBadge,
                          background: isSuccess ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
                          color: isSuccess ? '#34d399' : '#f87171',
                        }}>
                          {log.status}
                        </span>
                      </td>
                      <td style={styles.tdEndpoint}>{log.resource}</td>
                      <td style={styles.tdMuted}>{log.ip_address || '—'}</td>
                      <td style={styles.tdDetails}>{log.details || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </RoleGuard>
  );
}

const styles = {
  page: { padding: '32px', maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 24, flexWrap: 'wrap', gap: 16 },
  badge: { display: 'inline-block', background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  subtitle: { fontSize: 14, color: '#94a3b8', margin: 0 },
  btnSecondary: { background: 'rgba(99,102,241,0.1)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 8, padding: '10px 18px', fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  filterRow: { display: 'flex', gap: 16, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' },
  searchInput: { flex: 1, minWidth: 260, background: '#1e293b', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '10px 14px', color: '#f1f5f9', fontSize: 13 },
  pillGroup: { display: 'flex', gap: 8 },
  pill: { border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 12, fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' },
  tableCard: { background: '#1e293b', borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' },
  table: { width: '100%', borderCollapse: 'collapse', textAlign: 'left' },
  thRow: { borderBottom: '1px solid rgba(255,255,255,0.08)', background: '#0f172a' },
  th: { padding: '12px 16px', fontSize: 12, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' },
  tr: { borderBottom: '1px solid rgba(255,255,255,0.04)' },
  td: { padding: '12px 16px', fontSize: 13, color: '#e2e8f0' },
  tdTime: { padding: '12px 16px', fontSize: 12, color: '#94a3b8', whiteSpace: 'nowrap' },
  tdEndpoint: { padding: '12px 16px', fontSize: 13, color: '#38bdf8', fontFamily: 'monospace' },
  tdMuted: { padding: '12px 16px', fontSize: 12, color: '#64748b' },
  tdDetails: { padding: '12px 16px', fontSize: 12, color: '#cbd5e1' },
  statusBadge: { padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700 },
};
