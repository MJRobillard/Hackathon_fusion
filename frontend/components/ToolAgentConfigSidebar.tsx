'use client';

import { useState, useEffect } from 'react';
import { apiService } from '@/lib/api';

interface ConvergenceConfig {
  enabled: boolean;
  target_uncertainty_pcm: number;
  stable_delta_pcm: number;
  max_iterations: number;
  max_particles: number;
  max_batches: number;
  batches_step: number;
  particles_min_step: number;
}

interface ToolPromptConfig {
  tool_call_template: string;
  tool_result_template: string;
  per_tool_call_template: Record<string, string>;
}

interface OrchestrationConfig {
  tool_prompts: ToolPromptConfig;
  convergence: ConvergenceConfig;
}

interface CollapsibleSectionProps {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  color: 'blue' | 'purple' | 'emerald' | 'amber' | 'cyan' | 'pink' | 'indigo';
}

function CollapsibleSection({ title, icon, children, defaultOpen = false, color }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const colorClasses = {
    blue: {
      bar: 'bg-blue-500',
      text: 'text-blue-400',
      border: 'border-blue-500/30',
    },
    purple: {
      bar: 'bg-purple-500',
      text: 'text-purple-400',
      border: 'border-purple-500/30',
    },
    emerald: {
      bar: 'bg-emerald-500',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
    },
    amber: {
      bar: 'bg-amber-500',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
    },
    cyan: {
      bar: 'bg-cyan-500',
      text: 'text-cyan-400',
      border: 'border-cyan-500/30',
    },
    pink: {
      bar: 'bg-pink-500',
      text: 'text-pink-400',
      border: 'border-pink-500/30',
    },
    indigo: {
      bar: 'bg-indigo-500',
      text: 'text-indigo-400',
      border: 'border-indigo-500/30',
    },
  };

  const colors = colorClasses[color];

  return (
    <div className="space-y-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-2 hover:bg-[#14161B] rounded transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className={`w-1 h-4 ${colors.bar} rounded`} />
          {icon}
          <h3 className={`text-xs font-semibold ${colors.text} uppercase tracking-wider`}>{title}</h3>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>
      {isOpen && <div className="pl-3 space-y-3 border-l-2 border-[#1F2937]">{children}</div>}
    </div>
  );
}

const DEFAULT_CONFIG: OrchestrationConfig = {
  convergence: {
    enabled: false,
    target_uncertainty_pcm: 0,
    stable_delta_pcm: 0,
    max_iterations: 1,
    max_particles: 0,
    max_batches: 0,
    batches_step: 10,
    particles_min_step: 100,
  },
  tool_prompts: {
    tool_call_template: '',
    tool_result_template: '',
    per_tool_call_template: {},
  },
};

const normalizeConfig = (data: Partial<OrchestrationConfig> | null): OrchestrationConfig => ({
  convergence: {
    ...DEFAULT_CONFIG.convergence,
    ...(data?.convergence || {}),
  },
  tool_prompts: {
    ...DEFAULT_CONFIG.tool_prompts,
    ...(data?.tool_prompts || {}),
    per_tool_call_template: {
      ...(data?.tool_prompts?.per_tool_call_template || {}),
    },
  },
});

