import API from "../srevices/api";

export async function getSummary() {
  const { data } = await API.get("/analytics/summary");
  return data;
}

export async function startEmailSync() {
  const { data } = await API.post("/email/sync");
  return data;
}

export async function getEmails(params = {}) {
  const { data } = await API.get("/email/metadata", { params });
  return data;
}

export async function getEmailBody(id) {
  const { data } = await API.get(`/email/body/${id}`);
  return data;
}

export async function requestDraft(payload) {
  const { data } = await API.post("/email/draft", payload);
  return data;
}

export async function getContacts(params = {}) {
  const { data } = await API.get("/crm/contacts", { params });
  return data;
}

export async function getLeads() {
  const { data } = await API.get("/crm/leads");
  return data;
}

export async function getPipeline() {
  const { data } = await API.get("/crm/pipeline");
  return data;
}

export async function getActivities() {
  const { data } = await API.get("/crm/activities");
  return data;
}

export async function getCampaigns() {
  const { data } = await API.get("/campaigns");
  return data;
}

export async function createCampaign(payload) {
  const { data } = await API.post("/campaigns", payload);
  return data;
}

export async function startCampaign(id) {
  const { data } = await API.post(`/campaigns/${id}/start`);
  return data;
}

export async function getTask(id) {
  const { data } = await API.get(`/tasks/${id}`);
  return data;
}

export async function getInsights() {
  const { data } = await API.get("/crm/insights");
  return data;
}

export async function getContactProfile(contactId) {
  const { data } = await API.get(`/crm/contacts/${contactId}/profile`);
  return data;
}

export async function refreshContactProfile(contactId) {
  const { data } = await API.post(`/crm/contacts/${contactId}/profile/refresh`);
  return data;
}

export async function getContactInteractions(contactId) {
  const { data } = await API.get(`/crm/contacts/${contactId}/interactions`);
  return data;
}

// Phase 9 campaign API
export async function getCampaignsV9() {
  const { data } = await API.get("/api/v1/campaigns");
  return data;
}

export async function getCampaignAnalytics(id) {
  const { data } = await API.get(`/api/v1/campaigns/${id}/analytics`);
  return data;
}

export async function getCampaignProgress(id) {
  const { data } = await API.get(`/api/v1/campaigns/${id}/progress`);
  return data;
}

export async function getCampaignSends(id, params = {}) {
  const { data } = await API.get(`/api/v1/campaigns/${id}/sends`, { params });
  return data;
}
