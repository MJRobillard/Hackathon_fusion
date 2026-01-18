'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '@/lib/api';
import { useOpenMCBackendRunStream } from '@/hooks/useOpenMCBackendRunStream';

interface SimulationFormData {
  geometry: string;
  materials: string[];
  enrichment_pct: number;
  temperature_K: number;
  particles: number;
  batches: number;
}

export default function OpenMCBackendPanel() {
  // NOTE: TypeScript sometimes fails to pick up newer APIService members in this repo's setup.
  // We keep runtime correctness and avoid blocking the UI on TS declaration drift.
  const openmcApi = apiService as any;

  const [formData, setFormData] = useState<SimulationFormData>({
    geometry: 'PWR pin cell',
    materials: ['UO2', 'Water'],
    enrichment_pct: 4.5,
    temperature_K: 900.0,
    particles: 10000,
    batches: 50,
  });

  const [materialsInput, setMaterialsInput] = useState('UO2, Water');
  const [activeTab, setActiveTab] = useState<'submit' | 'monitor' | 'query' | 'sweep'>('submit');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const queryClient = useQueryClient();

  // Live OpenMC stream (proxied through main backend so it can tee into the backend terminal)
  const { logLines, toolEvents, isConnected: isStreamConnected, error: streamError, clear: clearStream } =
    useOpenMCBackendRunStream(selectedRunId);

  // Query OpenMC health
  const { data: health } = useQuery({
    queryKey: ['openmc-health'],
    queryFn: () => openmcApi.openmcGetHealth(),
    refetchInterval: 10000, // Every 10 seconds
  });

  // Query OpenMC statistics
  const { data: stats } = useQuery({
    queryKey: ['openmc-stats'],
    queryFn: () => openmcApi.openmcGetStatistics(),
    refetchInterval: 5000,
  });

  // Query recent runs
  const { data: runs, refetch: refetchRuns } = useQuery({
    queryKey: ['openmc-runs'],
    queryFn: () => openmcApi.openmcQueryRuns({ limit: 20, offset: 0 }),
    refetchInterval: 3000,
  });

  // Monitor selected run
  const { data: runDetails } = useQuery({
    queryKey: ['openmc-run', selectedRunId],
    queryFn: () => selectedRunId ? openmcApi.openmcGetSimulation(selectedRunId) : null,
    enabled: !!selectedRunId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false; // Stop polling
      }
      return 2000; // Poll every 2 seconds
    },
  });

  // Submit simulation mutation
  const submitMutation = useMutation({
    mutationFn: (spec: SimulationFormData) => openmcApi.openmcSubmitSimulation(spec),
    onSuccess: (data) => {
      setSelectedRunId((data as any).run_id);
      setActiveTab('monitor');
      queryClient.invalidateQueries({ queryKey: ['openmc-runs'] });
    },
  });

  // Sweep mutation
  const sweepMutation = useMutation({
    mutationFn: (params: { baseSpec: any; parameter: string; values: number[] }) =>
      openmcApi.openmcSubmitSweep(params.baseSpec, params.parameter, params.values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['openmc-runs'] });
    },
  });

  const handleSubmit = () => {
    // Parse materials
    const materials = materialsInput.split(',').map(m => m.trim());
    const spec = { ...formData, materials };
    submitMutation.mutate(spec);
  };

  const handleSubmitSweep = () => {
    const materials = materialsInput.split(',').map(m => m.trim());
    const baseSpec = { ...formData, materials };
    const values = [3.0, 3.5, 4.0, 4.5, 5.0];
    
    sweepMutation.mutate({
      baseSpec,
      parameter: 'enrichment_pct',
      values,
    });
  };

  const latestSuggestion = [...toolEvents]
    .reverse()
    .find((e) => e.type === 'tool_call' && e.tool_name === 'suggest_next_experiment' && e.args);

  const suggestionCandidates: SimulationFormData[] =
    (latestSuggestion?.args?.candidates as any[] | undefined)
      ?.filter(Boolean)
      ?.map((c) => ({
        geometry: c.geometry,
        materials: Array.isArray(c.materials) ? c.materials : [],
        enrichment_pct: Number(c.enrichment_pct),
        temperature_K: Number(c.temperature_K),
        particles: Number(c.particles),
        batches: Number(c.batches),
      }))
      ?.filter(
        (c) =>
          typeof c.geometry === 'string' &&
          c.geometry.length > 0 &&
          Array.isArray(c.materials) &&
          Number.isFinite(c.enrichment_pct) &&
          Number.isFinite(c.temperature_K) &&
          Number.isFinite(c.particles) &&
          Number.isFinite(c.batches)
      ) || [];

  return (
    <div className="flex flex-col h-full bg-[#0F1115] border border-gray-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-[#0A0B0D] border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="text-lg">⚛️</div>
          <div>
            <h2 className="text-sm font-semibold text-gray-200">OpenMC Backend Engine</h2>
            <p className="text-xs text-gray-500">Direct simulation control</p>
          </div>
        </div>
        
        {/* Health Status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${
            health?.status === 'healthy' ? 'bg-green-500 animate-pulse' :
            health?.status === 'degraded' ? 'bg-yellow-500' :
            'bg-red-500'
          }`}></div>
          <span className="text-xs text-gray-400">
            {health?.status || 'Unknown'}
          </span>
        </div>
      </div>

      {/* Stats Bar */}
      {stats && (
        <div className="flex gap-4 px-4 py-2 bg-gray-900/50 border-b border-gray-800 text-xs">
          <div>
            <span className="text-gray-500">Total Runs:</span>{' '}
            <span className="text-gray-300 font-mono">{stats.total_runs}</span>
          </div>
          <div>
            <span className="text-gray-500">Completed:</span>{' '}
            <span className="text-green-400 font-mono">{stats.completed_runs}</span>
          </div>
          <div>
            <span className="text-gray-500">Running:</span>{' '}
            <span className="text-blue-400 font-mono">{stats.running_runs}</span>
          </div>
          <div>
            <span className="text-gray-500">Failed:</span>{' '}
            <span className="text-red-400 font-mono">{stats.failed_runs}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-gray-900/30">
        {[
          { id: 'submit', label: '📤 Submit', icon: '📤' },
          { id: 'monitor', label: '📊 Monitor', icon: '📊' },
          { id: 'query', label: '🔍 Query', icon: '🔍' },
          { id: 'sweep', label: '📈 Sweep', icon: '📈' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/10'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'submit' && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              Submit New Simulation
            </h3>

            {/* Form */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Geometry</label>
                <select
                  value={formData.geometry}
                  onChange={(e) => setFormData({ ...formData, geometry: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                >
                  <option value="PWR pin cell">PWR Pin Cell</option>
                  <option value="BWR pin cell">BWR Pin Cell</option>
                  <option value="VVER pin cell">VVER Pin Cell</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Materials (comma-separated)</label>
                <input
                  type="text"
                  value={materialsInput}
                  onChange={(e) => setMaterialsInput(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                  placeholder="UO2, Water, Zircaloy"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Enrichment (%)
                  </label>
                  <input
                    type="number"
                    value={isNaN(formData.enrichment_pct) ? '' : formData.enrichment_pct}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setFormData({ ...formData, enrichment_pct: isNaN(val) ? 0 : val });
                    }}
                    className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                    min="0"
                    max="20"
                    step="0.1"
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Temperature (K)
                  </label>
                  <input
                    type="number"
                    value={isNaN(formData.temperature_K) ? '' : formData.temperature_K}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      setFormData({ ...formData, temperature_K: isNaN(val) ? 0 : val });
                    }}
                    className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                    min="0"
                    step="1"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Particles
                  </label>
                  <input
                    type="number"
                    value={isNaN(formData.particles) ? '' : formData.particles}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setFormData({ ...formData, particles: isNaN(val) ? 0 : val });
                    }}
                    className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                    min="100"
                    step="1000"
                  />
                </div>

                <div>
                  <label className="block text-xs text-gray-400 mb-1">
                    Batches
                  </label>
                  <input
                    type="number"
                    value={isNaN(formData.batches) ? '' : formData.batches}
                    onChange={(e) => {
                      const val = parseInt(e.target.value);
                      setFormData({ ...formData, batches: isNaN(val) ? 0 : val });
                    }}
                    className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                    min="10"
                    step="10"
                  />
                </div>
              </div>

              <button
                onClick={handleSubmit}
                disabled={submitMutation.isPending}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white text-sm font-medium rounded transition-colors"
              >
                {submitMutation.isPending ? '⏳ Submitting...' : '🚀 Submit Simulation'}
              </button>

              {submitMutation.isSuccess && (
                <div className="p-3 bg-green-900/20 border border-green-800 rounded text-sm">
                  <div className="text-green-400 font-semibold mb-1">✅ Submitted!</div>
                  <div className="text-gray-300 font-mono text-xs">
                    Run ID: {(submitMutation.data as any)?.run_id}
                  </div>
                </div>
              )}

              {submitMutation.isError && (
                <div className="p-3 bg-red-900/20 border border-red-800 rounded text-sm text-red-400">
                  ❌ {submitMutation.error?.message}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'monitor' && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              Monitor Simulation
            </h3>

            {selectedRunId ? (
              <div className="space-y-3">
                <div className="p-3 bg-gray-900 rounded border border-gray-800">
                  <div className="text-xs text-gray-400 mb-1">Run ID</div>
                  <div className="text-sm font-mono text-gray-200">{selectedRunId}</div>
                </div>

                {runDetails && (
                  <>
                    <div className="p-3 bg-gray-900 rounded border border-gray-800">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs text-gray-400">Status</span>
                        <span className={`text-sm font-semibold ${
                          runDetails.status === 'completed' ? 'text-green-400' :
                          runDetails.status === 'running' ? 'text-blue-400' :
                          runDetails.status === 'failed' ? 'text-red-400' :
                          'text-yellow-400'
                        }`}>
                          {runDetails.status.toUpperCase()}
                        </span>
                      </div>

                      {runDetails.status === 'running' && (
                        <div className="w-full bg-gray-800 rounded-full h-2 mt-2">
                          <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                        </div>
                      )}
                    </div>

                    {runDetails.status === 'completed' && (
                      <div className="space-y-2">
                        <div className="p-3 bg-green-900/20 border border-green-800 rounded">
                          <div className="text-xs text-gray-400 mb-1">k-effective</div>
                          <div className="text-2xl font-mono text-green-400 font-bold">
                            {runDetails.keff.toFixed(5)}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            ± {runDetails.keff_std.toFixed(5)} ({runDetails.uncertainty_pcm.toFixed(1)} pcm)
                          </div>
                        </div>

                        <div className="p-3 bg-gray-900 rounded border border-gray-800">
                          <div className="text-xs text-gray-400 mb-1">Runtime</div>
                          <div className="text-sm font-mono text-gray-200">
                            {runDetails.runtime_seconds.toFixed(2)}s
                          </div>
                        </div>
                      </div>
                    )}

                    {runDetails.error && (
                      <div className="p-3 bg-red-900/20 border border-red-800 rounded text-sm text-red-400">
                        {runDetails.error}
                      </div>
                    )}

                    {/* Suggested reruns from agent/tool calls */}
                    {suggestionCandidates.length > 0 && (
                      <div className="p-3 bg-purple-900/10 border border-purple-800 rounded">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-xs font-semibold text-purple-300">
                            🤖 Suggested next experiments
                          </div>
                          <div className="text-[11px] text-gray-500 font-mono">
                            from tool_call: suggest_next_experiment
                          </div>
                        </div>
                        <div className="space-y-2">
                          {suggestionCandidates.slice(0, 3).map((cand, idx) => (
                            <div
                              key={idx}
                              className="p-2 bg-gray-900/60 border border-gray-800 rounded"
                            >
                              <div className="text-[11px] text-gray-300 font-mono mb-2">
                                #{idx + 1} • {cand.geometry} • enr={cand.enrichment_pct}% • T={cand.temperature_K}K • N={cand.particles} • batches={cand.batches}
                              </div>
                              <div className="flex gap-2">
                                <button
                                  onClick={() => {
                                    setFormData(cand);
                                    setMaterialsInput(cand.materials.join(', '));
                                    setActiveTab('submit');
                                  }}
                                  className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 rounded border border-gray-700"
                                >
                                  Load into form
                                </button>
                                <button
                                  onClick={() => submitMutation.mutate(cand)}
                                  disabled={submitMutation.isPending}
                                  className="px-3 py-1.5 text-xs bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white rounded"
                                >
                                  Run candidate
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Live Output Stream */}
                    <div className="mt-4 p-3 bg-gray-950/60 rounded border border-gray-800">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs font-semibold text-gray-300">Live OpenMC Output</div>
                        <div className="flex items-center gap-2 text-[11px] text-gray-500">
                          <span className={`inline-block w-2 h-2 rounded-full ${isStreamConnected ? 'bg-green-500 animate-pulse' : streamError ? 'bg-red-500' : 'bg-gray-600'}`} />
                          <span>{isStreamConnected ? 'Streaming' : streamError ? 'Error' : 'Idle'}</span>
                          <button
                            onClick={clearStream}
                            className="ml-2 px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded border border-gray-700"
                            title="Clear streamed output"
                          >
                            Clear
                          </button>
                        </div>
                      </div>

                      {streamError && (
                        <div className="mb-2 text-xs text-red-400">
                          {streamError}
                        </div>
                      )}

                      {/* Tool-style interpreted events */}
                      {toolEvents.length > 0 && (
                        <div className="mb-3 max-h-28 overflow-y-auto space-y-1">
                          {toolEvents.slice(-8).map((ev, idx) => (
                            <div
                              key={`${ev.timestamp}-${idx}`}
                              className="text-[11px] font-mono text-gray-300 bg-gray-900/60 border border-gray-800 rounded px-2 py-1"
                            >
                              <span className="text-gray-500 mr-2">{ev.timestamp}</span>
                              <span className="text-emerald-400 mr-2">{ev.type}</span>
                              {ev.tool_name ? <span className="text-cyan-300 mr-2">{ev.tool_name}</span> : null}
                              <span className="text-gray-300">{ev.message || ev.error || ''}</span>
                              {(ev.args || ev.result) && (
                                <details className="mt-1">
                                  <summary className="cursor-pointer text-gray-500 hover:text-gray-300">
                                    details
                                  </summary>
                                  <pre className="mt-1 whitespace-pre-wrap text-[10px] text-gray-400">
                                    {JSON.stringify({ args: ev.args, result: ev.result }, null, 2)}
                                  </pre>
                                </details>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Raw log tail */}
                      <div className="h-64 overflow-y-auto rounded border border-gray-800 bg-black/40 p-3 font-mono text-xs text-gray-200 whitespace-pre-wrap">
                        {logLines.length === 0 ? (
                          <div className="text-gray-500 italic">Waiting for OpenMC output…</div>
                        ) : (
                          logLines.slice(-400).map((l, idx) => <div key={idx}>{l}</div>)
                        )}
                      </div>
                      <div className="mt-2 flex justify-between text-[11px] text-gray-500 font-mono">
                        <span>{logLines.length} lines</span>
                        <span>run_id: {selectedRunId}</span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="text-sm text-gray-500 italic">
                No simulation selected. Submit a new run or select from recent runs below.
              </div>
            )}

            {/* Recent runs selector */}
            <div className="mt-6">
              <h4 className="text-xs font-semibold text-gray-400 mb-2">Recent Runs</h4>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {runs?.runs?.map((run: any) => (
                  <button
                    key={run.run_id}
                    onClick={() => setSelectedRunId(run.run_id)}
                    className={`w-full px-3 py-2 text-left text-xs rounded transition-colors ${
                      selectedRunId === run.run_id
                        ? 'bg-blue-900/30 border border-blue-800 text-blue-300'
                        : 'bg-gray-900 border border-gray-800 text-gray-400 hover:bg-gray-800'
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-mono">{run.run_id.substring(0, 12)}...</span>
                      <span className={`
                        ${run.status === 'completed' ? 'text-green-400' :
                          run.status === 'running' ? 'text-blue-400' :
                          run.status === 'failed' ? 'text-red-400' :
                          'text-yellow-400'}
                      `}>
                        {run.status}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'query' && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              Query Run History
            </h3>

            {runs?.runs && runs.runs.length > 0 ? (
              <div className="space-y-2">
                {runs.runs.map((run: any) => (
                  <div
                    key={run.run_id}
                    className="p-3 bg-gray-900 rounded border border-gray-800 hover:border-gray-700 transition-colors"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-mono text-gray-400">
                        {run.run_id}
                      </span>
                      <span className={`text-xs font-semibold ${
                        run.status === 'completed' ? 'text-green-400' :
                        run.status === 'running' ? 'text-blue-400' :
                        run.status === 'failed' ? 'text-red-400' :
                        'text-yellow-400'
                      }`}>
                        {run.status}
                      </span>
                    </div>

                    {run.status === 'completed' && (
                      <div className="text-sm text-gray-300">
                        <span className="text-emerald-400 font-mono font-semibold">
                          k-eff: {run.keff.toFixed(5)}
                        </span>
                        <span className="text-gray-500 mx-2">•</span>
                        <span className="text-gray-400">
                          {run.runtime_seconds?.toFixed(2)}s
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500 italic">
                No runs found
              </div>
            )}
          </div>
        )}

        {activeTab === 'sweep' && (
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-200 mb-3">
              Parameter Sweep
            </h3>

            <div className="p-3 bg-blue-900/10 border border-blue-800 rounded text-xs text-blue-300">
              📈 Run multiple simulations varying one parameter
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Parameter to Sweep</label>
                <select
                  className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                  defaultValue="enrichment_pct"
                >
                  <option value="enrichment_pct">Enrichment (%)</option>
                  <option value="temperature_K">Temperature (K)</option>
                  <option value="particles">Particles</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1">Values</label>
                <input
                  type="text"
                  defaultValue="3.0, 3.5, 4.0, 4.5, 5.0"
                  className="w-full px-3 py-2 text-sm bg-gray-800 text-gray-200 rounded border border-gray-700 focus:outline-none focus:border-blue-500"
                  placeholder="3.0, 3.5, 4.0, 4.5, 5.0"
                />
              </div>

              <button
                onClick={handleSubmitSweep}
                disabled={sweepMutation.isPending}
                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 text-white text-sm font-medium rounded transition-colors"
              >
                {sweepMutation.isPending ? '⏳ Submitting Sweep...' : '📈 Start Sweep'}
              </button>

              {sweepMutation.isSuccess && (
                <div className="p-3 bg-green-900/20 border border-green-800 rounded text-sm text-green-400">
                  ✅ Sweep submitted! Check the Monitor tab for progress.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

