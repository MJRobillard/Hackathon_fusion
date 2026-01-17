/**
 * Constants for AONP Frontend
 */

export const REFRESH_INTERVALS = {
  statistics: 10000, // 10 seconds
  activeQuery: 2000, // 2 seconds
  runs: 5000, // 5 seconds
} as const;

export const AGENT_ICONS: Record<string, string> = {
  router: '🔀',
  studies: '📊',
  sweep: '📈',
  query: '🔍',
  analysis: '🧪',
};

export const AGENT_COLORS: Record<string, string> = {
  router: 'text-blue-400',
  studies: 'text-green-400',
  sweep: 'text-purple-400',
  query: 'text-yellow-400',
  analysis: 'text-red-400',
};

export const STATUS_COLORS: Record<string, string> = {
  waiting: 'text-gray-400',
  running: 'text-blue-400',
  complete: 'text-green-400',
  failed: 'text-red-400',
};

export const CRITICALITY_STATUS = {
  subcritical: {
    threshold: 1.0,
    label: 'SUB CRITICAL',
    color: 'text-amber-400',
    description: 'Neutron population decreases over time',
  },
  critical: {
    threshold: 1.0,
    label: 'CRITICAL',
    color: 'text-emerald-400',
    description: 'Neutron population remains constant',
  },
  supercritical: {
    threshold: Infinity,
    label: 'SUPER CRITICAL',
    color: 'text-red-400',
    description: 'Neutron population increases over time',
  },
} as const;

export const ROUTING_BADGES: Record<string, { label: string; color: string; time?: string }> = {
  studies: { label: 'Studies', color: 'bg-green-500/20 text-green-400' },
  sweep: { label: 'Sweep', color: 'bg-purple-500/20 text-purple-400' },
  query: { label: 'Query', color: 'bg-yellow-500/20 text-yellow-400' },
  analysis: { label: 'Analysis', color: 'bg-red-500/20 text-red-400' },
  keyword: { label: 'Fast', color: 'bg-blue-500/20 text-blue-400', time: '<50ms' },
  llm: { label: 'Smart', color: 'bg-purple-500/20 text-purple-400', time: '<2s' },
};
