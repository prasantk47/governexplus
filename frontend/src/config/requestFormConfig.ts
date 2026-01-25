/**
 * Request Form Configuration
 *
 * Defines the configurable fields for each access request type.
 * Admins can enable/disable fields and set required status.
 */

import { REQUEST_TYPES, RequestType } from './roles';

export type FieldType =
  | 'text'
  | 'email'
  | 'select'
  | 'multiselect'
  | 'date'
  | 'datetime'
  | 'textarea'
  | 'checkbox'
  | 'radio'
  | 'user_search'
  | 'role_search'
  | 'system_search';

export interface FieldOption {
  value: string;
  label: string;
}

export interface FormFieldConfig {
  id: string;
  name: string;
  label: string;
  type: FieldType;
  description?: string;
  placeholder?: string;
  defaultValue?: string | boolean | string[];
  options?: FieldOption[];
  validation?: {
    minLength?: number;
    maxLength?: number;
    pattern?: string;
    patternMessage?: string;
  };
  // Admin configurable
  enabled: boolean;
  required: boolean;
  order: number;
  category: 'user_info' | 'access_details' | 'justification' | 'timing' | 'other';
}

export interface RequestTypeFormConfig {
  requestType: RequestType;
  displayName: string;
  description: string;
  enabled: boolean;
  fields: FormFieldConfig[];
}

