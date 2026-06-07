/**
 * TradeSense — Dashboard Placeholder
 * Full implementation built during Week 4 of the 4-week sprint.
 */
import Link from "next/link";

export const metadata = {
  title: "Dashboard",
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
      <div className="text-center max-w-md px-6">
        <div className="text-6xl mb-6">📊</div>
        <h1 className="text-3xl font-bold text-white mb-3">Dashboard</h1>
        <p className="text-slate-400 mb-8">
          Behavioral analytics dashboard — implemented in Week 4.
          Upload your trade history to get started.
        </p>
        <Link
          href="/upload"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-colors"
        >
          Upload Trade History →
        </Link>
      </div>
    </div>
  );
}
