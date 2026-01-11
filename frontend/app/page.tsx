'use client';

import { useState, useEffect, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MissionControlTopBar } from '@/components/MissionControlTopBar';
import { ToolAgentConfigSidebar } from '@/components/ToolAgentConfigSidebar';
import { AgentPanel } from '@/components/AgentPanel';
import { MissionControlLogs } from '@/components/MissionControlLogs';
import { TelemetrySidebar } from '@/components/TelemetrySidebar';
import { StatusFooter } from '@/components/StatusFooter';
import { CommandPalette } from '@/components/CommandPalette';
import { DatabasePanel } from '@/components/DatabasePanel';
import { HealthPanel } from '@/components/HealthPanel';
import { AgentThinkingPanel } from '@/components/AgentThinkingPanel';
import RAGCopilotPanel from '@/components/RAGCopilotPanel';
import RAGAgentCard from '@/components/RAGAgentCard';
import GlobalTerminal from '@/components/GlobalTerminal';
import OpenMCBackendPanel from '@/components/OpenMCBackendPanel';
import { AnalyticsPanel } from '@/components/AnalyticsPanel';
import { useEventStream } from '@/hooks/useEventStream';
import { useQueryHistory } from '@/hooks/useQueryHistory';
import { apiService } from '@/lib/api';
import { REFRESH_INTERVALS } from '@/lib/constants';
import type { QueryData } from '@/lib/types';

