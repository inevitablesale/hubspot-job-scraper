export default function ScoreBadge({ score }) {
  const tone = score >= 80 ? 'bg-emerald-500/20 text-emerald-200 border-emerald-400/40' : score >= 60 ? 'bg-amber-500/20 text-amber-100 border-amber-400/40' : 'bg-slate-700 text-slate-200 border-slate-600'
  return <span className={`px-2 py-1 rounded-lg border text-xs font-semibold ${tone}`}>{score}</span>
}
