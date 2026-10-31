"""Il calendario Python (sensore, calendario di HA) deve dare gli stessi periodi del plugin JS, giorno per giorno.
Uso: python tests/test_calendario.py   (serve node; non serve Home Assistant)"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import types
from datetime import date, timedelta
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CC = RADICE / "custom_components" / "seasonal_glass"
DA, A = 2025, 2040


def carica():
    """Importa const.py e calendario.py come pacchetto, senza l'__init__ (che richiede Home Assistant)."""
    pacchetto = types.ModuleType("sg")
    pacchetto.__path__ = [str(CC)]
    sys.modules["sg"] = pacchetto
    for nome in ("const", "calendario"):
        spec = importlib.util.spec_from_file_location(f"sg.{nome}", CC / f"{nome}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"sg.{nome}"] = mod
        spec.loader.exec_module(mod)
    return sys.modules["sg.const"], sys.modules["sg.calendario"]


def confronta(opzioni: dict) -> int:
    const, cal = carica()
    periodi, n = cal.periodi_effettivi(opzioni)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(periodi, f)
    js = json.loads(subprocess.run(["node", str(RADICE / "tests" / "parita.mjs"), f.name, str(n), str(DA), str(A)],
                                   capture_output=True, text=True, check=True).stdout)
    diversi, d = [], date(DA, 1, 1)
    while d.year <= A:
        p = cal.periodo_del_giorno(opzioni, d)
        py = p["id"] if p else "normale"
        if js[d.isoformat()] != py:
            diversi.append(f"{d}: js={js[d.isoformat()]} py={py}")
        d += timedelta(days=1)
    print(f"{json.dumps(opzioni)[:70]:72} {'OK' if not diversi else f'{len(diversi)} DIFFERENZE'}")
    for r in diversi[:10]:
        print("   ", r)
    return len(diversi)


if __name__ == "__main__":
    casi = [
        {},
        {"giorni_normale": 3},
        {"natale_da": "12-08", "halloween_a": "11-05", "attivi": ["natale", "halloween", "inverno", "capodanno", "pasqua"]},
        {"ricorrenze": "02-29 Bisestile 🎈\n10-31 Festa #123456\n12-25 Compleanno"},
    ]
    sys.exit(1 if sum(confronta(c) for c in casi) else 0)
