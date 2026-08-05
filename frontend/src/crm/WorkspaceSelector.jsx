import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE = 'http://localhost:8000';

export default function WorkspaceSelector() {
  const { refreshWorkspaceContext } = useAuth();
  const [workspaces, setWorkspaces] = useState([]);
  const [currentWs, setCurrentWs] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newWsName, setNewWsName] = useState('');
  const [newWsType, setNewWsType] = useState('Team');

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchWorkspaces = () => {
    fetch(`${API_BASE}/api/v1/workspaces`, { headers })
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          setWorkspaces(data);
          const activeId = localStorage.getItem('active_workspace_id');
          const matched = data.find(w => w.id === parseInt(activeId)) || data[0];
          if (matched) {
            setCurrentWs(matched);
            localStorage.setItem('active_workspace_id', matched.id);
          }
        }
      })
      .catch(console.error);
  };

  useEffect(() => {
    if (token) fetchWorkspaces();
  }, [token]);

  const selectWorkspace = async (ws) => {
    setCurrentWs(ws);
    localStorage.setItem('active_workspace_id', ws.id);
    setIsOpen(false);
    await refreshWorkspaceContext(ws.id);
    window.location.reload();
  };

  const handleCreate = async () => {
    if (!newWsName.trim()) return;
    const res = await fetch(`${API_BASE}/api/v1/workspaces`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ name: newWsName, type: newWsType })
    });
    if (res.ok) {
      const created = await res.json();
      setNewWsName('');
      setShowCreate(false);
      fetchWorkspaces();
      selectWorkspace(created);
    }
  };

  if (!currentWs) return null;

  return (
    <div style={styles.container}>
      <button style={styles.selectorBtn} onClick={() => setIsOpen(!isOpen)}>
        <div style={{ ...styles.avatar, background: currentWs.brand_color || '#6366f1' }}>
          {currentWs.name.charAt(0).toUpperCase()}
        </div>
        <div style={styles.meta}>
          <div style={styles.wsName}>{currentWs.name}</div>
          <div style={styles.wsTag}>{currentWs.type || 'Team'} Workspace</div>
        </div>
        <span style={styles.chevron}>▾</span>
      </button>

      {isOpen && (
        <div style={styles.dropdown}>
          <div style={styles.menuHeader}>Switch Workspace</div>
          {workspaces.map(ws => (
            <div
              key={ws.id}
              style={{
                ...styles.menuItem,
                background: ws.id === currentWs.id ? 'rgba(99,102,241,0.15)' : 'transparent'
              }}
              onClick={() => selectWorkspace(ws)}
            >
              <div style={{ ...styles.avatarSmall, background: ws.brand_color || '#6366f1' }}>
                {ws.name.charAt(0).toUpperCase()}
              </div>
              <span style={styles.menuText}>{ws.name}</span>
              {ws.id === currentWs.id && <span style={styles.check}>✓</span>}
            </div>
          ))}
          <div style={styles.divider} />
          <button style={styles.createBtn} onClick={() => { setIsOpen(false); setShowCreate(true); }}>
            ＋ Create New Workspace
          </button>
        </div>
      )}

      {showCreate && (
        <div style={styles.overlay}>
          <div style={styles.modal}>
            <h3 style={styles.modalTitle}>Create Workspace</h3>
            <div style={styles.field}>
              <label style={styles.label}>Workspace Name</label>
              <input
                style={styles.input}
                placeholder="e.g. Sales Division"
                value={newWsName}
                onChange={e => setNewWsName(e.target.value)}
              />
            </div>
            <div style={styles.field}>
              <label style={styles.label}>Workspace Type</label>
              <select
                style={styles.input}
                value={newWsType}
                onChange={e => setNewWsType(e.target.value)}
              >
                <option value="Personal">Personal Workspace</option>
                <option value="Team">Team Workspace</option>
                <option value="Enterprise">Enterprise Workspace</option>
              </select>
            </div>
            <div style={styles.modalActions}>
              <button style={styles.cancelBtn} onClick={() => setShowCreate(false)}>Cancel</button>
              <button style={styles.submitBtn} onClick={handleCreate}>Create Workspace</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { position: 'relative', margin: '12px 16px 8px' },
  selectorBtn: { display: 'flex', alignItems: 'center', width: '100%', gap: 10, background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 10, padding: '8px 12px', cursor: 'pointer', color: '#e2e8f0' },
  avatar: { width: 30, height: 30, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#fff', fontSize: 13 },
  meta: { flex: 1, textAlign: 'left', overflow: 'hidden' },
  wsName: { fontSize: 13, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  wsTag: { fontSize: 10, color: '#64748b' },
  chevron: { color: '#64748b', fontSize: 12 },
  dropdown: { position: 'absolute', top: '100%', left: 0, right: 0, marginTop: 6, background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, padding: 6, zIndex: 100, boxShadow: '0 10px 25px rgba(0,0,0,0.4)' },
  menuHeader: { fontSize: 10, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', padding: '6px 10px' },
  menuItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 6, cursor: 'pointer', fontSize: 13, color: '#e2e8f0' },
  avatarSmall: { width: 22, height: 22, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#fff', fontSize: 11 },
  menuText: { flex: 1 },
  check: { color: '#818cf8', fontWeight: 700 },
  divider: { height: 1, background: 'rgba(255,255,255,0.06)', margin: '6px 0' },
  createBtn: { width: '100%', background: 'none', border: 'none', color: '#818cf8', fontSize: 12, fontWeight: 600, padding: '8px 10px', cursor: 'pointer', textAlign: 'left' },
  overlay: { position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  modal: { background: '#1e293b', borderRadius: 14, padding: 24, width: 360, color: '#e2e8f0' },
  modalTitle: { margin: '0 0 16px', fontSize: 16, fontWeight: 700 },
  field: { marginBottom: 14 },
  label: { display: 'block', fontSize: 12, fontWeight: 600, color: '#94a3b8', marginBottom: 6 },
  input: { width: '100%', background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '8px 12px', color: '#e2e8f0', fontSize: 13, boxSizing: 'border-box' },
  modalActions: { display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 20 },
  cancelBtn: { background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '8px 14px' },
  submitBtn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontWeight: 600, cursor: 'pointer' }
};
