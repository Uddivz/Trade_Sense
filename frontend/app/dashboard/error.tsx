'use client';

import { useEffect } from 'react';
import Link from 'next/link';

/**
 * Dashboard Segment Error Boundary.
 * Catches errors thrown by any route within /dashboard/** without crashing
 * the entire application. The navbar remains visible via the dashboard layout.
 */
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[TradeSense/Dashboard] Segment error:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center py-24 px-4 text-center">
      {/* Error icon */}
      <div className="flex items-center justify-center w-16 h-16 mb-6 rounded-2xl bg-red-500/10 border border-red-500/20">
        <svg
          className="w-8 h-8 text-red-400"
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

      {/* Copy */}
      <h2 className="text-xl font-bold text-white mb-2">Failed to Load Dashboard</h2>
      <p className="text-gray-400 text-sm max-w-sm leading-relaxed mb-2">
        We couldn&apos;t fetch your portfolio data. This may be a temporary issue with the API.
      </p>
      {error.message && (
        <p className="text-xs font-mono text-gray-600 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg mb-6 max-w-xs truncate">
          {error.message}
        </p>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={reset}
          id="dashboard-error-retry-btn"
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        >
          Try Again
        </button>
        <Link
          href="/dashboard/upload"
          className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg transition-colors border border-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        >
          Upload Trades
        </Link>
      </div>

      {/* Tip */}
      <p className="mt-8 text-xs text-gray-600">
        If this keeps happening, make sure the backend server is running on{' '}
        <span className="font-mono">localhost:8000</span>.
      </p>
    </div>
  );
}
