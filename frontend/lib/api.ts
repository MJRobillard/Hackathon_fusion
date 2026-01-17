/**
 * API Service for AONP Frontend
 * Handles all communication with the backend API
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

class APIService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} ${response.statusText} - ${errorText}`);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error(`Failed to connect to backend at ${url}. Is the server running?`);
      }
      throw error;
    }
  }

  // Health & Statistics
  async getHealth() {
    return this.fetchJson<any>('/api/v1/health');
  }

  async getStatistics() {
    return this.fetchJson<any>('/api/v1/statistics');
  }

  // Query endpoints
  async submitQuery(query: string, useLLM: boolean = false) {
    return this.fetchJson<{ query_id: string; status: string; stream_url?: string }>(
      '/api/v1/query',
      {
        method: 'POST',
        body: JSON.stringify({ query, use_llm: useLLM }),
      }
    );
  }

  async getQuery(queryId: string) {
    return this.fetchJson<any>(`/api/v1/query/${queryId}`);
  }

  createEventStream(queryId: string): EventSource {
    const url = `${this.baseUrl}/api/v1/query/${queryId}/stream`;
    return new EventSource(url);
  }

  // Runs endpoints
  async getRuns(limit: number = 50, offset: number = 0) {
    return this.fetchJson<any>(`/api/v1/runs?limit=${limit}&offset=${offset}`);
  }

  async getRunVisualization(runId: string) {
    return this.fetchJson<any>(`/api/v1/runs/${runId}/visualization`);
  }

  async getSweepVisualization(runIds: string[]) {
    return this.fetchJson<any>('/api/v1/runs/sweep/visualization', {
      method: 'POST',
      body: JSON.stringify({ run_ids: runIds }),
    });
  }

  async getComparisonVisualization(runIds: string[]) {
    return this.fetchJson<any>('/api/v1/runs/comparison/visualization', {
      method: 'POST',
      body: JSON.stringify({ run_ids: runIds }),
    });
  }

  async findSimilarRuns(runId: string, limit: number = 10) {
    return this.fetchJson<any>(`/api/v1/runs/${runId}/similar?limit=${limit}`);
  }

  // Database endpoints
  async getCollections() {
    return this.fetchJson<string[]>('/api/v1/db/collections');
  }

  async getDocuments(collection: string, limit: number = 50, offset: number = 0) {
    return this.fetchJson<any>(`/api/v1/db/${collection}?limit=${limit}&offset=${offset}`);
  }

  async getCollectionCount(collection: string) {
    return this.fetchJson<{ count: number }>(`/api/v1/db/${collection}/count`);
  }

  // RAG endpoints
  async ragGetHealth() {
    return this.fetchJson<any>('/api/v1/rag/health');
  }

  async ragGetStats() {
    return this.fetchJson<any>('/api/v1/rag/stats');
  }

  async ragQuery(query: string) {
    return this.fetchJson<any>('/api/v1/rag/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  }

  // Orchestration config
  async getOrchestrationConfig() {
    return this.fetchJson<any>('/api/v1/orchestration/config');
  }

  async patchOrchestrationConfig(config: any) {
    return this.fetchJson<any>('/api/v1/orchestration/config', {
      method: 'PATCH',
      body: JSON.stringify(config),
    });
  }

  // OpenMC endpoints (for OpenMCBackendPanel)
  async openmcGetHealth() {
    return this.fetchJson<any>('/api/v1/openmc/health');
  }

  async openmcGetStatistics() {
    return this.fetchJson<any>('/api/v1/openmc/statistics');
  }

  async openmcQueryRuns(params: { limit?: number; offset?: number; geometry?: string; status?: string }) {
    const queryParams = new URLSearchParams();
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.offset) queryParams.set('offset', params.offset.toString());
    if (params.geometry) queryParams.set('geometry', params.geometry);
    if (params.status) queryParams.set('status', params.status);
    
    return this.fetchJson<any>(`/api/v1/openmc/runs?${queryParams.toString()}`);
  }

  async openmcGetRun(runId: string) {
    return this.fetchJson<any>(`/api/v1/openmc/simulations/${runId}`);
  }

  async openmcGetSimulation(runId: string) {
    return this.fetchJson<any>(`/api/v1/openmc/simulations/${runId}`);
  }

  async openmcSubmitSimulation(spec: any) {
    return this.fetchJson<any>('/api/v1/openmc/simulations', {
      method: 'POST',
      body: JSON.stringify({ spec }),
    });
  }

  async openmcSubmitSweep(baseSpec: any, parameter: string, values: number[]) {
    return this.fetchJson<any>('/api/v1/openmc/sweeps', {
      method: 'POST',
      body: JSON.stringify({ base_spec: baseSpec, parameter, values }),
    });
  }
}

export const apiService = new APIService();
