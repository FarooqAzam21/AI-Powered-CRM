import { ROLE_PERMISSIONS } from "./permissionMap";
import { ROLES } from "./roles";

/**
 * Normalizes DB/SSO role strings to standardized frontend roles
 */
export const normalizeRole = (role) => {
  if (!role) return ROLES.VIEWER;
  
  // Strip spaces, underscores, and convert to lowercase for comparison
  const lower = role.toLowerCase().replace(/_/g, "").replace(/\s+/g, "");
  
  if (lower === "superadmin") return ROLES.SUPER_ADMIN;
  if (lower === "workspaceadmin") return ROLES.WORKSPACE_ADMIN;
  if (lower === "admin") return ROLES.ADMIN;
  if (lower === "securityanalyst" || lower === "agent") return ROLES.SECURITY_ANALYST;
  if (lower === "viewer" || lower === "user") return ROLES.VIEWER;
  if (lower === "sales") return ROLES.SALES;
  if (lower === "recruiter") return ROLES.RECRUITER;
  if (lower === "marketing") return ROLES.MARKETING;
  if (lower === "support") return ROLES.SUPPORT;
  
  // If we can't find a direct mapping, check standard keys
  for (const key of Object.keys(ROLES)) {
    if (ROLES[key].toLowerCase() === role.toLowerCase()) {
      return ROLES[key];
    }
  }
  
  return role;
};

/**
 * Checks if a standardized role has a given permission
 */
export const hasPermission = (userRole, permission) => {
  const normRole = normalizeRole(userRole);
  
  // Admin-level roles bypass all frontend UI permission checks
  if (
    normRole === ROLES.SUPER_ADMIN ||
    normRole === ROLES.WORKSPACE_ADMIN ||
    normRole === ROLES.ADMIN
  ) {
    return true;
  }
  
  const permissions = ROLE_PERMISSIONS[normRole] || [];
  return permissions.includes(permission);
};

/**
 * Checks if a standardized role satisfies a list of required permissions
 */
export const checkPermissions = (userRole, requiredPermissions, requireAll = false) => {
  if (!requiredPermissions) return true;
  
  const permissionsArray = Array.isArray(requiredPermissions)
    ? requiredPermissions
    : [requiredPermissions];

  if (permissionsArray.length === 0) return true;

  if (requireAll) {
    return permissionsArray.every((perm) => hasPermission(userRole, perm));
  } else {
    return permissionsArray.some((perm) => hasPermission(userRole, perm));
  }
};
