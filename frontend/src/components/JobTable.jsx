import { useMemo, useState } from 'react'
import ScoreBadge from './ScoreBadge'
import SignalsPillList from './SignalsPillList'

export default function JobTable({ jobs = [] }) {
  const [query, setQuery] = useState('')
  const [remoteOnly, setRemoteOnly] = useState(false)
  const [minScore, setMinScore] = useState(0)

  const filtered = useMemo(() => {
    return jobs
      .filter((job) => (remoteOnly ? job.remote : true))
      .filter((job) => (minScore ? job.score >= minScore : true))
      .filter((job) => {
        if (!query) return true
        const q = query.toLowerCase()
        return (
          job.company?.toLowerCase().includes(q) ||
          job.title?.toLowerCase().includes(q) ||
          job.signals?.some((s) => s.toLowerCase().includes(q))
        )
      })
  }, [jobs, query, remoteOnly, minScore])

  return (
    <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-4">
      <div className="flex flex-wrap gap-3 mb-3 items-center">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by company, title, or signal"
          className="rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm"
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input type="checkbox" checked={remoteOnly} onChange={(e) => setRemoteOnly(e.target.checked)} />
          Remote only
        </label>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          Min score
          <select
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded px-2 py-1"
          >
            <option value={0}>All</option>
            <option value={60}>60+</option>
            <option value={80}>80+</option>
          </select>
        </label>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-slate-400 text-xs uppercase">
            <tr className="border-b border-slate-800">
              <th className="text-left py-2">Company</th>
              <th className="text-left py-2">Title</th>
              <th className="text-left py-2">Score</th>
              <th className="text-left py-2">Signals</th>
              <th className="text-left py-2">Remote</th>
              <th className="text-left py-2">Link</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((job, idx) => (
              <tr key={`${job.url}-${idx}`} className="border-b border-slate-900 hover:bg-slate-900/50">
                <td className="py-2 font-semibold text-slate-100">{job.company}</td>
                <td className="py-2 text-slate-200">{job.title}</td>
                <td className="py-2"><ScoreBadge score={job.score} /></td>
                <td className="py-2"><SignalsPillList signals={job.signals} /></td>
                <td className="py-2 text-slate-200">{job.remote ? 'Yes' : '—'}</td>
                <td className="py-2">
                  <a href={job.url} target="_blank" rel="noreferrer" className="text-emerald-300 hover:text-emerald-200">
                    Open
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && <div className="text-slate-400 text-sm py-4">No results yet.</div>}
      </div>
    </div>
  )
}
