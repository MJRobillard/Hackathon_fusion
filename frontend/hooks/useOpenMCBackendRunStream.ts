import { useEffect, useRef, useState } from 'react';

export interface OpenMCRunToolEvent {
  timestamp: string;
  agent?: string;
  type: 'tool_call' | 'tool_result' | 'openmc_error';
  tool_name?: string;
  message?: string;
  args?: Record<string, any>;
  result?: Record<string, any>;
  error?: string;
}

interface UseOpenMCBackendRunStreamReturn {
  logLines: string[];
  toolEvents: OpenMCRunToolEvent[];
  isConnected: boolean;
  error: string | null;
  clear: () => void;
}

/**
 * Streams OpenMC run output through the main backend proxy:
 *   GET /api/v1/openmc/simulations/{runId}/stream  (SSE)
 */
export function useOpenMCBackendRunStream(runId: string | null): UseOpenMCBackendRunStreamReturn {
  const [logLines, setLogLines] = useState<string[]>([]);
  const [toolEvents, setToolEvents] = useState<OpenMCRunToolEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const clear = () => {
    setLogLines([]);
    setToolEvents([]);
  };

  useEffect(() => {
    if (!runId) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${apiUrl}/api/v1/openmc/simulations/${runId}/stream`;

    // Close any prior stream
    if (esRef.current) esRef.current.close();

    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    es.addEventListener('openmc_log', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        const content = data?.content ?? '';
        if (typeof content === 'string' && content.length > 0) {
          setLogLines((prev) => [...prev.slice(-2000), content]);
        }
      } catch {
        // ignore
      }
    });

    es.addEventListener('tool_call', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        setToolEvents((prev) => [
          ...prev.slice(-200),
          {
            timestamp: new Date().toLocaleTimeString(),
            agent: data.agent,
            type: 'tool_call',
            tool_name: data.tool_name,
            message: data.message,
            args: data.args,
          },
        ]);
      } catch {
        // ignore
      }
    });

    es.addEventListener('tool_result', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        const summary =
          (typeof data?.result?.summary === 'string' && data.result.summary) ||
          (typeof data?.result?.prompt === 'string' && data.result.prompt) ||
          undefined;
        setToolEvents((prev) => [
          ...prev.slice(-200),
          {
            timestamp: new Date().toLocaleTimeString(),
            agent: data.agent,
            type: 'tool_result',
            tool_name: data.tool_name,
            message: summary,
            result: data.result,
          },
        ]);
      } catch {
        // ignore
      }
    });

    es.addEventListener('openmc_error', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        const err = data?.error || 'OpenMC stream error';
        setError(err);
        setToolEvents((prev) => [
          ...prev.slice(-200),
          {
            timestamp: new Date().toLocaleTimeString(),
            type: 'openmc_error',
            error: err,
          },
        ]);
      } catch {
        setError('OpenMC stream error');
      }
    });

    es.addEventListener('agent_thinking', (e) => {
      try {
        const data = JSON.parse((e as MessageEvent).data);
        const content = data?.content || '';
        if (typeof content === 'string' && content.length > 0) {
          setToolEvents((prev) => [
            ...prev.slice(-200),
            {
              timestamp: new Date().toLocaleTimeString(),
              agent: data.agent,
              type: 'tool_call',
              tool_name: 'agent_blip',
              message: content,
              args: data.metadata,
            },
          ]);
        }
      } catch {
        // ignore
      }
    });

    es.onerror = () => {
      setIsConnected(false);
      // Keep error minimal; proxy will send openmc_error when appropriate
    };

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [runId]);

  return { logLines, toolEvents, isConnected, error, clear };
}


