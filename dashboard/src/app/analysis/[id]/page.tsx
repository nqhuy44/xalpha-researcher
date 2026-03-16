'use client'

import React, { use, useEffect, useState } from 'react'
import useSWR from 'swr'
import Link from 'next/link'
import {
  ArrowLeft,
  ShieldCheck,
  Target,
  Zap,
  ChevronUp,
  ChevronDown,
  Clock,
  MessageSquare,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function AnalysisDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: analysis, error } = useSWR(id ? `/api/analysis/${id}` : null, fetcher)
  
  const [authChecked, setAuthChecked] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    async function checkAuth() {
      try {
        const res = await fetch('/api/auth/me')
        if (res.ok) {
          setIsAuthenticated(true)
        } else {
          setIsAuthenticated(false)
        }
      } catch (error) {
        setIsAuthenticated(false)
      } finally {
        setAuthChecked(true)
      }
    }
    checkAuth()
  }, [])

  if (!authChecked) return null
  if (!isAuthenticated) return null

  if (error) return (
    <div className="min-h-screen bg-[#0a0f1d] flex flex-col items-center justify-center text-white">
      <AlertCircle className="w-16 h-16 text-rose-500 mb-4" />
      <h1 className="text-2xl font-black">Report Not Found</h1>
      <Link href="/analysis" className="mt-6 text-violet-400 font-bold hover:underline flex items-center gap-2">
        <ArrowLeft className="w-4 h-4" /> Back to Library
      </Link>
    </div>
  )

  if (!analysis) return (
    <div className="min-h-screen bg-[#0a0f1d] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-4 border-violet-500/20 border-t-violet-500 rounded-full animate-spin" />
        <p className="text-slate-500 font-bold animate-pulse uppercase tracking-widest text-xs">Loading AI Consensus...</p>
      </div>
    </div>
  )

  const getActionColor = (action: string) => {
    const a = action?.toUpperCase() || ''
    if (a.includes('MUA') || a.includes('TIỀM NĂNG') || a.includes('KHẢ QUAN')) return 'text-emerald-400'
    if (a.includes('BÁN') || a.includes('RỦI RO')) return 'text-rose-400'
    return 'text-slate-400'
  }

  return (
    <div className="min-h-screen bg-[#0a0f1d] text-slate-200 pb-20 selection:bg-violet-500/30">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-[#0a0f1d]/80 backdrop-blur-xl border-b border-slate-800/50">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/analysis" className="p-2.5 hover:bg-slate-800/50 rounded-xl transition-colors border border-transparent hover:border-slate-700">
              <ArrowLeft className="w-5 h-5 text-slate-400" />
            </Link>
            <div>
              <div className="flex items-center gap-3">
                <span className="p-1 px-2 bg-violet-600 rounded text-[10px] font-black uppercase tracking-tighter">AI Consensus</span>
                <h1 className="text-2xl font-black text-white tracking-tight">XAlpha Debate Report: {analysis.ticker}</h1>
              </div>
              <p className="text-xs font-bold text-slate-500 mt-0.5">
                Generated on {new Date(analysis.created_at).toLocaleDateString('en-GB')} | Multi-Agent Consensus V4.2
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
              <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">Verified by Referee</span>
            </div>
            <div className="px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-full">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mr-2">Confidence:</span>
              <span className="text-sm font-black text-white">{analysis.confidence_score}%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 mt-8 space-y-8">
        {/* Top Grid: Verdict & Referee */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Verdict */}
          <div className="lg:col-span-2 relative group overflow-hidden bg-slate-900/40 border border-slate-800 rounded-[2.5rem] p-8 lg:p-12">
            <div className="absolute top-0 right-0 p-12 opacity-[0.03] select-none pointer-events-none">
              <span className="text-[12rem] font-black italic tracking-tighter">VERDICT</span>
            </div>
            <div className="relative z-10">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-4">Qualitative Assessment</p>
              <div className="flex items-end gap-6 mb-8">
                <h2 className={`text-6xl lg:text-7xl font-black tracking-tighter ${getActionColor(analysis.decision)}`}>
                  {analysis.decision}
                </h2>
                <div className="flex gap-4 mb-3">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-emerald-500 uppercase">Bull Score</span>
                    <span className="text-2xl font-black text-emerald-400">{analysis.bull_score}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-rose-500 uppercase">Bear Score</span>
                    <span className="text-2xl font-black text-rose-400">{analysis.bear_score}</span>
                  </div>
                </div>
              </div>
              <p className="text-lg lg:text-xl font-medium text-slate-300 leading-relaxed italic border-l-4 border-violet-500/30 pl-6 py-2">
                "{analysis.judge_synthesis}"
              </p>
            </div>
          </div>

          {/* Referee Audit Section */}
          <div className="space-y-6">
            {(analysis.referee_history && analysis.referee_history.length > 0 ? analysis.referee_history : [
              {
                action: analysis.referee_action || 'CONFIRM',
                is_valid: analysis.is_referee_valid ?? true,
                referee_synthesis: analysis.referee_synthesis || 'Referee confirmed the judge reasoning as logically sound based on provided news and financial context.'
              }
            ]).map((audit: any, aIdx: number) => (
              <div key={aIdx} className="bg-slate-900/40 border border-slate-800 rounded-[2.5rem] p-8 flex flex-col justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-6">
                    <div className={`p-2 ${audit.action?.toUpperCase() === 'OVERRIDE' ? 'bg-rose-600/20 border-rose-500/20' : 'bg-violet-600/20 border-violet-500/20'} border rounded-xl`}>
                      <ShieldCheck className={`w-6 h-6 ${audit.action?.toUpperCase() === 'OVERRIDE' ? 'text-rose-400' : 'text-violet-400'}`} />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-white">Referee Audit (R{aIdx + 1})</h3>
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        {audit.action?.toUpperCase() === 'OVERRIDE' ? 'Rejection' : 'Integrity Check'}
                      </p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between py-3 border-b border-slate-800/50">
                      <span className="text-xs font-bold text-slate-500 uppercase">Action</span>
                      <span className={`text-sm font-black ${audit.action?.toUpperCase() === 'OVERRIDE' ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {audit.action || 'CONFIRM'}
                      </span>
                    </div>
                    <div className="flex items-center justify-between py-3 border-b border-slate-800/50">
                      <span className="text-xs font-bold text-slate-500 uppercase">Bias Check</span>
                      <span className="text-sm font-bold text-slate-300">
                        {audit.is_valid ? 'Valid / Balanced' : 'Rejected / Biased'}
                      </span>
                    </div>
                    <p className="text-s text-slate-400 leading-relaxed italic p-4 bg-slate-950/30 rounded-2xl border border-slate-800/50 mt-2">
                      "{audit.referee_synthesis}"
                    </p>
                  </div>
                </div>
                <div className="mt-6 flex items-center gap-2">
                  <span className={`px-3 py-1 ${audit.is_valid ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'} text-[10px] font-black uppercase rounded`}>
                    Status: {audit.is_valid ? 'Verified' : 'Overridden'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Separator */}
        <div className="flex items-center gap-6 py-4">
          <div className="h-[1px] flex-1 bg-gradient-to-r from-violet-500/50 to-transparent" />
          <h3 className="text-sm font-black text-white uppercase tracking-[0.3em]">Trading Horizons</h3>
          <div className="h-[1px] flex-1 bg-gradient-to-l from-violet-500/50 to-transparent" />
        </div>

        {/* Trading Horizons */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { title: 'Ngắn hạn', timeframe: '1 THÁNG', data: analysis.short_term },
            { title: 'Trung hạn', timeframe: '6 THÁNG', data: analysis.medium_term },
            { title: 'Dài hạn', timeframe: '1 NĂM', data: analysis.long_term },
          ].map((horizon, idx) => (
            <div key={idx} className="bg-slate-900/40 border border-slate-800 rounded-[2rem] p-6 hover:border-violet-500/30 transition-all group">
              <div className="flex items-center justify-between mb-6">
                <h4 className="font-bold text-slate-200">
                  {horizon.title} <span className={`text-[10px] ml-1 uppercase font-black ${horizon.data?.outlook?.toLowerCase() === 'bullish' ? 'text-emerald-400' : horizon.data?.outlook?.toLowerCase() === 'bearish' ? 'text-rose-400' : 'text-slate-400'}`}>({horizon.data?.outlook || 'N/A'})</span>
                </h4>
                <span className="text-[10px] font-black text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded uppercase">{horizon.timeframe}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-3 bg-slate-950/40 rounded-xl border border-slate-800">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest mb-1">Entry</p>
                  <p className="text-base font-black text-white">{horizon.data?.entry_price?.toLocaleString() || '---'}</p>
                </div>
                <div className="p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10">
                  <p className="text-[8px] font-bold text-emerald-500/60 uppercase tracking-widest mb-1">Target</p>
                  <p className="text-base font-black text-emerald-400">{horizon.data?.target_price?.toLocaleString() || '---'}</p>
                </div>
                <div className="p-3 bg-rose-500/5 rounded-xl border border-rose-500/10">
                  <p className="text-[8px] font-bold text-rose-500/60 uppercase tracking-widest mb-1">Stop Loss</p>
                  <p className="text-base font-black text-rose-400">{horizon.data?.stop_loss?.toLocaleString() || '---'}</p>
                </div>
                <div className="p-3 bg-slate-950/40 rounded-xl border border-slate-800">
                  <p className="text-[8px] font-bold text-slate-500 uppercase tracking-widest mb-1">R/R</p>
                  <p className="text-base font-black text-violet-400">{horizon.data?.risk_reward_ratio || '---'}</p>
                </div>
              </div>
              <p className="text-s text-slate-400 italic">
                {horizon.data?.rationale}
              </p>
            </div>
          ))}
        </div>
        
        {/* Debate Proceedings */}
        {analysis.debate_rounds && (
        <div className="space-y-12 mt-16">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <h2 className="text-4xl font-black text-white tracking-tighter">Biên bản Tranh biện Chi tiết</h2>
              <p className="text-sm font-bold text-slate-500 mt-1 uppercase tracking-[0.2em]">Multi-Agent Adversarial Information Flow</p>
            </div>
            <div className="flex items-center gap-6 pb-1">
              <div className="flex items-center gap-2.5">
                <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.4)]" />
                <span className="text-[11px] font-black text-slate-400 uppercase tracking-tighter">BULL FORCE (Alpha)</span>
              </div>
              <div className="flex items-center gap-2.5">
                <div className="w-3 h-3 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.4)]" />
                <span className="text-[11px] font-black text-slate-400 uppercase tracking-tighter">BEAR PRESSURE (Omega)</span>
              </div>
            </div>
          </div>

          <div className="space-y-24">
            {(() => {
              const allRounds = analysis.debate_rounds || [];
              const allRebuttals = allRounds.flatMap((r: any) => [
                ...(r.bull_rebuttals || []),
                ...(r.bear_rebuttals || [])
              ]);

              const cleanText = (text: string) => {
                if (!text) return "";
                // Remove bracketed tags like [SCOPE_ERROR] and Vietnamese labels like "Lỗi phạm vi:"
                let cleaned = text.trim()
                  .split('\n')[0]
                  .replace(/\[[A-Z_]+\]/g, '') // Remove [TAGS]
                  .replace(/^[a-zA-ZÀ-ỹ\s]+:\s*/, '') // Remove "Label: "
                  .trim()
                  .toLowerCase();
                return cleaned;
              };

              const renderThread = (targetText: string, depth: number = 0) => {
                if (depth > 5) return null; // Safety break

                const cleanedTarget = cleanText(targetText);
                const matches = allRebuttals.filter((reb: any) => 
                  cleanText(reb.target_claim) === cleanedTarget ||
                  (cleanedTarget.length > 20 && reb.target_claim?.toLowerCase().includes(cleanedTarget)) ||
                  (reb.target_claim?.length > 20 && cleanedTarget.includes(cleanText(reb.target_claim)))
                );

                if (matches.length === 0) return null;

                return (
                  <div className={`${depth === 0 ? 'ml-8' : 'ml-0'} mt-6 space-y-8 relative`}>
                    {depth === 0 && (
                      <div className="absolute -left-4 top-0 bottom-0 w-[2px] bg-gradient-to-b from-slate-800 via-slate-800 to-transparent" />
                    )}
                    {matches.map((reb: any, idxPerDepth: number) => {
                      const isBear = allRounds.some((r: any) => (r.bear_rebuttals || []).includes(reb));
                      
                      return (
                        <div key={`${depth}-${idxPerDepth}`} className="relative">
                          {depth === 0 && (
                            <div className="absolute -left-4 top-5 w-4 h-[2px] bg-slate-800" />
                          )}
                          <div className={`bg-slate-950/60 border border-slate-800/80 rounded-2xl p-5 shadow-xl transition-all hover:border-slate-700 ${depth > 0 ? 'border-l-4' : ''} ${depth > 0 ? (isBear ? 'border-l-rose-500/50' : 'border-l-emerald-500/50') : ''}`}>
                            <div className={`flex items-center gap-2 text-[10px] font-black uppercase mb-2 ${isBear ? 'text-rose-500' : 'text-emerald-500'}`}>
                              <ShieldCheck className="w-3 h-3" /> {isBear ? 'BEAR COUNTER' : 'BULL COUNTER'} {depth > 0 ? ` (ROUND ${depth + 1})` : ''}
                            </div>
                            <p className="text-sm text-slate-300 leading-relaxed font-medium">
                              {reb.counter_evidence}
                            </p>
                          </div>
                          {/* Recursive Call for deeper levels */}
                          {renderThread(reb.counter_evidence, depth + 1)}
                        </div>
                      );
                    })}
                  </div>
                );
              };

              return allRounds.map((round: any, rIdx: number) => {
                const hasArgs = (round.bull_arguments?.length || 0) > 0 || (round.bear_arguments?.length || 0) > 0;
                if (!hasArgs) return null; // Skip rounds that are purely rebuttals (handled by recursion)

                return (
                  <div key={rIdx} className="relative">
                    <div className="absolute -top-6 left-0 flex items-center gap-4">
                      <div className="h-[1px] w-8 bg-violet-500/50" />
                      <span className="text-[10px] font-black text-violet-400 uppercase tracking-[0.4em] bg-[#0a0f1d] px-2">
                        {rIdx === 0 ? 'Opening Arguments' : `Round ${rIdx + 1}`}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 pt-4">
                      {/* Bull Side */}
                      <div className="space-y-12">
                        {round.bull_arguments?.map((arg: any, aIdx: number) => (
                          <div key={aIdx}>
                            <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-6 relative overflow-hidden group hover:border-emerald-500/30 transition-all">
                              <div className="absolute top-0 left-0 w-1.5 h-full bg-emerald-500" />
                              <div className="flex items-center justify-between mb-4">
                                <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest">
                                  BULL ARGUMENT #{rIdx + 1}.{aIdx + 1}
                                </span>
                                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-500 text-[10px] font-black rounded border border-emerald-500/20">
                                  STR {arg.strength}/10
                                </span>
                              </div>
                              <h4 className="text-xl font-black text-white mb-3 leading-tight tracking-tight italic">{arg.claim}</h4>
                              <p className="text-sm text-slate-400 leading-relaxed border-l-2 border-slate-800 pl-4 py-1">
                                {arg.evidence}
                              </p>
                            </div>
                            {/* Start recursion */}
                            {renderThread(arg.claim)}
                          </div>
                        ))}
                      </div>

                      {/* Bear Side */}
                      <div className="space-y-12">
                        {round.bear_arguments?.map((arg: any, aIdx: number) => (
                          <div key={aIdx}>
                            <div className="bg-slate-900/40 border border-slate-800 rounded-3xl p-6 relative overflow-hidden group hover:border-rose-500/30 transition-all">
                              <div className="absolute top-0 left-0 w-1.5 h-full bg-rose-500" />
                              <div className="flex items-center justify-between mb-4">
                                <span className="text-[10px] font-black text-rose-500 uppercase tracking-widest">
                                  BEAR ARGUMENT #{rIdx + 1}.{aIdx + 1}
                                </span>
                                <span className="px-2 py-0.5 bg-rose-500/10 text-rose-500 text-[10px] font-black rounded border border-rose-500/20">
                                  STR {arg.strength}/10
                                </span>
                              </div>
                              <h4 className="text-xl font-black text-white mb-3 leading-tight tracking-tight italic">{arg.claim}</h4>
                              <p className="text-sm text-slate-400 leading-relaxed border-l-2 border-slate-800 pl-4 py-1">
                                {arg.evidence}
                              </p>
                            </div>
                            {/* Start recursion */}
                            {renderThread(arg.claim)}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              });
            })()}
          </div>
        </div>
        )}
      </div>
    </div>
  )
}
