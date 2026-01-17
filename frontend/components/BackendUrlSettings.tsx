'use client';

import { useState } from 'react';
import { Settings, Server, Globe, Check, X } from 'lucide-react';
import { useBackendUrl } from '@/hooks/useBackendUrl';

interface BackendUrlSettingsProps {
  onClose?: () => void;
}

export function BackendUrlSettings({ onClose }: BackendUrlSettingsProps) {
  const { mode, localUrl, remoteUrl, setMode, setLocalUrl, setRemoteUrl, currentUrl } = useBackendUrl();
  const [localInput, setLocalInput] = useState(localUrl);
  const [remoteInput, setRemoteInput] = useState(remoteUrl);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTestConnection = async () => {
    const urlToTest = mode === 'local' ? localInput : remoteInput;
    if (!urlToTest) {
      setTestResult({ success: false, message: 'Please enter a URL' });
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await fetch(`${urlToTest}/api/v1/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });

      if (response.ok) {
        setTestResult({ success: true, message: 'Connection successful!' });
      } else {
        setTestResult({ success: false, message: `Server responded with status ${response.status}` });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Connection failed';
      setTestResult({ success: false, message: `Failed to connect: ${message}` });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    setLocalUrl(localInput);
    setRemoteUrl(remoteInput);
    if (onClose) onClose();
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-4 min-w-[400px]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Settings size={18} className="text-gray-400" />
          <h3 className="text-sm font-semibold text-gray-200">Backend Connection</h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Mode Toggle */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-gray-400">Connection Mode</label>
        <div className="flex gap-2">
          <button
            onClick={() => setMode('local')}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border transition ${
              mode === 'local'
                ? 'bg-blue-600/20 border-blue-500 text-blue-400'
                : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
            }`}
          >
            <Server size={14} />
            <span className="text-xs font-medium">Local</span>
          </button>
          <button
            onClick={() => setMode('remote')}
            className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg border transition ${
              mode === 'remote'
                ? 'bg-blue-600/20 border-blue-500 text-blue-400'
                : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
            }`}
          >
            <Globe size={14} />
            <span className="text-xs font-medium">Remote</span>
          </button>
        </div>
      </div>

      {/* Local URL Input */}
      {mode === 'local' && (
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400">Local Backend URL</label>
          <input
            type="text"
            value={localInput}
            onChange={(e) => setLocalInput(e.target.value)}
            placeholder="http://localhost:8000"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      )}

      {/* Remote URL Input */}
      {mode === 'remote' && (
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-400">Remote Backend URL</label>
          <input
            type="text"
            value={remoteInput}
            onChange={(e) => setRemoteInput(e.target.value)}
            placeholder="https://your-backend.com"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      )}

      {/* Current URL Display */}
      <div className="bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2">
        <div className="text-xs text-gray-400 mb-1">Current Backend URL</div>
        <div className="text-sm font-mono text-gray-300 break-all">{currentUrl || 'Not set'}</div>
      </div>

      {/* Test Connection */}
      <div className="space-y-2">
        <button
          onClick={handleTestConnection}
          disabled={isTesting || !(mode === 'local' ? localInput : remoteInput)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700 rounded-lg text-sm text-gray-200 transition-colors"
        >
          {isTesting ? (
            <>
              <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
              <span>Testing...</span>
            </>
          ) : (
            <>
              <Check size={14} />
              <span>Test Connection</span>
            </>
          )}
        </button>
        {testResult && (
          <div
            className={`text-xs px-2 py-1 rounded ${
              testResult.success
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-red-500/20 text-red-400 border border-red-500/30'
            }`}
          >
            {testResult.message}
          </div>
        )}
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
      >
        Save Settings
      </button>
    </div>
  );
}
