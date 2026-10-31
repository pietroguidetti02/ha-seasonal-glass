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
# periodi che esistevano prima dell'opzione "noti" (0.1.x): chi aveva scelto gli attivi li ha visti tutti.
# Un periodo nuovo (non ancora visto nel menu Generale) parte attivo, anche se manca da "attivi".
PERIODI_V01 = ["autunno", "carnevale", "estate", "halloween", "inverno", "natale", "pasqua", "primavera"]
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


RE_RICORRENZA = re.compile(r"^(\d{2}-\d{2})\s+(.+?)(?:\s+(#[0-9a-fA-F]{6}))?$")
COLORE_RICORRENZA = "#e84393"


def leggi_ricorrenze(testo: str) -> list[dict]:
    """Una per riga: 'MM-GG Nome [emoji] [#colore]', es. '03-15 Compleanno Marta 🎂 #8e44ad'.
    -> periodi di un giorno, priorita' alta e senza giorni di pausa. Riga non valida -> ValueError(riga)."""
    out = []
    for riga in (testo or "").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#"):
            continue
        m = RE_RICORRENZA.match(riga)
        if not m:
            raise ValueError(riga)
        data, nome, colore = leggi_data(m[1]), m[2].split(), (m[3] or COLORE_RICORRENZA).lower()
        icona = nome.pop() if len(nome) > 1 and not any(c.isalnum() for c in nome[-1]) else "🎉"
        r, g, b = da_esadecimale(colore)
        out.append({
            "id": f"ricorrenza_{len(out) + 1}", "nome": " ".join(nome), "icona": icona, "priorita": 50,
            "senza_pausa": True, "ricorrenza": True, "date": {"da": data, "a": data},
            "colori": {m_: {"primary-color": colore} for m_ in MODI},
            "velatura": {"light": f"rgba({r},{g},{b},0.18)", "dark": f"rgba({r},{g},{b},0.24)"},
            "effetti": [{"tipo": "coriandoli", "quantita": 35}, {"tipo": "lucine", "stile": "bokeh", "quantita": 10}],
        })
    return out


def converti_opzioni(o: dict) -> dict:
    out: dict = {}
    if o.get("giorni_normale"):
        out["giorni_normale"] = int(o["giorni_normale"])
    if o.get("movimento") in MOVIMENTI:
        out["movimento"] = o["movimento"]
    periodi: dict = {}
    attivi, noti = o.get("attivi"), o.get("noti", PERIODI_V01)
    for p in PERIODI:
        pid, m = p["id"], {}
        if attivi is not None and pid not in attivi and pid in noti:
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
    try:
        if ricorrenze := leggi_ricorrenze(o.get("ricorrenze", "")):
            out["ricorrenze"] = ricorrenze
    except ValueError:
        pass  # gia' controllato nel modulo; un valore rovinato non deve bloccare il resto
    return out
