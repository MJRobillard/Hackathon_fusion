'use client';

import { useState } from 'react';
import { MissionControlTopBar } from '@/components/MissionControlTopBar';
import { RunsSidebar } from '@/components/RunsSidebar';
import { AgentPanel } from '@/components/AgentPanel';
import { MissionControlLogs } from '@/components/MissionControlLogs';
import { TelemetrySidebar } from '@/components/TelemetrySidebar';
import { StatusFooter } from '@/components/StatusFooter';

export default function MissionControlPage() {
  const [activeRunId, setActiveRunId] = useState('OM-945');
  const [isProcessing, setIsProcessing] = useState(true);

  const handlePlay = () => {
    setIsProcessing(true);
  };

  const handleStop = () => {
    setIsProcessing(false);
  };

  const handleReset = () => {
    setIsProcessing(false);
    // Reset logic here
  };

  const handleCommandPalette = () => {
    // Open command palette modal
    console.log('Command palette triggered');
  };

  const handleSelectRun = (runId: string) => {
    setActiveRunId(runId);
  };

  return (
    <div className="h-screen w-screen bg-[#0A0B0D] flex flex-col overflow-hidden">
      {/* Top Bar */}
      <MissionControlTopBar
        projectName="fusion-core-alpha-09"
        onPlay={handlePlay}
        onStop={handleStop}
        onReset={handleReset}
        onCommandPalette={handleCommandPalette}
        isProcessing={isProcessing}
      />

      {/* Main Content Grid */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Runs */}
        <RunsSidebar activeRunId={activeRunId} onSelectRun={handleSelectRun} />

        {/* Center Panel */}
        <div className="flex-1 flex flex-col gap-4 p-4 overflow-hidden">
          {/* Agent Orchestration */}
          <AgentPanel currentTask="Flux Optimization Layer (Node-4)" />

          {/* Execution Logs */}
          <MissionControlLogs showCursor={isProcessing} />
        </div>

        {/* Right Sidebar: Telemetry */}
        <TelemetrySidebar />
      </div>

      {/* Footer */}
      <StatusFooter
        systemStatus={isProcessing ? 'busy' : 'ready'}
        version="OpenMC v0.14.0"
        cores={128}
        coreUsage={isProcessing ? 82 : 0}
        latency={42}
        tokenConsumption={1.2}
        eta="14:48:00"
      />
    </div>
  );
}

