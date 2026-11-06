"""Seasonal Glass: addobbi stagionali automatici per le dashboard.

L'integrazione:
- serve i file del plugin (cartella www/) su /seasonal_glass/ e lo carica in ogni pagina del frontend
  (niente risorsa Lovelace da aggiungere a mano);
- espone le impostazioni scelte da "Configura" su /api/seasonal_glass/impostazioni (con login: dentro ci sono
  anche i giorni personali; le pagine fuori dal frontend usano il calendario automatico);
- crea il sensore "Periodo" (sensor.py), che avvisa con una notifica interna quando l'addobbo cambia,
  e il calendario dei periodi (calendar.py);
- offre il servizio seasonal_glass.anteprima: mostra un periodo su tutti i dispositivi per qualche minuto
  (il plugin lo legge dallo stesso endpoint, entro ~30 secondi).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, PERIODI, URL_BASE, converti_opzioni

CARTELLA = Path(__file__).parent
PIATTAFORME = ["sensor", "calendar"]
SCHEMA_ANTEPRIMA = vol.Schema({
    vol.Required("periodo"): cv.string,
    vol.Optional("minuti", default=10): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    dati = hass.data.setdefault(DOMAIN, {})
    if not dati.get("registrato"):  # percorsi e script si registrano una volta sola per avvio
        manifest = await hass.async_add_executor_job((CARTELLA / "manifest.json").read_text, "utf-8")
        versione = json.loads(manifest)["version"]
        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASE, str(CARTELLA / "www"), False)]
        )
        hass.http.register_view(ConfigView(hass))
        add_extra_js_url(hass, f"{URL_BASE}/seasonal-glass.js?v={versione}")
        hass.services.async_register(DOMAIN, "anteprima", _anteprima, schema=SCHEMA_ANTEPRIMA)
        dati["registrato"] = True
    dati["opzioni"] = dict(entry.options)
    entry.async_on_unload(entry.add_update_listener(_opzioni_cambiate))
    await hass.config_entries.async_forward_entry_setups(entry, PIATTAFORME)
    return True


async def _anteprima(call: ServiceCall) -> None:
    """periodo = id (halloween, natale, ricorrenza_1...) oppure "normale"; minuti = 0 annulla."""
    hass, pid, minuti = call.hass, call.data["periodo"].strip().lower(), call.data["minuti"]
    dati = hass.data[DOMAIN]
    validi = {p["id"] for p in PERIODI} | {r["id"] for r in converti_opzioni(dati.get("opzioni", {})).get("ricorrenze", [])}
    if pid not in validi | {"normale"}:
        raise ServiceValidationError(f"Periodo sconosciuto: {pid}. Validi: normale, {', '.join(sorted(validi))}")
    if minuti == 0:
        dati.pop("anteprima", None)
    else:
        dati["anteprima"] = {"id": "off" if pid == "normale" else pid, "fino": int((time.time() + minuti * 60) * 1000)}


async def _opzioni_cambiate(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data[DOMAIN]["opzioni"] = dict(entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # lo script resta caricato fino al riavvio, ma senza impostazioni torna al calendario automatico
    hass.data[DOMAIN]["opzioni"] = {}
    return await hass.config_entries.async_unload_platforms(entry, PIATTAFORME)


class ConfigView(HomeAssistantView):
    """Impostazioni correnti nel formato che il plugin JS si aspetta."""

    url = "/api/seasonal_glass/impostazioni"
    name = "api:seasonal_glass:impostazioni"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request):
        dati = self.hass.data.get(DOMAIN, {})
        out = converti_opzioni(dati.get("opzioni", {}))
        if (a := dati.get("anteprima")) and a["fino"] > time.time() * 1000:
            out["anteprima"] = a
        return self.json(out)
