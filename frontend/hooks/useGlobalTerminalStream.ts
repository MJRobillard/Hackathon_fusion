import { useState, useEffect, useRef } from 'react';

interface TerminalEvent {
  timestamp: string;
  stream: 'stdout' | 'stderr' | 'system';
  content: string;
}

interface UseGlobalTerminalStreamReturn {
  lines: string[];
  events: TerminalEvent[];
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
  clear: () => void;
}

/**
 * Hook to consume global terminal stream from backend
 * Captures ALL backend output (stdout + stderr)
 * 
 * @returns Stream state and control functions
 */
export function useGlobalTerminalStream(): UseGlobalTerminalStreamReturn {
  const [lines, setLines] = useState<string[]>([]);
  const [events, setEvents] = useState<TerminalEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = () => {
    try {
      // Close existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Connect to main API for terminal stream
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const streamUrl = `${apiUrl}/api/v1/terminal/stream`;

      console.log('Connecting to global terminal stream:', streamUrl);

      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('Terminal stream connected');
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data: TerminalEvent = JSON.parse(event.data);
          
          // Add to events list
          setEvents((prev) => [...prev.slice(-1000), data]); // Keep last 1000 events
          
          // Add content to lines
          if (data.content) {
            setLines((prev) => [...prev, data.content]);
          }
        } catch (err) {
          console.error('Failed to parse terminal event:', err);
        }
      };

      eventSource.onerror = (err) => {
        // Silently handle error - don't spam console
        setIsConnected(false);
        
        if (eventSource.readyState === EventSource.CLOSED) {
          // Don't reconnect automatically if endpoint doesn't exist (404)
          // Only show error once
          if (!error) {
            setError('Terminal stream endpoint not available. Start the backend server with terminal streaming enabled.');
            console.warn('Terminal stream endpoint not available at:', streamUrl);
          }
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
    setEvents([]);
    setError(null);
    setIsConnected(false);
    
    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    connect();
  };

  const clear = () => {
    setLines([]);
    setEvents([]);
  };

  // Connect on mount
  useEffect(() => {
    // Add a small delay before connecting to avoid race conditions
    const timer = setTimeout(() => {
      connect();
    }, 1000);

    // Cleanup on unmount
    return () => {
      clearTimeout(timer);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return {
    lines,
    events,
    isConnected,
    error,
    reconnect,
    clear,
  };
}

