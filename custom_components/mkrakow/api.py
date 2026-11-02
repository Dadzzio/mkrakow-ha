"""Klient nieoficjalnego API aplikacji mKraków (api.um.krakow.pl)."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from typing import Any

import aiohttp

from .const import API_URL

_LOGGER = logging.getLogger(__name__)

SCOPE = "KartaKrakowiaka openid"
USER_AGENT = "mkrakow/7 CFNetwork/3896.200.61 Darwin/27.2.0"
WERSJA_KLIENTA = "mKrakow 4.0.1"
PLATFORMA = "iOS 27.2"
TIMEOUT = aiohttp.ClientTimeout(total=30)


class MKrakowBlad(Exception):
    """Błąd połączenia lub nieoczekiwana odpowiedź."""


class MKrakowBladLogowania(MKrakowBlad):
    """Złe dane logowania albo zły kod SMS."""


class MKrakowSesjaWygasla(MKrakowBlad):
    """Refresh token nie działa – potrzebne nowe logowanie z kodem SMS."""


def naglowek_basic(wartosc: str) -> str:
    wartosc = wartosc.strip()
    if wartosc.lower().startswith("authorization:"):
        wartosc = wartosc.split(":", 1)[1].strip()
    if not wartosc.lower().startswith("basic "):
        wartosc = f"Basic {wartosc}"
    return wartosc


def telefon_api(telefon: str) -> str:
    """Aplikacja wysyła numer telefonu w polu password jako 9 cyfr (bez +48)."""
    cyfry = "".join(z for z in telefon if z.isdigit())
    if len(cyfry) == 11 and cyfry.startswith("48"):
        cyfry = cyfry[2:]
    return cyfry


def nowe_app_id() -> str:
    return secrets.token_hex(16)


class MKrakowApi:
    def __init__(
        self,
        sesja: aiohttp.ClientSession,
        apikey: str,
        auth_sms: str,
        auth_klient: str,
        app_id: str,
    ) -> None:
        self._sesja = sesja
        self._apikey = apikey.strip()
        self._auth_sms = naglowek_basic(auth_sms)
        self._auth_klient = naglowek_basic(auth_klient)
        self._app_id = app_id

    def _naglowki(self, autoryzacja: str | None = None) -> dict[str, str]:
        h = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pl-PL,pl;q=0.9",
            "User-Agent": USER_AGENT,
            "apikey": self._apikey,
        }
        if autoryzacja:
            h["Authorization"] = autoryzacja
        return h

    async def _zadanie(
        self, metoda: str, sciezka: str, naglowki: dict[str, str], **kwargs: Any
    ) -> tuple[int, Any]:
        try:
            async with self._sesja.request(
                metoda, f"{API_URL}{sciezka}", headers=naglowki, timeout=TIMEOUT, **kwargs
            ) as odp:
                tekst = await odp.text()
                try:
                    dane = await odp.json(content_type=None) if tekst else None
                except ValueError:
                    dane = None
                return odp.status, dane
        except (aiohttp.ClientError, asyncio.TimeoutError) as ex:
            raise MKrakowBlad(f"Brak połączenia z api.um.krakow.pl: {ex}") from ex

    # --- logowanie (2FA SMS) ---

    async def zaloguj(self, pesel: str, telefon: str) -> dict[str, str]:
        """Krok 1: wysyła SMS. Zwraca stan potrzebny do potwierdzenia kodem."""
        state = secrets.token_hex(16)
        status, dane = await self._zadanie(
            "POST",
            "/mkrakow-sms/login",
            self._naglowki(self._auth_sms),
            json={
                "username": pesel.strip(),
                "password": telefon_api(telefon),
                "state": state,
                "appId": self._app_id,
            },
        )
        if status in (400, 401, 403) or (status == 200 and not (dane or {}).get("success")):
            raise MKrakowBladLogowania(f"Logowanie odrzucone (HTTP {status})")
        if status != 200 or not (dane or {}).get("transactionId"):
            raise MKrakowBlad(f"Nieoczekiwana odpowiedź logowania (HTTP {status})")
        return {"state": state, "transactionId": dane["transactionId"]}

    async def potwierdz_sms(self, stan: dict[str, str], kod: str) -> dict[str, Any]:
        """Krok 2: kod SMS → tokeny."""
        status, dane = await self._zadanie(
            "POST",
            "/mkrakow-sms/validate-sms",
            self._naglowki(self._auth_sms),
            json={
                "state": stan["state"],
                "appId": self._app_id,
                "transactionId": stan["transactionId"],
                "smsOTP": kod.strip(),
            },
        )
        if status in (400, 401, 403) or (status == 200 and not (dane or {}).get("access_token")):
            raise MKrakowBladLogowania(f"Kod SMS odrzucony (HTTP {status})")
        if status != 200:
            raise MKrakowBlad(f"Nieoczekiwana odpowiedź weryfikacji SMS (HTTP {status})")
        return self._tokeny(dane)

    # --- sesja ---

    @staticmethod
    def _tokeny(dane: dict[str, Any]) -> dict[str, Any]:
        teraz = time.time()
        return {
            "access_token": dane["access_token"],
            "refresh_token": dane["refresh_token"],
            "wygasa": teraz + int(dane.get("expires_in") or 3600),
            "wydano": teraz,
        }

    async def odswiez(self, refresh_token: str) -> dict[str, Any]:
        """Nowy access token. Refresh token rotuje – zawsze zapisz nowy."""
        status, dane = await self._zadanie(
            "POST",
            "/mkrakow-oauth/token",
            self._naglowki(self._auth_klient),
            data={"grant_type": "refresh_token", "refresh_token": refresh_token, "scope": SCOPE},
        )
        if status in (400, 401):
            raise MKrakowSesjaWygasla(f"Odświeżenie sesji odrzucone (HTTP {status})")
        if status != 200 or not (dane or {}).get("access_token"):
            raise MKrakowBlad(f"Nieoczekiwana odpowiedź odświeżania (HTTP {status})")
        return self._tokeny(dane)

    async def wyloguj(self, refresh_token: str) -> None:
        try:
            await self._zadanie(
                "POST",
                "/mkrakow-oauth/revoke",
                self._naglowki(self._auth_klient),
                data={"token": refresh_token, "token_type_hint": "refresh_token"},
            )
        except MKrakowBlad as ex:
            _LOGGER.debug("Wylogowanie nieudane: %s", ex)

    # --- dane ---

    async def uzytkownik(self, access_token: str) -> dict[str, Any]:
        status, dane = await self._zadanie(
            "GET", "/mkrakow-oauth/userinfo", self._naglowki(f"Bearer {access_token}")
        )
        if status == 401:
            raise MKrakowSesjaWygasla("Token nieważny")
        if status != 200 or not isinstance(dane, dict):
            raise MKrakowBlad(f"Nieoczekiwana odpowiedź userinfo (HTTP {status})")
        return dane

    async def bilety(self, access_token: str) -> list[dict[str, Any]]:
        naglowki = self._naglowki(f"Bearer {access_token}")
        naglowki.update(
            {
                "x-client-version": WERSJA_KLIENTA,
                "x-platform": PLATFORMA,
                "x-device-id": self._app_id,
                "x-device-name": "Home Assistant",
            }
        )
        status, dane = await self._zadanie("GET", "/skk-tickets/tickets/list", naglowki)
        if status == 401:
            raise MKrakowSesjaWygasla("Token nieważny")
        if status != 200 or not isinstance(dane, dict):
            raise MKrakowBlad(f"Nieoczekiwana odpowiedź listy biletów (HTTP {status})")
        return list(dane.get("tickets") or [])
