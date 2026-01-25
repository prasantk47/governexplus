/**
 * RACI Matrix Configuration for GOVERNEX+ Zero Trust Platform
 *
 * R = Responsible (Does the work)
 * A = Accountable (Final decision maker)
 * C = Consulted (Provides input)
 * I = Informed (Kept in the loop)
 *
 * Key difference from SAP GRC:
 * - Platform takes over risk + evidence generation
 * - Fewer human dependencies
 * - Faster, cleaner ownership
 */

export type RACIRole = 'R' | 'A' | 'C' | 'I' | '-';

export interface RACIEntry {
  activity: string;
  endUser: RACIRole;
  manager: RACIRole;
  roleOwner: RACIRole;
  platform: RACIRole;
  securityAdmin: RACIRole;
  auditor: RACIRole;
}

// ============================================
// 1. ACCESS REQUEST WORKFLOW
// ============================================

export const ACCESS_REQUEST_RACI: RACIEntry[] = [
  {
    activity: 'Submit access request',
    endUser: 'R',
    manager: 'I',
    roleOwner: 'I',
    platform: 'I',
    securityAdmin: 'I',
    auditor: 'I',
  },
  {
    activity: 'Risk evaluation (real-time)',
    endUser: 'I',
    manager: 'I',
    roleOwner: 'I',
    platform: 'A',
    securityAdmin: 'I',
    auditor: 'I',
  },
  {
    activity: 'Business approval',
    endUser: 'I',
    manager: 'A',
    roleOwner: 'C',
    platform: 'I',
    securityAdmin: 'I',
    auditor: 'I',
  },
  {
    activity: 'Role validation',
    endUser: 'I',
    manager: 'C',
    roleOwner: 'A',
    platform: 'I',
    securityAdmin: 'I',
    auditor: 'I',
  },
  {
    activity: 'Provisioning',
    endUser: 'I',
    manager: 'I',
    roleOwner: 'I',
    platform: 'A',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Evidence generation',
    endUser: 'I',
    manager: 'I',
    roleOwner: 'I',
    platform: 'A',
    securityAdmin: 'I',
    auditor: 'I',
  },
];

// ============================================
// 2. SOD & RISK MANAGEMENT
// ============================================

export const SOD_RISK_RACI: RACIEntry[] = [
  {
    activity: 'SoD rule execution',
    endUser: '-',
    manager: '-',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Contextual risk scoring',
    endUser: '-',
    manager: '-',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Auto-mitigation suggestion',
    endUser: '-',
    manager: '-',
    roleOwner: '-',
    platform: 'R',
    securityAdmin: 'A',
    auditor: 'I',
  },
  {
    activity: 'Continuous risk monitoring',
    endUser: '-',
    manager: '-',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Control effectiveness proof',
    endUser: '-',
    manager: '-',
    roleOwner: '-',
    platform: 'R',
    securityAdmin: 'C',
    auditor: 'A',
  },
];

// ============================================
// 3. FIREFIGHTER / PRIVILEGED ACCESS
// ============================================

export const FIREFIGHTER_RACI: RACIEntry[] = [
  {
    activity: 'Request privileged access',
    endUser: 'R',
    manager: 'I',
    roleOwner: '-',
    platform: 'I',
    securityAdmin: 'I',
    auditor: 'I',
  },
  {
    activity: 'Risk evaluation',
    endUser: 'I',
    manager: '-',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Approval',
    endUser: 'I',
    manager: 'A',
    roleOwner: '-',
    platform: 'I',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Live session control',
    endUser: 'I',
    manager: '-',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: 'C',
    auditor: 'I',
  },
  {
    activity: 'Auto-revoke',
    endUser: 'I',
    manager: '-',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: 'I',
    auditor: 'I',
  },
  {
    activity: 'Review & evidence',
    endUser: 'I',
    manager: '-',
    roleOwner: '-',
    platform: 'R',
    securityAdmin: 'C',
    auditor: 'A',
  },
];

// ============================================
// 4. ACCESS REVIEWS / CERTIFICATIONS
// ============================================

