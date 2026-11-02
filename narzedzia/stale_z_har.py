#!/usr/bin/env python3
"""Wyciąga z nagrania HAR (Proxyman) trzy stałe aplikacji mKraków potrzebne w integracji.

Użycie:  python3 stale_z_har.py nagranie.har [drugie.har ...]

Działa tylko lokalnie, niczego nie wysyła. Wypisuje WYŁĄCZNIE stałe aplikacji
(apikey i dwa nagłówki Authorization: Basic) – bez PESEL-u, numeru telefonu i tokenów.
"""

import json
import sys

HOST = "api.um.krakow.pl"


def naglowek(wpis, nazwa):
    for h in wpis["request"].get("headers", []):
        if h.get("name", "").lower() == nazwa:
            return h.get("value")
    return None


def main(pliki):
    apikey = auth_sms = auth_klient = None
    for plik in pliki:
        with open(plik, encoding="utf-8") as f:
            har = json.load(f)
        for wpis in har.get("log", {}).get("entries", []):
            url = wpis["request"].get("url", "")
            if HOST not in url:
                continue
            apikey = apikey or naglowek(wpis, "apikey")
            auth = naglowek(wpis, "authorization") or ""
            if not auth.lower().startswith("basic "):
                continue
            if "/mkrakow-sms/" in url:
                auth_sms = auth_sms or auth
            elif "/mkrakow-oauth/token" in url or "/mkrakow-oauth/revoke" in url:
                auth_klient = auth_klient or auth

    wyniki = [
        ("Nagłówek apikey", apikey, "dowolne zapytanie do api.um.krakow.pl"),
        ("Authorization z /mkrakow-sms/login", auth_sms, "nagraj logowanie w aplikacji (PESEL + SMS)"),
        ("Authorization z /mkrakow-oauth/token", auth_klient, "nagraj otwarcie aplikacji po >1 h przerwy albo wylogowanie"),
    ]
    brak = False
    for nazwa, wartosc, skad in wyniki:
        print(f"\n{nazwa}:")
        if wartosc:
            print(wartosc)
        else:
            brak = True
            print(f"  NIE ZNALEZIONO – {skad}")
    print()
    return 1 if brak else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
