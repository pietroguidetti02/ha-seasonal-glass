"""Genera dist/seasonal-glass.js e anteprima.html scansionando periodi/<nome>/.

Uso:  python build.py            -> costruisce
      python build.py --ha       -> costruisce e copia anche in <config HA> (variabile HA_CONFIG, predefinito C:/DockerConfig/HA)
Aggiungere un periodo = creare una cartella in periodi/ con periodo.json e rilanciare.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent
PERIODI = RADICE / "periodi"
DIST = RADICE / "dist"
HA_CONFIG = Path(os.environ.get("HA_CONFIG", "C:/DockerConfig/HA"))  # cartella config di HA per --ha
HA_WWW = HA_CONFIG / "www" / "seasonal-glass"
IMG = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
POSIZIONI = {"alto-sinistra", "alto-destra", "basso-sinistra", "basso-destra", "alto-centro", "basso-centro"}


def immagine(cartella, base):
    """Primo file immagine con quel nome base (sfondo-light.png, sfondo.jpg, ...)."""
    for f in sorted(cartella.iterdir()):
        if f.suffix.lower() in IMG and f.stem.lower() == base:
            return f
    return None


def leggi_periodi():
    periodi, custom = [], {}
    for cartella in sorted(p for p in PERIODI.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        cfg_file = cartella / "periodo.json"
        if not cfg_file.exists():
            print(f"  ! {cartella.name}: manca periodo.json, salto")
            continue
        p = json.loads(cfg_file.read_text(encoding="utf-8"))
        pid = cartella.name
        p["id"] = pid
        p.setdefault("nome", pid.capitalize())
        dest = DIST / "periodi" / pid
        if dest.exists():
            shutil.rmtree(dest)

        def copia(f):
            rel = f.relative_to(cartella)
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest / rel)
            return f"periodi/{pid}/{rel.as_posix()}"

        # sfondo: sfondo-light/-dark, oppure sfondo unico per entrambi
        comune = immagine(cartella, "sfondo")
        sfondo = {}
        for modo in ("light", "dark"):
            f = immagine(cartella, f"sfondo-{modo}") or comune
            if f:
                sfondo[modo] = copia(f)
        if sfondo:
            p["sfondo"] = sfondo

        # decorazioni: il nome del file e' la posizione (alto-sinistra.png, alto-sinistra.dark.png)
        deco_dir = cartella / "decorazioni"
        if deco_dir.is_dir():
            decos = {}
            for f in sorted(deco_dir.iterdir()):
                if f.suffix.lower() not in IMG:
                    continue
                parti = f.stem.lower().split(".")
                pos, modo = parti[0], (parti[1] if len(parti) > 1 else "light")
                if pos not in POSIZIONI:
                    print(f"  ! {pid}: decorazione '{f.name}' ignorata (posizioni: {', '.join(sorted(POSIZIONI))})")
                    continue
                decos.setdefault(pos, {"pos": pos})[modo] = copia(f)
            # opzioni extra per posizione da periodo.json: "decorazioni_opzioni": {"alto-destra": {"max": "30vmin"}}
            for pos, opz in p.pop("decorazioni_opzioni", {}).items():
                if pos in decos:
                    decos[pos].update(opz)
            p["decorazioni"] = list(decos.values())

        js = cartella / "effetto.js"
        if js.exists():
            codice = re.sub(r"\bexport\s+default\b", "__m.default =", js.read_text(encoding="utf-8"), count=1)
            custom[pid] = f"(() => {{ const __m = {{}};\n{codice}\nreturn __m.default; }})()"

        periodi.append(p)
        print(f"  + {pid:12} prio {p.get('priorita', 0):>3}  date {json.dumps(p.get('date'))}"
              f"  effetti {[e['tipo'] for e in p.get('effetti', [])]}"
              f"{'  sfondo' if sfondo else ''}{'  +effetto.js' if pid in custom else ''}")
    return periodi, custom


def impostazioni():
    f = RADICE / "impostazioni.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def bundle(periodi, custom, base_expr):
    core = (RADICE / "src" / "core.js").read_text(encoding="utf-8")
    custom_js = ",\n".join(f"  {json.dumps(k)}: {v}" for k, v in custom.items())
    return (
        "/* Seasonal Glass - FILE GENERATO da build.py, non modificare: modificare src/ e periodi/ */\n"
        f"const BASE = {base_expr};\n"
        f"const IMPOSTAZIONI = {json.dumps(impostazioni())};\n"
        f"const PERIODI = {json.dumps(periodi, ensure_ascii=False, indent=1)};\n"
        f"const CUSTOM = {{\n{custom_js}\n}};\n\n{core}"
    )


ANTEPRIMA = """<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anteprima addobbi</title>
<style>
  :root{--primary-color:#6a74d3;--accent-color:#8a6ad3;--primary-background-color:#eef1f6;--primary-text-color:#131536;--card:rgba(255,255,255,.55)}
  html.scuro{--primary-background-color:#0b1018;--primary-text-color:#f0f3ff;--card:rgba(20,28,40,.55)}
  body{margin:0;font:15px system-ui,sans-serif;color:var(--primary-text-color);min-height:100vh;
    background:var(--lovelace-background, linear-gradient(135deg,var(--primary-background-color),#c9d3e6))}
  html.scuro body{background:var(--lovelace-background, linear-gradient(135deg,#0b1018,#1c2536))}
  header{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:14px 16px;position:relative;z-index:5}
  header select,header button{font:inherit;padding:6px 10px;border-radius:10px;border:1px solid #8884;background:var(--card);color:inherit}
  main{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px;padding:16px}
  .card{background:var(--card);backdrop-filter:blur(14px);border:1px solid #fff3;border-radius:20px;padding:16px}
  .card h3{margin:0 0 8px;font-size:15px}
  .btn{display:inline-block;padding:8px 14px;border-radius:12px;background:var(--primary-color);color:#fff;border:0;font:inherit;cursor:pointer}
  .tog{width:42px;height:24px;border-radius:12px;background:var(--primary-color);display:inline-block;vertical-align:middle;position:relative}
  .tog:after{content:"";position:absolute;right:3px;top:3px;width:18px;height:18px;border-radius:50%;background:#fff}
  .acc{color:var(--accent-color);font-weight:600}
</style></head><body>
<header><b>Anteprima addobbi</b>
  <select id="p"><option value="">(data di oggi)</option>__OPZIONI__<option value="off">Normale (nessun addobbo)</option></select>
  <button id="m">Passa a dark</button><span id="info"></span></header>
<main>
  <div class="card"><h3>Luce soggiorno</h3><span class="tog"></span> Accesa</div>
  <div class="card"><h3>Termostato</h3><span class="acc">21,5 °C</span> - riscaldamento</div>
  <div class="card"><h3>Cancello</h3><button class="btn" onclick="this.textContent='Cliccato!'">Apri</button></div>
  <div class="card"><h3>Meteo</h3>Nuvoloso, 12 °C</div>
  <div class="card"><h3>Allarme</h3>Disinserito</div>
  <div class="card"><h3>Prova click</h3><button class="btn" onclick="this.textContent=+this.textContent+1||1">0</button> i bottoni devono funzionare anche sotto gli addobbi</div>
  <div id="cal" style="grid-column:1/-1;max-width:520px"></div>
</main>
<script>
  const q = new URLSearchParams(location.search), sel = document.getElementById('p'), m = document.getElementById('m');
  sel.value = q.get('addobbi') || '';
  if (q.get('modo') === 'dark') document.documentElement.classList.add('scuro');
  const vai = () => { const u = new URLSearchParams(); if (sel.value) u.set('addobbi', sel.value);
    if (document.documentElement.classList.contains('scuro')) u.set('modo', 'dark'); location.search = u; };
  sel.onchange = vai;
  m.textContent = document.documentElement.classList.contains('scuro') ? 'Passa a light' : 'Passa a dark';
  m.onclick = () => { document.documentElement.classList.toggle('scuro'); vai(); };
</script>
<script type="module">
__BUNDLE__
document.getElementById('info').textContent = 'periodi: ' + PERIODI.map(p => p.nome).join(', ');
const card = document.createElement('seasonal-glass-card');
const man = new URLSearchParams(location.search).get('manuale');
card.setConfig(man ? JSON.parse(man) : { mostra: 12 });
document.getElementById('cal').appendChild(card);
</script>
</body></html>
"""


def main():
    print("Periodi trovati:")
    DIST.mkdir(exist_ok=True)
    periodi, custom = leggi_periodi()
    (DIST / "seasonal-glass.js").write_text(
        bundle(periodi, custom, "new URL('.', import.meta.url).href"), encoding="utf-8")
    opzioni = "".join(f'<option value="{p["id"]}">{p["nome"]}</option>' for p in periodi)
    html = ANTEPRIMA.replace("__OPZIONI__", opzioni).replace("__BUNDLE__", bundle(periodi, custom, "'dist/'"))
    (RADICE / "anteprima.html").write_text(html, encoding="utf-8")
    integrazione(periodi)
    print(f"OK -> dist/seasonal-glass.js ({len(periodi)} periodi), anteprima.html, custom_components/{DOMINIO}")
    if "--ha" in sys.argv:  # installa l'integrazione nel Home Assistant di casa (poi serve un riavvio)
        if HA_CC.exists():
            shutil.rmtree(HA_CC)
        shutil.copytree(CC, HA_CC, ignore=shutil.ignore_patterns("__pycache__"))
        print(f"Copiato in {HA_CC} -> riavviare HA")


DOMINIO = "seasonal_glass"
CC = RADICE / "custom_components" / DOMINIO
HA_CC = HA_CONFIG / "custom_components" / DOMINIO


def integrazione(periodi):
    """Aggiorna i file generati dell'integrazione: www/ (plugin), periodi.json, traduzioni dei menu."""
    www = CC / "www"
    if www.exists():
        shutil.rmtree(www)
    shutil.copytree(DIST, www)
    elenco = [{k: p[k] for k in ("id", "nome", "icona", "priorita", "senza_pausa", "date", "colori", "velatura") if k in p} for p in periodi]
    (CC / "periodi.json").write_text(json.dumps(elenco, ensure_ascii=False, indent=1), encoding="utf-8")

    testi = {
        "it": {
            "titolo": "Seasonal Glass", "aggiungi": "Aggiunge gli addobbi stagionali automatici alle dashboard.",
            "solo_una": "Seasonal Glass e' gia' configurato.",
            "menu": "Cosa vuoi modificare? Ricordati di premere **Salva** alla fine.",
            "generale": "Generale", "date": "Date dei periodi", "salva": "Salva e chiudi",
            "movimento": "Animazioni", "giorni_normale": "Giorni normali tra due addobbi", "attivi": "Periodi attivi", "notifica": "Notifica quando cambia l'addobbo",
            "desc_date": "Lascia vuoto per il calendario automatico. Formato: `MM-GG` (es. `10-20`) oppure "
                         "`P-10` / `P+3` = giorni da Pasqua. Se un periodo segue subito un altro, compare dopo "
                         "i giorni normali.\n\nDate automatiche:\n{automatiche}",
            "da": "inizio", "a": "fine", "errore": "Data non valida: usa MM-GG oppure P-10 / P+3",
            "sempre": "Sempre", "auto": "Segui il dispositivo (riduci movimento)", "mai": "Mai (immagine ferma)",
            "colori": "Colori", "scegli_periodo": "Periodo", "desc_colori": "Scegli il periodo di cui cambiare i colori (✎ = modificato).",
            "desc_colori_periodo": "{periodo}. **Colore principale**: pulsanti, interruttori, accenti. **Velatura**: tinta "
                                   "semitrasparente stesa sopra lo sfondo; se scegli solo l'intensita' usa il colore principale. "
                                   "Intensita' 0 = nessuna velatura. Lascia vuoto per i valori predefiniti.",
            "principale_light": "Colore principale (tema chiaro)", "principale_dark": "Colore principale (tema scuro)",
            "velatura_light": "Velatura (tema chiaro)", "velatura_dark": "Velatura (tema scuro)",
            "intensita": "Intensita' velatura", "ripristina": "Ripristina i colori predefiniti",
            "ricorrenze": "Ricorrenze", "desc_ricorrenze": "Compleanni, anniversari e altre giornate tue: una per riga, "
                          "`MM-GG Nome emoji #colore` (emoji e colore facoltativi), es. `03-15 Compleanno Marta 🎂 #8e44ad`. "
                          "Quel giorno le dashboard si colorano e compaiono i coriandoli.",
            "elenco": "Elenco", "errore_ricorrenza": "Riga non valida: {riga}",
            "srv_anteprima": "Anteprima periodo", "srv_anteprima_desc": "Mostra un periodo su tutti i dispositivi per qualche minuto, poi torna al calendario automatico.",
            "srv_periodo": "Periodo", "srv_periodo_desc": "Id del periodo (es. natale, halloween, capodanno, ricorrenza_1) oppure normale.",
            "srv_minuti": "Minuti", "srv_minuti_desc": "Durata dell'anteprima. 0 = annulla subito.",
        },
        "en": {
            "titolo": "Seasonal Glass", "aggiungi": "Adds automatic seasonal decorations to your dashboards.",
            "solo_una": "Seasonal Glass is already configured.",
            "menu": "What do you want to change? Remember to press **Save** at the end.",
            "generale": "General", "date": "Period dates", "salva": "Save and close",
            "movimento": "Animations", "giorni_normale": "Normal days between two decorations", "attivi": "Active periods", "notifica": "Notify when the decoration changes",
            "desc_date": "Leave empty for the automatic calendar. Format: `MM-DD` (e.g. `10-20`) or "
                         "`P-10` / `P+3` = days from Easter. If a period directly follows another, it appears "
                         "after the normal days.\n\nAutomatic dates:\n{automatiche}",
            "da": "start", "a": "end", "errore": "Invalid date: use MM-DD or P-10 / P+3",
            "sempre": "Always", "auto": "Follow the device (reduce motion)", "mai": "Never (still image)",
            "colori": "Colors", "scegli_periodo": "Period", "desc_colori": "Pick the period whose colors you want to change (✎ = changed).",
            "desc_colori_periodo": "{periodo}. **Main color**: buttons, switches, accents. **Tint**: semi-transparent color "
                                   "laid over the background; with only an intensity it uses the main color. "
                                   "Intensity 0 = no tint. Leave empty for the defaults.",
            "principale_light": "Main color (light theme)", "principale_dark": "Main color (dark theme)",
            "velatura_light": "Tint (light theme)", "velatura_dark": "Tint (dark theme)",
            "intensita": "Tint intensity", "ripristina": "Restore default colors",
            "ricorrenze": "Personal days", "desc_ricorrenze": "Birthdays, anniversaries and other days of yours: one per line, "
                          "`MM-DD Name emoji #color` (emoji and color optional), e.g. `03-15 Marta's birthday 🎂 #8e44ad`. "
                          "On that day the dashboards change color and confetti appears.",
            "elenco": "List", "errore_ricorrenza": "Invalid line: {riga}",
            "srv_anteprima": "Preview period", "srv_anteprima_desc": "Shows a period on every device for a few minutes, then goes back to the automatic calendar.",
            "srv_periodo": "Period", "srv_periodo_desc": "Period id (e.g. natale, halloween, capodanno, ricorrenza_1) or normale.",
            "srv_minuti": "Minutes", "srv_minuti_desc": "Preview length. 0 = cancel now.",
        },
    }
    for lingua, t in testi.items():
        campi_date = {f"{p['id']}_{e}": f"{p.get('icona', '')} {p['nome']} - {t[e]}".strip()
                      for p in periodi for e in ("da", "a")}
        tr = {
            "config": {
                "step": {"user": {"title": t["titolo"], "description": t["aggiungi"]}},
                "abort": {"single_instance_allowed": t["solo_una"]},
            },
            "options": {
                "step": {
                    "init": {"title": t["titolo"], "description": t["menu"],
                             "menu_options": {"generale": t["generale"], "date": t["date"], "colori": t["colori"],
                                              "ricorrenze": t["ricorrenze"], "salva": t["salva"]}},
                    "generale": {"title": t["generale"], "data": {
                        "movimento": t["movimento"], "giorni_normale": t["giorni_normale"], "attivi": t["attivi"], "notifica": t["notifica"]}},
                    "date": {"title": t["date"], "description": t["desc_date"], "data": campi_date},
                    "colori": {"title": t["colori"], "description": t["desc_colori"],
                               "data": {"periodo": t["scegli_periodo"]}},
                    "colori_periodo": {"title": t["colori"], "description": t["desc_colori_periodo"],
                                       "data": {k: t[k] for k in ("principale_light", "principale_dark", "velatura_light",
                                                                  "velatura_dark", "intensita", "ripristina")}},
                    "ricorrenze": {"title": t["ricorrenze"], "description": t["desc_ricorrenze"],
                                   "data": {"ricorrenze": t["elenco"]}},
                },
                "error": {"data_non_valida": t["errore"], "ricorrenza_non_valida": t["errore_ricorrenza"]},
            },
            "services": {"anteprima": {"name": t["srv_anteprima"], "description": t["srv_anteprima_desc"], "fields": {
                "periodo": {"name": t["srv_periodo"], "description": t["srv_periodo_desc"]},
                "minuti": {"name": t["srv_minuti"], "description": t["srv_minuti_desc"]}}}},
            "selector": {"movimento": {"options": {k: t[k] for k in ("sempre", "auto", "mai")}}},
        }
        cartella = CC / "translations"
        cartella.mkdir(exist_ok=True)
        (cartella / f"{lingua}.json").write_text(json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")
        if lingua == "en":
            (CC / "strings.json").write_text(json.dumps(tr, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
