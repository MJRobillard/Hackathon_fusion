import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'aonp_backend_url';
const DEFAULT_LOCAL_URL = 'http://localhost:8000';
const DEFAULT_REMOTE_URL = '';

export type BackendMode = 'local' | 'remote';

interface BackendUrlConfig {
  mode: BackendMode;
  localUrl: string;
  remoteUrl: string;
}

export function useBackendUrl() {
  const [config, setConfig] = useState<BackendUrlConfig>(() => {
    if (typeof window === 'undefined') {
      return {
        mode: 'local',
        localUrl: DEFAULT_LOCAL_URL,
        remoteUrl: DEFAULT_REMOTE_URL,
      };
    }

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error('Failed to load backend URL config:', e);
    }

    return {
      mode: 'local',
      localUrl: DEFAULT_LOCAL_URL,
      remoteUrl: DEFAULT_REMOTE_URL,
    };
  });

  // Save to localStorage whenever config changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
      } catch (e) {
        console.error('Failed to save backend URL config:', e);
      }
    }
  }, [config]);

  const setMode = useCallback((mode: BackendMode) => {
    setConfig((prev) => ({ ...prev, mode }));
  }, []);

  const setLocalUrl = useCallback((url: string) => {
    setConfig((prev) => ({ ...prev, localUrl: url }));
  }, []);

  const setRemoteUrl = useCallback((url: string) => {
    setConfig((prev) => ({ ...prev, remoteUrl: url }));
  }, []);

  const currentUrl = config.mode === 'local' ? config.localUrl : config.remoteUrl;

  return {
    mode: config.mode,
    localUrl: config.localUrl,
    remoteUrl: config.remoteUrl,
    currentUrl,
    setMode,
    setLocalUrl,
    setRemoteUrl,
  };
}
