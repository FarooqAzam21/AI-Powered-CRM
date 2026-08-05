import React, { useState } from 'react';
import RoleGuard from '../security/RoleGuard';

const API_BASE = 'http://localhost:8000';

const ENDPOINTS = [
  { method: 'GET',  path: '/contacts',            body: null,  desc: 'List contacts', params: [{ name: 'skip', default: '0' }, { name: 'limit', default: '20' }, { name: 'search', default: '' }] },
  { method: 'POST', path: '/contacts',            body: '{\n  "email": "john@example.com",\n  "name": "John Smith",\n  "company": "Acme Corp"\n}',  desc: 'Create contact', params: [] },
  { method: 'GET',  path: '/api/v1/deals/',       body: null,  desc: 'List pipeline deals', params: [{ name: 'limit', default: '20' }] },
  { method: 'POST', path: '/api/v1/deals/',       body: '{\n  "name": "Enterprise Deal",\n  "value": 50000,\n  "stage": "prospecting"\n}',  desc: 'Create deal', params: [] },
  { method: 'GET',  path: '/api/v1/campaigns',   body: null,  desc: 'List email campaigns', params: [{ name: 'limit', default: '10' }] },
  { method: 'GET',  path: '/crm/contacts',        body: null,  desc: 'CRM contacts with interactions', params: [{ name: 'limit', default: '50' }] },
  { method: 'GET',  path: '/crm/insights',        body: null,  desc: 'AI-generated insights', params: [{ name: 'limit', default: '10' }] },
  { method: 'GET',  path: '/crm/pipeline',        body: null,  desc: 'Pipeline stage summary', params: [] },
  { method: 'GET',  path: '/api/v1/developer/usage', body: null, desc: 'API usage analytics', params: [] },
  { method: 'GET',  path: '/api/v1/developer/keys',  body: null, desc: 'List API keys', params: [] },
];

const METHOD_COLORS = { GET: '#10b981', POST: '#6366f1', PUT: '#f59e0b', DELETE: '#ef4444', PATCH: '#06b6d4' };