export const CERTIFICATION_RACI: RACIEntry[] = [
  {
    activity: 'Continuous review trigger',
    endUser: '-',
    manager: 'I',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: '-',
    auditor: 'I',
  },
  {
    activity: 'Risk-prioritized review',
    endUser: '-',
    manager: 'A',
    roleOwner: '-',
    platform: 'R',
    securityAdmin: '-',
    auditor: 'I',
  },
  {
    activity: 'Auto-escalation',
    endUser: '-',
    manager: 'I',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: '-',
    auditor: 'I',
  },
  {
    activity: 'Auto-revoke on ignore',
    endUser: '-',
    manager: 'I',
    roleOwner: '-',
    platform: 'A',
    securityAdmin: '-',
    auditor: 'I',
  },
  {
    activity: 'Audit assurance',
    endUser: '-',
    manager: 'I',
    roleOwner: '-',
    platform: 'R',
    securityAdmin: '-',
    auditor: 'A',
  },
];

// ============================================
// WORKFLOW STAGES
// ============================================

export type WorkflowStatus =
  | 'pending'
  | 'in_progress'
  | 'approved'
  | 'rejected'
  | 'escalated'
  | 'auto_approved'
  | 'auto_revoked'
  | 'completed';

export interface WorkflowStage {
  id: string;
  name: string;
  description: string;
  responsible: string;
  accountable: string;
  slaHours: number;
  autoAction: string;
}

export const ACCESS_REQUEST_WORKFLOW: WorkflowStage[] = [
  {
    id: 'submit',
    name: 'Request Submitted',
    description: 'User submits access request',
    responsible: 'End User',
    accountable: 'End User',
    slaHours: 0,
    autoAction: 'none',
  },
  {
    id: 'risk_eval',
    name: 'Risk Evaluation',
    description: 'Platform performs real-time risk assessment',
    responsible: 'Platform',
    accountable: 'Platform',
    slaHours: 0.1, // Near instant
    autoAction: 'Calculate risk score and SoD conflicts',
  },
  {
    id: 'manager_approval',
    name: 'Manager Approval',
    description: 'Business manager reviews and approves',
    responsible: 'Manager',
    accountable: 'Manager',
    slaHours: 8,
    autoAction: 'Escalate if SLA breached',
  },
  {
    id: 'role_validation',
    name: 'Role Validation',
    description: 'Role owner validates request appropriateness',
    responsible: 'Role Owner',
    accountable: 'Role Owner',
    slaHours: 4,
    autoAction: 'Skip if low risk',
  },
  {
    id: 'security_review',
    name: 'Security Review',
    description: 'Security admin reviews high-risk requests',
    responsible: 'Security Admin',
    accountable: 'Security Admin',
    slaHours: 24,
    autoAction: 'Required for high/critical risk only',
  },
  {
    id: 'provisioning',
    name: 'Provisioning',
    description: 'Platform provisions access automatically',
    responsible: 'Platform',
    accountable: 'Platform',
    slaHours: 0.5,
    autoAction: 'Auto-provision on approval',
  },
  {
    id: 'evidence',
    name: 'Evidence Generation',
    description: 'Platform generates audit evidence',
    responsible: 'Platform',
    accountable: 'Platform',
    slaHours: 0,
    autoAction: 'Auto-generate on completion',
  },
];

// ============================================
// HELPER FUNCTIONS
// ============================================

export function getRACIColor(role: RACIRole): string {
  switch (role) {
    case 'R':
      return 'bg-blue-100 text-blue-800';
    case 'A':
      return 'bg-green-100 text-green-800';
    case 'C':
      return 'bg-yellow-100 text-yellow-800';
    case 'I':
      return 'bg-gray-100 text-gray-600';
    case '-':
      return 'bg-gray-50 text-gray-400';
  }
}

export function getRACILabel(role: RACIRole): string {
  switch (role) {
    case 'R':
      return 'Responsible';
    case 'A':
      return 'Accountable';
    case 'C':
      return 'Consulted';
    case 'I':
      return 'Informed';
    case '-':
      return 'Not Involved';
  }
}

export function getWorkflowStage(stageId: string): WorkflowStage | undefined {
  return ACCESS_REQUEST_WORKFLOW.find((stage) => stage.id === stageId);
}
