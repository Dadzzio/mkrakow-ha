"""Wybór biletu z listy /skk-tickets/tickets/list (bez zależności od Home Assistanta)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parsuj_date(tekst: str | None) -> datetime | None:
    """Daty z API są w UTC, np. 2026-12-01T22:59:59Z."""
    if not tekst:
        return None
    try:
        data = datetime.fromisoformat(tekst.replace("Z", "+00:00"))
    except ValueError:
        return None
    if data.tzinfo is None:
        data = data.replace(tzinfo=timezone.utc)
    return data


def _opis(bilet: dict[str, Any]) -> dict[str, Any]:
    return {
        "nazwa": bilet.get("commodityName"),
        "status": bilet.get("status"),
        "od": bilet.get("startDate"),
        "do": bilet.get("endDate"),
        "miesiace": bilet.get("monthsPeriod"),
        "dni": bilet.get("daysPeriod"),
        "cena": bilet.get("price"),
        "metropolitalny": bilet.get("isMetropolitan"),
    }


def podsumuj(bilety: list[dict[str, Any]], teraz: datetime) -> dict[str, Any]:
    """Zwraca bilet, który kończy się najpóźniej spośród jeszcze ważnych.

    Kupiony z wyprzedzeniem bilet (start w przyszłości) przedłuża ważność,
    więc liczy się najpóźniejszy koniec, a nie tylko bilet aktywny dziś.
    """
    wazne = []
    for bilet in bilety:
        koniec = parsuj_date(bilet.get("endDate"))
        if koniec is None or koniec <= teraz:
            continue
        if str(bilet.get("status") or "").lower() in {"returned", "cancelled", "canceled"}:
            continue
        wazne.append((koniec, bilet))
    wazne.sort(key=lambda p: p[0])

    aktualny = None
    for _koniec, bilet in wazne:
        start = parsuj_date(bilet.get("startDate"))
        if start is None or start <= teraz:
            aktualny = bilet
    ostatni = wazne[-1] if wazne else None

    return {
        "waznosc": ostatni[0] if ostatni else None,
        "bilet": _opis(ostatni[1]) if ostatni else None,
        "aktualny": _opis(aktualny) if aktualny else None,
        "wszystkie": [_opis(b) for b in bilety],
    }
