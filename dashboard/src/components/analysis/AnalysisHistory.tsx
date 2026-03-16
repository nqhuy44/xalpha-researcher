"use client"

import React from 'react'
import { History, Filter, Clock, CheckCircle2, AlertCircle } from 'lucide-react'
import Link from 'next/link'

export function AnalysisHistory({ history, loading }: { history: any[], loading: boolean }) {
  if (loading) {
    return (
      <div className="bg-[#1e293b]/30 border border-slate-800 rounded-2xl overflow-hidden shadow-sm p-12 flex justify-center">
        <div className="w-8 h-8 border-4 border-violet-500/30 border-t-violet-500 rounded-full animate-spin"></div>
      </div>
    )
  }

  const items = history || []

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  }

  const getStatus = (createdAt: string) => {
    if (!createdAt) return { label: 'Unknown', color: 'text-slate-500', icon: <AlertCircle className="w-3 h-3" /> };
    const now = new Date();
    const created = new Date(createdAt);
    const diffDays = Math.floor((now.getTime() - created.getTime()) / (1000 * 3600 * 24));
    
    if (diffDays > 7) {
      return { label: 'Expired', color: 'text-red-500', icon: <AlertCircle className="w-3 h-3" /> };
    }
    const remaining = 7 - diffDays;
    return { label: `Valid (${remaining}d)`, color: 'text-emerald-500', icon: <CheckCircle2 className="w-3 h-3" /> };
  }

  return (
    <div className="bg-[#1e293b]/30 border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
      <div className="p-6 border-b border-slate-800 flex items-center justify-between">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <History className="w-5 h-5 text-violet-500" />
          Analysis History
        </h2>
        <div className="flex items-center gap-4">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-3.5 h-3.5" />
            <input 
              type="text" 
              placeholder="Filter history..." 
              className="bg-slate-900/50 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs focus:ring-1 focus:ring-violet-500 outline-none w-48"
            />
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-slate-900/50 border-b border-slate-800">
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Date</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Ticker</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Final Call</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Units</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Confidence</th>
              <th className="px-6 py-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {items.map((item, idx) => {
              const actionColor = item.suggested_action?.includes('MUA') || item.suggested_action?.includes('BUY') ? 'text-vn-up' : 
                          item.suggested_action?.includes('BÁN') || item.suggested_action?.includes('SELL') ? 'text-vn-down' : 'text-vn-ref';
              
              const status = getStatus(item.created_at);
              
              return (
                <tr key={idx} className="hover:bg-slate-800/20 transition-colors">
                  <td className="px-6 py-4 text-xs text-slate-400 font-medium">{formatDate(item.created_at)}</td>
                  <td className="px-6 py-4 text-sm font-black">
                    <Link href={`/analysis/${item.id}`} className="text-white hover:text-violet-400 transition-colors">
                      {item.ticker}
                    </Link>
                  </td>
                  <td className={`px-6 py-4 text-xs font-bold ${actionColor}`}>{item.suggested_action || 'N/A'}</td>
                  <td className="px-6 py-4 text-xs font-bold text-slate-300">
                    {item.suggested_shares ? `${item.suggested_shares > 0 ? '+' : ''}${item.suggested_shares}` : '-'}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${item.analyst_confidence > 70 ? 'bg-emerald-500' : item.analyst_confidence > 40 ? 'bg-amber-500' : 'bg-red-500'}`}></div>
                      <span className="text-xs font-bold text-slate-300">{item.analyst_confidence || 0}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className={`flex items-center justify-end gap-1.5 text-[10px] font-black uppercase tracking-wider ${status.color}`}>
                      {status.icon}
                      {status.label}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      
      <div className="p-4 bg-slate-900/30 text-center">
        <button className="text-xs font-bold text-slate-500 hover:text-slate-300 uppercase tracking-widest transition-colors">
          Load More Entries
        </button>
      </div>
    </div>
  )
}
