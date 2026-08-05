import { useContext } from "react";
import { PermissionContext } from "./permissionContext";

export const usePermissionContext = () => {
  const context = useContext(PermissionContext);
  if (!context) {
    throw new Error("usePermissionContext must be used within a PermissionProvider");
  }
  return context;
};

export const useRole = () => {
  const { role } = usePermissionContext();
  return role;
};

export const usePermissions = () => {
  const { permissions } = usePermissionContext();
  return permissions;
};

export const useWorkspace = () => {
  const { workspace } = usePermissionContext();
  return workspace;
};

export const useCan = (permission) => {
  const { can } = usePermissionContext();
  return can(permission);
};
