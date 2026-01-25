/**
 * Role-Based Access Control Configuration
 *
 * Roles:
 * - admin: System configuration only (no approvals, no workflow admin)
 * - security_admin: All activities except configs (workflow admin, ruleset management, forwarding)
 * - manager: Approvals and reports only (no configs, no ruleset changes)
 * - end_user: Submit requests, request for others, password self-service
 */

export type UserRole = 'admin' | 'security_admin' | 'manager' | 'end_user';

// Request types available in the system
export const REQUEST_TYPES = {
  NEW_ACCOUNT: 'new_account',
  CHANGE_ACCOUNT: 'change_account',
  COPY_USER: 'copy_user',
  REMOVE_ACCOUNT: 'remove_account',
  LOCK_ACCOUNT: 'lock_account',
  UNLOCK_ACCOUNT: 'unlock_account',
  PASSWORD_RESET: 'password_reset',
} as const;

export type RequestType = typeof REQUEST_TYPES[keyof typeof REQUEST_TYPES];

export interface Permission {
  id: string;
  name: string;
  description: string;
}

export interface RoleConfig {
  id: UserRole;
  name: string;
  description: string;
  permissions: string[];
}

// All available permissions in the system
export const PERMISSIONS = {
  // Dashboard
  VIEW_DASHBOARD: 'view_dashboard',

  // Access Requests
  VIEW_ACCESS_REQUESTS: 'view_access_requests',
  VIEW_MY_REQUESTS: 'view_my_requests',
  CREATE_ACCESS_REQUEST: 'create_access_request',
  CREATE_REQUEST_FOR_OTHERS: 'create_request_for_others',
  APPROVE_ACCESS_REQUEST: 'approve_access_request',
  FORWARD_ACCESS_REQUEST: 'forward_access_request',

  // Request Types
  REQUEST_NEW_ACCOUNT: 'request_new_account',
  REQUEST_CHANGE_ACCOUNT: 'request_change_account',
  REQUEST_COPY_USER: 'request_copy_user',
  REQUEST_REMOVE_ACCOUNT: 'request_remove_account',
  REQUEST_LOCK_ACCOUNT: 'request_lock_account',
  REQUEST_UNLOCK_ACCOUNT: 'request_unlock_account',

  // Password Self-Service
  VIEW_PASSWORD_SELF_SERVICE: 'view_password_self_service',
  CHANGE_OWN_PASSWORD: 'change_own_password',
  RESET_PASSWORD_IN_SYSTEMS: 'reset_password_in_systems',

  // Risk Management
  VIEW_RISK_DASHBOARD: 'view_risk_dashboard',
  VIEW_VIOLATIONS: 'view_violations',
  MANAGE_RISK_RULES: 'manage_risk_rules',
  REMEDIATE_VIOLATIONS: 'remediate_violations',

  // Roles Management
  VIEW_ROLES: 'view_roles',
  MANAGE_ROLES: 'manage_roles',
  DESIGN_ROLES: 'design_roles',

  // Users Management
  VIEW_USERS: 'view_users',
  MANAGE_USERS: 'manage_users',

  // Certification
  VIEW_CERTIFICATIONS: 'view_certifications',
  APPROVE_CERTIFICATIONS: 'approve_certifications',
  MANAGE_CERTIFICATION_CAMPAIGNS: 'manage_certification_campaigns',

  // Firefighter
  VIEW_FIREFIGHTER: 'view_firefighter',
  REQUEST_FIREFIGHTER: 'request_firefighter',
  APPROVE_FIREFIGHTER: 'approve_firefighter',
  MANAGE_FIREFIGHTER_IDS: 'manage_firefighter_ids',

  // Reports
  VIEW_REPORTS: 'view_reports',
  RUN_REPORTS: 'run_reports',
  EXPORT_REPORTS: 'export_reports',

  // Audit
  VIEW_AUDIT_LOG: 'view_audit_log',

  // Settings & Configuration
  VIEW_SETTINGS: 'view_settings',
  MANAGE_SYSTEM_CONFIG: 'manage_system_config',
  MANAGE_INTEGRATIONS: 'manage_integrations',
  MANAGE_NOTIFICATIONS: 'manage_notifications',

  // Workflow Administration
  ADMIN_WORKFLOWS: 'admin_workflows',
  FORWARD_WORKFLOWS: 'forward_workflows',

  // Bulk Access
  CREATE_BULK_ACCESS_REQUEST: 'create_bulk_access_request',
  MANAGE_REQUEST_TEMPLATES: 'manage_request_templates',

  // Risk Simulation
  RUN_RISK_SIMULATION: 'run_risk_simulation',

  // SoD Rule Library
  VIEW_SOD_RULES: 'view_sod_rules',
  MANAGE_SOD_RULES: 'manage_sod_rules',

  // Entitlement Intelligence
  VIEW_ENTITLEMENT_INTELLIGENCE: 'view_entitlement_intelligence',
  REVOKE_UNUSED_ACCESS: 'revoke_unused_access',

  // Compliance
  VIEW_COMPLIANCE: 'view_compliance',
  MANAGE_COMPLIANCE: 'manage_compliance',

  // Contextual Risk
  VIEW_CONTEXTUAL_RISK: 'view_contextual_risk',

  // Policy Management
  VIEW_POLICIES: 'view_policies',
  MANAGE_POLICIES: 'manage_policies',

  // Live Session Monitoring
  VIEW_LIVE_SESSIONS: 'view_live_sessions',
  TERMINATE_SESSIONS: 'terminate_sessions',
} as const;

