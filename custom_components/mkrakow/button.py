"""Przycisk „Pokaż bilet”: pobiera świeży kod i pokazuje go przez 2 min."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MKrakowConfigEntry
from .const import DOMAIN
from .coordinator import MKrakowKoordynator
from .entity import encja_urzadzenia


async def async_setup_entry(
    hass: HomeAssistant, entry: MKrakowConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([PokazBilet(entry.runtime_data)])


class PokazBilet(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "pokaz_bilet"
    _attr_icon = "mdi:ticket-account"

    def __init__(self, k: MKrakowKoordynator) -> None:
        self.k = k
        self._attr_unique_id = f"{k.config_entry.unique_id}_pokaz_bilet"
        self.entity_id = f"button.{DOMAIN}_pokaz_bilet"
        self._attr_device_info = encja_urzadzenia(k)

    async def async_press(self) -> None:
        if self.k.kod_encja is not None:
            await self.k.kod_encja.odswiez(auto=True)
