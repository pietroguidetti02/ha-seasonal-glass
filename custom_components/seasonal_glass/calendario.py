"""Calendario dei periodi lato server: stessa logica di src/core.js (vincitore, giorni "normale"),
con le impostazioni dell'integrazione. Gli override scritti nello YAML della card valgono solo nel frontend."""
from __future__ import annotations

from datetime import date, timedelta

from .const import PERIODI, converti_opzioni


def pasqua(y: int) -> date:  # algoritmo di Meeus, come in core.js
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    n = h + l - 7 * m + 114
    return date(y, n // 31, n % 31 + 1)


def _giorno(v, anno: int) -> date:
    if isinstance(v, dict):
        return pasqua(anno) + timedelta(days=v["pasqua"])
    mese, g = (int(x) for x in v.split("-"))
    try:
        return date(anno, mese, g)
    except ValueError:  # 02-29 negli anni non bisestili
        return date(anno, mese, 28)


def _attivo(p: dict, oggi: date) -> bool:
    d = p.get("date", {})
    da, a = ({"pasqua": d["pasqua"][0]}, {"pasqua": d["pasqua"][1]}) if "pasqua" in d else (d.get("da"), d.get("a"))
    if not da or not a:
        return False
    for anno in (oggi.year - 1, oggi.year):
        inizio, fine = _giorno(da, anno), _giorno(a, anno)
        if fine < inizio:
            fine = _giorno(a, anno + 1)
        if inizio <= oggi <= fine:
            return True
    return False


def periodi_effettivi(opzioni: dict) -> tuple[list[dict], int]:
    man = converti_opzioni(opzioni)
    out = []
    for p in PERIODI:
        m = man.get("periodi", {}).get(p["id"], {})
        if m.get("disattivo"):
            continue
        date_p = p.get("date", {})
        if "da" in m or "a" in m:
            base = ({"da": {"pasqua": date_p["pasqua"][0]}, "a": {"pasqua": date_p["pasqua"][1]}}
                    if "pasqua" in date_p else dict(date_p))
            base.update({k: m[k] for k in ("da", "a") if k in m})
            date_p = base
        out.append({**p, "date": date_p})
    return out, max(1, man.get("giorni_normale", 1))


def _vincitore(periodi: list[dict], giorno: date):
    attivi = [p for p in periodi if _attivo(p, giorno)]
    return max(attivi, key=lambda p: p.get("priorita", 0), default=None)


def periodo_del_giorno(opzioni: dict, oggi: date | None = None):
    periodi, n = periodi_effettivi(opzioni)
    oggi = oggi or date.today()
    p = _vincitore(periodi, oggi)
    if not p:
        return None
    d = oggi
    for _ in range(n):  # iniziato da meno di N giorni subito dopo un altro periodo -> normale
        d -= timedelta(days=1)
        prima = _vincitore(periodi, d)
        if prima is not p:
            return p if prima is None else None
    return p
