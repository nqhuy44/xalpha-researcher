"use client"

import React from 'react'
import { MoreHorizontal, ShoppingCart, Tag } from 'lucide-react'

export function PortfolioTable({ positions, loading, showValues }: { positions: any[], loading: boolean, showValues: boolean }) {
  if (loading) {
    return (
      <div className="bg-slate-900/30 rounded-xl border border-slate-800 p-12 text-center text-slate-400">
        Loading portfolio data...
      </div>
    )
  }

  if (positions.length === 0) {
    return (
      <div className="bg-slate-900/30 rounded-xl border border-slate-800 p-12 text-center text-slate-400">
        No positions found. Start by adding a transaction.
      </div>
    )
  }

  return (
    <div className="bg-slate-900/30 rounded-xl border border-slate-800 overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-800/50 text-slate-400 text-[10px] font-bold uppercase tracking-widest">
              <th className="px-6 py-4">Ticker</th>
              <th className="px-6 py-4">Quantity</th>
              <th className="px-6 py-4 text-right">Avg Cost</th>
              <th className="px-6 py-4 text-right">Market Price</th>
              <th className="px-6 py-4">Allocation</th>
              <th className="px-6 py-4 text-right">P&L (%)</th>
              <th className="px-6 py-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {positions.map((pos) => {
              if (pos.symbol === 'CASH') return null;
              
              const marketPrice = pos.market_price || pos.avg_price;
              const pnl = pos.pnl_percent || 0;
              
              // Ticker color logic
              let tickerColor = 'text-slate-200';
              if (pnl > 0) tickerColor = 'text-vn-up';
              else if (pnl < 0) tickerColor = 'text-vn-down';
              else tickerColor = 'text-vn-ref';

              return (
                <tr key={pos.symbol} className="hover:bg-slate-800/30 transition-colors border-b border-slate-800/50 last:border-0">
                  <td className="px-6 py-4">
                    <span className={`font-bold ${tickerColor}`}>{pos.symbol}</span>
                  </td>
                  <td className="px-6 py-4 text-slate-400">
                    {showValues ? pos.shares.toLocaleString() : '••••'}
                  </td>
                  <td className="px-6 py-4 text-right text-white">
                    {showValues ? pos.avg_price.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '••••'}
                  </td>
                  <td className={`px-6 py-4 text-right font-semibold ${pnl > 0 ? 'text-vn-up' : pnl < 0 ? 'text-vn-down' : 'text-vn-ref'}`}>
                    {showValues ? marketPrice.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '••••'}
                  </td>
                  <td className="px-6 py-4 text-sm font-medium">
                    <div className="flex items-center gap-2 min-w-[100px]">
                      <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div className="h-full bg-violet-500" style={{ width: `${pos.weight_percent || 0}%` }}></div>
                      </div>
                      <span className="text-xs font-medium">{(pos.weight_percent || 0).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className={`px-6 py-4 text-right font-bold ${pnl > 0 ? 'text-vn-up' : pnl < 0 ? 'text-vn-down' : 'text-vn-ref'}`}>
                    {pnl > 0 ? '+' : ''}{pnl.toFixed(2)}%
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex justify-center gap-2">
                      <button className="p-1 hover:text-vn-up">
                        <ShoppingCart className="w-5 h-5" />
                      </button>
                      <button className="p-1 hover:text-vn-down">
                        <Tag className="w-5 h-5" />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
