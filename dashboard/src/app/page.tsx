"use client"

import React, { useState, useEffect } from "react"
import { Navbar } from "@/components/layout/Navbar"
import { PortfolioTable } from "@/components/portfolio/PortfolioTable"
import { AIAnalysisList } from "@/components/debate/AIAnalysisList"
import { TransactionModal } from "@/components/portfolio/TransactionModal"
import { usePortfolio } from "@/hooks/use-portfolio"
import { useAnalysis } from "@/hooks/use-analysis"
import { TrendingUp, TrendingDown, Wallet, ArrowUp, PieChart, Plus, Shield } from "lucide-react"

export default function DashboardPage() {
  const { portfolio, summary, isLoading: portfolioLoading, mutate: mutatePortfolio } = usePortfolio()
  const { suggestions, isLoading: analysisLoading } = useAnalysis()
  const [authChecked, setAuthChecked] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [password, setPassword] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [showValues, setShowValues] = useState(false)

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

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (res.ok) {
        setIsAuthenticated(true)
      } else {
        alert("Invalid password")
      }
    } catch (error) {
      alert("Error logging in")
    }
  }

  const handleBulkAnalyze = async () => {
    try {
      const res = await fetch('/api/analysis/bulk', { method: 'POST' })
      if (res.ok) {
        alert("Bulk analysis started successfully")
      } else {
        alert("Failed to start bulk analysis")
      }
    } catch (error) {
      alert("Error starting bulk analysis")
    }
  }

  if (!authChecked) return null

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#0F172A]">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl w-full max-w-md shadow-2xl">
          <div className="flex flex-col items-center gap-4 mb-8">
            <div className="p-4 bg-violet-600 rounded-2xl shadow-lg shadow-violet-500/20">
              <Shield className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold">AgentXAlpha Login</h1>
            <p className="text-slate-500 text-sm">Enter admin password to access the terminal</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Admin Password"
              className="w-full bg-slate-800 border-none rounded-xl px-4 py-3 focus:ring-2 focus:ring-violet-500 text-white"
              autoFocus
            />
            <button className="w-full bg-violet-600 hover:bg-violet-700 text-white font-bold py-3 rounded-xl transition-all">
              Unlock Terminal
            </button>
          </form>
        </div>
      </div>
    )
  }

  const { total_nav, total_cost, total_pnl, cash_balance, stock_value } = summary;
  const pnlPercent = total_cost > 0 ? (total_pnl / total_cost) * 100 : 0;

  return (
    <div className="flex flex-col min-h-screen">
      <Navbar />
      
      <main className="px-12 py-8 w-full space-y-8">
        <div className="flex justify-end mb-2">
          <button 
            onClick={() => setShowValues(!showValues)}
            className="flex items-center gap-2 text-xs font-bold text-slate-400 hover:text-white transition-colors bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700"
          >
            <span className="material-symbols-outlined text-sm">
              {showValues ? 'visibility_off' : 'visibility'}
            </span>
            {showValues ? 'Hide Values' : 'Show Values'}
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="Net Asset Value" 
            value={showValues ? total_nav.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "******"} 
            unit="VND" 
            trend="Total Assets" 
            icon={<PieChart className="w-4 h-4" />} 
          />
          <StatCard 
            title="Total P&L" 
            value={showValues ? (total_pnl >= 0 ? '+' : '') + total_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "******"} 
            unit="VND" 
            trend={(total_pnl >= 0 ? '+' : '') + pnlPercent.toFixed(2) + "%"} 
            trendUp={total_pnl >= 0} 
            icon={total_pnl >= 0 ? <ArrowUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />} 
            valueClass={total_pnl > 0 ? "text-vn-up" : total_pnl < 0 ? "text-vn-down" : "text-vn-ref"}
          />
          <StatCard 
            title="Stock Value" 
            value={showValues ? stock_value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "******"} 
            unit="VND" 
            trend="Active Holdings" 
            icon={<TrendingUp className="w-4 h-4" />} 
          />
          <StatCard 
            title="Cash (Power)" 
            value={showValues ? cash_balance.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "******"} 
            unit="VND" 
            trend="Available to trade" 
            icon={<Wallet className="w-4 h-4" />} 
            valueClass="text-vn-ref"
            trendClass="text-violet-500"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Main Content Area */}
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <PieChart className="w-5 h-5 text-violet-500" />
                Portfolio Holdings
              </h2>
              <div className="flex gap-2">
                <button 
                  onClick={() => setIsModalOpen(true)}
                  className="bg-violet-600 hover:bg-violet-700 text-white px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 shadow-lg shadow-violet-500/20 transition-all"
                >
                  <Plus className="w-4 h-4" />
                  Add Transaction
                </button>
              </div>
            </div>

            <PortfolioTable positions={portfolio} loading={portfolioLoading} showValues={showValues} />
          </div>

          {/* AI Analysis Sidebar */}
          <div className="space-y-6">
             <div className="bg-gradient-to-br from-violet-500/10 to-transparent border border-violet-500/20 rounded-2xl p-6 shadow-xl shadow-violet-500/5">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-violet-500 text-2xl animate-pulse">auto_awesome</span>
                    <h2 className="text-lg font-bold">AI Portfolio Agent</h2>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-500 text-[10px] font-bold uppercase tracking-wider">Live Analysis</span>
                </div>
                
                <AIAnalysisList 
                  suggestions={suggestions} 
                  loading={analysisLoading} 
                  portfolioSymbols={(portfolio as any[]).map(p => p.symbol)}
                />
                
                <div className="grid grid-cols-1 mt-6">
                  <button 
                    onClick={handleBulkAnalyze}
                    className="bg-violet-500/20 hover:bg-violet-500/30 text-violet-500 py-3 rounded-xl text-xs font-bold transition-all border border-violet-500/20 flex flex-col items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">analytics</span>
                    Bulk Analyze
                  </button>
                </div>
             </div>

             <div className="bg-blue-500/10 border border-blue-500/30 rounded-2xl p-4 flex items-center gap-4">
                <div className="p-2 bg-blue-500 rounded-lg text-white">
                  <Shield className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-xs font-bold text-blue-500 uppercase tracking-widest leading-none">Risk Guard</p>
                  <p className="text-sm font-medium mt-1">Portfolio Volatility: Low</p>
                </div>
              </div>
          </div>
        </div>
      </main>

      <footer className="mt-auto border-t border-slate-800 py-8 text-center bg-[#0F172A]/50">
        <p className="text-xs text-slate-500 uppercase tracking-widest font-semibold">© 2026 AgentXAlpha • AI-Driven Intelligence</p>
      </footer>

      <TransactionModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => mutatePortfolio()}
      />
    </div>
  )
}

function StatCard({ title, value, unit, trend, trendUp, icon, valueClass, trendClass }: any) {
  return (
    <div className="bg-[#1e293b]/50 p-6 rounded-xl border border-slate-800 flex flex-col justify-between hover:border-violet-500/50 transition-all shadow-sm">
      <div>
        <p className="text-slate-400 text-sm font-medium">{title}</p>
        <h3 className={`text-2xl font-bold mt-1 ${valueClass || 'text-white'}`}>
          {value} <span className="text-xs font-normal opacity-50">{unit}</span>
        </h3>
      </div>
      <div className={`mt-4 flex items-center gap-2 text-sm font-semibold ${trendClass || (trendUp ? 'text-vn-up' : 'text-vn-down')}`}>
        {icon}
        <span>{trend}</span>
      </div>
    </div>
  )
}
