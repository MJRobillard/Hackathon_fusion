'use client';

import { useState } from 'react';

interface MissionControlTopBarProps {
  projectName?: string;
  onPlay?: () => void;
  onStop?: () => void;
  onReset?: () => void;
  onCommandPalette?: () => void;
  onOpenDatabase?: () => void;
  onOpenHealth?: () => void;
  isProcessing?: boolean;
}

export function MissionControlTopBar({
  projectName = 'fusion-core-alpha-09',
  onPlay,
  onStop,
  onReset,
  onCommandPalette,
  onOpenDatabase,
  onOpenHealth,
  isProcessing = false,
}: MissionControlTopBarProps) {
  const [showCommandPalette, setShowCommandPalette] = useState(false);

  const handleCommandPalette = () => {
    setShowCommandPalette(true);
    onCommandPalette?.();
  };

  return (
    <header className="h-14 bg-[#0F1115] border-b border-[#1F2937] flex items-center justify-between px-6">
      {/* Left: Logo and Title */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          {/* Logo Icon */}
          <div className="w-8 h-8 bg-blue-600 rounded-md flex items-center justify-center font-mono font-bold text-white text-xs">
            MC
          </div>
          <h1 className="text-sm font-semibold text-gray-200 tracking-wide">
            AI OPENMC 
          </h1>
          <p className="text-xs text-gray-500">By Daertech</p>
        </div>
        
        <div className="h-5 w-px bg-[#1F2937]" />
        
        {/* Project Badge */}
        <div className="px-3 py-1.5 bg-[#14161B] border border-[#1F2937] rounded">
          <span className="font-mono text-xs text-blue-400">
            PROJECT: <span className="text-gray-300">{projectName}</span>
          </span>
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-3">
        {/* System Buttons */}
        <div className="flex items-center gap-1">
          <button
            onClick={onOpenHealth}
            className="p-2 hover:bg-[#1F2937] rounded transition-colors group"
            title="System Health"
          >
            <svg
              className="w-4 h-4 text-emerald-500 group-hover:text-emerald-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
          
          <button
            onClick={onOpenDatabase}
            className="p-2 hover:bg-[#1F2937] rounded transition-colors group"
            title="MongoDB Database"
          >
            <svg
              className="w-4 h-4 text-emerald-500 group-hover:text-emerald-400"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M17.193 9.555c-1.264-5.58-4.252-7.414-4.573-8.115-.28-.394-.53-.954-.735-1.44-.036.495-.055.685-.523 1.184-.723.566-4.438 3.682-4.74 10.02-.282 5.912 4.27 9.435 4.888 9.884l.07.05A73.49 73.49 0 0011.91 24h.481c.114-1.032.284-2.056.51-3.07.417-.296 4.488-3.3 4.488-8.944 0-.954-.126-1.77-.196-2.431z"/>
            </svg>
          </button>
        </div>
        
        <div className="h-5 w-px bg-[#1F2937]" />
        
        {/* Control Buttons */}
        <div className="flex items-center gap-1 p-1 bg-[#14161B] border border-[#1F2937] rounded">
          <button
            onClick={onPlay}
            disabled={isProcessing}
            className="p-2 hover:bg-[#1F2937] rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
            title="Play"
          >
            <svg
              className="w-4 h-4 text-emerald-500 group-hover:text-emerald-400"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M8 5v14l11-7z" />
            </svg>
          </button>
          
          <button
            onClick={onStop}
            disabled={!isProcessing}
            className="p-2 hover:bg-[#1F2937] rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed group"
            title="Stop"
          >
            <svg
              className="w-4 h-4 text-red-500 group-hover:text-red-400"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <rect x="6" y="6" width="12" height="12" />
            </svg>
          </button>
          
          <button
            onClick={onReset}
            className="p-2 hover:bg-[#1F2937] rounded transition-colors group"
            title="Reset"
          >
            <svg
              className="w-4 h-4 text-blue-500 group-hover:text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>

        {/* Command Palette Button */}
        <button
          onClick={handleCommandPalette}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          Agentic Prompting
        </button>
      </div>
    </header>
  );
}

