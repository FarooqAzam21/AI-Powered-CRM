import React, { useState } from 'react';

const SECTIONS = [
  { id: 'auth', label: '🔐 Authentication' },
  { id: 'rate', label: '⚡ Rate Limiting' },
  { id: 'events', label: '🔔 Webhook Events' },
  { id: 'sdk-python', label: '🐍 Python SDK' },
  { id: 'sdk-node', label: '⬡ Node.js SDK' },
  { id: 'errors', label: '🚨 Error Codes' },
];

const CODE = {
  auth: `# Bearer Token authentication
curl -H "Authorization: Bearer crm_live_YOUR_API_KEY" \\
     https://your-crm.com/contacts

# X-API-Key header (alternative)
curl -H "X-API-Key: crm_live_YOUR_API_KEY" \\
     https://your-crm.com/contacts`,

  rate: `# Rate limit headers returned on every API response
X-RateLimit-Limit: 60         # Max requests per minute
X-RateLimit-Remaining: 47     # Remaining this window
X-RateLimit-Reset: 38         # Seconds until reset

# When exceeded:
HTTP 429 Too Many Requests
Retry-After: 22               # Seconds to wait`,

  'sdk-python': `import requests

API_KEY = "crm_live_YOUR_KEY"
BASE_URL = "https://your-crm.com"

headers = {"Authorization": f"Bearer {API_KEY}"}

# List contacts
contacts = requests.get(f"{BASE_URL}/contacts", headers=headers).json()

# Create contact
new_contact = requests.post(
    f"{BASE_URL}/contacts",
    headers={**headers, "Content-Type": "application/json"},
    json={"email": "john@company.com", "name": "John Smith", "company": "Acme"}
).json()`,

  'sdk-node': `const fetch = require('node-fetch');

const API_KEY = 'crm_live_YOUR_KEY';
const BASE_URL = 'https://your-crm.com';

const headers = {
  Authorization: \`Bearer \${API_KEY}\`,
  'Content-Type': 'application/json',
};

// List contacts
const contacts = await fetch(\`\${BASE_URL}/contacts\`, { headers }).then(r => r.json());

// Create contact
const newContact = await fetch(\`\${BASE_URL}/contacts\`, {
  method: 'POST',
  headers,
  body: JSON.stringify({ email: 'jane@company.com', name: 'Jane Doe' }),
}).then(r => r.json());`,

  events: `// Webhook payload structure
{
  "event": "contact.created",
  "timestamp": "2025-01-23T10:15:00Z",
  "data": {
    "id": 142,
    "email": "john@acme.com",
    "name": "John Smith",
    "company": "Acme Corp"
  }
}

// Verify signature on your server (Python)
import hmac, hashlib

def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)`,

  errors: `// Standard error response format
{
  "detail": "Insufficient API key scopes"
}

// HTTP Status Codes:
// 200 — OK
// 400 — Bad Request (validation error)
// 401 — Unauthorized (invalid/expired key)
// 403 — Forbidden (insufficient scope)
// 404 — Not Found
// 409 — Conflict (e.g. contact already exists)
// 429 — Too Many Requests (rate limited)
// 500 — Internal Server Error`,
};

const ENDPOINTS = [
  { method: 'GET',    path: '/contacts',            scope: 'contacts.read',   desc: 'List contacts with pagination and search' },
  { method: 'POST',   path: '/contacts',            scope: 'contacts.write',  desc: 'Create a new contact record' },
  { method: 'PUT',    path: '/contacts/{id}',       scope: 'contacts.write',  desc: 'Update an existing contact' },
  { method: 'GET',    path: '/api/v1/deals/',       scope: 'crm.read',        desc: 'List all deals in pipeline' },
  { method: 'POST',   path: '/api/v1/deals/',       scope: 'crm.write',       desc: 'Create a new deal' },
  { method: 'PUT',    path: '/api/v1/deals/{id}',   scope: 'crm.write',       desc: 'Update a deal record' },
  { method: 'GET',    path: '/api/v1/campaigns',    scope: 'campaigns.read',  desc: 'List email campaigns' },
  { method: 'POST',   path: '/api/v1/campaigns/{id}/start', scope: 'campaigns.write', desc: 'Launch a campaign' },
  { method: 'GET',    path: '/crm/contacts',        scope: 'crm.read',        desc: 'Full contact list with interactions' },
  { method: 'GET',    path: '/crm/insights',        scope: 'analytics.read',  desc: 'AI-generated CRM insights' },
];

const METHOD_COLORS = { GET: '#10b981', POST: '#6366f1', PUT: '#f59e0b', DELETE: '#ef4444', PATCH: '#06b6d4' };

