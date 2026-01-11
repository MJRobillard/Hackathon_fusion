'use client';

interface StatusFooterProps {
  systemStatus?: 'ready' | 'busy' | 'error';
  version?: string;
  cores?: number;
  coreUsage?: number;
  latency?: number;
  tokenConsumption?: number;
  eta?: string;
}

export function StatusFooter({
  systemStatus = 'ready',
  version = 'OpenMC v0.14.0',
  cores = 128,
  coreUsage = 0,
  latency = 42,
  tokenConsumption = 1.2,
  eta = '14:48:00',
}: StatusFooterProps) {
  const statusConfig = {
    ready: { label: 'SYSTEM READY', color: 'text-emerald-500', dotColor: 'bg-emerald-500' },
    busy: { label: 'PROCESSING', color: 'text-blue-500', dotColor: 'bg-blue-500' },
    error: { label: 'ERROR', color: 'text-red-500', dotColor: 'bg-red-500' },
  };

  const config = statusConfig[systemStatus];

  return (
    <footer className="h-8 bg-[#050607] border-t border-[#111827] flex items-center justify-between px-4 text-[10px] font-mono text-gray-400">
      {/* Left side */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="relative flex items-center">
            <div className={`w-2 h-2 rounded-full ${config.dotColor} animate-pulse-dot`} />
            {systemStatus === 'busy' && (
              <div className={`absolute w-2 h-2 rounded-full ${config.dotColor} animate-pulse-ring`} />
            )}
          </div>
          <span className={`${config.color} font-semibold`}>{config.label}</span>
        </div>
        <span className="text-gray-500">|</span>
        <span>{version}</span>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {cores > 0 && (
          <>
            <span>CPU ({cores} Cores @ {coreUsage}%)</span>
            <span className="text-gray-500">|</span>
          </>
        )}
        <span>LATENCY: {latency}ms</span>
        <span className="text-gray-500">|</span>
        <span>TOKEN CONSUMPTION: {tokenConsumption}k/min</span>
        <span className="text-gray-500">|</span>
        <span>EST: {eta}</span>
      </div>
    </footer>
  );
}