export default function Home() {
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showDatabase, setShowDatabase] = useState(false);
  const [showHealth, setShowHealth] = useState(false);
  const [showRAGPanel, setShowRAGPanel] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [terminalMode, setTerminalMode] = useState<'stream' | 'openmc'>('stream');
  const [showAgentThinking, setShowAgentThinking] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const queryClient = useQueryClient();

  const { queries, addQuery, updateQuery, getQuery } = useQueryHistory();
  const { logs, agentStatuses, agentThoughts, isConnected, clearLogs } = useEventStream(activeQueryId);

  // Fetch statistics
  const { data: statistics } = useQuery({
    queryKey: ['statistics'],
    queryFn: () => apiService.getStatistics(),
    refetchInterval: REFRESH_INTERVALS.statistics,
  });

  // Poll active query status
  const { data: activeQueryData } = useQuery({
    queryKey: ['query', activeQueryId],
    queryFn: () => apiService.getQuery(activeQueryId!),
    enabled: !!activeQueryId && isProcessing,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        setIsProcessing(false);
        return false;
      }
      return REFRESH_INTERVALS.activeQuery;
    },
  });

  // Update query in history when data changes
  useEffect(() => {
    if (activeQueryData && activeQueryId) {
      updateQuery(activeQueryId, activeQueryData);
      // Auto-select run_id from results if available
      if (activeQueryData.results?.run_id && !selectedRunId) {
        setSelectedRunId(activeQueryData.results.run_id);
      }
      if (activeQueryData.results?.run_ids && selectedRunIds.length === 0) {
        setSelectedRunIds(activeQueryData.results.run_ids);
      }
    }
  }, [activeQueryData, activeQueryId, updateQuery, selectedRunId, selectedRunIds]);

  // Submit query mutation
  const submitMutation = useMutation({
    mutationFn: ({ query, useLLM }: { query: string; useLLM: boolean }) =>
      apiService.submitQuery(query, useLLM),
    onSuccess: (data) => {
      const newQuery: QueryData = {
        query_id: data.query_id,
        query: '',
        status: data.status,
        created_at: new Date().toISOString(),
      };

      addQuery(newQuery);
      setActiveQueryId(data.query_id);
      setIsProcessing(true);
      clearLogs();
      setShowCommandPalette(false);

      queryClient.invalidateQueries({ queryKey: ['query', data.query_id] });
    },
    onError: (error) => {
      console.error('Failed to submit query:', error);
      setIsProcessing(false);
    },
  });

  const handleSubmitQuery = (query: string, useLLM: boolean) => {
    submitMutation.mutate({ query, useLLM });
  };

  const handleSelectQuery = (queryId: string) => {
    const query = getQuery(queryId);
    if (query) {
      setActiveQueryId(queryId);

      if (query.status === 'processing' || query.status === 'queued') {
        setIsProcessing(true);
      } else {
        setIsProcessing(false);
      }
    }
  };

  const handlePlay = () => {
    setShowCommandPalette(true);
  };

  const handleStop = () => {
    setIsProcessing(false);
  };

  const handleReset = () => {
    setActiveQueryId(null);
    setIsProcessing(false);
    clearLogs();
  };

  const activeQuery = activeQueryId ? getQuery(activeQueryId) : undefined;

  // Convert queries to runs format for sidebar
  const runs = useMemo(() => {
    return queries.map((q, index) => ({
      id: q.query_id.substring(0, 8).toUpperCase(),
      status: (q.status === 'completed'
        ? 'success'
        : q.status === 'failed'
        ? 'failed'
        : q.status === 'processing'
        ? 'running'
        : 'warning') as 'running' | 'failed' | 'success' | 'warning',
      label: q.routing?.agent || 'Query',
      timestamp: new Date(q.created_at).toLocaleTimeString(),
    }));
  }, [queries]);

  // Convert agent statuses to agent panel format
  const agents = useMemo(() => {
    const statusMap = agentStatuses.reduce((acc, status) => {
      acc[status.agent] = status.status;
      return acc;
    }, {} as Record<string, string>);

    type AgentStatus = 'waiting' | 'running' | 'complete' | 'failed';

    const baseAgents = [
      {
        id: 'parser',
        name: 'Intent Classifier',
        status: (statusMap['router'] || 'waiting') as AgentStatus,
        message: statusMap['router'] === 'complete'
          ? `Routed to ${activeQuery?.routing?.agent || 'agent'}`
          : statusMap['router'] === 'running'
          ? 'Analyzing query intent...'
          : 'Waiting for query...',
      },
      {
        id: 'executor',
        name: 'Study Executor',
        status: (statusMap['studies'] || statusMap['sweep'] || 'waiting') as AgentStatus,
        message: statusMap['studies'] === 'running' || statusMap['sweep'] === 'running'
          ? 'Executing simulation...'
          : statusMap['studies'] === 'complete' || statusMap['sweep'] === 'complete'
          ? 'Simulation complete'
          : 'Waiting for routing...',
      },
      {
        id: 'analyzer',
        name: 'Results Analyzer',
        status: (statusMap['analysis'] || 'waiting') as AgentStatus,
        message: statusMap['analysis'] === 'running'
          ? 'Analyzing results...'
          : statusMap['analysis'] === 'complete'
          ? 'Analysis complete'
          : 'Waiting for results...',
      },
    ];

    // Add RAG Copilot agent if routed to rag_copilot
    if (activeQuery?.routing?.agent === 'rag_copilot') {
      baseAgents.push({
        id: 'rag_copilot',
        name: 'RAG Copilot',
        status: (statusMap['rag'] || 'running') as AgentStatus,
        message: statusMap['rag'] === 'running'
          ? 'Analyzing with RAG...'
          : statusMap['rag'] === 'complete'
          ? 'RAG analysis complete'
          : 'Searching documents...',
      });
    }

    return baseAgents;
  }, [agentStatuses, activeQuery]);

  // Convert logs to mission control format
  const missionControlLogs = useMemo(() => {
    return logs.map(log => ({
      timestamp: new Date(log.timestamp).toLocaleTimeString(),
      level: log.level === 'success' ? 'INFO' : log.level.toUpperCase() as any,
      message: log.message,
    }));
  }, [logs]);

  // Extract telemetry from active query results
  const telemetry = useMemo(() => {
    if (!activeQuery?.results) return undefined;

    return {
      keff: activeQuery.results.keff,
      keff_std: activeQuery.results.keff_std,
      convergenceRate: 75,
      iteration: activeQuery.results.batches || 42,
      totalIterations: 100,
      run_id: activeQuery.results.run_id,
      interlocks: {
        geometryCheck: 'passed' as const,
        crossSection: 'passed' as const,
        convergenceVariance: activeQuery.results.keff_std && activeQuery.results.keff_std > 0.0005
          ? 'alert' as const
          : 'passed' as const,
      },
      resources: {
        cores: 128,
        coresUsage: isProcessing ? 82 : 0,
        agentCost: 4.22,
      },
    };
  }, [activeQuery, isProcessing]);

  return (
    <div className="h-screen w-screen bg-[#0A0B0D] flex flex-col overflow-hidden">
      {/* Modals */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
        onSubmit={handleSubmitQuery}
        isProcessing={isProcessing}
      />
      <DatabasePanel
        isOpen={showDatabase}
        onClose={() => setShowDatabase(false)}
      />
      <HealthPanel
        isOpen={showHealth}
        onClose={() => setShowHealth(false)}
      />

      {/* Top Bar */}
      <MissionControlTopBar
        projectName="fusion-core-alpha-09"
        onPlay={handlePlay}
        onStop={handleStop}
        onReset={handleReset}
        onCommandPalette={() => setShowCommandPalette(true)}
        onOpenDatabase={() => setShowDatabase(true)}
        onOpenHealth={() => setShowHealth(true)}
        isProcessing={isProcessing}
      />

      {/* Main Content Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Tool & Agent Config */}
        <ToolAgentConfigSidebar />

        {/* Center Panel */}
        <div className="flex-1 flex flex-col gap-4 p-4 overflow-hidden">
          {/* Agent Orchestration */}
          <div className="space-y-4">
            <AgentPanel
              agents={agents}
              currentTask={activeQuery?.query || 'Waiting for command...'}
            />

            {/* Agent thinking / tool calls */}
            <div className="px-2">
              <button
                onClick={() => setShowAgentThinking((v) => !v)}
                className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
              >
                {showAgentThinking ? '▾ Hide agent reasoning' : '▸ Show agent reasoning'}
              </button>
            </div>

            {showAgentThinking && (
              <div className="px-2 h-64">
                <AgentThinkingPanel thoughts={agentThoughts} autoScroll={true} />
              </div>
            )}

            {/* RAG Copilot Indicator */}
            {activeQuery?.routing?.agent === 'rag_copilot' && (
              <div className="px-4">
                <RAGAgentCard
                  status={isProcessing ? 'running' : activeQuery.status === 'completed' ? 'complete' : 'waiting'}
                  intent={activeQuery.routing?.intent}
                />
              </div>
            )}
          </div>

          {/* Backend Terminal / OpenMC Panel - Full Width */}
          <div className="flex-1 flex flex-col gap-2 min-h-0">
            {/* Terminal Mode Toggle */}
            <div className="flex items-center gap-2 px-2">
              <div className="flex gap-1 bg-gray-900 rounded-lg p-1 border border-gray-800">
                <button
                  onClick={() => setTerminalMode('stream')}
                  className={`px-4 py-1.5 text-xs font-medium rounded transition-colors ${
                    terminalMode === 'stream'
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  📡 Backend Stream
                </button>
                <button
                  onClick={() => setTerminalMode('openmc')}
                  className={`px-4 py-1.5 text-xs font-medium rounded transition-colors ${
                    terminalMode === 'openmc'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  ⚛️ OpenMC Engine
                </button>
              </div>
              <div className="flex-1"></div>
              <div className="text-xs text-gray-500">
                {terminalMode === 'stream' 
                  ? 'Streaming all backend output' 
                  : 'Direct OpenMC simulation control'}
              </div>
            </div>

            {/* Terminal Content */}
            <div className="flex-1 min-h-0">
              {terminalMode === 'stream' ? (
                <GlobalTerminal autoScroll={true} maxLines={5000} />
              ) : (
                <OpenMCBackendPanel />
              )}
            </div>
          </div>
        </div>

        {/* Right Sidebar: Telemetry / Analytics / RAG Toggle */}
        <div className="flex flex-col border-l border-gray-800 bg-[#0F1115]" style={{ width: showRAGPanel ? '800px' : showAnalytics ? '600px' : '360px' }}>
          {/* Toggle Tabs */}
          <div className="flex border-b border-gray-800 bg-[#0A0B0D]">
            <button
              onClick={() => {
                setShowRAGPanel(false);
                setShowAnalytics(false);
              }}
              className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
                !showRAGPanel && !showAnalytics
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-[#0F1115]'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              📊 Telemetry
            </button>
            <button
              onClick={() => {
                setShowRAGPanel(false);
                setShowAnalytics(true);
              }}
              className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
                showAnalytics
                  ? 'text-emerald-400 border-b-2 border-emerald-400 bg-[#0F1115]'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              📈 Analytics
            </button>
            <button
              onClick={() => {
                setShowRAGPanel(true);
                setShowAnalytics(false);
              }}
              className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
                showRAGPanel
                  ? 'text-purple-400 border-b-2 border-purple-400 bg-[#0F1115]'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              🤖 RAG Copilot
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-hidden">
            {showRAGPanel ? (
              <RAGCopilotPanel
                queryId={activeQueryId || undefined}
                activeQuery={activeQuery?.query}
              />
            ) : showAnalytics ? (
              <AnalyticsPanel
                activeRunId={selectedRunId || activeQuery?.results?.run_id}
                selectedRunIds={selectedRunIds.length > 0 ? selectedRunIds : (activeQuery?.results?.run_ids || [])}
                onRunSelect={(runId: string) => {
                  setSelectedRunId(runId);
                  setShowAnalytics(true);
                }}
                onRunIdsChange={(runIds: string[]) => {
                  setSelectedRunIds(runIds);
                }}
              />
            ) : (
              <TelemetrySidebar metrics={telemetry} />
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <StatusFooter
        systemStatus={isProcessing ? 'busy' : 'ready'}
        version="OpenMC v0.14.0"
        cores={128}
        coreUsage={isProcessing ? 82 : 0}
        latency={42}
        tokenConsumption={1.2}
        eta="14:48:00"
      />
    </div>
  );
}
