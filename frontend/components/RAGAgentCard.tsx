'use client';

interface RAGAgentCardProps {
  status: 'waiting' | 'running' | 'complete' | 'failed';
  intent?: string;
}

export default function RAGAgentCard({ status, intent }: RAGAgentCardProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'running':
        return 'border-blue-500/50 bg-blue-500/10';
      case 'complete':
        return 'border-green-500/50 bg-green-500/10';
      case 'failed':
        return 'border-red-500/50 bg-red-500/10';
      default:
        return 'border-gray-700 bg-gray-900/30';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>;
      case 'complete':
        return <div className="text-green-400">✓</div>;
      case 'failed':
        return <div className="text-red-400">✗</div>;
      default:
        return <div className="w-2 h-2 bg-gray-600 rounded-full"></div>;
    }
  };

  return (
    <div
      className={`relative p-4 rounded-lg border-2 transition-all duration-300 ${getStatusColor()}`}
    >
      {/* Gradient Glow Effect */}
      {status === 'running' && (
        <div className="absolute inset-0 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-lg animate-pulse"></div>
      )}

      <div className="relative">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <span className="text-lg">🤖</span>
            </div>
            <div>
              <div className="text-sm font-bold text-white">RAG Copilot</div>
              <div className="text-xs text-gray-400">Document Intelligence</div>
            </div>
          </div>
          {getStatusIcon()}
        </div>

        {/* Technology Stack */}
        <div className="flex flex-wrap gap-2 mb-3">
        <div className="px-2 py-0.5 bg-orange-500/20 border border-orange-500/30 rounded text-xs text-orange-300 font-mono">
            Voyage Embeddings 
          </div>
          <div className="px-2 py-0.5 bg-orange-500/20 border border-orange-500/30 rounded text-xs text-orange-300 font-mono">
            🔥 Fireworks
          </div>
          <div className="px-2 py-0.5 bg-orange-500/20 border border-green-500/30 rounded text-xs text-orange-300 font-mono">
             Voyage Embeddings! 🚀
          </div>
          <div className="px-2 py-0.5 bg-blue-500/20 border border-blue-500/30 rounded text-xs text-blue-300 font-mono">
            🗄️ MongoDB
          </div>
        </div>

        {/* Status Message */}
        <div className="text-xs text-gray-400">
          {status === 'waiting' && 'Waiting for query...'}
          {status === 'running' && (
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-1 h-3 bg-blue-400 rounded animate-pulse"></div>
                <div className="w-1 h-3 bg-blue-400 rounded animate-pulse delay-75"></div>
                <div className="w-1 h-3 bg-blue-400 rounded animate-pulse delay-150"></div>
              </div>
              <span>
                {intent === 'literature_search' && 'Searching research papers...'}
                {intent === 'reproducibility' && 'Analyzing reproducibility...'}
                {intent === 'suggest_experiments' && 'Generating suggestions...'}
                {intent === 'similar_runs' && 'Finding similar runs...'}
                {!intent && 'Processing with RAG...'}
              </span>
            </div>
          )}
          {status === 'complete' && 'Analysis complete'}
          {status === 'failed' && 'Analysis failed'}
        </div>

        {/* Intent Badge */}
        {intent && status === 'running' && (
          <div className="mt-3 p-2 bg-gray-900/50 rounded border border-gray-800">
            <div className="text-xs text-gray-500">Intent:</div>
            <div className="text-xs text-gray-300 font-medium">
              {intent.replace(/_/g, ' ')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