// Default field definitions for all request types
export const FIELD_DEFINITIONS: Record<string, Omit<FormFieldConfig, 'enabled' | 'required' | 'order'>> = {
  // User Information Fields
  userId: {
    id: 'userId',
    name: 'userId',
    label: 'User ID / Username',
    type: 'text',
    description: 'Unique identifier for the user account',
    placeholder: 'e.g., john.doe',
    category: 'user_info',
    validation: { minLength: 3, maxLength: 50, pattern: '^[a-zA-Z0-9._-]+$', patternMessage: 'Only letters, numbers, dots, underscores, and hyphens' },
  },
  employeeId: {
    id: 'employeeId',
    name: 'employeeId',
    label: 'Employee ID',
    type: 'text',
    description: 'HR employee identification number',
    placeholder: 'e.g., EMP001',
    category: 'user_info',
  },
  firstName: {
    id: 'firstName',
    name: 'firstName',
    label: 'First Name',
    type: 'text',
    category: 'user_info',
  },
  lastName: {
    id: 'lastName',
    name: 'lastName',
    label: 'Last Name',
    type: 'text',
    category: 'user_info',
  },
  email: {
    id: 'email',
    name: 'email',
    label: 'Email Address',
    type: 'email',
    placeholder: 'user@company.com',
    category: 'user_info',
  },
  jobTitle: {
    id: 'jobTitle',
    name: 'jobTitle',
    label: 'Job Title',
    type: 'text',
    category: 'user_info',
  },
  department: {
    id: 'department',
    name: 'department',
    label: 'Department',
    type: 'select',
    options: [
      { value: 'Finance', label: 'Finance' },
      { value: 'IT', label: 'IT' },
      { value: 'HR', label: 'Human Resources' },
      { value: 'Sales', label: 'Sales' },
      { value: 'Operations', label: 'Operations' },
      { value: 'Marketing', label: 'Marketing' },
      { value: 'Legal', label: 'Legal' },
      { value: 'Engineering', label: 'Engineering' },
      { value: 'Customer Support', label: 'Customer Support' },
    ],
    category: 'user_info',
  },
  manager: {
    id: 'manager',
    name: 'manager',
    label: 'Manager',
    type: 'user_search',
    description: 'Direct manager for approval workflow',
    placeholder: 'Search for manager...',
    category: 'user_info',
  },
  costCenter: {
    id: 'costCenter',
    name: 'costCenter',
    label: 'Cost Center',
    type: 'text',
    placeholder: 'e.g., CC1001',
    category: 'user_info',
  },
  companyCode: {
    id: 'companyCode',
    name: 'companyCode',
    label: 'Company Code',
    type: 'text',
    placeholder: 'e.g., 1000',
    category: 'user_info',
  },
  location: {
    id: 'location',
    name: 'location',
    label: 'Location / Office',
    type: 'text',
    placeholder: 'e.g., New York HQ',
    category: 'user_info',
  },
  phoneNumber: {
    id: 'phoneNumber',
    name: 'phoneNumber',
    label: 'Phone Number',
    type: 'text',
    placeholder: '+1 (555) 123-4567',
    category: 'user_info',
  },
  mobilePhone: {
    id: 'mobilePhone',
    name: 'mobilePhone',
    label: 'Mobile Phone',
    type: 'text',
    placeholder: '+1 (555) 987-6543',
    category: 'user_info',
  },
  building: {
    id: 'building',
    name: 'building',
    label: 'Building',
    type: 'text',
    placeholder: 'e.g., HQ-A',
    category: 'user_info',
  },
  room: {
    id: 'room',
    name: 'room',
    label: 'Room Number',
    type: 'text',
    placeholder: 'e.g., 305',
    category: 'user_info',
  },
  floor: {
    id: 'floor',
    name: 'floor',
    label: 'Floor',
    type: 'text',
    placeholder: 'e.g., 3',
    category: 'user_info',
  },

  // SAP Logon Tab Fields
  userType: {
    id: 'userType',
    name: 'userType',
    label: 'User Type',
    type: 'select',
    description: 'SAP user type classification',
    options: [
      { value: 'A', label: 'Dialog (A) - Interactive login' },
      { value: 'B', label: 'System (B) - Background processing' },
      { value: 'C', label: 'Communication (C) - RFC/CPIC' },
      { value: 'L', label: 'Reference (L) - License reference' },
      { value: 'S', label: 'Service (S) - Service user' },
    ],
    defaultValue: 'A',
    category: 'access_details',
  },
  userGroup: {
    id: 'userGroup',
    name: 'userGroup',
    label: 'User Group',
    type: 'select',
    description: 'SAP user group for authorization (SU01 Logon tab)',
    options: [
      { value: 'SUPER', label: 'SUPER - Super Users' },
      { value: 'USERS', label: 'USERS - Standard Users' },
      { value: 'LIMITED', label: 'LIMITED - Limited Access' },
      { value: 'DEVELOPER', label: 'DEVELOPER - Development Users' },
      { value: 'SUPPORT', label: 'SUPPORT - Support Users' },
      { value: 'BATCH', label: 'BATCH - Batch Processing' },
    ],
    category: 'access_details',
  },
  securityPolicy: {
    id: 'securityPolicy',
    name: 'securityPolicy',
    label: 'Security Policy',
    type: 'select',
    description: 'SAP password and logon security policy',
    options: [
      { value: 'DEFAULT', label: 'Default Policy' },
      { value: 'STRICT', label: 'Strict Policy' },
      { value: 'SERVICE', label: 'Service Account Policy' },
    ],
    defaultValue: 'DEFAULT',
    category: 'access_details',
  },

  // SAP Defaults Tab Fields
  logonLanguage: {
    id: 'logonLanguage',
    name: 'logonLanguage',
    label: 'Logon Language',
    type: 'select',
    description: 'Default language for SAP logon',
    options: [
      { value: 'EN', label: 'English (EN)' },
      { value: 'DE', label: 'German (DE)' },
      { value: 'ES', label: 'Spanish (ES)' },
      { value: 'FR', label: 'French (FR)' },
      { value: 'IT', label: 'Italian (IT)' },
      { value: 'JA', label: 'Japanese (JA)' },
      { value: 'ZH', label: 'Chinese (ZH)' },
      { value: 'PT', label: 'Portuguese (PT)' },
    ],
    defaultValue: 'EN',
    category: 'other',
  },
  decimalNotation: {
    id: 'decimalNotation',
    name: 'decimalNotation',
    label: 'Decimal Notation',
    type: 'select',
    description: 'Number format preference',
    options: [
      { value: 'X', label: '1,234.56 (US format)' },
      { value: '', label: '1.234,56 (European format)' },
      { value: 'Y', label: '1 234,56 (Space separator)' },
    ],
    defaultValue: 'X',
    category: 'other',
  },
  dateFormat: {
    id: 'dateFormat',
    name: 'dateFormat',
    label: 'Date Format',
    type: 'select',
    description: 'Date display format preference',
    options: [
      { value: '1', label: 'DD.MM.YYYY' },
      { value: '2', label: 'MM/DD/YYYY' },
      { value: '3', label: 'MM-DD-YYYY' },
      { value: '4', label: 'YYYY.MM.DD' },
      { value: '5', label: 'YYYY/MM/DD' },
      { value: '6', label: 'YYYY-MM-DD' },
    ],
    defaultValue: '1',
    category: 'other',
  },
  timeZone: {
    id: 'timeZone',
    name: 'timeZone',
    label: 'Time Zone',
    type: 'select',
    description: 'User time zone setting',
    options: [
      { value: 'UTC', label: 'UTC' },
      { value: 'EST', label: 'Eastern (EST)' },
      { value: 'CST', label: 'Central (CST)' },
      { value: 'MST', label: 'Mountain (MST)' },
      { value: 'PST', label: 'Pacific (PST)' },
      { value: 'CET', label: 'Central European (CET)' },
      { value: 'IST', label: 'India (IST)' },
      { value: 'JST', label: 'Japan (JST)' },
    ],
    category: 'other',
  },
  startMenu: {
    id: 'startMenu',
    name: 'startMenu',
    label: 'Start Menu / Transaction',
    type: 'text',
    description: 'Initial SAP menu or transaction code after logon',
    placeholder: 'e.g., SAP_EASY_ACCESS or ME21N',
    category: 'other',
  },
  outputDevice: {
    id: 'outputDevice',
    name: 'outputDevice',
    label: 'Output Device (Printer)',
    type: 'text',
    description: 'Default printer/spool device',
    placeholder: 'e.g., LP01',
    category: 'other',
  },

  // Access Details Fields
  targetSystems: {
    id: 'targetSystems',
    name: 'targetSystems',
    label: 'Target Systems',
    type: 'system_search',
    description: 'Systems where the account will be created/modified',
    category: 'access_details',
  },
  roles: {
    id: 'roles',
    name: 'roles',
    label: 'Roles',
    type: 'role_search',
    description: 'Roles to assign to the user',
    category: 'access_details',
  },
  sourceUser: {
    id: 'sourceUser',
    name: 'sourceUser',
    label: 'Source User (Copy From)',
    type: 'user_search',
    description: 'User whose roles will be copied',
    placeholder: 'Search for user to copy...',
    category: 'access_details',
  },
  lockReason: {
    id: 'lockReason',
    name: 'lockReason',
    label: 'Lock Reason',
    type: 'select',
    options: [
      { value: 'leave', label: 'Extended Leave' },
      { value: 'security', label: 'Security Investigation' },
      { value: 'termination_pending', label: 'Termination Pending' },
      { value: 'compliance', label: 'Compliance Requirement' },
      { value: 'other', label: 'Other' },
    ],
    category: 'access_details',
  },
  lockDuration: {
    id: 'lockDuration',
    name: 'lockDuration',
    label: 'Lock Duration',
    type: 'select',
    options: [
      { value: '', label: 'Indefinite (until unlocked)' },
      { value: '7', label: '7 days' },
      { value: '14', label: '14 days' },
      { value: '30', label: '30 days' },
      { value: '90', label: '90 days' },
    ],
    category: 'access_details',
  },
  removeAction: {
    id: 'removeAction',
    name: 'removeAction',
    label: 'Removal Action',
    type: 'radio',
    options: [
      { value: 'lock', label: 'Lock Account' },
      { value: 'disable', label: 'Disable Account' },
      { value: 'delete', label: 'Delete Account (Permanent)' },
    ],
    defaultValue: 'lock',
    category: 'access_details',
  },
  accessLevel: {
    id: 'accessLevel',
    name: 'accessLevel',
    label: 'Access Level',
    type: 'select',
    options: [
      { value: 'read', label: 'Read Only' },
      { value: 'write', label: 'Read/Write' },
      { value: 'admin', label: 'Administrator' },
    ],
    category: 'access_details',
  },

  // Justification Fields
  justification: {
    id: 'justification',
    name: 'justification',
    label: 'Business Justification',
    type: 'textarea',
    description: 'Explain the business need for this request',
    placeholder: 'Provide a detailed business justification...',
    validation: { minLength: 20, maxLength: 2000 },
    category: 'justification',
  },
  projectCode: {
    id: 'projectCode',
    name: 'projectCode',
    label: 'Project Code',
    type: 'text',
    description: 'Associated project or initiative',
    placeholder: 'e.g., PRJ-2024-001',
    category: 'justification',
  },
  ticketNumber: {
    id: 'ticketNumber',
    name: 'ticketNumber',
    label: 'Ticket / Request Number',
    type: 'text',
    description: 'Related service desk or change ticket',
    placeholder: 'e.g., INC123456',
    category: 'justification',
  },
  sponsorApproval: {
    id: 'sponsorApproval',
    name: 'sponsorApproval',
    label: 'Sponsor Pre-Approval',
    type: 'checkbox',
    description: 'Has this been pre-approved by a business sponsor?',
    category: 'justification',
  },

  // Timing Fields
  isTemporary: {
    id: 'isTemporary',
    name: 'isTemporary',
    label: 'Temporary Access',
    type: 'checkbox',
    description: 'Is this a time-limited access request?',
    category: 'timing',
  },
  startDate: {
    id: 'startDate',
    name: 'startDate',
    label: 'Start Date',
    type: 'date',
    category: 'timing',
  },
  endDate: {
    id: 'endDate',
    name: 'endDate',
    label: 'End Date',
    type: 'date',
    category: 'timing',
  },
  effectiveDate: {
    id: 'effectiveDate',
    name: 'effectiveDate',
    label: 'Effective Date',
    type: 'date',
    description: 'When should this change take effect?',
    category: 'timing',
  },

  // Other Fields
  notifyUser: {
    id: 'notifyUser',
    name: 'notifyUser',
    label: 'Notify User',
    type: 'checkbox',
    description: 'Send email notification to the user',
    defaultValue: true,
    category: 'other',
  },
  additionalNotes: {
    id: 'additionalNotes',
    name: 'additionalNotes',
    label: 'Additional Notes',
    type: 'textarea',
    placeholder: 'Any additional information...',
    category: 'other',
  },
  attachments: {
    id: 'attachments',
    name: 'attachments',
    label: 'Attachments',
    type: 'text', // Would be file upload in real implementation
    description: 'Supporting documents (approval emails, etc.)',
    category: 'other',
  },
};

