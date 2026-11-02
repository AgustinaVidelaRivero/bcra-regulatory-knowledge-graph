"""Comunes de los censos de S0-1: TOs de la partición, líneas cacheadas y la escalera de e0-r2 con el código de
una copia (solo lectura)."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def cargar_codigo(raiz: Path):
    for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking",):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import correr_e0 as CE  # noqa: PLC0415
    import e0_lib as E0  # noqa: PLC0415
    return CE, E0


def tos_particion(raiz: Path) -> list[str]:
    c = json.loads((raiz / "data/experiment/segmentacion_84/b584_particion/conteos_b584.json").read_text())
    return sorted(t for t, v in c.items() if isinstance(v, dict))


def paginas_de(cache: Path, to: str, E0) -> list:
    d = json.loads((cache / f"{to}.json").read_text(encoding="utf-8"))
    return [[E0.Linea(*x) for x in p] for p in d]


def parsear(CE, E0, to: str, paginas: list):
    """Escalera de e0-r2 más las reglas 1 y 2 post-parseo, como `correr_e0.correr`."""
    roles = E0.clasificar_paginas(paginas)
    res, roles, rep, modo, marc = CE.escalera_e0_r2(to, f"{to}.pdf", paginas, roles)
    res.reasignaciones_continuidad = E0.aplicar_continuidad_enumeracion(res)
    E0.corregir_fronteras_intra_palabra(res)
    return res, roles, modo, marc


def nodos(res):
    def rec(n):
        yield n
        for h in n.hijos:
            yield from rec(h)
    for s in res.secciones:
        yield from rec(s)
