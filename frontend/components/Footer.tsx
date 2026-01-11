'use client';

import { Database, Activity, CheckCircle, XCircle } from 'lucide-react';
import { formatNumber } from '@/lib/formatters';
import type { SystemStatistics } from '@/lib/types';

interface FooterProps {
  statistics?: SystemStatistics;
  isLoading?: boolean;
}

export function Footer({ statistics, isLoading }: FooterProps) {
  if (isLoading) {
    return (
      <div className="bg-gray-900 border-t border-gray-800 px-6 py-2">
        <div className="flex items-center justify-center text-xs text-gray-500">
          Loading statistics...
        </div>
      </div>
    );
  }

  if (!statistics) {
    return (
      <div className="bg-gray-900 border-t border-gray-800 px-6 py-2">
        <div className="flex items-center justify-center text-xs text-gray-500">
          Statistics unavailable
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border-t border-gray-800 px-6 py-2">
      <div className="flex items-center justify-between text-xs">
        {/* Left: Statistics */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-gray-400">
            <Database size={14} />
            <span className="text-gray-500">Studies:</span>
            <span className="font-mono font-semibold text-gray-300">
              {formatNumber(statistics.total_studies)}
            </span>
          </div>

          <div className="text-gray-700">|</div>

          <div className="flex items-center gap-1.5 text-gray-400">
            <Activity size={14} />
            <span className="text-gray-500">Runs:</span>
            <span className="font-mono font-semibold text-gray-300">
              {formatNumber(statistics.total_runs)}
            </span>
            <span className="text-gray-600">
              ({formatNumber(statistics.completed_runs)} completed)
            </span>
          </div>

          <div className="text-gray-700">|</div>

          <div className="flex items-center gap-1.5 text-gray-400">
            <span className="text-gray-500">Queries:</span>
            <span className="font-mono font-semibold text-gray-300">
              {formatNumber(statistics.total_queries)}
            </span>
          </div>
        </div>

        {/* Right: MongoDB Status */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-gray-500">MongoDB:</span>
            {statistics.mongodb_status === 'connected' ? (
              <div className="flex items-center gap-1.5 text-emerald-400">
                <CheckCircle size={14} />
                <span className="font-semibold">Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-red-400">
                <XCircle size={14} />
                <span className="font-semibold">Disconnected</span>
              </div>
            )}
          </div>

          {/* Backend Indicator */}
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-gray-500">Backend Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}

