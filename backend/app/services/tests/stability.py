"""Test 5: Stability — first derivatives (deltas) must be finite and non-zero at simulated points."""
import ast
import io
import base64
import textwrap
from typing import Any
import numpy as np
from app.models.validation import ModelUnderstanding, TestResult, TestStatus
from .base import BaseTest
from app.utils.code_executor import safe_exec


_DRIVER_TEMPLATE = """
import numpy as np
import sys

{model_code}

def _run_stability(n_points=200, bump=1e-4, seed=42):
    np.random.seed(seed)
    rng = np.random.default_rng(seed)

    risk_factor_names = {risk_factors}

    results = []
    all_finite = True
    any_nonzero = False

    for _ in range(n_points):
        # Simulate realistic market inputs
        rf = {{}}
        for name in risk_factor_names:
            if "rate" in name.lower() or "taxa" in name.lower() or "juros" in name.lower():
                rf[name] = rng.uniform(0.05, 0.20)   # 5% to 20% rates
            elif "vol" in name.lower():
                rf[name] = rng.uniform(0.05, 0.80)   # 5% to 80% vol
            elif "spot" in name.lower() or "price" in name.lower() or "preco" in name.lower():
                rf[name] = rng.uniform(50, 200)
            elif "fx" in name.lower() or "cambio" in name.lower() or "usd" in name.lower():
                rf[name] = rng.uniform(4.5, 6.5)
            else:
                rf[name] = rng.uniform(0.8, 1.2)

        try:
            pricer = ModelPricer()
            pv0 = pricer.price(rf)

            deltas = {{}}
            for fname in risk_factor_names:
                rf_up = dict(rf)
                rf_dn = dict(rf)
                rf_up[fname] = rf[fname] * (1 + bump)
                rf_dn[fname] = rf[fname] * (1 - bump)
                pv_up = pricer.price(rf_up)
                pv_dn = pricer.price(rf_dn)
                delta = (pv_up - pv_dn) / (2 * rf[fname] * bump)
                deltas[fname] = delta

                if not np.isfinite(delta):
                    all_finite = False
                if abs(delta) > 1e-10:
                    any_nonzero = True

            results.append({{"pv": pv0, "deltas": deltas, "rf": rf}})
        except Exception as e:
            results.append({{"error": str(e), "rf": rf}})

    return {{
        "n_points": n_points,
        "all_deltas_finite": all_finite,
        "any_delta_nonzero": any_nonzero,
        "sample_results": results[:5],
        "passed": all_finite and any_nonzero,
    }}

_result = _run_stability()
"""


class StabilityTest(BaseTest):
    test_id = "T05_stability"
    test_name = "Teste de Estabilidade (Derivadas Primeiras)"

    async def _execute(
        self,
        result: TestResult,
        mu: ModelUnderstanding,
        replication_code: str,
    ) -> None:
        rf_names = [rf.name for rf in mu.risk_factors]
        driver = _DRIVER_TEMPLATE.format(
            model_code=replication_code,
            risk_factors=repr(rf_names),
        )

        output = safe_exec(driver, "_result")

        if output is None:
            result.status = TestStatus.WARNING
            result.summary = "Não foi possível executar o código replicado para o teste de estabilidade."
            return

        passed = output.get("passed", False)
        result.status = TestStatus.PASSED if passed else TestStatus.FAILED
        result.details = {
            "n_points_simulated": output.get("n_points"),
            "all_deltas_finite": output.get("all_deltas_finite"),
            "any_delta_nonzero": output.get("any_delta_nonzero"),
            "sample": output.get("sample_results", []),
        }
        result.summary = (
            f"Deltas calculados em {output.get('n_points')} pontos simulados. "
            f"Todos finitos: {output.get('all_deltas_finite')}. "
            f"Algum não-nulo: {output.get('any_delta_nonzero')}."
        )
        if not passed:
            if not output.get("all_deltas_finite"):
                result.impediments.append("Delta infinito ou NaN detectado — modelo instável")
            if not output.get("any_delta_nonzero"):
                result.impediments.append("Todos os deltas são zero — modelo possivelmente incorreto")

        # Try to generate stability plot
        try:
            fig_b64 = await self._plot_stability(output, rf_names)
            if fig_b64:
                result.figures.append(fig_b64)
        except Exception:
            pass

    async def _plot_stability(self, output: dict, rf_names: list) -> str | None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        samples = output.get("sample_results", [])
        valid = [s for s in samples if "deltas" in s]
        if not valid or not rf_names:
            return None

        fig, ax = plt.subplots(figsize=(8, 4))
        for fname in rf_names[:4]:
            vals = [s["deltas"].get(fname, np.nan) for s in valid]
            ax.plot(vals, label=fname, marker="o", markersize=3)
        ax.set_title("Delta por Fator de Risco (amostra de pontos)")
        ax.set_xlabel("Ponto simulado")
        ax.set_ylabel("Delta (∂PV/∂RF)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=100)
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
