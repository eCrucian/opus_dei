import { CheckCircle2, XCircle, Loader2, Clock, AlertTriangle } from 'lucide-react'

const STATUS_STEPS = [
  { key: 'parsing',           label: 'Leitura dos arquivos' },
  { key: 'analyzing',         label: 'Análise do modelo pela IA' },
  { key: 'testing',           label: 'Execução dos testes' },
  { key: 'generating_report', label: 'Geração do relatório' },
  { key: 'done',              label: 'Concluído' },
]

const ORDER = STATUS_STEPS.map(s => s.key)

function stepState(stepKey, currentStatus) {
  const stepIdx = ORDER.indexOf(stepKey)
  const curIdx = ORDER.indexOf(currentStatus)
  if (currentStatus === 'error') return 'error'
  if (curIdx > stepIdx) return 'done'
  if (curIdx === stepIdx) return 'running'
  return 'pending'
}

const icons = {
  done:    <CheckCircle2 className="w-5 h-5 text-green-500" />,
  running: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
  pending: <Clock className="w-5 h-5 text-gray-300" />,
  error:   <XCircle className="w-5 h-5 text-red-500" />,
}

export default function ProgressTracker({ status }) {
  if (!status) return null
  const { status: st, progress_log = [], tests_completed = 0 } = status

  return (
    <div className="card space-y-5">
      <h2 className="font-semibold text-gray-800">Progresso da Validação</h2>

      <ol className="space-y-3">
        {STATUS_STEPS.map(({ key, label }) => {
          const state = stepState(key, st)
          return (
            <li key={key} className="flex items-center gap-3">
              {icons[state] || icons.pending}
              <span className={`text-sm ${
                state === 'done' ? 'text-green-700 font-medium' :
                state === 'running' ? 'text-blue-700 font-semibold' :
                state === 'error' ? 'text-red-600' :
                'text-gray-400'
              }`}>
                {label}
              </span>
              {state === 'running' && key === 'testing' && tests_completed > 0 && (
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                  {tests_completed} teste(s)
                </span>
              )}
            </li>
          )
        })}
      </ol>

      {progress_log.length > 0 && (
        <div className="bg-gray-900 rounded-lg p-4 max-h-48 overflow-y-auto">
          {progress_log.slice(-15).map((line, i) => (
            <p key={i} className="text-xs text-gray-300 font-mono leading-5">{line}</p>
          ))}
        </div>
      )}
    </div>
  )
}
