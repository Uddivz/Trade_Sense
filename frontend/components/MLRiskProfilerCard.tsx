'use client';

import React from 'react';
import { MLRiskScoreResponse } from '@/types';

interface MLRiskProfilerCardProps {
  mlRisk: MLRiskScoreResponse | null;
}

const FEATURE_LABELS: Record<string, string> = {
  disposition_effect_score: 'Disposition Effect',
  hhi: 'Portfolio Concentration (HHI)',
  portfolio_turnover_ratio: 'Portfolio Turnover (PTR)',
  cost_drag_pct: 'Transaction Cost Drag',
  pgr: 'Proportion of Gains Realized',
  plr: 'Proportion of Losses Realized',
};

const FEATURE_DESCRIPTIONS: Record<string, string> = {
  disposition_effect_score: 'Urge to sell winners quickly and hold losers too long.',
  hhi: 'Level of asset concentration. Higher score equals higher concentration risk.',
  portfolio_turnover_ratio: 'Frequency of buying and selling. Elevated PTR implies overtrading.',
  cost_drag_pct: 'Performance drag due to broker fees, taxes, and other transactional costs.',
  pgr: 'Rate at which profitable holdings are realized relative to total paper gains.',
  plr: 'Rate at which losing holdings are realized relative to total paper losses.',
};

const formatFeatureValue = (feature: string, value: number): string => {
  if (feature === 'hhi') {
    return Math.round(value).toString();
  }
  if (feature === 'portfolio_turnover_ratio' || feature === 'cost_drag_pct' || feature === 'pgr' || feature === 'plr') {
    return `${(value * 100).toFixed(1)}%`;
  }
  return value.toFixed(2);
};

