'use client';

import { useState } from 'react';
import type { RoutingInfo } from '@/lib/types';

interface AgentCardData {
  id: string;
  name: string;
  status: 'waiting' | 'running' | 'complete' | 'failed';
  message?: string;
  tools?: string[];
}

interface AgentPanelProps {
  agents?: AgentCardData[];
  currentTask?: string;
  routing?: RoutingInfo;
}

// Tool definitions for each agent based on query_graph.py
const AGENT_TOOLS: Record<string, string[]> = {
  router: [],
  studies: ['submit_study', 'get_run_by_id', 'validate_physics'],
  sweep: ['generate_sweep', 'compare_runs', 'validate_physics'],
  query: ['query_results', 'get_study_statistics', 'get_recent_runs'],
  analysis: ['compare_runs', 'get_run_by_id'],
  rag_copilot: [],
  finalize: [],
  openmc: ['run_simulation', 'extract_results'],
};

const GraphFlowDiagram = ({ routing, agents }: { routing?: AgentPanelProps['routing']; agents?: AgentCardData[] }) => {
  const getAgentStatus = (nodeId: string): 'waiting' | 'running' | 'complete' | 'failed' => {
    const agent = agents?.find((a) => a.id.toLowerCase() === nodeId.toLowerCase());
    return agent?.status || 'waiting';
  };

  const getNodeStatus = (nodeId: string) => {
    if (nodeId === 'route') {
      return routing ? (routing.agent ? 'complete' : 'running') : 'waiting';
    }
    if (nodeId === 'openmc') {
      const studiesStatus = getAgentStatus('studies');
      const sweepStatus = getAgentStatus('sweep');
      if (studiesStatus === 'running' || sweepStatus === 'running') return 'running';
      if (studiesStatus === 'complete' || sweepStatus === 'complete') return 'complete';
      return 'waiting';
    }
    if (nodeId === 'finalize') {
      return agents?.some((a) => a.status === 'complete') ? 'complete' : 'waiting';
    }
    return getAgentStatus(nodeId);
  };

  const statusColors = {
    waiting: 'border-gray-700 bg-gray-800/30 text-gray-500',
    running: 'border-blue-500 bg-blue-500/10 text-blue-400 shadow-lg shadow-blue-500/20',
    complete: 'border-emerald-500 bg-emerald-500/10 text-emerald-400',
    failed: 'border-red-500 bg-red-500/10 text-red-400',
  };

  const isActiveRoute = (agentId: string) => {
    return routing?.agent?.toLowerCase() === agentId.toLowerCase();
  };

  return (
    <div className="p-3 bg-[#0F1115] border border-[#1F2937] rounded">
      <div className="flex items-center gap-2 mb-3">
        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
        <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">Query Graph Flow</h4>
      </div>
      
      {/* Compact Left-to-Right Flow */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2" style={{ minHeight: '80px' }}>
        {/* Route */}
        <div className={`flex-shrink-0 px-2.5 py-1.5 rounded border text-[9px] font-mono font-semibold ${statusColors[getNodeStatus('route')]}`}>
          route
        </div>
        
        <svg className="w-3 h-3 text-gray-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>

        {/* Conditional */}
        <div className="flex-shrink-0 px-2 py-1 bg-purple-500/10 border border-purple-500/30 rounded text-[8px] text-purple-400 font-mono">
          cond
        </div>

        <svg className="w-3 h-3 text-gray-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>

        {/* Specialist Agents in compact layout */}
        <div className="flex items-center gap-1 flex-shrink-0">
          {['studies', 'sweep', 'query', 'analysis'].map((agentId, idx) => {
            const status = getNodeStatus(agentId);
            const active = isActiveRoute(agentId);
            return (
              <div key={agentId} className="flex items-center gap-0.5">
                <div className={`px-2 py-1 rounded border text-[9px] font-mono font-semibold ${
                  active ? statusColors[status] : statusColors['waiting']
                }`}>
                  {agentId}
                </div>
                {idx < 3 && <span className="text-gray-600 text-[8px]">|</span>}
              </div>
            );
          })}
        </div>

        <svg className="w-3 h-3 text-gray-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>

        {/* OpenMC (compact, shows connection to studies/sweep) */}
        <div className="relative flex-shrink-0">
          <div className={`px-2.5 py-1.5 rounded border text-[9px] font-mono font-semibold ${statusColors[getNodeStatus('openmc')]}`}>
            ⚛️ OpenMC
          </div>
          {/* Small tool connection indicator */}
          <div className="absolute -top-1 -left-1 w-2 h-2 bg-purple-500/50 rounded-full border border-purple-500" title="Tool: studies/sweep → OpenMC" />
        </div>

        <svg className="w-3 h-3 text-gray-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>

        {/* Analysis */}
        <div className={`flex-shrink-0 px-2.5 py-1.5 rounded border text-[9px] font-mono font-semibold ${statusColors[getNodeStatus('analysis')]}`}>
          analysis
        </div>

        <svg className="w-3 h-3 text-gray-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>

        {/* Finalize */}
        <div className={`flex-shrink-0 px-2.5 py-1.5 rounded border text-[9px] font-mono font-semibold ${statusColors[getNodeStatus('finalize')]}`}>
          finalize
        </div>

        <svg className="w-3 h-3 text-gray-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>

        {/* END */}
        <div className="flex-shrink-0 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-[9px] text-gray-500 font-mono">
          END
        </div>
      </div>

      {/* Compact legend/info */}
      <div className="mt-2 pt-2 border-t border-[#1F2937]">
        <details className="group">
          <summary className="text-[9px] text-gray-500 cursor-pointer hover:text-gray-400 font-mono">
            Flow: route → cond → [studies|sweep|query|analysis] → OpenMC → analysis → finalize → END
          </summary>
          <div className="mt-1.5 text-[8px] text-gray-600 font-mono space-y-0.5 pl-3">
            <div>• Conditional routing to specialist agents</div>
            <div>• studies/sweep use OpenMC tool</div>
            <div>• All paths converge to analysis → finalize</div>
          </div>
        </details>
      </div>
    </div>
  );
};

const AgentCard = ({ agent, routing }: { agent: AgentCardData; routing?: AgentPanelProps['routing'] }) => {
  const [showTools, setShowTools] = useState(false);
  const tools = agent.tools || AGENT_TOOLS[agent.id.toLowerCase()] || [];
  const isActive = routing?.agent?.toLowerCase() === agent.id.toLowerCase() || 
                   (agent.id.toLowerCase() === 'router' && routing);

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
      className={`flex-1 p-4 rounded border ${config.borderColor} ${config.bgColor} transition-all ${
        isActive ? 'ring-2 ring-blue-500/50' : ''
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2 flex-1">
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <div className="flex-1 min-w-0">
            <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
              {agent.name}
            </h3>
            {isActive && routing?.intent && (
              <p className="text-[10px] text-blue-400 mt-0.5">Intent: {routing.intent}</p>
            )}
          </div>
        </div>
        {config.icon && <div className="mt-0.5 flex-shrink-0">{config.icon}</div>}
      </div>

      {/* Status message */}
      <div className="min-h-[40px] mb-2">
        {agent.message && (
          <p className={`text-xs ${config.color} leading-relaxed`}>
            {agent.message}
          </p>
        )}
      </div>

      {/* Tools */}
      {tools.length > 0 && (
        <div className="mt-2 pt-2 border-t border-[#1F2937]">
          <button
            onClick={() => setShowTools(!showTools)}
            className="flex items-center gap-1.5 text-[10px] text-gray-500 hover:text-gray-400 transition-colors w-full"
          >
            <svg
              className={`w-3 h-3 transition-transform ${showTools ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            <span className="font-mono">
              {tools.length} {tools.length === 1 ? 'tool' : 'tools'}
            </span>
          </button>
          {showTools && (
            <div className="mt-2 space-y-1 pl-4">
              {tools.map((tool) => (
                <div key={tool} className="text-[10px] font-mono text-gray-600">
                  • {tool}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const defaultAgents: AgentCardData[] = [
  {
    id: 'parser',
    name: 'Intent Classifier',
    status: 'complete',
    message: 'Routed to Studies Agent',
  },
  {
    id: 'studies',
    name: 'Study Executor',
    status: 'running',
    message: 'Executing simulation...',
  },
  {
    id: 'analyzer',
    name: 'Results Analyzer',
    status: 'waiting',
    message: 'Waiting for results...',
  },
];

export function AgentPanel({ 
  agents = defaultAgents,
  currentTask = 'Waiting for command...',
  routing,
}: AgentPanelProps) {
  // Enhance agents with tools from AGENT_TOOLS
  const enhancedAgents = agents.map((agent) => ({
    ...agent,
    tools: agent.tools || AGENT_TOOLS[agent.id.toLowerCase()] || [],
  }));

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
            <span className="text-xs text-blue-400 font-mono max-w-md truncate">{currentTask}</span>
          </div>
        </div>
      </div>

      {/* Query Graph Flow Diagram */}
      <GraphFlowDiagram routing={routing} agents={enhancedAgents} />
    </div>
  );
}
