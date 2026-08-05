import React, { useEffect, useState } from 'react';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';

export default function OrganizationAdmin() {
  const [profile, setProfile] = useState(null);
  const [directory, setDirectory] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('directory');

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/api/v1/organization/profile`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/organization/directory`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/organization/departments`, { headers }).then(r => r.json()),
      fetch(`${API_BASE}/api/v1/organization/policies`, { headers }).then(r => r.json()),
    ]).then(([p, d, de, po]) => {
      setProfile(p);
      setDirectory(Array.isArray(d) ? d : []);
      setDepartments(Array.isArray(de) ? de : []);
      setPolicies(Array.isArray(po) ? po : []);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  return (
    <RoleGuard roles={['Super Admin', 'Admin']}>
      <div style={styles.page}>
        <div style={styles.header}>
          <div>
            <div style={styles.badge}>Enterprise Console</div>
            <h1 style={styles.title}>{profile?.name || 'Organization Admin'}</h1>
            <p style={styles.sub}>Manage departments, employee hierarchy, workspace policies, and user provisioning.</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div style={styles.tabBar}>
          {[
            { id: 'directory', label: '👥 Employee Directory' },
            { id: 'departments', label: '🏢 Departments' },
            { id: 'policies', label: '🛡️ Security & Policies' },
          ].map(t => (
            <button
              key={t.id}
              style={{
                ...styles.tabBtn,
                background: tab === t.id ? 'rgba(99,102,241,0.15)' : 'transparent',
                color: tab === t.id ? '#818cf8' : '#94a3b8',
                borderColor: tab === t.id ? '#6366f1' : 'transparent'
              }}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={styles.loading}>Loading Organization Data…</div>
        ) : (
          <div style={styles.panel}>
            {tab === 'directory' && (
              <table style={styles.table}>
                <thead>
                  <tr>
                    {['Name', 'Email', 'Role', 'Job Title', 'Department', 'Status'].map(h => (
                      <th key={h} style={styles.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {directory.map(u => (
                    <tr key={u.id} style={styles.tr}>
                      <td style={styles.td}><strong>{u.name}</strong></td>
                      <td style={styles.td}>{u.email}</td>
                      <td style={styles.td}><span style={styles.roleTag}>{u.role}</span></td>
                      <td style={styles.td}>{u.job_title || '—'}</td>
                      <td style={styles.td}>{u.department || 'Unassigned'}</td>
                      <td style={styles.td}>
                        <span style={{ ...styles.statusBadge, color: u.status === 'active' ? '#10b981' : '#ef4444' }}>
                          {u.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {tab === 'departments' && (
              <div style={styles.grid}>
                {departments.map(d => (
                  <div key={d.id} style={styles.card}>
                    <div style={styles.cardTitle}>{d.name}</div>
                    <div style={styles.cardSub}>Code: {d.code || 'N/A'}</div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'policies' && (
              <div style={styles.grid}>
                {policies.length === 0 ? (
                  <div style={styles.empty}>No security policies defined yet.</div>
                ) : (
                  policies.map(p => (
                    <div key={p.id} style={styles.card}>
                      <div style={styles.cardTitle}>{p.name}</div>
                      <div style={styles.cardSub}>Type: {p.policy_type}</div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </RoleGuard>
  );
}

const styles = {
  page: { padding: 32, maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { marginBottom: 24 },
  badge: { display: 'inline-block', background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 8 },
  title: { fontSize: 26, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  sub: { color: '#64748b', fontSize: 14, margin: 0 },
  tabBar: { display: 'flex', gap: 8, marginBottom: 20, borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: 8 },
  tabBtn: { border: '1px solid', borderRadius: 8, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s' },
  panel: { background: '#1e293b', borderRadius: 12, padding: 20, boxShadow: '0 4px 20px rgba(0,0,0,0.2)' },
  loading: { textAlign: 'center', padding: 40, color: '#64748b' },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '10px 14px', fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', borderBottom: '1px solid rgba(255,255,255,0.06)' },
  tr: { borderBottom: '1px solid rgba(255,255,255,0.04)' },
  td: { padding: '12px 14px', fontSize: 13, color: '#e2e8f0' },
  roleTag: { background: 'rgba(99,102,241,0.12)', color: '#818cf8', padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600 },
  statusBadge: { fontSize: 12, fontWeight: 700 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 },
  card: { background: '#0f172a', borderRadius: 10, padding: 16, border: '1px solid rgba(255,255,255,0.06)' },
  cardTitle: { fontSize: 14, fontWeight: 700, color: '#e2e8f0', marginBottom: 4 },
  cardSub: { fontSize: 12, color: '#64748b' },
  empty: { color: '#64748b', textAlign: 'center', padding: 30 }
};
