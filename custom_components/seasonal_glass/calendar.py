"""Calendario di HA "Seasonal Glass": i periodi dell'anno come eventi di giornata intera
(pannello Calendario, card calendario, automazioni con trigger calendario). Il "normale" non compare."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change

from .calendario import calendario


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([PeriodiCalendar(entry)])


def _evento(t: dict) -> CalendarEvent:
    p = t["periodo"]
    return CalendarEvent(
        summary=f"{p.get('icona', '')} {p['nome']}".strip(), start=t["inizio"], end=t["fine"] + timedelta(days=1),
        uid=f"seasonal_glass_{t['id']}_{t['inizio'].isoformat()}")


class PeriodiCalendar(CalendarEntity):
    _attr_name = "Seasonal Glass"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_calendario"

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_track_time_change(self.hass, self._ricalcola, hour=0, minute=0, second=10))
        self.async_on_remove(self._entry.add_update_listener(self._opzioni))

    async def _opzioni(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.async_write_ha_state()

    @callback
    def _ricalcola(self, _now=None) -> None:
        self.async_write_ha_state()

    def _tratti(self, dal: date, giorni: int) -> list[dict]:
        return [t for t in calendario(dict(self._entry.options), dal, giorni) if t["periodo"]]

    @property
    def event(self) -> CalendarEvent | None:
        """Periodo in corso (con la sua vera data d'inizio), altrimenti il prossimo."""
        oggi = date.today()
        tratti = [t for t in self._tratti(oggi - timedelta(days=120), 520) if t["fine"] >= oggi]
        return _evento(tratti[0]) if tratti else None

    async def async_get_events(self, hass: HomeAssistant, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        # si parte 4 mesi prima (piu' del periodo piu' lungo) per avere giusto l'inizio di un periodo gia' in corso
        dal = start_date.date() - timedelta(days=120)
        giorni = min((end_date.date() - dal).days + 1, 3 * 366)
        return [_evento(t) for t in self._tratti(dal, giorni) if t["fine"] >= start_date.date() and t["inizio"] < end_date.date()]
