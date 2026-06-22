'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { portfolioApi } from '@/lib/api';
import { usePortfolioStore } from '@/store/portfolioStore';
import type { Transaction, PaginatedResponse } from '@/types';

// ── Constants ─────────────────────────────────────────────────────────────────
const PAGE_SIZE = 50;

// ── Types ─────────────────────────────────────────────────────────────────────
type SortKey = 'trade_date' | 'symbol' | 'transaction_type' | 'quantity' | 'price' | 'net_value';
type SortDir = 'asc' | 'desc';
type TypeFilter = 'ALL' | 'BUY' | 'SELL';

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt = (n: number | null | undefined, decimals = 2) =>
  n == null ? '—' : `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;

const fmtQty = (n: number | null | undefined) =>
  n == null ? '—' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 4 });

const fmtDate = (s: string) =>
  new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

// ── Sub-components ────────────────────────────────────────────────────────────
function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 flex flex-col gap-1">
      <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">{label}</span>
      <span className="text-xl font-bold text-white">{value}</span>
      {sub && <span className="text-xs text-gray-500">{sub}</span>}
    </div>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active) return <span className="ml-1 text-gray-600">↕</span>;
  return <span className="ml-1 text-blue-400">{dir === 'asc' ? '↑' : '↓'}</span>;
}

// ── Pagination bar ─────────────────────────────────────────────────────────────
function PaginationBar({
  page, totalPages, total, pageSize, onPage,
}: {
  page: number;
  totalPages: number;
  total: number;
  pageSize: number;
  onPage: (p: number) => void;
}) {
  if (totalPages <= 1) return null;

  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  // Build visible page numbers: always show first, last, and ±2 around current
  const pages: (number | '…')[] = [];
  const addPage = (p: number) => {
    if (!pages.includes(p)) pages.push(p);
  };
  addPage(1);
  for (let p = Math.max(2, page - 2); p <= Math.min(totalPages - 1, page + 2); p++) addPage(p);
  addPage(totalPages);

  // Insert ellipsis gaps
  const withEllipsis: (number | '…')[] = [];
  let prev = 0;
  for (const p of pages as number[]) {
    if (prev && p - prev > 1) withEllipsis.push('…');
    withEllipsis.push(p);
    prev = p;
  }

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-1">
      <span className="text-sm text-gray-400">
        Showing <span className="text-white font-medium">{from}–{to}</span> of{' '}
        <span className="text-white font-medium">{total}</span> transactions
      </span>
      <div className="flex items-center gap-1">
        {/* Prev */}
        <button
          id="tx-page-prev"
          onClick={() => onPage(page - 1)}
          disabled={page === 1}
          className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          ← Prev
        </button>

        {/* Page numbers */}
        {withEllipsis.map((p, i) =>
          p === '…' ? (
            <span key={`ellipsis-${i}`} className="px-2 text-gray-500 select-none">…</span>
          ) : (
            <button
              key={p}
              id={`tx-page-${p}`}
              onClick={() => onPage(p as number)}
              className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${
                p === page
                  ? 'bg-blue-600 text-white shadow'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {p}
            </button>
          )
        )}

        {/* Next */}
        <button
          id="tx-page-next"
          onClick={() => onPage(page + 1)}
          disabled={page === totalPages}
          className="px-3 py-1.5 rounded-lg text-sm bg-gray-800 text-gray-300 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          Next →
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function TransactionsPage() {
  const { activePortfolio } = usePortfolioStore();

  // Server-state
  const [pageData, setPageData] = useState<PaginatedResponse<Transaction> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);

  // Filters & sort (applied to the current page's items client-side)
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('ALL');
  const [sortKey, setSortKey] = useState<SortKey>('trade_date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const fetchPage = useCallback(async (page: number) => {
    if (!activePortfolio?.id) { setIsLoading(false); return; }
    setIsLoading(true);
    try {
      const res = await portfolioApi.getTransactions(activePortfolio.id, page, PAGE_SIZE);
      setPageData(res.data);
      setCurrentPage(page);
      // Reset client-side filters when navigating pages
      setSearch('');
      setTypeFilter('ALL');
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load transactions.');
    } finally {
      setIsLoading(false);
    }
  }, [activePortfolio]);

  useEffect(() => {
    fetchPage(1);
  }, [fetchPage]);

  // ── Client-side filter + sort (within current page) ────────────────────────
  const visibleRows = useMemo(() => {
    let rows = pageData?.items ?? [];

    if (typeFilter !== 'ALL') rows = rows.filter(t => t.transaction_type === typeFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(t =>
        t.symbol.toLowerCase().includes(q) ||
        (t.broker ?? '').toLowerCase().includes(q) ||
        (t.isin ?? '').toLowerCase().includes(q)
      );
    }

    rows = [...rows].sort((a, b) => {
      let av: string | number = a[sortKey] as string | number;
      let bv: string | number = b[sortKey] as string | number;
      if (sortKey === 'trade_date') { av = new Date(av as string).getTime(); bv = new Date(bv as string).getTime(); }
      else if (typeof av === 'string') { av = av.toLowerCase(); bv = (bv as string).toLowerCase(); }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return rows;
  }, [pageData, typeFilter, search, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const handlePage = (p: number) => { window.scrollTo({ top: 0, behavior: 'smooth' }); fetchPage(p); };

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-10 bg-gray-900 rounded-xl w-1/3" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {[...Array(6)].map((_, i) => <div key={i} className="h-20 bg-gray-900 rounded-xl" />)}
        </div>
        <div className="h-96 bg-gray-900 rounded-xl" />
      </div>
    );
  }

  if (!activePortfolio) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="text-6xl mb-6">📋</div>
        <h1 className="text-2xl font-bold text-white mb-3">No Portfolio Found</h1>
        <p className="text-gray-400 mb-8 max-w-sm">Upload a trade history CSV to create your portfolio.</p>
        <Link href="/dashboard/upload" className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
          Upload Trades
        </Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="text-5xl mb-4">⚠️</div>
        <p className="text-red-400 font-medium">{error}</p>
        <button onClick={() => fetchPage(1)} className="mt-4 text-sm text-blue-400 hover:text-blue-300">
          Retry
        </button>
      </div>
    );
  }

  const total = pageData?.total ?? 0;
  const totalPages = pageData?.total_pages ?? 1;
  const items = pageData?.items ?? [];

  // Stats computed from the full set via totals the server provided
  const buysOnPage = items.filter(t => t.transaction_type === 'BUY').length;
  const sellsOnPage = items.filter(t => t.transaction_type === 'SELL').length;
  const investedOnPage = items.filter(t => t.transaction_type === 'BUY').reduce((s, t) => s + Number(t.net_value), 0);
  const proceedsOnPage = items.filter(t => t.transaction_type === 'SELL').reduce((s, t) => s + Number(t.net_value), 0);
  const feesOnPage = items.reduce((s, t) => s + Number(t.fees ?? 0) + Number(t.brokerage ?? 0) + Number(t.stt ?? 0), 0);

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Transaction History</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {activePortfolio.name} · {activePortfolio.broker_name ?? 'All brokers'} ·{' '}
            <span className="text-white font-medium">{total}</span> total trades
          </p>
        </div>
        <Link
          href="/dashboard/upload"
          className="self-start sm:self-auto px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          + Upload CSV
        </Link>
      </div>

      {/* ── Page Stats ── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard label="Total Trades"   value={String(total)} sub="across all pages" />
        <StatCard label="Buys (page)"    value={String(buysOnPage)} />
        <StatCard label="Sells (page)"   value={String(sellsOnPage)} />
        <StatCard label="Invested (page)" value={fmt(investedOnPage, 0)} />
        <StatCard label="Charges (page)"  value={fmt(feesOnPage, 0)} sub="brokerage + STT + fees" />
      </div>

      {/* ── Filters ── */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none">🔍</span>
          <input
            id="tx-search"
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search symbol, broker, ISIN on this page…"
            className="w-full pl-9 pr-4 py-2.5 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
          />
        </div>
        <div className="flex gap-1 bg-gray-900 border border-gray-700 rounded-lg p-1">
          {(['ALL', 'BUY', 'SELL'] as TypeFilter[]).map(t => (
            <button
              key={t}
              id={`tx-filter-${t.toLowerCase()}`}
              onClick={() => setTypeFilter(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                typeFilter === t
                  ? t === 'BUY' ? 'bg-green-600 text-white shadow'
                  : t === 'SELL' ? 'bg-red-600 text-white shadow'
                  : 'bg-blue-600 text-white shadow'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* ── Table ── */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {/* Table toolbar */}
        <div className="px-6 py-3 border-b border-gray-800 flex items-center justify-between">
          <span className="text-sm text-gray-400">
            Page <span className="text-white font-medium">{currentPage}</span> of{' '}
            <span className="text-white font-medium">{totalPages}</span>
            {(search || typeFilter !== 'ALL') && (
              <> · <span className="text-white font-medium">{visibleRows.length}</span> matching filter</>
            )}
          </span>
          {(search || typeFilter !== 'ALL') && (
            <button
              onClick={() => { setSearch(''); setTypeFilter('ALL'); }}
              className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-400 uppercase tracking-wider bg-gray-800/50">
              <tr>
                {(
                  [
                    { key: 'trade_date',       label: 'Date' },
                    { key: 'symbol',           label: 'Symbol' },
                    { key: 'transaction_type', label: 'Type' },
                    { key: 'quantity',         label: 'Qty',       right: true },
                    { key: 'price',            label: 'Price',     right: true },
                    { key: 'net_value',        label: 'Net Value', right: true },
                  ] as { key: SortKey; label: string; right?: boolean }[]
                ).map(({ key, label, right }) => (
                  <th
                    key={key}
                    onClick={() => handleSort(key)}
                    className={`px-5 py-3 cursor-pointer select-none hover:text-white transition-colors ${right ? 'text-right' : ''}`}
                  >
                    {label}<SortIcon active={sortKey === key} dir={sortDir} />
                  </th>
                ))}
                <th className="px-5 py-3 text-right">Charges</th>
                <th className="px-5 py-3">Broker</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {visibleRows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-16 text-center text-gray-500">
                    {total === 0
                      ? 'No transactions found. Upload a CSV to get started.'
                      : 'No transactions match your current filters.'}
                  </td>
                </tr>
              ) : (
                visibleRows.map(tx => {
                  const isBuy = tx.transaction_type === 'BUY';
                  const charges = Number(tx.fees ?? 0) + Number(tx.brokerage ?? 0) + Number(tx.stt ?? 0) + Number(tx.other_charges ?? 0);
                  return (
                    <tr key={tx.id} className="hover:bg-gray-800/40 transition-colors">
                      <td className="px-5 py-3.5 text-gray-300 whitespace-nowrap font-mono text-xs">
                        {fmtDate(tx.trade_date)}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="font-semibold text-white">{tx.symbol}</div>
                        {tx.isin && <div className="text-xs text-gray-500 font-mono">{tx.isin}</div>}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          isBuy
                            ? 'bg-green-500/15 text-green-400 ring-1 ring-green-500/30'
                            : 'bg-red-500/15 text-red-400 ring-1 ring-red-500/30'
                        }`}>
                          {isBuy ? '▲' : '▼'} {tx.transaction_type}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right text-gray-200 tabular-nums">{fmtQty(tx.quantity)}</td>
                      <td className="px-5 py-3.5 text-right text-gray-200 tabular-nums">{fmt(tx.price)}</td>
                      <td className={`px-5 py-3.5 text-right font-semibold tabular-nums ${isBuy ? 'text-red-300' : 'text-green-300'}`}>
                        {isBuy ? '-' : '+'}{fmt(tx.net_value)}
                      </td>
                      <td className="px-5 py-3.5 text-right text-gray-500 tabular-nums text-xs">
                        {charges > 0 ? fmt(charges) : '—'}
                      </td>
                      <td className="px-5 py-3.5 text-gray-400 text-xs">{tx.broker ?? '—'}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination bar ── */}
        <div className="px-6 py-4 border-t border-gray-800">
          <PaginationBar
            page={currentPage}
            totalPages={totalPages}
            total={total}
            pageSize={PAGE_SIZE}
            onPage={handlePage}
          />
        </div>
      </div>
    </div>
  );
}
