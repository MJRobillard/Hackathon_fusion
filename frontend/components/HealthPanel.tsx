'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/lib/api';

interface HealthPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HealthPanel({ isOpen, onClose }: HealthPanelProps) {
  const [testResults, setTestResults] = useState<Record<string, any>>({});

  // Fetch health status
  const { data: healthData, isLoading, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiService.getHealth(),
    enabled: isOpen,
    refetchInterval: 5000, // Refresh every 5 seconds when open
  });

  // Fetch statistics for additional info
  const { data: statsData } = useQuery({
    queryKey: ['statistics'],
    queryFn: () => apiService.getStatistics(),
    enabled: isOpen,
    refetchInterval: 5000,
  });

  const handleRunTest = async (testName: string, testFn: () => Promise<any>) => {
    setTestResults(prev => ({
      ...prev,
      [testName]: { status: 'running' }
    }));

    try {
      const result = await testFn();
      setTestResults(prev => ({
        ...prev,
        [testName]: { status: 'success', data: result }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [testName]: { status: 'failed', error: error instanceof Error ? error.message : 'Unknown error' }
      }));
    }
  };

  const runAllTests = async () => {
    await handleRunTest('health', () => apiService.getHealth());
    await handleRunTest('statistics', () => apiService.getStatistics());
    await refetch();
  };

  if (!isOpen) return null;

  const overallHealth = healthData?.status === 'healthy';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-3xl mx-4 bg-[#14161B] border border-[#1F2937] rounded-lg shadow-2xl max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[#1F2937] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${overallHealth ? 'bg-emerald-500 animate-pulse-dot' : 'bg-red-500'}`} />
            <h2 className="text-sm font-semibold text-gray-300 tracking-wide">SYSTEM HEALTH</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={runAllTests}
              className="px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
            >
              Run All Tests
            </button>
            <button
              onClick={onClose}
              className="p-1 hover:bg-[#1F2937] rounded transition-colors"
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Overall Status */}
          <div className={`p-4 rounded border ${overallHealth ? 'bg-emerald-500/5 border-emerald-500/30' : 'bg-red-500/5 border-red-500/30'}`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Overall Status</h3>
              <span className={`text-xs font-mono font-bold ${overallHealth ? 'text-emerald-400' : 'text-red-400'}`}>
                {isLoading ? 'CHECKING...' : overallHealth ? 'HEALTHY' : 'UNHEALTHY'}
              </span>
            </div>
            <p className="text-xs text-gray-400">
              {isLoading ? 'Running diagnostics...' : overallHealth ? 'All systems operational' : 'One or more services are down'}
            </p>
          </div>

          {/* Service Status */}
          <div className="grid grid-cols-2 gap-4">
            {/* MongoDB */}
            <div className="p-4 bg-[#0A0B0D] border border-[#1F2937] rounded">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M17.193 9.555c-1.264-5.58-4.252-7.414-4.573-8.115-.28-.394-.53-.954-.735-1.44-.036.495-.055.685-.523 1.184-.723.566-4.438 3.682-4.74 10.02-.282 5.912 4.27 9.435 4.888 9.884l.07.05A73.49 73.49 0 0111.91 24h.481c.114-1.032.284-2.056.51-3.07.417-.296 4.488-3.3 4.488-8.944 0-.954-.126-1.77-.196-2.431z"/>
                  </svg>
                  <h4 className="text-xs font-semibold text-gray-300">MongoDB</h4>
                </div>
                <div className={`w-2 h-2 rounded-full ${healthData?.services?.mongodb ? 'bg-emerald-500' : 'bg-red-500'}`} />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Status:</span>
                  <span className={healthData?.services?.mongodb ? 'text-emerald-400' : 'text-red-400'}>
                    {isLoading ? 'Checking...' : healthData?.services?.mongodb ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
                {statsData && (
                  <>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Total Studies:</span>
                      <span className="text-gray-300 font-mono">{statsData.total_studies}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-500">Total Runs:</span>
                      <span className="text-gray-300 font-mono">{statsData.total_runs}</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* OpenMC */}
            <div className="p-4 bg-[#0A0B0D] border border-[#1F2937] rounded">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <h4 className="text-xs font-semibold text-gray-300">OpenMC</h4>
                </div>
                <div className={`w-2 h-2 rounded-full ${healthData?.services?.openmc ? 'bg-emerald-500' : 'bg-amber-500'}`} />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Status:</span>
                  <span className={healthData?.services?.openmc ? 'text-emerald-400' : 'text-amber-400'}>
                    {isLoading ? 'Checking...' : healthData?.services?.openmc ? 'Available' : 'Not tested'}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">Version:</span>
                  <span className="text-gray-300 font-mono">0.14.0</span>
                </div>
              </div>
            </div>
          </div>

          {/* API Endpoints */}
          <div className="p-4 bg-[#0A0B0D] border border-[#1F2937] rounded">
            <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide mb-3">API Endpoints</h3>
            <div className="space-y-2">
              {[
                { name: 'Health Check', endpoint: '/api/v1/health', test: () => apiService.getHealth() },
                { name: 'Statistics', endpoint: '/api/v1/statistics', test: () => apiService.getStatistics() },
              ].map((endpoint) => {
                const result = testResults[endpoint.name];
                return (
                  <div key={endpoint.name} className="flex items-center justify-between py-2 border-b border-[#1F2937] last:border-0">
                    <div className="flex-1">
                      <div className="text-xs text-gray-300">{endpoint.name}</div>
                      <div className="text-[10px] font-mono text-gray-500">{endpoint.endpoint}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {result && (
                        <span className={`text-[10px] font-mono font-semibold ${
                          result.status === 'success' ? 'text-emerald-400' :
                          result.status === 'failed' ? 'text-red-400' :
                          'text-blue-400'
                        }`}>
                          {result.status === 'success' ? '✓ PASS' :
                           result.status === 'failed' ? '✗ FAIL' :
                           '⋯ RUNNING'}
                        </span>
                      )}
                      <button
                        onClick={() => handleRunTest(endpoint.name, endpoint.test)}
                        className="px-2 py-1 text-[10px] font-semibold bg-[#1F2937] hover:bg-[#374151] text-gray-300 rounded transition-colors"
                      >
                        Test
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Test Results */}
          {Object.keys(testResults).length > 0 && (
            <div className="p-4 bg-[#0A0B0D] border border-[#1F2937] rounded">
              <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide mb-3">Test Results</h3>
              <div className="space-y-2">
                {Object.entries(testResults).map(([name, result]) => (
                  <div key={name} className="p-2 bg-[#14161B] rounded">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-300">{name}</span>
                      <span className={`text-[10px] font-mono font-semibold ${
                        result.status === 'success' ? 'text-emerald-400' :
                        result.status === 'failed' ? 'text-red-400' :
                        'text-blue-400'
                      }`}>
                        {result.status.toUpperCase()}
                      </span>
                    </div>
                    {result.error && (
                      <p className="text-[10px] text-red-400 font-mono">{result.error}</p>
                    )}
                    {result.data && (
                      <pre className="text-[9px] text-gray-500 font-mono overflow-x-auto mt-1">
                        {JSON.stringify(result.data, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

