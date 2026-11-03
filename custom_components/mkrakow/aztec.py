"""Rysowanie kodu Aztec do PNG (biblioteka aztec_code_generator + Pillow)."""

from __future__ import annotations

import io

from aztec_code_generator import AztecCode


def png(tresc: str, modul: int = 8, ramka: int = 4) -> bytes:
    kod = AztecCode(tresc)
    obraz = kod.image(module_size=modul, border=ramka)
    bufor = io.BytesIO()
    obraz.save(bufor, format="PNG")
    return bufor.getvalue()
