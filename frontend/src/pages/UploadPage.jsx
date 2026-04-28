import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Info } from 'lucide-react'
import DocumentUpload from '../components/Upload/DocumentUpload'
import CodeUpload from '../components/Upload/CodeUpload'
import { startValidation } from '../services/api'

export default function UploadPage() {
  const [docFile, setDocFile] = useState(null)
  const [codeFiles, setCodeFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!docFile) return
    setLoading(true)
    setError(null)
    try {
      const { job_id } = await startValidation(docFile, codeFiles)
      navigate(`/validation/${job_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Erro ao iniciar validação.')
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Nova Validação de Modelo</h1>
        <p className="text-gray-500 mt-1">
          Faça upload da documentação do modelo e, opcionalmente, dos scripts ou planilhas de implementação.
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6 flex gap-3">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-800">
          <strong>Sem o documento, não é possível iniciar.</strong> A planilha/script é opcional —
          se fornecida, será comparada com a documentação.
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card">
          <DocumentUpload file={docFile} onFile={setDocFile} />
        </div>

        <div className="card">
          <CodeUpload files={codeFiles} onFiles={setCodeFiles} />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!docFile || loading}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>Iniciando...</>
            ) : (
              <>Iniciar Validação <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
