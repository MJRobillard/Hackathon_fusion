'use client';

import { useEffect, useRef } from 'react';
import { Terminal, Trash2 } from 'lucide-react';
import { formatTimestamp } from '@/lib/formatters';
import type { LogEntry } from '@/lib/types';

interface ExecutionLogsProps {
  logs: LogEntry[];
  autoScroll?: boolean;
  onClear?: () => void;
}

export function ExecutionLogs({ logs, autoScroll = true, onClear }: ExecutionLogsProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const getLogColor = (level: string, source: string) => {
    if (level === 'error') return 'text-red-400';
    if (level === 'warning') return 'text-yellow-400';
    if (level === 'success') return 'text-emerald-400';

    // Source-specific colors
    const sourceColors: Record<string, string> = {
      ROUTER: 'text-gray-400',
      STUDIES: 'text-blue-400',
      SWEEP: 'text-purple-400',
      QUERY: 'text-emerald-400',
      ANALYSIS: 'text-orange-400',
      TOOL: 'text-cyan-400',
      SYSTEM: 'text-pink-400',
    };

    return sourceColors[source] || 'text-gray-300';
  };

  const getSourceBadge = (source: string) => {
    const badges: Record<string, string> = {
      ROUTER: 'bg-gray-600/20 text-gray-400 border-gray-600/30',
      STUDIES: 'bg-blue-600/20 text-blue-400 border-blue-600/30',
      SWEEP: 'bg-purple-600/20 text-purple-400 border-purple-600/30',
      QUERY: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
      ANALYSIS: 'bg-orange-600/20 text-orange-400 border-orange-600/30',
      TOOL: 'bg-cyan-600/20 text-cyan-400 border-cyan-600/30',
      SYSTEM: 'bg-pink-600/20 text-pink-400 border-pink-600/30',
    };

    const badgeClass = badges[source] || 'bg-gray-600/20 text-gray-400 border-gray-600/30';

    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${badgeClass}`}
      >
        {source}
      </span>
    );
  };

  if (logs.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 h-full">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Terminal size={18} className="text-gray-400" />
            <h3 className="text-sm font-semibold text-gray-200">Execution Logs</h3>
          </div>
        </div>
        <div className="text-center text-xs text-gray-500 mt-8">
          Waiting for execution logs...
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Terminal size={18} className="text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-200">Execution Logs</h3>
          <span className="text-xs text-gray-500">({logs.length})</span>
        </div>
        {onClear && logs.length > 0 && (
          <button
            onClick={onClear}
            className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
          >
            <Trash2 size={12} />
            <span>Clear</span>
          </button>
        )}
      </div>

      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto space-y-1 font-mono text-[11px] leading-relaxed"
      >
        {logs.map((log, index) => (
          <div key={index} className="flex gap-3 hover:bg-gray-800/50 px-2 py-1 rounded">
            <span className="text-gray-600 shrink-0 w-[65px]">
              {formatTimestamp(log.timestamp)}
            </span>
            <span className="shrink-0 w-[90px]">{getSourceBadge(log.source)}</span>
            <span className={`flex-1 ${getLogColor(log.level, log.source)}`}>
              {log.message}
            </span>
          </div>
        ))}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

