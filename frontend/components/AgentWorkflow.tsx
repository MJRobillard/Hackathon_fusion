'use client';

import { ArrowRight, Loader2 } from 'lucide-react';
import { AGENT_ICONS, AGENT_COLORS, STATUS_COLORS } from '@/lib/constants';
import type { AgentStatus, RoutingInfo } from '@/lib/types';

interface AgentWorkflowProps {
  routing?: RoutingInfo;
  agentStatuses: AgentStatus[];
  isProcessing: boolean;
}

export function AgentWorkflow({ routing, agentStatuses, isProcessing }: AgentWorkflowProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'waiting':
        return '⏳';
      case 'running':
        return <Loader2 className="inline animate-spin" size={14} />;
      case 'complete':
        return '✓';
      case 'failed':
        return '✗';
      default:
        return '•';
    }
  };

  const renderAgentCard = (agent: AgentStatus) => {
    const statusColor = STATUS_COLORS[agent.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.waiting;
    const agentColor = AGENT_COLORS[agent.agent as keyof typeof AGENT_COLORS] || AGENT_COLORS.router;

    return (
      <div
        key={agent.agent}
        className={`flex-1 min-w-[140px] p-3 rounded-lg border transition-all ${
          agent.status === 'running'
            ? 'bg-blue-600/10 border-blue-500/50 shadow-lg shadow-blue-500/20'
            : agent.status === 'complete'
            ? 'bg-emerald-600/10 border-emerald-500/30'
            : agent.status === 'failed'
            ? 'bg-red-600/10 border-red-500/30'
            : 'bg-gray-800/50 border-gray-700/50'
        }`}
      >
        <div className="flex items-center gap-2 mb-2">
          <span className="text-2xl">{AGENT_ICONS[agent.agent]}</span>
          <div className="flex-1">
            <div className={`text-sm font-semibold ${agentColor} capitalize`}>
              {agent.agent}
            </div>
            <div className={`text-[10px] font-mono uppercase ${statusColor}`}>
              {agent.status}
            </div>
          </div>
          <span className={`text-lg ${statusColor}`}>
            {getStatusIcon(agent.status)}
          </span>
        </div>

        {agent.duration && (
          <div className="text-[10px] text-gray-500 font-mono">
            {agent.duration < 1000
              ? `${agent.duration}ms`
              : `${(agent.duration / 1000).toFixed(2)}s`}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-sm font-semibold text-gray-200">Agent Workflow</h3>
        {routing && (
          <div className="ml-auto flex items-center gap-2 text-xs">
            <span className="text-gray-500">Method:</span>
            <span className={routing.method === 'keyword' ? 'text-blue-400' : 'text-purple-400'}>
              {routing.method === 'keyword' ? '⚡ Fast Routing' : '🧠 Smart Routing'}
            </span>
          </div>
        )}
      </div>

      {/* Agent Cards */}
      <div className="flex items-center gap-3 flex-wrap lg:flex-nowrap">
        {agentStatuses.map((agent, index) => (
          <div key={agent.agent} className="flex items-center gap-3">
            {renderAgentCard(agent)}
            {index < agentStatuses.length - 1 && (
              <ArrowRight size={20} className="text-gray-600 hidden lg:block" />
            )}
          </div>
        ))}
      </div>

      {/* Routing Details */}
      {routing && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <div className="text-xs text-gray-400 space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">Intent:</span>
              <span className="text-gray-300">{routing.intent}</span>
            </div>
            {routing.confidence && (
              <div className="flex justify-between">
                <span className="text-gray-500">Confidence:</span>
                <span className="text-gray-300">{(routing.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
            {routing.reasoning && (
              <div className="mt-2 text-[11px] text-gray-500 italic">
                {routing.reasoning}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

