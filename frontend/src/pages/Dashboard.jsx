import StatusPill from '../components/StatusPill'
import RunControls from '../components/RunControls'
import AnimatedCount from '../components/AnimatedCount'
import ProgressRadial from '../components/ProgressRadial'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function Dashboard({ status, onRefresh, version }) {
  const history = status?.history || []
  const processed = status?.processed_companies || 0
  const total = status?.total_companies || 0

  return (
    <div className="space-y-6">
      <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-6 flex flex-col gap-4">
        <div className="flex flex-wrap justify-between gap-4 items-center">
          <div>
            <p className="text-slate-400 text-sm">HubSpot Job Discovery Agent</p>
            <h1 className="text-3xl font-semibold text-white">Control Room</h1>
            {version && (
              <p className="text-xs text-slate-500 mt-1">Backend {version.backendVersion} · Frontend {version.frontendVersion}</p>
            )}
          </div>
          <StatusPill status={status?.status || 'idle'} />
          <RunControls running={status?.running} onStatus={onRefresh} />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[{ label: 'Companies Scanned', value: status?.processed_companies || 0 }, { label: 'Jobs Found', value: status?.jobs_found || 0 }, { label: 'High Priority', value: status?.high_priority || 0 }, { label: 'US Remote', value: status?.remote_us || 0 }].map((card) => (
            <div key={card.label} className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-soft">
              <p className="text-sm text-slate-400">{card.label}</p>
              <div className="text-2xl font-bold text-white mt-1"><AnimatedCount value={card.value} /></div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-slate-400 text-sm mb-2">Coverage</p>
            <h3 className="text-xl font-semibold text-white">Company Coverage Map</h3>
            <p className="text-slate-400 text-sm">Hover companies in the Results Explorer for details.</p>
          </div>
          <ProgressRadial value={processed} total={total || 1} />
        </div>
        <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xl font-semibold text-white">Recent Runs</h3>
            <span className="text-slate-500 text-sm">Last {history.length} runs</span>
          </div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorJobs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#34d399" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#34d399" stopOpacity={0.1} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 10 }} hide />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#11141a', border: '1px solid #1f2937' }} labelStyle={{ color: '#e5e7eb' }} />
                <Area type="monotone" dataKey="delivered" stroke="#34d399" fillOpacity={1} fill="url(#colorJobs)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
