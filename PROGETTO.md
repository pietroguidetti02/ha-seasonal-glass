# Seasonal Glass – addobbi stagionali per le dashboard di Home Assistant

Contesto per chi (persona o agente AI) lavora su questo progetto. Lingua di lavoro: italiano.

## Obiettivo
Un **plugin frontend** per Home Assistant (risorsa Lovelace JS, da distribuire poi via HACS)
che "addobba" da solo la dashboard secondo il periodo dell'anno:
- cambia la **palette** (colore primario/accento e qualsiasi variabile CSS del tema)
- mette uno **sfondo** del periodo (PNG/JPG forniti dall'utente)
- aggiunge **decorazioni** (es. ragnatele negli angoli ad Halloween)
- aggiunge **effetti animati** (es. neve che cade e lucine che brillano a Natale)

Vincoli fondamentali:
1. **Non deve mai intralciare l'uso della dashboard**: tutti i livelli decorativi hanno
   `pointer-events: none`, opacita' contenuta, nessun elemento sopra i controlli che catturi tocchi.
2. **Versione light e dark di tutto**: il ciclo esistente (automazione HA col sole che alterna
   i temi *Frosted Glass Light* di giorno e *Frosted Glass Dark* di notte) deve continuare a funzionare.
   Il plugin NON cambia tema: si appoggia al tema attivo e rileva se e' chiaro o scuro.
3. **Periodi aggiungibili senza toccare il codice**: ogni periodo e' una cartella in `periodi/`.
   Si aggiunge una cartella, si lancia `python build.py`, e il periodo esiste.
4. Leggero: deve girare anche su Chromecast/tablet (pochi elementi, pausa a scheda nascosta,
   rispetto di `prefers-reduced-motion`).

## Struttura
```
seasonal-glass/
  PROGETTO.md            questo file
  build.py               scansiona periodi/ e genera dist/
  impostazioni.json      opzioni globali (giorni_normale)
  README.md              documentazione pubblica (inglese, GitHub/HACS)
  src/core.js            motore del plugin (rilevamento periodo, light/dark, effetti)
  periodi/<nome>/        un periodo = una cartella
    periodo.json         date, priorita', colori light/dark, effetti
    sfondo.png|jpg|webp           (opzionale) sfondo per entrambi i modi
    sfondo-light.* / sfondo-dark.* (opzionale) sfondi separati
    decorazioni/         (opzionale) immagini posizionate dal NOME del file:
                         alto-sinistra, alto-destra, basso-sinistra, basso-destra,
                         alto-centro, basso-centro  (+ variante  <pos>.dark.png  per il buio)
    effetto.js           (opzionale) effetto personalizzato, vedi sotto
  dist/                  GENERATO: seasonal-glass.js + immagini copiate (da caricare in HA)
  anteprima.html         GENERATO: prova nel browser senza Home Assistant
```

## Il ciclo dell'anno (deciso con l'utente)
Concetto: le **4 stagioni** sono lo sfondo e coprono tutto l'anno, iniziando **10 giorni prima**
di equinozio/solstizio. Le **feste** (priorita' piu' alta) ci si appoggiano sopra e compaiono
**almeno 10 giorni prima** del giorno di festa (Halloween, Natale, Pasqua).
Tra due addobbi c'e' SEMPRE un ritorno al **normale** (nessun addobbo, tema com'e'): lo garantisce il
motore col **giorno cuscinetto**: quando si passerebbe direttamente da un periodo a un altro, i primi
`giorni_normale` giorni del nuovo sono normali (`impostazioni.json`, predefinito 1, minimo 1).
Il normale dura di piu' se nel calendario restano giorni non coperti da alcun periodo.
Per questo le date di inizio delle feste in periodo.json sono anticipate di 1 giorno (quel giorno e' cuscinetto):
se si aumenta `giorni_normale`, anticiparle di conseguenza per mantenere i 10 giorni.

| Periodo | Date in periodo.json | Visibile (con 1 giorno normale) | Prio | Effetti |
|---|---|---|---|---|
| inverno | 11/12 - 09/03 | dopo Natale fino al 9/3 (interrotto da carnevale) | 10 | neve leggera |
| carnevale | Pasqua-53 - Pasqua-47 | giovedi' grasso - martedi' grasso | 25 | coriandoli |
| primavera | 10/03 - 10/06 | dall'11/3 (interrotta da Pasqua) | 10 | germogli verdi trasparenti negli angoli bassi, petali |
| pasqua | Pasqua-11 - Pasqua+1 | da Pasqua-10 a Pasquetta | 25 | uova decorate negli angoli bassi (dondolano), petali pastello |
| estate | 11/06 - 11/09 | dal 12/6 | 10 | lucciole (solo dark) |
| autunno | 12/09 - 10/12 | dal 13/9 (interrotto da Halloween e Natale) | 10 | foglie marroni trasparenti negli angoli, foglie che cadono |
| halloween | 20/10 - 02/11 | 21/10 - 02/11 | 20 | ragnatele + ragno, pipistrelli |
| natale | 30/11 - 06/01 | 01/12 - 06/01 | 30 | lucine a festoni, lucine bokeh, neve |

Esempio 2027 (verificato): natale 1/1 > normale 7/1 > inverno 8/1 > normale 3/2 > carnevale 4/2 >
normale 10/2 > inverno 11/2 > normale 10/3 > primavera 11/3 > normale 17/3 > pasqua 18/3 > normale 30/3 >
primavera 31/3 > normale 11/6 > estate 12/6 > normale 12/9 > autunno 13/9 > normale 20/10 >
halloween 21/10 > normale 3/11 > autunno 4/11 > normale 30/11 > natale 1/12.

Le date si ricalcolano da sole ogni anno (Pasqua con l'algoritmo di Meeus; carnevale e pasqua la seguono).
Verificato 2026-2035: mai due addobbi attaccati; Halloween, Natale e Pasqua sempre >= 10 giorni prima.
Se si cambiano le date, rilanciare il controllo (vedi "Verifiche").
Schermi: tutte le misure in `vmin` (lato corto) -> proporzionato in verticale e orizzontale (provato 500x1000 e 1100x650).

## periodo.json
```json
{
  "nome": "Halloween",
  "priorita": 20,
  "date": { "da": "10-20", "a": "11-02" },
  "colori": {
    "light": { "primary-color": "#e8730c", "accent-color": "#7b3fa0" },
    "dark":  { "primary-color": "#ff8c1a", "accent-color": "#a66bd3" }
  },
  "sfondo_opacita": 1,
  "effetti": [ { "tipo": "ragnatele" }, { "tipo": "pipistrelli", "quantita": 4 } ]
}
```
- `date`: `"MM-GG"`; se la fine viene prima dell'inizio attraversa il capodanno (Natale `12-01` -> `01-06`).
  Ogni estremo puo' anche essere `{ "pasqua": n }` (n giorni da Pasqua, negativo = prima), mischiabile
  con le date fisse: primavera = `{ "da": { "pasqua": 3 }, "a": "06-10" }`.
  Scorciatoia: `{ "pasqua": [-7, 1] }` = da Pasqua-7 a Pasqua+1.
- Periodi sovrapposti (non dovrebbero esserci): vince la `priorita` piu' alta.
- `colori`: chiavi = nomi di variabili CSS del tema SENZA `--`. Qualsiasi variabile e' ammessa.
- Effetti integrati (`tipo`): `neve`, `lucine` (`stile`: `filo` | `bokeh`), `ragnatele` (`angoli`, `ragno`),
  `foglie`, `petali`, `coriandoli`, `pipistrelli`, `lucciole` (`colore`),
  d'angolo (SVG, `angoli`, `dimensione`, `opacita`): `germogli`, `fogliame`, `uova`.
- Regola: Halloween, Natale e Pasqua partono ALMENO 10 giorni prima della festa (20/10, 01/12, Pasqua-10).
  Parametri comuni: `quantita`, `opacita`, `solo` (`"light"` o `"dark"` per limitarlo a un modo).

## Effetto personalizzato (effetto.js)
```js
// ctx = { dark, livello (div fisso, pointer-events none), periodo }
// deve restituire una funzione di pulizia
export default function (ctx) {
  const el = document.createElement('div');
  ctx.livello.appendChild(el);
  return () => el.remove();
}
```

## Come funziona il motore (src/core.js)
- Caricato come modulo da Lovelace. Ogni 30 s (e ad ogni cambio tema) ricalcola:
  periodo attivo (data odierna) + modo light/dark.
- Light/dark: 1) nome del tema attivo contiene "dark/scuro/notte" -> dark, "light/chiaro" -> light;
  2) altrimenti `hass.themes.darkMode`; 3) altrimenti luminosita' di `--primary-background-color`.
