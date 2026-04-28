import { useParams, Link } from 'react-router-dom'
import { ExternalLink, Download, FileText, RefreshCw } from 'lucide-react'
import { useValidation } from '../hooks/useValidation'
import ProgressTracker from '../components/Validation/ProgressTracker'
import TestCard from '../components/Validation/TestCard'
import { getReportUrl, getDownloadUrl } from '../services/api'

export default function ValidationPage() {
  const { jobId } = useParams()
  const { status, results, error } = useValidation(jobId)

  const isDone = status?.status === 'done'
  const isError = status?.status === 'error'

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Validação em Andamento</h1>
          <p className="text-xs text-gray-500 font-mono mt-1">{jobId}</p>
        </div>
        {isDone && (
          <div className="flex gap-2">
            <a
              href={getReportUrl(jobId)}
              target="_blank"
              rel="noreferrer"
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <FileText className="w-4 h-4" /> Ver Relatório
            </a>
            <a
              href={getDownloadUrl(jobId)}
              className="btn-secondary flex items-center gap-2 text-sm"
            >
              <Download className="w-4 h-4" /> Download
            </a>
          </div>
        )}
      </div>

      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-5">
          <h3 className="font-semibold text-red-700 mb-1">Erro na validação</h3>
          <p className="text-sm text-red-600">{error || status?.error}</p>
        </div>
      )}

      <ProgressTracker status={status} />

      {results?.model_understanding && (
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-3">Modelo Identificado</h2>
          <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div>
              <span className="text-gray-500">Produto:</span>{' '}
              <span className="font-medium">{results.model_understanding.product_type}</span>
            </div>
            <div>
              <span className="text-gray-500">Fatores de risco:</span>{' '}
              <span className="font-medium">{results.model_understanding.risk_factors?.length ?? 0}</span>
            </div>
            <div>
              <span className="text-gray-500">Monte Carlo:</span>{' '}
              <span className="font-medium">{results.model_understanding.has_monte_carlo ? 'Sim' : 'Não'}</span>
            </div>
            <div>
              <span className="text-gray-500">Equações:</span>{' '}
              <span className="font-medium">{results.model_understanding.equations?.length ?? 0}</span>
            </div>
          </div>
        </div>
      )}

      {results?.test_results?.length > 0 && (
        <div>
          <h2 className="font-semibold text-gray-800 mb-3">Resultados dos Testes</h2>
          <div className="space-y-3">
            {results.test_results.map(t => (
              <TestCard key={t.test_id} test={t} />
            ))}
          </div>
        </div>
      )}

      {!isDone && !isError && (
        <div className="text-center text-sm text-gray-500 flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" />
          Atualizando automaticamente a cada 3 segundos...
        </div>
      )}
    </div>
  )
}
