'use client';

import { useState, useRef, useEffect } from 'react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (query: string, useLLM: boolean) => void;
  isProcessing?: boolean;
}

export function CommandPalette({ isOpen, onClose, onSubmit, isProcessing }: CommandPaletteProps) {
  const [query, setQuery] = useState('');
  const [useLLM, setUseLLM] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query, useLLM);
      setQuery('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-2xl mx-4 bg-[#14161B] border border-[#1F2937] rounded-lg shadow-2xl">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[#1F2937]">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-300 tracking-wide">COMMAND PALETTE</h2>
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

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="p-4">
          <div className="mb-4">
            <label className="block text-xs text-gray-400 mb-2">
              QUERY
            </label>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g., Simulate PWR at 4.5% enrichment..."
              className="w-full px-4 py-3 bg-[#0A0B0D] border border-[#1F2937] rounded text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
              disabled={isProcessing}
            />
          </div>

          {/* Options */}
          <div className="mb-4">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={useLLM}
                onChange={(e) => setUseLLM(e.target.checked)}
                className="w-4 h-4 bg-[#0A0B0D] border border-[#1F2937] rounded focus:ring-blue-500 focus:ring-2"
                disabled={isProcessing}
              />
              <span className="text-xs text-gray-400">
                Use LLM Routing (slower but more accurate)
              </span>
            </label>
          </div>

          {/* Examples */}
          <div className="mb-4 p-3 bg-[#0A0B0D] border border-[#1F2937] rounded">
            <p className="text-[10px] text-gray-500 font-semibold mb-2">EXAMPLE QUERIES:</p>
            <div className="space-y-1">
              <button
                type="button"
                onClick={() => setQuery('Simulate PWR at 4.5% enrichment')}
                className="block w-full text-left text-xs text-gray-400 hover:text-blue-400 transition-colors"
                disabled={isProcessing}
              >
                • Simulate PWR at 4.5% enrichment
              </button>
              <button
                type="button"
                onClick={() => setQuery('Run parameter sweep for enrichment 3% to 5%')}
                className="block w-full text-left text-xs text-gray-400 hover:text-blue-400 transition-colors"
                disabled={isProcessing}
              >
                • Run parameter sweep for enrichment 3% to 5%
              </button>
              <button
                type="button"
                onClick={() => setQuery('Find all critical PWR configurations')}
                className="block w-full text-left text-xs text-gray-400 hover:text-blue-400 transition-colors"
                disabled={isProcessing}
              >
                • Find all critical PWR configurations
              </button>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-gray-200 transition-colors"
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!query.trim() || isProcessing}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed text-white text-xs font-semibold rounded transition-colors"
            >
              {isProcessing ? 'Processing...' : 'Execute'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

