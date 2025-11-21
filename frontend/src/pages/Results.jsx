import JobTable from '../components/JobTable'
import LiveBotWindow from '../components/LiveBotWindow'

export default function Results({ jobs = [], coverage = [] }) {
  return (
    <div className="space-y-6">
      <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-5">
        <h2 className="text-xl font-semibold text-white mb-4">Live Google Maps Bot</h2>
        <LiveBotWindow />
      </div>
      <div className="bg-panel rounded-2xl border border-slate-800 shadow-soft p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-semibold text-white">Company Coverage</h2>
          <span className="text-slate-500 text-sm">Hover rows for detail</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-slate-400 text-xs uppercase">
              <tr className="border-b border-slate-800">
                <th className="text-left py-2">Company</th>
                <th className="text-left py-2">Status</th>
                <th className="text-left py-2">Jobs</th>
                <th className="text-left py-2">Last Scan</th>
              </tr>
            </thead>
            <tbody>
              {coverage.map((c) => (
                <tr key={c.company} className="border-b border-slate-900 hover:bg-slate-900/50">
                  <td className="py-2 text-slate-100 font-semibold">{c.company}</td>
                  <td className="py-2 text-slate-200">{c.status}</td>
                  <td className="py-2 text-slate-200">{c.jobs}</td>
                  <td className="py-2 text-slate-400">{c.last_scan ? new Date(c.last_scan).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!coverage.length && <div className="text-slate-400 text-sm py-4">No companies loaded.</div>}
        </div>
      </div>
      <JobTable jobs={jobs} />
    </div>
  )
}
