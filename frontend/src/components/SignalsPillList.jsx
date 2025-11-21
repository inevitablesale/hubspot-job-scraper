export default function SignalsPillList({ signals = [] }) {
  if (!signals.length) return <span className="text-slate-500 text-sm">—</span>
  return (
    <div className="flex flex-wrap gap-2">
      {signals.map((s, i) => (
        <span key={`${s}-${i}`} className="px-2 py-1 rounded-full bg-slate-800 text-slate-200 text-xs border border-slate-700">
          {s}
        </span>
      ))}
    </div>
  )
}
