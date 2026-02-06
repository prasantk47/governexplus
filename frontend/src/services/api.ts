/**
 * Governex+ Platform - API Service
 * Domain: governexplus.com
 *
 * Production deployments must set VITE_API_URL environment variable.
 * The localhost fallback is only available in development mode.
 */
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

// API Base URL - localhost fallback only available in development
const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;

  if (import.meta.env.DEV) {
    return 'http://localhost:9000';
  }

  // In production without VITE_API_URL, log warning and use relative path
  console.warn('VITE_API_URL not configured. Using relative API path.');
  return '/api';
};

const API_BASE_URL = getApiBaseUrl();

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add tenant ID if available
    const tenantId = localStorage.getItem('tenantId');
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - redirect to login
      localStorage.removeItem('accessToken');
      window.location.href = '/login';
    }

    if (error.response?.status === 403) {
      // Forbidden - show permission error
      console.error('Permission denied');
    }

    return Promise.reject(error);
  }
);

// ==================== Auth API ====================
export const authApi = {
  login: (credentials: { username: string; password: string }) =>
    api.post('/auth/login', credentials),

  logout: () => api.post('/auth/logout'),

  refreshToken: () => api.post('/auth/refresh'),

  getProfile: () => api.get('/auth/profile'),
};

// ==================== Access Requests API ====================
export const accessRequestApi = {
  list: (params?: { status?: string; page?: number; limit?: number }) =>
    api.get('/access-requests', { params }),

  get: (id: string) => api.get(`/access-requests/${id}`),

  create: (data: any) => api.post('/access-requests', data),

  submit: (id: string) => api.post(`/access-requests/${id}/submit`),

  approve: (id: string, stepId: string, data: any) =>
    api.post(`/access-requests/${id}/approve/${stepId}`, data),

  reject: (id: string, stepId: string, data: any) =>
    api.post(`/access-requests/${id}/reject/${stepId}`, data),

  previewRisk: (data: any) => api.post('/access-requests/preview-risk', data),

  getPendingApprovals: () => api.get('/access-requests/approvals/pending'),

  getMyRequests: () => api.get('/access-requests/my-requests'),
};

// ==================== Certification API ====================
export const certificationApi = {
  listCampaigns: (params?: any) => api.get('/certification/campaigns', { params }),

  getCampaign: (id: string) => api.get(`/certification/campaigns/${id}`),

  createCampaign: (data: any) => api.post('/certification/campaigns', data),

  getMyReviews: () => api.get('/certification/my-reviews'),

  submitDecision: (campaignId: string, itemId: string, data: any) =>
    api.post(`/certification/campaigns/${campaignId}/items/${itemId}/decision`, data),

  bulkCertify: (campaignId: string, data: any) =>
    api.post(`/certification/campaigns/${campaignId}/bulk-certify`, data),
};

// ==================== Firefighter API ====================
export const firefighterApi = {
  // Reason Codes
  getReasonCodes: () => api.get('/firefighter/reason-codes'),
  getReasonCode: (code: string) => api.get(`/firefighter/reason-codes/${code}`),

  // Firefighter IDs
  listFirefighters: () => api.get('/firefighter/firefighters'),
  getFirefighterStatus: (id: string) => api.get(`/firefighter/firefighters/${id}/status`),

  // Requests
  requestAccess: (data: any) => api.post('/firefighter/requests', data),
  listRequests: (params?: any) => api.get('/firefighter/requests', { params }),
  getRequest: (id: string) => api.get(`/firefighter/requests/${id}`),
  getPendingRequests: () => api.get('/firefighter/requests/pending'),
  approveRequest: (id: string, data?: any) =>
    api.post(`/firefighter/requests/${id}/approve`, data),
  rejectRequest: (id: string, data: any) =>
    api.post(`/firefighter/requests/${id}/reject`, data),

  // Sessions
  listSessions: (params?: any) => api.get('/firefighter/sessions', { params }),
  getActiveSessions: () => api.get('/firefighter/sessions/active'),
  getSession: (id: string) => api.get(`/firefighter/sessions/${id}`),
  getSessionCredentials: (id: string, userId: string) =>
    api.get(`/firefighter/sessions/${id}/credentials`, { params: { user_id: userId } }),
  endSession: (id: string, userId: string) =>
    api.post(`/firefighter/sessions/${id}/end`, null, { params: { user_id: userId } }),
  revokeSession: (id: string, revokedBy: string, reason: string) =>
    api.post(`/firefighter/sessions/${id}/revoke`, null, { params: { revoked_by: revokedBy, reason } }),

  // Session Extension
  extendSession: (id: string, data: { requested_by: string; extension_minutes: number; reason: string; approved_by?: string }) =>
    api.post(`/firefighter/sessions/${id}/extend`, data),

  // Activity Logging
  logActivity: (sessionId: string, data: any) =>
    api.post(`/firefighter/sessions/${sessionId}/activity`, data),
  getSessionActivities: (sessionId: string) =>
    api.get(`/firefighter/sessions/${sessionId}/activities`),

  // Controller Review
  getControllerReview: (sessionId: string) =>
    api.get(`/firefighter/sessions/${sessionId}/controller-review`),
  startControllerReview: (sessionId: string, controllerId: string) =>
    api.post(`/firefighter/sessions/${sessionId}/controller-review/start`, { controller_id: controllerId }),
  completeControllerReview: (sessionId: string, data: {
    controller_id: string;
    approved: boolean;
    findings: string[];
    comments: string;
    flagged_activities?: string[];
  }) => api.post(`/firefighter/sessions/${sessionId}/controller-review/complete`, data),

  // Legacy review (for compatibility)
  reviewSession: (id: string, data: any) =>
    api.post(`/firefighter/sessions/${id}/review`, data),
  getPendingReviews: (reviewerId: string) =>
    api.get('/firefighter/reviews/pending', { params: { reviewer_id: reviewerId } }),

  // Audit Evidence
  getAuditEvidence: (sessionId: string) =>
    api.get(`/firefighter/sessions/${sessionId}/audit-evidence`),
  exportAuditEvidence: (sessionId: string, format: 'json' | 'csv' | 'pdf_data' = 'json') =>
    api.get(`/firefighter/sessions/${sessionId}/audit-evidence/export`, {
      params: { format },
      responseType: format === 'json' ? 'json' : 'blob',
    }),
  getSessionsForAudit: (params?: { start_date?: string; end_date?: string; status?: string; firefighter_id?: string }) =>
    api.get('/firefighter/audit/sessions', { params }),

  // Statistics
  getStatistics: () => api.get('/firefighter/statistics'),
};

