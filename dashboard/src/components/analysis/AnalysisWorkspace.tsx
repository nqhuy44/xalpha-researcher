"use client"

import React, { useState } from 'react'
import { Search, Zap, ListChecks, CheckCircle2 } from 'lucide-react'

export function AnalysisWorkspace() {
  const [tickers, setTickers] = useState("")
  const [depth, setDepth] = useState("debate")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ text: string, type: 'success' | 'error' } | null>(null)

  const handleRunAnalysis = async () => {
    if (!tickers) return;
    setLoading(true);
    setMessage(null);
    const symbols = tickers.split(',').map(s => s.trim().toUpperCase());
    
    try {
      for (const symbol of symbols) {
        const res = await fetch(`/api/portfolio/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol })
        });
        if (!res.ok) throw new Error(`Failed to analyze ${symbol}`);
      }
      setMessage({ text: `Successfully triggered analysis for ${symbols.join(', ')}`, type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  }

  const handleBulkAnalyze = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch('/api/analysis/bulk', {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to trigger bulk analysis');
      const data = await res.json();
      setMessage({ text: data.message, type: 'success' });
    } catch (err: any) {
      setMessage({ text: err.message, type: 'error' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-[#1e293b]/50 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden h-full">
      <div className="flex items-center gap-2 mb-6">
        <div className="p-2 bg-violet-600 rounded-lg shadow-lg shadow-violet-500/20">
          <Zap className="w-5 h-5 text-white fill-white" />
        </div>
        <h2 className="text-xl font-bold">Analysis Workspace</h2>
      </div>

      <div className="space-y-6">
        <div>
          <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Tickers</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input 
              type="text" 
              value={tickers}
              onChange={(e) => setTickers(e.target.value)}
              placeholder="e.g. FPT, VNM, HPG"
              className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl pl-10 pr-4 py-3 text-sm focus:ring-2 focus:ring-violet-500 outline-none transition-all"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Analysis Depth</label>
          <select 
            value={depth}
            onChange={(e) => setDepth(e.target.value)}
            className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-violet-500 outline-none transition-all appearance-none text-white italic"
          >
            <option value="debate">Bull-Bear AI Debate (Deep Insight)</option>
          </select>
        </div>

        {message && (
          <div className={`p-4 rounded-xl text-xs font-bold flex items-center gap-2 ${message.type === 'success' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}>
            {message.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
            {message.text}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-8">
          <button 
            onClick={handleRunAnalysis}
            disabled={loading || !tickers}
            className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-violet-500/20 active:scale-[0.98]"
          >
            {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Zap className="w-4 h-4 fill-white" />}
            Run Analysis Engine
          </button>
          <button 
            onClick={handleBulkAnalyze}
            disabled={loading}
            className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-slate-300 px-6 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all border border-slate-700 active:scale-[0.98]"
          >
            {loading ? <div className="w-4 h-4 border-2 border-slate-500 border-t-slate-300 rounded-full animate-spin"></div> : <ListChecks className="w-4 h-4" />}
            Bulk Analyze Portfolio
          </button>
        </div>
      </div>
    </div>
  )
}
