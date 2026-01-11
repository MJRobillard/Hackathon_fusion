'use client';

interface AgentCardData {
  id: string;
  name: string;
  status: 'waiting' | 'running' | 'complete' | 'failed';
  message?: string;
}

interface AgentPanelProps {
  agents?: AgentCardData[];
  currentTask?: string;
}

const AgentCard = ({ agent }: { agent: AgentCardData }) => {
  const statusConfig = {
    waiting: {
      color: 'text-gray-500',
      bgColor: 'bg-[#14161B]',
      borderColor: 'border-[#1F2937]',
      icon: null,
    },
    running: {
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/5',
      borderColor: 'border-blue-500/30',
      icon: (
        <div className="relative flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse-dot" />
          <div className="absolute w-2 h-2 rounded-full bg-blue-500 animate-pulse-ring" />
        </div>
      ),
    },
    complete: {
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/5',
      borderColor: 'border-emerald-500/30',
      icon: (
        <svg className="w-4 h-4 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
            clipRule="evenodd"
          />
        </svg>
      ),
    },
    failed: {
      color: 'text-red-400',
      bgColor: 'bg-red-500/5',
      borderColor: 'border-red-500/30',
      icon: (
        <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
            clipRule="evenodd"
          />
        </svg>
      ),
    },
  };

  const config = statusConfig[agent.status];

  return (
    <div
      className={`flex-1 p-4 rounded border ${config.borderColor} ${config.bgColor} transition-all`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
            {agent.name}
          </h3>
        </div>
        {config.icon && <div className="mt-0.5">{config.icon}</div>}
      </div>

      {/* Status message */}
      <div className="min-h-[40px]">
        {agent.message && (
          <p className={`text-xs ${config.color} leading-relaxed`}>
            {agent.message}
          </p>
        )}
      </div>
    </div>
  );
};

const defaultAgents: AgentCardData[] = [
  {
    id: 'parser',
    name: 'Parser Agent',
    status: 'complete',
    message: 'Validated geometry.xml',
  },
  {
    id: 'simulation',
    name: 'Simulation Core',
    status: 'running',
    message: 'Executing Monte Carlo...',
  },
  {
    id: 'validation',
    name: 'Validation Gate',
    status: 'waiting',
    message: 'Waiting for results...',
  },
];

export function AgentPanel({ 
  agents = defaultAgents,
  currentTask = 'Flux Optimization Layer (Node-4)'
}: AgentPanelProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-300 tracking-wide mb-1">
            AGENT ORCHESTRATION
          </h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Current Task:</span>
            <span className="text-xs text-blue-400 font-mono">{currentTask}</span>
          </div>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="flex gap-4">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>

      {/* Workflow Timeline (Optional Visual) */}
      <div className="flex items-center gap-2 px-4">
        {agents.map((agent, index) => (
          <div key={agent.id} className="flex items-center flex-1">
            <div
              className={`flex-1 h-8 rounded flex items-center justify-center text-[10px] font-mono font-semibold border ${
                agent.status === 'complete'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : agent.status === 'running'
                  ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                  : 'bg-gray-800/30 border-gray-700 text-gray-500'
              }`}
            >
              {agent.name.split(' ')[0]}
            </div>
            {index < agents.length - 1 && (
              <svg className="w-4 h-4 text-gray-600 mx-1" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

