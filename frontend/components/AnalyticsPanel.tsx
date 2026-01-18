'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/lib/api';
import { BatchConvergenceChart } from './BatchConvergenceChart';
import { ParameterSweepChart } from './ParameterSweepChart';
import { ComparisonChart } from './ComparisonChart';
import type { VisualizationResponse, BatchConvergenceData, ParameterSweepData, ComparisonData, RunSummary } from '@/lib/types';

interface AnalyticsPanelProps {
  activeRunId?: string;
  selectedRunIds?: string[];
  viewMode?: 'dashboard' | 'run' | 'sweep' | 'comparison';
  onRunSelect?: (runId: string) => void;
  onRunIdsChange?: (runIds: string[]) => void;
}

export function AnalyticsPanel({
  activeRunId,
  selectedRunIds = [],
  viewMode = 'dashboard',
  onRunSelect,
  onRunIdsChange,
}: AnalyticsPanelProps) {
  const [selectedView, setSelectedView] = useState<'run' | 'sweep' | 'comparison' | 'dashboard'>(viewMode as any);
  const [localSelectedRunIds, setLocalSelectedRunIds] = useState<string[]>(selectedRunIds);

  // Fetch run visualization if we have an active run
  const { data: runVisualization, isLoading: runLoading } = useQuery({
    queryKey: ['visualization', 'run', activeRunId],
    queryFn: () => apiService.getRunVisualization(activeRunId!),
    enabled: !!activeRunId && selectedView === 'run',
  });

  // Fetch sweep visualization if we have multiple run IDs
  const { data: sweepVisualization, isLoading: sweepLoading } = useQuery({
    queryKey: ['visualization', 'sweep', selectedRunIds.join(',')],
    queryFn: () => apiService.getSweepVisualization(selectedRunIds),
    enabled: selectedRunIds.length >= 2 && selectedView === 'sweep',
  });

  // Fetch comparison visualization if we have multiple run IDs
  const { data: comparisonVisualization, isLoading: comparisonLoading } = useQuery({
    queryKey: ['visualization', 'comparison', selectedRunIds.join(',')],
    queryFn: () => apiService.getComparisonVisualization(selectedRunIds),
    enabled: selectedRunIds.length >= 2 && selectedView === 'comparison',
  });

  // Fetch statistics for dashboard
  const { data: statistics } = useQuery({
    queryKey: ['statistics'],
    queryFn: () => apiService.getStatistics(),
  });

  // Fetch all runs for dashboard
  const { data: allRuns, isLoading: runsLoading } = useQuery({
    queryKey: ['runs', 'all'],
    queryFn: () => apiService.getRuns(50, 0),
  });

  // Fetch similar runs if we have an active run
  const { data: similarRuns } = useQuery({
    queryKey: ['runs', 'similar', activeRunId],
    queryFn: () => apiService.findSimilarRuns(activeRunId!, 10),
    enabled: !!activeRunId && selectedView === 'run',
  });

  // Sync local state with props
  useEffect(() => {
    setLocalSelectedRunIds(selectedRunIds);
  }, [selectedRunIds]);

  // Determine which view to show
  const currentView = selectedView || viewMode;

  // Helper to select a run
  const handleRunClick = (runId: string) => {
    if (onRunSelect) {
      onRunSelect(runId);
      setSelectedView('run');
    }
  };

  // Helper to toggle run selection for comparison/sweep
  const handleRunToggle = (runId: string) => {
    const newSelection = localSelectedRunIds.includes(runId)
      ? localSelectedRunIds.filter(id => id !== runId)
      : [...localSelectedRunIds, runId];
    
    setLocalSelectedRunIds(newSelection);
    if (onRunIdsChange) {
      onRunIdsChange(newSelection);
    }

    // Auto-switch to comparison if 2+ runs selected
    if (newSelection.length >= 2 && selectedView === 'dashboard') {
      setSelectedView('comparison');
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0A0B0D]">
      {/* View selector */}
      <div className="flex border-b border-gray-800 bg-[#0A0B0D] px-2 py-1 gap-1">
        {activeRunId && (
          <button
            onClick={() => setSelectedView('run')}
            className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
              currentView === 'run'
                ? 'bg-blue-600 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Batch Convergence
          </button>
        )}
        {selectedRunIds.length >= 2 && (
          <>
            <button
              onClick={() => setSelectedView('sweep')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                currentView === 'sweep'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Sweep
            </button>
            <button
              onClick={() => setSelectedView('comparison')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                currentView === 'comparison'
                  ? 'bg-green-600 text-white'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Compare
            </button>
          </>
        )}
        <button
          onClick={() => setSelectedView('dashboard')}
          className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
            currentView === 'dashboard'
              ? 'bg-gray-700 text-white'
              : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Overview
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {currentView === 'run' && activeRunId && (
          <div className="space-y-4">
            {runLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-sm text-gray-500">Loading visualization...</div>
              </div>
            ) : runVisualization && runVisualization.type === 'batch_convergence' ? (
              <>
                <BatchConvergenceChart data={runVisualization.data as BatchConvergenceData} />
                
                {/* Similar Runs */}
                {similarRuns && similarRuns.similar_runs.length > 0 && (
                  <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
                    <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide mb-3">
                      Similar Experiments ({similarRuns.total_found})
                    </h3>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {similarRuns.similar_runs.map((run: any) => (
                        <div
                          key={run.run_id}
                          className={`flex items-center justify-between p-2 rounded border transition-colors cursor-pointer ${
                            activeRunId === run.run_id
                              ? 'bg-blue-600/20 border-blue-500'
                              : 'bg-[#0A0B0D] border-[#1F2937] hover:border-blue-500'
                          }`}
                          onClick={() => handleRunClick(run.run_id)}
                        >
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-mono text-gray-300 truncate">
                              {run.run_id?.substring(0, 12) || 'Unknown'}
                            </div>
                            <div className="text-[10px] text-gray-500">
                              {run.geometry} {run.enrichment_pct ? `@ ${run.enrichment_pct}%` : ''}
                              {run.temperature_K ? `, ${run.temperature_K}K` : ''}
                            </div>
                          </div>
                          <div className="text-xs font-mono text-emerald-400 ml-2">
                            k={run.keff?.toFixed(5) || 'N/A'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-sm text-gray-500">No visualization data available for run {activeRunId}</div>
            )}
          </div>
        )}

        {currentView === 'sweep' && selectedRunIds.length >= 2 && (
          <div className="space-y-4">
            {sweepLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-sm text-gray-500">Loading sweep visualization...</div>
              </div>
            ) : sweepVisualization && sweepVisualization.type === 'parameter_sweep' ? (
              <ParameterSweepChart data={sweepVisualization.data as ParameterSweepData} />
            ) : (
              <div className="text-sm text-gray-500">No sweep data available</div>
            )}
          </div>
        )}

        {currentView === 'comparison' && selectedRunIds.length >= 2 && (
          <div className="space-y-4">
            {comparisonLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-sm text-gray-500">Loading comparison...</div>
              </div>
            ) : comparisonVisualization && comparisonVisualization.type === 'comparison' ? (
              <ComparisonChart data={comparisonVisualization.data as ComparisonData} />
            ) : (
              <div className="text-sm text-gray-500">No comparison data available</div>
            )}
          </div>
        )}

        {currentView === 'dashboard' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-[#14161B] border border-[#1F2937] rounded">
                <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Total Runs</div>
                <div className="text-2xl font-mono font-bold text-gray-200">
                  {statistics?.total_runs || 0}
                </div>
              </div>
              <div className="p-3 bg-[#14161B] border border-[#1F2937] rounded">
                <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Completed</div>
                <div className="text-2xl font-mono font-bold text-emerald-400">
                  {statistics?.completed_runs || 0}
                </div>
              </div>
              <div className="p-3 bg-[#14161B] border border-[#1F2937] rounded">
                <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Total Studies</div>
                <div className="text-2xl font-mono font-bold text-blue-400">
                  {statistics?.total_studies || 0}
                </div>
              </div>
              <div className="p-3 bg-[#14161B] border border-[#1F2937] rounded">
                <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1">Queries</div>
                <div className="text-2xl font-mono font-bold text-purple-400">
                  {statistics?.total_queries || 0}
                </div>
              </div>
            </div>

            {/* All Runs */}
            {allRuns && allRuns.runs.length > 0 && (
              <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
                <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide mb-3">
                  All Runs ({allRuns.total})
                </h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {runsLoading ? (
                    <div className="text-[10px] text-gray-500 py-4 text-center">Loading runs...</div>
                  ) : (
                    allRuns.runs.map((run: RunSummary) => (
                      <div
                        key={run.run_id}
                        className="flex items-center justify-between p-2 bg-[#0A0B0D] rounded border border-[#1F2937] hover:border-blue-500 transition-colors cursor-pointer"
                        onClick={() => {
                          setSelectedView('run');
                          handleRunClick(run.run_id);
                        }}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-mono text-gray-300 truncate">
                            {run.run_id?.substring(0, 12) || 'Unknown'}
                          </div>
                          <div className="text-[10px] text-gray-500">
                            {run.geometry} {run.enrichment_pct ? `@ ${run.enrichment_pct}%` : ''}
                            {run.temperature_K ? `, ${run.temperature_K}K` : ''}
                          </div>
                        </div>
                        <div className="text-xs font-mono text-emerald-400 ml-2">
                          k={run.keff?.toFixed(5) || 'N/A'}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Recent Runs (fallback) */}
            {(!allRuns || allRuns.runs.length === 0) && statistics?.recent_runs && statistics.recent_runs.length > 0 && (
              <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
                <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide mb-3">
                  Recent Runs
                </h3>
                <div className="space-y-2">
                  {statistics.recent_runs.map((run: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-[#0A0B0D] rounded border border-[#1F2937] hover:border-gray-600 transition-colors cursor-pointer"
                      onClick={() => {
                        setSelectedView('run');
                        handleRunClick(run.run_id);
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-mono text-gray-300 truncate">
                          {run.run_id || `Run ${idx + 1}`}
                        </div>
                        <div className="text-[10px] text-gray-500">{run.geometry}</div>
                      </div>
                      <div className="text-xs font-mono text-emerald-400 ml-2">
                        k={run.keff?.toFixed(5) || 'N/A'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Instructions */}
            <div className="p-4 bg-[#14161B] border border-[#1F2937] rounded">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide mb-2">
                How to Use
              </h3>
              <ul className="text-[10px] text-gray-400 space-y-1 list-disc list-inside">
                <li>Select a run to view batch convergence</li>
                <li>Select multiple runs to compare or view parameter sweeps</li>
                <li>Charts update automatically when new data is available</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

