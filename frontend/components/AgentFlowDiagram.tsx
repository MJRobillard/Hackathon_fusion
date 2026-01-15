'use client';

import { ArrowRight, Loader2, Check, X } from 'lucide-react';
import { AGENT_ICONS, AGENT_COLORS } from '@/lib/constants';
import type { AgentStatus, RoutingInfo } from '@/lib/types';

interface AgentFlowDiagramProps {
  routing?: RoutingInfo;
  agentStatuses: AgentStatus[];
  isProcessing: boolean;
}

export function AgentFlowDiagram({ routing, agentStatuses, isProcessing }: AgentFlowDiagramProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'waiting':
        return null;
      case 'running':
        return <Loader2 className="w-5 h-5 animate-spin" />;
      case 'complete':
        return <Check className="w-5 h-5" />;
      case 'failed':
        return <X className="w-5 h-5" />;
      default:
        return null;
    }
  };

  const getAgentStatus = (agentName: string) => {
    return agentStatuses.find((a) => a.agent === agentName);
  };

  const routerStatus = getAgentStatus('router');
  const targetAgent = routing?.agent;
  const targetStatus = targetAgent ? getAgentStatus(targetAgent) : undefined;

  // All possible specialist agents
  const allAgents = ['studies', 'sweep', 'query', 'analysis'];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-sm font-semibold text-gray-200">Agent Workflow</h3>
        {routing && routing.method && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500">Method:</span>
            <span className={routing.method === 'keyword' ? 'text-blue-400' : 'text-purple-400'}>
              {routing.method === 'keyword' ? '⚡ Fast' : '🧠 Smart'}
            </span>
            {routing.confidence && (
              <span className="text-gray-600">
                ({(routing.confidence * 100).toFixed(0)}%)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Flow Diagram */}
      <div className="flex items-start gap-6">
        {/* Router Node */}
        <div className="flex flex-col items-center">
          <div
            className={`relative w-28 h-28 rounded-xl border-2 transition-all duration-300 ${
              routerStatus?.status === 'running'
                ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/50'
                : routerStatus?.status === 'complete'
                ? 'border-emerald-500 bg-emerald-500/10'
                : 'border-gray-700 bg-gray-800/50'
            }`}
          >
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-4xl mb-2">{AGENT_ICONS.router}</div>
              <div className="text-xs font-semibold text-gray-300">Router</div>
              {routerStatus && (
                <div className="mt-1">
                  {getStatusIcon(routerStatus.status)}
                </div>
              )}
            </div>
            {routerStatus?.status === 'running' && (
              <div className="absolute inset-0 rounded-xl border-2 border-blue-500 animate-ping opacity-75"></div>
            )}
          </div>
          {routerStatus?.duration !== undefined && (
            <div className="mt-2 text-[10px] text-gray-500 font-mono">
              {routerStatus.duration < 1000
                ? `${routerStatus.duration}ms`
                : `${(routerStatus.duration / 1000).toFixed(2)}s`}
            </div>
          )}
        </div>

        {/* Arrow with animation */}
        <div className="flex items-center pt-12">
          <div className="relative">
            <ArrowRight
              size={32}
              className={`transition-all duration-500 ${
                routerStatus?.status === 'complete'
                  ? 'text-emerald-500'
                  : routerStatus?.status === 'running'
                  ? 'text-blue-500'
                  : 'text-gray-600'
              }`}
            />
            {routerStatus?.status === 'running' && (
              <div className="absolute inset-0 flex items-center">
                <div className="w-8 h-0.5 bg-blue-500 animate-pulse"></div>
              </div>
            )}
          </div>
        </div>

        {/* Specialist Agents Grid */}
        <div className="flex-1">
          <div className="grid grid-cols-2 gap-3">
            {allAgents.map((agent) => {
              const status = getAgentStatus(agent);
              const isTarget = targetAgent === agent;
              const isActive = status?.status === 'running';
              const isComplete = status?.status === 'complete';
              const isWaiting = !isTarget && !status;

              return (
                <div
                  key={agent}
                  className={`relative rounded-lg border-2 p-4 transition-all duration-300 ${
                    isActive
                      ? 'border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/30 scale-105'
                      : isComplete
                      ? 'border-emerald-500 bg-emerald-500/10'
                      : isTarget && routerStatus?.status === 'complete'
                      ? 'border-yellow-500/50 bg-yellow-500/5'
                      : isWaiting
                      ? 'border-gray-800 bg-gray-900/50 opacity-40'
                      : 'border-gray-700 bg-gray-800/50'
                  }`}
                >
                  {/* Pulse animation for active agent */}
                  {isActive && (
                    <div className="absolute inset-0 rounded-lg border-2 border-blue-500 animate-ping opacity-75"></div>
                  )}

                  <div className="relative flex flex-col items-center">
                    <div className="text-3xl mb-2">
                      {AGENT_ICONS[agent as keyof typeof AGENT_ICONS]}
                    </div>
                    <div
                      className={`text-xs font-semibold capitalize mb-1 ${
                        AGENT_COLORS[agent as keyof typeof AGENT_COLORS]
                      }`}
                    >
                      {agent}
                    </div>
                    
                    {/* Status indicator */}
                    {status && (
                      <div className="flex items-center gap-1 mt-1">
                        {getStatusIcon(status.status)}
                        <span className="text-[10px] text-gray-500 uppercase">
                          {status.status}
                        </span>
                      </div>
                    )}

                    {/* Duration */}
                    {status?.duration !== undefined && (
                      <div className="mt-1 text-[10px] text-gray-500 font-mono">
                        {status.duration < 1000
                          ? `${status.duration}ms`
                          : `${(status.duration / 1000).toFixed(2)}s`}
                      </div>
                    )}

                    {/* Target indicator */}
                    {isTarget && !status && routerStatus?.status === 'complete' && (
                      <div className="mt-2 text-[10px] text-yellow-500 font-semibold animate-pulse">
                        Next →
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Routing Intent */}
          {routing?.intent && (
            <div className="mt-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
              <div className="text-[10px] text-gray-500 uppercase mb-1">Intent</div>
              <div className="text-xs text-gray-300">{routing.intent}</div>
            </div>
          )}
        </div>
      </div>

      {/* Routing Details */}
      {routing?.reasoning && (
        <div className="mt-6 pt-4 border-t border-gray-800">
          <div className="text-[10px] text-gray-500 uppercase mb-2">Routing Reasoning</div>
          <div className="text-xs text-gray-400 italic leading-relaxed">
            {routing.reasoning}
          </div>
        </div>
      )}
    </div>
  );
}