// Role definitions with their permissions
export const ROLES: Record<UserRole, RoleConfig> = {
  admin: {
    id: 'admin',
    name: 'System Administrator',
    description: 'System configuration and setup only. Cannot approve requests or manage workflows.',
    permissions: [
      PERMISSIONS.VIEW_DASHBOARD,
      PERMISSIONS.VIEW_SETTINGS,
      PERMISSIONS.MANAGE_SYSTEM_CONFIG,
      PERMISSIONS.MANAGE_INTEGRATIONS,
      PERMISSIONS.MANAGE_NOTIFICATIONS,
      PERMISSIONS.VIEW_USERS,
      PERMISSIONS.MANAGE_USERS,
      PERMISSIONS.VIEW_ROLES,
      PERMISSIONS.MANAGE_ROLES,
      PERMISSIONS.VIEW_AUDIT_LOG,
      // New permissions for admin
      PERMISSIONS.MANAGE_REQUEST_TEMPLATES,
      PERMISSIONS.MANAGE_SOD_RULES,
      PERMISSIONS.MANAGE_COMPLIANCE,
      PERMISSIONS.MANAGE_POLICIES,
    ],
  },
  security_admin: {
    id: 'security_admin',
    name: 'Security Administrator',
    description: 'Full access to security operations, workflows, and rulesets. Cannot modify system configuration.',
    permissions: [
      PERMISSIONS.VIEW_DASHBOARD,
      PERMISSIONS.VIEW_ACCESS_REQUESTS,
      PERMISSIONS.CREATE_ACCESS_REQUEST,
      PERMISSIONS.FORWARD_ACCESS_REQUEST,
      PERMISSIONS.VIEW_RISK_DASHBOARD,
      PERMISSIONS.VIEW_VIOLATIONS,
      PERMISSIONS.MANAGE_RISK_RULES,
      PERMISSIONS.REMEDIATE_VIOLATIONS,
      PERMISSIONS.VIEW_ROLES,
      PERMISSIONS.DESIGN_ROLES,
      PERMISSIONS.VIEW_USERS,
      PERMISSIONS.VIEW_CERTIFICATIONS,
      PERMISSIONS.MANAGE_CERTIFICATION_CAMPAIGNS,
      PERMISSIONS.VIEW_FIREFIGHTER,
      PERMISSIONS.REQUEST_FIREFIGHTER,
      PERMISSIONS.MANAGE_FIREFIGHTER_IDS,
      PERMISSIONS.VIEW_REPORTS,
      PERMISSIONS.RUN_REPORTS,
      PERMISSIONS.EXPORT_REPORTS,
      PERMISSIONS.VIEW_AUDIT_LOG,
      PERMISSIONS.ADMIN_WORKFLOWS,
      PERMISSIONS.FORWARD_WORKFLOWS,
      // New permissions for security admin
      PERMISSIONS.CREATE_BULK_ACCESS_REQUEST,
      PERMISSIONS.MANAGE_REQUEST_TEMPLATES,
      PERMISSIONS.RUN_RISK_SIMULATION,
      PERMISSIONS.VIEW_SOD_RULES,
      PERMISSIONS.MANAGE_SOD_RULES,
      PERMISSIONS.VIEW_ENTITLEMENT_INTELLIGENCE,
      PERMISSIONS.REVOKE_UNUSED_ACCESS,
      PERMISSIONS.VIEW_COMPLIANCE,
      PERMISSIONS.VIEW_CONTEXTUAL_RISK,
      PERMISSIONS.VIEW_POLICIES,
      PERMISSIONS.VIEW_LIVE_SESSIONS,
      PERMISSIONS.TERMINATE_SESSIONS,
    ],
  },
  manager: {
    id: 'manager',
    name: 'Manager / Approver',
    description: 'Approval authority and reporting access. Cannot modify configurations or rulesets.',
    permissions: [
      PERMISSIONS.VIEW_DASHBOARD,
      PERMISSIONS.VIEW_ACCESS_REQUESTS,
      PERMISSIONS.CREATE_ACCESS_REQUEST,
      PERMISSIONS.APPROVE_ACCESS_REQUEST,
      PERMISSIONS.VIEW_RISK_DASHBOARD,
      PERMISSIONS.VIEW_VIOLATIONS,
      PERMISSIONS.VIEW_ROLES,
      PERMISSIONS.VIEW_USERS,
      PERMISSIONS.VIEW_CERTIFICATIONS,
      PERMISSIONS.APPROVE_CERTIFICATIONS,
      PERMISSIONS.VIEW_FIREFIGHTER,
      PERMISSIONS.REQUEST_FIREFIGHTER,
      PERMISSIONS.APPROVE_FIREFIGHTER,
      PERMISSIONS.VIEW_REPORTS,
      PERMISSIONS.RUN_REPORTS,
      PERMISSIONS.EXPORT_REPORTS,
      PERMISSIONS.VIEW_AUDIT_LOG,
      // New permissions for manager
      PERMISSIONS.CREATE_BULK_ACCESS_REQUEST,
      PERMISSIONS.RUN_RISK_SIMULATION,
      PERMISSIONS.VIEW_SOD_RULES,
      PERMISSIONS.VIEW_ENTITLEMENT_INTELLIGENCE,
      PERMISSIONS.VIEW_COMPLIANCE,
      PERMISSIONS.VIEW_CONTEXTUAL_RISK,
      PERMISSIONS.VIEW_POLICIES,
      PERMISSIONS.VIEW_LIVE_SESSIONS,
    ],
  },
  end_user: {
    id: 'end_user',
    name: 'End User',
    description: 'Submit access requests, request for others, and manage passwords via self-service.',
    permissions: [
      PERMISSIONS.VIEW_DASHBOARD,
      PERMISSIONS.VIEW_MY_REQUESTS,
      PERMISSIONS.CREATE_ACCESS_REQUEST,
      PERMISSIONS.CREATE_REQUEST_FOR_OTHERS,
      // Request types
      PERMISSIONS.REQUEST_NEW_ACCOUNT,
      PERMISSIONS.REQUEST_CHANGE_ACCOUNT,
      PERMISSIONS.REQUEST_COPY_USER,
      PERMISSIONS.REQUEST_REMOVE_ACCOUNT,
      PERMISSIONS.REQUEST_LOCK_ACCOUNT,
      PERMISSIONS.REQUEST_UNLOCK_ACCOUNT,
      // Password self-service
      PERMISSIONS.VIEW_PASSWORD_SELF_SERVICE,
      PERMISSIONS.CHANGE_OWN_PASSWORD,
      PERMISSIONS.RESET_PASSWORD_IN_SYSTEMS,
    ],
  },
};

