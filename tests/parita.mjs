// Calcola il periodo di ogni giorno con la logica di src/core.js (solo il blocco "date", senza browser).
// node tests/parita.mjs <periodi.json> <giorni_normale> <anno_da> <anno_a>  -> JSON {"AAAA-MM-GG": id}
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const [file, n, da, a] = process.argv.slice(2);
const core = readFileSync(new URL('../src/core.js', import.meta.url), 'utf8');
const blocco = core.slice(core.indexOf('// ---------- date ----------'), core.indexOf('// ---------- light / dark'));
const PERIODI = JSON.parse(readFileSync(file, 'utf8'));
const ctx = { PERIODI, MANUALE: { giorni_normale: +n }, IMPOSTAZIONI: {}, periodiEffettivi: () => PERIODI };
vm.runInNewContext(blocco + `
  const out = {};
  for (let d = new Date(${+da}, 0, 1); d.getFullYear() <= ${+a}; d.setDate(d.getDate() + 1)) {
    const p = periodoDelGiorno(new Date(d)), m = String(d.getMonth() + 1).padStart(2, '0'), g = String(d.getDate()).padStart(2, '0');
    out[d.getFullYear() + '-' + m + '-' + g] = p ? p.id : 'normale';
  }
  risultato = JSON.stringify(out);`, ctx);
process.stdout.write(ctx.risultato);
