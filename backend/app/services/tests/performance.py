"""Test 6: Performance/Curvature — second derivatives (gammas) and Taylor expansion relevance."""
import io
import base64
import numpy as np
from app.models.validation import ModelUnderstanding, TestResult, TestStatus
from .base import BaseTest
from app.utils.code_executor import safe_exec


_DRIVER_TEMPLATE = """
import numpy as np

{model_code}

def _run_curvature(n_points=100, bump=1e-3, seed=42):
    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    risk_factor_names = {risk_factors}

    results = []
    for _ in range(n_points):
        rf = {{}}
        for name in risk_factor_names:
            if "rate" in name.lower() or "taxa" in name.lower():
                rf[name] = rng.uniform(0.05, 0.20)
            elif "vol" in name.lower():
                rf[name] = rng.uniform(0.10, 0.60)
            elif "spot" in name.lower() or "price" in name.lower():
                rf[name] = rng.uniform(80, 150)
            elif "fx" in name.lower() or "usd" in name.lower():
                rf[name] = rng.uniform(4.5, 6.5)
            else:
                rf[name] = rng.uniform(0.8, 1.2)

        try:
            pricer = ModelPricer()
            pv0 = pricer.price(rf)

            gammas = {{}}
            for fname in risk_factor_names:
                h = rf[fname] * bump
                rf_up = dict(rf); rf_up[fname] += h
                rf_dn = dict(rf); rf_dn[fname] -= h
                g = (pricer.price(rf_up) - 2*pv0 + pricer.price(rf_dn)) / (h**2)
                gammas[fname] = g

            # Cross gammas (first pair of risk factors)
            cross_gammas = {{}}
            for i, f1 in enumerate(risk_factor_names[:3]):
                for f2 in risk_factor_names[i+1:4]:
                    h1 = rf[f1] * bump
                    h2 = rf[f2] * bump
                    rfpp = dict(rf); rfpp[f1] += h1; rfpp[f2] += h2
                    rfpm = dict(rf); rfpm[f1] += h1; rfpm[f2] -= h2
                    rfmp = dict(rf); rfmp[f1] -= h1; rfmp[f2] += h2
                    rfmm = dict(rf); rfmm[f1] -= h1; rfmm[f2] -= h2
                    cg = (pricer.price(rfpp) - pricer.price(rfpm) -
                          pricer.price(rfmp) + pricer.price(rfmm)) / (4*h1*h2)
                    cross_gammas[f"{{f1}}_x_{{f2}}"] = cg

            results.append({{
                "pv": pv0, "gammas": gammas,
                "cross_gammas": cross_gammas, "rf": rf
            }})
        except Exception as e:
            results.append({{"error": str(e)}})

    valid = [r for r in results if "gammas" in r]
    gamma_means = {{}}
    gamma_rel = {{}}
    for fname in risk_factor_names:
        vals = [r["gammas"].get(fname, np.nan) for r in valid]
        pv_vals = [r["pv"] for r in valid]
        g_mean = float(np.nanmean(vals))
        pv_mean = float(np.nanmean(pv_vals))
        gamma_means[fname] = g_mean
        gamma_rel[fname] = abs(0.5 * g_mean * (rf[fname]*0.01)**2 / pv_mean) if pv_mean != 0 else 0

    return {{
        "n_valid": len(valid),
        "gamma_means": gamma_means,
        "gamma_relative_impact_1pct": gamma_rel,
        "cross_gammas_sample": valid[0].get("cross_gammas", {{}}) if valid else {{}},
        "sample_results": results[:5],
    }}

_result = _run_curvature()
"""


class PerformanceTest(BaseTest):
    test_id = "T06_performance"
    test_name = "Teste de Performance / Curvatura (Derivadas Segundas)"

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
            result.summary = "Não foi possível executar o código para o teste de curvatura."
            return

        gamma_rel = output.get("gamma_relative_impact_1pct", {})
        significant = {k: v for k, v in gamma_rel.items() if abs(v) > 0.001}

        result.status = TestStatus.PASSED
        result.details = {
            "gamma_means": output.get("gamma_means", {}),
            "gamma_impact_1pct": gamma_rel,
            "significant_gammas": significant,
            "cross_gammas": output.get("cross_gammas_sample", {}),
            "n_valid": output.get("n_valid"),
        }
        result.summary = (
            f"Gammas calculados. Fatores com curvatura relevante (>0.1% impacto a 1% choque): "
            f"{list(significant.keys()) or 'nenhum'}."
        )
        if significant:
            result.recommendations.append(
                "Modelo apresenta curvatura relevante — considere estratégia de hedge de convexidade."
            )

        try:
            fig_b64 = _plot_gammas(gamma_rel)
            if fig_b64:
                result.figures.append(fig_b64)
        except Exception:
            pass


def _plot_gammas(gamma_rel: dict) -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not gamma_rel:
        return None
    names = list(gamma_rel.keys())
    vals = [abs(v) * 100 for v in gamma_rel.values()]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.bar(names, vals, color=["#d62728" if v > 0.1 else "#1f77b4" for v in vals])
    ax.axhline(0.1, color="red", linestyle="--", label="Threshold 0.1%")
    ax.set_title("Impacto Relativo do Gamma por Fator de Risco (choque 1%)")
    ax.set_ylabel("Impacto % do PV")
    ax.set_xlabel("Fator de Risco")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
