"""Comparación de dos salidas de E0 por TO (mismo criterio que `r2_codigo2/c2_e0.py`, `comparar_to`): ids nuevos y que
desaparecen, orden de los comunes, chunks que cambian y en qué campos, los que cambian solo en la herencia, y
renglones del texto propio que se ganan o se pierden en el TO.

Uso: python -B comparar_e0.py <dir base> <dir nuevo> <salida.json> [--tos a,b]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

CAMPOS_HERENCIA = {"herencia", "herencia_recortada", "chars_completo", "sha256_completo"}


def leer_chunks(d: Path, to: str) -> list[dict]:
    p = d / f"chunks_{to}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def comparar_to(cb: list[dict], cn: list[dict]) -> OrderedDict:
    ib, inn = [c["id"] for c in cb], [c["id"] for c in cn]
    db, dn = {c["id"]: c for c in cb}, {c["id"]: c for c in cn}
    cambian = OrderedDict()
    for i in ib:
        if i in dn and db[i] != dn[i]:
            cambian[i] = sorted(k for k in set(db[i]) | set(dn[i]) if db[i].get(k) != dn[i].get(k))
    tb = Counter(x for c in cb for x in (c.get("texto") or "").split("\n"))
    tn = Counter(x for c in cn for x in (c.get("texto") or "").split("\n"))
    return OrderedDict([
        ("chunks", [len(cb), len(cn)]),
        ("ids_nuevos", [i for i in inn if i not in db]),
        ("ids_que_desaparecen", [i for i in ib if i not in dn]),
        ("orden_igual_en_comunes", [i for i in ib if i in dn] == [i for i in inn if i in db]),
        ("cambian", cambian),
        ("cambian_solo_en_la_herencia", sorted(i for i, ks in cambian.items() if set(ks) <= CAMPOS_HERENCIA)),
        ("renglones_ganados", sorted((tn - tb).elements())),
        ("renglones_perdidos", sorted((tb - tn).elements()))])


def comparar(base: Path, nueva: Path, tos: list[str] | None = None) -> OrderedDict:
    if tos is None:
        tos = sorted({p.name[len("chunks_"):-len(".json")] for d in (base, nueva) for p in d.glob("chunks_*.json")})
    por_to = OrderedDict()
    for to in tos:
        r = comparar_to(leer_chunks(base, to), leer_chunks(nueva, to))
        if r["ids_nuevos"] or r["ids_que_desaparecen"] or not r["orden_igual_en_comunes"] or r["cambian"] \
                or r["renglones_ganados"] or r["renglones_perdidos"]:
            por_to[to] = r
    archivos_distintos = sorted(p.name for p in nueva.glob("*.json")
                                if not (base / p.name).exists() or (base / p.name).read_bytes() != p.read_bytes())
    resumen = OrderedDict([
        ("tos", len(tos)),
        ("tos_con_cambios", sorted(por_to)),
        ("tos_con_ids_que_cambian", sorted(t for t, r in por_to.items()
                                           if r["ids_nuevos"] or r["ids_que_desaparecen"]
                                           or not r["orden_igual_en_comunes"])),
        ("chunks_que_cambian_por_to", {t: len(r["cambian"]) for t, r in por_to.items() if r["cambian"]}),
        ("ids_nuevos_por_to", {t: len(r["ids_nuevos"]) for t, r in por_to.items() if r["ids_nuevos"]}),
        ("ids_que_desaparecen_por_to", {t: len(r["ids_que_desaparecen"]) for t, r in por_to.items()
                                        if r["ids_que_desaparecen"]}),
        ("renglones_ganados_por_to", {t: len(r["renglones_ganados"]) for t, r in por_to.items()
                                      if r["renglones_ganados"]}),
        ("renglones_perdidos_por_to", {t: len(r["renglones_perdidos"]) for t, r in por_to.items()
                                       if r["renglones_perdidos"]}),
        ("archivos_distintos", archivos_distintos)])
    return OrderedDict([("resumen", resumen), ("por_to", por_to)])


if __name__ == "__main__":
    base, nueva, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    tos = sys.argv[sys.argv.index("--tos") + 1].split(",") if "--tos" in sys.argv else None
    r = comparar(base, nueva, tos)
    sal.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(r["resumen"], ensure_ascii=False, indent=1))
