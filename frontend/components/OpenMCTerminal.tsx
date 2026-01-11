'use client';

import { useState, useEffect, useRef } from 'react';
import { useOpenMCStream } from '@/hooks/useOpenMCStream';

interface OpenMCTerminalProps {
  runId: string;
  autoScroll?: boolean;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export default function OpenMCTerminal({ 
  runId, 
  autoScroll = true,
  onComplete,
  onError 
}: OpenMCTerminalProps) {
  const { lines, isConnected, error, isComplete } = useOpenMCStream(runId);
  const terminalRef = useRef<HTMLDivElement>(null);
  const [isPaused, setIsPaused] = useState(false);

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    if (autoScroll && !isPaused && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines, autoScroll, isPaused]);

  // Notify parent when complete
  useEffect(() => {
    if (isComplete && onComplete) {
      onComplete();
    }
  }, [isComplete, onComplete]);

  // Notify parent of errors
  useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

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
    navigator.clipboard.writeText(text).then(() => {
      // Could show a toast notification here
    });
  };

  const downloadLog = () => {
    const text = lines.join('');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `openmc-${runId}-${Date.now()}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

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
            OpenMC Output - {runId}
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className="flex items-center gap-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 
              isComplete ? 'bg-blue-500' : 
              error ? 'bg-red-500' : 
              'bg-gray-500'
            }`}></div>
            <span className="text-gray-400">
              {isConnected ? 'Streaming...' : 
               isComplete ? 'Complete' : 
               error ? 'Error' : 
               'Disconnected'}
            </span>
          </div>

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
        {error && (
          <div className="text-red-400 mb-4 p-3 bg-red-900/20 border border-red-800 rounded">
            <strong>Error:</strong> {error}
          </div>
        )}

        {lines.length === 0 && !error && (
          <div className="text-gray-500 italic">
            Waiting for simulation output...
          </div>
        )}

        {lines.map((line, index) => (
          <TerminalLine key={index} line={line} index={index} />
        ))}

        {isComplete && (
          <div className="mt-4 text-green-400">
            ─── Simulation Complete ───
          </div>
        )}
      </div>

      {/* Terminal Footer with Stats */}
      <div className="px-4 py-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-400 font-mono">
        <div className="flex justify-between items-center">
          <span>{lines.length} lines</span>
          <span>Run ID: {runId}</span>
        </div>
      </div>
    </div>
  );
}

interface TerminalLineProps {
  line: string;
  index: number;
}

function TerminalLine({ line, index }: TerminalLineProps) {
  // Colorize based on content
  let className = 'whitespace-pre-wrap break-words';
  
  if (line.includes('[ERROR]') || line.includes('✗') || line.includes('failed')) {
    className += ' text-red-400';
  } else if (line.includes('[WARNING]') || line.includes('⚠️')) {
    className += ' text-yellow-400';
  } else if (line.includes('[OK]') || line.includes('✓') || line.includes('completed')) {
    className += ' text-green-400';
  } else if (line.includes('===') || line.includes('---')) {
    className += ' text-blue-400';
  } else if (line.includes('Run ID:') || line.includes('Spec Hash:')) {
    className += ' text-cyan-400';
  } else if (line.match(/^\s*\d+\/\d+/)) {
    // Batch numbers
    className += ' text-purple-400';
  } else if (line.includes('INFO:') || line.includes('GET') || line.includes('POST')) {
    className += ' text-gray-500';
  } else {
    className += ' text-gray-300';
  }

  return <div className={className}>{line || '\u00A0'}</div>;
}