// Default configuration for each request type
export const DEFAULT_REQUEST_FORM_CONFIGS: RequestTypeFormConfig[] = [
  {
    requestType: REQUEST_TYPES.NEW_ACCOUNT,
    displayName: 'New Account',
    description: 'Create a new user account with initial roles',
    enabled: true,
    fields: [
      // User Information (Address Tab)
      { ...FIELD_DEFINITIONS.userId, enabled: true, required: true, order: 1 },
      { ...FIELD_DEFINITIONS.firstName, enabled: true, required: true, order: 2 },
      { ...FIELD_DEFINITIONS.lastName, enabled: true, required: true, order: 3 },
      { ...FIELD_DEFINITIONS.email, enabled: true, required: true, order: 4 },
      { ...FIELD_DEFINITIONS.employeeId, enabled: true, required: false, order: 5 },
      { ...FIELD_DEFINITIONS.jobTitle, enabled: true, required: false, order: 6 },
      { ...FIELD_DEFINITIONS.department, enabled: true, required: true, order: 7 },
      { ...FIELD_DEFINITIONS.manager, enabled: true, required: true, order: 8 },
      { ...FIELD_DEFINITIONS.costCenter, enabled: true, required: false, order: 9 },
      { ...FIELD_DEFINITIONS.companyCode, enabled: true, required: false, order: 10 },
      { ...FIELD_DEFINITIONS.location, enabled: true, required: false, order: 11 },
      { ...FIELD_DEFINITIONS.phoneNumber, enabled: false, required: false, order: 12 },
      { ...FIELD_DEFINITIONS.mobilePhone, enabled: false, required: false, order: 13 },
      { ...FIELD_DEFINITIONS.building, enabled: false, required: false, order: 14 },
      { ...FIELD_DEFINITIONS.room, enabled: false, required: false, order: 15 },
      { ...FIELD_DEFINITIONS.floor, enabled: false, required: false, order: 16 },
      // SAP Logon Tab Fields
      { ...FIELD_DEFINITIONS.userType, enabled: true, required: false, order: 17 },
      { ...FIELD_DEFINITIONS.userGroup, enabled: true, required: false, order: 18 },
      { ...FIELD_DEFINITIONS.securityPolicy, enabled: false, required: false, order: 19 },
      // SAP Defaults Tab Fields
      { ...FIELD_DEFINITIONS.logonLanguage, enabled: true, required: false, order: 20 },
      { ...FIELD_DEFINITIONS.decimalNotation, enabled: false, required: false, order: 21 },
      { ...FIELD_DEFINITIONS.dateFormat, enabled: false, required: false, order: 22 },
      { ...FIELD_DEFINITIONS.timeZone, enabled: false, required: false, order: 23 },
      { ...FIELD_DEFINITIONS.startMenu, enabled: false, required: false, order: 24 },
      { ...FIELD_DEFINITIONS.outputDevice, enabled: false, required: false, order: 25 },
      // Access Details
      { ...FIELD_DEFINITIONS.targetSystems, enabled: true, required: true, order: 26 },
      { ...FIELD_DEFINITIONS.roles, enabled: true, required: true, order: 27 },
      // Justification
      { ...FIELD_DEFINITIONS.justification, enabled: true, required: true, order: 28 },
      { ...FIELD_DEFINITIONS.projectCode, enabled: false, required: false, order: 29 },
      { ...FIELD_DEFINITIONS.ticketNumber, enabled: false, required: false, order: 30 },
      // Timing
      { ...FIELD_DEFINITIONS.isTemporary, enabled: true, required: false, order: 31 },
      { ...FIELD_DEFINITIONS.startDate, enabled: true, required: false, order: 32 },
      { ...FIELD_DEFINITIONS.endDate, enabled: true, required: false, order: 33 },
      // Other
      { ...FIELD_DEFINITIONS.notifyUser, enabled: true, required: false, order: 34 },
      { ...FIELD_DEFINITIONS.additionalNotes, enabled: false, required: false, order: 35 },
    ],
  },
  {
    requestType: REQUEST_TYPES.CHANGE_ACCOUNT,
    displayName: 'Change Account',
    description: 'Modify roles on an existing account',
    enabled: true,
    fields: [
      { ...FIELD_DEFINITIONS.roles, enabled: true, required: true, order: 1 },
      { ...FIELD_DEFINITIONS.justification, enabled: true, required: true, order: 2 },
      { ...FIELD_DEFINITIONS.projectCode, enabled: false, required: false, order: 3 },
      { ...FIELD_DEFINITIONS.ticketNumber, enabled: false, required: false, order: 4 },
      { ...FIELD_DEFINITIONS.isTemporary, enabled: true, required: false, order: 5 },
      { ...FIELD_DEFINITIONS.startDate, enabled: true, required: false, order: 6 },
      { ...FIELD_DEFINITIONS.endDate, enabled: true, required: false, order: 7 },
      { ...FIELD_DEFINITIONS.effectiveDate, enabled: false, required: false, order: 8 },
      { ...FIELD_DEFINITIONS.additionalNotes, enabled: false, required: false, order: 9 },
    ],
  },
  {
    requestType: REQUEST_TYPES.COPY_USER,
    displayName: 'Copy User',
    description: 'Create account by copying roles from another user',
    enabled: true,
    fields: [
      { ...FIELD_DEFINITIONS.userId, enabled: true, required: true, order: 1 },
      { ...FIELD_DEFINITIONS.firstName, enabled: true, required: true, order: 2 },
      { ...FIELD_DEFINITIONS.lastName, enabled: true, required: true, order: 3 },
      { ...FIELD_DEFINITIONS.email, enabled: true, required: true, order: 4 },
      { ...FIELD_DEFINITIONS.employeeId, enabled: true, required: false, order: 5 },
      { ...FIELD_DEFINITIONS.jobTitle, enabled: true, required: false, order: 6 },
      { ...FIELD_DEFINITIONS.department, enabled: true, required: true, order: 7 },
      { ...FIELD_DEFINITIONS.manager, enabled: true, required: true, order: 8 },
      { ...FIELD_DEFINITIONS.costCenter, enabled: false, required: false, order: 9 },
      { ...FIELD_DEFINITIONS.companyCode, enabled: false, required: false, order: 10 },
      { ...FIELD_DEFINITIONS.location, enabled: false, required: false, order: 11 },
      { ...FIELD_DEFINITIONS.sourceUser, enabled: true, required: true, order: 12 },
      { ...FIELD_DEFINITIONS.targetSystems, enabled: true, required: true, order: 13 },
      { ...FIELD_DEFINITIONS.justification, enabled: true, required: true, order: 14 },
      { ...FIELD_DEFINITIONS.additionalNotes, enabled: false, required: false, order: 15 },
    ],
  },
  {
    requestType: REQUEST_TYPES.REMOVE_ACCOUNT,
    displayName: 'Remove Account',
    description: 'Delete or deactivate a user account',
    enabled: true,
    fields: [
      { ...FIELD_DEFINITIONS.targetSystems, enabled: true, required: true, order: 1 },
      { ...FIELD_DEFINITIONS.removeAction, enabled: true, required: true, order: 2 },
      { ...FIELD_DEFINITIONS.justification, enabled: true, required: true, order: 3 },
      { ...FIELD_DEFINITIONS.ticketNumber, enabled: false, required: false, order: 4 },
      { ...FIELD_DEFINITIONS.effectiveDate, enabled: true, required: false, order: 5 },
      { ...FIELD_DEFINITIONS.notifyUser, enabled: true, required: false, order: 6 },
      { ...FIELD_DEFINITIONS.additionalNotes, enabled: false, required: false, order: 7 },
    ],
  },
  {
    requestType: REQUEST_TYPES.LOCK_ACCOUNT,
    displayName: 'Lock Account',
    description: 'Temporarily lock a user account',
    enabled: true,
    fields: [
      { ...FIELD_DEFINITIONS.targetSystems, enabled: true, required: true, order: 1 },
      { ...FIELD_DEFINITIONS.lockReason, enabled: true, required: true, order: 2 },
      { ...FIELD_DEFINITIONS.lockDuration, enabled: true, required: false, order: 3 },
      { ...FIELD_DEFINITIONS.justification, enabled: true, required: true, order: 4 },
      { ...FIELD_DEFINITIONS.ticketNumber, enabled: false, required: false, order: 5 },
      { ...FIELD_DEFINITIONS.notifyUser, enabled: true, required: false, order: 6 },
      { ...FIELD_DEFINITIONS.additionalNotes, enabled: false, required: false, order: 7 },
    ],
  },
  {
    requestType: REQUEST_TYPES.UNLOCK_ACCOUNT,
    displayName: 'Unlock Account',
    description: 'Re-enable a locked user account',
    enabled: true,
    fields: [
      { ...FIELD_DEFINITIONS.targetSystems, enabled: true, required: true, order: 1 },
      { ...FIELD_DEFINITIONS.justification, enabled: true, required: true, order: 2 },
      { ...FIELD_DEFINITIONS.ticketNumber, enabled: false, required: false, order: 3 },
      { ...FIELD_DEFINITIONS.notifyUser, enabled: true, required: false, order: 6 },
      { ...FIELD_DEFINITIONS.additionalNotes, enabled: false, required: false, order: 4 },
    ],
  },
];

// Helper to get config for a specific request type
export function getRequestFormConfig(requestType: RequestType): RequestTypeFormConfig | undefined {
  return DEFAULT_REQUEST_FORM_CONFIGS.find((c) => c.requestType === requestType);
}

// Helper to get enabled fields for a request type
export function getEnabledFields(requestType: RequestType): FormFieldConfig[] {
  const config = getRequestFormConfig(requestType);
  if (!config) return [];
  return config.fields.filter((f) => f.enabled).sort((a, b) => a.order - b.order);
}

// Helper to get required fields for a request type
export function getRequiredFields(requestType: RequestType): FormFieldConfig[] {
  const config = getRequestFormConfig(requestType);
  if (!config) return [];
  return config.fields.filter((f) => f.enabled && f.required).sort((a, b) => a.order - b.order);
}

// Category labels for grouping fields
export const FIELD_CATEGORIES = {
  user_info: { label: 'User Information', description: 'Basic user profile fields' },
  access_details: { label: 'Access Details', description: 'System and role configuration' },
  justification: { label: 'Justification', description: 'Business reason and approvals' },
  timing: { label: 'Timing', description: 'Validity dates and duration' },
  other: { label: 'Other', description: 'Additional options and notes' },
};