export default function Documentation() {
  const [activeSection, setActiveSection] = useState('auth');

  return (
    <div style={s.page}>
      <div style={s.header}>
        <div style={s.badge}>Developer Documentation</div>
        <h1 style={s.title}>API Reference</h1>
        <p style={s.sub}>Everything you need to integrate your systems with the Enterprise CRM.</p>
      </div>

      <div style={s.layout}>
        {/* Sidebar nav */}
        <nav style={s.nav}>
          {SECTIONS.map(sec => (
            <button key={sec.id} style={{ ...s.navItem, background: activeSection === sec.id ? 'rgba(99,102,241,0.15)' : 'transparent', color: activeSection === sec.id ? '#818cf8' : '#94a3b8', borderLeft: activeSection === sec.id ? '3px solid #6366f1' : '3px solid transparent' }} onClick={() => setActiveSection(sec.id)}>
              {sec.label}
            </button>
          ))}
          <div style={s.navDivider} />
          <button style={{ ...s.navItem, color: '#94a3b8', borderLeft: '3px solid transparent' }} onClick={() => setActiveSection('endpoints')}>📋 Endpoint Index</button>
        </nav>

        {/* Content */}
        <div style={s.content}>
          {activeSection === 'auth' && (
            <Section title="🔐 Authentication" desc="All API requests must include a valid API key. Keys are generated in the API Keys section and scoped to specific permissions.">
              <h3 style={s.h3}>Bearer Token (Recommended)</h3>
              <p style={s.p}>Pass your key in the <code style={s.icode}>Authorization</code> header using the Bearer scheme:</p>
              <CodeBlock code={CODE.auth} />
              <h3 style={s.h3}>Key Format</h3>
              <div style={s.infoGrid}>
                <div style={s.infoCard}><div style={s.infoIcon}>🔴</div><div style={s.infoLabel}>Live Keys</div><code style={s.prefixDemo}>crm_live_xxxxxxxxxxxx</code><p style={s.infoP}>Use for production systems</p></div>
                <div style={s.infoCard}><div style={s.infoIcon}>🧪</div><div style={s.infoLabel}>Test Keys</div><code style={s.prefixDemo}>crm_test_xxxxxxxxxxxx</code><p style={s.infoP}>Use for development/staging</p></div>
              </div>
            </Section>
          )}

          {activeSection === 'rate' && (
            <Section title="⚡ Rate Limiting" desc="API requests are rate-limited per key using a sliding window algorithm. Limits are configurable per key.">
              <CodeBlock code={CODE.rate} />
              <h3 style={s.h3}>Default Limits</h3>
              <div style={s.table}>
                {[['Per Minute', '60 requests'], ['Per Day', '1,000 requests'], ['Custom', 'Set per key in Admin panel']].map(([k, v]) => (
                  <div key={k} style={s.tableRow}><span style={s.tableKey}>{k}</span><span style={s.tableVal}>{v}</span></div>
                ))}
              </div>
            </Section>
          )}

          {activeSection === 'events' && (
            <Section title="🔔 Webhook Events" desc="Register a webhook endpoint to receive real-time notifications when CRM events occur.">
              <CodeBlock code={CODE.events} />
              <h3 style={s.h3}>Available Events</h3>
              {[['contact.created','Contact Created','A new contact is added to the CRM'],['contact.updated','Contact Updated','A contact record is modified'],['deal.created','Deal Created','A new deal is added'],['deal.won','Deal Won','A deal is marked as closed won'],['deal.lost','Deal Lost','A deal is marked as closed lost'],['campaign.started','Campaign Started','An email campaign is launched']].map(([evt, label, desc]) => (
                <div key={evt} style={s.evtDocRow}>
                  <code style={s.evtCode}>{evt}</code>
                  <div><div style={s.evtTitle}>{label}</div><div style={s.evtDocDesc}>{desc}</div></div>
                </div>
              ))}
            </Section>
          )}

          {(activeSection === 'sdk-python' || activeSection === 'sdk-node') && (
            <Section title={activeSection === 'sdk-python' ? '🐍 Python Integration' : '⬡ Node.js Integration'} desc="Copy and customize this snippet to start integrating your system with the CRM API.">
              <CodeBlock code={CODE[activeSection]} />
            </Section>
          )}

          {activeSection === 'errors' && (
            <Section title="🚨 Error Reference" desc="All API errors return a structured JSON body with a detail field.">
              <CodeBlock code={CODE.errors} />
            </Section>
          )}

          {activeSection === 'endpoints' && (
            <Section title="📋 Endpoint Index" desc="Full list of available REST API endpoints and required scopes.">
              <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '70px 1fr 140px 1fr', background: '#0f172a', padding: '10px 14px', fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  <span>Method</span><span>Path</span><span>Scope</span><span>Description</span>
                </div>
                {ENDPOINTS.map((ep, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '70px 1fr 140px 1fr', padding: '12px 14px', borderTop: '1px solid rgba(255,255,255,0.04)', background: i % 2 === 0 ? '#1e293b' : '#0f172a' }}>
                    <span style={{ color: METHOD_COLORS[ep.method] || '#94a3b8', fontWeight: 700, fontSize: 11 }}>{ep.method}</span>
                    <code style={{ fontSize: 12, color: '#e2e8f0' }}>{ep.path}</code>
                    <code style={{ fontSize: 11, color: '#818cf8', background: 'rgba(99,102,241,0.1)', padding: '2px 6px', borderRadius: 4, height: 'fit-content' }}>{ep.scope}</code>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>{ep.desc}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, desc, children }) {
  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: '#f1f5f9', margin: '0 0 8px' }}>{title}</h2>
      <p style={{ color: '#94a3b8', fontSize: 14, marginBottom: 28, lineHeight: 1.6 }}>{desc}</p>
      {children}
    </div>
  );
}

