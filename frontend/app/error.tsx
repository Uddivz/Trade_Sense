'use client';

import { useEffect } from 'react';

/**
 * Root Error Boundary — catches unhandled errors in any segment below the root layout.
 * Next.js App Router convention: must be a Client Component with `reset` prop.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log to console (will be replaced with structured logging later)
    console.error('[TradeSense] Unhandled error:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center space-y-6">
        {/* Icon */}
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

        {/* Heading */}
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Something went wrong</h1>
          <p className="text-gray-400 text-sm leading-relaxed">
            An unexpected error occurred. This has been logged and our team will look into it.
          </p>
          {error.digest && (
            <p className="mt-3 text-xs font-mono text-gray-600 bg-gray-900 px-3 py-1.5 rounded-lg inline-block">
              Error ID: {error.digest}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <button
            onClick={reset}
            className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950"
          >
            Try Again
          </button>
          <a
            href="/dashboard"
            className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg transition-colors border border-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-950"
          >
            Go to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}
