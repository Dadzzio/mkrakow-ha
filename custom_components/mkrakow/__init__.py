"""mKraków – ważność biletu okresowego KKM z aplikacji mKraków."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import MKrakowKoordynator, magazyn_tokenow, utworz_api

PLATFORMS = [Platform.BUTTON, Platform.IMAGE, Platform.SENSOR]

type MKrakowConfigEntry = ConfigEntry[MKrakowKoordynator]


async def async_setup_entry(hass: HomeAssistant, entry: MKrakowConfigEntry) -> bool:
    koordynator = MKrakowKoordynator(hass, entry)
    await koordynator.async_config_entry_first_refresh()
    entry.runtime_data = koordynator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MKrakowConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    magazyn = magazyn_tokenow(hass, entry.entry_id)
    tokeny = await magazyn.async_load() or {}
    if tokeny.get("refresh_token"):
        await utworz_api(hass, dict(entry.data)).wyloguj(tokeny["refresh_token"])
    await magazyn.async_remove()
