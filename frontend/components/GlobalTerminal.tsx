'use client';

import { useEffect, useRef, useState } from 'react';
import { useGlobalTerminalStream } from '@/hooks/useGlobalTerminalStream';

interface GlobalTerminalProps {
  autoScroll?: boolean;
  maxLines?: number;
}

export default function GlobalTerminal({ 
  autoScroll = true,
  maxLines = 5000
}: GlobalTerminalProps) {
  const { lines, isConnected, error, reconnect, clear } = useGlobalTerminalStream();
  const terminalRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState<'all' | 'errors' | 'openmc'>('all');

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    if (autoScroll && !isPaused && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines, autoScroll, isPaused]);

  const handleScroll = () => {
    if (terminalRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = terminalRef.current;
      const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10;
      setIsPaused(!isAtBottom);
    }
  };

  const scrollToBottom = () => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
      setIsPaused(false);
    }
  };

  const copyToClipboard = () => {
    const text = lines.join('');
    navigator.clipboard.writeText(text);
  };

  const downloadLog = () => {
    const text = lines.join('');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backend-terminal-${Date.now()}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Filter lines based on selected filter
  const filteredLines = lines.filter(line => {
    if (filter === 'all') return true;
    if (filter === 'errors') return line.includes('[ERROR]') || line.includes('✗') || line.includes('failed') || line.includes('ERROR');
    if (filter === 'openmc') return line.includes('OpenMC') || line.includes('k-effective') || line.includes('Bat./Gen');
    return true;
  }).slice(-maxLines);

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
      {/* Terminal Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span className="text-sm font-mono text-gray-300">
            Backend Terminal Stream
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 
              error ? 'bg-red-500' : 
              'bg-gray-500'
            }`}></div>
            <span className="text-gray-400">
              {isConnected ? 'Live' : error ? 'Error' : 'Disconnected'}
            </span>
          </div>

          {/* Filter */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            className="px-2 py-1 text-xs bg-gray-700 text-gray-200 rounded border border-gray-600 focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Output</option>
            <option value="errors">Errors Only</option>
            <option value="openmc">OpenMC Only</option>
          </select>

          {/* Action Buttons */}
          <div className="flex gap-1">
            {isPaused && (
              <button
                onClick={scrollToBottom}
                className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                title="Scroll to bottom"
              >
                ↓ Resume
              </button>
            )}
            <button
              onClick={clear}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
              title="Clear terminal"
            >
              Clear
            </button>
            <button
              onClick={copyToClipboard}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
              title="Copy to clipboard"
            >
              Copy
            </button>
            <button
              onClick={downloadLog}
              className="px-2 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors"
              title="Download log"
            >
              Download
            </button>
            {error && (
              <button
                onClick={reconnect}
                className="px-2 py-1 text-xs bg-orange-600 hover:bg-orange-700 text-white rounded transition-colors"
                title="Reconnect"
              >
                Reconnect
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Terminal Content */}
      <div
        ref={terminalRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed"
        style={{ 
          backgroundColor: '#1a1a1a',
          color: '#e0e0e0',
        }}
      >
        {error && !isConnected && (
          <div className="text-red-400 mb-4 p-3 bg-red-900/20 border border-red-800 rounded">
            <strong>Error:</strong> {error}
          </div>
        )}

        {filteredLines.length === 0 && !error && (
          <div className="text-gray-500 italic">
            {isConnected ? 'Waiting for output...' : 'Connecting to backend...'}
          </div>
        )}

        {filteredLines.map((line, index) => (
          <TerminalLine key={`${index}-${line.slice(0, 20)}`} line={line} />
        ))}
      </div>

      {/* Terminal Footer with Stats */}
      <div className="px-4 py-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-400 font-mono">
        <div className="flex justify-between items-center">
          <span>
            {lines.length} lines total
            {filter !== 'all' && ` • ${filteredLines.length} filtered`}
          </span>
          <span className="flex items-center gap-2">
            <span className={isConnected ? 'text-green-400' : 'text-gray-500'}>
              {isConnected ? '● Streaming' : '○ Offline'}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}

interface TerminalLineProps {
  line: string;
}

function TerminalLine({ line }: TerminalLineProps) {
  // Colorize based on content
  let className = 'whitespace-pre-wrap break-words';
  
  if (line.includes('[ERROR]') || line.includes('✗') || line.includes('failed') || line.includes('ERROR:')) {
    className += ' text-red-400';
  } else if (line.includes('[WARNING]') || line.includes('⚠️') || line.includes('WARNING:')) {
    className += ' text-yellow-400';
  } else if (line.includes('[OK]') || line.includes('✓') || line.includes('completed') || line.includes('SUCCESS')) {
    className += ' text-green-400';
  } else if (line.includes('===') || line.includes('---') || line.includes('OpenMC')) {
    className += ' text-blue-400';
  } else if (line.includes('Run ID:') || line.includes('Spec Hash:') || line.includes('🚀') || line.includes('📡')) {
    className += ' text-cyan-400';
  } else if (line.match(/^\s*\d+\/\d+/)) {
    // Batch numbers
    className += ' text-purple-400';
  } else if (line.includes('INFO:') || line.includes('GET') || line.includes('POST')) {
    className += ' text-gray-500';
  } else if (line.includes('k-effective') || line.includes('keff')) {
    className += ' text-emerald-300 font-semibold';
  } else {
    className += ' text-gray-300';
  }

  return <div className={className}>{line || '\u00A0'}</div>;
}

