'use client';

import { useEffect, useRef } from 'react';

interface ThoughtStep {
  timestamp: string;
  agent: string;
  type: 'thinking' | 'decision' | 'tool_call' | 'observation' | 'planning';
  content: string;
  metadata?: Record<string, any>;
}

interface AgentThinkingPanelProps {
  thoughts?: ThoughtStep[];
  autoScroll?: boolean;
}

const ThoughtCard = ({ thought }: { thought: ThoughtStep }) => {
  const typeConfig = {
    thinking: {
      icon: '🤔',
      label: 'THINKING',
      bgColor: 'bg-blue-500/5',
      borderColor: 'border-blue-500/30',
      textColor: 'text-blue-400',
    },
    decision: {
      icon: '⚡',
      label: 'DECISION',
      bgColor: 'bg-purple-500/5',
      borderColor: 'border-purple-500/30',
      textColor: 'text-purple-400',
    },
    tool_call: {
      icon: '🔧',
      label: 'TOOL CALL',
      bgColor: 'bg-emerald-500/5',
      borderColor: 'border-emerald-500/30',
      textColor: 'text-emerald-400',
    },
    observation: {
      icon: '👁️',
      label: 'OBSERVATION',
      bgColor: 'bg-amber-500/5',
      borderColor: 'border-amber-500/30',
      textColor: 'text-amber-400',
    },
    planning: {
      icon: '📋',
      label: 'PLANNING',
      bgColor: 'bg-cyan-500/5',
      borderColor: 'border-cyan-500/30',
      textColor: 'text-cyan-400',
    },
  };

  const config = typeConfig[thought.type];

  return (
    <div className={`p-3 rounded border ${config.borderColor} ${config.bgColor} transition-all hover:bg-opacity-80`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">{config.icon}</span>
          <div>
            <span className={`text-[10px] font-mono font-bold ${config.textColor} uppercase tracking-wider`}>
              {config.label}
            </span>
            <span className="text-[10px] text-gray-500 ml-2">
              {thought.agent}
            </span>
          </div>
        </div>
        <span className="text-[9px] text-gray-600 font-mono">
          {thought.timestamp}
        </span>
      </div>

      {/* Content */}
      <p className="text-xs text-gray-300 leading-relaxed mb-2">
        {thought.content}
      </p>

      {/* Metadata */}
      {thought.metadata && Object.keys(thought.metadata).length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-700">
          <details className="group">
            <summary className="text-[10px] text-gray-500 cursor-pointer hover:text-gray-400">
              View Details
            </summary>
            <pre className="text-[9px] text-gray-600 font-mono mt-2 overflow-x-auto">
              {JSON.stringify(thought.metadata, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
};

export function AgentThinkingPanel({ thoughts = [], autoScroll = true }: AgentThinkingPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thoughts, autoScroll]);

  return (
    <div className="h-full bg-[#0A0B0D] border border-[#1F2937] rounded flex flex-col">
      {/* Header */}
      <div className="h-10 border-b border-[#1F2937] flex items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <h3 className="text-xs font-semibold text-gray-300 tracking-wide">AGENT REASONING</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-gray-500">
            {thoughts.length} {thoughts.length === 1 ? 'step' : 'steps'}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {thoughts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <svg className="w-12 h-12 text-gray-600 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              <p className="text-sm text-gray-500">Waiting for agent thoughts...</p>
              <p className="text-xs text-gray-600 mt-1">Agent reasoning will appear here during execution</p>
            </div>
          </div>
        ) : (
          <>
            {thoughts.map((thought, index) => (
              <ThoughtCard key={index} thought={thought} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  );
}

