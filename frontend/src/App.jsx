import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Logs from './pages/Logs'
import Results from './pages/Results'
import useStatus from './hooks/useStatus'

const tabs = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'logs', label: 'Live Logs' },
  { id: 'results', label: 'Results' },
]

export default function App() {
  const [active, setActive] = useState('dashboard')
  const { status, results, refresh } = useStatus()

  return (
    <div className="min-h-screen bg-surface text-white">
      <header className="px-6 py-4 border-b border-slate-800 flex items-center justify-between sticky top-0 bg-surface/95 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-300 font-bold">
            HS
          </div>
          <div>
            <div className="text-sm text-slate-400">HubSpot Radar</div>
            <div className="text-lg font-semibold">Job Discovery Agent</div>
          </div>
        </div>
        <nav className="flex items-center gap-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors border border-transparent ${
                active === tab.id ? 'bg-slate-800 text-white border-slate-700' : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="px-6 py-6 space-y-6">
        {active === 'dashboard' && <Dashboard status={status} onRefresh={refresh} />}
        {active === 'logs' && <Logs />}
        {active === 'results' && <Results jobs={results.jobs} coverage={results.coverage} />}
      </main>
    </div>
  )
}
