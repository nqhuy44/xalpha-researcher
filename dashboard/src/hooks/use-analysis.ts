"use client"

import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then((res) => {
  if (!res.ok) throw new Error('Failed to fetch')
  return res.json()
})

export function useAnalysis() {
  const { data, error, isLoading, mutate } = useSWR('/api/analysis/recent', fetcher)

  return {
    suggestions: data?.suggestions || [],
    isLoading,
    isError: error,
    mutate
  }
}
