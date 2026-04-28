import { useDropzone } from 'react-dropzone'
import { FileText, X, Upload } from 'lucide-react'

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/x-ipynb+json': ['.ipynb'],
  'text/markdown': ['.md'],
  'text/plain': ['.txt'],
}

export default function DocumentUpload({ file, onFile }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPTED,
    maxFiles: 1,
    onDrop: (accepted) => accepted[0] && onFile(accepted[0]),
  })

  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-2">
        Documento do Modelo <span className="text-red-500">*</span>
        <span className="ml-2 text-xs font-normal text-gray-500">
          PDF, DOCX, Jupyter Notebook, Markdown
        </span>
      </label>

      {file ? (
        <div className="flex items-center gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <FileText className="w-6 h-6 text-blue-600 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-800 truncate">{file.name}</p>
            <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
          <button
            onClick={() => onFile(null)}
            className="p-1 text-gray-400 hover:text-red-500 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
            isDragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
          <p className="text-gray-600 font-medium">
            {isDragActive ? 'Solte aqui...' : 'Arraste ou clique para selecionar'}
          </p>
          <p className="text-xs text-gray-400 mt-1">.pdf · .docx · .ipynb · .md · .txt</p>
        </div>
      )}
    </div>
  )
}
