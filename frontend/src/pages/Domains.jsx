import { useEffect, useMemo, useState } from 'react'
import { deleteDomain, fetchDomainChanges, fetchDomains } from '../api/crawler'
import StatusPill from '../components/StatusPill'
import ScoreBadge from '../components/ScoreBadge'
import SignalsPillList from '../components/SignalsPillList'

export default function Domains() {
  const [domains, setDomains] = useState([])
  const [stats, setStats] = useState({ total: 0, with_hubspot: 0 })
  const [changes, setChanges] = useState({})
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const data = await fetchDomains()
      setDomains(data.domains || [])
      setStats(data.stats || { total: 0, with_hubspot: 0 })
      const diff = await fetchDomainChanges()
      setChanges(diff)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filtered = useMemo(() => {
    const term = search.toLowerCase()
    return domains.filter((d) =>
      !term ||
      d.domain?.toLowerCase().includes(term) ||
      (d.company || '').toLowerCase().includes(term) ||
      (d.categoryName || '').toLowerCase().includes(term)
    )
  }, [domains, search])

  const handleRemove = async (domain) => {
    await deleteDomain(domain)
    await load()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-slate-400">Domain registry</div>
          <div className="text-2xl font-semibold">Agency coverage</div>
        </div>
        <button
          onClick={load}
          className="px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm font-semibold hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total domains" value={stats.total} />
        <StatCard label="With HubSpot" value={stats.with_hubspot} />
        <StatCard label="Recent total" value={changes.total || 0} />
        <StatCard label="HubSpot detected" value={changes.with_hubspot || 0} />
      </div>

      <div className="flex items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search domain, company, category"
          className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm focus:outline-none"
        />
      </div>

      <div className="overflow-auto rounded-xl border border-slate-800 bg-slate-900/70">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-800/70 text-slate-300">
            <tr>
              <th className="px-4 py-3 text-left">Company</th>
              <th className="px-4 py-3 text-left">Domain</th>
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-left">Source</th>
              <th className="px-4 py-3 text-left">Score</th>
              <th className="px-4 py-3 text-left">HubSpot</th>
              <th className="px-4 py-3 text-left">Signals</th>
              <th className="px-4 py-3 text-left">Last seen</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((d) => (
              <tr key={d.domain} className="border-t border-slate-800">
                <td className="px-4 py-3 font-semibold text-white">{d.company || d.domain}</td>
                <td className="px-4 py-3 text-emerald-300">{d.domain}</td>
                <td className="px-4 py-3 text-slate-300">{d.categoryName || '—'}</td>
                <td className="px-4 py-3 text-slate-400 uppercase">{d.source || 'seed'}</td>
                <td className="px-4 py-3"><ScoreBadge score={d.score || 0} /></td>
                <td className="px-4 py-3">
                  <StatusPill
                    status={d.hubspot?.has_hubspot ? 'running' : 'idle'}
                    label={d.hubspot?.has_hubspot ? `Yes (${d.hubspot.confidence || 0}%)` : 'No'}
                  />
                </td>
                <td className="px-4 py-3"><SignalsPillList signals={d.signals || []} /></td>
                <td className="px-4 py-3 text-slate-400">{d.last_seen || '—'}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleRemove(d.domain)}
                    className="px-3 py-1 rounded-lg bg-red-900/50 text-red-200 border border-red-800 text-xs"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={9}>
                  {loading ? 'Loading…' : 'No domains found'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatCard({ label, value }) {
  return (
    <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 shadow-sm">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="text-2xl font-semibold text-white">{value}</div>
    </div>
  )
}
