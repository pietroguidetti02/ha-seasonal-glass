"""Sensore "periodo attuale" (es. Halloween, Normale). A ogni cambio, se l'opzione "notifica" e' attiva,
crea una notifica interna di HA. Lo stato precedente viene ripristinato al riavvio: niente notifiche doppie.
Attributi: fine del periodo attuale, prossimo periodo, quando inizia e tra quanti giorni (per le automazioni)."""
from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.restore_state import RestoreEntity

from datetime import date

from .calendario import calendario
from .const import DOMAIN

NORMALE = "Normale"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([PeriodoSensor(entry)])


class PeriodoSensor(RestoreEntity, SensorEntity):
    _attr_name = "Seasonal Glass periodo"
    _attr_icon = "mdi:pine-tree"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_periodo"
        self._precedente: str | None = None

    async def async_added_to_hass(self) -> None:
        if (vecchio := await self.async_get_last_state()) is not None:
            self._precedente = vecchio.state
        self._aggiorna(scrivi=False)
        # poco dopo mezzanotte (il calendario cambia solo di giorno) e quando cambiano le opzioni
        self.async_on_remove(async_track_time_change(self.hass, self._mezzanotte, hour=0, minute=0, second=10))
        self.async_on_remove(self._entry.add_update_listener(self._opzioni))

    async def _opzioni(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._aggiorna()

    @callback
    def _mezzanotte(self, _now) -> None:
        self._aggiorna()

    @callback
    def _aggiorna(self, scrivi: bool = True) -> None:
        o = self._entry.options
        oggi = date.today()
        tratti = calendario(dict(o), oggi)
        p = tratti[0]["periodo"]
        prossimo = next((t for t in tratti[1:] if t["periodo"]), None)  # prossimo addobbo vero (salta "normale")
        nome = p["nome"] if p else NORMALE
        self._attr_native_value = nome
        self._attr_extra_state_attributes = {
            "id": tratti[0]["id"], "icona": (p or {}).get("icona", ""),
            "fine": tratti[0]["fine"].isoformat(),
            "prossimo": prossimo["periodo"]["nome"] if prossimo else None,
            "prossimo_id": prossimo["id"] if prossimo else None,
            "prossimo_icona": prossimo["periodo"].get("icona", "") if prossimo else None,
            "prossimo_inizio": prossimo["inizio"].isoformat() if prossimo else None,
            "giorni_al_prossimo": (prossimo["inizio"] - oggi).days if prossimo else None,
        }
        if self._precedente not in (None, "unknown", "unavailable", nome) and o.get("notifica", True):
            icona = (p or {}).get("icona", "✨")
            persistent_notification.async_create(
                self.hass, f"Da oggi le dashboard sono in modalita' **{nome}**.",
                title=f"{icona} Seasonal Glass", notification_id=f"{DOMAIN}_cambio")
        self._precedente = nome
        if scrivi:
            self.async_write_ha_state()
