"""S0-2 de U-SEG-OFICIAL: qué clase de cambio produce cada regla de S0 sobre las unidades de E0, para asignarle su
fila de la tabla de reprocesamiento (data/experiment/mantenimiento/tabla_reprocesamiento.md). Por regla, compara la
corrida con esa regla sola (o, para el acompañamiento T, la corrida con todas contra la corrida sin T) con su
referencia, unidad por unidad: ids nuevos y que desaparecen; unidades comunes cuyo texto propio cambia (F01); las
que solo cambian la herencia, por tipo de tramo (encabezado: F02; intro, cierre, chapeau, intersticial: F03); las que
solo cambian sus marcas (F04); y las que solo cambian páginas, propias o de un tramo heredado con el mismo texto,
o los metadatos de una parte (F05). Solo lectura.

Uso: python -B filas_por_regla.py <runs> <base> <tos,coma> <salida.json> regla=<dir>[:<ref>] ...
(sin <ref>, la referencia es la base)"""
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

runs, base, tos, sal = Path(sys.argv[1]), sys.argv[2], sys.argv[3].split(","), Path(sys.argv[4])
pares = [(a.split("=")[0], *(a.split("=")[1].split(":") + [base])[:2]) for a in sys.argv[5:]]


def leer(run: str, to: str) -> dict:
    p = runs / run / f"chunks_{to}.json"
    if not p.exists():
        p = runs / run / "por_to" / to / f"chunks_{to}.json"
    return {c["id"]: c for c in json.loads(p.read_text(encoding="utf-8"))}


def tramos(c: dict) -> Counter:
    return Counter((t["tipo"], t["texto"]) for t in c.get("herencia", []))


out = OrderedDict()
for regla, d, ref in pares:
    cuenta, tos_regla = Counter(), set()
    for to in tos:
        a, b = leer(ref, to), leer(d, to)
        n, x = set(b) - set(a), set(a) - set(b)
        cuenta["ids_nuevos"] += len(n)
        cuenta["ids_que_desaparecen"] += len(x)
        for k in set(a) & set(b):
            ca, cb = a[k], b[k]
            if ca == cb:
                continue
            if ca["sha256_propio"] != cb["sha256_propio"]:
                cuenta["F01_texto_propio"] += 1
            elif ca["herencia"] != cb["herencia"]:
                dif = (tramos(ca) - tramos(cb)) + (tramos(cb) - tramos(ca))
                tipos = {t for t, _ in dif}
                if "encabezado" in tipos:
                    cuenta["F02_herencia_encabezado"] += 1
                if tipos - {"encabezado"}:
                    cuenta["F03_herencia_prosa"] += 1
                if not tipos:
                    cuenta["F05_paginas_de_la_herencia"] += 1
            elif ca["flags"] != cb["flags"]:
                cuenta["F04_marcas"] += 1
            elif ca["paginas"] != cb["paginas"]:
                cuenta["F05_paginas"] += 1
            elif ca.get("sub_chunk") != cb.get("sub_chunk"):
                cuenta["F05_metadatos_de_parte"] += 1
            else:
                cuenta["otro_campo"] += 1
        if n or x or any(a[k] != b[k] for k in set(a) & set(b)):
            tos_regla.add(to)
    out[regla] = OrderedDict([("referencia", ref), ("corrida", d), ("tos", sorted(tos_regla)), ("cambios", dict(cuenta))])
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
for r, v in out.items():
    print(f"{r:6} {len(v['tos']):2} TOs {v['cambios']}")
