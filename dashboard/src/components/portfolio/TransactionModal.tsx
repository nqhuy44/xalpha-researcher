"use client"

import React, { useState, useEffect } from 'react'
import { X, CheckCircle2, AlertCircle, Loader2, Search, Calendar, Landmark, Coins, TrendingUp, ShieldCheck, Zap } from 'lucide-react'

interface TransactionModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

type TransactionMode = 'STOCK' | 'CASH';
type TransactionAction = 'BUY' | 'SELL' | 'DEPOSIT' | 'WITHDRAW' | 'INIT';

export function TransactionModal({ isOpen, onClose, onSuccess }: TransactionModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<TransactionMode>('STOCK')
  const [form, setForm] = useState({
    symbol: '',
    action: 'BUY' as TransactionAction,
    shares: '',
    price: '',
    commission: '0.15',
    date: new Date().toISOString().split('T')[0],
    notes: ''
  })

  // Calculations
  const sharesCount = Number(form.shares) || 0
  const priceValue = Number(form.price) || 0
  const commRate = 0.0015 // Fixed 0.15% commission
  
  const rawValue = sharesCount * priceValue
  const commissionFee = rawValue * commRate
  const taxRate = form.action === 'SELL' ? 0.001 : 0
  const taxFee = rawValue * taxRate

  const totalValue = form.action === 'SELL' 
    ? rawValue - commissionFee - taxFee 
    : (form.action === 'BUY' || form.action === 'INIT') 
      ? rawValue + commissionFee 
      : (mode === 'CASH' ? sharesCount : rawValue)

  useEffect(() => {
    if (mode === 'CASH') {
      if (form.action !== 'DEPOSIT' && form.action !== 'WITHDRAW') {
        setForm(prev => ({ ...prev, action: 'DEPOSIT' }))
      }
    } else {
      if (form.action === 'DEPOSIT' || form.action === 'WITHDRAW') {
        setForm(prev => ({ ...prev, action: 'BUY' }))
      }
    }
  }, [mode])

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // For CASH, we use "shares" field as the amount in the existing API
      const payload = {
        symbol: mode === 'CASH' ? 'CASH' : form.symbol.toUpperCase(),
        shares: mode === 'CASH' ? Number(form.shares) : Number(form.shares),
        action: form.action,
        avg_price: mode === 'CASH' ? 1.0 : Number(form.price),
        notes: form.notes
      }

      const res = await fetch('/api/portfolio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.error || 'Failed to submit transaction')
      }

      onSuccess()
      onClose()
      setForm({ ...form, symbol: '', shares: '', price: '', notes: '' })
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div 
        className="absolute inset-0 bg-[#020617]/90 backdrop-blur-md animate-in fade-in duration-300"
        onClick={onClose}
      />
      
      <div className="relative w-full max-w-2xl bg-[#0F172A] border border-slate-800 rounded-3xl shadow-[0_0_50px_-12px_rgba(0,0,0,0.5)] overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="px-8 py-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Zap className="text-white w-6 h-6 fill-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white tracking-tight">New Transaction</h2>
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-500">Institutional Trade Terminal</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-500">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-8 pb-8 space-y-6">
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-500 font-medium">
              <AlertCircle className="w-5 h-5" />
              {error}
            </div>
          )}

          {/* Mode & Buy/Sell Toggle */}
          <div className="flex flex-col gap-4">
            <div className="flex bg-slate-900/50 p-1 rounded-xl border border-slate-800/50">
              <button 
                type="button"
                onClick={() => setMode('STOCK')}
                className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${mode === 'STOCK' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
              >
                STOCK
              </button>
              <button 
                type="button"
                onClick={() => setMode('CASH')}
                className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${mode === 'CASH' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}
              >
                CASH
              </button>
            </div>

            {mode === 'STOCK' ? (
              <div className="flex bg-slate-900/80 p-1.5 rounded-2xl border border-slate-800 shadow-inner">
                <button 
                  type="button"
                  onClick={() => setForm({...form, action: 'BUY'})}
                  className={`flex-1 py-3 rounded-xl text-sm font-black transition-all tracking-widest ${form.action === 'BUY' ? 'bg-[#22c55e] text-white shadow-[0_0_20px_rgba(34,197,94,0.3)]' : 'text-slate-500 hover:bg-slate-800/50'}`}
                >
                  BUY
                </button>
                <button 
                  type="button"
                  onClick={() => setForm({...form, action: 'SELL'})}
                  className={`flex-1 py-3 rounded-xl text-sm font-black transition-all tracking-widest ${form.action === 'SELL' ? 'bg-[#ef4444] text-white shadow-[0_0_20px_rgba(239,68,68,0.3)]' : 'text-slate-500 hover:bg-slate-800/50'}`}
                >
                  SELL
                </button>
              </div>
            ) : (
              <div className="flex bg-slate-900/80 p-1.5 rounded-2xl border border-slate-800 shadow-inner">
                <button 
                  type="button"
                  onClick={() => setForm({...form, action: 'DEPOSIT'})}
                  className={`flex-1 py-3 rounded-xl text-sm font-black transition-all tracking-widest ${form.action === 'DEPOSIT' ? 'bg-violet-600 text-white shadow-[0_0_20px_rgba(124,58,237,0.3)]' : 'text-slate-500 hover:bg-slate-800/50'}`}
                >
                  DEPOSIT
                </button>
                <button 
                  type="button"
                  onClick={() => setForm({...form, action: 'WITHDRAW'})}
                  className={`flex-1 py-3 rounded-xl text-sm font-black transition-all tracking-widest ${form.action === 'WITHDRAW' ? 'bg-amber-600 text-white shadow-[0_0_20px_rgba(217,119,6,0.3)]' : 'text-slate-500 hover:bg-slate-800/50'}`}
                >
                  WITHDRAW
                </button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Field: Search Ticker / Cash Action */}
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">
                {mode === 'STOCK' ? 'Search Ticker' : 'Cash Label'}
              </label>
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-violet-500 transition-colors">
                  {mode === 'STOCK' ? <Search className="w-5 h-5" /> : <Landmark className="w-5 h-5" />}
                </div>
                <input 
                  required
                  type="text"
                  placeholder={mode === 'STOCK' ? "e.g. HPG, VNM, FPT" : "CASH"}
                  readOnly={mode === 'CASH'}
                  className="w-full pl-12 pr-4 py-4 bg-slate-900/50 border border-slate-800 rounded-2xl text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all font-medium"
                  value={mode === 'CASH' ? 'CASH' : form.symbol}
                  onChange={e => setForm({...form, symbol: e.target.value})}
                />
              </div>
            </div>

            {/* Field: Date */}
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Transaction Date</label>
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-violet-500 transition-colors">
                  <Calendar className="w-5 h-5" />
                </div>
                <input 
                  type="date"
                  className="w-full pl-12 pr-4 py-4 bg-slate-900/50 border border-slate-800 rounded-2xl text-white focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all font-medium [color-scheme:dark]"
                  value={form.date}
                  onChange={e => setForm({...form, date: e.target.value})}
                />
              </div>
            </div>

            {/* Field: Quantity / Amount */}
            <div className="space-y-2">
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">
                {mode === 'STOCK' ? 'Quantity' : 'Amount (VND)'}
              </label>
              <input 
                required
                type="number"
                placeholder="0"
                className="w-full px-5 py-4 bg-slate-900/50 border border-slate-800 rounded-2xl text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all font-bold text-lg"
                value={form.shares}
                onChange={e => setForm({...form, shares: e.target.value})}
              />
            </div>

            {/* Field: Price (Stock Only) */}
            {mode === 'STOCK' ? (
              <div className="space-y-2 relative">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Price per Share (VND)</label>
                <div className="relative">
                  <input 
                    required
                    type="number"
                    placeholder="50,000"
                    className="w-full px-5 py-4 bg-slate-900/50 border border-slate-800 rounded-2xl text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50 transition-all font-bold text-lg pr-16"
                    value={form.price}
                    onChange={e => setForm({...form, price: e.target.value})}
                  />
                  <span className="absolute right-5 top-1/2 -translate-y-1/2 text-[10px] font-black text-slate-600 uppercase">VND</span>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Service</label>
                <div className="w-full px-5 py-4 bg-slate-900/20 border border-slate-800/50 rounded-2xl text-slate-500 font-medium italic">
                  Cash Balance Management
                </div>
              </div>
            )}

            {/* Field: Commission (Stock Only) */}
            {mode === 'STOCK' && (
              <div className="space-y-2 relative">
                <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-1">Commission / Fees</label>
                <div className="relative">
                  <input 
                    type="number"
                    readOnly
                    className="w-full px-5 py-4 bg-slate-900/30 border border-slate-800/50 rounded-2xl text-slate-500 cursor-not-allowed font-medium pr-10"
                    value="0.15"
                  />
                  <span className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-600 font-bold">%</span>
                </div>
              </div>
            )}

            {/* Total Value Box */}
            <div className={`space-y-2 p-5 rounded-2xl border flex flex-col justify-end ${mode === 'STOCK' ? 'bg-violet-500/5 border-violet-500/20' : 'bg-slate-800/20 border-slate-800'}`}>
              <label className="text-[10px] font-black text-violet-500 uppercase tracking-widest mb-1">Estimated Total Value</label>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Commission (0.15%):</span>
                  <span className="text-vn-ref font-medium">-{commissionFee.toLocaleString()} VND</span>
                </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-white">{totalValue.toLocaleString()}</span>
                <span className="text-[10px] font-black text-slate-500 uppercase">VND</span>
              </div>
            </div>
          </div>

          {/* Validation Card */}
          {mode === 'STOCK' && form.symbol && (
            <div className="p-5 rounded-2xl bg-gradient-to-br from-violet-600/10 to-transparent border border-violet-500/20 flex gap-4 animate-in slide-in-from-bottom-2 duration-300">
              <div className="w-10 h-10 bg-violet-600/20 rounded-xl flex items-center justify-center shrink-0">
                <ShieldCheck className="text-violet-500 w-6 h-6" />
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-black text-violet-400 uppercase tracking-wider">AgentX Alpha Validation</h3>
                  <span className="text-[8px] font-black bg-slate-800 px-2 py-0.5 rounded text-amber-500 uppercase tracking-widest">Real-time</span>
                </div>
                <div className="space-y-1">
                  <p className="text-[10px] text-slate-300 flex items-center gap-2">
                    <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                    Checking liquidity for <span className="font-bold text-white tracking-widest">{form.symbol.toUpperCase()}:HOSE</span>
                  </p>
                  <p className="text-[10px] text-slate-300 flex items-center gap-2">
                    <TrendingUp className="w-3 h-3 text-violet-500" />
                    Projected <span className="text-emerald-500 font-bold">+1.2%</span> impact on Portfolio NAV
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Footer Buttons */}
          <div className="grid grid-cols-5 gap-4 pt-2">
            <button 
              type="button" 
              onClick={onClose}
              className="col-span-2 py-4 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-white font-bold rounded-2xl transition-all"
            >
              Discard
            </button>
            <button 
              type="submit"
              disabled={loading || (mode === 'STOCK' && !form.symbol)}
              className="col-span-3 py-4 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold rounded-2xl shadow-xl shadow-violet-500/30 transition-all flex items-center justify-center gap-2 group tracking-wide"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Coins className="w-5 h-5 group-hover:scale-110 transition-transform" />
                  Confirm Transaction
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
