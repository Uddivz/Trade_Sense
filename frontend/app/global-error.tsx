'use client';

import { useEffect } from 'react';

/**
 * Global Error Boundary — catches errors in the root layout itself (e.g., Providers crash).
 * Must render <html> and <body> because the root layout is bypassed on this error.
 * Next.js App Router convention: file must be named `global-error.tsx` at the app root.
 */
export default function GlobalRootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[TradeSense] Root layout error:', error);
  }, [error]);

  return (
    <html lang="en" className="h-full">
      <body className="min-h-full bg-gray-950 text-white flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="flex items-center justify-center w-20 h-20 mx-auto rounded-2xl bg-red-500/10 border border-red-500/20">
            <svg
              className="w-10 h-10 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>

          <div>
            <h1 className="text-2xl font-bold text-white mb-2">Application Error</h1>
            <p className="text-gray-400 text-sm leading-relaxed">
              The application encountered a critical error and could not load. Please refresh the page.
            </p>
            {error.digest && (
              <p className="mt-3 text-xs font-mono text-gray-600 bg-gray-900 px-3 py-1.5 rounded-lg inline-block">
                Error ID: {error.digest}
              </p>
            )}
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={reset}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Reload Application
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