function CodeBlock({ code }) {
  return (
    <div style={{ position: 'relative', marginBottom: 24 }}>
      <button style={{ position: 'absolute', top: 10, right: 10, background: 'rgba(255,255,255,0.08)', border: 'none', color: '#94a3b8', borderRadius: 6, padding: '4px 10px', fontSize: 11, cursor: 'pointer' }} onClick={() => navigator.clipboard.writeText(code)}>
        Copy
      </button>
      <pre style={{ background: '#0a0f1a', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10, padding: '20px', color: '#e2e8f0', fontSize: 13, lineHeight: 1.7, overflowX: 'auto', margin: 0 }}>
        {code}
      </pre>
    </div>
  );
}

const s = {
  page: { padding: '32px', maxWidth: 1200, margin: '0 auto', fontFamily: "'Inter', sans-serif" },
  header: { marginBottom: 32 },
  badge: { display: 'inline-block', background: 'rgba(99,102,241,0.15)', color: '#818cf8', padding: '4px 12px', borderRadius: 20, fontSize: 12, fontWeight: 600, marginBottom: 10 },
  title: { fontSize: 28, fontWeight: 700, color: '#f1f5f9', margin: '0 0 8px' },
  sub: { fontSize: 14, color: '#94a3b8', margin: 0 },
  layout: { display: 'grid', gridTemplateColumns: '220px 1fr', gap: 32, alignItems: 'start' },
  nav: { background: '#1e293b', borderRadius: 12, padding: '16px 8px', position: 'sticky', top: 20 },
  navItem: { display: 'block', width: '100%', textAlign: 'left', padding: '10px 14px', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600, transition: 'all 0.15s', marginBottom: 2, boxSizing: 'border-box' },
  navDivider: { height: 1, background: 'rgba(255,255,255,0.06)', margin: '8px 6px' },
  content: { background: '#1e293b', borderRadius: 12, padding: '32px', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' },
  h3: { fontSize: 15, fontWeight: 700, color: '#e2e8f0', margin: '24px 0 10px' },
  p: { fontSize: 14, color: '#94a3b8', lineHeight: 1.6, marginBottom: 16 },
  icode: { background: 'rgba(255,255,255,0.08)', padding: '1px 6px', borderRadius: 4, fontSize: 13 },
  infoGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 },
  infoCard: { background: '#0f172a', borderRadius: 10, padding: '16px 20px', border: '1px solid rgba(255,255,255,0.06)' },
  infoIcon: { fontSize: 24, marginBottom: 8 },
  infoLabel: { fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 8 },
  prefixDemo: { fontSize: 12, color: '#818cf8', background: 'rgba(99,102,241,0.1)', padding: '4px 10px', borderRadius: 6, display: 'block', marginBottom: 8 },
  infoP: { fontSize: 12, color: '#64748b', margin: 0 },
  table: { background: '#0f172a', borderRadius: 10, overflow: 'hidden', marginBottom: 24, border: '1px solid rgba(255,255,255,0.06)' },
  tableRow: { display: 'flex', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.04)' },
  tableKey: { fontSize: 13, fontWeight: 600, color: '#94a3b8' },
  tableVal: { fontSize: 13, color: '#e2e8f0' },
  evtDocRow: { display: 'flex', gap: 16, alignItems: 'flex-start', padding: '14px 0', borderBottom: '1px solid rgba(255,255,255,0.05)' },
  evtCode: { fontSize: 12, background: 'rgba(99,102,241,0.12)', color: '#818cf8', padding: '3px 10px', borderRadius: 6, whiteSpace: 'nowrap', flexShrink: 0 },
  evtTitle: { fontSize: 13, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 },
  evtDocDesc: { fontSize: 12, color: '#64748b' },
};
