import axios from 'axios';

const getBaseUrl = () => import.meta.env.VITE_API_URL || '';

const api = axios.create();
api.interceptors.request.use(cfg => {
  cfg.baseURL = getBaseUrl();
  const token = localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  const tid = localStorage.getItem('tenant_id');
  if (tid) cfg.headers['X-Tenant-ID'] = tid;
  return cfg;
});

export const riskManagementApi = {
  // Risks
  listRisks: (params?: Record<string, any>) => api.get('/risk-management/risks', { params }),
  getRisk: (id: string) => api.get(`/risk-management/risks/${id}`),
  createRisk: (data: any) => api.post('/risk-management/risks', data),
  updateRisk: (id: string, data: any) => api.put(`/risk-management/risks/${id}`, data),
  deleteRisk: (id: string) => api.delete(`/risk-management/risks/${id}`),
  // Assessments
  createAssessment: (riskId: string, data: any) => api.post(`/risk-management/risks/${riskId}/assessments`, data),
  getRiskAssessments: (riskId: string) => api.get(`/risk-management/risks/${riskId}/assessments`),
  submitAssessment: (id: string) => api.put(`/risk-management/assessments/${id}/submit`),
  reviewAssessment: (id: string, data: any) => api.put(`/risk-management/assessments/${id}/review`, data),
  runCampaign: (data: any) => api.post('/risk-management/assessment-campaigns', data),
  // Appetite
  setAppetite: (data: any) => api.post('/risk-management/appetites', data),
  getAppetite: (params?: any) => api.get('/risk-management/appetites', { params }),
  checkAppetiteBreach: (riskId: string) => api.get(`/risk-management/risks/${riskId}/appetite-check`),
  // KRIs
  createKRI: (data: any) => api.post('/risk-management/kris', data),
  getKRIDashboard: () => api.get('/risk-management/kris/dashboard'),
  recordKRIMeasurement: (kriId: string, data: any) => api.post(`/risk-management/kris/${kriId}/measurements`, data),
  getKRIHistory: (kriId: string) => api.get(`/risk-management/kris/${kriId}/history`),
  // Responses
  createResponse: (riskId: string, data: any) => api.post(`/risk-management/risks/${riskId}/responses`, data),
  getResponses: (riskId: string) => api.get(`/risk-management/risks/${riskId}/responses`),
  updateResponseStatus: (id: string, data: any) => api.put(`/risk-management/responses/${id}/status`, data),
  // Incidents
  reportIncident: (data: any) => api.post('/risk-management/incidents', data),
  updateIncident: (id: string, data: any) => api.put(`/risk-management/incidents/${id}`, data),
  getIncidents: (params?: any) => api.get('/risk-management/incidents', { params }),
  linkIncidentToRisk: (id: string, data: any) => api.post(`/risk-management/incidents/${id}/link-risk`, data),
  // Reporting
  getHeatmap: () => api.get('/risk-management/heatmap'),
  getTrends: (months?: number) => api.get('/risk-management/trends', { params: { period_months: months } }),
  getTopRisks: (limit?: number) => api.get('/risk-management/top-risks', { params: { limit } }),
  getOverdueReviews: () => api.get('/risk-management/overdue-reviews'),
  recordAttestation: (riskId: string, data: any) => api.post(`/risk-management/risks/${riskId}/review-attestation`, data),
};
