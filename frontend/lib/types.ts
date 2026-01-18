/**
 * TypeScript type definitions for AONP Frontend
 */

export interface QueryData {
  query_id: string;
  query: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  routing?: RoutingInfo;
  results?: SimulationResults;
  analysis?: any;
  suggestions?: any;
  error?: string;
}

export interface RoutingInfo {
  agent: string;
  intent: string;
  confidence?: number;
  reasoning?: string;
  method?: 'keyword' | 'llm';
}

export interface AgentStatus {
  agent: 'router' | 'studies' | 'sweep' | 'query' | 'analysis';
  status: 'waiting' | 'running' | 'complete' | 'failed';
  duration?: number;
}

export interface LogEntry {
  timestamp: string;
  source: 'SYSTEM' | 'ROUTER' | 'STUDIES' | 'SWEEP' | 'QUERY' | 'ANALYSIS' | 'TOOL';
  message: string;
  level?: 'info' | 'success' | 'warning' | 'error';
}

export interface SimulationResults {
  status: string;
  run_id?: string;
  run_ids?: string[];
  keff?: number;
  keff_std?: number;
  spec?: any;
  geometry?: string;
  enrichment_pct?: number;
  temperature_K?: number;
  particles?: number;
  batches?: number;
  keff_mean?: number;
  keff_min?: number;
  keff_max?: number;
  keff_values?: number[];
  results?: Array<{
    run_id?: string;
    keff?: number;
    geometry?: string;
    [key: string]: any;
  }>;
  count?: number;
}

export interface SystemStatistics {
  total_studies: number;
  total_runs: number;
  completed_runs: number;
  total_queries: number;
  mongodb_status?: string;
}

export interface BatchConvergenceData {
  batch_numbers: number[];
  batch_keff: number[];
  entropy?: number[];
  n_inactive: number;
  final_keff: number;
  final_keff_std: number;
  note?: string;
}

export interface ParameterSweepData {
  parameter: string;
  values: number[];
  keff: number[];
  keff_std: number[];
}

export interface ComparisonData {
  num_runs: number;
  keff_values: number[];
  keff_mean: number;
  keff_min: number;
  keff_max: number;
  runs: Array<{
    run_id: string;
    keff: number;
    keff_std?: number;
  }>;
}

export interface VisualizationResponse {
  type: 'batch_convergence' | 'parameter_sweep' | 'comparison';
  data: BatchConvergenceData | ParameterSweepData | ComparisonData;
}

export interface RunSummary {
  run_id: string;
  geometry: string;
  keff?: number;
  keff_std?: number;
  status: string;
  created_at: string;
  enrichment_pct?: number;
  temperature_K?: number;
}

export interface RAGHealth {
  status: string;
  vector_db?: string;
  documents?: number;
  fireworks_llm?: string;
  papers_indexed?: number;
  runs_indexed?: number;
}

export interface RAGStats {
  total_queries?: number;
  total_documents?: number;
  average_response_time?: number;
  status?: string;
  collections?: {
    papers?: {
      count: number;
      description: string;
    };
    runs?: {
      count: number;
      description: string;
    };
  };
  vector_store?: {
    type: string;
    location: string;
  };
}

export interface RAGResponse {
  answer: string;
  sources: Array<{
    document: string;
    score: number;
    content: string;
  }>;
  query_id?: string;
}

export interface RunQueryResponse {
  runs: RunSummary[];
  total: number;
  limit: number;
  offset: number;
}
