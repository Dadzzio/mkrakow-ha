"""Testy wyciągania stałych z HAR (bez Home Assistanta)."""

import importlib.util
import json
import unittest
from pathlib import Path

_SCIEZKA = Path(__file__).parents[1] / "custom_components" / "mkrakow" / "har.py"
_spec = importlib.util.spec_from_file_location("har", _SCIEZKA)
har = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(har)


def _wpis(url, **naglowki):
    return {"request": {"url": url, "headers": [{"name": k, "value": v} for k, v in naglowki.items()]}}


def _har(*wpisy):
    return json.dumps({"log": {"entries": list(wpisy)}})


class TestHar(unittest.TestCase):
    def test_wszystkie_stale(self):
        w = har.stale_z_har(
            _har(
                _wpis("https://example.com/x", apikey="obcy"),
                _wpis("https://api.um.krakow.pl/mkrakow-sms/login", apikey="K", Authorization="Basic S"),
                _wpis("https://api.um.krakow.pl/mkrakow-oauth/token", apikey="K", Authorization="Basic C"),
                _wpis("https://api.um.krakow.pl/skk-tickets/tickets/list", Authorization="Bearer T"),
            )
        )
        self.assertEqual(w, {"apikey": "K", "auth_sms": "Basic S", "auth_klient": "Basic C"})

    def test_brak_i_revoke(self):
        w = har.stale_z_har(
            _har(_wpis("https://api.um.krakow.pl/mkrakow-oauth/revoke", apikey="K", authorization="Basic C"))
        )
        self.assertEqual(w, {"apikey": "K", "auth_klient": "Basic C"})

    def test_nie_json(self):
        with self.assertRaises(ValueError):
            har.stale_z_har("nie json")


if __name__ == "__main__":
    unittest.main()
