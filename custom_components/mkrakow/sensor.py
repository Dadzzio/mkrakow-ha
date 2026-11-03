"""Sensory: koniec ważności biletu (timestamp), dni do końca, sesja."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import MKrakowConfigEntry
from .const import DOMAIN
from .coordinator import MKrakowKoordynator
from .entity import encja_urzadzenia


def _dni(dane: dict[str, Any]) -> int | None:
    koniec: datetime | None = dane.get("waznosc")
    if koniec is None:
        return 0
    return (dt_util.as_local(koniec).date() - dt_util.now().date()).days


def _sesja(k: MKrakowKoordynator) -> datetime | None:
    if not k.sesja_od:
        return None
    return datetime.fromtimestamp(k.sesja_od, tz=timezone.utc)


@dataclass(frozen=True, kw_only=True)
class OpisSensora(SensorEntityDescription):
    wartosc: Callable[[MKrakowKoordynator], Any]
    atrybuty: Callable[[MKrakowKoordynator], dict[str, Any]] | None = None


SENSORY = (
    OpisSensora(
        key="waznosc_biletu",
        translation_key="waznosc_biletu",
        icon="mdi:ticket-confirmation",
        device_class=SensorDeviceClass.TIMESTAMP,
        wartosc=lambda k: k.data.get("waznosc"),
        atrybuty=lambda k: {
            "bilet": k.data.get("bilet"),
            "aktualny": k.data.get("aktualny"),
            "bilety": k.data.get("wszystkie"),
        },
    ),
    OpisSensora(
        key="dni_do_konca",
        translation_key="dni_do_konca",
        icon="mdi:calendar-clock",
        native_unit_of_measurement=UnitOfTime.DAYS,
        wartosc=lambda k: _dni(k.data),
    ),
    OpisSensora(
        key="sesja",
        translation_key="sesja",
        icon="mdi:account-key",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        wartosc=_sesja,
        atrybuty=lambda k: {"ostatnia_aktualizacja": k.data.get("aktualizacja")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: MKrakowConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    k = entry.runtime_data
    async_add_entities(SensorMKrakow(k, opis) for opis in SENSORY)


class SensorMKrakow(CoordinatorEntity[MKrakowKoordynator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: OpisSensora

    def __init__(self, k: MKrakowKoordynator, opis: OpisSensora) -> None:
        super().__init__(k)
        self.entity_description = opis
        wpis = k.config_entry
        self._attr_unique_id = f"{wpis.unique_id}_{opis.key}"
        # stałe entity_id niezależnie od języka HA
        self.entity_id = f"sensor.{DOMAIN}_{opis.key}"
        self._attr_device_info = encja_urzadzenia(k)

    @property
    def native_value(self) -> Any:
        return self.entity_description.wartosc(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.atrybuty is None:
            return None
        return self.entity_description.atrybuty(self.coordinator)
