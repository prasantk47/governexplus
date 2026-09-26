import { api } from './api';

export const auditManagementApi = {
  // Entities
  listEntities: (params?: Record<string, unknown>) =>
    api.get('/audit-management/entities', { params }),
  createEntity: (data: Record<string, unknown>) =>
    api.post('/audit-management/entities', data),
  updateEntity: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/entities/${id}`, data),
  computeEntityRisk: (id: string) =>
    api.post(`/audit-management/entities/${id}/compute-risk`),

  // Plans
  listPlans: (params?: Record<string, unknown>) =>
    api.get('/audit-management/plans', { params }),
  getPlan: (id: string) => api.get(`/audit-management/plans/${id}`),
  createPlan: (data: Record<string, unknown>) =>
    api.post('/audit-management/plans', data),
  updatePlan: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/plans/${id}`, data),
  submitPlan: (id: string) => api.put(`/audit-management/plans/${id}/submit`),
  approvePlan: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/plans/${id}/approve`, data),
  generateRiskBasedPlan: (data: Record<string, unknown>) =>
    api.post('/audit-management/plans/generate-risk-based', data),

  // Engagements
  listEngagements: (params?: Record<string, unknown>) =>
    api.get('/audit-management/engagements', { params }),
  getEngagement: (id: string) =>
    api.get(`/audit-management/engagements/${id}`),
  createEngagement: (data: Record<string, unknown>) =>
    api.post('/audit-management/engagements', data),
  updateEngagement: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/engagements/${id}`, data),
  advanceEngagement: (id: string) =>
    api.put(`/audit-management/engagements/${id}/advance`),

  // Findings
  listFindings: (params?: Record<string, unknown>) =>
    api.get('/audit-management/findings', { params }),
  createFinding: (engId: string, data: Record<string, unknown>) =>
    api.post(`/audit-management/engagements/${engId}/findings`, data),
  updateFinding: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/findings/${id}`, data),
  recordMgmtResponse: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/findings/${id}/management-response`, data),
  linkFindingToRisk: (id: string, data: Record<string, unknown>) =>
    api.post(`/audit-management/findings/${id}/link-risk`, data),
  linkFindingToControl: (id: string, data: Record<string, unknown>) =>
    api.post(`/audit-management/findings/${id}/link-control`, data),

  // Actions
  createAction: (findingId: string, data: Record<string, unknown>) =>
    api.post(`/audit-management/findings/${findingId}/actions`, data),
  updateAction: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/actions/${id}`, data),
  closeAction: (id: string, data: Record<string, unknown>) =>
    api.put(`/audit-management/actions/${id}/close`, data),
  getOverdueActions: () => api.get('/audit-management/actions/overdue'),
  escalateActions: () => api.post('/audit-management/actions/escalate'),

  // Dashboard & Reports
  getDashboard: () => api.get('/audit-management/dashboard'),
  getCommitteeReport: (params?: Record<string, unknown>) =>
    api.get('/audit-management/committee-report', { params }),
  getEngagementReport: (id: string) =>
    api.get(`/audit-management/engagements/${id}/report`),
};
