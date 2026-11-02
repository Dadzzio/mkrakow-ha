"""Wyciąganie stałych aplikacji mKraków z nagrania HAR (bez zależności od Home Assistanta)."""

from __future__ import annotations

import json
from typing import Any

HOST = "api.um.krakow.pl"

APIKEY = "apikey"
AUTH_SMS = "auth_sms"
AUTH_KLIENT = "auth_klient"


def _naglowek(wpis: dict[str, Any], nazwa: str) -> str | None:
    for h in wpis.get("request", {}).get("headers", []):
        if str(h.get("name", "")).lower() == nazwa:
            return h.get("value")
    return None


def stale_z_har(tekst: str) -> dict[str, str]:
    """Zwraca znalezione stałe: apikey, auth_sms, auth_klient (brakujących nie ma w wyniku)."""
    try:
        har = json.loads(tekst)
    except ValueError as ex:
        raise ValueError("To nie jest plik HAR (JSON)") from ex
    wynik: dict[str, str] = {}
    for wpis in (har.get("log") or {}).get("entries") or []:
        url = str(wpis.get("request", {}).get("url", ""))
        if HOST not in url:
            continue
        if APIKEY not in wynik and (k := _naglowek(wpis, "apikey")):
            wynik[APIKEY] = k
        auth = _naglowek(wpis, "authorization") or ""
        if not auth.lower().startswith("basic "):
            continue
        if "/mkrakow-sms/" in url:
            wynik.setdefault(AUTH_SMS, auth)
        elif "/mkrakow-oauth/token" in url or "/mkrakow-oauth/revoke" in url:
            wynik.setdefault(AUTH_KLIENT, auth)
    return wynik
