"use client"

import React from 'react'
import { Bolt, Search, User, LogOut } from 'lucide-react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'

export function Navbar() {
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-[#0F172A]/80 backdrop-blur-md px-6 py-3">
      <div className="w-full flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2 text-violet-500">
            <Bolt className="w-8 h-8 font-bold" />
            <span className="text-xl font-bold tracking-tight text-white">AgentXAlpha</span>
          </div>
            <NavItem href="/" label="Portfolio" active={pathname === '/'} />
            <NavItem href="/analysis" label="Analysis" active={pathname === '/analysis'} />
            <NavItem href="/risk" label="Risk" active={pathname === '/risk'} />
        </div>
        
        <div className="flex items-center gap-4">
          <div className="relative hidden sm:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input 
              className="pl-10 pr-4 py-1.5 bg-slate-800 border-none rounded-lg text-sm focus:ring-2 focus:ring-violet-500 w-64 text-slate-100" 
              placeholder="Search Tickers..." 
              type="text"
            />
          </div>
          <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-violet-500 to-purple-400 p-0.5">
            <div className="h-full w-full rounded-full bg-slate-800 flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}

function NavItem({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link 
      href={href}
      className={`text-sm font-medium transition-colors hover:text-violet-500 ${
        active ? 'text-violet-500 border-b-2 border-violet-500 pb-4 mt-4' : 'text-slate-500'
      }`}
    >
      {label}
    </Link>
  )
}
