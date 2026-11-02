"""Stałe integracji mKraków."""

DOMAIN = "mkrakow"

API_URL = "https://api.um.krakow.pl"

CONF_PESEL = "pesel"
CONF_HASLO = "haslo"
CONF_KOD_SMS = "kod_sms"
CONF_APIKEY = "apikey"
CONF_AUTH_SMS = "auth_sms"
CONF_AUTH_KLIENT = "auth_klient"
CONF_APP_ID = "app_id"
CONF_TOKENY = "tokeny"

INTERWAL_MINUTY = 30  # odświeżenie sesji + odczyt biletów; access token żyje 60 min

ZDARZENIE_SESJA_WYGASLA = f"{DOMAIN}_sesja_wygasla"

WERSJA_MAGAZYNU = 1
