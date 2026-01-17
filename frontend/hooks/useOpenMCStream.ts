import { useState, useEffect, useRef } from 'react';
import { useBackendUrl } from './useBackendUrl';

interface UseOpenMCStreamReturn {
  lines: string[];
  isConnected: boolean;
  error: string | null;
  isComplete: boolean;
  reconnect: () => void;
}

/**
 * Hook to consume Server-Sent Events from OpenMC simulation stream
 * 
 * @param runId - The run identifier
 * @returns Stream state and control functions
 */
export function useOpenMCStream(runId: string): UseOpenMCStreamReturn {
  const { currentUrl } = useBackendUrl();
  const [lines, setLines] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = () => {
    if (!runId) {
      setError('No run ID provided');
      return;
    }

    try {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Use backend URL from hook
      const streamUrl = `${currentUrl}/runs/${runId}/stream`;

      console.log('Connecting to OpenMC stream:', streamUrl);

      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('OpenMC stream connected');
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        const line = event.data;
        
        // Check if simulation is complete
        if (line.includes('[OK]') && line.includes('Results written')) {
          setIsComplete(true);
          eventSource.close();
          setIsConnected(false);
        }
        
        // Add line to output
        setLines((prev) => [...prev, line]);
      };

      eventSource.onerror = (err) => {
        console.error('OpenMC stream error:', err);
        setIsConnected(false);
        
        // Check if it's a completion (not an error)
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log('Stream closed');
          // Don't set error if we received data (likely normal completion)
          if (lines.length === 0) {
            setError('Connection closed before receiving data');
          }
        } else {
          setError('Stream connection error');
          
          // Attempt to reconnect after 2 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connect();
          }, 2000);
        }
        
        eventSource.close();
      };

    } catch (err) {
      console.error('Failed to create EventSource:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect to stream');
      setIsConnected(false);
    }
  };

  const reconnect = () => {
    setLines([]);
    setError(null);
    setIsComplete(false);
    setIsConnected(false);
    connect();
  };

  // Connect on mount and when URL or runId changes
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [runId, currentUrl]);

  return {
    lines,
    isConnected,
    error,
    isComplete,
    reconnect,
  };
}

