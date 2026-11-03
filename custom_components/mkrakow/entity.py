"""Wspólne urządzenie dla encji integracji."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN


def encja_urzadzenia(k) -> DeviceInfo:
    wpis = k.config_entry
    return DeviceInfo(
        identifiers={(DOMAIN, wpis.unique_id or wpis.entry_id)},
        name="mKraków",
        manufacturer="Urząd Miasta Krakowa",
        model="Karta Krakowiaka – bilety KKM",
        entry_type=DeviceEntryType.SERVICE,
    )