- Palette: un `<style>` in `<head>` con `html { --var: valore !important }` (vince sugli stili
  inline che HA applica col tema; si eredita dentro gli shadow DOM).
- Sfondo: imposta `--lovelace-background` (usata da Frosted Glass e dal frontend HA).
- Decorazioni/effetti: un `div` `position:fixed; inset:0; pointer-events:none; z-index` alto.
- Test/debug da URL: `?addobbi=natale` forza un periodo, `?addobbi=off` disattiva,
  `?addobbi=natale&modo=dark` forza anche il modo. (Si puo' anche fissare con
  `localStorage.addobbi = "halloween"`.)

## Integrazione HA (`custom_components/seasonal_glass/`) = modo principale di installare e configurare
- Si aggiunge da Impostazioni > Dispositivi e servizi; **Configura** apre un menu:
  Generale (animazioni sempre/auto/mai, giorni normali, periodi attivi) · Date dei periodi (inizio/fine per
  periodo, `MM-GG` o `P-10`/`P+3`, vuoto = automatico) · Salva e chiudi.
- `__init__.py`: serve `www/` su `/seasonal_glass/`, carica lo script in ogni pagina (`add_extra_js_url`,
  niente risorsa Lovelace), espone `/api/seasonal_glass/config` (senza login, lo legge anche il kiosk).