// ==================== Risk API ====================
export const riskApi = {
  analyzeUser: (userId: string) => api.post('/risk/analyze/user', { user_id: userId }),

  analyzeBatch: (userIds: string[]) =>
    api.post('/risk/analyze/batch', { user_ids: userIds }),

  listRules: (params?: any) => api.get('/risk/rules', { params }),

  getRule: (id: string) => api.get(`/risk/rules/${id}`),

  listViolations: (params?: any) => api.get('/risk/violations', { params }),

  simulateAccess: (data: any) => api.post('/risk/simulate/add-role', data),
};

// ==================== Users API ====================
export interface UserFilters {
  search?: string;
  status?: string;
  department?: string;
  risk_level?: string;
  user_type?: string;
  has_violations?: boolean;
  limit?: number;
  offset?: number;
}

export interface CreateUserRequest {
  user_id: string;
  username: string;
  full_name: string;
  email?: string;
  department?: string;
  title?: string;
  cost_center?: string;
  manager_user_id?: string;
  location?: string;
  user_type?: string;
  password?: string;
}

export interface UpdateUserRequest {
  username?: string;
  full_name?: string;
  email?: string;
  department?: string;
  title?: string;
  cost_center?: string;
  manager_user_id?: string;
  location?: string;
  status?: string;
  user_type?: string;
}

export interface RoleAssignmentRequest {
  role_id: string;
  valid_from?: string;
  valid_to?: string;
  justification?: string;
}

export const usersApi = {
  // List users with pagination and filters
  list: (params?: UserFilters) => api.get('/users', { params }),

  // Get user statistics
  getStats: () => api.get('/users/stats'),

  // Get departments list
  getDepartments: () => api.get('/users/departments'),

  // Get single user details
  get: (userId: string) => api.get(`/users/${userId}`),

  // Create new user
  create: (data: CreateUserRequest) => api.post('/users', data),

  // Update user
  update: (userId: string, data: UpdateUserRequest) =>
    api.put(`/users/${userId}`, data),

  // Delete user (soft delete)
  delete: (userId: string) => api.delete(`/users/${userId}`),

  // Role operations
  getRoles: (userId: string) => api.get(`/users/${userId}/roles`),

  assignRole: (userId: string, data: RoleAssignmentRequest) =>
    api.post(`/users/${userId}/roles`, data),

  revokeRole: (userId: string, roleId: string) =>
    api.delete(`/users/${userId}/roles/${roleId}`),

  // Entitlements and transactions
  getEntitlements: (userId: string) => api.get(`/users/${userId}/entitlements`),

  getTransactions: (userId: string) => api.get(`/users/${userId}/transactions`),

  // Risk operations
  getRiskProfile: (userId: string) => api.get(`/users/${userId}/risk-profile`),

  recalculateRisk: (userId: string) =>
    api.post(`/users/${userId}/recalculate-risk`),
};

// ==================== Roles API ====================
export const rolesApi = {
  list: (params?: any) => api.get('/role-engineering/roles', { params }),

  get: (roleId: string) => api.get(`/role-engineering/roles/${roleId}`),

  create: (data: any) => api.post('/role-engineering/roles', data),

  update: (roleId: string, data: any) =>
    api.put(`/role-engineering/roles/${roleId}`, data),

  testRole: (roleId: string) =>
    api.post(`/role-engineering/roles/${roleId}/test`),

  getCatalog: () => api.get('/role-engineering/catalog'),
};

