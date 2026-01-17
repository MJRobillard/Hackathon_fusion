'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { BackendUrlProvider, useBackendUrlContext } from '@/lib/backendUrlContext';
import { setBackendUrlGetter } from '@/lib/api';

// Component to sync backend URL with API service
function BackendUrlSync() {
  const { currentUrl } = useBackendUrlContext();
  
  useEffect(() => {
    setBackendUrlGetter(() => currentUrl);
  }, [currentUrl]);
  
  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <BackendUrlProvider>
        <BackendUrlSync />
        {children}
      </BackendUrlProvider>
    </QueryClientProvider>
  );
}

