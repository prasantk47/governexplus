import { api } from './api';

export const processControlApi = {
  // Controls
  listControls: (params?: Record<string, unknown>) =>
    api.get('/process-control/controls', { params }),
  getControl: (id: string) => api.get(`/process-control/controls/${id}`),
  createControl: (data: Record<string, unknown>) =>
    api.post('/process-control/controls', data),
  updateControl: (id: string, data: Record<string, unknown>) =>
    api.put(`/process-control/controls/${id}`, data),
  retireControl: (id: string) =>
    api.put(`/process-control/controls/${id}/retire`),

  // Testing
  createTest: (controlId: string, data: Record<string, unknown>) =>
    api.post(`/process-control/controls/${controlId}/tests`, data),
  recordTestResult: (testId: string, data: Record<string, unknown>) =>
    api.put(`/process-control/tests/${testId}/result`, data),
  getControlTests: (controlId: string) =>
    api.get(`/process-control/controls/${controlId}/tests`),

  // Deficiencies
  listDeficiencies: (params?: Record<string, unknown>) =>
    api.get('/process-control/deficiencies', { params }),
  createDeficiency: (data: Record<string, unknown>) =>
    api.post('/process-control/deficiencies', data),
  updateDeficiency: (id: string, data: Record<string, unknown>) =>
    api.put(`/process-control/deficiencies/${id}`, data),
  remediateDeficiency: (id: string, data: Record<string, unknown>) =>
    api.put(`/process-control/deficiencies/${id}/remediate`, data),
  verifyDeficiency: (id: string) =>
    api.put(`/process-control/deficiencies/${id}/verify`),

  // Self-Assessment
  createCampaign: (data: Record<string, unknown>) =>
    api.post('/process-control/self-assessment-campaigns', data),
  submitAssessment: (id: string, data: Record<string, unknown>) =>
    api.put(`/process-control/self-assessments/${id}/submit`, data),
  getPendingAssessments: (params?: Record<string, unknown>) =>
    api.get('/process-control/self-assessments/pending', { params }),

  // CCM
  listCCMRules: () => api.get('/process-control/ccm-rules'),
  createCCMRule: (data: Record<string, unknown>) =>
    api.post('/process-control/ccm-rules', data),
  executeCCMRule: (ruleId: string) =>
    api.post(`/process-control/ccm-rules/${ruleId}/execute`),
  runAllCCM: () => api.post('/process-control/ccm/run-all'),
  getCCMDashboard: () => api.get('/process-control/ccm/dashboard'),

  // Evidence
  uploadEvidence: (data: Record<string, unknown>) =>
    api.post('/process-control/evidence', data),
  listEvidence: (params?: Record<string, unknown>) =>
    api.get('/process-control/evidence', { params }),
  getEvidence: (id: string) => api.get(`/process-control/evidence/${id}`),
  setLegalHold: (id: string, data: Record<string, unknown>) =>
    api.put(`/process-control/evidence/${id}/legal-hold`, data),

  // Sign-Off
  createSignoff: (data: Record<string, unknown>) =>
    api.post('/process-control/signoffs', data),
  submitCertification: (id: string, data: Record<string, unknown>) =>
    api.put(`/process-control/signoffs/${id}/submit`, data),
  getSignoffHierarchy: (params?: Record<string, unknown>) =>
    api.get('/process-control/signoffs/hierarchy', { params }),
  getPendingSignoffs: (params?: Record<string, unknown>) =>
    api.get('/process-control/signoffs/pending', { params }),

  // Dashboard
  getDashboard: () => api.get('/process-control/dashboard'),
  getAuditPackage: (controlId: string) =>
    api.get(`/process-control/controls/${controlId}/audit-package`),

  // Frameworks
  getFrameworkCoverage: (frameworkId: string) =>
    api.get(`/process-control/frameworks/${frameworkId}/coverage`),
};
