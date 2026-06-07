/**
 * TradeSense — React Query + Zustand Providers
 * Wraps the application with all required context providers.
 */
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  // Create QueryClient inside component so it's not shared between requests (SSR safety)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,         // 1 minute — behavioral metrics don't change that fast
            retry: 1,                      // Retry once on failure
            refetchOnWindowFocus: false,   // Don't refetch on every tab switch
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