export default function MLRiskProfilerCard({ mlRisk }: MLRiskProfilerCardProps) {
  if (!mlRisk) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-4"></div>
        <p className="text-gray-400 text-sm">Computing ML Risk Profile...</p>
      </div>
    );
  }

  const { risk_label, confidence, shap_explanation, model_version } = mlRisk;

  // ── Needle calculations for the speedometer ──────────────────────────────
  let angle = 90; // Default center (Medium)
  if (risk_label === 'LOW') angle = 150;     // Left
  else if (risk_label === 'MEDIUM') angle = 90; // Center
  else if (risk_label === 'HIGH') angle = 30;   // Right

  const rad = (angle * Math.PI) / 180;
  const needleLength = 28;
  const targetX = 50 + needleLength * Math.cos(rad);
  const targetY = 50 - needleLength * Math.sin(rad);

  // ── SHAP contribution bar calculations ──────────────────────────────────
  const maxShap = Math.max(
    ...shap_explanation.map((item) => Math.abs(item.shap_value)),
    0.01
  );

  // Color mappings
  const badgeColors = {
    LOW: 'bg-green-500/10 text-green-400 border-green-500/30',
    MEDIUM: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    HIGH: 'bg-red-500/10 text-red-400 border-red-500/30',
  };

  const riskMutedColors = {
    LOW: 'text-green-500',
    MEDIUM: 'text-amber-500',
    HIGH: 'text-red-500',
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-lg transition-all duration-300 hover:border-gray-700/80">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-gray-800 pb-4 mb-6">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <span>🧠</span> ML Behavioral Risk Profile
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            XGBoost classification based on real-time portfolio metrics
          </p>
        </div>
        <div className="mt-3 md:mt-0 flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${badgeColors[risk_label]}`}>
            {risk_label} RISK
          </span>
          <span className="text-xs font-mono text-gray-500" title={`Model version used for inference: ${model_version}`}>
            v{model_version}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-center">
        {/* Speedometer Column (2/5 span) */}
        <div className="lg:col-span-2 flex flex-col items-center border-r border-gray-800/50 pr-0 lg:pr-8">
          <div className="relative w-full max-w-[200px]">
            <svg viewBox="0 0 100 60" className="w-full drop-shadow-[0_4px_12px_rgba(0,0,0,0.5)]">
              <defs>
                <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#10B981" />   {/* Green */}
                  <stop offset="50%" stopColor="#F59E0B" />  {/* Yellow */}
                  <stop offset="100%" stopColor="#EF4444" /> {/* Red */}
                </linearGradient>
              </defs>
              {/* Gauge Track */}
              <path
                d="M 10 50 A 40 40 0 0 1 90 50"
                fill="none"
                stroke="url(#gaugeGradient)"
                strokeWidth="7"
                strokeLinecap="round"
                opacity="0.85"
              />
              {/* Needle Point Center Pin */}
              <circle cx="50" cy="50" r="4.5" fill="#fff" />
              <circle cx="50" cy="50" r="2.5" fill="#1f2937" />
              {/* Needle */}
              <line
                x1="50"
                y1="50"
                x2={targetX}
                y2={targetY}
                stroke="#ffffff"
                strokeWidth="2.5"
                strokeLinecap="round"
                className="transition-all duration-1000 ease-out"
              />
            </svg>
            <div className="text-center mt-2">
              <span className="text-xs text-gray-400 font-medium">Confidence</span>
              <div className="text-xl font-extrabold text-white mt-0.5">
                {(confidence * 100).toFixed(1)}%
              </div>
            </div>
          </div>
          
          <div className="mt-4 text-center px-4">
            <p className="text-sm text-gray-300 leading-relaxed">
              Your overall trading profile is classified as{' '}
              <strong className={riskMutedColors[risk_label]}>{risk_label.toLowerCase()}-risk</strong>. 
              {risk_label === 'HIGH' && ' High-risk behavior indicates severe exposure to emotional bias, overtrading, or overconcentration.'}
              {risk_label === 'MEDIUM' && ' Moderate-risk behavior indicates minor emotional bias or turnover, with room for structural optimization.'}
              {risk_label === 'LOW' && ' Excellent risk control! You maintain disciplined hold patterns, low costs, and a balanced portfolio.'}
            </p>
          </div>
        </div>

        {/* SHAP Explanations Column (3/5 span) */}
        <div className="lg:col-span-3 space-y-5">
          <div>
            <h4 className="text-sm font-semibold text-gray-300">Behavioral Risk Drivers (SHAP Explanations)</h4>
            <p className="text-xs text-gray-500 mt-1">
              Relative feature contributions pushing the rating towards low-risk (left) or high-risk (right)
            </p>
          </div>

          <div className="space-y-4">
            {shap_explanation.map((item) => {
              const label = FEATURE_LABELS[item.feature] || item.feature;
              const desc = FEATURE_DESCRIPTIONS[item.feature] || '';
              const displayVal = formatFeatureValue(item.feature, item.value);
              const percentage = Math.min((Math.abs(item.shap_value) / maxShap) * 50, 50);

              const isIncrease = item.direction === 'increases_risk';

              return (
                <div key={item.feature} className="group relative">
                  <div className="flex justify-between items-baseline mb-1">
                    <span className="text-xs font-semibold text-gray-300 group-hover:text-white transition-colors">
                      {label}
                    </span>
                    <span className="text-xs font-mono font-bold text-gray-400 bg-gray-800 px-1.5 py-0.5 rounded">
                      {displayVal}
                    </span>
                  </div>

                  {/* Bidirectional Bar */}
                  <div className="relative h-6 bg-gray-950/60 rounded-md border border-gray-800/40 overflow-hidden flex items-center">
                    {/* Centered zero marker line */}
                    <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-800 z-10"></div>
                    
                    {/* Reduces Risk Bar (extends left from center) */}
                    {!isIncrease && (
                      <div
                        className="absolute right-1/2 h-full bg-gradient-to-l from-emerald-500/80 to-teal-600/70 rounded-l-sm"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    )}

                    {/* Increases Risk Bar (extends right from center) */}
                    {isIncrease && (
                      <div
                        className="absolute left-1/2 h-full bg-gradient-to-r from-orange-500/80 to-red-600/70 rounded-r-sm"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    )}

                    {/* Label markers inside bar */}
                    <span className="absolute left-3 text-[10px] font-medium text-green-500/60 pointer-events-none select-none">
                      - Risk
                    </span>
                    <span className="absolute right-3 text-[10px] font-medium text-red-500/60 pointer-events-none select-none">
                      + Risk
                    </span>
                  </div>

                  {/* Feature description tooltip on hover */}
                  <p className="text-[10px] text-gray-500 mt-1 max-h-0 overflow-hidden group-hover:max-h-12 transition-all duration-300 ease-in-out">
                    {desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
