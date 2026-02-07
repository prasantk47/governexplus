/**
 * Provisioning API Service
 *
 * Client for the provisioning engine API endpoints.
 */

const getApiBase = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl) return envUrl;
  if (import.meta.env.DEV) return 'http://localhost:9000';
  return '/api';
};

const API_BASE = getApiBase();

export interface ConnectorType {
  type_id: string;
  display_name: string;
  description: string;
  category: string;
}

export interface ConnectorConfig {
  connector_id: string;
  type_id: string;
  name: string;
  host: string;
  port?: number;
  username: string;
  password: string;
  enabled: boolean;
  extra_config?: Record<string, unknown>;
}

export interface ConnectorStatus {
  connector_id: string;
  name: string;
  system_type: string;
  status: 'disconnected' | 'connecting' | 'connected' | 'error' | 'reconnecting';
  is_connected: boolean;
  connected_at?: string;
  last_error?: {
    error: string;
    code: string;
    timestamp: string;
  };
  operation_count: number;
  error_count: number;
  enabled: boolean;
}

export interface ProvisioningTask {
  task_id: string;
  source_type: string;
  source_id: string;
  user_id: string;
  user_name: string;
  description: string;
  status: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  progress: {
    total: number;
    completed: number;
    failed: number;
    pending: number;
    progress_percent: number;
  };
  steps: ProvisioningStep[];
}

export interface ProvisioningStep {
  step_id: string;
  action: string;
  target_system: string;
  target_user: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  result?: Record<string, unknown>;
}

export interface UserData {
  user_id: string;
  first_name: string;
  last_name: string;
  email: string;
  department?: string;
  job_title?: string;
  manager_id?: string;
  initial_password?: string;
}

export interface RoleAssignment {
  system: string;
  role_name: string;
  valid_from?: string;
  valid_to?: string;
}

class ProvisioningApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = localStorage.getItem('accessToken');
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // ==========================================================================
  // Connector Types
  // ==========================================================================

  async getConnectorTypes(): Promise<{
    types: ConnectorType[];
    categories: Record<string, ConnectorType[]>;
  }> {
    return this.request('/provisioning/connector-types');
  }

  // ==========================================================================
  // Connector Management
  // ==========================================================================

  async listConnectors(): Promise<{ connectors: ConnectorStatus[] }> {
    return this.request('/provisioning/connectors');
  }

  async getConnector(connectorId: string): Promise<ConnectorStatus> {
    return this.request(`/provisioning/connectors/${connectorId}`);
  }

  async createConnector(config: ConnectorConfig): Promise<{
    success: boolean;
    connector_id: string;
    status: ConnectorStatus;
  }> {
    return this.request('/provisioning/connectors', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async deleteConnector(connectorId: string): Promise<{ success: boolean }> {
    return this.request(`/provisioning/connectors/${connectorId}`, {
      method: 'DELETE',
    });
  }

  async connectConnector(connectorId: string): Promise<{
    success: boolean;
    status: ConnectorStatus;
  }> {
    return this.request(`/provisioning/connectors/${connectorId}/connect`, {
      method: 'POST',
    });
  }

  async disconnectConnector(connectorId: string): Promise<{
    success: boolean;
    status: ConnectorStatus;
  }> {
    return this.request(`/provisioning/connectors/${connectorId}/disconnect`, {
      method: 'POST',
    });
  }

  async testConnection(connectorId: string): Promise<{
    success: boolean;
    operation: string;
    data?: Record<string, unknown>;
    error?: string;
    duration_ms: number;
  }> {
    return this.request(`/provisioning/connectors/${connectorId}/test`, {
      method: 'POST',
    });
  }

  // ==========================================================================
  // User/Role Queries
  // ==========================================================================

  async listUsers(
    connectorId: string,
    pattern?: string
  ): Promise<{
    success: boolean;
    data?: { users: Array<{ user_id: string; first_name?: string; last_name?: string }>; count: number };
    error?: string;
  }> {
    const params = pattern ? `?pattern=${encodeURIComponent(pattern)}` : '';
    return this.request(`/provisioning/connectors/${connectorId}/users${params}`);
  }

  async getUser(
    connectorId: string,
    userId: string
  ): Promise<{
    success: boolean;
    data?: Record<string, unknown>;
    error?: string;
  }> {
    return this.request(`/provisioning/connectors/${connectorId}/users/${userId}`);
  }

  async getUserRoles(
    connectorId: string,
    userId: string
  ): Promise<{
    success: boolean;
    data?: { user_id: string; roles: Array<{ role_name: string; from_date?: string; to_date?: string }> };
    error?: string;
  }> {
    return this.request(`/provisioning/connectors/${connectorId}/users/${userId}/roles`);
  }

  async listRoles(
    connectorId: string,
    pattern?: string
  ): Promise<{
    success: boolean;
    data?: { roles: Array<{ role_name: string; description?: string }>; count: number };
    error?: string;
  }> {
    const params = pattern ? `?pattern=${encodeURIComponent(pattern)}` : '';
    return this.request(`/provisioning/connectors/${connectorId}/roles${params}`);
  }

  // ==========================================================================
  // Provisioning Operations
  // ==========================================================================

  async provisionUser(
    userData: UserData,
    targetSystems: string[],
    sourceType: string = 'manual',
    sourceId: string = ''
  ): Promise<{ success: boolean; task: ProvisioningTask }> {
    return this.request('/provisioning/provision/user', {
      method: 'POST',
      body: JSON.stringify({
        ...userData,
        target_systems: targetSystems,
        source_type: sourceType,
        source_id: sourceId,
      }),
    });
  }

  async assignRoles(
    userId: string,
    roles: RoleAssignment[],
    sourceType: string = 'access_request',
    sourceId: string = '',
    priority: string = 'normal'
  ): Promise<{ success: boolean; task: ProvisioningTask }> {
    return this.request('/provisioning/provision/roles/assign', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        roles,
        source_type: sourceType,
        source_id: sourceId,
        priority,
      }),
    });
  }

  async revokeRoles(
    userId: string,
    roles: Array<{ system: string; role_name: string }>,
    sourceType: string = 'access_request',
    sourceId: string = ''
  ): Promise<{ success: boolean; task: ProvisioningTask }> {
    return this.request('/provisioning/provision/roles/revoke', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        roles,
        source_type: sourceType,
        source_id: sourceId,
      }),
    });
  }

  async deprovisionUser(
    userId: string,
    targetSystems: string[],
    action: 'lock' | 'disable' | 'delete' = 'lock',
    sourceType: string = 'jml_event',
    sourceId: string = ''
  ): Promise<{ success: boolean; task: ProvisioningTask }> {
    return this.request('/provisioning/provision/deprovision', {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        target_systems: targetSystems,
        action,
        source_type: sourceType,
        source_id: sourceId,
      }),
    });
  }

  // ==========================================================================
  // Task Management
  // ==========================================================================

  async listTasks(filters?: {
    status?: string;
    user_id?: string;
    source_type?: string;
    limit?: number;
  }): Promise<{ tasks: ProvisioningTask[]; count: number }> {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.user_id) params.append('user_id', filters.user_id);
    if (filters?.source_type) params.append('source_type', filters.source_type);
    if (filters?.limit) params.append('limit', filters.limit.toString());

    const query = params.toString();
    return this.request(`/provisioning/tasks${query ? `?${query}` : ''}`);
  }

  async getTask(taskId: string): Promise<ProvisioningTask> {
    return this.request(`/provisioning/tasks/${taskId}`);
  }

  async cancelTask(taskId: string): Promise<{ success: boolean }> {
    return this.request(`/provisioning/tasks/${taskId}/cancel`, {
      method: 'POST',
    });
  }

  // ==========================================================================
  // Queue Management
  // ==========================================================================

  async getQueueStatus(): Promise<{
    running: boolean;
    workers: number;
    queue_size: number;
    processing: number;
    completed: number;
    failed: number;
    stats: Record<string, number>;
  }> {
    return this.request('/provisioning/queue/status');
  }

  async startQueue(): Promise<{ success: boolean }> {
    return this.request('/provisioning/queue/start', { method: 'POST' });
  }

  async stopQueue(): Promise<{ success: boolean }> {
    return this.request('/provisioning/queue/stop', { method: 'POST' });
  }

  async retryFailedTask(taskId: string): Promise<{ success: boolean }> {
    return this.request(`/provisioning/queue/tasks/${taskId}/retry`, {
      method: 'POST',
    });
  }
}

export const provisioningApi = new ProvisioningApiService();
export default provisioningApi;
