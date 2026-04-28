"""Agent: given the methodology analysis, propose and generate quantitative test scripts."""
import re
from typing import List, Dict
from app.models.validation import ModelUnderstanding
from .base import BaseAgent


_PROPOSE_PROMPT = """
Com base no modelo e na análise metodológica abaixo, proponha uma lista de testes quantitativos.

=== MODELO ===
{model_summary}

=== ANÁLISE METODOLÓGICA ===
{methodology_analysis}

Retorne JSON com:
{{
  "tests": [
    {{
      "test_id": "qt_001",
      "name": "nome do teste",
      "description": "o que o teste verifica",
      "category": "pricing|convergence|calibration|stress|boundary",
      "expected_outcome": "o que se espera encontrar",
      "risk_factors_involved": ["lista"]
    }}
  ]
}}
"""

_GENERATE_PROMPT = """
Escreva código Python 3.9+ que executa o seguinte teste quantitativo no modelo de precificação.

=== MODELO ===
{model_code_snippet}

=== TESTE ===
ID: {test_id}
Nome: {test_name}
Descrição: {test_description}
Fatores de risco: {risk_factors}

Requisitos:
1. Crie uma função `run_test_{test_id}(pricer_class) -> dict` que:
   - Instancia o pricer com parâmetros sintéticos razoáveis
   - Executa o teste
   - Retorna dict com: passed (bool), details (str), metrics (dict), figures_base64 (list[str])
2. Use matplotlib para gráficos, convertendo-os para base64 via io.BytesIO
3. Inclua `if __name__ == "__main__":` com exemplo de uso

Escreva APENAS o código Python, sem markdown.
"""


class QuantTestGeneratorAgent(BaseAgent):
    async def propose_tests(self, mu: ModelUnderstanding, methodology_analysis: str) -> List[Dict]:
        prompt = _PROPOSE_PROMPT.format(
            model_summary=mu.raw_summary,
            methodology_analysis=methodology_analysis,
        )
        data = await self.ask_json(prompt)
        return data.get("tests", [])

    async def generate_test_code(
        self,
        test: Dict,
        mu: ModelUnderstanding,
        replication_code: str,
    ) -> str:
        model_snippet = replication_code[:3000]
        prompt = _GENERATE_PROMPT.format(
            model_code_snippet=model_snippet,
            test_id=test["test_id"],
            test_name=test["name"],
            test_description=test["description"],
            risk_factors=", ".join(test.get("risk_factors_involved", [])),
        )
        code = await self.ask(prompt, temperature=0.1, max_tokens=8192)
        code = re.sub(r"^```(?:python)?\s*", "", code.strip())
        code = re.sub(r"\s*```$", "", code).strip()
        return code
