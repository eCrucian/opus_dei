# Validador Automático de Modelos MtM

Sistema de validação automática de modelos de **mark-to-market** para produtos financeiros brasileiros e internacionais — renda fixa, renda variável, derivativos, estruturados e exóticos.

O sistema lê a documentação do modelo, entende as equações e fatores de risco, e executa uma bateria de testes técnicos assistidos por IA generativa, produzindo um relatório de validação com opinião final.

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Execução](#execução)
- [Fluxo de Validação](#fluxo-de-validação)
- [Testes Implementados](#testes-implementados)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Formatos Suportados](#formatos-suportados)

---

## Funcionalidades

- Upload de documentação do modelo (PDF, DOCX, Jupyter Notebook, Markdown)
- Upload opcional de implementação (Python, MATLAB, SQL, R, planilhas Excel)
- Extração automática de equações LaTeX e OMML (Word Equation Editor)
- Identificação de fatores de risco vs. parâmetros cadastrais
- Geração de código Python replicando o modelo documentado
- Execução de testes quantitativos gerados dinamicamente por IA
- Relatório HTML completo com tabelas, gráficos e opinião final
- Interface de IA agnóstica: Ollama (local), OpenAI, Anthropic, Google Gemini

---

## Arquitetura

### Backend — FastAPI + Python 3.12

```
backend/app/
├── config.py                    Configurações via .env
├── models/validation.py         Pydantic models (ValidationJob, TestResult, RiskFactor...)
├── api/routes/
│   ├── upload.py                POST /api/upload/start | GET /api/upload/jobs
│   ├── validation.py            GET /api/validation/{id}/status | /results
│   └── report.py                GET /api/report/{id} (HTML) | /download
├── services/
│   ├── llm/
│   │   ├── base.py              BaseLLMClient — interface abstrata única
│   │   ├── ollama.py            DeepSeek-R1 via Ollama (padrão local)
│   │   ├── openai_client.py     GPT-4o e compatíveis
│   │   ├── anthropic_client.py  Claude
│   │   ├── gemini_client.py     Google Gemini
│   │   └── factory.py           create_llm_client() — lê LLM_PROVIDER do .env
│   ├── parsers/
│   │   ├── document.py          PDF, DOCX, Jupyter Notebook, Markdown
│   │   ├── excel.py             .xlsx / .xlsm — extrai dados e fórmulas
│   │   └── code.py              Python, MATLAB, SQL, R, Julia
│   ├── agents/
│   │   ├── document_analyzer.py    Extrai equações, fatores de risco, metodologia
│   │   ├── model_replicator.py     Gera código Python da implementação do modelo
│   │   ├── quant_test_generator.py Propõe e escreve scripts de testes quantitativos
│   │   └── replica_comparator.py   Compara código fornecido × documentação
│   ├── tests/
│   │   ├── doc_quality.py    T01 — Qualidade da documentação (nota 0–10)
│   │   ├── methodology.py    T02 — Premissas, alternativas, limitações
│   │   ├── quantitative.py   T03 — Testes gerados e executados por IA
│   │   ├── stability.py      T05 — Derivadas primeiras (deltas)
│   │   ├── performance.py    T06 — Derivadas segundas (gammas + cross-gammas)
│   │   ├── monte_carlo.py    T07 — Convergência MC e sensibilidade à janela de vol
│   │   └── replication.py    T08 — Aderência implementação × documentação
│   ├── orchestrator.py       Pipeline assíncrono completo
│   └── report_generator.py   Relatório HTML via Jinja2 + opinião final da IA
└── utils/
    ├── storage.py             Persistência de jobs em JSON
    └── code_executor.py       Execução segura via subprocess (timeout 60s)
```

### Frontend — React 18 + Vite + Tailwind CSS

```
frontend/src/
├── pages/
│   ├── HomePage.jsx        Landing com features e fluxo dos 11 passos
│   ├── UploadPage.jsx      Formulário de upload com drag-and-drop
│   ├── ValidationPage.jsx  Progresso em tempo real + resultados dos testes
│   └── JobsPage.jsx        Histórico de todas as validações
├── components/
│   ├── Layout/Header.jsx
│   ├── Upload/
│   │   ├── DocumentUpload.jsx   Dropzone para o documento do modelo
│   │   └── CodeUpload.jsx       Dropzone para scripts e planilhas
│   └── Validation/
│       ├── ProgressTracker.jsx  Steps visuais + log em tempo real
│       └── TestCard.jsx         Card colapsável por teste com gráficos
├── hooks/useValidation.js   Polling automático a cada 3 segundos
└── services/api.js          Chamadas ao backend via axios
```

### Storage (gerado em tempo de execução)

```
backend/storage/
├── uploads/{job_id}/          Arquivos enviados pelo usuário
├── sessions/{job_id}.json     Estado completo do job (resultados, logs)
├── generated_code/{job_id}/   Código Python gerado pela IA (replicação + testes)
└── reports/{job_id}.html      Relatório final
```

---

## Pré-requisitos

| Componente | Versão mínima |
|---|---|
| Python | 3.9+ (recomendado 3.12) |
| Node.js | 18+ |
| npm | 9+ |
| Ollama (se usar local) | qualquer versão recente |

---

## Instalação

### 1. Clone / abra o projeto

```bash
cd opus_dei
```

### 2. Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (Linux/macOS)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

---

## Configuração

Copie o arquivo de exemplo e edite:

```bash
# Na raiz do projeto
copy .env.example backend\.env      # Windows
cp .env.example backend/.env        # Linux/macOS
```

Edite `backend/.env`:

```env
# Escolha o provider: ollama | openai | anthropic | gemini
LLM_PROVIDER=ollama

# --- Ollama (modelo local, padrão) ---
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:latest

# --- OpenAI (opcional) ---
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# --- Anthropic (opcional) ---
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-7

# --- Google Gemini (opcional) ---
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash
```

Para usar o **DeepSeek-R1 local via Ollama** (padrão), certifique-se de ter o modelo baixado:

```bash
ollama pull deepseek-r1:latest
```

---

## Execução

### Opção A — Script automático (Windows)

Na raiz do projeto, clique duas vezes em `start.bat` ou execute:

```bat
start.bat
```

Isso abre dois terminais: um para o backend e um para o frontend.

---

### Opção B — Manual (dois terminais)

**Terminal 1 — Backend:**

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS
python run.py
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

---

### URLs

| Serviço | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger / Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

---

## Fluxo de Validação

```
1.  Upload do documento do modelo (obrigatório)
        └── PDF · DOCX · Jupyter Notebook · Markdown · TXT

2.  Upload da implementação (opcional)
        └── Python · MATLAB · SQL · R · Julia · Excel (xlsx/xlsm)

3.  IA lê e entende o modelo
        └── Produto, metodologia, equações, fatores de risco, escopo regulatório

4.  T01 — Qualidade da documentação
        └── 8 critérios avaliados → nota 0–10

5.  T02 — Análise metodológica
        └── Premissas, avaliação qualitativa, comparação com alternativas,
            lista de testes quantitativos sugeridos

6.  IA gera código Python replicando o modelo (classe ModelPricer)

7.  T03 — Testes quantitativos
        └── IA propõe e escreve scripts de teste, que são executados
            automaticamente; resultados e figuras são capturados

8.  T05 — Estabilidade (derivadas primeiras)
        └── ∂PV/∂RF calculado em 200 pontos simulados
            Critério: delta finito e não-nulo para todos os fatores de risco

9.  T06 — Curvatura (derivadas segundas)
        └── ∂²PV/∂RF² e cross-gammas calculados
            Avaliação do impacto via expansão em série de Taylor

10. T07 — Convergência Monte Carlo (se aplicável)
        └── Teste com 100 → 10.000 simulações
            Sensibilidade do preço à janela de calibração de volatilidade

11. T08 — Comparação implementação × documentação (se código fornecido)
        └── IA avalia aderência, mapeia fatores de risco, lista divergências

12. Relatório final gerado em HTML
        └── Opinião: Favorável | Desfavorável | Favorável com Recomendações
            Impeditivos críticos e oportunidades de melhoria
```

---

## Testes Implementados

| ID | Nome | Critério de aprovação |
|---|---|---|
| T01 | Qualidade da Documentação | Nota ≥ 7/10 |
| T02 | Análise Metodológica | Sempre informativo (não bloqueante) |
| T03 | Testes Quantitativos | Todos os sub-testes gerados passam |
| T05 | Estabilidade | Todos os deltas finitos e não-nulos |
| T06 | Curvatura | Gammas calculados e classificados |
| T07 | Convergência MC | Variação < 1% nas últimas 3 etapas |
| T08 | Replicação | Score ≥ 7/10, sem impeditivos críticos |

---

## Formatos Suportados

### Documentação do modelo

| Formato | Extensão | Observação |
|---|---|---|
| PDF | `.pdf` | Texto extraído por página |
| Word | `.docx` | Inclui equações OMML do Equation Editor |
| Jupyter Notebook | `.ipynb` | Células markdown + outputs |
| Markdown | `.md` | Blocos LaTeX `$...$` e `$$...$$` |
| Texto | `.txt` | |

### Implementação (opcional)

| Formato | Extensão |
|---|---|
| Python | `.py` |
| MATLAB | `.m` |
| SQL | `.sql` |
| R | `.r` |
| Julia | `.jl` |
| Excel | `.xlsx` · `.xlsm` · `.xlsb` · `.xls` |

### Fatores de risco — regra de negócio central

**São** fatores de risco (inputs com movimento de mercado):
- Spots: câmbio (USD/BRL, EUR/BRL), preços de commodities, índices de ações
- Taxas de juros: sempre na forma de fator de desconto P(t,T), distinguindo accrual de projeção
- Volatilidades implícitas (superfície de vol, smile/skew)
- Correlações entre ativos (para modelos multi-ativos)
- Spreads de crédito

**Não são** fatores de risco:
- Notional / valor de face
- Datas de vencimento e de pagamento
- Barreiras, strikes e limites contratuais (valores fixos)
- Parâmetros cadastrais do produto

---

## Providers de IA

Para trocar o provider, basta alterar `LLM_PROVIDER` no `.env` e reiniciar o backend. Nenhuma outra alteração é necessária — a interface é completamente agnóstica ao modelo.

| Provider | `LLM_PROVIDER` | Requisito |
|---|---|---|
| Ollama (local) | `ollama` | Ollama rodando + modelo baixado |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini` | `GEMINI_API_KEY` |
