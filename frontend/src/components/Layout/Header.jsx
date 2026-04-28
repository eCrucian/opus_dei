import { Link } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-navy-800 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
          <ShieldCheck className="w-7 h-7 text-blue-400" />
          <div>
            <div className="font-bold text-lg leading-tight">Validador MtM</div>
            <div className="text-xs text-blue-300">Validação automática de modelos de mercado</div>
          </div>
        </Link>
        <nav className="flex items-center gap-6 text-sm text-blue-200">
          <Link to="/" className="hover:text-white transition-colors">Início</Link>
          <Link to="/upload" className="hover:text-white transition-colors">Nova Validação</Link>
          <Link to="/jobs" className="hover:text-white transition-colors">Histórico</Link>
        </nav>
      </div>
    </header>
  )
}
