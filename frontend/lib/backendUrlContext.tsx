'use client';

import { createContext, useContext, ReactNode } from 'react';
import { useBackendUrl, BackendMode } from '@/hooks/useBackendUrl';

interface BackendUrlContextType {
  mode: BackendMode;
  localUrl: string;
  remoteUrl: string;
  currentUrl: string;
  setMode: (mode: BackendMode) => void;
  setLocalUrl: (url: string) => void;
  setRemoteUrl: (url: string) => void;
}

const BackendUrlContext = createContext<BackendUrlContextType | undefined>(undefined);

export function BackendUrlProvider({ children }: { children: ReactNode }) {
  const backendUrl = useBackendUrl();
  return <BackendUrlContext.Provider value={backendUrl}>{children}</BackendUrlContext.Provider>;
}

export function useBackendUrlContext() {
  const context = useContext(BackendUrlContext);
  if (context === undefined) {
    throw new Error('useBackendUrlContext must be used within a BackendUrlProvider');
  }
  return context;
}
