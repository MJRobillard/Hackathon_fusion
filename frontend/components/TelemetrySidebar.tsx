'use client';

interface TelemetryMetrics {
  keff?: number;
  keff_std?: number;
  convergenceRate?: number;
  iteration?: number;
  totalIterations?: number;
  interlocks?: {
    geometryCheck: 'passed' | 'failed' | 'pending';
    crossSection: 'passed' | 'failed' | 'pending';
    convergenceVariance: 'passed' | 'alert' | 'failed';
  };
  resources?: {
    cores: number;
    coresUsage: number;
    agentCost?: number;
  };
}

interface TelemetrySidebarProps {
  metrics?: TelemetryMetrics;
}

const MetricCard = ({
  title,
  value,
  unit,
  uncertainty,
  status,
}: {
  title: string;
  value: number | string;
  unit?: string;
  uncertainty?: string;
  status?: 'nominal' | 'alert' | 'warning';
}) => {
  const statusColors = {
    nominal: 'text-emerald-400 border-emerald-500/30',
    alert: 'text-amber-400 border-amber-500/30',
    warning: 'text-red-400 border-red-500/30',
  };

  const statusLabels = {
    nominal: 'NOMINAL',
    alert: 'ALERT',
    warning: 'WARNING',
  };

  return (
    <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-semibold text-gray-500 tracking-wider uppercase">
          {title}
        </h3>
        {status && (
          <span
            className={`px-2 py-0.5 text-[8px] font-mono font-bold border rounded ${statusColors[status]}`}
          >
            [{statusLabels[status]}]
          </span>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-mono font-bold text-gray-100">
          {typeof value === 'number' ? value.toFixed(5) : value}
        </span>
        {unit && <span className="text-xs text-gray-500">{unit}</span>}
      </div>
      {uncertainty && (
        <p className="mt-1 text-xs text-gray-500 font-mono">
          ± {uncertainty}
        </p>
      )}
    </div>
  );
};

const ProgressBar = ({
  label,
  current,
  total,
  percentage,
}: {
  label: string;
  current: number;
  total: number;
  percentage: number;
}) => {
  return (
    <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
      <h3 className="text-[10px] font-semibold text-gray-500 tracking-wider uppercase mb-3">
        {label}
      </h3>
      <div className="space-y-2">
        <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400 font-mono">
            Iteration {current}/{total}
          </span>
          <span className="text-blue-400 font-mono font-semibold">
            {percentage}% Complete
          </span>
        </div>
      </div>
    </div>
  );
};

const InterlockItem = ({
  label,
  status,
}: {
  label: string;
  status: 'passed' | 'alert' | 'failed' | 'pending';
}) => {
  const statusConfig = {
    passed: {
      icon: '●',
      color: 'text-emerald-500',
      label: 'PASSED',
    },
    alert: {
      icon: '●',
      color: 'text-amber-500',
      label: 'ALERT',
    },
    failed: {
      icon: '●',
      color: 'text-red-500',
      label: 'FAILED',
    },
    pending: {
      icon: '○',
      color: 'text-gray-600',
      label: 'PENDING',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1F2937] last:border-0">
      <span className="text-xs text-gray-300">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`text-sm ${config.color}`}>{config.icon}</span>
        <span className={`text-[10px] font-mono font-semibold ${config.color}`}>
          {config.label}
        </span>
      </div>
    </div>
  );
};

const defaultMetrics: TelemetryMetrics = {
  keff: 1.00245,
  keff_std: 0.00012,
  convergenceRate: 75,
  iteration: 42,
  totalIterations: 100,
  interlocks: {
    geometryCheck: 'passed',
    crossSection: 'passed',
    convergenceVariance: 'alert',
  },
  resources: {
    cores: 128,
    coresUsage: 82,
    agentCost: 4.22,
  },
};

export function TelemetrySidebar({ metrics = defaultMetrics }: TelemetrySidebarProps) {
  return (
    <div className="w-72 h-full bg-[#0A0B0D] border-l border-[#1F2937] flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="h-14 border-b border-[#1F2937] flex items-center px-4">
        <h2 className="text-sm font-semibold text-gray-300 tracking-wide">LIVE TELEMETRY</h2>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        {/* Live Metrics */}
        <div className="space-y-3">
          <MetricCard
            title="Effective Multiplication (K-EFF)"
            value={metrics.keff || 0}
            uncertainty={metrics.keff_std?.toFixed(5)}
            status="nominal"
          />
          
          <ProgressBar
            label="Convergence Rate"
            current={metrics.iteration || 0}
            total={metrics.totalIterations || 100}
            percentage={metrics.convergenceRate || 0}
          />
        </div>

        {/* Interlocks */}
        <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
          <h3 className="text-[10px] font-semibold text-gray-500 tracking-wider uppercase mb-3">
            INTERLOCKS
          </h3>
          <div className="space-y-0">
            <InterlockItem
              label="Geometry Check"
              status={metrics.interlocks?.geometryCheck || 'pending'}
            />
            <InterlockItem
              label="Cross Section"
              status={metrics.interlocks?.crossSection || 'pending'}
            />
            <InterlockItem
              label="Convergence Variance"
              status={metrics.interlocks?.convergenceVariance || 'pending'}
            />
          </div>
        </div>

        {/* Resource Allocation */}
        <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
          <h3 className="text-[10px] font-semibold text-gray-500 tracking-wider uppercase mb-3">
            RESOURCE ALLOCATION
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">CPU</span>
              <span className="text-xs font-mono text-gray-200">
                {metrics.resources?.cores} Cores
              </span>
            </div>
            <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500"
                style={{ width: `${metrics.resources?.coresUsage || 0}%` }}
              />
            </div>
            <div className="flex items-center justify-between pt-2 border-t border-[#1F2937]">
              <span className="text-xs text-gray-400">Agent Cost</span>
              <span className="text-xs font-mono text-emerald-400">
                ${metrics.resources?.agentCost?.toFixed(2) || '0.00'}
              </span>
            </div>
          </div>
        </div>

        {/* Export Button */}
        <button className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded transition-colors flex items-center justify-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          EXPORT ARTIFACTS
        </button>
      </div>
    </div>
  );
}

