import { CheckCircle2, XCircle, AlertTriangle, MinusCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

const statusConfig = {
  passed:  { icon: CheckCircle2, color: 'text-green-600', bg: 'bg-green-50 border-green-200', label: 'Aprovado' },
  failed:  { icon: XCircle,      color: 'text-red-600',   bg: 'bg-red-50 border-red-200',     label: 'Reprovado' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-50 border-yellow-200', label: 'Atenção' },
  skipped: { icon: MinusCircle,  color: 'text-gray-400',  bg: 'bg-gray-50 border-gray-200',   label: 'N/A' },
  pending: { icon: MinusCircle,  color: 'text-gray-400',  bg: 'bg-gray-50 border-gray-200',   label: 'Pendente' },
}

export default function TestCard({ test }) {
  const [open, setOpen] = useState(false)
  const cfg = statusConfig[test.status] || statusConfig.pending
  const Icon = cfg.icon
  const hasScore = test.score != null

  return (
    <div className={`border rounded-xl overflow-hidden ${cfg.bg}`}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 p-4 text-left hover:brightness-95 transition-all"
      >
        <Icon className={`w-5 h-5 flex-shrink-0 ${cfg.color}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-800">{test.test_name}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.color} bg-white border ${cfg.bg.split(' ')[1]}`}>
              {cfg.label}
            </span>
          </div>
          {hasScore && (
            <div className="mt-1.5 flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-white/60 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${(test.score / test.max_score) * 100}%`,
                    background: test.score >= 7 ? '#16a34a' : test.score >= 4 ? '#d97706' : '#dc2626',
                  }}
                />
              </div>
              <span className="text-xs font-mono text-gray-600 whitespace-nowrap">
                {test.score.toFixed(1)} / {test.max_score.toFixed(0)}
              </span>
            </div>
          )}
          <p className="text-xs text-gray-600 mt-1 truncate">{test.summary}</p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" /> : <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />}
      </button>

      {open && (
        <div className="border-t border-current/10 p-4 bg-white/70 space-y-3">
          {test.impediments?.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-red-700 uppercase tracking-wide mb-1">Impeditivos</h4>
              <ul className="space-y-1">
                {test.impediments.map((item, i) => (
                  <li key={i} className="text-sm text-red-700 flex gap-2">
                    <span className="mt-0.5 flex-shrink-0">•</span>{item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {test.recommendations?.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-amber-700 uppercase tracking-wide mb-1">Recomendações</h4>
              <ul className="space-y-1">
                {test.recommendations.map((item, i) => (
                  <li key={i} className="text-sm text-amber-800 flex gap-2">
                    <span className="mt-0.5 flex-shrink-0">•</span>{item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {test.figures?.length > 0 && (
            <div className="space-y-3">
              {test.figures.map((fig, i) => (
                <img
                  key={i}
                  src={`data:image/png;base64,${fig}`}
                  alt={`Figura ${i + 1}`}
                  className="rounded-lg border border-gray-200 max-w-full"
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
