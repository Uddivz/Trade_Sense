'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { portfolioApi, analyticsApi } from '@/lib/api';
import { usePortfolioStore } from '@/store/portfolioStore';
import { BehavioralMetricResponse, Holding, Recommendation } from '@/types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

export default function DashboardPage() {
  const { activePortfolio, setActivePortfolio } = usePortfolioStore();
  const [metrics, setMetrics] = useState<BehavioralMetricResponse | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        let currentPortfolioId = activePortfolio?.id;
        
        // Ensure portfolio
        if (!currentPortfolioId) {
          const res = await portfolioApi.list();
          if (res.data && res.data.length > 0) {
            setActivePortfolio(res.data[0]);
            currentPortfolioId = res.data[0].id;
          } else {
            setIsLoading(false);
            return;
          }
        }

        // Fetch data in parallel
        const [holdingsRes, analyticsRes, recRes] = await Promise.all([
          portfolioApi.getHoldings(currentPortfolioId as string),
          analyticsApi.getSummary(currentPortfolioId as string).catch(() => ({ data: null })), // Catch 404
          analyticsApi.getRecommendations()
        ]);

        setHoldings(holdingsRes.data);
        if (analyticsRes.data) setMetrics(analyticsRes.data);
        setRecommendations(recRes.data);

      } catch (err) {
        console.error('Dashboard fetch error:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [activePortfolio, setActivePortfolio]);

  const dismissRecommendation = async (id: string) => {
    try {
      await analyticsApi.dismissRecommendation(id);
      setRecommendations(recommendations.filter(r => r.id !== id));
    } catch (err) {
      console.error('Failed to dismiss', err);
    }
  };

  if (isLoading) {
    return <div className="animate-pulse flex flex-col gap-6 p-4">
      <div className="h-32 bg-gray-900 rounded-xl"></div>
      <div className="h-64 bg-gray-900 rounded-xl"></div>
    </div>;
  }

  if (!activePortfolio || !metrics) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-6xl mb-6">📊</div>
        <h1 className="text-3xl font-bold text-white mb-3">Welcome to TradeSense</h1>
        <p className="text-slate-400 mb-8 max-w-md">
          Upload your trade history CSV to generate behavioral insights and see your dashboard.
        </p>
        <Link href="/dashboard/upload" className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
          Upload Trades
        </Link>
      </div>
    );
  }

  const pgrPlrData = [
    { name: 'Gains (PGR)', Realized: metrics.pgr || 0, Paper: 1 - (metrics.pgr || 0) },
    { name: 'Losses (PLR)', Realized: metrics.plr || 0, Paper: 1 - (metrics.plr || 0) },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      {/* ── Left Column: Analytics & Charts ── */}
      <div className="lg:col-span-2 space-y-6">
        
        {/* Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-sm text-gray-400 font-medium">Disposition Effect</div>
            <div className={`text-2xl font-bold mt-1 ${metrics.disposition_effect_score && metrics.disposition_effect_score > 0.05 ? 'text-red-400' : 'text-green-400'}`}>
              {(metrics.disposition_effect_score || 0).toFixed(2)}
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-sm text-gray-400 font-medium">Concentration (HHI)</div>
            <div className={`text-2xl font-bold mt-1 ${metrics.hhi && metrics.hhi > 2500 ? 'text-red-400' : 'text-blue-400'}`}>
              {Math.round(metrics.hhi || 0)}
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-sm text-gray-400 font-medium">Turnover (PTR)</div>
            <div className="text-2xl font-bold text-white mt-1">
              {((metrics.portfolio_turnover_ratio || 0) * 100).toFixed(1)}%
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-sm text-gray-400 font-medium">Cost Drag</div>
            <div className="text-2xl font-bold text-yellow-400 mt-1">
              {((metrics.cost_drag_pct || 0) * 100).toFixed(2)}%
            </div>
          </div>
        </div>

        {/* Chart: PGR vs PLR */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-bold text-white mb-4">Disposition Effect Analysis</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pgrPlrData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                <XAxis dataKey="name" stroke="#9CA3AF" />
                <YAxis stroke="#9CA3AF" />
                <Tooltip contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', color: '#fff' }} />
                <Legend />
                <Bar dataKey="Realized" stackId="a" fill="#3B82F6" />
                <Bar dataKey="Paper" stackId="a" fill="#6B7280" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Holdings Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800 bg-gray-900/50">
            <h3 className="font-bold text-white">Current Holdings</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-300">
              <thead className="text-xs text-gray-400 uppercase bg-gray-800/50">
                <tr>
                  <th className="px-6 py-3">Symbol</th>
                  <th className="px-6 py-3">Qty</th>
                  <th className="px-6 py-3 text-right">Avg Cost</th>
                  <th className="px-6 py-3 text-right">Market Value</th>
                  <th className="px-6 py-3 text-right">Unrealized P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-b border-gray-800 hover:bg-gray-800/50">
                    <td className="px-6 py-4 font-medium text-white">{h.symbol}</td>
                    <td className="px-6 py-4">{Number(h.quantity).toFixed(2)}</td>
                    {/* BUG-05 FIX: Use correct field names matching backend HoldingResponse */}
                    <td className="px-6 py-4 text-right">₹{Number(h.average_cost).toFixed(2)}</td>
                    <td className="px-6 py-4 text-right">₹{Number(h.market_value).toFixed(2)}</td>
                    <td className={`px-6 py-4 text-right font-medium ${Number(h.unrealized_pnl) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {Number(h.unrealized_pnl) >= 0 ? '+' : ''}₹{Number(h.unrealized_pnl).toFixed(2)}
                      <span className="text-xs ml-1 opacity-70">
                        ({Number(h.unrealized_pnl_pct) >= 0 ? '+' : ''}{(Number(h.unrealized_pnl_pct) * 100).toFixed(2)}%)
                      </span>
                    </td>
                  </tr>
                ))}
                {holdings.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">No active holdings found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* ── Right Column: Recommendations ── */}
      <div className="space-y-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span>💡</span> Coaching Insights
          </h3>
          
          <div className="space-y-4">
            {recommendations.length === 0 ? (
              <div className="text-sm text-gray-500 text-center py-6">
                Your portfolio looks healthy! No active recommendations.
              </div>
            ) : (
              recommendations.map(rec => (
                <div key={rec.id} className={`p-4 rounded-xl border ${rec.severity === 'HIGH' ? 'bg-red-500/10 border-red-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
                  <div className="flex justify-between items-start mb-2">
                    <h4 className={`font-semibold ${rec.severity === 'HIGH' ? 'text-red-400' : 'text-yellow-400'}`}>
                      {rec.title}
                    </h4>
                    <button 
                      onClick={() => dismissRecommendation(rec.id)}
                      className="text-gray-500 hover:text-gray-300 text-xs px-2 py-1 bg-gray-900/50 rounded"
                    >
                      Dismiss
                    </button>
                  </div>
                  <p className="text-sm text-gray-300 leading-relaxed mb-3">
                    {rec.body}
                  </p>
                  <div className="text-xs bg-gray-950/50 rounded-lg p-2 font-mono text-gray-400">
                    Rule ID: {rec.rule_id}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

    </div>
  );
}
