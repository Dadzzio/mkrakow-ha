"""Rysowanie kodu Aztec do PNG (biblioteka aztec_code_generator + Pillow)."""

from __future__ import annotations

import io

from aztec_code_generator import AztecCode


def rodzaj(tresc: str) -> str:
    """Opis formatu treści bez ujawniania jej (do diagnostyki)."""
    t = tresc.strip()
    if t.startswith("data:image"):
        return "data-uri"
    if t.startswith("iVBOR"):
        return "png-base64"
    if t.startswith("PHN2Zy") or t.startswith("<svg"):
        return "svg"
    if all(c in "0123456789abcdefABCDEF" for c in t):
        return f"hex-{len(t)}"
    return f"tekst-{len(t)}"


def png(tresc: str, modul: int = 8, ramka: int = 4) -> bytes:
    import base64

    t = tresc.strip()
    if t.startswith("data:image/png;base64,"):
        return base64.b64decode(t.split(",", 1)[1])
    if t.startswith("iVBOR"):
        return base64.b64decode(t)
    kod = AztecCode(t)
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
