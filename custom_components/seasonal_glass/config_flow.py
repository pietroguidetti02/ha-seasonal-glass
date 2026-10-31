"""Aggiunta da Dispositivi e servizi + menu "Configura" (generale, date, colori, ricorrenze)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN, MODI, MOVIMENTI, PERIODI, PERIODI_V01, colore_predefinito, date_automatiche, leggi_data, leggi_ricorrenze


class SeasonalGlassConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Seasonal Glass", data={})
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return SeasonalGlassOptionsFlow()


class SeasonalGlassOptionsFlow(OptionsFlow):
    def __init__(self) -> None:
        self.opzioni: dict | None = None
        self.periodo: dict | None = None  # periodo scelto nel menu Colori

    def _opz(self) -> dict:
        if self.opzioni is None:
            self.opzioni = dict(self.config_entry.options)
        return self.opzioni

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="init", menu_options=["generale", "date", "colori", "ricorrenze", "salva"])

    async def async_step_generale(self, user_input=None) -> ConfigFlowResult:
        o = self._opz()
        tutti = [p["id"] for p in PERIODI]
        if user_input is not None:
            o.update(user_input, noti=tutti)  # periodi visti nel menu: d'ora in poi decide "attivi"
            return await self.async_step_init()
        schema = vol.Schema({
            vol.Required("movimento", default=o.get("movimento", "auto")): selector.SelectSelector(
                selector.SelectSelectorConfig(options=MOVIMENTI, translation_key="movimento",
                                              mode=selector.SelectSelectorMode.LIST)),
            vol.Required("giorni_normale", default=o.get("giorni_normale", 1)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=30, step=1, mode=selector.NumberSelectorMode.BOX,
                                              unit_of_measurement="giorni")),
            vol.Required("attivi", default=[i for i in tutti if i in o.get("attivi", tutti) or i not in o.get("noti", PERIODI_V01)]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[{"value": p["id"], "label": f"{p.get('icona', '')} {p['nome']}".strip()} for p in PERIODI],
                    multiple=True, mode=selector.SelectSelectorMode.LIST)),
            vol.Required("notifica", default=o.get("notifica", True)): selector.BooleanSelector(),
        })
        return self.async_show_form(step_id="generale", data_schema=schema)

    async def async_step_date(self, user_input=None) -> ConfigFlowResult:
        o, errori = self._opz(), {}
        if user_input is not None:
            for chiave, valore in user_input.items():
                try:
                    leggi_data(valore)
                except ValueError:
                    errori[chiave] = "data_non_valida"
            if not errori:
                for p in PERIODI:  # campo svuotato = torna automatico
                    for e in ("da", "a"):
                        o[f"{p['id']}_{e}"] = user_input.get(f"{p['id']}_{e}", "").strip()
                return await self.async_step_init()
        campi, righe = {}, []
        for p in PERIODI:
            da, a = date_automatiche(p)
            righe.append(f"{p.get('icona', '')} **{p['nome']}**: {da} → {a}")
            for e in ("da", "a"):
                k = f"{p['id']}_{e}"
                valore = (user_input or {}).get(k, o.get(k, ""))
                campi[vol.Optional(k, description={"suggested_value": valore})] = selector.TextSelector()
        return self.async_show_form(
            step_id="date", data_schema=vol.Schema(campi), errors=errori,
            description_placeholders={"automatiche": "\n".join(righe)},
        )

    async def async_step_colori(self, user_input=None) -> ConfigFlowResult:
        """Primo passo dei colori: quale periodo."""
        if user_input is not None:
            self.periodo = next(p for p in PERIODI if p["id"] == user_input["periodo"])
            return await self.async_step_colori_periodo()
        o = self._opz()
        opzioni = []
        for p in PERIODI:
            modificato = any(k.startswith(p["id"] + "_") and k.split("_", 1)[1].split("_")[0]
                             in ("principale", "velatura", "intensita") for k in o)
            etichetta = f"{p.get('icona', '')} {p['nome']}".strip() + (" ✎" if modificato else "")
            opzioni.append({"value": p["id"], "label": etichetta})
        schema = vol.Schema({vol.Required("periodo", default=PERIODI[0]["id"]): selector.SelectSelector(
            selector.SelectSelectorConfig(options=opzioni, mode=selector.SelectSelectorMode.LIST))})
        return self.async_show_form(step_id="colori", data_schema=schema)

    async def async_step_colori_periodo(self, user_input=None) -> ConfigFlowResult:
        """Colore principale e velatura del periodo scelto. Si salva solo cio' che differisce dal predefinito."""
        o, p = self._opz(), self.periodo
        pid = p["id"]
        chiavi = [f"{pid}_principale_{m}" for m in MODI] + [f"{pid}_velatura_{m}" for m in MODI] + [f"{pid}_intensita"]
        if user_input is not None:
            for k in chiavi:
                o.pop(k, None)
            if not user_input.get("ripristina"):
                for m in MODI:
                    scelto = user_input.get(f"principale_{m}")
                    if scelto and list(map(int, scelto)) != colore_predefinito(p, m):
                        o[f"{pid}_principale_{m}"] = list(map(int, scelto))
                    if user_input.get(f"velatura_{m}"):
                        o[f"{pid}_velatura_{m}"] = list(map(int, user_input[f"velatura_{m}"]))
                if user_input.get("intensita") is not None:
                    o[f"{pid}_intensita"] = user_input["intensita"]
            return await self.async_step_init()
        campi = {}
        for m in MODI:
            valore = o.get(f"{pid}_principale_{m}") or colore_predefinito(p, m)
            campi[vol.Optional(f"principale_{m}", description={"suggested_value": valore})] = selector.ColorRGBSelector()
        for m in MODI:
            campi[vol.Optional(f"velatura_{m}", description={"suggested_value": o.get(f"{pid}_velatura_{m}")})] =                 selector.ColorRGBSelector()
        campi[vol.Optional("intensita", description={"suggested_value": o.get(f"{pid}_intensita")})] =             selector.NumberSelector(selector.NumberSelectorConfig(
                min=0, max=60, step=5, mode=selector.NumberSelectorMode.SLIDER, unit_of_measurement="%"))
        campi[vol.Optional("ripristina", default=False)] = selector.BooleanSelector()
        return self.async_show_form(
            step_id="colori_periodo", data_schema=vol.Schema(campi),
            description_placeholders={"periodo": f"{p.get('icona', '')} {p['nome']}".strip()},
        )

    async def async_step_ricorrenze(self, user_input=None) -> ConfigFlowResult:
        """Compleanni, anniversari...: una per riga 'MM-GG Nome [emoji] [#colore]'."""
        o, errori, riga = self._opz(), {}, ""
        if user_input is not None:
            testo = user_input.get("ricorrenze", "")
            try:
                leggi_ricorrenze(testo)
            except ValueError as e:
                errori["ricorrenze"], riga = "ricorrenza_non_valida", str(e)
            else:
                o["ricorrenze"] = testo.strip()
                return await self.async_step_init()
        valore = (user_input or {}).get("ricorrenze", o.get("ricorrenze", ""))
        schema = vol.Schema({vol.Optional("ricorrenze", description={"suggested_value": valore}):
                             selector.TextSelector(selector.TextSelectorConfig(multiline=True))})
        return self.async_show_form(step_id="ricorrenze", data_schema=schema, errors=errori,
                                    description_placeholders={"riga": riga})

    async def async_step_salva(self, user_input=None) -> ConfigFlowResult:
        return self.async_create_entry(data=self._opz())
