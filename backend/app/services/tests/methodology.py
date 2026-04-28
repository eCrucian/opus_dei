"""Test 2: Methodology assessment — premises, limitations, alternatives, quantitative test list."""
from app.models.validation import ModelUnderstanding, TestResult, TestStatus
from .base import BaseTest
from app.services.agents.base import BaseAgent


_PROMPT = """
Faça uma análise metodológica aprofundada do seguinte modelo de precificação.

=== MODELO ===
Produto: {product_type}
Metodologia: {pricing_methodology}
Resumo: {summary}
Fatores de risco: {risk_factors}
Equações: {equations}

Sua análise deve cobrir:

(i) **Premissas** — liste todas as premissas implícitas e explícitas do modelo
(ii) **Avaliação qualitativa** — para cada premissa, avalie se é razoável, quando falha e o impacto
(iii) **Comparação com alternativas** — compare com pelo menos 2 outros métodos para o mesmo problema:
     pontos fortes, pontos fracos, quando cada um é mais apropriado
(iv) **Testes quantitativos sugeridos** — liste os testes que devem ser conduzidos

Retorne JSON:
{{
  "premissas": [
    {{
      "premissa": "...",
      "tipo": "mercado|modelo|numerica|regulatoria",
      "avaliacao": "razoavel|questionavel|restritiva",
      "impacto_se_violada": "...",
      "contexto_br": "relevância no mercado brasileiro"
    }}
  ],
  "alternativas": [
    {{
      "nome": "método alternativo",
      "descricao": "...",
      "vantagens": ["..."],
      "desvantagens": ["..."],
      "quando_usar": "..."
    }}
  ],
  "testes_quantitativos": [
    {{
      "nome": "nome do teste",
      "descricao": "...",
      "tipo": "pricing|stress|convergence|calibration|boundary",
      "prioridade": "alta|media|baixa"
    }}
  ],
  "limitacoes_modelo": ["..."],
  "recomendacoes": ["..."],
  "impeditivos": ["..."],
  "sumario": "..."
}}
"""


class MethodologyTest(BaseTest):
    test_id = "T02_methodology"
    test_name = "Análise Metodológica"

    async def _execute(self, result: TestResult, mu: ModelUnderstanding) -> None:
        agent = BaseAgent(self.llm)
        rf_str = "\n".join(f"  - {rf.name} ({rf.type}): {rf.description}" for rf in mu.risk_factors)
        eq_str = "\n".join(f"  [{eq.label}]: {eq.latex} — {eq.description}" for eq in mu.equations)

        prompt = _PROMPT.format(
            product_type=mu.product_type,
            pricing_methodology=mu.pricing_methodology,
            summary=mu.raw_summary,
            risk_factors=rf_str or "  (não identificados)",
            equations=eq_str or "  (não identificadas)",
        )
        data = await agent.ask_json(prompt, max_tokens=12288)

        result.status = TestStatus.PASSED
        result.details = {
            "premissas": data.get("premissas", []),
            "alternativas": data.get("alternativas", []),
            "testes_sugeridos": data.get("testes_quantitativos", []),
            "limitacoes": data.get("limitacoes_modelo", []),
            "raw": data,
        }
        result.recommendations = data.get("recomendacoes", [])
        result.impediments = data.get("impeditivos", [])
        result.summary = data.get("sumario", "")
