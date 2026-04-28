"""Agent: read the model document and produce a structured ModelUnderstanding."""
import json
from app.models.validation import ParsedDocument, ModelUnderstanding, RiskFactor, ModelEquation
from .base import BaseAgent


_PROMPT_TEMPLATE = """
Analise o documento de modelo abaixo e extraia as informações estruturadas.

=== DOCUMENTO ===
{doc_text}

=== EQUAÇÕES BRUTAS DETECTADAS ===
{equations}

Retorne um JSON com a seguinte estrutura EXATA (sem campos extras, sem markdown):
{{
  "product_type": "tipo do produto (ex: swap de taxa de juros, opção europeia, etc.)",
  "product_description": "descrição detalhada do produto em 2-4 parágrafos",
  "scope": "escopo de aplicação do modelo",
  "regulatory_scope": "escopo regulatório (BACEN, CVM, IFRS, etc.) ou null",
  "pricing_methodology": "descrição da metodologia de precificação",
  "has_monte_carlo": true/false,
  "has_multiple_assets": true/false,
  "risk_factors": [
    {{
      "name": "nome do fator",
      "type": "spot|rate|vol|spread|other",
      "description": "descrição",
      "curve_or_index": "nome da curva/índice ou null",
      "is_accrued": true/false/null,
      "is_projected": true/false/null
    }}
  ],
  "parameters": [
    {{"name": "nome", "description": "descrição", "unit": "unidade ou null"}}
  ],
  "equations": [
    {{
      "label": "rótulo/nome da equação",
      "latex": "equação em LaTeX",
      "description": "o que a equação representa",
      "variables": ["lista das variáveis"]
    }}
  ],
  "raw_summary": "resumo executivo do modelo em 3-5 parágrafos"
}}

ATENÇÃO:
- Fatores de risco SÃO: spots (câmbio, commodities), taxas de juros (como fatores de desconto P(t,T)),
  volatilidades, correlações, spreads de crédito
- NÃO são fatores de risco: notional, datas de vencimento, barreiras (valores fixos), condições cadastrais
- Se as equações estão em OMML (Word), infira o LaTeX equivalente com base no contexto
- Se não houver escopo regulatório explícito, coloque null
"""


class DocumentAnalyzerAgent(BaseAgent):
    async def analyze(self, doc: ParsedDocument) -> ModelUnderstanding:
        equations_str = "\n".join(f"  - {eq}" for eq in doc.equations_raw[:30]) or "  (nenhuma equação detectada automaticamente)"
        prompt = _PROMPT_TEMPLATE.format(
            doc_text=doc.raw_text[:40_000],
            equations=equations_str,
        )
        data = await self.ask_json(prompt, max_tokens=16384)

        risk_factors = [RiskFactor(**rf) for rf in data.get("risk_factors", [])]
        equations = [ModelEquation(**eq) for eq in data.get("equations", [])]

        return ModelUnderstanding(
            product_type=data.get("product_type", ""),
            product_description=data.get("product_description", ""),
            scope=data.get("scope", ""),
            regulatory_scope=data.get("regulatory_scope"),
            pricing_methodology=data.get("pricing_methodology", ""),
            has_monte_carlo=data.get("has_monte_carlo", False),
            has_multiple_assets=data.get("has_multiple_assets", False),
            risk_factors=risk_factors,
            parameters=data.get("parameters", []),
            equations=equations,
            raw_summary=data.get("raw_summary", ""),
        )
