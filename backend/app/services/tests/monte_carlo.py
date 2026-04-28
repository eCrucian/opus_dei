"""Test 7: Monte Carlo convergence tests (only if model uses MC)."""
import io
import base64
import numpy as np
from app.models.validation import ModelUnderstanding, TestResult, TestStatus
from .base import BaseTest
from app.utils.code_executor import safe_exec


_MC_DRIVER = """
import numpy as np

{model_code}

def _run_mc_convergence(seed=42):
    rng = np.random.default_rng(seed)

    rf_base = {rf_base}

    path_counts = [100, 500, 1000, 2000, 5000, 10000]
    prices = []

    for n in path_counts:
        try:
            pricer = ModelPricer(n_simulations=n, seed=seed)
            p = pricer.price(rf_base)
            prices.append(float(p))
        except TypeError:
            try:
                pricer = ModelPricer()
                p = pricer.price(rf_base, n_simulations=n)
                prices.append(float(p))
            except Exception as e:
                prices.append(None)
        except Exception as e:
            prices.append(None)

    valid_prices = [p for p in prices if p is not None]
    converged = False
    if len(valid_prices) >= 3:
        last3 = valid_prices[-3:]
        rel_range = (max(last3) - min(last3)) / (abs(np.mean(last3)) + 1e-10)
        converged = rel_range < 0.01  # < 1% range in last 3

    return {{
        "path_counts": path_counts,
        "prices": prices,
        "converged": converged,
        "n_for_convergence": path_counts[len(valid_prices)-1] if valid_prices else None,
    }}

_result = _run_mc_convergence()
"""

_VOL_WINDOW_DRIVER = """
import numpy as np

{model_code}

def _run_vol_window(seed=42):
    rng = np.random.default_rng(seed)
    rf_base = {rf_base}

    # Simulate different vol calibration windows (as vol scaling)
    windows = [21, 42, 63, 126, 252]
    vol_base = rf_base.get({vol_factor!r}, 0.20)

    results = []
    for w in windows:
        # Scale vol roughly with sqrt(w/252)
        vol_scaled = vol_base * np.sqrt(w / 252.0)
        rf = dict(rf_base)
        if {vol_factor!r} in rf:
            rf[{vol_factor!r}] = vol_scaled
        try:
            pricer = ModelPricer()
            p = pricer.price(rf)
            results.append({{"window_days": w, "vol": vol_scaled, "price": float(p)}})
        except Exception as e:
            results.append({{"window_days": w, "error": str(e)}})

    return {{"vol_sensitivity": results}}

_result2 = _run_vol_window()
"""


class MonteCarloTest(BaseTest):
    test_id = "T07_monte_carlo"
    test_name = "Teste de Convergência Monte Carlo"

    async def _execute(
        self,
        result: TestResult,
        mu: ModelUnderstanding,
        replication_code: str,
    ) -> None:
        if not mu.has_monte_carlo:
            result.status = TestStatus.SKIPPED
            result.summary = "Modelo não utiliza simulação de Monte Carlo — teste não aplicável."
            return

        # Build a simple default rf dict
        rf_base = {}
        vol_factor = None
        for rf in mu.risk_factors:
            if rf.type == "rate":
                rf_base[rf.name] = 0.12
            elif rf.type == "vol":
                rf_base[rf.name] = 0.25
                vol_factor = rf.name
            elif rf.type == "spot":
                rf_base[rf.name] = 100.0
            else:
                rf_base[rf.name] = 1.0

        driver = _MC_DRIVER.format(model_code=replication_code, rf_base=repr(rf_base))
        output = safe_exec(driver, "_result")

        if output is None:
            result.status = TestStatus.WARNING
            result.summary = "Não foi possível executar o teste de convergência MC."
            return

        result.details["convergence"] = output
        converged = output.get("converged", False)
        result.status = TestStatus.PASSED if converged else TestStatus.WARNING

        try:
            fig_b64 = _plot_convergence(output)
            if fig_b64:
                result.figures.append(fig_b64)
        except Exception:
            pass

        # Vol window test if there's a vol factor
        if vol_factor:
            vol_driver = _VOL_WINDOW_DRIVER.format(
                model_code=replication_code,
                rf_base=repr(rf_base),
                vol_factor=vol_factor,
            )
            vol_output = safe_exec(vol_driver, "_result2")
            if vol_output:
                result.details["vol_window_sensitivity"] = vol_output
                try:
                    fig2 = _plot_vol_sensitivity(vol_output.get("vol_sensitivity", []))
                    if fig2:
                        result.figures.append(fig2)
                except Exception:
                    pass

        result.summary = (
            f"Convergência MC: {'SIM' if converged else 'NÃO'} — "
            f"testado com {output.get('path_counts')} simulações."
        )
        if not converged:
            result.recommendations.append(
                "Aumentar número de simulações ou reduzir variance via técnicas de redução de variância."
            )


def _plot_convergence(output: dict) -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    counts = output.get("path_counts", [])
    prices = output.get("prices", [])
    valid = [(c, p) for c, p in zip(counts, prices) if p is not None]
    if not valid:
        return None

    cs, ps = zip(*valid)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.semilogx(cs, ps, marker="o", linewidth=2, color="#1f77b4")
    ax.axhline(ps[-1], color="red", linestyle="--", alpha=0.5, label=f"Ref: {ps[-1]:.4f}")
    ax.set_title("Convergência MC — Preço vs Nº de Simulações")
    ax.set_xlabel("Nº de simulações (log)")
    ax.set_ylabel("Preço (PV)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _plot_vol_sensitivity(data: list) -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = [d for d in data if "price" in d]
    if not valid:
        return None

    windows = [d["window_days"] for d in valid]
    prices = [d["price"] for d in valid]
    vols = [d["vol"] for d in valid]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(windows, prices, marker="s", color="#2ca02c")
    ax1.set_title("Preço vs Janela de Calibração de Vol")
    ax1.set_xlabel("Janela (dias úteis)")
    ax1.set_ylabel("Preço (PV)")
    ax1.grid(True, alpha=0.3)

    ax2.plot(windows, vols, marker="^", color="#d62728")
    ax2.set_title("Volatilidade Calibrada vs Janela")
    ax2.set_xlabel("Janela (dias úteis)")
    ax2.set_ylabel("Vol anualizada")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()