- Le opzioni stanno nella config entry (`.storage/core.config_entries`), non in YAML. Il plugin le rilegge
  ogni 2 minuti: nessun riavvio dopo una modifica.
- File GENERATI da build.py (non modificarli a mano): `www/`, `periodi.json`, `strings.json`, `translations/`.
  Un periodo nuovo compare da solo anche nei menu di Configura.
- `hacs.json` in radice: repo HACS di categoria Integration.
- Provata il 30/10/2026: import + conversione date dentro il container HA 2026.10.4 (copia in /tmp, poi rimossa).
- `python build.py --ha` copia l'integrazione in `C:\DockerConfig\HA\custom_components\seasonal_glass` (poi riavvio).
- Animazioni: il server di casa ha gli effetti visivi di Windows disattivati -> il browser segnala
  "riduci movimento". Per questo il predefinito e' `movimento: sempre` e non `auto`.

## Card calendario (`custom:seasonal-glass-card`, nello stesso file JS)
- Mostra periodo attuale + prossimi periodi con i normali in mezzo (date, durata), icona da `periodo.json` -> `icona`.
- 👁 = anteprima solo su questo dispositivo (localStorage `addobbi`), "Torna automatico" la toglie.
- **Modifiche manuali** nello YAML della card: `giorni_normale`, `periodi: { <id>: { da, a, pasqua, priorita, disattivo, nome, icona } }`.
  Valgono per TUTTI i dispositivi: il plugin all'avvio (e ogni 10 min) legge la dashboard via websocket
  `lovelace/config` (dashboard predefinita, o `window.seasonalGlass.dashboard`) e cerca la card.
  Funziona anche per l'utente non admin "tv" (lettura). Periodi modificati = badge "manuale".
- Nota: `da` e' la data grezza; se il periodo precedente e' attaccato, compare dal giorno dopo (cuscinetto).
- Da valutare: editor visuale con campi data (salvare la config richiede admin).

