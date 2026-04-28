"""Agent: generate Python code that replicates the model as described in the documentation."""
import re
from app.models.validation import ModelUnderstanding
from .base import BaseAgent


_PROMPT = """
Com base no entendimento do modelo abaixo, escreva um módulo Python 3.9+ completo e funcional
que implemente o modelo de precificação exatamente como descrito na documentação.

=== MODELO ===
Produto: {product_type}
Metodologia: {pricing_methodology}
Fatores de risco: {risk_factors}
Equações:
{equations}

Requisitos do código:
1. Crie uma classe `ModelPricer` com:
   - `__init__(self, **params)` — recebe parâmetros cadastrais (notional, datas, etc.)
   - `price(self, risk_factors: dict) -> float` — recebe dict com fatores de risco e retorna o PV
   - `greeks(self, risk_factors: dict, bump=1e-4) -> dict` — calcula delta de cada fator de risco por bumping
   - `get_risk_factors(self) -> list[str]` — retorna nomes dos fatores de risco
2. Use numpy, scipy se necessário
3. Docstrings claras em cada método explicando o que representa matematicamente
4. Adicione constantes ou enums para os nomes dos fatores de risco
5. Inclua no topo do arquivo um bloco `# RISK_FACTORS = [...]` com a lista dos fatores
6. Inclua um `if __name__ == "__main__":` com exemplo de uso com dados sintéticos realistas

Escreva APENAS o código Python, sem markdown, sem explicações fora do código.
"""


class ModelReplicatorAgent(BaseAgent):
    async def replicate(self, mu: ModelUnderstanding) -> str:
        risk_factors_str = ", ".join(
            f"{rf.name} ({rf.type})" for rf in mu.risk_factors
        )
        equations_str = "\n".join(
            f"  [{eq.label}]: {eq.latex} — {eq.description}"
            for eq in mu.equations
        ) or "  (extrair equações do texto da documentação)"

        prompt = _PROMPT.format(
            product_type=mu.product_type,
            pricing_methodology=mu.pricing_methodology,
            risk_factors=risk_factors_str,
            equations=equations_str,
        )
        code = await self.ask(prompt, temperature=0.1, max_tokens=16384)
        # strip any accidental markdown fences
        code = re.sub(r"^```(?:python)?\s*", "", code.strip())
        code = re.sub(r"\s*```$", "", code).strip()
        return code
