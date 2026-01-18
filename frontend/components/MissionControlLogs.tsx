'use client';

import { useEffect, useRef } from 'react';

interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'PROCESS' | 'ERROR';
  message: string;
}

interface MissionControlLogsProps {
  logs?: LogEntry[];
  autoScroll?: boolean;
  showCursor?: boolean;
}

const LogLine = ({ log }: { log: LogEntry }) => {
  const levelColors = {
    INFO: 'text-gray-400',
    WARNING: 'text-amber-400',
    PROCESS: 'text-blue-400',
    ERROR: 'text-red-400',
  };

  const levelBadges = {
    INFO: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    WARNING: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    PROCESS: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    ERROR: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  return (
    <div className="flex items-start gap-3 py-1.5 hover:bg-[#14161B] transition-colors">
      <span className="text-[10px] font-mono text-gray-600 shrink-0 w-20">
        {log.timestamp}
      </span>
      <span
        className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 border rounded shrink-0 ${levelBadges[log.level]}`}
      >
        {log.level}
      </span>
      <span className={`text-xs font-mono ${levelColors[log.level]} leading-relaxed flex-1`}>
        {log.message}
      </span>
    </div>
  );
};

const defaultLogs: LogEntry[] = [
  {
    timestamp: '14:30:05',
    level: 'INFO',
    message: 'Initializing OpenMC environment...',
  },
  {
    timestamp: '14:30:08',
    level: 'INFO',
    message: 'Loading cross-section data: ENDF/B-VII.1',
  },
  {
    timestamp: '14:31:12',
    level: 'PROCESS',
    message: 'Agent "MaterialsOptimizer" spawned (PID: 4421)',
  },
  {
    timestamp: '14:35:44',
    level: 'WARNING',
    message: 'Local flux density exceeding nominal variance.',
  },
  {
    timestamp: '14:38:22',
    level: 'INFO',
    message: 'Iteration 42/100 complete. k-eff: 1.00245 ± 0.00012',
  },
];

export function MissionControlLogs({
  logs = defaultLogs,
  autoScroll = true,
  showCursor = true,
}: MissionControlLogsProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  return (
    <div className="h-full bg-[#0A0B0D] border border-[#1F2937] rounded flex flex-col">
      {/* Header */}
      <div className="h-10 border-b border-[#1F2937] flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h3 className="text-xs font-semibold text-gray-300 tracking-wide">EXECUTION LOGS</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-3 text-[10px] font-mono text-gray-500">
            <span>ERRORS: <span className="text-red-400">0</span></span>
            <span>WARNINGS: <span className="text-amber-400">1</span></span>
          </div>
          <button className="p-1 hover:bg-[#1F2937] rounded transition-colors">
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Logs Content */}
      <div className="flex-1 overflow-y-auto px-4 py-2 terminal-text">
        {logs.map((log, index) => (
          <LogLine key={index} log={log} />
        ))}
        {showCursor && (
          <div className="flex items-start gap-3 py-1.5">
            <span className="text-[10px] font-mono text-gray-600 w-20">--:--:--</span>
            <span className="text-xs font-mono text-gray-400 animate-cursor">▊</span>
          </div>
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

