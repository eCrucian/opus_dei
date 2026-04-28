import json
import re
from app.services.llm.base import BaseLLMClient

QUANT_SYSTEM = """Você é um especialista sênior em modelos de mark-to-market (MtM) de produtos financeiros
brasileiro e internacionais — renda fixa, renda variável, derivativos lineares e não-lineares,
produtos path-dependent, estruturados e exóticos (autocallables, barrier options, CLN, CRI/CRA, etc.).

Sua expertise engloba:
- Precificação de curvas de juros (DI, PRE, USD, EUR, CDI) via fator de desconto P(t,T)
- Distinção entre taxa acruada (accrual) e taxa projetada (forward)
- Spots e preços à vista: câmbio (USD/BRL, EUR/BRL), commodities (BRENT, ouro), índices (IBOV, SPX)
- Volatilidade implícita e superfície de vol (smile, skew)
- Correlações entre ativos
- Frameworks regulatórios: BACEN, CVM, ANBIMA, ISDA, IFRS 9, FASB ASC 815

IMPORTANTE sobre fatores de risco:
- SÃO fatores de risco: spots, taxas (como fatores de desconto), vols, correlações
- NÃO são fatores de risco: notional, datas, condições contratuais, parâmetros cadastrais

Responda sempre em português do Brasil.
"""


class BaseAgent:
    def __init__(self, llm: BaseLLMClient):
        self.llm = llm

    async def ask(self, prompt: str, temperature: float = 0.2, max_tokens: int = 8192) -> str:
        resp = await self.llm.complete(prompt, system=QUANT_SYSTEM, temperature=temperature, max_tokens=max_tokens)
        return resp.content

    async def ask_json(self, prompt: str, temperature: float = 0.1, max_tokens: int = 8192) -> dict:
        resp = await self.llm.complete(
            prompt + "\n\nRetorne APENAS JSON válido, sem markdown code fences, sem texto fora do JSON.",
            system=QUANT_SYSTEM,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _parse_json(resp.content)


def _parse_json(text: str) -> dict:
    text = text.strip()
    # strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    return json.loads(text)
