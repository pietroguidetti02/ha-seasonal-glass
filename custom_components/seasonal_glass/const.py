"""Costanti e conversione impostazioni -> formato del plugin JS."""
from __future__ import annotations

import json
import re
from pathlib import Path

DOMAIN = "seasonal_glass"
URL_BASE = "/seasonal_glass"

# generato da build.py: [{id, nome, icona, date}, ...]
PERIODI = json.loads((Path(__file__).parent / "periodi.json").read_text(encoding="utf-8"))

MOVIMENTI = ["sempre", "auto", "mai"]
RE_DATA = re.compile(r"^(\d{2})-(\d{2})$")
RE_PASQUA = re.compile(r"^[Pp]\s*([+-]\s*\d+)?$")


def leggi_data(testo: str):
    """'10-20' -> '10-20'; 'P-10' / 'P+3' / 'P' -> {'pasqua': n}; vuoto -> None; non valido -> ValueError."""
    testo = (testo or "").strip()
    if not testo:
        return None
    if m := RE_DATA.match(testo):
        mese, giorno = int(m[1]), int(m[2])
        if 1 <= mese <= 12 and 1 <= giorno <= 31:
            return testo
        raise ValueError(testo)
    if m := RE_PASQUA.match(testo):
        return {"pasqua": int((m[1] or "0").replace(" ", ""))}
    raise ValueError(testo)


def scrivi_data(valore) -> str:
    """Inverso di leggi_data, per mostrare le date automatiche nel modulo."""
    if isinstance(valore, dict):
        n = valore["pasqua"]
        return "P" if n == 0 else f"P{n:+d}"
    return valore or ""


def date_automatiche(p: dict) -> tuple[str, str]:
    d = p.get("date", {})
    if "pasqua" in d:
        return scrivi_data({"pasqua": d["pasqua"][0]}), scrivi_data({"pasqua": d["pasqua"][1]})
    return scrivi_data(d.get("da")), scrivi_data(d.get("a"))


MODI = ("light", "dark")


def esadecimale(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(c) for c in rgb)


def da_esadecimale(testo: str) -> list[int] | None:
    """'#e8730c' -> [232, 115, 12]; altro (gradienti, nomi) -> None."""
    testo = (testo or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", testo):
        return [int(testo[i:i + 2], 16) for i in (1, 3, 5)]
    return None


def colore_predefinito(p: dict, modo: str) -> list[int] | None:
    return da_esadecimale(p.get("colori", {}).get(modo, {}).get("primary-color", ""))


def colori_manuali(p: dict, o: dict) -> dict:
    """Opzioni '<id>_principale_<modo>', '<id>_velatura_<modo>' ([r,g,b]) e '<id>_intensita' (0-60 %)
    -> {'colori': {modo: {...}}, 'velatura': {modo: 'rgba(...)'}} per il plugin."""
    pid, out = p["id"], {}
    colori, velatura = {}, {}
    intensita = o.get(f"{pid}_intensita")
    for modo in MODI:
        principale = o.get(f"{pid}_principale_{modo}")
        if principale:
            colori[modo] = {"primary-color": esadecimale(principale)}
        tinta = o.get(f"{pid}_velatura_{modo}")
        if tinta is None and intensita is None:
            continue  # velatura predefinita del periodo
        if intensita is not None and float(intensita) <= 0:
            velatura[modo] = "transparent"
            continue
        rgb = tinta or principale or colore_predefinito(p, modo)
        if not rgb:
            continue
        a = (float(intensita) if intensita is not None else 30) / 100
        r, g, b = (int(c) for c in rgb)
        velatura[modo] = f"rgba({r},{g},{b},{a:.2f})"
    if colori:
        out["colori"] = colori
    if velatura:
        out["velatura"] = velatura
    return out


def converti_opzioni(o: dict) -> dict:
    out: dict = {}
    if o.get("giorni_normale"):
        out["giorni_normale"] = int(o["giorni_normale"])
    if o.get("movimento") in MOVIMENTI:
        out["movimento"] = o["movimento"]
    periodi: dict = {}
    attivi = o.get("attivi")
    for p in PERIODI:
        pid, m = p["id"], {}
        if attivi is not None and pid not in attivi:
            m["disattivo"] = True
        for estremo in ("da", "a"):
            try:
                v = leggi_data(o.get(f"{pid}_{estremo}", ""))
            except ValueError:
                v = None
            if v is not None:
                m[estremo] = v
        m.update(colori_manuali(p, o))
        if m:
            periodi[pid] = m
    if periodi:
        out["periodi"] = periodi
    return out
