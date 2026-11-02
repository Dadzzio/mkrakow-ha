"""Konfiguracja w UI: PESEL + numer telefonu (+ plik HAR ze stałymi aplikacji) → kod SMS."""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    FileSelector,
    FileSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import har
from .api import MKrakowApi, MKrakowBlad, MKrakowBladLogowania, nowe_app_id
from .const import (
    CONF_APIKEY,
    CONF_APP_ID,
    CONF_AUTH_KLIENT,
    CONF_AUTH_SMS,
    CONF_HAR,
    CONF_HAR_2,
    CONF_KOD_SMS,
    CONF_PESEL,
    CONF_TELEFON,
    CONF_TOKENY,
    DOMAIN,
)
from .coordinator import utworz_api

UKRYTE = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
PLIK = FileSelector(FileSelectorConfig(accept=".har,application/json"))
STALE = (CONF_APIKEY, CONF_AUTH_SMS, CONF_AUTH_KLIENT)

SCHEMAT_USER = vol.Schema(
    {
        vol.Required(CONF_PESEL): str,
        vol.Required(CONF_TELEFON): str,
        vol.Optional(CONF_HAR): PLIK,
        vol.Optional(CONF_HAR_2): PLIK,
        vol.Optional(CONF_APIKEY): UKRYTE,
        vol.Optional(CONF_AUTH_SMS): UKRYTE,
        vol.Optional(CONF_AUTH_KLIENT): UKRYTE,
    }
)


def _czytaj_har(hass, file_id: str) -> dict[str, str]:
    with process_uploaded_file(hass, file_id) as sciezka:
        return har.stale_z_har(sciezka.read_text(encoding="utf-8", errors="replace"))


SCHEMAT_SMS = vol.Schema({vol.Required(CONF_KOD_SMS): str})


class MKrakowConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._dane: dict[str, Any] = {}
        self._stan: dict[str, str] | None = None
        self._api: MKrakowApi | None = None

    async def _wyslij_sms(self) -> dict[str, str]:
        self._api = utworz_api(self.hass, self._dane)
        try:
            self._stan = await self._api.zaloguj(self._dane[CONF_PESEL], self._dane[CONF_TELEFON])
        except MKrakowBladLogowania:
            return {"base": "invalid_auth"}
        except MKrakowBlad:
            return {"base": "cannot_connect"}
        return {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        bledy: dict[str, str] = {}
        brakuje = ""
        if user_input is not None:
            stale: dict[str, str] = {}
            for klucz in (CONF_HAR, CONF_HAR_2):
                if file_id := user_input.get(klucz):
                    try:
                        z_pliku = await self.hass.async_add_executor_job(
                            _czytaj_har, self.hass, file_id
                        )
                    except (ValueError, OSError):
                        bledy = {klucz: "zly_har"}
                        continue
                    for k, v in z_pliku.items():
                        stale.setdefault(k, v)
            for k in STALE:
                if v := (user_input.get(k) or "").strip():
                    stale[k] = v
            braki = [k for k in STALE if not stale.get(k)]
            if not bledy and braki:
                bledy = {"base": "brak_stalych"}
                brakuje = ", ".join(braki)
            if not bledy:
                self._dane = {
                    CONF_PESEL: user_input[CONF_PESEL].strip(),
                    CONF_TELEFON: user_input[CONF_TELEFON].strip(),
                    **stale,
                    CONF_APP_ID: nowe_app_id(),
                }
                bledy = await self._wyslij_sms()
                if not bledy:
                    return await self.async_step_sms()
        schemat = SCHEMAT_USER
        if user_input is not None:
            schemat = self.add_suggested_values_to_schema(
                SCHEMAT_USER,
                {k: user_input.get(k) for k in (CONF_PESEL, CONF_TELEFON) if user_input.get(k)},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=schemat,
            errors=bledy,
            description_placeholders={"brakuje": brakuje},
        )

    async def async_step_sms(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        bledy: dict[str, str] = {}
        if user_input is not None and self._api and self._stan:
            try:
                tokeny = await self._api.potwierdz_sms(self._stan, user_input[CONF_KOD_SMS])
                ja = await self._api.uzytkownik(tokeny["access_token"])
            except MKrakowBladLogowania:
                bledy = {"base": "invalid_code"}
            except MKrakowBlad:
                bledy = {"base": "cannot_connect"}
            else:
                tokeny["zalogowano"] = time.time()
                dane = {**self._dane, CONF_TOKENY: tokeny}
                if self.source == "reauth":
                    return self.async_update_reload_and_abort(self._get_reauth_entry(), data=dane)
                await self.async_set_unique_id(str(ja.get("sub") or self._dane[CONF_PESEL]))
                self._abort_if_unique_id_configured()
                imie = ja.get("given_name") or "konto"
                return self.async_create_entry(title=f"mKraków ({imie})", data=dane)
        return self.async_show_form(step_id="sms", data_schema=SCHEMAT_SMS, errors=bledy)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        self._dane = {k: v for k, v in entry_data.items() if k != CONF_TOKENY}
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        bledy: dict[str, str] = {}
        if user_input is not None:
            bledy = await self._wyslij_sms()
            if not bledy:
                return await self.async_step_sms()
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
            errors=bledy,
        )
