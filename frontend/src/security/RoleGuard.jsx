import React from "react";
import { useRole } from "./permissionHooks";
import { normalizeRole } from "./permissionUtils";

/**
 * Conditionally renders children if the user has one of the allowed roles.
 * 
 * @param {string} props.role - Single allowed role
 * @param {string[]} props.roles - Array of allowed roles
 * @param {React.ReactNode} props.fallback - Optional element to render if role check fails
 */
export default function RoleGuard({
  role,
  roles,
  fallback = null,
  children,
}) {
  const userRole = useRole();
  const allowedRoles = roles || (role ? [role] : []);
  
  const normUserRole = normalizeRole(userRole);
  const normAllowedRoles = allowedRoles.map(r => normalizeRole(r));

  const hasAccess = normAllowedRoles.includes(normUserRole);

  if (hasAccess) {
    return <>{children}</>;
  }

  return <>{fallback}</>;
}