export function ToolAgentConfigSidebar() {
  const [config, setConfig] = useState<OrchestrationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getOrchestrationConfig();
      setConfig(normalizeConfig(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config');
      setConfig(normalizeConfig(null));
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    if (!config) return;
    try {
      setSaving(true);
      setError(null);
      setSuccess(false);
      await apiService.patchOrchestrationConfig({
        convergence: config.convergence,
        tool_prompts: config.tool_prompts,
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  const updateConvergence = (updates: Partial<ConvergenceConfig>) => {
    if (!config) return;
    setConfig({
      ...config,
      convergence: { ...config.convergence, ...updates },
    });
  };

  const updateToolPrompt = (key: keyof ToolPromptConfig, value: string | Record<string, string>) => {
    if (!config) return;
    setConfig({
      ...config,
      tool_prompts: { ...config.tool_prompts, [key]: value },
    });
  };

  const updatePerToolTemplate = (toolName: string, template: string) => {
    if (!config) return;
    const newPerTool = { ...config.tool_prompts.per_tool_call_template };
    if (template.trim() === '') {
      delete newPerTool[toolName];
    } else {
      newPerTool[toolName] = template;
    }
    updateToolPrompt('per_tool_call_template', newPerTool);
  };

  if (loading) {
    return (
      <div className="w-80 h-full bg-[#0A0B0D] border-r border-[#1F2937] flex items-center justify-center">
        <div className="text-sm text-gray-500">Loading config...</div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="w-80 h-full bg-[#0A0B0D] border-r border-[#1F2937] flex items-center justify-center">
        <div className="text-sm text-red-500">Failed to load config</div>
      </div>
    );
  }

  const allTools = [
    'submit_study',
    'validate_physics',
    'generate_sweep',
    'compare_runs',
    'query_results',
    'get_run_by_id',
    'get_study_statistics',
    'get_recent_runs',
  ];

  return (
    <div className="w-80 h-full bg-[#0A0B0D] border-r border-[#1F2937] flex flex-col">
      {/* Header */}
      <div className="h-14 border-b border-[#1F2937] flex items-center px-4">
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <h2 className="text-sm font-semibold text-gray-300 tracking-wide">TOOL & AGENT CONFIG</h2>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Success/Error Messages */}
        {error && (
          <div className="px-3 py-2 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-400">
            {error}
          </div>
        )}
        {success && (
          <div className="px-3 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded text-xs text-emerald-400">
            Config saved successfully
          </div>
        )}

        {/* Retry Agent / Convergence Config */}
        <CollapsibleSection title="Retry Agent (Convergence)" color="blue" defaultOpen={true}>
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="convergence-enabled"
                checked={config.convergence.enabled}
                onChange={(e) => updateConvergence({ enabled: e.target.checked })}
                className="w-4 h-4 rounded border-gray-600 bg-[#14161B] text-blue-500 focus:ring-blue-500"
              />
              <label htmlFor="convergence-enabled" className="text-xs text-gray-400 cursor-pointer">
                Enable convergence loop
              </label>
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Target Uncertainty (pcm)
              </label>
              <input
                type="number"
                value={config.convergence.target_uncertainty_pcm}
                onChange={(e) =>
                  updateConvergence({ target_uncertainty_pcm: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="1"
                min="0"
              />
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Stable Delta (pcm)
              </label>
              <input
                type="number"
                value={config.convergence.stable_delta_pcm}
                onChange={(e) =>
                  updateConvergence({ stable_delta_pcm: parseFloat(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="1"
                min="0"
              />
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Max Iterations
              </label>
              <input
                type="number"
                value={config.convergence.max_iterations}
                onChange={(e) =>
                  updateConvergence({ max_iterations: parseInt(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="1"
                min="1"
              />
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Max Particles
              </label>
              <input
                type="number"
                value={config.convergence.max_particles}
                onChange={(e) =>
                  updateConvergence({ max_particles: parseInt(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="1000"
                min="0"
              />
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Max Batches
              </label>
              <input
                type="number"
                value={config.convergence.max_batches}
                onChange={(e) =>
                  updateConvergence({ max_batches: parseInt(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="10"
                min="0"
              />
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Batches Step
              </label>
              <input
                type="number"
                value={config.convergence.batches_step}
                onChange={(e) =>
                  updateConvergence({ batches_step: parseInt(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="10"
                min="0"
              />
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Particles Min Step
              </label>
              <input
                type="number"
                value={config.convergence.particles_min_step}
                onChange={(e) =>
                  updateConvergence({ particles_min_step: parseInt(e.target.value) || 0 })
                }
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-blue-500 focus:outline-none"
                step="100"
                min="0"
              />
            </div>
          </div>
        </CollapsibleSection>

        {/* Tool Prompts Config */}
        <CollapsibleSection title="Tool Prompts (Global Templates)" color="purple">
          <div className="space-y-3">
            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Tool Call Template
              </label>
              <input
                type="text"
                value={config.tool_prompts.tool_call_template}
                onChange={(e) => updateToolPrompt('tool_call_template', e.target.value)}
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-purple-500 focus:outline-none font-mono"
                placeholder="{tool_name}, {agent}, {run_id}, {iteration}"
              />
              <p className="text-[9px] text-gray-600 mt-1">
                Variables: {'{tool_name}'}, {'{agent}'}, {'{run_id}'}, {'{iteration}'}
              </p>
            </div>

            <div>
              <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide">
                Tool Result Template
              </label>
              <input
                type="text"
                value={config.tool_prompts.tool_result_template}
                onChange={(e) => updateToolPrompt('tool_result_template', e.target.value)}
                className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-purple-500 focus:outline-none font-mono"
                placeholder="{tool_name}, {agent}"
              />
              <p className="text-[9px] text-gray-600 mt-1">
                Variables: {'{tool_name}'}, {'{agent}'}
              </p>
            </div>
          </div>
        </CollapsibleSection>

        {/* Individual Tool Templates */}
        <CollapsibleSection title="Tool-Specific Templates" color="emerald">
          <div className="space-y-3">
            {allTools.map((toolName) => (
              <div key={toolName}>
                <label className="block text-[10px] text-gray-500 mb-1.5 uppercase tracking-wide font-mono">
                  {toolName}
                </label>
                <input
                  type="text"
                  value={config.tool_prompts.per_tool_call_template?.[toolName] || ''}
                  onChange={(e) => updatePerToolTemplate(toolName, e.target.value)}
                  className="w-full px-2 py-1.5 bg-[#14161B] border border-[#1F2937] rounded text-xs text-gray-300 focus:border-emerald-500 focus:outline-none font-mono"
                  placeholder="Override (blank = use global template)"
                />
              </div>
            ))}
          </div>
        </CollapsibleSection>

        {/* Agent Info Sections (read-only for now) */}
        <CollapsibleSection
          title="Router Agent"
          color="cyan"
          icon={
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          }
        >
          <div className="space-y-2 text-xs text-gray-400">
            <p>Routes queries to appropriate specialist agents based on intent classification.</p>
            <p className="text-[10px] text-gray-600">Intents: single_study, sweep, query, analysis, rag_query</p>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="Studies Agent"
          color="amber"
          icon={
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        >
          <div className="space-y-2 text-xs text-gray-400">
            <p>Handles single simulation requests.</p>
            <p className="text-[10px] text-gray-600 font-mono">Tools: submit_study, get_run_by_id, validate_physics</p>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="Sweep Agent"
          color="pink"
          icon={
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
          }
        >
          <div className="space-y-2 text-xs text-gray-400">
            <p>Handles parameter sweep requests with multiple runs.</p>
            <p className="text-[10px] text-gray-600 font-mono">Tools: generate_sweep, compare_runs, validate_physics</p>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="Query Agent"
          color="indigo"
          icon={
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          }
        >
          <div className="space-y-2 text-xs text-gray-400">
            <p>Handles database search and query requests.</p>
            <p className="text-[10px] text-gray-600 font-mono">Tools: query_results, get_study_statistics, get_recent_runs</p>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="Analysis Agent"
          color="cyan"
          icon={
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        >
          <div className="space-y-2 text-xs text-gray-400">
            <p>Handles result analysis and comparison of specific runs.</p>
            <p className="text-[10px] text-gray-600 font-mono">Tools: compare_runs, get_run_by_id</p>
          </div>
        </CollapsibleSection>

        <CollapsibleSection
          title="RAG Copilot Agent"
          color="purple"
          icon={
            <svg className="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          }
        >
          <div className="space-y-2 text-xs text-gray-400">
            <p>RAG-based agent for literature search, reproducibility analysis, and experiment suggestions.</p>
            <p className="text-[10px] text-gray-600">Uses vector search over research papers and past runs.</p>
          </div>
        </CollapsibleSection>
      </div>

      {/* Footer - Save Button */}
      <div className="border-t border-[#1F2937] p-4">
        <button
          onClick={saveConfig}
          disabled={saving}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-xs font-medium text-white rounded transition-colors"
        >
          {saving ? 'Saving...' : 'Save Configuration'}
        </button>
      </div>
    </div>
  );
}
