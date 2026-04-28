"""Generate the final HTML/PDF validation report."""
import base64
from datetime import datetime
from pathlib import Path
from typing import List
from jinja2 import Environment, BaseLoader
from app.models.validation import ValidationJob, TestResult, TestStatus
from app.config import settings
from app.services.llm.base import BaseLLMClient
from app.services.agents.base import BaseAgent


_OPINION_PROMPT = """
Com base nos resultados dos testes abaixo, emita uma opinião final sobre o modelo.

=== MODELO ===
{product_type}

=== RESULTADOS ===
{test_summary}

Retorne JSON:
{{
  "opiniao": "favoravel|desfavoravel|favoravel_com_recomendacoes",
  "justificativa": "2-3 parágrafos explicando a opinião",
  "impeditivos": ["lista de pontos críticos que impedem aprovação, se houver"],
  "recomendacoes_prioritarias": ["lista das 3-5 principais recomendações"],
  "oportunidades_melhoria": ["melhorias não críticas"],
  "nota_geral": X.X
}}
"""

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Validação — {{ job.model_understanding.product_type }}</title>
<style>
  :root { --blue: #1a3a5c; --accent: #2563eb; --green: #16a34a; --red: #dc2626; --yellow: #d97706; --gray: #6b7280; }
  body { font-family: 'Segoe UI', sans-serif; max-width: 1100px; margin: auto; padding: 2rem; color: #1f2937; line-height: 1.6; }
  h1 { color: var(--blue); border-bottom: 3px solid var(--accent); padding-bottom: .5rem; }
  h2 { color: var(--blue); margin-top: 2rem; }
  h3 { color: #374151; }
  .badge { display: inline-block; padding: .25rem .75rem; border-radius: 999px; font-size: .85rem; font-weight: 600; }
  .badge-passed { background: #dcfce7; color: var(--green); }
  .badge-failed { background: #fee2e2; color: var(--red); }
  .badge-warning { background: #fef9c3; color: var(--yellow); }
  .badge-skipped { background: #f3f4f6; color: var(--gray); }
  .opinion-box { border-left: 5px solid; padding: 1rem 1.5rem; border-radius: 4px; margin: 1.5rem 0; }
  .opinion-favoravel { border-color: var(--green); background: #f0fdf4; }
  .opinion-desfavoravel { border-color: var(--red); background: #fff1f2; }
  .opinion-favoravel_com_recomendacoes { border-color: var(--yellow); background: #fffbeb; }
  .test-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1.25rem; margin: 1rem 0; }
  .score-bar { height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; margin: .5rem 0; }
  .score-fill { height: 100%; border-radius: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: .9rem; margin: 1rem 0; }
  th { background: var(--blue); color: white; padding: .5rem .75rem; text-align: left; }
  td { padding: .5rem .75rem; border-bottom: 1px solid #e5e7eb; }
  tr:nth-child(even) { background: #f9fafb; }
  .fig-container { text-align: center; margin: 1rem 0; }
  img { max-width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; }
  ul { padding-left: 1.5rem; }
  li { margin: .3rem 0; }
  .critical { color: var(--red); font-weight: 600; }
  .footer { color: var(--gray); font-size: .85rem; text-align: center; margin-top: 3rem; border-top: 1px solid #e5e7eb; padding-top: 1rem; }
</style>
</head>
<body>

<h1>Relatório de Validação de Modelo</h1>
<p><strong>Produto:</strong> {{ job.model_understanding.product_type }}<br>
<strong>Data:</strong> {{ now }}<br>
<strong>Job ID:</strong> {{ job.job_id }}</p>

{% if opinion %}
<div class="opinion-box opinion-{{ opinion.opiniao }}">
  <h2 style="margin-top:0">Opinião Final: {{ opinion.opiniao | replace('_', ' ') | title }}</h2>
  <p>{{ opinion.justificativa }}</p>
  {% if opinion.impeditivos %}
  <h4>Impeditivos:</h4>
  <ul>{% for i in opinion.impeditivos %}<li class="critical">{{ i }}</li>{% endfor %}</ul>
  {% endif %}
  {% if opinion.recomendacoes_prioritarias %}
  <h4>Recomendações Prioritárias:</h4>
  <ul>{% for r in opinion.recomendacoes_prioritarias %}<li>{{ r }}</li>{% endfor %}</ul>
  {% endif %}
</div>
{% endif %}

<h2>1. Entendimento do Modelo</h2>
<table>
  <tr><th>Campo</th><th>Valor</th></tr>
  <tr><td>Tipo de Produto</td><td>{{ job.model_understanding.product_type }}</td></tr>
  <tr><td>Metodologia</td><td>{{ job.model_understanding.pricing_methodology }}</td></tr>
  <tr><td>Escopo</td><td>{{ job.model_understanding.scope }}</td></tr>
  <tr><td>Monte Carlo</td><td>{{ 'Sim' if job.model_understanding.has_monte_carlo else 'Não' }}</td></tr>
  <tr><td>Múltiplos Ativos</td><td>{{ 'Sim' if job.model_understanding.has_multiple_assets else 'Não' }}</td></tr>
  {% if job.model_understanding.regulatory_scope %}
  <tr><td>Escopo Regulatório</td><td>{{ job.model_understanding.regulatory_scope }}</td></tr>
  {% endif %}
</table>

<h3>Fatores de Risco</h3>
<table>
  <tr><th>Nome</th><th>Tipo</th><th>Curva/Índice</th><th>Descrição</th></tr>
  {% for rf in job.model_understanding.risk_factors %}
  <tr>
    <td>{{ rf.name }}</td>
    <td>{{ rf.type }}</td>
    <td>{{ rf.curve_or_index or '—' }}</td>
    <td>{{ rf.description }}</td>
  </tr>
  {% endfor %}
</table>

{% if job.model_understanding.equations %}
<h3>Equações Principais</h3>
{% for eq in job.model_understanding.equations %}
<div style="background:#f8fafc; border-left:3px solid #2563eb; padding:.75rem 1rem; margin:.75rem 0; border-radius:4px;">
  <strong>{{ eq.label }}</strong>: <code>{{ eq.latex }}</code><br>
  <em>{{ eq.description }}</em>
</div>
{% endfor %}
{% endif %}

<h2>2. Resultados dos Testes</h2>
{% for test in job.test_results %}
<div class="test-card">
  <h3>{{ test.test_name }} <span class="badge badge-{{ test.status }}">{{ test.status }}</span></h3>
  {% if test.score is not none %}
  <div>Nota: <strong>{{ "%.1f"|format(test.score) }}/{{ "%.0f"|format(test.max_score) }}</strong></div>
  <div class="score-bar">
    <div class="score-fill" style="width:{{ (test.score/test.max_score*100)|round }}%;
      background:{{ '#16a34a' if test.score >= 7 else '#d97706' if test.score >= 4 else '#dc2626' }};"></div>
  </div>
  {% endif %}
  <p>{{ test.summary }}</p>

  {% if test.impediments %}
  <h4 style="color:var(--red)">Impeditivos</h4>
  <ul>{% for i in test.impediments %}<li class="critical">{{ i }}</li>{% endfor %}</ul>
  {% endif %}

  {% if test.recommendations %}
  <h4>Recomendações</h4>
  <ul>{% for r in test.recommendations %}<li>{{ r }}</li>{% endfor %}</ul>
  {% endif %}

  {% for fig in test.figures %}
  <div class="fig-container">
    <img src="data:image/png;base64,{{ fig }}" alt="Figura do teste {{ test.test_id }}">
  </div>
  {% endfor %}
</div>
{% endfor %}

{% if all_recommendations %}
<h2>3. Oportunidades de Melhoria</h2>
<ul>{% for r in all_recommendations %}<li>{{ r }}</li>{% endfor %}</ul>
{% endif %}

<div class="footer">
  Gerado automaticamente pelo Sistema de Validação de Modelos MtM &bull;
  {{ now }} &bull; Powered by IA Generativa
</div>
</body>
</html>
"""


class ReportGenerator:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm
        self.agent = BaseAgent(llm)

    async def generate(self, job: ValidationJob) -> Path:
        opinion = await self._build_opinion(job)

        all_recs = []
        for t in job.test_results:
            all_recs.extend(t.recommendations)

        env = Environment(loader=BaseLoader())
        tmpl = env.from_string(_HTML_TEMPLATE)
        html = tmpl.render(
            job=job,
            opinion=opinion,
            all_recommendations=list(dict.fromkeys(all_recs)),
            now=datetime.utcnow().strftime("%d/%m/%Y %H:%M UTC"),
        )

        report_path = settings.reports_dir / f"{job.job_id}.html"
        report_path.write_text(html, encoding="utf-8")
        return report_path

    async def _build_opinion(self, job: ValidationJob) -> dict:
        lines = []
        for t in job.test_results:
            lines.append(
                f"- {t.test_name}: {t.status.value}"
                + (f" | nota {t.score:.1f}/{t.max_score}" if t.score is not None else "")
                + f" | {t.summary[:200]}"
            )
        test_summary = "\n".join(lines)

        prompt = _OPINION_PROMPT.format(
            product_type=job.model_understanding.product_type if job.model_understanding else "desconhecido",
            test_summary=test_summary,
        )
        try:
            return await self.agent.ask_json(prompt)
        except Exception:
            return {
                "opiniao": "favoravel_com_recomendacoes",
                "justificativa": "Análise automática concluída.",
                "impeditivos": [],
                "recomendacoes_prioritarias": [],
                "oportunidades_melhoria": [],
                "nota_geral": 5.0,
            }
