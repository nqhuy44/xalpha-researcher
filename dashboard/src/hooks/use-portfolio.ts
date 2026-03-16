"use client"

import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch')
  return res.json()
})

export function usePortfolio() {
  const { data, error, isLoading, mutate } = useSWR('/api/portfolio', fetcher)

  return {
    portfolio: data?.holdings || [],
    summary: data?.summary || { total_nav: 0, total_pnl: 0, cash_balance: 0, stock_value: 0 },
    isLoading,
    isError: error,
    mutate
  }
}
