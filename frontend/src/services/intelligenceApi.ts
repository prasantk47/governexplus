import axios from 'axios';

const getBaseUrl = () => import.meta.env.VITE_API_URL || '';

const api = axios.create();

api.interceptors.request.use((cfg) => {
  cfg.baseURL = getBaseUrl();
  const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  const tid = localStorage.getItem('tenant_id');
  if (tid) cfg.headers['X-Tenant-ID'] = tid;
  return cfg;
});

export interface HealthScore {
  overall: number;
  overall_score?: number;
  trend: number | string;
  trend_label?: string;
  components?: {
    access: number;
    controls: number;
    risk: number;
    audit: number;
  };
  pillars?: Record<string, { score: number; label: string; [k: string]: unknown }>;
  narrative?: string;
  computed_at?: string;
}

export interface AttentionItem {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  action_label: string;
  action_type: 'fix' | 'review' | 'escalate' | 'investigate';
  link?: string;
  object_type?: string;
  object_id?: string;
  module?: string;
  due_in?: string;
}

export interface Insight {
  id: string;
  title: string;
  narrative: string;
  trend?: string;
  severity?: 'critical' | 'high' | 'medium' | 'info';
  related_count?: number;
  category?: string;
}

export interface ExplainResult {
  object_type: string;
  object_id: string;
  narrative: string;
  risk_level: string;
  recommendations: string[];
}

export interface FixPreview {
  object_type: string;
  object_id: string;
  title: string;
  description: string;
  impact: string;
  steps: string[];
  reversible: boolean;
  estimated_effort: string;
}

export interface ModuleStat {
  label: string;
  value: string | number;
  trend?: number;
  link: string;
  color?: string;
}

export interface PersonalizedDashboard {
  greeting: string;
  attention_count: number;
  module_stats: ModuleStat[];
  recent_activity: {
    id: string;
    timestamp: string;
    actor: string;
    action: string;
    object: string;
    module: string;
  }[];
}

export const intelligenceApi = {
  getHealthScore: () => api.get<HealthScore>('/grc-intelligence/health'),
  getAttentionItems: (params?: { role?: string }) =>
    api.get<AttentionItem[]>('/grc-intelligence/attention', { params }),
  getInsights: () => api.get<Insight[]>('/grc-intelligence/attention'),
  explain: (objectType: string, objectId: string) =>
    api.post<ExplainResult>('/grc-intelligence/explain', {
      object_type: objectType,
      object_id: objectId,
    }),
  investigate: (query: string) =>
    api.post<{ answer: string; sources: string[] }>('/grc-intelligence/investigate', { query }),
  previewFix: (objectType: string, objectId: string) =>
    api.post<FixPreview>('/grc-intelligence/fix-preview', {
      object_type: objectType,
      object_id: objectId,
    }),
  quickFix: (objectType: string, objectId: string) =>
    api.post<{ success: boolean; message: string }>('/grc-intelligence/quick-fix', {
      object_type: objectType,
      object_id: objectId,
      confirmed: true,
    }),
  getPersonalizedDashboard: (role: string) =>
    api.get<PersonalizedDashboard>(`/grc-intelligence/dashboard/${role}`),
};