## Kiosk / screensaver Chromecast (da fare SICURAMENTE)
Il plugin deve girare anche sulla pagina screensaver castata sul Chromecast
(`C:\DockerConfig\HA\www\screensaver\index.html`, servita da ha-kiosk come `/kiosk` del proxy ha-kiosk).
Non e' una dashboard Lovelace, quindi va incluso a mano nella pagina:
```html
<script>window.seasonalGlass = { modo: 'dark' };</script>  <!-- o 'light', o una funzione che ritorna true se scuro -->
<script type="module" src="/local/seasonal-glass/seasonal-glass.js"></script>
```
- Fuori da Lovelace non c'e' il tema HA da cui capire light/dark: si usa `window.seasonalGlass.modo`.
- `--lovelace-background` li' non ha effetto: per lo sfondo del periodo la pagina dovra' leggere
  `window.__seasonalGlass` oppure usare la variabile CSS nel proprio `background`.
- Il Chromecast e' debole: controllare fluidita' (eventualmente meno `quantita`).
- Verificare il percorso `/local/...` attraverso il proxy ha-kiosk (:8124).

## Verifiche
- `python build.py` stampa i periodi trovati; `node --check dist/seasonal-glass.js` per la sintassi.
- Anteprima: aprire `anteprima.html` (periodo e light/dark dai controlli in alto).
- Calendario: script node usato il 30/10/2026 che percorre ogni giorno 2026-2035 e segnala
  sovrapposizioni o periodi attaccati senza normale (da ricreare in `tools/` se serve).

## Stato e prossimi passi
- [x] Licenze verificate (30/10/2026): Frosted Glass (wessamlauf/homeassistant-frosted-glass-themes)
      e liquid-glass (Nezz/homeassistant-visionos-theme) sono **MIT**. Il plugin non copia codice
      da loro: non c'e' obbligo, ma nel README citarli come ispirazione.
- [x] Motore + 8 periodi (carnevale, pasqua, primavera, estate, autunno, halloween, inverno, natale) + anteprima.
- [x] README.md (inglese, per GitHub/HACS).
- [x] Card calendario con modifiche manuali.
- [x] Kiosk/screensaver Chromecast: plugin incluso + variabili `--seasonal-glass-velatura/colore`.
- [ ] Immagini dell'utente (sfondi): solo proprie / generate / licenza libera.
- [x] Integrazione con menu Configura (al posto della risorsa manuale).
- [x] Installata in HA locale (v0.1.3): velatura sfondo + menu Configura -> Colori + icone brand.
- [x] Pubblicata su GitHub (30/10/2026): https://github.com/pietroguidetti02/ha-seasonal-glass (pubblico,
      8 topic, release v0.1.3, GIF dei periodi in `docs/`, invito alla stella in fondo al README).
- [x] Validazione automatica `.github/workflows/validate.yml` (hacs/action + hassfest): verde.
- [ ] Elenco ufficiale HACS: PR https://github.com/hacs/default/pull/12990 (13 controlli verdi), in attesa
      di revisione umana (settimane). Non toccare il ramo `pietroguidetti02-add-seasonal-glass` del fork
      `pietroguidetti02/default` finche' e' aperta. Nel frattempo: HACS -> Custom repositories.
- [ ] Lancio su Reddit / forum HA a inizio dicembre (Natale), con il link del repo e le GIF.

## Pubblicare una nuova versione
1. Modificare `src/` o `periodi/`, poi `python build.py` (con `--ha` copia anche nell'HA locale -> riavvio).
2. Alzare `version` in `custom_components/seasonal_glass/manifest.json` (il `?v=` fa riscaricare lo script alle app).
3. Commit, `git push` (il login gh ha gli scope repo + workflow), aspettare che **Validate** sia verde su Actions.
4. SOLO DOPO i test verdi: `gh release create vX.Y.Z -R pietroguidetti02/ha-seasonal-glass --title vX.Y.Z --notes "..."`.
   (Una release creata prima dei test e' stata rifatta il 30/10: HACS chiede release successive alla validazione.)
- Autore dei commit: pietroguidetti02 con indirizzo noreply di GitHub (config locale del repo), mai l'email personale.
- GIF del README: catturate da `anteprima.html` con Edge headless via DevTools (script node `cattura.mjs`,
  40 fotogrammi a 80 ms) + ffmpeg con palette; ricrearle se cambiano gli effetti.

## Ambiente
Server di casa Windows, HA in Docker, config in `C:\DockerConfig\HA` (git locale,
diario `diario-di-bordo-HA.txt`). Vedi `C:\DockerConfig\CLAUDE.md`.
