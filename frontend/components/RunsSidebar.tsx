'use client';

interface RunData {
  id: string;
  status: 'running' | 'success' | 'warning' | 'failed';
  label: string;
  timestamp: string;
}

interface RunsSidebarProps {
  runs?: RunData[];
  activeRunId?: string;
  onSelectRun?: (runId: string) => void;
}

const StatusPill = ({ status }: { status: RunData['status'] }) => {
  const statusConfig = {
    running: {
      label: 'RUNNING',
      dotColor: 'bg-blue-500',
      textColor: 'text-blue-400',
      borderColor: 'border-blue-500/30',
      bgColor: 'bg-blue-500/10',
      pulse: true,
    },
    success: {
      label: 'SUCCESS',
      dotColor: 'bg-emerald-500',
      textColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/30',
      bgColor: 'bg-emerald-500/10',
      pulse: false,
    },
    warning: {
      label: 'WARNING',
      dotColor: 'bg-amber-500',
      textColor: 'text-amber-400',
      borderColor: 'border-amber-500/30',
      bgColor: 'bg-amber-500/10',
      pulse: false,
    },
    failed: {
      label: 'FAILED',
      dotColor: 'bg-red-500',
      textColor: 'text-red-400',
      borderColor: 'border-red-500/30',
      bgColor: 'bg-red-500/10',
      pulse: false,
    },
  };

  const config = statusConfig[status];

  return (
    <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded border ${config.borderColor} ${config.bgColor}`}>
      <div className="relative flex items-center">
        <div className={`w-1.5 h-1.5 rounded-full ${config.dotColor} ${config.pulse ? 'animate-pulse-dot' : ''}`} />
        {config.pulse && (
          <div className={`absolute w-1.5 h-1.5 rounded-full ${config.dotColor} animate-pulse-ring`} />
        )}
      </div>
      <span className={`text-[9px] font-mono font-semibold ${config.textColor}`}>
        {config.label}
      </span>
    </div>
  );
};

const defaultRuns: RunData[] = [
  {
    id: 'OM-945',
    status: 'running',
    label: 'Neutronics',
    timestamp: '14:30:05',
  },
  {
    id: 'OM-944',
    status: 'success',
    label: 'Optimization',
    timestamp: '13:15:20',
  },
  {
    id: 'OM-943',
    status: 'warning',
    label: 'Coupled',
    timestamp: '12:05:11',
  },
  {
    id: 'OM-942',
    status: 'failed',
    label: 'Neutronics',
    timestamp: '10:45:00',
  },
  {
    id: 'OM-941',
    status: 'success',
    label: 'Neutronics',
    timestamp: '09:00:15',
  },
];

export function RunsSidebar({ runs = defaultRuns, activeRunId, onSelectRun }: RunsSidebarProps) {
  return (
    <div className="w-80 h-full bg-[#0A0B0D] border-r border-[#1F2937] flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-[#1F2937] flex items-center px-4">
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
          <h2 className="text-sm font-semibold text-gray-300 tracking-wide">SIMULATION RUNS</h2>
        </div>
      </div>

      {/* Filter/Search placeholder */}
      <div className="px-4 py-3 border-b border-[#1F2937]">
        <button className="w-full flex items-center gap-2 px-3 py-2 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-500 hover:border-gray-600 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          <span>Filter runs...</span>
        </button>
      </div>

      {/* Runs List */}
      <div className="flex-1 overflow-y-auto">
        {runs.map((run) => (
          <button
            key={run.id}
            onClick={() => onSelectRun?.(run.id)}
            className={`w-full px-4 py-3 border-l-2 border-b border-[#1F2937] hover:bg-[#14161B] transition-colors text-left ${
              activeRunId === run.id
                ? 'border-l-blue-500 bg-[#14161B]'
                : 'border-l-transparent'
            }`}
          >
            {/* Run ID */}
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-sm font-semibold text-gray-200">
                {run.id}
              </span>
              <span className="font-mono text-[10px] text-gray-500">
                {run.timestamp}
              </span>
            </div>

            {/* Label and Status */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">{run.label}</span>
              <StatusPill status={run.status} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

