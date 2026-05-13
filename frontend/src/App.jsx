import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import AuthCallback from "./pages/AuthCallback";
import AdminDashboard from "./dashboards/AdminDashboard";
import AgentsDashboard from "./dashboards/AgentsDashboard";
import UserDashboard from "./dashboards/UserDasboard";
import { useAuth } from "./context/AuthContext";

function AppContent() {
  const { user } = useAuth();

  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
      <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      {/* Root Redirect */}
      <Route path="/" element={
        !user ? <Navigate to="/login" /> :
          user.role === "admin" ? <Navigate to="/admin" /> :
            user.role === "agent" ? <Navigate to="/agent" /> :
              <Navigate to="/dashboard" />
      } />

      {/* Protected Routes */}
      <Route path="/admin" element={user && user.role === "admin" ? <AdminDashboard /> : <Navigate to="/login" />} />
      <Route path="/agent" element={user && user.role === "agent" ? <AgentsDashboard /> : <Navigate to="/login" />} />
      <Route path="/dashboard" element={user ? <UserDashboard /> : <Navigate to="/login" />} />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
