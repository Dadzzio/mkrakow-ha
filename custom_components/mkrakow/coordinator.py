"""Koordynator: co 30 min odświeża sesję (refresh token rotuje) i czyta listę biletów."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import bilety
from .api import MKrakowApi, MKrakowBlad, MKrakowSesjaWygasla
from .const import (
    CONF_APIKEY,
    CONF_APP_ID,
    CONF_AUTH_KLIENT,
    CONF_AUTH_SMS,
    CONF_TOKENY,
    DOMAIN,
    INTERWAL_MINUTY,
    WERSJA_MAGAZYNU,
    ZDARZENIE_SESJA_WYGASLA,
)

_LOGGER = logging.getLogger(__name__)


def utworz_api(hass: HomeAssistant, dane: dict[str, Any]) -> MKrakowApi:
    return MKrakowApi(
        async_get_clientsession(hass),
        dane[CONF_APIKEY],
        dane[CONF_AUTH_SMS],
        dane[CONF_AUTH_KLIENT],
        dane[CONF_APP_ID],
    )


def magazyn_tokenow(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, WERSJA_MAGAZYNU, f"{DOMAIN}.{entry_id}.tokeny")


class MKrakowKoordynator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=INTERWAL_MINUTY),
        )
        self.api = utworz_api(hass, dict(entry.data))
        self._magazyn = magazyn_tokenow(hass, entry.entry_id)
        self._tokeny: dict[str, Any] | None = None
        self.sesja_od: float | None = None
        # refresh token rotuje – dwa równoległe odświeżenia zabiłyby sesję
        self._blokada = asyncio.Lock()
        self.kod_encja: Any = None  # image.mkrakow_kod_biletu (ustawiane przez encję)

    async def _wczytaj_tokeny(self) -> dict[str, Any]:
        """Bierze nowsze z: magazynu (rotowane) i config entry (świeże logowanie/reauth)."""
        z_wpisu = self.config_entry.data.get(CONF_TOKENY) or {}
        z_magazynu = await self._magazyn.async_load() or {}
        if z_magazynu.get("wydano", 0) >= z_wpisu.get("wydano", 0):
            return z_magazynu or z_wpisu
        return z_wpisu

    async def _odswiez_sesje(self) -> str:
        """Odświeża sesję (pod blokadą) i zwraca aktualny access token."""
        async with self._blokada:
            if self._tokeny is None:
                self._tokeny = await self._wczytaj_tokeny()
                self.sesja_od = self._tokeny.get("zalogowano") or self._tokeny.get("wydano")
            if not self._tokeny.get("refresh_token"):
                raise MKrakowSesjaWygasla("Brak sesji – zaloguj się ponownie kodem SMS")
            nowe = await self.api.odswiez(self._tokeny["refresh_token"])
            nowe["zalogowano"] = self.sesja_od
            self._tokeny = nowe
            await self._magazyn.async_save(nowe)
            return nowe["access_token"]

    async def _token(self) -> str:
        """Ważny access token – bez odświeżania, jeśli zostało ponad 2 min."""
        t = self._tokeny or {}
        if t.get("access_token") and t.get("wygasa", 0) - time.time() > 120:
            return t["access_token"]
        return await self._odswiez_sesje()

    def _sesja_wygasla(self) -> None:
        self.hass.bus.async_fire(ZDARZENIE_SESJA_WYGASLA, {"entry_id": self.config_entry.entry_id})

    async def pobierz_kod(self) -> tuple[str, float]:
        """Kod Aztec do kontroli biletu (ważny ok. 5 min)."""
        try:
            token = await self._token()
            return await self.api.kod_kontrolny(token)
        except MKrakowSesjaWygasla:
            self._sesja_wygasla()
            self.config_entry.async_start_reauth(self.hass)
            raise

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            token = await self._odswiez_sesje()
            lista = await self.api.bilety(token)
        except MKrakowSesjaWygasla as ex:
            self._sesja_wygasla()
            raise ConfigEntryAuthFailed(str(ex)) from ex
        except MKrakowBlad as ex:
            raise UpdateFailed(str(ex)) from ex

        dane = bilety.podsumuj(lista, dt_util.utcnow())
        dane["aktualizacja"] = dt_util.utcnow()
        return dane
