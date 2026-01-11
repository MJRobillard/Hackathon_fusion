// Example: Integrate RAG Copilot into Mission Control
// This shows how to add the RAG components to your existing page

'use client';

import { useState } from 'react';
import { TopBar } from '@/components/TopBar';
import { RunsSidebar } from '@/components/RunsSidebar';
import { AgentWorkflow } from '@/components/AgentWorkflow';
import { ExecutionLogs } from '@/components/ExecutionLogs';
import { ResultsPanel } from '@/components/ResultsPanel';
import { TelemetrySidebar } from '@/components/TelemetrySidebar';
import { StatusFooter } from '@/components/StatusFooter';

// NEW: Import RAG components
import RAGCopilotPanel from '@/components/RAGCopilotPanel';
import RAGAgentCard from '@/components/RAGAgentCard';

export default function MissionControlWithRAG() {
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);
  const [activeQuery, setActiveQuery] = useState<string>('');
  const [routing, setRouting] = useState<any>(null);
  const [showRAGPanel, setShowRAGPanel] = useState(true); // Toggle RAG panel
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <div className="h-screen flex flex-col bg-[#0A0B0D]">
      {/* Top Bar */}
      <TopBar
        onSubmit={(query, useLLM) => {
          setActiveQuery(query);
          // Submit query logic...
        }}
        isProcessing={isProcessing}
        activeQueryId={activeQueryId || undefined}
      />

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: Runs */}
        <div className="w-80 border-r border-gray-800">
          <RunsSidebar
            activeRunId={activeQueryId || undefined}
            onSelectRun={setActiveQueryId}
          />
        </div>

        {/* Center Panel: Agent Workflow + Logs */}
        <div className="flex-1 flex flex-col">
          {/* Agent Workflow - NOW INCLUDES RAG CARD */}
          <div className="p-4 border-b border-gray-800">
            <h3 className="text-sm font-medium text-gray-400 mb-4">Agent Orchestration</h3>
            
            <div className="grid grid-cols-3 gap-4">
              {/* Router Card */}
              <div className="p-4 bg-gray-900 border border-gray-800 rounded-lg">
                <div className="text-sm font-medium text-white mb-1">Router</div>
                <div className="text-xs text-gray-400">Intent Classification</div>
              </div>

              {/* Specialist Agent Cards */}
              {routing?.agent === 'studies' && (
                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                  <div className="text-sm font-medium text-white mb-1">Studies Agent</div>
                  <div className="text-xs text-gray-400">Running simulation...</div>
                </div>
              )}

              {routing?.agent === 'sweep' && (
                <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                  <div className="text-sm font-medium text-white mb-1">Sweep Agent</div>
                  <div className="text-xs text-gray-400">Parameter sweep...</div>
                </div>
              )}

              {routing?.agent === 'query' && (
                <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                  <div className="text-sm font-medium text-white mb-1">Query Agent</div>
                  <div className="text-xs text-gray-400">Searching database...</div>
                </div>
              )}

              {routing?.agent === 'analysis' && (
                <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                  <div className="text-sm font-medium text-white mb-1">Analysis Agent</div>
                  <div className="text-xs text-gray-400">Comparing runs...</div>
                </div>
              )}

              {/* NEW: RAG COPILOT CARD */}
              {routing?.agent === 'rag_copilot' && (
                <RAGAgentCard
                  status="running"
                  intent={routing?.intent}
                />
              )}
            </div>
          </div>

          {/* Execution Logs */}
          <div className="flex-1 overflow-hidden">
            <ExecutionLogs logs={[]} />
          </div>
        </div>

        {/* Right Sidebar: Toggle between Telemetry and RAG */}
        <div className="w-[360px] border-l border-gray-800 flex flex-col">
          {/* Toggle Tabs */}
          <div className="flex border-b border-gray-800 bg-[#0F1115]">
            <button
              onClick={() => setShowRAGPanel(false)}
              className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
                !showRAGPanel
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              📊 Telemetry
            </button>
            <button
              onClick={() => setShowRAGPanel(true)}
              className={`flex-1 px-4 py-2 text-xs font-medium transition-colors ${
                showRAGPanel
                  ? 'text-purple-400 border-b-2 border-purple-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              🤖 RAG Copilot
            </button>
          </div>

          {/* Panel Content */}
          <div className="flex-1 overflow-hidden">
            {showRAGPanel ? (
              // NEW: RAG COPILOT PANEL
              <RAGCopilotPanel
                queryId={activeQueryId || undefined}
                activeQuery={activeQuery}
              />
            ) : (
              // Original Telemetry Sidebar
              <TelemetrySidebar />
            )}
          </div>
        </div>
      </div>

      {/* Footer */}
      <StatusFooter />
    </div>
  );
}

// ============================================================================
// ALTERNATIVE: RAG AS SEPARATE MODAL/DRAWER
// ============================================================================

export function MissionControlWithRAGModal() {
  const [showRAGModal, setShowRAGModal] = useState(false);
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);
  const [activeQuery, setActiveQuery] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState(false);

  return (
    <>
      {/* Original Mission Control Layout */}
      <div className="h-screen flex flex-col bg-[#0A0B0D]">
        <TopBar
          onSubmit={(query, useLLM) => {
            setActiveQuery(query);
            // If RAG query, show modal
            if (query.toLowerCase().includes('literature') ||
                query.toLowerCase().includes('suggest') ||
                query.toLowerCase().includes('reproducibility')) {
              setShowRAGModal(true);
            }
          }}
          isProcessing={isProcessing}
          activeQueryId={activeQueryId || undefined}
        />

        {/* ... rest of layout ... */}

        {/* RAG Button in Footer */}
        <div className="px-4 py-2 bg-[#050607] border-t border-gray-800 flex items-center justify-between">
          <div className="text-xs text-gray-600">● SYSTEM READY</div>
          
          {/* RAG Copilot Button */}
          <button
            onClick={() => setShowRAGModal(true)}
            className="px-3 py-1 bg-gradient-to-r from-purple-500/20 to-blue-500/20 border border-purple-500/30 rounded-lg hover:bg-purple-500/30 transition-colors"
          >
            <span className="text-xs text-purple-300">🤖 RAG Copilot</span>
          </button>
        </div>
      </div>

      {/* RAG Modal Overlay */}
      {showRAGModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-4xl h-[80vh] bg-[#0A0B0D] border-2 border-purple-500/50 rounded-xl shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-purple-900/50 to-blue-900/50 border-b border-gray-800">
              <h2 className="text-lg font-bold text-white">🤖 RAG Copilot</h2>
              <button
                onClick={() => setShowRAGModal(false)}
                className="px-3 py-1 hover:bg-gray-800 rounded transition-colors text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="h-[calc(100%-73px)] overflow-hidden">
              <RAGCopilotPanel
                queryId={activeQueryId || undefined}
                activeQuery={activeQuery}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ============================================================================
// ALTERNATIVE: RAG IN RESULTS PANEL
// ============================================================================

export function ResultsPanelWithRAG({ queryData }: { queryData: any }) {
  if (queryData?.routing?.agent === 'rag_copilot') {
    return (
      <div className="p-6 space-y-6">
        {/* RAG Response Section */}
        <div className="border-l-4 border-purple-500 pl-4">
          <h3 className="text-lg font-bold text-white mb-2">
            🤖 RAG Copilot Analysis
          </h3>
          <div className="flex gap-2 mb-4">
            <div className="px-2 py-1 bg-purple-500/20 rounded text-xs text-purple-300">
              🚀 Voyage AI
            </div>
            <div className="px-2 py-1 bg-orange-500/20 rounded text-xs text-orange-300">
              🔥 Fireworks
            </div>
          </div>
        </div>

        {/* Intent Badge */}
        <div className="flex items-center gap-2 p-3 bg-gray-900/50 border border-gray-800 rounded-lg">
          <span className="text-2xl">
            {queryData.results.intent === 'literature_search' && '📚'}
            {queryData.results.intent === 'reproducibility' && '🔬'}
            {queryData.results.intent === 'suggest_experiments' && '💡'}
            {queryData.results.intent === 'similar_runs' && '🔍'}
          </span>
          <div>
            <div className="text-xs text-gray-400">Intent</div>
            <div className="text-sm font-medium text-white">
              {queryData.results.intent.replace(/_/g, ' ')}
            </div>
          </div>
        </div>

        {/* Response */}
        <div className="p-4 bg-gray-900/30 border border-gray-800 rounded-lg">
          <div className="whitespace-pre-wrap text-sm text-gray-300 leading-relaxed">
            {queryData.results.result}
          </div>
        </div>

        {/* Technology Footer */}
        <div className="flex items-center justify-center gap-3 pt-4 border-t border-gray-800">
          <span className="text-xs text-gray-500">Powered by</span>
          <div className="flex gap-2">
            <div className="px-2 py-1 bg-purple-500/10 rounded text-xs text-purple-400">
              Voyage-3 Embeddings
            </div>
            <div className="px-2 py-1 bg-orange-500/10 rounded text-xs text-orange-400">
              Llama 3.1 70B
            </div>
            <div className="px-2 py-1 bg-blue-500/10 rounded text-xs text-blue-400">
              ChromaDB
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Regular results for other agents
  return <ResultsPanel results={queryData?.results} analysis={queryData?.analysis} suggestions={queryData?.suggestions} />;
}

