"""Testy wyboru biletu (bez Home Assistanta): python -m unittest discover tests"""

import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

_SCIEZKA = Path(__file__).parents[1] / "custom_components" / "mkrakow" / "bilety.py"
_spec = importlib.util.spec_from_file_location("bilety", _SCIEZKA)
bilety = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bilety)

TERAZ = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)


def _bilet(od, do, status="active", nazwa="Bilet ulg. 3-mies. metropolitalny st. I+II"):
    return {
        "status": status,
        "startDate": od,
        "endDate": do,
        "commodityName": nazwa,
        "monthsPeriod": 3,
    }


class TestBilety(unittest.TestCase):
    def test_aktywny(self):
        w = bilety.podsumuj([_bilet("2026-09-01T22:00:00Z", "2026-12-01T22:59:59Z")], TERAZ)
        self.assertEqual(w["waznosc"], datetime(2026, 12, 1, 22, 59, 59, tzinfo=timezone.utc))
        self.assertEqual(w["bilet"]["nazwa"], "Bilet ulg. 3-mies. metropolitalny st. I+II")
        self.assertEqual(w["aktualny"]["do"], "2026-12-01T22:59:59Z")

    def test_kupiony_z_wyprzedzeniem_przedluza(self):
        w = bilety.podsumuj(
            [
                _bilet("2026-09-01T22:00:00Z", "2026-12-01T22:59:59Z"),
                _bilet("2026-12-01T23:00:00Z", "2027-03-01T22:59:59Z", status="inactive"),
            ],
            TERAZ,
        )
        self.assertEqual(w["waznosc"].year, 2027)
        self.assertEqual(w["aktualny"]["do"], "2026-12-01T22:59:59Z")

    def test_wygasly_i_zwrocony_pomijane(self):
        w = bilety.podsumuj(
            [
                _bilet("2026-06-01T22:00:00Z", "2026-09-01T21:59:59Z", status="expired"),
                _bilet("2026-10-01T22:00:00Z", "2027-01-01T22:59:59Z", status="returned"),
            ],
            TERAZ,
        )
        self.assertIsNone(w["waznosc"])
        self.assertIsNone(w["bilet"])
        self.assertEqual(len(w["wszystkie"]), 2)

    def test_pusta_lista(self):
        self.assertIsNone(bilety.podsumuj([], TERAZ)["waznosc"])


if __name__ == "__main__":
    unittest.main()
