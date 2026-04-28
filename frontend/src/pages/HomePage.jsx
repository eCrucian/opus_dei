import { Link } from 'react-router-dom'
import { ShieldCheck, FileSearch, BarChart3, Code2, FileText, Zap } from 'lucide-react'

const features = [
  { icon: FileSearch, title: 'Leitura Inteligente', desc: 'PDF, DOCX, Jupyter Notebook, Markdown — equações LaTeX e OMML extraídas automaticamente.' },
  { icon: ShieldCheck, title: 'Testes Automáticos', desc: 'Qualidade da doc, metodologia, estabilidade, curvatura, convergência Monte Carlo e replicação.' },
  { icon: BarChart3, title: 'Derivadas Numéricas', desc: 'Deltas e gammas computados em pontos simulados para validar estabilidade e curvatura.' },
  { icon: Code2, title: 'Replicação do Modelo', desc: 'IA gera código Python replicando o modelo documentado e compara com a implementação fornecida.' },
  { icon: Zap, title: 'IA Agnóstica', desc: 'DeepSeek R1 (Ollama local), GPT-4o, Claude ou Gemini — troque pelo .env.' },
  { icon: FileText, title: 'Relatório Completo', desc: 'Relatório HTML com tabelas, gráficos, opiniões e recomendações prontos para MRC/validadores.' },
]

export default function HomePage() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12">
      <div className="text-center mb-14">
        <h1 className="text-4xl font-bold text-navy-800 mb-4">
          Validador Automático de Modelos MtM
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Validação rigorosa de modelos de mark-to-market: documentação, metodologia,
          estabilidade, curvatura e aderência à implementação — com IA generativa especializada.
        </p>
        <div className="flex justify-center gap-4 mt-8">
          <Link to="/upload" className="btn-primary text-base px-8 py-3">
            Iniciar Validação
          </Link>
          <Link to="/jobs" className="btn-secondary text-base px-8 py-3">
            Ver Histórico
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {features.map(({ icon: Icon, title, desc }) => (
          <div key={title} className="card hover:shadow-md transition-shadow">
            <Icon className="w-7 h-7 text-blue-600 mb-3" />
            <h3 className="font-semibold text-gray-800 mb-1">{title}</h3>
            <p className="text-sm text-gray-500 leading-relaxed">{desc}</p>
          </div>
        ))}
      </div>

      <div className="mt-12 bg-navy-800 text-white rounded-2xl p-8">
        <h2 className="text-xl font-bold mb-4">Fluxo de Validação</h2>
        <ol className="space-y-2 text-sm text-blue-200">
          {[
            'Upload do documento do modelo (PDF/DOCX/ipynb/MD)',
            'IA extrai equações, fatores de risco e metodologia',
            'Teste T01: Qualidade da documentação (nota 0-10)',
            'Teste T02: Análise metodológica — premissas, alternativas, limitações',
            'Teste T03: Testes quantitativos gerados e executados por IA',
            'Replicação: IA gera código Python do modelo',
            'Teste T05: Estabilidade — derivadas primeiras em pontos simulados',
            'Teste T06: Curvatura — derivadas segundas e gammas cruzados',
            'Teste T07: Convergência Monte Carlo (se aplicável)',
            'Teste T08: Comparação implementação × documentação (se código fornecido)',
            'Relatório final com opinião: Favorável / Desfavorável / Favorável com Recomendações',
          ].map((step, i) => (
            <li key={i} className="flex gap-3">
              <span className="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
