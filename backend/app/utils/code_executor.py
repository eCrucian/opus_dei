"""Sandboxed Python code execution.

Uses a subprocess with a timeout so that runaway generated code
cannot hang the server. Returns the value of `result_var` after execution.
"""
import subprocess
import sys
import json
import tempfile
import textwrap
import os
from typing import Any, Optional


def safe_exec(code: str, result_var: str, timeout: int = 60) -> Optional[Any]:
    """
    Execute `code` in a subprocess and return the JSON-serialised value of `result_var`.
    Returns None on any error or timeout.
    """
    wrapper = textwrap.dedent(f"""
import json, sys, numpy as np

def _np_convert(obj):
    if isinstance(obj, (np.integer,)): return int(obj)
    if isinstance(obj, (np.floating,)): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    raise TypeError(f"{{type(obj)}} not serializable")

try:
{textwrap.indent(code, '    ')}
    print("__RESULT__" + json.dumps({result_var}, default=_np_convert))
except Exception as _e:
    print("__ERROR__" + str(_e), file=sys.stderr)
""")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(wrapper)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "MPLBACKEND": "Agg"},
        )
        for line in proc.stdout.splitlines():
            if line.startswith("__RESULT__"):
                return json.loads(line[len("__RESULT__"):])
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
