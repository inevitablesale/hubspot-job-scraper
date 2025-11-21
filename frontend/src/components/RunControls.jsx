import { useState } from 'react'
import { runCrawl, stopCrawl } from '../api/crawler'

export default function RunControls({ running, onStatus }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleRun = async () => {
    try {
      setLoading(true)
      await runCrawl()
      setError(null)
      onStatus && onStatus()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to start')
    } finally {
      setLoading(false)
    }
  }

  const handleStop = async () => {
    try {
      setLoading(true)
      await stopCrawl()
      onStatus && onStatus()
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to stop')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleRun}
        disabled={running || loading}
        className="px-4 py-2 rounded-lg bg-emerald-500 text-black font-semibold shadow-soft disabled:opacity-60"
      >
        {running ? 'Running…' : 'Start Crawl'}
      </button>
      <button
        onClick={handleStop}
        disabled={!running || loading}
        className="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 border border-slate-600 disabled:opacity-50"
      >
        Stop
      </button>
      {error && <span className="text-sm text-amber-300">{error}</span>}
    </div>
  )
}
