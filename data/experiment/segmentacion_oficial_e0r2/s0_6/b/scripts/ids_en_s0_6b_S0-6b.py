"""Los ids de unidades en `s0_6/b/` (U-SEG-OFICIAL, S0-6b; la regla única de S1-quater: en `s0_6/b/` solo pueden aparecer
los ids de las 40 filas y de las 286 leídas de S1-ter). Recorre todos los archivos del directorio, toma todo lo que tiene
forma de id (`<to>::…`) y controla que cada uno sea de una leída (`mostradas_S1ter`, del diseño sellado de S1-quater,
con la E0 de S1-ter y el orden sellado). No imprime ningún id que no sea de una leída: de esos, solo la cuenta y el
archivo. Sale con 1 si hay alguno.

Uso: python -B ids_en_s0_6b_S0-6b.py --dir <s0_6/b> --comun <dir de comun_S1quater.py> --orden <orden_lectura_S1ter.json>
       --s1ter <E0 de S1-ter> --out <json>
"""
import argparse
import json
import re
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("dir", "comun", "orden", "s1ter", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.comun))
import comun_S1quater as Q     # noqa: E402

orden = json.loads(Q.leer_sellado(a.orden, Q.SHA_ORDEN_S1TER, "el orden de S1-ter"))
leidas = set(Q.mostradas_S1ter(orden, Q.E0(a.s1ter)))
RX = re.compile(r"\b[a-z][a-z0-9_]*::[A-Za-z0-9_.]+(?:::[A-Za-z0-9_.]+)*")
por_archivo, fuera = {}, {}
for p in sorted(a.dir.rglob("*")):
    if not p.is_file():
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    ids = {m.rstrip(".") for m in RX.findall(t)}
    rel = str(p.relative_to(a.dir))
    if ids:
        por_archivo[rel] = len(ids)
    otros = [i for i in ids if i not in leidas]
    if otros:
        fuera[rel] = len(otros)
res = {"leidas": len(leidas), "archivos_con_ids": por_archivo, "ids_que_no_son_leidas_por_archivo": fuera,
       "ids_que_no_son_leidas": sum(fuera.values())}
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(res, ensure_ascii=False))
sys.exit(1 if fuera else 0)
