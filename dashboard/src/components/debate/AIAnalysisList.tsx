"use client"

import React, { useState } from 'react'
import { Info, Clock, CheckCircle2, AlertCircle, FileText, X, Zap } from 'lucide-react'
import Link from 'next/link'

export function AIAnalysisList({ suggestions, loading, portfolioSymbols }: { suggestions: any[], loading: boolean, portfolioSymbols: string[] }) {
  const [selectedSug, setSelectedSug] = useState<any>(null);

  if (loading) {
    return (
       <div className="space-y-4 text-center py-8">
          <p className="text-sm text-slate-500 animate-pulse">Consulting AI Agents...</p>
       </div>
    )
  }

  // Filter only tickers in portfolio
  const activeSuggestions = suggestions.filter(sug => portfolioSymbols.includes(sug.symbol));

  if (activeSuggestions.length === 0) {
    return (
       <div className="space-y-4 text-center py-8">
          <p className="text-sm text-slate-500 italic">No analyses for your current holdings</p>
       </div>
    )
  }

  return (
    <div className="space-y-3">
      {activeSuggestions.map((sug: any) => {
        const remainingDays = sug.is_expired ? 0 : 7 - Math.floor((new Date().getTime() - new Date(sug.created_at).getTime()) / (24 * 60 * 60 * 1000));
        const hasShares = sug.suggested_shares !== undefined && sug.suggested_shares !== 0;
        
        return (
          <div 
            key={`${sug.symbol}-${sug.created_at}`} 
            onClick={() => setSelectedSug(sug)}
            className="bg-slate-900/60 rounded-xl p-5 border border-slate-800 hover:border-violet-500/60 transition-all group cursor-pointer hover:bg-slate-800/40 relative overflow-hidden"
          >
            <div className="flex justify-between items-center mb-1">
              <div className="flex items-center gap-3">
                <span className="text-lg font-black tracking-tight text-white">{sug.symbol}</span>
                <span className={`px-2 py-1 rounded text-[10px] border font-black uppercase ${getActionStyle(sug.suggested_action)}`}>
                  {sug.suggested_action}
                </span>
              </div>
              {sug.is_expired || remainingDays <= 0 ? (
                <span className="text-[10px] font-bold text-vn-down">Expired</span>
              ) : (
                <span className="text-[10px] font-bold text-vn-up">{remainingDays}d left</span>
              )}
            </div>

            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-2">
                {hasShares && (
                  <div className="flex items-center gap-1 bg-violet-500/10 border border-violet-500/30 px-2 py-1 rounded-lg">
                    <span className="text-[10px] font-bold text-violet-400 uppercase tracking-tighter">Target:</span>
                    <span className="text-xs font-black text-violet-400">
                      {sug.suggested_shares > 0 ? '+' : ''}{sug.suggested_shares}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1 text-slate-500 group-hover:text-violet-400 transition-colors">
                <span className="text-[10px] font-black uppercase tracking-widest">View Details</span>
                <Info className="w-3.5 h-3.5" />
              </div>
            </div>
          </div>
        )
      })}

      {/* Detail Modal */}
      {selectedSug && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-[#1e293b] border border-slate-700 w-full max-w-3xl rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-violet-600 rounded-xl shadow-lg shadow-violet-500/20">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-black text-white">{selectedSug.symbol} Analysis</h3>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">AI Verdict Report</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedSug(null)}
                className="p-2 hover:bg-slate-800 rounded-full text-slate-400 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-8 space-y-8">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <div className="p-5 bg-slate-900/50 rounded-2xl border border-slate-800 flex flex-col items-center text-center justify-center min-h-[120px]">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 border-b border-slate-800 pb-1 w-full">Recommended Action</p>
                  <p className={`text-lg font-black leading-tight ${getActionStyleString(selectedSug.suggested_action)}`}>
                    {selectedSug.suggested_action}
                  </p>
                </div>
                <div className="p-5 bg-violet-600/10 rounded-2xl border border-violet-600/30 flex flex-col items-center text-center justify-center min-h-[120px]">
                  <p className="text-[10px] font-bold text-violet-500 uppercase tracking-widest mb-2 border-b border-violet-500/10 pb-1 w-full">Target Units</p>
                  <p className="text-xl font-black text-violet-400">
                    {selectedSug.suggested_shares > 0 ? '+' : ''}{selectedSug.suggested_shares || '0'} 
                    <span className="text-[10px] ml-1 opacity-60">Units</span>
                  </p>
                </div>
                <div className="p-5 bg-slate-900/50 rounded-2xl border border-slate-800 flex flex-col items-center text-center justify-center min-h-[120px]">
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 border-b border-slate-800 pb-1 w-full">Confidence Score</p>
                  <div className="flex flex-col items-center gap-2 w-full px-2">
                    <span className="text-xl font-black text-white">{selectedSug.analyst_confidence}%</span>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div className="bg-emerald-500 h-full shadow-[0_0_8px_rgba(16,185,129,0.5)]" style={{ width: `${selectedSug.analyst_confidence}%` }} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-violet-400">
                  <span className="material-symbols-outlined text-sm">psychology</span>
                  <span className="text-xs font-black uppercase tracking-widest">AI Rationale</span>
                </div>
                <div className="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 italic leading-relaxed text-slate-200 shadow-inner">
                  "{selectedSug.rationale}"
                </div>
              </div>

              <div className="flex items-center justify-between pt-4">
                <div className="flex items-center gap-4 text-xs font-bold text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(selectedSug.created_at).toLocaleDateString('en-GB')}
                  </div>
                </div>
                <Link 
                  href={`/analysis/${selectedSug.id}`}
                  className="bg-violet-600 hover:bg-violet-700 text-white px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 shadow-lg shadow-violet-500/20 transition-all active:scale-[0.98]"
                >
                  <FileText className="w-4 h-4" />
                  Full Report
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function getActionStyle(action: string) {
  const a = action?.toUpperCase() || '';
  if (a.includes('BUY') || a.includes('MUA') || a.includes('GIA_TĂNG')) 
    return 'bg-vn-up/20 text-vn-up border-vn-up/40 font-bold';
  if (a.includes('CHỐT_LỜI') || a.includes('TAKE_PROFIT')) 
    return 'bg-vn-up/30 text-vn-up border-vn-up/50 font-black shadow-lg shadow-vn-up/10 ring-1 ring-vn-up/50';
  if (a.includes('SELL') || a.includes('BÁN') || a.includes('REDUCE') || a.includes('GIẢM') || a.includes('CẮT_LỖ') || a.includes('STOP_LOSS')) 
    return 'bg-vn-down/20 text-vn-down border-vn-down/40 font-bold';
  if (a.includes('CẮT_LỖ'))
    return 'bg-vn-down/30 text-vn-down border-vn-down/50 font-black shadow-lg shadow-vn-down/10 ring-1 ring-vn-down/50';
  if (a.includes('HOLD') || a.includes('GIỮ')) 
    return 'bg-vn-ref/20 text-vn-ref border-vn-ref/40 font-bold';
  return 'bg-violet-500/20 text-violet-500 border-violet-500/30';
}

function getActionStyleString(action: string) {
  const a = action?.toUpperCase() || '';
  if (a.includes('BUY') || a.includes('MUA') || a.includes('GIA_TĂNG') || a.includes('CHỐT_LỜI')) return 'text-vn-up';
  if (a.includes('SELL') || a.includes('BÁN') || a.includes('REDUCE') || a.includes('GIẢM') || a.includes('CẮT_LỖ')) return 'text-vn-down';
  return 'text-vn-ref';
}
