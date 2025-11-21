import { useEffect, useState, useCallback } from 'react'
import { getStatus, getResults } from '../api/crawler'

export default function useStatus() {
  const [status, setStatus] = useState({ status: 'idle', running: false })
  const [results, setResults] = useState({ jobs: [], coverage: [] })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      const [s, r] = await Promise.all([getStatus(), getResults()])
      setStatus(s)
      setResults(r)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, 5000)
    return () => clearInterval(timer)
  }, [refresh])

  return { status, results, loading, error, refresh }
}
