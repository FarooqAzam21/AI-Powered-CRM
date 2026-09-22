import { createContext, useContext, useState, useCallback } from "react";
import API from "../srevices/api";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("user"));
    } catch {
      return null;
    }
  });

  const login = useCallback(async (email, password) => {
    try {
      const res = await API.post("/auth/login", {
        email,
        password
      });

      const userObj = {
        access_token: res.data.access_token,
        id: res.data.id,
        email: res.data.email,
        name: res.data.name,
        role: res.data.role,
        workspace_id: res.data.workspace_id,
        organization_id: res.data.organization_id,
        gmail_connected: res.data.gmail_connected,
      };

      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("refresh_token", res.data.refresh_token);
      if (res.data.workspace_id) {
        localStorage.setItem("active_workspace_id", String(res.data.workspace_id));
      }
      localStorage.setItem("user", JSON.stringify(userObj));
      setUser(userObj);
      return { success: true };
    } catch (error) {
      let message = error.response?.data?.detail || "Login failed. Please check your credentials.";
      if (message === "Invalid credentials") message = "Incorrect email or password. Please try again.";
      return { success: false, message };
    }
  }, []);

  const register = useCallback(async (name, email, password, role, workspace_name) => {
    try {
      const res = await API.post("/auth/register", {
        name,
        email,
        password,
        role,
        workspace_name,
      });

      // Backend now returns access_token on register too
      if (res.data.access_token) {
        const userObj = {
          access_token: res.data.access_token,
          id: res.data.id,
          email: res.data.email,
          name: res.data.name,
          role: res.data.role,
          workspace_id: res.data.workspace_id,
          organization_id: res.data.organization_id,
          gmail_connected: res.data.gmail_connected,
        };
        localStorage.setItem("token", res.data.access_token);
        if (res.data.refresh_token) {
          localStorage.setItem("refresh_token", res.data.refresh_token);
        }
        if (res.data.workspace_id) {
          localStorage.setItem("active_workspace_id", String(res.data.workspace_id));
        }
        localStorage.setItem("user", JSON.stringify(userObj));
        setUser(userObj);
      }

      return { success: true, message: res.data.message };
    } catch (error) {
      let message = error.response?.data?.detail || "Registration failed. User might already exist.";
      if (message === "User exists") message = "This email is already registered. Try logging in!";
      return { success: false, message };
    }
  }, []);

  const refreshWorkspaceContext = useCallback(async (workspaceId) => {
    if (!workspaceId) return;
    const token = localStorage.getItem("token");
    if (!token) return;

    localStorage.setItem("active_workspace_id", String(workspaceId));

    const cachedUser = JSON.parse(localStorage.getItem("user") || "null");
    if (cachedUser) {
      const enrichedUser = {
        ...cachedUser,
        workspace_id: workspaceId,
      };
      localStorage.setItem("user", JSON.stringify(enrichedUser));
      setUser(enrichedUser);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      await API.post("/auth/logout", { refresh_token: refreshToken });
    } catch (e) {
      console.error("Logout error", e);
    } finally {
      localStorage.clear();
      setUser(null);
    }
  }, []);

  const ssoLogin = useCallback((token) => {
    try {
      // Simple JWT Decode (Payload is part 2)
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));

      const decoded = JSON.parse(jsonPayload);

      const userObj = {
        access_token: token,
        id: decoded.id,
        email: decoded.sub,
        name: decoded.name,
        role: decoded.role,
        gmail_connected: decoded.gmail_connected ?? true,
      };

      localStorage.setItem("token", token);
      localStorage.setItem("user", JSON.stringify(userObj));
      setUser(userObj);
      return true;
    } catch (e) {
      console.error("Failed to decode SSO token", e);
      return false;
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout, ssoLogin, refreshWorkspaceContext }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
