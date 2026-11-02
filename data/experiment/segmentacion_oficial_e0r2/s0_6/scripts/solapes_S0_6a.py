"""Solapes de texto entre dos salidas de E0 de un TO (U-SEG-OFICIAL, S0-6a; solo lectura): para listar en qué unidades
nuevas quedó el texto de una unidad vieja. Dos unidades se solapan si comparten al menos un renglón de texto propio de
MIN_CHARS caracteres o más y una página. Es un listado de apoyo: no decide nada."""
from __future__ import annotations

MIN_CHARS = 20


def _renglones(c: dict) -> set[str]:
    return {r.strip() for r in c["texto"].split("\n") if len(r.strip()) >= MIN_CHARS}


def solapes(viejos: list[dict], nuevos: list[dict]) -> dict[str, list[str]]:
    """Por id nuevo, los ids viejos con los que comparte un renglón y una página."""
    idx: dict[str, list[dict]] = {}
    for c in viejos:
        for r in _renglones(c):
            idx.setdefault(r, []).append(c)
    out = {}
    for c in nuevos:
        pags = set(c.get("paginas") or [])
        out[c["id"]] = sorted({v["id"] for r in _renglones(c) for v in idx.get(r, ()) if pags & set(v.get("paginas") or [])})
    return out
