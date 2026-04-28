import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getJobs } from '../services/api'
import { CheckCircle2, XCircle, Loader2, Clock, ArrowRight } from 'lucide-react'

const STATUS_ICON = {
  done:    <CheckCircle2 className="w-4 h-4 text-green-500" />,
  error:   <XCircle className="w-4 h-4 text-red-500" />,
  pending: <Clock className="w-4 h-4 text-gray-400" />,
}

const statusFallback = <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />

export default function JobsPage() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getJobs().then(setJobs).finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="flex justify-center items-center h-64">
      <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Histórico de Validações</h1>
        <Link to="/upload" className="btn-primary text-sm">Nova Validação</Link>
      </div>

      {jobs.length === 0 ? (
        <div className="card text-center py-16">
          <p className="text-gray-500">Nenhuma validação realizada ainda.</p>
          <Link to="/upload" className="btn-primary mt-4 inline-block">Começar</Link>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map(job => (
            <Link
              key={job.job_id}
              to={`/validation/${job.job_id}`}
              className="card flex items-center gap-4 hover:shadow-md transition-shadow cursor-pointer no-underline"
            >
              {STATUS_ICON[job.status] || statusFallback}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800 truncate">
                  {job.doc_filename || job.job_id}
                </p>
                {job.product_type && (
                  <p className="text-xs text-gray-500">{job.product_type}</p>
                )}
                <p className="text-xs text-gray-400 mt-0.5">
                  {new Date(job.created_at).toLocaleString('pt-BR')}
                </p>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                job.status === 'done' ? 'bg-green-100 text-green-700' :
                job.status === 'error' ? 'bg-red-100 text-red-700' :
                'bg-blue-100 text-blue-700'
              }`}>
                {job.status}
              </span>
              <ArrowRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