export default function APIExplorer() {
  const [selectedEndpoint, setSelectedEndpoint] = useState(ENDPOINTS[0]);
  const [apiKey, setApiKey] = useState('');
  const [params, setParams] = useState({});
  const [body, setBody] = useState(ENDPOINTS[0].body || '');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [statusCode, setStatusCode] = useState(null);
  const [latency, setLatency] = useState(null);

  const selectEndpoint = (ep) => {
    setSelectedEndpoint(ep);
    setBody(ep.body || '');
    setParams({});
    setResponse(null);
    setStatusCode(null);
  };

  const buildUrl = () => {
    let url = `${API_BASE}${selectedEndpoint.path}`;
    const qp = selectedEndpoint.params?.filter(p => params[p.name] || p.default).map(p => `${p.name}=${encodeURIComponent(params[p.name] ?? p.default)}`).join('&');
    if (qp) url += `?${qp}`;
    return url;
  };

  const execute = async () => {
    if (!apiKey) return alert('Enter an API Key to execute requests');
    setLoading(true);
    setResponse(null);
    const start = Date.now();
    try {
      const opts = {
        method: selectedEndpoint.method,
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
      };
      if (body && selectedEndpoint.method !== 'GET') {
        opts.body = body;
      }
      const res = await fetch(buildUrl(), opts);
      setStatusCode(res.status);
      setLatency(Date.now() - start);
      const ct = res.headers.get('content-type') || '';
      const data = ct.includes('json') ? await res.json() : await res.text();
      setResponse(data);
    } catch (e) {
      setResponse({ error: e.message });
      setStatusCode(0);
      setLatency(Date.now() - start);
    }
    setLoading(false);
  };

  const statusColor = statusCode >= 200 && statusCode < 300 ? '#10b981' : statusCode >= 400 ? '#ef4444' : '#f59e0b';

  return (
    <RoleGuard roles={['Admin', 'Workspace Admin', 'Super Admin']}>
      <div style={s.page}>
        <div style={s.header}>
          <div>
            <div style={s.badge}>Interactive</div>
            <h1 style={s.title}>🧪 API Explorer</h1>
            <p style={s.sub}>Live-test CRM API endpoints directly from your browser using your API key.</p>
          </div>
        </div>

        {/* API Key Input */}
        <div style={s.keyBar}>
          <span style={s.keyLabel}>🔑 API Key</span>
          <input style={s.keyInput} type="password" placeholder="crm_live_..." value={apiKey} onChange={e => setApiKey(e.target.value)} />
          <div style={s.keyHint}>Enter a Live or Test key to authenticate requests</div>
        </div>

        <div style={s.layout}>
          {/* Endpoint List */}
          <div style={s.sidebar}>
            <div style={s.sidebarTitle}>Endpoints</div>
            {ENDPOINTS.map((ep, i) => (
              <button key={i} style={{ ...s.epItem, background: selectedEndpoint.path === ep.path && selectedEndpoint.method === ep.method ? 'rgba(99,102,241,0.15)' : 'transparent', borderLeft: selectedEndpoint.path === ep.path && selectedEndpoint.method === ep.method ? '3px solid #6366f1' : '3px solid transparent' }} onClick={() => selectEndpoint(ep)}>
                <span style={{ ...s.method, color: METHOD_COLORS[ep.method] }}>{ep.method}</span>
                <span style={s.epPath}>{ep.path}</span>
              </button>
            ))}
          </div>

          {/* Request / Response Panel */}
          <div style={s.main}>
            {/* Request builder */}
            <div style={s.panel}>
              <div style={s.panelHeader}>
                <span style={{ ...s.methodBig, color: METHOD_COLORS[selectedEndpoint.method], background: `${METHOD_COLORS[selectedEndpoint.method]}18` }}>{selectedEndpoint.method}</span>
                <code style={s.pathBig}>{buildUrl()}</code>
              </div>
              <p style={s.epDesc}>{selectedEndpoint.desc}</p>

              {/* Query Params */}
              {selectedEndpoint.params?.length > 0 && (
                <div style={s.section}>
                  <div style={s.sectionTitle}>Query Parameters</div>
                  <div style={s.paramsGrid}>
                    {selectedEndpoint.params.map(p => (
                      <div key={p.name} style={s.paramRow}>
                        <label style={s.paramLabel}>{p.name}</label>
                        <input style={s.paramInput} placeholder={p.default} value={params[p.name] ?? ''} onChange={e => setParams(prev => ({ ...prev, [p.name]: e.target.value }))} />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Body */}
              {selectedEndpoint.body !== null && (
                <div style={s.section}>
                  <div style={s.sectionTitle}>Request Body (JSON)</div>
                  <textarea style={s.bodyEditor} value={body} onChange={e => setBody(e.target.value)} rows={6} spellCheck={false} />
                </div>
              )}

              <button style={s.btnRun} onClick={execute} disabled={loading}>
                {loading ? '⏳ Sending…' : '▶ Execute Request'}
              </button>
            </div>

            {/* Response */}
            <div style={s.panel}>
              <div style={s.responseHeader}>
                <span style={s.sectionTitle}>Response</span>
                {statusCode !== null && (
                  <div style={s.responseMeta}>
                    <span style={{ ...s.statusBadge, color: statusColor, background: `${statusColor}18` }}>{statusCode}</span>
                    <span style={s.latencyBadge}>{latency}ms</span>
                  </div>
                )}
              </div>
              {response === null ? (
                <div style={s.emptyResponse}>
                  <div style={{ fontSize: 36, marginBottom: 12 }}>📭</div>
                  <div style={{ color: '#64748b', fontSize: 13 }}>Execute a request to see the response here</div>
                </div>
              ) : (
                <div style={{ position: 'relative' }}>
                  <button style={s.copyRes} onClick={() => navigator.clipboard.writeText(JSON.stringify(response, null, 2))}>Copy</button>
                  <pre style={s.responseBody}>{JSON.stringify(response, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </RoleGuard>
  );
}

const s = {
  page: { padding: 32, maxWidth: 1300, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { marginBottom: 24 },
  badge: { display: 'inline-block', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 8 },
  title: { fontSize: 26, fontWeight: 700, color: '#f1f5f9', margin: '0 0 6px' },
  sub: { color: '#64748b', fontSize: 14, margin: 0 },
  keyBar: { display: 'flex', gap: 12, alignItems: 'center', background: '#1e293b', borderRadius: 10, padding: '14px 20px', marginBottom: 24, flexWrap: 'wrap' },
  keyLabel: { fontSize: 13, fontWeight: 700, color: '#94a3b8', whiteSpace: 'nowrap' },
  keyInput: { flex: 1, minWidth: 280, background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8, padding: '9px 14px', color: '#e2e8f0', fontSize: 14, outline: 'none' },
  keyHint: { fontSize: 11, color: '#64748b', whiteSpace: 'nowrap' },
  layout: { display: 'grid', gridTemplateColumns: '220px 1fr', gap: 20 },
  sidebar: { background: '#1e293b', borderRadius: 12, padding: '16px 8px' },
  sidebarTitle: { fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', padding: '0 10px', marginBottom: 10 },
  epItem: { display: 'flex', gap: 8, alignItems: 'center', width: '100%', textAlign: 'left', padding: '9px 12px', border: 'none', borderRadius: 6, cursor: 'pointer', transition: 'all 0.15s', marginBottom: 2 },
  method: { fontSize: 10, fontWeight: 900, minWidth: 36, textAlign: 'right' },
  epPath: { fontSize: 11, color: '#94a3b8', wordBreak: 'break-all', lineHeight: 1.3 },
  main: { display: 'flex', flexDirection: 'column', gap: 20 },
  panel: { background: '#1e293b', borderRadius: 12, padding: '20px', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' },
  panelHeader: { display: 'flex', gap: 14, alignItems: 'center', marginBottom: 10 },
  methodBig: { padding: '5px 12px', borderRadius: 8, fontSize: 12, fontWeight: 900 },
  pathBig: { fontSize: 13, color: '#e2e8f0', wordBreak: 'break-all' },
  epDesc: { fontSize: 13, color: '#64748b', margin: '0 0 20px' },
  section: { marginBottom: 18 },
  sectionTitle: { fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 },
  paramsGrid: { display: 'flex', flexDirection: 'column', gap: 8 },
  paramRow: { display: 'grid', gridTemplateColumns: '120px 1fr', gap: 12, alignItems: 'center' },
  paramLabel: { fontSize: 12, fontWeight: 600, color: '#94a3b8' },
  paramInput: { background: '#0f172a', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6, padding: '7px 12px', color: '#e2e8f0', fontSize: 13, outline: 'none' },
  bodyEditor: { width: '100%', background: '#0a0f1a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '12px 14px', color: '#e2e8f0', fontSize: 12, fontFamily: 'monospace', lineHeight: 1.6, resize: 'vertical', boxSizing: 'border-box', outline: 'none' },
  btnRun: { background: 'linear-gradient(135deg, #6366f1, #818cf8)', color: '#fff', border: 'none', borderRadius: 8, padding: '11px 24px', fontSize: 14, fontWeight: 700, cursor: 'pointer', width: '100%', marginTop: 8 },
  responseHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  responseMeta: { display: 'flex', gap: 8, alignItems: 'center' },
  statusBadge: { padding: '3px 10px', borderRadius: 10, fontSize: 12, fontWeight: 700 },
  latencyBadge: { fontSize: 11, color: '#64748b' },
  emptyResponse: { textAlign: 'center', padding: '48px 20px' },
  responseBody: { background: '#0a0f1a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: '16px 18px', color: '#e2e8f0', fontSize: 12, lineHeight: 1.7, overflowX: 'auto', maxHeight: 400, overflowY: 'auto', margin: 0, whiteSpace: 'pre-wrap' },
  copyRes: { position: 'absolute', top: 10, right: 10, background: 'rgba(255,255,255,0.08)', border: 'none', color: '#94a3b8', borderRadius: 6, padding: '4px 10px', fontSize: 11, cursor: 'pointer' },
};
