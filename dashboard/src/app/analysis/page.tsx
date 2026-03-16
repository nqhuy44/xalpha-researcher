"use client"

import React, { useEffect, useState } from "react"
import { Navbar } from "@/components/layout/Navbar"
import { Shield, Sparkles, Activity, History, Zap, Plus } from "lucide-react"
import { usePortfolio } from "@/hooks/use-portfolio"
import { useAnalysis } from "@/hooks/use-analysis"
import { AnalysisWorkspace } from "@/components/analysis/AnalysisWorkspace"
import { AnalysisLibrary } from "@/components/analysis/AnalysisLibrary"
import { AnalysisHistory } from "@/components/analysis/AnalysisHistory"

import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch')
  return res.json()
})

export default function AnalysisPage() {
  const { portfolio, isLoading: portfolioLoading } = usePortfolio()
  const { suggestions, isLoading: analysisLoading } = useAnalysis()
  const { data: historyData, isLoading: historyLoading } = useSWR('/api/analysis/history', fetcher)
  const { data: statsData } = useSWR('/api/analysis/stats', fetcher, { refreshInterval: 3000 })

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

  const portfolioSymbols = (portfolio as any[]).map(p => p.symbol) || []

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />

      <main className="px-12 py-8 w-full space-y-12">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h1 className="text-4xl font-black tracking-tight text-white uppercase">Analysis Management</h1>
            <p className="text-slate-500 font-medium">Deep-dive AI insights for your digital asset portfolio and watchlist.</p>
          </div>
          <div className="flex items-center gap-3">
            <button className="bg-slate-800/80 hover:bg-slate-800 text-slate-300 px-6 py-2.5 rounded-xl font-bold border border-slate-700 flex items-center gap-2 transition-all">
              <History className="w-4 h-4" />
              History
            </button>
            <button className="bg-violet-600 hover:bg-violet-700 text-white px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-violet-500/20 shadow-inner">
              <Plus className="w-4 h-4" />
              New Analysis
            </button>
          </div>
        </div>

        {/* Bento Grid Top Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <AnalysisWorkspace />
          </div>

          <div className="space-y-8">
            {/* System Health Card */}
            <div className="bg-gradient-to-br from-violet-600 to-purple-700 rounded-3xl p-8 shadow-2xl shadow-violet-900/20 relative overflow-hidden group">
              <div className="relative z-10">
                <p className="text-xs font-bold text-violet-200 uppercase tracking-widest mb-1">System Health</p>
                <h3 className="text-2xl font-black text-white uppercase mb-2">Optimized</h3>
                <div className="flex items-end gap-1">
                  <span className="text-5xl font-black text-white">{statsData?.system_health || "98.4%"}</span>
                </div>
              </div>
              <Sparkles className="absolute right-8 top-1/2 -translate-y-1/2 w-24 h-24 text-white/10 group-hover:scale-110 transition-transform duration-700" />
              <div className="absolute -bottom-1 -right-1 w-32 h-32 bg-white/5 rounded-full blur-3xl"></div>
            </div>

            {/* Status Card */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between h-[160px]">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-bold uppercase tracking-widest">Pending Tasks</span>
                <div className="bg-violet-500/20 p-2 rounded-lg">
                  <Activity className="w-4 h-4 text-violet-500" />
                </div>
              </div>
              <div>
                <h4 className="text-3xl font-black text-white mt-2">{statsData?.pending_tasks || 0} Analyses</h4>
                {statsData?.active_symbols?.length > 0 && (
                  <p className="text-[12px] text-emerald-400 font-bold mt-1 uppercase tracking-tighter">
                    Processing: {statsData.active_symbols.join(", ")}
                  </p>
                )}
                {statsData?.queued_symbols?.length > 0 && (
                  <p className="text-[12px] text-amber-400 font-bold mt-1 uppercase tracking-tighter">
                    Queued: {statsData.queued_symbols.join(", ")}
                  </p>
                )}
                {(!statsData?.active_symbols?.length && !statsData?.queued_symbols?.length) && (
                  <p className="text-[12px] text-slate-500 font-bold mt-1 uppercase tracking-tighter">
                    System Idle
                  </p>
                )}
                <div className="w-full h-1.5 bg-slate-800 rounded-full mt-4 overflow-hidden">
                  <div className={`bg-violet-500 h-full transition-all duration-1000 ${statsData?.pending_tasks > 0 ? 'w-[85%] animate-pulse' : 'w-0'}`} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Actionable Library Section */}
        <AnalysisLibrary
          suggestions={suggestions}
          loading={analysisLoading}
          portfolioSymbols={portfolioSymbols}
        />

        {/* Historical Records Section */}
        <AnalysisHistory history={historyData?.history || []} loading={historyLoading} />

      </main>

      <footer className="mt-24 border-t border-slate-800 py-12 px-12 bg-[#0F172A]/80 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-2 text-violet-500 font-black tracking-tighter text-lg">
            <Zap className="w-5 h-5 fill-violet-500" />
            AgentXAlpha
            <span className="text-slate-500 font-medium ml-2 text-sm">© 2026</span>
          </div>
          <div className="flex items-center gap-8 text-xs font-bold text-slate-500 uppercase tracking-widest">
            <a href="#" className="hover:text-violet-500 transition-colors">API Docs</a>
            <a href="#" className="hover:text-violet-500 transition-colors">Security</a>
            <a href="#" className="hover:text-violet-500 transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-violet-500 transition-colors">Terms of Service</a>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-violet-500/10 border border-violet-500/20 rounded-full">
            <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-pulse"></div>
            <span className="text-[10px] font-bold text-violet-500 uppercase tracking-wider">AI Agent Online</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
