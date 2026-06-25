'use client';

import { useEffect } from 'react';
import Link from 'next/link';

/**
 * Transactions Segment Error Boundary.
 * Isolates failures in the /dashboard/transactions route — e.g. paginated
 * fetch timeouts or 500s — so the rest of the dashboard is unaffected.
 */
export default function TransactionsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[TradeSense/Transactions] Segment error:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center py-24 px-4 text-center">
      {/* Error icon */}
      <div className="flex items-center justify-center w-16 h-16 mb-6 rounded-2xl bg-orange-500/10 border border-orange-500/20">
        <svg
          className="w-8 h-8 text-orange-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z"
          />
        </svg>
      </div>

      {/* Copy */}
      <h2 className="text-xl font-bold text-white mb-2">Failed to Load Transactions</h2>
      <p className="text-gray-400 text-sm max-w-sm leading-relaxed mb-2">
        We couldn&apos;t retrieve your transaction history. Please try again or check your connection.
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
          id="transactions-error-retry-btn"
          className="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        >
          Try Again
        </button>
        <Link
          href="/dashboard"
          className="px-5 py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-200 text-sm font-medium rounded-lg transition-colors border border-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-950"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
