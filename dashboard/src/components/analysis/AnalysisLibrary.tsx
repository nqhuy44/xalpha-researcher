"use client"

import React from 'react'
import { LayoutGrid, List, Eye, Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import Link from 'next/link'

export function AnalysisLibrary({ suggestions, loading, portfolioSymbols }: { suggestions: any[], loading: boolean, portfolioSymbols: string[] }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 h-64 animate-pulse"></div>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <LayoutGrid className="w-5 h-5 text-violet-500" />
          Active Analysis Library
        </h2>
        <div className="flex bg-slate-800/50 p-1 rounded-lg border border-slate-700">
          <button className="p-1.5 bg-slate-700 text-white rounded-md">
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button className="p-1.5 text-slate-500 hover:text-slate-300">
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {suggestions.map((sug, idx) => {
          const isHolding = portfolioSymbols.includes(sug.symbol);
          const { color, label, icon } = getActionStyle(sug.suggested_action);

          return (
            <div key={idx} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 hover:border-violet-500/40 transition-all group shadow-sm hover:shadow-violet-500/5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl font-black tracking-tighter text-white">{sug.symbol}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${isHolding ? 'bg-violet-500/20 text-violet-500' : 'bg-slate-800 text-slate-500'}`}>
                      {isHolding ? 'Portfolio' : 'Watchlist'}
                    </span>
                  </div>
                  <span className="text-xs font-medium text-slate-500 truncate max-w-[150px] uppercase tracking-wider">{sug.company_name || 'Stock Asset'}</span>
                </div>
                <div className={`flex flex-col items-end ${color}`}>
                  <div className="flex items-center gap-1 font-bold">
                    {label}
                    {icon}
                  </div>
                  <div className="flex items-center gap-1 text-[10px] opacity-70">
                    <Clock className="w-3 h-3" />
                    <span>Expires {new Date(new Date(sug.created_at).getTime() + 7 * 24 * 60 * 60 * 1000).toLocaleDateString('en-GB')}</span>
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/30 rounded-xl p-4 mb-4 border border-slate-800/50 group-hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center gap-2 mb-2 text-violet-400">
                  <div className="p-1 bg-violet-500/20 rounded">
                    <span className="material-symbols-outlined text-xs">psychology</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-widest">Thought Log</span>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed line-clamp-6">
                  "{sug.rationale || 'No analysis reasoning provided.'}"
                </p>
              </div>

              <div className="flex items-center justify-between mb-4 px-1">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Action:</span>
                <span className={`text-sm font-black ${color}`}>
                  {sug.suggested_action} {sug.suggested_shares ? `(${sug.suggested_shares > 0 ? '+' : ''}${sug.suggested_shares} units)` : ''}
                </span>
              </div>

              <Link
                href={`/analysis/${sug.id}`}
                className="w-full bg-slate-800 hover:bg-slate-700 text-white font-bold py-3 rounded-xl transition-all border border-slate-700 flex items-center justify-center gap-2 text-sm shadow-sm active:scale-[0.98]"
              >
                <Eye className="w-4 h-4" />
                View Full Report
              </Link>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function getActionStyle(action: string) {
  const a = action?.toUpperCase() || '';
  if (a.includes('BUY') || a.includes('MUA')) return { color: 'text-vn-up', label: 'Strong Buy', icon: <TrendingUp className="w-4 h-4" /> };
  if (a.includes('SELL') || a.includes('BÁN') || a.includes('REDUCE') || a.includes('GIẢM')) return { color: 'text-vn-down', label: 'Reduce', icon: <TrendingDown className="w-4 h-4" /> };
  return { color: 'text-vn-ref', label: 'Hold', icon: <Minus className="w-4 h-4" /> };
}
