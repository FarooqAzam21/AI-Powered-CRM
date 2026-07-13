import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AuthCallback from "./pages/AuthCallback";
import Login from "./pages/Login";
import Register from "./pages/Register";
import { useAuth } from "./context/AuthContext";
import CRMLayout from "./crm/CRMLayout";

const Dashboard = lazy(() => import("./crm/Dashboard"));
const Inbox = lazy(() => import("./crm/Inbox"));
const Contacts = lazy(() => import("./crm/Contacts"));
const Pipelines = lazy(() => import("./crm/Pipelines"));
const Deals = lazy(() => import("./crm/Deals"));
const Campaigns = lazy(() => import("./crm/Campaigns"));
const Analytics = lazy(() => import("./crm/Analytics"));
const LeadProfiles = lazy(() => import("./crm/LeadProfiles"));
const AIInsights = lazy(() => import("./crm/AIInsights"));
const AITasks = lazy(() => import("./crm/AITasks"));
const AIAgentsPage = lazy(() => import("./crm/AIAgentsPage"));
const Settings = lazy(() => import("./crm/Settings"));

function LoadingShell() {
  return <div className="min-h-screen bg-[#080b12] p-6 text-slate-300">Loading workspace...</div>;
}

function Protected({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

function AppContent() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/dashboard" replace />} />
      <Route path="/register" element={!user ? <Register /> : <Navigate to="/dashboard" replace />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        path="/"
        element={
          <Protected>
            <CRMLayout />
          </Protected>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="inbox" element={<Inbox />} />
        <Route path="contacts" element={<Contacts />} />
        <Route path="pipelines" element={<Pipelines />} />
        <Route path="deals" element={<Deals />} />
        <Route path="campaigns" element={<Campaigns />} />
        <Route path="lead-profiles" element={<LeadProfiles />} />
        <Route path="ai-insights" element={<AIInsights />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="ai-tasks" element={<AITasks />} />
        <Route path="ai-agents" element={<AIAgentsPage />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingShell />}>
        <AppContent />
      </Suspense>
    </BrowserRouter>
  );
}
