import React, { createContext, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import { ROLE_PERMISSIONS } from "./permissionMap";
import { normalizeRole, hasPermission } from "./permissionUtils";

export const PermissionContext = createContext(null);

export const PermissionProvider = ({ children }) => {
  const { user } = useAuth();

  const securityState = useMemo(() => {
    if (!user) {
      return {
        role: null,
        permissions: [],
        workspace: null,
        organization: null,
        userId: null,
        can: () => false,
      };
    }

    const role = user.role;
    const normalized = normalizeRole(role);
    const permissions = ROLE_PERMISSIONS[normalized] || [];
    
    // Support database or implicit fallback values
    const workspace = {
      id: user.workspace_id || 1,
      name: user.workspace_name || "Default Workspace",
    };
    
    const organization = {
      id: user.organization_id || 1,
      name: user.organization_name || "Enterprise Organization",
    };
    
    const userId = user.id;

    // Fast memoized checking function
    const can = (permission) => {
      return hasPermission(role, permission);
    };

    return {
      role,
      permissions,
      workspace,
      organization,
      userId,
      can,
    };
  }, [user]);

  return (
    <PermissionContext.Provider value={securityState}>
      {children}
    </PermissionContext.Provider>
  );
};
