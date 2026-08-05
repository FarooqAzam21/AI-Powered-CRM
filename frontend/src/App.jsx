import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AuthCallback from "./pages/AuthCallback";
import Login from "./pages/Login";
import Register from "./pages/Register";
import AccessDenied from "./pages/AccessDenied";
import { useAuth } from "./context/AuthContext";
import CRMLayout from "./crm/CRMLayout";

import { PermissionProvider } from "./security/permissionContext";
import { useRole } from "./security/permissionHooks";
import { checkPermissions } from "./security/permissionUtils";
import { PERMISSIONS } from "./security/permissions";

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

// Developer Portal Pages
const DeveloperDashboard = lazy(() => import("./pages/DeveloperDashboard"));
const APIKeys = lazy(() => import("./pages/APIKeys"));
const WebhookManager = lazy(() => import("./pages/WebhookManager"));
const Documentation = lazy(() => import("./pages/Documentation"));
const APIExplorer = lazy(() => import("./pages/APIExplorer"));
const OrganizationAdmin = lazy(() => import("./pages/OrganizationAdmin"));

// Placeholder components for recruiter routes
function Hiring() {
  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Hiring Portal</h2>
        <p className="text-sm text-slate-400">Manage open roles, job descriptions, and recruitment pipelines.</p>
      </div>
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
        <p className="text-sm text-slate-400">Open Positions</p>
        <p className="text-lg font-medium mt-1">4 Active Roles</p>
      </div>
    </section>
  );
}

function Candidates() {
  return (
    <section className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold">Candidates</h2>
        <p className="text-sm text-slate-400">Review job applicants and interview feedback.</p>
      </div>
      <div className="rounded-lg border border-white/10 bg-white/[0.03] p-5">
        <p className="text-sm text-slate-400">Total Applicants</p>
        <p className="text-lg font-medium mt-1">128 Candidates</p>
      </div>
    </section>
  );
}

function LoadingShell() {
  return <div className="min-h-screen bg-[#080b12] p-6 text-slate-300">Loading workspace...</div>;
}

function Protected({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

function RoutePermissionGuard({ permission, permissions, children }) {
  const { user } = useAuth();
  const role = useRole();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const targetPermissions = permissions || (permission ? [permission] : []);
  const hasAccess = checkPermissions(role, targetPermissions);

  if (!hasAccess) {
    return <Navigate to="/access-denied" replace />;
  }

  return children;
}

function AppContent() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/dashboard" replace />} />
      <Route path="/register" element={!user ? <Register /> : <Navigate to="/dashboard" replace />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/access-denied" element={<AccessDenied />} />
      <Route
        path="/"
        element={
          <Protected>
            <CRMLayout />
          </Protected>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route
          path="dashboard"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.DASHBOARD_VIEW}>
              <Dashboard />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="inbox"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.INBOX_VIEW}>
              <Inbox />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="contacts"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.CONTACTS_VIEW}>
              <Contacts />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="pipelines"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.PIPELINES_VIEW}>
              <Pipelines />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="deals"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.DEALS_VIEW}>
              <Deals />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="campaigns"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.CAMPAIGNS_VIEW}>
              <Campaigns />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="lead-profiles"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.CONTACTS_VIEW}>
              <LeadProfiles />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="ai-insights"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.AI_ANALYTICS}>
              <AIInsights />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="analytics"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.ANALYTICS_VIEW}>
              <Analytics />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="ai-tasks"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.AI_REPLY}>
              <AITasks />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="ai-agents"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.AI_SETTINGS}>
              <AIAgentsPage />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="settings"
          element={
            <RoutePermissionGuard
              permissions={[
                PERMISSIONS.SETTINGS_WORKSPACE,
                PERMISSIONS.SETTINGS_SECURITY,
                PERMISSIONS.SETTINGS_AUDIT_LOGS,
              ]}
            >
              <Settings />
            </RoutePermissionGuard>
          }
        />
        
        {/* Recruiter Routes */}
        <Route
          path="hiring"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.HIRING_VIEW}>
              <Hiring />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="candidates"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.CANDIDATES_VIEW}>
              <Candidates />
            </RoutePermissionGuard>
          }
        />

        {/* Developer Portal — Workspace Admin only */}
        <Route
          path="developer"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.SETTINGS_WORKSPACE}>
              <DeveloperDashboard />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="developer/keys"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.SETTINGS_WORKSPACE}>
              <APIKeys />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="developer/webhooks"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.SETTINGS_WORKSPACE}>
              <WebhookManager />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="developer/explorer"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.SETTINGS_WORKSPACE}>
              <APIExplorer />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="developer/docs"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.SETTINGS_WORKSPACE}>
              <Documentation />
            </RoutePermissionGuard>
          }
        />
        <Route
          path="organization"
          element={
            <RoutePermissionGuard permission={PERMISSIONS.SETTINGS_WORKSPACE}>
              <OrganizationAdmin />
            </RoutePermissionGuard>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingShell />}>
        <PermissionProvider>
          <AppContent />
        </PermissionProvider>
      </Suspense>
    </BrowserRouter>
  );
}
