import { useMemo, useState, useRef, useEffect } from 'react'
import useWebSocketLog from '../hooks/useWebSocketLog'

const colorFor = (level) => {
  const l = level?.toUpperCase()
  if (l === 'SUCCESS') return 'text-emerald-300'
  if (l === 'WARNING') return 'text-amber-300'
  if (l === 'ERROR') return 'text-rose-300'
  return 'text-slate-200'
}

export default function LogStream() {
  const { logs, connected } = useWebSocketLog()
  const [paused, setPaused] = useState(false)
  const [query, setQuery] = useState('')
  const bottomRef = useRef(null)

  const filtered = useMemo(() => {
    if (!query) return logs
    const q = query.toLowerCase()
    return logs.filter((l) => l.message?.toLowerCase().includes(q) || l.level?.toLowerCase().includes(q))
  }, [logs, query])

  useEffect(() => {
    if (!paused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [filtered, paused])

  return (
    <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-4 h-full flex flex-col">
      <div className="flex items-center gap-3 mb-3">
        <span className={`text-xs px-2 py-1 rounded-full ${connected ? 'bg-emerald-500/20 text-emerald-200' : 'bg-slate-700'}`}>
          {connected ? 'Live' : 'Reconnecting…'}
        </span>
        <input
          type="text"
          placeholder="Search logs"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1 rounded-lg bg-slate-900/80 border border-slate-800 px-3 py-2 text-sm"
        />
        <button
          onClick={() => setPaused((p) => !p)}
          className="text-sm px-3 py-2 rounded-lg bg-slate-800 border border-slate-700"
        >
          {paused ? 'Resume' : 'Pause'}
        </button>
      </div>
      <div className="overflow-y-auto text-sm flex-1 space-y-1 pr-1">
        {filtered.map((log, idx) => (
          <div key={`${log.ts}-${idx}`} className="font-mono">
            <span className="text-slate-500 mr-2">{new Date(log.ts).toLocaleTimeString()}</span>
            <span className={`mr-2 uppercase tracking-tight text-xs ${colorFor(log.level)}`}>{log.level}</span>
            <span className="text-slate-100">{log.message}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