// Helper function to check if a role has a specific permission
export function hasPermission(role: UserRole, permission: string): boolean {
  return ROLES[role]?.permissions.includes(permission) ?? false;
}

// Helper function to get all permissions for a role
export function getRolePermissions(role: UserRole): string[] {
  return ROLES[role]?.permissions ?? [];
}

// Navigation items configuration with required permissions
export interface NavItemConfig {
  name: string;
  href: string;
  permissions: string[];
  children?: NavItemConfig[];
}

export const NAV_PERMISSIONS: NavItemConfig[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    permissions: [PERMISSIONS.VIEW_DASHBOARD],
  },
  {
    name: 'Access Requests',
    href: '/access-requests',
    permissions: [PERMISSIONS.VIEW_ACCESS_REQUESTS, PERMISSIONS.VIEW_MY_REQUESTS],
    children: [
      { name: 'My Requests', href: '/access-requests', permissions: [PERMISSIONS.VIEW_MY_REQUESTS] },
      { name: 'All Requests', href: '/access-requests/all', permissions: [PERMISSIONS.VIEW_ACCESS_REQUESTS] },
      { name: 'New Request', href: '/access-requests/new', permissions: [PERMISSIONS.CREATE_ACCESS_REQUEST] },
      { name: 'Approvals', href: '/approvals', permissions: [PERMISSIONS.APPROVE_ACCESS_REQUEST, PERMISSIONS.FORWARD_ACCESS_REQUEST] },
    ],
  },
  {
    name: 'Password Self-Service',
    href: '/password',
    permissions: [PERMISSIONS.VIEW_PASSWORD_SELF_SERVICE],
    children: [
      { name: 'Change Password', href: '/password/change', permissions: [PERMISSIONS.CHANGE_OWN_PASSWORD] },
      { name: 'Reset in Systems', href: '/password/reset', permissions: [PERMISSIONS.RESET_PASSWORD_IN_SYSTEMS] },
    ],
  },
  {
    name: 'Risk Management',
    href: '/risk',
    permissions: [PERMISSIONS.VIEW_RISK_DASHBOARD],
    children: [
      { name: 'Dashboard', href: '/risk', permissions: [PERMISSIONS.VIEW_RISK_DASHBOARD] },
      { name: 'Violations', href: '/risk/violations', permissions: [PERMISSIONS.VIEW_VIOLATIONS] },
      { name: 'Rules', href: '/risk/rules', permissions: [PERMISSIONS.MANAGE_RISK_RULES] },
    ],
  },
  {
    name: 'Roles',
    href: '/roles',
    permissions: [PERMISSIONS.VIEW_ROLES],
    children: [
      { name: 'All Roles', href: '/roles', permissions: [PERMISSIONS.VIEW_ROLES] },
      { name: 'Role Designer', href: '/roles/designer', permissions: [PERMISSIONS.DESIGN_ROLES] },
    ],
  },
  {
    name: 'Users',
    href: '/users',
    permissions: [PERMISSIONS.VIEW_USERS],
  },
  {
    name: 'Certification',
    href: '/certification',
    permissions: [PERMISSIONS.VIEW_CERTIFICATIONS],
  },
  {
    name: 'Firefighter',
    href: '/firefighter',
    permissions: [PERMISSIONS.VIEW_FIREFIGHTER],
    children: [
      { name: 'Dashboard', href: '/firefighter', permissions: [PERMISSIONS.VIEW_FIREFIGHTER] },
      { name: 'Request Access', href: '/firefighter/request', permissions: [PERMISSIONS.REQUEST_FIREFIGHTER] },
      { name: 'Sessions', href: '/firefighter/sessions', permissions: [PERMISSIONS.VIEW_FIREFIGHTER] },
    ],
  },
  {
    name: 'Reports',
    href: '/reports',
    permissions: [PERMISSIONS.VIEW_REPORTS],
  },
  {
    name: 'Audit Log',
    href: '/audit',
    permissions: [PERMISSIONS.VIEW_AUDIT_LOG],
  },
  {
    name: 'Settings',
    href: '/settings',
    permissions: [PERMISSIONS.VIEW_SETTINGS, PERMISSIONS.MANAGE_SYSTEM_CONFIG],
  },
];
