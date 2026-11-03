"""Kod Aztec biletu do kontroli – generowany na żądanie, ważny ok. 5 min."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from . import MKrakowConfigEntry, aztec
from .api import MKrakowBlad
from .const import DOMAIN
from .coordinator import MKrakowKoordynator
from .entity import encja_urzadzenia

ZAPAS_S = 45  # odśwież kod, gdy do wygaśnięcia zostało mniej
AUTO_ODSWIEZANIE_MIN = 10  # po naciśnięciu „Pokaż bilet” kod odświeża się sam przez tyle minut


async def async_setup_entry(
    hass: HomeAssistant, entry: MKrakowConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([KodBiletu(hass, entry.runtime_data)])


class KodBiletu(ImageEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "kod_biletu"
    _attr_content_type = "image/png"
    _attr_icon = "mdi:qrcode"

    def __init__(self, hass: HomeAssistant, k: MKrakowKoordynator) -> None:
        super().__init__(hass)
        self.entity_description = ImageEntityDescription(key="kod_biletu")
        self.k = k
        wpis = k.config_entry
        self._attr_unique_id = f"{wpis.unique_id}_kod_biletu"
        self.entity_id = f"image.{DOMAIN}_kod_biletu"
        self._attr_device_info = encja_urzadzenia(k)
        self._png: bytes | None = None
        self._wygasa: float = 0
        self._auto_do: float = 0
        self._blad: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._co_minute, timedelta(minutes=1))
        )
        self.k.kod_encja = self

    @callback
    def _co_minute(self, _teraz: datetime) -> None:
        # w oknie auto-odświeżania wymuś nowy obraz, zanim kod wygaśnie
        if time.time() < self._auto_do and self._wygasa - time.time() < 90:
            self.hass.async_create_task(self.odswiez())

    async def odswiez(self, auto: bool = False) -> None:
        if auto:
            self._auto_do = time.time() + AUTO_ODSWIEZANIE_MIN * 60
        try:
            tresc, wygasa = await self.k.pobierz_kod()
        except MKrakowBlad as ex:
            self._blad = str(ex)
            self.async_write_ha_state()
            return
        self._png = await self.hass.async_add_executor_job(aztec.png, tresc)
        self._wygasa = wygasa
        self._blad = None
        self._attr_image_last_updated = dt_util.utcnow()
        self.async_write_ha_state()

    async def async_image(self) -> bytes | None:
        if self._png is None or self._wygasa - time.time() < ZAPAS_S:
            await self.odswiez()
        return self._png

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "wazny_do": datetime.fromtimestamp(self._wygasa, tz=timezone.utc).isoformat()
            if self._wygasa
            else None,
            "auto_odswiezanie_do": datetime.fromtimestamp(
                self._auto_do, tz=timezone.utc
            ).isoformat()
            if self._auto_do > time.time()
            else None,
            "blad": self._blad,
        }
