'use client';

import { useEffect, useState, useCallback } from 'react';
import { apiService } from '@/lib/api';
import type { LogEntry, AgentStatus } from '@/lib/types';

export interface AgentThought {
  timestamp: string;
  agent: string;
  type: 'thinking' | 'decision' | 'tool_call' | 'observation' | 'planning';
  content: string;
  metadata?: Record<string, any>;
}

export function useEventStream(queryId: string | null) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([
    { agent: 'router', status: 'waiting' },
  ]);
  const [agentThoughts, setAgentThoughts] = useState<AgentThought[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const addLog = useCallback((source: LogEntry['source'], message: string, level: LogEntry['level'] = 'info') => {
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        source,
        message,
        level,
      },
    ]);
  }, []);

  const updateAgentStatus = useCallback(
    (agent: AgentStatus['agent'], status: AgentStatus['status'], duration?: number) => {
      setAgentStatuses((prev) => {
        const exists = prev.find((a) => a.agent === agent);
        if (exists) {
          return prev.map((a) =>
            a.agent === agent ? { ...a, status, duration } : a
          );
        }
        return [...prev, { agent, status, duration }];
      });
    },
    []
  );

  const addThought = useCallback((agent: string, type: AgentThought['type'], content: string, metadata?: Record<string, any>) => {
    setAgentThoughts((prev) => [
      ...prev,
      {
        timestamp: new Date().toLocaleTimeString(),
        agent,
        type,
        content,
        metadata,
      },
    ]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
    setAgentStatuses([{ agent: 'router', status: 'waiting' }]);
    setAgentThoughts([]);
  }, []);

  useEffect(() => {
    if (!queryId) {
      setIsConnected(false);
      return;
    }

    const eventSource = apiService.createEventStream(queryId);
    setIsConnected(true);

    eventSource.onopen = () => {
      addLog('SYSTEM', 'Connected to event stream', 'success');
    };

    eventSource.addEventListener('routing', (e) => {
      const data = JSON.parse(e.data);
      addLog('ROUTER', data.message || 'Routing query...');
      updateAgentStatus('router', 'running');
    });

    eventSource.addEventListener('routing_complete', (e) => {
      const data = JSON.parse(e.data);
      addLog('ROUTER', `✓ Routed to: ${data.agent} (${data.intent})`, 'success');
      updateAgentStatus('router', 'complete', data.duration);
      
      // Initialize target agent
      if (data.agent) {
        updateAgentStatus(data.agent as AgentStatus['agent'], 'running');
      }
    });

    eventSource.addEventListener('agent_start', (e) => {
      const data = JSON.parse(e.data);
      addLog(data.agent.toUpperCase() as LogEntry['source'], 'Starting execution...');
      updateAgentStatus(data.agent as AgentStatus['agent'], 'running');
    });

    eventSource.addEventListener('agent_progress', (e) => {
      const data = JSON.parse(e.data);
      addLog(data.agent.toUpperCase() as LogEntry['source'], data.message);
    });

    eventSource.addEventListener('tool_call', (e) => {
      const data = JSON.parse(e.data);
      addLog('TOOL', `${data.tool_name} - ${data.message || 'Executing...'}`);
      // Show exactly what the agent passed to the tool (args) in Agent Reasoning
      addThought(
        data.agent || 'System',
        'tool_call',
        data.message || `Calling tool ${data.tool_name}`,
        {
          tool_name: data.tool_name,
          args: data.args,
        }
      );
    });

    eventSource.addEventListener('tool_result', (e) => {
      const data = JSON.parse(e.data);
      addLog('TOOL', `✓ ${data.tool_name} completed`, 'success');
      addThought(
        data.agent || 'System',
        'observation',
        data.message || `Tool ${data.tool_name} returned results`,
        {
          tool_name: data.tool_name,
          result: data.result,
        }
      );
    });

    // New: Agent thinking events
    eventSource.addEventListener('agent_thinking', (e) => {
      const data = JSON.parse(e.data);
      // Back-compat: some backends embed a more specific subtype in `data.type`
      const subtype = (data?.type as AgentThought['type'] | undefined) || 'thinking';
      const normalized: AgentThought['type'] =
        subtype === 'observation' || subtype === 'planning' || subtype === 'decision' || subtype === 'tool_call'
          ? subtype
          : 'thinking';
      addThought(data.agent, normalized, data.content, data.metadata);
    });

    eventSource.addEventListener('agent_decision', (e) => {
      const data = JSON.parse(e.data);
      addThought(data.agent, 'decision', data.content, data.metadata);
      addLog(data.agent.toUpperCase() as LogEntry['source'], `Decision: ${data.content}`);
    });

    eventSource.addEventListener('agent_planning', (e) => {
      const data = JSON.parse(e.data);
      addThought(data.agent, 'planning', data.content, data.metadata);
    });

    // New: explicit observation events (preferred over stuffing subtype into agent_thinking)
    eventSource.addEventListener('agent_observation', (e) => {
      const data = JSON.parse(e.data);
      addThought(data.agent, 'observation', data.content, data.metadata);
    });

    eventSource.addEventListener('query_complete', (e) => {
      const data = JSON.parse(e.data);
      addLog('SYSTEM', '✓ Query completed successfully', 'success');
      
      // Mark all agents as complete
      setAgentStatuses((prev) =>
        prev.map((a) => (a.status === 'running' ? { ...a, status: 'complete' } : a))
      );
      
      eventSource.close();
      setIsConnected(false);
    });

    eventSource.addEventListener('query_error', (e) => {
      const data = JSON.parse(e.data);
      addLog('SYSTEM', `✗ Error: ${data.error}`, 'error');
      
      // Mark all running agents as failed
      setAgentStatuses((prev) =>
        prev.map((a) => (a.status === 'running' ? { ...a, status: 'failed' } : a))
      );
      
      eventSource.close();
      setIsConnected(false);
    });

    eventSource.onerror = () => {
      addLog('SYSTEM', 'Event stream connection lost', 'warning');
      setIsConnected(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [queryId, addLog, updateAgentStatus]);

  return { logs, agentStatuses, agentThoughts, isConnected, clearLogs };
}

