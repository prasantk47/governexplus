/**
 * Request Templates Configuration for GOVERNEX+
 * Pre-defined access request templates by role/department
 */

export interface RequestTemplate {
  id: string;
  name: string;
  description: string;
  department: string;
  roles: {
    roleId: string;
    roleName: string;
    system: string;
    riskLevel: 'low' | 'medium' | 'high' | 'critical';
  }[];
  defaultJustification: string;
  isTemporary: boolean;
  defaultDurationDays?: number;
  usageCount: number;
  lastUsed?: string;
  createdBy: string;
  isPublic: boolean;
}

export const REQUEST_TEMPLATES: RequestTemplate[] = [
  {
    id: 'TPL-001',
    name: 'New Finance Analyst',
    description: 'Standard access bundle for new Finance department analysts',
    department: 'Finance',
    roles: [
      { roleId: 'FIN-001', roleName: 'AP Clerk', system: 'SAP S/4HANA', riskLevel: 'medium' },
      { roleId: 'FIN-002', roleName: 'GL Viewer', system: 'SAP S/4HANA', riskLevel: 'low' },
      { roleId: 'FIN-003', roleName: 'Report Viewer', system: 'SAP BW', riskLevel: 'low' },
    ],
    defaultJustification: 'New hire onboarding - Finance Analyst position',
    isTemporary: false,
    usageCount: 45,
    lastUsed: '2024-01-18',
    createdBy: 'System',
    isPublic: true,
  },
  {
    id: 'TPL-002',
    name: 'Procurement Specialist',
    description: 'Standard access for Procurement team members',
    department: 'Procurement',
    roles: [
      { roleId: 'PROC-001', roleName: 'Purchase Requisition Creator', system: 'SAP S/4HANA', riskLevel: 'medium' },
      { roleId: 'PROC-002', roleName: 'Vendor Master Viewer', system: 'SAP S/4HANA', riskLevel: 'low' },
      { roleId: 'PROC-003', roleName: 'Contract Viewer', system: 'SAP Ariba', riskLevel: 'low' },
    ],
    defaultJustification: 'Procurement team member access',
    isTemporary: false,
    usageCount: 32,
    lastUsed: '2024-01-17',
    createdBy: 'System',
    isPublic: true,
  },
  {
    id: 'TPL-003',
    name: 'IT Support Temporary',
    description: 'Temporary elevated access for IT support activities',
    department: 'IT',
    roles: [
      { roleId: 'IT-001', roleName: 'User Admin', system: 'Active Directory', riskLevel: 'high' },
      { roleId: 'IT-002', roleName: 'Password Reset', system: 'SAP S/4HANA', riskLevel: 'medium' },
      { roleId: 'IT-003', roleName: 'System Monitor', system: 'ServiceNow', riskLevel: 'low' },
    ],
    defaultJustification: 'IT support ticket resolution',
    isTemporary: true,
    defaultDurationDays: 7,
    usageCount: 89,
    lastUsed: '2024-01-18',
    createdBy: 'System',
    isPublic: true,
  },
  {
    id: 'TPL-004',
    name: 'HR Onboarding Specialist',
    description: 'Access for HR team handling employee onboarding',
    department: 'HR',
    roles: [
      { roleId: 'HR-001', roleName: 'Employee Master Maintainer', system: 'Workday', riskLevel: 'medium' },
      { roleId: 'HR-002', roleName: 'Benefits Admin', system: 'Workday', riskLevel: 'medium' },
      { roleId: 'HR-003', roleName: 'Position Viewer', system: 'SAP SuccessFactors', riskLevel: 'low' },
    ],
    defaultJustification: 'HR onboarding team access',
    isTemporary: false,
    usageCount: 28,
    lastUsed: '2024-01-16',
    createdBy: 'System',
    isPublic: true,
  },
  {
    id: 'TPL-005',
    name: 'External Auditor',
    description: 'Read-only access for external audit activities',
    department: 'Audit',
    roles: [
      { roleId: 'AUD-001', roleName: 'Financial Report Viewer', system: 'SAP S/4HANA', riskLevel: 'low' },
      { roleId: 'AUD-002', roleName: 'Audit Trail Viewer', system: 'GOVERNEX+', riskLevel: 'low' },
      { roleId: 'AUD-003', roleName: 'Control Evidence Viewer', system: 'GOVERNEX+', riskLevel: 'low' },
    ],
    defaultJustification: 'External audit engagement',
    isTemporary: true,
    defaultDurationDays: 30,
    usageCount: 12,
    lastUsed: '2024-01-10',
    createdBy: 'System',
    isPublic: true,
  },
  {
    id: 'TPL-006',
    name: 'Sales Operations',
    description: 'Standard access for Sales Operations team',
    department: 'Sales',
    roles: [
      { roleId: 'SALES-001', roleName: 'CRM User', system: 'Salesforce', riskLevel: 'low' },
      { roleId: 'SALES-002', roleName: 'Quote Creator', system: 'SAP CPQ', riskLevel: 'medium' },
      { roleId: 'SALES-003', roleName: 'Order Viewer', system: 'SAP S/4HANA', riskLevel: 'low' },
    ],
    defaultJustification: 'Sales operations team member',
    isTemporary: false,
    usageCount: 56,
    lastUsed: '2024-01-18',
    createdBy: 'System',
    isPublic: true,
  },
];

// Department options for filtering
export const DEPARTMENTS = [
  'Finance',
  'Procurement',
  'IT',
  'HR',
  'Audit',
  'Sales',
  'Operations',
  'Legal',
  'Compliance',
];

// Helper to get templates by department
export function getTemplatesByDepartment(department: string): RequestTemplate[] {
  return REQUEST_TEMPLATES.filter((t) => t.department === department);
}

// Helper to get public templates
export function getPublicTemplates(): RequestTemplate[] {
  return REQUEST_TEMPLATES.filter((t) => t.isPublic);
}
