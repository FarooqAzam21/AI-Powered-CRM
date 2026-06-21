import { useState } from "react";

import { getContacts, getContactProfile, refreshContactProfile } from "./api";
import useApiResource from "./useApiResource";

export default function LeadProfiles() {
  const { data: contacts, loading } = useApiResource(() => getContacts({ limit: 30 }), []);
  const [selectedId, setSelectedId] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [error, setError] = useState("");

  async function loadProfile(contactId) {
    setSelectedId(contactId);
    setLoadingProfile(true);
    setError("");
    try {
      setProfile(await getContactProfile(contactId));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load profile.");
      setProfile(null);
    } finally {
      setLoadingProfile(false);
    }
  }

  async function regenerate() {
    if (!selectedId) return;
    setLoadingProfile(true);
    try {
      setProfile(await refreshContactProfile(selectedId));
    } catch (err) {
      setError(err.response?.data?.detail || "Profile refresh failed.");
    } finally {
      setLoadingProfile(false);
    }
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[320px_1fr]">
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
        <h2 className="mb-4 text-xl font-semibold">Lead Profiles</h2>
        {loading ? (
          <p className="text-sm text-slate-400">Loading contacts...</p>
        ) : (
          <div className="space-y-2">
            {(contacts || []).map((contact) => (
              <button
                key={contact.id}
                onClick={() => loadProfile(contact.id)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                  selectedId === contact.id ? "bg-cyan-400/15 text-cyan-100" : "bg-black/20 text-slate-300 hover:bg-white/5"
                }`}
              >
                <p className="font-medium">{contact.name || contact.email}</p>
                <p className="text-xs text-slate-400">{contact.email}</p>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">AI Customer Profile</h2>
          {selectedId && (
            <button onClick={regenerate} disabled={loadingProfile} className="rounded-md bg-cyan-400 px-3 py-1.5 text-xs font-medium text-slate-950 disabled:opacity-50">
              Regenerate
            </button>
          )}
        </div>
        {error && <p className="mb-3 text-sm text-amber-200">{error}</p>}
        {!selectedId ? (
          <p className="text-sm text-slate-400">Select a contact to view their AI-generated profile.</p>
        ) : loadingProfile ? (
          <p className="text-sm text-slate-400">Generating profile...</p>
        ) : profile ? (
          <div className="space-y-4 text-sm">
            <Block title="Summary" value={profile.summary} />
            <Block title="Buyer Persona" value={profile.buyer_persona} />
            <Block title="Communication Style" value={profile.communication_style} />
            <Block title="Engagement Level" value={profile.engagement_level} />
            <Block title="Industry" value={profile.company_industry} />
          </div>
        ) : (
          <p className="text-sm text-slate-400">No profile available.</p>
        )}
      </div>
    </section>
  );
}

function Block({ title, value }) {
  return (
    <div className="rounded-md bg-black/20 p-3">
      <p className="mb-1 text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="text-slate-200">{value || "—"}</p>
    </div>
  );
}
