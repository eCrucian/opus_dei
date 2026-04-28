"""Agent: compare provided code/Excel against the model documentation."""
from app.models.validation import ModelUnderstanding, ParsedCode
from .base import BaseAgent


_PROMPT = """
Compare o código/planilha fornecido(a) com a documentação do modelo e avalie a aderência.

=== DOCUMENTAÇÃO DO MODELO ===
{model_summary}

Fatores de risco documentados:
{risk_factors}

Equações documentadas:
{equations}

=== IMPLEMENTAÇÃO FORNECIDA ===
{code_summary}

Retorne JSON:
{{
  "adherence_score": 0-10,
  "adheres_to_methodology": true/false,
  "findings": [
    {{
      "type": "match|discrepancy|gap|limitation",
      "element": "o que foi analisado",
      "description": "detalhamento",
      "severity": "critical|major|minor|info"
    }}
  ],
  "risk_factors_mapped": ["fatores encontrados na implementação"],
  "risk_factors_missing": ["fatores na doc mas ausentes no código"],
  "undocumented_logic": ["lógica no código não coberta pela doc"],
  "summary": "parágrafo com avaliação geral"
}}
"""


class ReplicaComparatorAgent(BaseAgent):
    async def compare(
        self,
        mu: ModelUnderstanding,
        provided_code: ParsedCode,
        replication_code: str,
    ) -> dict:
        rf_str = "\n".join(f"  - {rf.name} ({rf.type}): {rf.description}" for rf in mu.risk_factors)
        eq_str = "\n".join(f"  [{eq.label}]: {eq.latex}" for eq in mu.equations)

        code_summary = ""
        for f in provided_code.files[:5]:
            code_summary += f"\n### {f['filename']} ({f['language']})\n"
            code_summary += f['content'][:4000]

        prompt = _PROMPT.format(
            model_summary=mu.raw_summary,
            risk_factors=rf_str,
            equations=eq_str,
            code_summary=code_summary[:20000],
        )
        return await self.ask_json(prompt, max_tokens=8192)
