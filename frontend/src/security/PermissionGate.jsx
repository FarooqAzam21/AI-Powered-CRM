import React from "react";
import { useRole } from "./permissionHooks";
import { checkPermissions } from "./permissionUtils";

/**
 * Conditionally renders children if the user satisfies the given permission requirements.
 * 
 * @param {string} props.permission - Single required permission
 * @param {string[]} props.permissions - Array of required permissions
 * @param {boolean} props.requireAll - If true, requires all permissions; if false, requires any
 * @param {React.ReactNode} props.fallback - Optional element to render if permission check fails
 */
export default function PermissionGate({
  permission,
  permissions,
  requireAll = false,
  fallback = null,
  children,
}) {
  const role = useRole();
  const targetPermissions = permissions || (permission ? [permission] : []);
  
  const hasAccess = checkPermissions(role, targetPermissions, requireAll);

  if (hasAccess) {
    return <>{children}</>;
  }

  return <>{fallback}</>;
}
