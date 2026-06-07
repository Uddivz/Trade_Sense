/**
 * TradeSense — Landing Page
 * Redirects authenticated users to dashboard; shows marketing content to guests.
 */
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-6">
      {/* Hero */}
      <div className="text-center max-w-3xl">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-sm font-medium mb-8">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse" />
          Behavioral Analytics Platform
        </div>

        <h1 className="text-5xl sm:text-6xl font-bold text-white leading-tight tracking-tight">
          Turn Trading History Into{" "}
          <span className="bg-gradient-to-r from-blue-400 to-violet-400 bg-clip-text text-transparent">
            Behavioral Intelligence
          </span>
        </h1>

        <p className="mt-6 text-xl text-slate-400 leading-relaxed">
          TradeSense analyzes your broker's CSV and surfaces the behavioral
          biases costing you returns — disposition effect, overtrading,
          concentration risk, and more.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/register"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-lg transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
          >
            Get Started Free
          </Link>
          <Link
            href="/login"
            className="w-full sm:w-auto px-8 py-4 rounded-xl border border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white font-semibold text-lg transition-all duration-200"
          >
            Sign In →
          </Link>
        </div>
      </div>

      {/* Feature Pills */}
      <div className="mt-20 flex flex-wrap justify-center gap-3">
        {[
          "📊 Disposition Effect",
          "🔄 Overtrading Detection",
          "🎯 Concentration Risk",
          "🧠 Behavioral Risk Score",
          "💡 Personalized Recommendations",
        ].map((feat) => (
          <span
            key={feat}
            className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 text-sm"
          >
            {feat}
          </span>
        ))}
      </div>

      <p className="mt-16 text-slate-600 text-sm">
        Upload your Zerodha CSV → Get behavioral analytics in seconds
      </p>
    </main>
  );
}
