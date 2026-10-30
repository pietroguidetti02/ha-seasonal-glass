"""Seasonal Glass: addobbi stagionali automatici per le dashboard.

L'integrazione:
- serve i file del plugin (cartella www/) su /seasonal_glass/ e lo carica in ogni pagina del frontend
  (niente risorsa Lovelace da aggiungere a mano);
- espone le impostazioni scelte da "Configura" su /api/seasonal_glass/config (senza login: sono solo
  date e preferenze grafiche, cosi' le legge anche la pagina kiosk).
"""
from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, URL_BASE, converti_opzioni

CARTELLA = Path(__file__).parent


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
        dati["registrato"] = True
    dati["opzioni"] = dict(entry.options)
    entry.async_on_unload(entry.add_update_listener(_opzioni_cambiate))
    return True


async def _opzioni_cambiate(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data[DOMAIN]["opzioni"] = dict(entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # lo script resta caricato fino al riavvio, ma senza impostazioni torna al calendario automatico
    hass.data[DOMAIN]["opzioni"] = {}
    return True


class ConfigView(HomeAssistantView):
    """Impostazioni correnti nel formato che il plugin JS si aspetta."""

    url = "/api/seasonal_glass/config"
    name = "api:seasonal_glass:config"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request):
        return self.json(converti_opzioni(self.hass.data.get(DOMAIN, {}).get("opzioni", {})))
