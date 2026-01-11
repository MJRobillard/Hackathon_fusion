'use client';

import { useState, useEffect, useRef } from 'react';
import { apiService } from '@/lib/api';
import type { RAGResponse, RAGHealth, RAGStats, RunSummary, RunQueryResponse } from '@/lib/types';

interface RAGCopilotPanelProps {
  queryId?: string;
  activeQuery?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  timestamp: Date;
}

export default function RAGCopilotPanel({ queryId, activeQuery }: RAGCopilotPanelProps) {
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
  const [ragHealth, setRagHealth] = useState<RAGHealth | null>(null);
  const [ragStats, setRagStats] = useState<RAGStats | null>(null);
  const [experiments, setExperiments] = useState<RunSummary[]>([]);
  const [experimentsTotal, setExperimentsTotal] = useState<number>(0);
  const [experimentsOffset, setExperimentsOffset] = useState<number>(0);
  const [loadingMoreExperiments, setLoadingMoreExperiments] = useState<boolean>(false);
  const [loading, setLoading] = useState(false);
  const [loadingExperiments, setLoadingExperiments] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'response' | 'stats' | 'health'>('response');
  const [selectedExperiment, setSelectedExperiment] = useState<string | null>(null);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const EXPERIMENTS_PER_PAGE = 20;

  // Fetch RAG health, stats, and experiments on mount
  useEffect(() => {
    fetchRagHealth();
    fetchRagStats();
    fetchExperiments();
  }, []);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchRagHealth = async () => {
    try {
      const health = await apiService.ragGetHealth();
      setRagHealth(health);
    } catch (err) {
      console.error('Failed to fetch RAG health:', err);
    }
  };

  const fetchRagStats = async () => {
    try {
      const stats = await apiService.ragGetStats();
      setRagStats(stats);
    } catch (err) {
      console.error('Failed to fetch RAG stats:', err);
    }
  };

  const fetchExperiments = async (reset: boolean = true) => {
    try {
      if (reset) {
        setLoadingExperiments(true);
        setExperimentsOffset(0);
      } else {
        setLoadingMoreExperiments(true);
      }
      
      const offset = reset ? 0 : experiments.length;
      const response = await apiService.getRuns(EXPERIMENTS_PER_PAGE, offset);
      
      if (reset) {
        setExperiments(response.runs);
        setExperimentsOffset(response.runs.length);
      } else {
        setExperiments(prev => [...prev, ...response.runs]);
        setExperimentsOffset(prev => prev + response.runs.length);
      }
      
      setExperimentsTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch experiments:', err);
    } finally {
      setLoadingExperiments(false);
      setLoadingMoreExperiments(false);
    }
  };

  const loadMoreExperiments = () => {
    if (!loadingMoreExperiments && !loadingExperiments && experiments.length < experimentsTotal) {
      fetchExperiments(false);
    }
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || isSending) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: chatInput.trim(),
      timestamp: new Date(),
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsSending(true);
    setError(null);

    try {
      const response = await apiService.ragQuery(userMessage.content);
      
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.result,
        intent: response.intent,
        timestamp: new Date(),
      };

      setChatMessages(prev => [...prev, assistantMessage]);
      
      // Also update the ragResponse for the old UI if needed
      setRagResponse({
        query: userMessage.content,
        result: response.result,
        intent: response.intent,
      } as RAGResponse);
    } catch (err) {
      console.error('Failed to send message:', err);
      setError(err instanceof Error ? err.message : 'Failed to send message');
      
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: '❌ Failed to get response. Please check your connection and try again.',
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  };

  const getIntentIcon = (intent: string) => {
    switch (intent) {
      case 'literature_search':
        return '📚';
      case 'reproducibility':
        return '🔬';
      case 'suggest_experiments':
        return '💡';
      case 'similar_runs':
        return '🔍';
      default:
        return '🤖';
    }
  };

  const getIntentLabel = (intent: string) => {
    switch (intent) {
      case 'literature_search':
        return 'Literature Search';
      case 'reproducibility':
        return 'Reproducibility Check';
      case 'suggest_experiments':
        return 'Experiment Suggestions';
      case 'similar_runs':
        return 'Similar Runs';
      default:
        return 'General Query';
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="flex h-full bg-[#0A0B0D] border border-gray-800 rounded-lg overflow-hidden">
      {/* Left Panel - Previous Experiments */}
      <div className="w-80 border-r border-gray-800 flex flex-col bg-[#0F1115]">
        <div className="px-4 py-3 border-b border-gray-800 bg-[#0A0B0D]">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Previous Experiments</h3>
              <p className="text-xs text-gray-400 mt-1">
                {experimentsTotal > 0 
                  ? `Showing ${experiments.length} of ${experimentsTotal}`
                  : 'Loading...'}
              </p>
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {loadingExperiments ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-sm text-gray-400">Loading experiments...</div>
            </div>
          ) : experiments.length === 0 ? (
            <div className="text-center py-12 px-4">
              <div className="text-2xl mb-2">🔬</div>
              <div className="text-sm text-gray-400">No experiments found</div>
            </div>
          ) : (
            <>
              <div className="divide-y divide-gray-800">
                {experiments.map((experiment) => (
                  <button
                    key={experiment.run_id}
                    onClick={() => setSelectedExperiment(experiment.run_id)}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-900/50 transition-colors ${
                      selectedExperiment === experiment.run_id ? 'bg-blue-500/10 border-l-2 border-blue-500' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-white truncate mb-1">
                          {experiment.run_id}
                        </div>
                        <div className="text-xs text-gray-400 mb-1">
                          {experiment.geometry}
                          {experiment.enrichment_pct && ` • ${experiment.enrichment_pct}%`}
                        </div>
                      </div>
                      <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                        experiment.status === 'completed' 
                          ? 'bg-green-500/20 text-green-400' 
                          : experiment.status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {experiment.status}
                      </div>
                    </div>
                    
                    {experiment.keff != null && (
                      <div className="flex items-center gap-3 text-xs">
                        <div>
                          <span className="text-gray-500">k-eff:</span>{' '}
                          <span className="text-blue-400 font-mono">{experiment.keff.toFixed(5)}</span>
                          {experiment.keff_std != null && (
                            <span className="text-gray-500"> ± {experiment.keff_std.toFixed(5)}</span>
                          )}
                        </div>
                      </div>
                    )}
                    
                    <div className="text-xs text-gray-500 mt-1.5">
                      {formatDate(experiment.created_at)}
                    </div>
                  </button>
                ))}
              </div>
              
              {/* Load More Button */}
              {experiments.length < experimentsTotal && (
                <div className="px-4 py-3 border-t border-gray-800 bg-[#0A0B0D]">
                  <button
                    onClick={loadMoreExperiments}
                    disabled={loadingMoreExperiments}
                    className="w-full px-3 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded text-xs text-gray-300 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loadingMoreExperiments ? (
                      <>
                        <svg className="animate-spin h-3 w-3 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Loading...
                      </>
                    ) : (
                      <>
                        Load More ({experimentsTotal - experiments.length} remaining)
                      </>
                    )}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Right Panel - RAG Content */}
      <div className="flex-1 flex flex-col min-w-0">
      {/* Header with Branding */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <span className="text-xl">🤖</span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">RAG Copilot</h3>
            <p className="text-xs text-gray-400">Document Intelligence & Suggestions</p>
          </div>
        </div>

         {/* Technology Badges */}
         <div className="flex items-center gap-2">
           <div className="px-2 py-1 bg-orange-500/20 border border-orange-500/30 rounded text-xs text-orange-300 font-mono">
             🔥 Fireworks LLM
           </div>
           <div className="px-2 py-1 bg-blue-500/20 border border-blue-500/30 rounded text-xs text-blue-300 font-mono">
             🗄️ MongoDB
           </div>
           <div className="px-2 py-1 bg-green-500/20 border border-green-500/30 rounded text-xs text-green-300 font-mono">
             ✓ Voyage 
           </div>
         </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-800 bg-[#0F1115]">
        <button
          onClick={() => setActiveTab('response')}
          className={`px-4 py-2 text-xs font-medium transition-colors ${
            activeTab === 'response'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Response
        </button>
        <button
          onClick={() => setActiveTab('stats')}
          className={`px-4 py-2 text-xs font-medium transition-colors ${
            activeTab === 'stats'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          Knowledge Base
        </button>
        <button
          onClick={() => setActiveTab('health')}
          className={`px-4 py-2 text-xs font-medium transition-colors ${
            activeTab === 'health'
              ? 'text-blue-400 border-b-2 border-blue-400'
              : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          System Status
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'response' && (
          <div className="space-y-4 flex flex-col h-full">
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto space-y-4">
              {chatMessages.length === 0 ? (
                <div className="text-center py-12">
                  <div className="text-4xl mb-4">🤖</div>
                  <div className="text-sm text-gray-400 mb-2">RAG Copilot Ready</div>
                  <div className="text-xs text-gray-600">
                    Ask about literature, reproducibility, or get experiment suggestions
                  </div>
                  
                  {/* Example Queries */}
                  <div className="mt-6 space-y-2">
                    <div className="text-xs text-gray-500 mb-3">Example Queries:</div>
                    <div className="text-xs text-left space-y-2">
                      <button
                        onClick={() => setChatInput("What does the literature say about PWR enrichment?")}
                        className="w-full p-2 bg-gray-900/30 border border-gray-800 rounded text-gray-400 hover:bg-gray-900/50 hover:text-gray-300 transition-colors text-left"
                      >
                        💡 "What does the literature say about PWR enrichment?"
                      </button>
                      <button
                        onClick={() => setChatInput("Suggest follow-up experiments for PWR reactors")}
                        className="w-full p-2 bg-gray-900/30 border border-gray-800 rounded text-gray-400 hover:bg-gray-900/50 hover:text-gray-300 transition-colors text-left"
                      >
                        🔬 "Suggest follow-up experiments for PWR reactors"
                      </button>
                      <button
                        onClick={() => setChatInput("Find similar runs to PWR at 4.5%")}
                        className="w-full p-2 bg-gray-900/30 border border-gray-800 rounded text-gray-400 hover:bg-gray-900/50 hover:text-gray-300 transition-colors text-left"
                      >
                        🔍 "Find similar runs to PWR at 4.5%"
                      </button>
                      <button
                        onClick={() => setChatInput("Tell me about fusion neutronics")}
                        className="w-full p-2 bg-gray-900/30 border border-gray-800 rounded text-gray-400 hover:bg-gray-900/50 hover:text-gray-300 transition-colors text-left"
                      >
                        📚 "Tell me about fusion neutronics"
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  {chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-lg p-3 ${
                          message.role === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-800 border border-gray-700 text-gray-200'
                        }`}
                      >
                        {message.role === 'assistant' && message.intent && (
                          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700">
                            <span className="text-lg">{getIntentIcon(message.intent)}</span>
                            <span className="text-xs text-gray-400">
                              {getIntentLabel(message.intent)}
                            </span>
                          </div>
                        )}
                        <div className="text-sm whitespace-pre-wrap leading-relaxed">
                          {message.content}
                        </div>
                        <div className="text-xs text-gray-400 mt-2">
                          {message.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Powered By Footer */}
            {chatMessages.length > 0 && (
              <div className="flex items-center justify-center gap-4 pt-4 border-t border-gray-800">
                <div className="text-xs text-gray-500">Powered by</div>
                  <div className="flex items-center gap-2">
                    <div className="px-2 py-1 bg-orange-500/10 rounded text-xs text-orange-400">
                      NVIDIA Nemotron Nano 9B
                    </div>
                    <div className="px-2 py-1 bg-blue-500/10 rounded text-xs text-blue-400">
                      MongoDB Direct Query
                    </div>
                  </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'stats' && ragStats && (
          <div className="space-y-4">
            <div className="text-sm font-medium text-gray-300 mb-4">Knowledge Base Statistics</div>

             {/* Papers Collection */}
             <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
               <div className="flex items-center justify-between mb-2">
                 <div className="flex items-center gap-2">
                   <span className="text-2xl">📚</span>
                   <div>
                     <div className="text-sm font-medium text-purple-300">Research Papers Read</div>
                     <div className="text-xs text-purple-400/70">
                       {ragStats.collections.papers.description}
                     </div>
                   </div>
                 </div>
                 <div className="text-2xl font-bold text-purple-300">
                   {ragStats.collections.papers.count}
                 </div>
               </div>
               <div className="text-xs text-purple-400/60 mt-2">
                 Learned through Fireworks LLM context
               </div>
             </div>

             {/* Runs Collection */}
             <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
               <div className="flex items-center justify-between mb-2">
                 <div className="flex items-center gap-2">
                   <span className="text-2xl">🔬</span>
                   <div>
                     <div className="text-sm font-medium text-blue-300">Studies Learned From</div>
                     <div className="text-xs text-blue-400/70">
                       {ragStats.collections.runs.description}
                     </div>
                   </div>
                 </div>
                 <div className="text-2xl font-bold text-blue-300">
                   {ragStats.collections.runs.count}
                 </div>
               </div>
               <div className="text-xs text-blue-400/60 mt-2">
                 Available in MongoDB (direct query)
               </div>
             </div>

             {/* RAG Method Info */}
             <div className="p-4 bg-gray-900/50 border border-gray-800 rounded-lg">
               <div className="text-xs text-gray-400 mb-2">RAG Method</div>
               <div className="flex items-center justify-between">
                 <div className="text-sm text-gray-300">{ragStats.vector_store.type}</div>
                 <div className="text-xs text-gray-500">
                   {ragStats.vector_store.location}
                 </div>
               </div>
             </div>
          </div>
        )}

        {activeTab === 'health' && ragHealth && (
          <div className="space-y-4">
            <div className="text-sm font-medium text-gray-300 mb-4">System Health</div>

            {/* Overall Status */}
            <div
              className={`p-4 rounded-lg border-2 ${
                ragHealth.status === 'healthy'
                  ? 'bg-green-500/10 border-green-500/30'
                  : 'bg-red-500/10 border-red-500/30'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-3xl">
                  {ragHealth.status === 'healthy' ? '✅' : '❌'}
                </span>
                <div>
                  <div className="text-sm font-bold text-white">
                    {ragHealth.status === 'healthy' ? 'All Systems Operational' : 'System Error'}
                  </div>
                  <div className="text-xs text-gray-400">RAG Copilot Status</div>
                </div>
              </div>
            </div>

             {/* Component Status */}
             <div className="space-y-3">
               {/* Fireworks LLM */}
               <div className="flex items-center justify-between p-3 bg-gray-900/50 border border-gray-800 rounded-lg">
                 <div className="flex items-center gap-2">
                   <span className="text-lg">🔥</span>
                   <div className="text-sm text-gray-300">Fireworks LLM (NVIDIA Nemotron Nano 9B)</div>
                 </div>
                 <div className="px-2 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400">
                   {ragHealth.fireworks_llm || 'connected'}
                 </div>
               </div>

               {/* MongoDB */}
               <div className="flex items-center justify-between p-3 bg-gray-900/50 border border-gray-800 rounded-lg">
                 <div className="flex items-center gap-2">
                   <span className="text-lg">🗄️</span>
                   <div className="text-sm text-gray-300">MongoDB (Direct Query)</div>
                 </div>
                 <div className="px-2 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400">
                   connected
                 </div>
               </div>

               {/* In-Context Learning */}
               <div className="flex items-center justify-between p-3 bg-gray-900/50 border border-gray-800 rounded-lg">
                 <div className="flex items-center gap-2">
                   <span className="text-lg">🧠</span>
                   <div className="text-sm text-gray-300">In-Context Learning</div>
                 </div>
                 <div className="px-2 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400">
                   enabled
                 </div>
               </div>
             </div>

             {/* Knowledge Base Stats */}
             <div className="grid grid-cols-2 gap-3 pt-4 border-t border-gray-800">
               <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg text-center">
                 <div className="text-2xl font-bold text-purple-300">
                   {ragHealth.papers_indexed}
                 </div>
                 <div className="text-xs text-purple-400/70 mt-1">Papers Read</div>
               </div>
               <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center">
                 <div className="text-2xl font-bold text-blue-300">
                   {ragHealth.runs_indexed}
                 </div>
                 <div className="text-xs text-blue-400/70 mt-1">Studies Learned</div>
               </div>
             </div>
          </div>
        )}
      </div>

      {/* Chat Input Footer */}
      <div className="px-4 py-3 bg-[#050607] border-t border-gray-800">
        {/* Status Bar */}
        <div className="flex items-center justify-between text-xs mb-3">
          <div className="text-gray-600">
            {ragHealth?.status === 'healthy' ? (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                RAG Copilot Online
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 bg-gray-600 rounded-full"></span>
                Checking status...
              </span>
            )}
          </div>
          <div className="text-gray-600 font-mono">
            {ragStats && (
              <>
                {ragStats.collections.papers.count}P + {ragStats.collections.runs.count}R
              </>
            )}
          </div>
        </div>

        {/* Chat Input */}
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about literature, experiments, or reproducibility..."
            disabled={isSending}
            className="flex-1 px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed resize-none"
            rows={2}
          />
          <button
            onClick={sendChatMessage}
            disabled={isSending || !chatInput.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            {isSending ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Thinking...
              </>
            ) : (
              <>
                <span>Send</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </>
            )}
          </button>
        </div>
        
        <div className="text-xs text-gray-600 mt-2">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
      </div>
    </div>
  );
}

