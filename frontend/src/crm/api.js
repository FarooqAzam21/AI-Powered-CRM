import API from "../srevices/api";

export async function getSummary() {
  const { data } = await API.get("/analytics/summary");
  return data;
}

export async function getAnalyticsEngine() {
  const { data } = await API.get("/analytics/engine");
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

export async function searchEmails(params = {}) {
  const { data } = await API.get("/email/search", { params });
  return data;
}

export async function getEmail(id, includeBody = false) {
  const { data } = await API.get(`/email/${id}`, { params: { include_body: includeBody } });
  return data;
}

export async function getEmailContext(id, includeBody = false) {
  const { data } = await API.get(`/email/context/${id}`, { params: { include_body: includeBody } });
  return data;
}

export async function getEmailBody(id) {
  const { data } = await API.get(`/email/body/${id}`);
  return data;
}

export async function classifySyncedEmail(id) {
  const { data } = await API.post(`/email/classify/${id}`);
  return data;
}

export async function manuallyClassifySyncedEmail(id, payload) {
  const { data } = await API.post(`/email/classify/${id}/manual`, payload);
  return data;
}

export async function classifySyncedEmails(payload = {}) {
  const { data } = await API.post("/email/classify", payload);
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

// Phase 5 — AI
export async function getAIHealth() {
  const { data } = await API.get("/api/v1/ai/health");
  return data;
}

export async function getAIStats() {
  const { data } = await API.get("/api/v1/ai/stats");
  return data;
}

export async function classifyEmail(payload) {
  const { data } = await API.post("/api/v1/ai/classify-email", payload);
  return data;
}

export async function generateReply(payload) {
  const { data } = await API.post("/api/v1/ai/generate-reply", payload);
  return data;
}

export async function getReplyQuota() {
  const { data } = await API.get("/api/v1/ai/reply-quota");
  return data;
}

export async function sendEmailReply(payload) {
  const { data } = await API.post("/email/send-reply", payload);
  return data;
}

export async function getCeleryHealth() {
  const { data } = await API.get("/tasks/health");
  return data;
}

export async function getTaskStatus(taskId) {
  const { data } = await API.get(`/tasks/status/${taskId}`);
  return data;
}

export async function triggerGmailSync() {
  const { data } = await API.post("/tasks/sync-gmail");
  return data;
}

// Phase 6 — Deals
export async function getDeals(params = {}) {
  const { data } = await API.get("/api/v1/deals/", { params });
  return data;
}

export async function createDeal(payload) {
  const { data } = await API.post("/api/v1/deals/", payload);
  return data;
}

export async function updateDeal(id, payload) {
  const { data } = await API.put(`/api/v1/deals/${id}`, payload);
  return data;
}

export async function closeDeal(id, won = true, reason = null) {
  const { data } = await API.post(`/api/v1/deals/${id}/close`, null, { params: { won, ...(reason ? { reason } : {}) } });
  return data;
}

export async function getDealPipelineSummary() {
  const { data } = await API.get("/api/v1/deals/pipeline/summary");
  return data;
}

export async function getRecommendations(limit = 10) {
  const { data } = await API.get("/api/v1/recommendations", { params: { limit } });
  return data;
}

export async function actionRecommendation(id) {
  const { data } = await API.post(`/api/v1/recommendations/${id}/action`);
  return data;
}

// Phase 7 — Advanced analytics
export async function getWinLossSummary(days = 90) {
  const { data } = await API.get("/api/v1/analytics/win-loss-summary", { params: { days } });
  return data;
}

export async function getSalesVelocity() {
  const { data } = await API.get("/api/v1/analytics/velocity");
  return data;
}

export async function getBottlenecks() {
  const { data } = await API.get("/api/v1/analytics/bottlenecks");
  return data;
}

export async function getForecastAccuracy() {
  const { data } = await API.get("/api/v1/analytics/forecast-accuracy");
  return data;
}

export async function getTerritories() {
  const { data } = await API.get("/api/v1/analytics/territories");
  return data;
}

export async function getOptimizationRecommendations() {
  const { data } = await API.get("/api/v1/analytics/optimization-recommendations");
  return data;
}

// Phase 8 — WebSocket metrics
export async function getWsDashboardMetrics() {
  const { data } = await API.get("/api/v1/ws/metrics/dashboard");
  return data;
}

export async function getWsPipelineSnapshot() {
  const { data } = await API.get("/api/v1/ws/metrics/pipeline");
  return data;
}

export async function getWsConnections() {
  const { data } = await API.get("/api/v1/ws/connections");
  return data;
}

// Phase P3 — Enterprise Billing & Subscriptions
export async function getBillingPlans() {
  const { data } = await API.get("/api/v1/billing/plans");
  return data;
}

export async function getBillingSubscription() {
  const { data } = await API.get("/api/v1/billing/subscription");
  return data;
}

export async function getBillingUsage() {
  const { data } = await API.get("/api/v1/billing/usage");
  return data;
}

export async function getBillingFeatures() {
  const { data } = await API.get("/api/v1/billing/features");
  return data;
}

export async function subscribePlan(payload) {
  const { data } = await API.post("/api/v1/billing/subscribe", payload);
  return data;
}

export async function cancelSubscription() {
  const { data } = await API.post("/api/v1/billing/cancel");
  return data;
}

export async function startBillingTrial(payload) {
  const { data } = await API.post("/api/v1/billing/trial/start", payload);
  return data;
}

export async function getBillingHistory() {
  const { data } = await API.get("/api/v1/billing/history");
  return data;
}

export async function createBillingCheckout(payload) {
  const { data } = await API.post("/api/v1/billing/checkout", payload);
  return data;
}

// Phase P4 — Enterprise AI Copilot & Knowledge RAG
export async function getCopilotStatus() {
  const { data } = await API.get("/api/v1/copilot/status");
  return data;
}

export async function listCopilotConversations(params = {}) {
  const { data } = await API.get("/api/v1/copilot/conversations", { params });
  return data;
}

export async function createCopilotConversation(payload = {}) {
  const { data } = await API.post("/api/v1/copilot/conversations", payload);
  return data;
}

export async function getCopilotConversation(conversationId) {
  const { data } = await API.get(`/api/v1/copilot/conversations/${conversationId}`);
  return data;
}

export async function deleteCopilotConversation(conversationId) {
  const { data } = await API.delete(`/api/v1/copilot/conversations/${conversationId}`);
  return data;
}

export async function sendCopilotMessage(payload) {
  const { data } = await API.post("/api/v1/copilot/chat", payload);
  return data;
}

export async function confirmCopilotAction(payload) {
  const { data } = await API.post("/api/v1/copilot/actions/confirm", payload);
  return data;
}

export async function rejectCopilotAction(payload) {
  const { data } = await API.post("/api/v1/copilot/actions/reject", payload);
  return data;
}

export async function indexKnowledgeBase(payload) {
  const { data } = await API.post("/api/v1/copilot/rag/index", payload);
  return data;
}

export async function searchKnowledgeBase(query) {
  const { data } = await API.get("/api/v1/copilot/rag/search", { params: { q: query } });
  return data;
}


// ── P5: Workflow Automation API ────────────────────────────────────────────

export async function listWorkflows(params = {}) {
  const { data } = await API.get("/api/v1/workflows/", { params });
  return data;
}

export async function createWorkflow(payload) {
  const { data } = await API.post("/api/v1/workflows/", payload);
  return data;
}

export async function getWorkflow(id) {
  const { data } = await API.get(`/api/v1/workflows/${id}`);
  return data;
}

export async function updateWorkflow(id, payload) {
  const { data } = await API.put(`/api/v1/workflows/${id}`, payload);
  return data;
}

export async function deleteWorkflow(id) {
  await API.delete(`/api/v1/workflows/${id}`);
}

export async function enableWorkflow(id) {
  const { data } = await API.post(`/api/v1/workflows/${id}/enable`);
  return data;
}

export async function disableWorkflow(id) {
  const { data } = await API.post(`/api/v1/workflows/${id}/disable`);
  return data;
}

export async function validateWorkflow(id) {
  const { data } = await API.post(`/api/v1/workflows/${id}/validate`);
  return data;
}

export async function testWorkflow(id, testData = {}) {
  const { data } = await API.post(`/api/v1/workflows/${id}/test`, testData);
  return data;
}

export async function listWorkflowExecutions(workflowId, params = {}) {
  const { data } = await API.get(`/api/v1/workflows/${workflowId}/executions`, { params });
  return data;
}

export async function getWorkflowExecution(execId) {
  const { data } = await API.get(`/api/v1/workflows/executions/${execId}`);
  return data;
}

export async function cancelWorkflowExecution(execId) {
  const { data } = await API.post(`/api/v1/workflows/executions/${execId}/cancel`);
  return data;
}

export async function listPendingApprovals() {
  const { data } = await API.get("/api/v1/workflows/approvals/pending");
  return data;
}

export async function approveAction(approvalId, notes = "") {
  const { data } = await API.post(`/api/v1/workflows/approvals/${approvalId}/approve`, { decision: "approved", notes });
  return data;
}

export async function rejectAction(approvalId, notes = "") {
  const { data } = await API.post(`/api/v1/workflows/approvals/${approvalId}/reject`, { decision: "rejected", notes });
  return data;
}
