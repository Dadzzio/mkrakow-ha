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


def zaslepka(rozmiar: int = 552) -> bytes:
    """Szary obrazek „Naciśnij Pokaż bilet” – kod jest widoczny tylko po kliknięciu."""
    from PIL import Image, ImageDraw

    obraz = Image.new("RGB", (rozmiar, rozmiar), (240, 240, 240))
    d = ImageDraw.Draw(obraz)
    d.rectangle((8, 8, rozmiar - 9, rozmiar - 9), outline=(200, 200, 200), width=4)
    tekst = "Kod biletu ukryty\n(kliknij przycisk)"  # bez polskich znaków: domyślna czcionka
    try:
        from PIL import ImageFont

        czcionka = ImageFont.load_default(size=44)
    except (TypeError, OSError):
        czcionka = None
    d.multiline_text(
        (rozmiar / 2, rozmiar / 2),
        tekst,
        fill=(90, 90, 90),
        font=czcionka,
        anchor="mm",
        align="center",
        spacing=12,
    )
    bufor = io.BytesIO()
    obraz.save(bufor, format="PNG")
    return bufor.getvalue()
