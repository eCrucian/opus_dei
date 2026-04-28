"""Test 1: Documentation quality assessment (score 0-10)."""
from app.models.validation import ParsedDocument, ModelUnderstanding, TestResult, TestStatus
from .base import BaseTest
from app.services.agents.base import BaseAgent, QUANT_SYSTEM


_CRITERIA = """
Avalie a documentação do modelo nos seguintes critérios (0-10 cada):

1. **Clareza** — linguagem precisa, sem ambiguidades, fórmulas bem definidas
2. **Completude** — cobre todo o ciclo de vida do produto (payoff, valorização, sensibilidades)
3. **Declaração de escopo** — define explicitamente o que o modelo cobre e o que não cobre
4. **Premissas** — lista e justifica as premissas do modelo
5. **Testes e validação** — há evidência de backtesting, stress test ou benchmarking
6. **Equacionamento** — equações matemáticas presentes, corretas e referenciadas
7. **Fatores de risco** — identificação clara dos fatores de risco e parâmetros
8. **Escopo regulatório** — alinhamento com normas (BACEN, CVM, IFRS, ISDA) se aplicável

Para cada critério, dê uma nota de 0 a 10 e justifique brevemente.

Retorne JSON:
{{
  "scores": {{
    "clareza": {{"score": X, "justificativa": "..."}},
    "completude": {{"score": X, "justificativa": "..."}},
    "escopo": {{"score": X, "justificativa": "..."}},
    "premissas": {{"score": X, "justificativa": "..."}},
    "testes": {{"score": X, "justificativa": "..."}},
    "equacionamento": {{"score": X, "justificativa": "..."}},
    "fatores_risco": {{"score": X, "justificativa": "..."}},
    "escopo_regulatorio": {{"score": X, "justificativa": "..."}}
  }},
  "nota_geral": X.X,
  "pontos_fortes": ["..."],
  "pontos_fracos": ["..."],
  "recomendacoes": ["..."],
  "impeditivos": ["..."],
  "sumario": "..."
}}
"""


class DocQualityTest(BaseTest):
    test_id = "T01_doc_quality"
    test_name = "Qualidade da Documentação"

    async def _execute(self, result: TestResult, doc: ParsedDocument, mu: ModelUnderstanding) -> None:
        agent = BaseAgent(self.llm)
        prompt = f"""
Documento do modelo:
=== TEXTO ===
{doc.raw_text[:30000]}

=== ENTENDIMENTO EXTRAÍDO ===
Produto: {mu.product_type}
Metodologia: {mu.pricing_methodology}
Fatores de risco identificados: {len(mu.risk_factors)}
Equações identificadas: {len(mu.equations)}

{_CRITERIA}
"""
        data = await agent.ask_json(prompt, max_tokens=8192)

        scores = data.get("scores", {})
        nota = data.get("nota_geral", 0)

        result.score = float(nota)
        result.max_score = 10.0
        result.details = {
            "scores": scores,
            "pontos_fortes": data.get("pontos_fortes", []),
            "pontos_fracos": data.get("pontos_fracos", []),
        }
        result.recommendations = data.get("recomendacoes", [])
        result.impediments = data.get("impeditivos", [])
        result.summary = data.get("sumario", "")

        if nota >= 7:
            result.status = TestStatus.PASSED
        elif nota >= 4:
            result.status = TestStatus.WARNING
        else:
            result.status = TestStatus.FAILED
