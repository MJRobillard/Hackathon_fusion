'use client';

import { useState } from 'react';
import { Send, Zap, Brain } from 'lucide-react';
import { ROUTING_BADGES } from '@/lib/constants';

interface TopBarProps {
  onSubmit: (query: string, useLLM: boolean) => void;
  isProcessing: boolean;
  activeQueryId?: string;
  activeStatus?: string;
}

export function TopBar({ onSubmit, isProcessing, activeQueryId, activeStatus }: TopBarProps) {
  const [query, setQuery] = useState('Simulate a PWR pin cell at 4.5% enrichment and 600K temperature');
  const [useLLM, setUseLLM] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isProcessing) {
      onSubmit(query.trim(), useLLM);
    }
  };

  const getStatusBadge = () => {
    if (!activeQueryId) return null;

    const statusColors = {
      queued: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      processing: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      failed: 'bg-red-500/20 text-red-400 border-red-500/30',
    };

    const statusIcons = {
      queued: '⏳',
      processing: '🔄',
      completed: '✓',
      failed: '✗',
    };

    const color = statusColors[activeStatus as keyof typeof statusColors] || statusColors.queued;
    const icon = statusIcons[activeStatus as keyof typeof statusIcons] || statusIcons.queued;

    return (
      <div className={`flex items-center gap-2 px-3 py-1 rounded-lg border text-xs font-mono ${color}`}>
        <span>{icon}</span>
        <span className="hidden sm:inline">{activeQueryId}</span>
        <span className="sm:hidden">{activeQueryId.slice(0, 8)}</span>
        <span className="text-[10px] opacity-70">{activeStatus}</span>
      </div>
    );
  };

  return (
    <div className="bg-gray-900 border-b border-gray-800 px-6 py-3">
      <form onSubmit={handleSubmit} className="flex items-center gap-3">
        <div className="flex-1 flex items-center gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Example: Simulate a PWR pin cell at 4.5% enrichment and 600K temperature"
            disabled={isProcessing}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          
          {/* Mode Toggle */}
          <div className="flex gap-1 p-1 bg-gray-800 rounded-lg">
            <button
              type="button"
              onClick={() => setUseLLM(false)}
              disabled={isProcessing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
                !useLLM
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                  : 'text-gray-400 hover:text-gray-200 disabled:opacity-50'
              }`}
            >
              <Zap size={14} />
              <span>Fast</span>
              <span className="text-[10px] opacity-60">{ROUTING_BADGES.keyword.time}</span>
            </button>
            <button
              type="button"
              onClick={() => setUseLLM(true)}
              disabled={isProcessing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition ${
                useLLM
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                  : 'text-gray-400 hover:text-gray-200 disabled:opacity-50'
              }`}
            >
              <Brain size={14} />
              <span>Smart</span>
              <span className="text-[10px] opacity-60">{ROUTING_BADGES.llm.time}</span>
            </button>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={!query.trim() || isProcessing}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
          >
            <Send size={16} />
            <span className="hidden sm:inline">Submit</span>
          </button>
        </div>

        {/* Active Query Status */}
        {activeQueryId && (
          <div className="hidden lg:flex items-center gap-2 pl-3 border-l border-gray-700">
            {getStatusBadge()}
          </div>
        )}
      </form>
    </div>
  );
}

