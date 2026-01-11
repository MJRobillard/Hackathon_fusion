'use client';

import { TrendingUp, AlertTriangle, CheckCircle, Lightbulb, Activity } from 'lucide-react';
import { formatKeff, getCriticalityStatus, formatNumber } from '@/lib/formatters';
import type { SimulationResults } from '@/lib/types';

interface ResultsPanelProps {
  results?: SimulationResults;
  analysis?: string;
  suggestions?: string[];
}

export function ResultsPanel({ results, analysis, suggestions }: ResultsPanelProps) {
  if (!results) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 h-full">
        <div className="flex items-center gap-2 mb-4">
          <Activity size={18} className="text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-200">Results</h3>
        </div>
        <div className="text-center text-xs text-gray-500 mt-8">
          Results will appear here after execution...
        </div>
      </div>
    );
  }

  const renderSingleStudy = () => {
    if (!results.keff) return null;

    const criticalityStatus = getCriticalityStatus(results.keff);

    return (
      <div className="space-y-4">
        {/* k-eff Display */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="text-xs text-gray-500 uppercase font-semibold mb-1">
                k-effective
              </div>
              <div className="text-2xl font-mono font-bold text-gray-100">
                {formatKeff(results.keff, results.keff_std)}
              </div>
            </div>
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
              criticalityStatus.label.includes('CRITICAL') && !criticalityStatus.label.includes('SUB')
                ? 'bg-emerald-600/20 border-emerald-500/30'
                : criticalityStatus.label.includes('SUB')
                ? 'bg-amber-600/20 border-amber-500/30'
                : 'bg-red-600/20 border-red-500/30'
            }`}>
              <span className="text-lg">{criticalityStatus.label.split(' ')[0]}</span>
              <span className={`text-xs font-semibold ${criticalityStatus.color}`}>
                {criticalityStatus.label.split(' ')[1]}
              </span>
            </div>
          </div>
          <div className="text-xs text-gray-400">
            {criticalityStatus.description}
          </div>
        </div>

        {/* Run Details */}
        <div className="grid grid-cols-2 gap-3">
          {results.run_id && (
            <div className="bg-gray-800/30 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Run ID</div>
              <div className="text-xs font-mono text-gray-300">{results.run_id}</div>
            </div>
          )}
          {results.geometry && (
            <div className="bg-gray-800/30 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Geometry</div>
              <div className="text-xs font-semibold text-gray-300">{results.geometry}</div>
            </div>
          )}
          {results.enrichment_pct !== undefined && (
            <div className="bg-gray-800/30 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Enrichment</div>
              <div className="text-xs font-semibold text-gray-300">
                {results.enrichment_pct.toFixed(2)}%
              </div>
            </div>
          )}
          {results.temperature_K !== undefined && (
            <div className="bg-gray-800/30 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Temperature</div>
              <div className="text-xs font-semibold text-gray-300">
                {formatNumber(results.temperature_K)} K
              </div>
            </div>
          )}
          {results.particles !== undefined && (
            <div className="bg-gray-800/30 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Particles</div>
              <div className="text-xs font-semibold text-gray-300">
                {formatNumber(results.particles)}
              </div>
            </div>
          )}
          {results.batches !== undefined && (
            <div className="bg-gray-800/30 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Batches</div>
              <div className="text-xs font-semibold text-gray-300">
                {formatNumber(results.batches)}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderSweepResults = () => {
    if (!results.run_ids || results.run_ids.length === 0) return null;

    return (
      <div className="space-y-4">
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
            <div className="text-xs text-gray-500 mb-1">Runs</div>
            <div className="text-xl font-mono font-bold text-gray-100">
              {results.run_ids.length}
            </div>
          </div>
          {results.keff_mean !== undefined && (
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Mean k-eff</div>
              <div className="text-xl font-mono font-bold text-gray-100">
                {results.keff_mean.toFixed(5)}
              </div>
            </div>
          )}
          {results.keff_min !== undefined && results.keff_max !== undefined && (
            <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-1">Range</div>
              <div className="text-sm font-mono font-bold text-gray-100">
                {results.keff_min.toFixed(3)} - {results.keff_max.toFixed(3)}
              </div>
            </div>
          )}
        </div>

        {/* Individual Runs */}
        {results.keff_values && results.keff_values.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-500 font-semibold uppercase">
              Individual Results
            </div>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {results.keff_values.map((keff, index) => {
                const status = getCriticalityStatus(keff);
                return (
                  <div
                    key={index}
                    className="flex items-center justify-between bg-gray-800/30 rounded px-3 py-2"
                  >
                    <span className="text-xs font-mono text-gray-400">
                      {results.run_ids?.[index] || `Run ${index + 1}`}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-semibold text-gray-300">
                        {keff.toFixed(5)}
                      </span>
                      <span className={`text-xs ${status.color}`}>
                        {status.label.split(' ')[0]}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderQueryResults = () => {
    if (!results.results || results.results.length === 0) return null;

    return (
      <div className="space-y-4">
        <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-3">
          <div className="text-xs text-gray-500 mb-1">Query Results</div>
          <div className="text-2xl font-mono font-bold text-gray-100">
            {results.count || results.results.length} found
          </div>
        </div>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          {results.results.slice(0, 10).map((result: any, index: number) => (
            <div
              key={index}
              className="bg-gray-800/30 rounded-lg p-3 text-xs space-y-1"
            >
              {result.run_id && (
                <div className="font-mono text-gray-400">{result.run_id}</div>
              )}
              {result.keff !== undefined && (
                <div className="text-gray-300">
                  k-eff: <span className="font-mono font-semibold">{result.keff.toFixed(5)}</span>
                </div>
              )}
              {result.geometry && (
                <div className="text-gray-500">Geometry: {result.geometry}</div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 h-full overflow-y-auto">
      <div className="flex items-center gap-2 mb-4">
        <Activity size={18} className="text-gray-400" />
        <h3 className="text-sm font-semibold text-gray-200">Results</h3>
      </div>

      {/* Results Display */}
      <div className="space-y-6">
        {results.keff !== undefined && renderSingleStudy()}
        {results.run_ids && results.run_ids.length > 0 && renderSweepResults()}
        {results.results && results.results.length > 0 && renderQueryResults()}

        {/* Analysis Section */}
        {analysis && (
          <div className="border-t border-gray-800 pt-4">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle size={16} className="text-emerald-400" />
              <h4 className="text-xs font-semibold text-gray-200 uppercase">Analysis</h4>
            </div>
            <div className="bg-emerald-600/5 border border-emerald-600/20 rounded-lg p-3 text-xs text-gray-300 leading-relaxed">
              {analysis}
            </div>
          </div>
        )}

        {/* Suggestions Section */}
        {suggestions && suggestions.length > 0 && (
          <div className="border-t border-gray-800 pt-4">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb size={16} className="text-yellow-400" />
              <h4 className="text-xs font-semibold text-gray-200 uppercase">
                Next Experiments
              </h4>
            </div>
            <div className="space-y-2">
              {suggestions.map((suggestion, index) => (
                <div
                  key={index}
                  className="flex gap-2 bg-yellow-600/5 border border-yellow-600/20 rounded-lg p-3 text-xs text-gray-300"
                >
                  <span className="text-yellow-400 font-bold shrink-0">{index + 1}.</span>
                  <span className="leading-relaxed">{suggestion}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

