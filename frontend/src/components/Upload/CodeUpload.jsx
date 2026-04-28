import { useDropzone } from 'react-dropzone'
import { Code2, FileSpreadsheet, X, Plus } from 'lucide-react'

const ACCEPTED = {
  'text/x-python': ['.py'],
  'text/x-matlab': ['.m'],
  'text/x-sql': ['.sql'],
  'text/x-r': ['.r'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx', '.xlsm'],
  'application/vnd.ms-excel': ['.xls'],
}

const iconFor = (name) => {
  const ext = name.split('.').pop().toLowerCase()
  if (['xlsx', 'xlsm', 'xlsb', 'xls'].includes(ext)) return FileSpreadsheet
  return Code2
}

export default function CodeUpload({ files, onFiles }) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPTED,
    multiple: true,
    onDrop: (accepted) => onFiles([...files, ...accepted]),
  })

  const remove = (idx) => onFiles(files.filter((_, i) => i !== idx))

  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-2">
        Scripts / Planilhas <span className="text-gray-400 font-normal text-xs">(opcional)</span>
        <span className="ml-2 text-xs font-normal text-gray-500">
          .py · .m · .sql · .r · .xlsx · .xlsm
        </span>
      </label>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all mb-3 ${
          isDragActive
            ? 'border-green-500 bg-green-50'
            : 'border-gray-300 hover:border-green-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <Plus className="w-7 h-7 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-500 text-sm">
          {isDragActive ? 'Solte aqui...' : 'Adicionar implementação'}
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, idx) => {
            const Icon = iconFor(f.name)
            return (
              <div key={idx} className="flex items-center gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <Icon className="w-5 h-5 text-green-600 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate">{f.name}</p>
                  <p className="text-xs text-gray-500">{(f.size / 1024).toFixed(1)} KB</p>
                </div>
                <button onClick={() => remove(idx)} className="p-1 text-gray-400 hover:text-red-500 rounded">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
