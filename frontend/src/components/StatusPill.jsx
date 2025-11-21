const variants = {
  running: 'bg-emerald-500/20 text-emerald-200 border border-emerald-500/40',
  scheduled: 'bg-amber-500/20 text-amber-200 border border-amber-500/40',
  idle: 'bg-slate-700/50 text-slate-200 border border-slate-600/40',
}

export default function StatusPill({ status = 'idle' }) {
  const text = status === 'running' ? 'Running' : status === 'scheduled' ? 'Scheduled' : 'Idle'
  return <span className={`px-3 py-1 rounded-full text-sm font-medium ${variants[status] || variants.idle}`}>{text}</span>
}
