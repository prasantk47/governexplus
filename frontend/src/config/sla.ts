/**
 * SLA Configuration for GOVERNEX+ Zero Trust Platform
 *
 * Platform-enforced SLAs with auto-escalation and auto-actions
 */

// Risk Levels
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

// SLA time units
export type TimeUnit = 'minutes' | 'hours' | 'days';

export interface SLADuration {
  value: number;
  unit: TimeUnit;
}

// ============================================
// 1. ACCESS REQUEST SLAs
// ============================================

export interface AccessRequestSLA {
  riskLevel: RiskLevel;
  approvalSLA: SLADuration;
  autoAction: 'auto_approve' | 'escalate' | 'security_review' | 'block_until_approved';
  description: string;
}

export const ACCESS_REQUEST_SLAS: AccessRequestSLA[] = [
  {
    riskLevel: 'low',
    approvalSLA: { value: 4, unit: 'hours' },
    autoAction: 'auto_approve',
    description: 'Low risk requests auto-approved after SLA',
  },
  {
    riskLevel: 'medium',
    approvalSLA: { value: 8, unit: 'hours' },
    autoAction: 'escalate',
    description: 'Medium risk escalated to next approver',
  },
  {
    riskLevel: 'high',
    approvalSLA: { value: 24, unit: 'hours' },
    autoAction: 'security_review',
    description: 'High risk requires security team review',
  },
  {
    riskLevel: 'critical',
    approvalSLA: { value: 2, unit: 'hours' },
    autoAction: 'block_until_approved',
    description: 'Critical requests blocked until explicitly approved',
  },
];

// ============================================
// 2. FIREFIGHTER / PRIVILEGED ACCESS SLAs
// ============================================

export interface FirefighterSLA {
  stage: 'approval' | 'max_session' | 'log_review' | 'missed_review';
  sla: SLADuration;
  autoAction: string;
}

export const FIREFIGHTER_SLAS: FirefighterSLA[] = [
  {
    stage: 'approval',
    sla: { value: 30, unit: 'minutes' },
    autoAction: 'Auto-escalate to security admin',
  },
  {
    stage: 'max_session',
    sla: { value: 4, unit: 'hours' },
    autoAction: 'Auto-terminate session with warning',
  },
  {
    stage: 'log_review',
    sla: { value: 24, unit: 'hours' },
    autoAction: 'Flag for compliance review',
  },
  {
    stage: 'missed_review',
    sla: { value: 48, unit: 'hours' },
    autoAction: 'Auto-alert + escalation to manager',
  },
];

export const FIREFIGHTER_SESSION_LIMITS = {
  minDuration: { value: 15, unit: 'minutes' as TimeUnit },
  maxDuration: { value: 4, unit: 'hours' as TimeUnit },
  extensionLimit: 2, // Max number of extensions allowed
  extensionDuration: { value: 1, unit: 'hours' as TimeUnit },
};

// ============================================
// 3. SOD VIOLATION SLAs
// ============================================

export interface SoDViolationSLA {
  severity: RiskLevel;
  remediationSLA: SLADuration;
  escalationAt: SLADuration;
  autoAction: string;
}

export const SOD_VIOLATION_SLAS: SoDViolationSLA[] = [
  {
    severity: 'critical',
    remediationSLA: { value: 7, unit: 'days' },
    escalationAt: { value: 3, unit: 'days' },
    autoAction: 'Escalate to CISO + block conflicting access',
  },
  {
    severity: 'high',
    remediationSLA: { value: 14, unit: 'days' },
    escalationAt: { value: 7, unit: 'days' },
    autoAction: 'Escalate to security admin',
  },
  {
    severity: 'medium',
    remediationSLA: { value: 30, unit: 'days' },
    escalationAt: { value: 14, unit: 'days' },
    autoAction: 'Notify manager + add to review queue',
  },
  {
    severity: 'low',
    remediationSLA: { value: 90, unit: 'days' },
    escalationAt: { value: 45, unit: 'days' },
    autoAction: 'Include in next certification cycle',
  },
];

// ============================================
// 4. CERTIFICATION / ACCESS REVIEW SLAs
// ============================================

export interface CertificationSLA {
  stage: 'review_window' | 'reminder' | 'escalation' | 'no_action';
  timing: SLADuration;
  action: string;
}

export const CERTIFICATION_SLAS: CertificationSLA[] = [
  {
    stage: 'review_window',
    timing: { value: 14, unit: 'days' },
    action: 'Standard review window (can extend to 30 days)',
  },
  {
    stage: 'reminder',
    timing: { value: 7, unit: 'days' },
    action: 'Send reminder notification to reviewer',
  },
  {
    stage: 'escalation',
    timing: { value: 14, unit: 'days' },
    action: 'Escalate to manager and security admin',
  },
  {
    stage: 'no_action',
    timing: { value: 21, unit: 'days' },
    action: 'Auto-revoke access with audit trail',
  },
];

export const CERTIFICATION_SETTINGS = {
  defaultReviewWindow: { value: 14, unit: 'days' as TimeUnit },
  maxReviewWindow: { value: 30, unit: 'days' as TimeUnit },
  riskBasedPrioritization: true,
  autoRevokeEnabled: true,
  requireJustification: true,
};

// ============================================
// HELPER FUNCTIONS
// ============================================

export function getSLAInHours(duration: SLADuration): number {
  switch (duration.unit) {
    case 'minutes':
      return duration.value / 60;
    case 'hours':
      return duration.value;
    case 'days':
      return duration.value * 24;
  }
}

export function getSLAInMinutes(duration: SLADuration): number {
  switch (duration.unit) {
    case 'minutes':
      return duration.value;
    case 'hours':
      return duration.value * 60;
    case 'days':
      return duration.value * 24 * 60;
  }
}

export function formatSLA(duration: SLADuration): string {
  const { value, unit } = duration;
  if (value === 1) {
    return `${value} ${unit.slice(0, -1)}`; // Remove 's' for singular
  }
  return `${value} ${unit}`;
}

export function getAccessRequestSLA(riskLevel: RiskLevel): AccessRequestSLA | undefined {
  return ACCESS_REQUEST_SLAS.find((sla) => sla.riskLevel === riskLevel);
}

export function getSoDViolationSLA(severity: RiskLevel): SoDViolationSLA | undefined {
  return SOD_VIOLATION_SLAS.find((sla) => sla.severity === severity);
}