// ==================== Reports API ====================
export const reportsApi = {
  list: (params?: any) => api.get('/reporting/reports', { params }),

  get: (reportId: string) => api.get(`/reporting/reports/${reportId}`),

  execute: (reportId: string, params?: any) =>
    api.post(`/reporting/reports/${reportId}/execute`, params),

  export: (reportId: string, format: string) =>
    api.get(`/reporting/reports/${reportId}/export`, {
      params: { format },
      responseType: 'blob',
    }),
};

// ==================== Dashboard API ====================
export const dashboardApi = {
  getStats: () => api.get('/dashboard/summary'),

  getRiskMetrics: () => api.get('/dashboard/risk-metrics'),

  getCertificationMetrics: () => api.get('/dashboard/certification-metrics'),

  getFirefighterMetrics: () => api.get('/dashboard/firefighter-metrics'),
};

// ==================== AI API ====================
export const aiApi = {
  analyzeRisk: (userId: string) => api.post('/ai/risk/analyze', { user_id: userId }),

  query: (query: string) => api.post('/ai/query', { query }),

  mineRoles: (params: any) => api.post('/ai/roles/mine', params),

  getRemediation: (violationId: string) =>
    api.post('/ai/remediation/plan', { violation_id: violationId }),

  chat: (message: string, conversationId?: string) =>
    api.post('/ai/chat', { message, conversation_id: conversationId }),
};

// ==================== Security Controls API ====================
export const securityControlsApi = {
  // Controls CRUD
  list: (params?: {
    category?: string;
    business_area?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => api.get('/security-controls/controls', { params }),

  get: (controlId: string) => api.get(`/security-controls/controls/${controlId}`),

  create: (data: any) => api.post('/security-controls/controls', data),

  update: (controlId: string, data: any) =>
    api.put(`/security-controls/controls/${controlId}`, data),

  delete: (controlId: string) => api.delete(`/security-controls/controls/${controlId}`),

  // Categories and business areas
  getCategories: () => api.get('/security-controls/controls/categories'),
  getBusinessAreas: () => api.get('/security-controls/controls/business-areas'),

  // Value mappings
  getValueMappings: (controlId: string) =>
    api.get(`/security-controls/controls/${controlId}/mappings`),
  addValueMapping: (controlId: string, data: any) =>
    api.post(`/security-controls/controls/${controlId}/mappings`, data),

  // Evaluations
  evaluateControl: (controlId: string, data: {
    system_id: string;
    actual_value?: string;
    client?: string;
    evaluated_by?: string;
    additional_data?: any;
  }) => api.post(`/security-controls/controls/${controlId}/evaluate`, data),

  batchEvaluate: (data: {
    system_id: string;
    client?: string;
    evaluated_by?: string;
    evaluations: Array<{ control_id: string; actual_value?: string; additional_data?: any }>;
  }) => api.post('/security-controls/evaluate/batch', data),

  evaluateParameters: (data: {
    system_id: string;
    client?: string;
    evaluated_by?: string;
    parameter_values: Record<string, any>;
  }) => api.post('/security-controls/evaluate/parameters', data),

  getEvaluations: (params?: {
    control_id?: string;
    system_id?: string;
    risk_rating?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }) => api.get('/security-controls/evaluations', { params }),

  getEvaluationReport: (systemId: string, params?: {
    start_date?: string;
    end_date?: string;
  }) => api.get(`/security-controls/evaluations/report/${systemId}`, { params }),

  // Exceptions
  createException: (data: {
    control_id: string;
    system_id?: string;
    requested_by: string;
    business_justification: string;
    risk_acceptance?: string;
    compensating_controls?: string[];
    valid_from?: string;
    valid_to?: string;
    is_permanent?: boolean;
    review_frequency_days?: number;
  }) => api.post('/security-controls/exceptions', data),

  getExceptions: (params?: {
    control_id?: string;
    system_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => api.get('/security-controls/exceptions', { params }),

  approveException: (exceptionId: string, data: {
    approved_by: string;
    approved: boolean;
    rejection_reason?: string;
  }) => api.post(`/security-controls/exceptions/${exceptionId}/approve`, data),

  // System profiles
  getSystemProfiles: () => api.get('/security-controls/systems'),
  getSystemProfile: (systemId: string) => api.get(`/security-controls/systems/${systemId}`),

  // Dashboard
  getDashboard: () => api.get('/security-controls/dashboard'),

  // Import/Export
  importControls: (data: {
    content: string;
    format: 'csv' | 'json';
    delimiter?: string;
    update_existing?: boolean;
  }) => api.post('/security-controls/import', data),

  importControlsFile: (file: File, updateExisting: boolean = false) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/security-controls/import/file', formData, {
      params: { update_existing: updateExisting },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  exportControls: (format: 'json' | 'csv' = 'json', controlIds?: string[]) =>
    api.get('/security-controls/export', {
      params: {
        format,
        control_ids: controlIds?.join(','),
      },
      responseType: format === 'json' ? 'json' : 'blob',
    }),

  getImportTemplate: (format: 'json' | 'csv' = 'json') =>
    api.get('/security-controls/import/template', { params: { format } }),
};

export default api;
