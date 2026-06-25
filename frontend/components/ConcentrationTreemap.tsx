'use client';

import {
  Treemap,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Holding } from '@/types';

// ── Colour palette for treemap cells ─────────────────────────────────────────
// 10 distinct, dark-mode-friendly hues ordered for visual contrast.
const PALETTE = [
  '#3B82F6', // blue-500
  '#8B5CF6', // violet-500
  '#06B6D4', // cyan-500
  '#10B981', // emerald-500
  '#F59E0B', // amber-500
  '#EF4444', // red-500
  '#EC4899', // pink-500
  '#14B8A6', // teal-500
  '#F97316', // orange-500
  '#6366F1', // indigo-500
];

// ── Types ─────────────────────────────────────────────────────────────────────

interface TreemapNode {
  name: string;
  size: number;          // market value — drives cell area
  pnl: number;           // unrealized P&L
  pnlPct: number;        // unrealized P&L %
  color: string;
  [key: string]: unknown; // satisfies Recharts TreemapDataType index signature
}

interface ConcentrationTreemapProps {
  holdings: Holding[];
}

// ── Custom Content Renderer ───────────────────────────────────────────────────

interface CustomContentProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  name?: string;
  color?: string;
  pnlPct?: number;
}

function CustomTreemapContent(props: CustomContentProps) {
  const { x = 0, y = 0, width = 0, height = 0, name, color, pnlPct = 0 } = props;

  // Don't render label if cell is too small
  const showLabel = width > 50 && height > 36;
  const showPnl = width > 60 && height > 55;

  return (
    <g>
      <rect
        x={x + 1}
        y={y + 1}
        width={width - 2}
        height={height - 2}
        rx={6}
        ry={6}
        style={{ fill: color, opacity: 0.85 }}
      />
      {showLabel && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showPnl ? 8 : 0)}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{
            fill: '#fff',
            fontSize: Math.min(14, width / 6),
            fontWeight: 700,
            fontFamily: 'inherit',
          }}
        >
          {name}
        </text>
      )}
      {showPnl && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 14}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{
            fill: pnlPct >= 0 ? '#86EFAC' : '#FCA5A5',
            fontSize: Math.min(11, width / 8),
            fontFamily: 'inherit',
          }}
        >
          {pnlPct >= 0 ? '+' : ''}{(pnlPct * 100).toFixed(1)}%
        </text>
      )}
    </g>
  );
}

// ── Custom Tooltip ────────────────────────────────────────────────────────────

interface TooltipPayload {
  payload?: TreemapNode;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length || !payload[0]?.payload) return null;
  const d = payload[0].payload;
  const pnlPositive = d.pnl >= 0;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-3 shadow-xl text-sm min-w-[160px]">
      <p className="font-bold text-white text-base mb-2">{d.name}</p>
      <div className="space-y-1 text-gray-300">
        <div className="flex justify-between gap-4">
          <span className="text-gray-400">Market Value</span>
          <span className="font-mono">₹{d.size.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-400">Unrealized P&L</span>
          <span className={`font-mono font-semibold ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}>
            {pnlPositive ? '+' : ''}₹{Math.abs(d.pnl).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-gray-400">Return</span>
          <span className={`font-mono font-semibold ${pnlPositive ? 'text-green-400' : 'text-red-400'}`}>
            {pnlPositive ? '+' : ''}{(d.pnlPct * 100).toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

/**
 * ConcentrationTreemap — visualises portfolio allocation by market value.
 * Cell size ∝ position size; P&L % shown inside each cell and on hover tooltip.
 * Implements the HHI concentration chart missing from the original dashboard.
 */
export default function ConcentrationTreemap({ holdings }: ConcentrationTreemapProps) {
  if (!holdings.length) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
        No holdings data available.
      </div>
    );
  }

  // Map holdings → treemap data, sorted by market value descending
  const data: TreemapNode[] = holdings
    .filter((h) => Number(h.market_value) > 0)
    .sort((a, b) => Number(b.market_value) - Number(a.market_value))
    .map((h, i) => ({
      name: h.symbol,
      size: Number(h.market_value),
      pnl: Number(h.unrealized_pnl),
      pnlPct: Number(h.unrealized_pnl_pct),
      color: PALETTE[i % PALETTE.length],
    }));

  const totalValue = data.reduce((sum, d) => sum + d.size, 0);

  return (
    <div>
      {/* Header row: top-3 holdings weight summary */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {data.slice(0, 3).map((d, i) => (
          <div key={d.name} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block w-2.5 h-2.5 rounded-sm flex-shrink-0"
              style={{ backgroundColor: d.color }}
            />
            <span className="text-gray-400">{d.name}</span>
            <span className="text-gray-200 font-mono font-medium">
              {((d.size / totalValue) * 100).toFixed(1)}%
            </span>
            {i < Math.min(data.length - 1, 2) && (
              <span className="text-gray-700 ml-1">·</span>
            )}
          </div>
        ))}
        {data.length > 3 && (
          <span className="text-xs text-gray-600">+{data.length - 3} more</span>
        )}
      </div>

      {/* Treemap */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={data}
            dataKey="size"
            aspectRatio={4 / 3}
            content={<CustomTreemapContent />}
          >
            <Tooltip content={<CustomTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </div>

      {/* Footer note */}
      <p className="text-xs text-gray-600 mt-3 text-center">
        Cell area proportional to market value. Hover for P&L details.
      </p>
    </div>
  );
}
