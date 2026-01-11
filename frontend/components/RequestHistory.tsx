'use client';

import { Clock } from 'lucide-react';
import { AGENT_ICONS, ROUTING_BADGES } from '@/lib/constants';
import { formatTimeAgo, truncateQuery } from '@/lib/formatters';
import type { QueryData } from '@/lib/types';

interface RequestHistoryProps {
  queries: QueryData[];
  activeQueryId?: string;
  onSelect: (queryId: string) => void;
}

export function RequestHistory({ queries, activeQueryId, onSelect }: RequestHistoryProps) {
  const getStatusIcon = (status: string) => {
    const icons = {
      queued: '⏳',
      processing: '🔄',
      completed: '✓',
      failed: '✗',
    };
    return icons[status as keyof typeof icons] || '•';
  };

  const getStatusColor = (status: string) => {
    const colors = {
      queued: 'text-yellow-400',
      processing: 'text-blue-400',
      completed: 'text-emerald-400',
      failed: 'text-red-400',
    };
    return colors[status as keyof typeof colors] || 'text-gray-400';
  };

  if (queries.length === 0) {
    return (
      <div className="h-full bg-gray-900 border-r border-gray-800 p-4">
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-800">
          <Clock size={18} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-200">Recent Requests</h2>
        </div>
        <div className="text-center text-xs text-gray-500 mt-8">
          No queries yet.<br />Submit one to get started.
        </div>
      </div>
    );
  }

  return (
    <div className="h-full bg-gray-900 border-r border-gray-800 p-4 overflow-y-auto">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-gray-800">
        <Clock size={18} className="text-gray-400" />
        <h2 className="text-sm font-semibold text-gray-200">Recent Requests</h2>
        <span className="ml-auto text-xs text-gray-500">{queries.length}</span>
      </div>

      <div className="space-y-2">
        {queries.map((query) => (
          <button
            key={query.query_id}
            onClick={() => onSelect(query.query_id)}
            className={`w-full text-left p-3 rounded-lg border transition-all ${
              activeQueryId === query.query_id
                ? 'bg-blue-600/10 border-blue-500/50 shadow-lg shadow-blue-500/10'
                : 'bg-gray-800/50 border-gray-700/50 hover:bg-gray-800 hover:border-gray-600'
            }`}
          >
            {/* Query ID */}
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-xs font-mono text-gray-400">{query.query_id}</span>
              <span className={`text-xs ${getStatusColor(query.status)}`}>
                {getStatusIcon(query.status)}
              </span>
            </div>

            {/* Query Text */}
            <div className="text-xs text-gray-300 mb-2 line-clamp-2">
              &quot;{truncateQuery(query.query, 60)}&quot;
            </div>

            {/* Routing & Time */}
            <div className="flex items-center justify-between text-[10px]">
              {query.routing ? (
                <div className="flex items-center gap-1.5">
                  <span className="text-gray-500">🔀</span>
                  <span className="text-gray-400">
                    {AGENT_ICONS[query.routing.agent]} {query.routing.agent}
                  </span>
                  <span className="text-gray-600">
                    ({query.routing.method === 'keyword' ? '⚡' : '🧠'})
                  </span>
                </div>
              ) : (
                <span className="text-gray-500">Routing...</span>
              )}
              <span className="text-gray-500">{formatTimeAgo(query.created_at)}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

