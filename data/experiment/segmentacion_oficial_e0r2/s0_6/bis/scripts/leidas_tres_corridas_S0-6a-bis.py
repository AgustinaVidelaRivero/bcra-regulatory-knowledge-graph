"""Las 286 unidades leídas en S1-ter en tres E0: la de S1-ter, la de la primera corrida de S0-6a y la de esta etapa
(U-SEG-OFICIAL, S0-6a-bis; USD 0, sin API; solo lectura). Las unidades leídas salen del orden sellado de S1-ter y de su
E0 (`mostradas_S1ter`, del diseño sellado de S1-quater, sin cambios), igual que en `../scripts/control_leidas_S0-6a.py`.

Uso: python -B leidas_tres_corridas_S0-6a-bis.py --comun <dir de comun_S1quater.py> --orden <orden_lectura_S1ter.json>
       --s1ter <E0 de S1-ter> --primera <E0 de la primera corrida> --nueva <E0 de esta etapa> --out <json>

Por unidad, el corte (id, sha256 propio y páginas) y la herencia, comparados de a pares: esta etapa contra S1-ter y
contra la primera corrida. Clases: igual a las dos; igual a S1-ter (la primera la cambiaba y esta vuelve); igual a la
primera (el cambio de la primera sigue); distinta de las dos. Solo ids de unidades leídas, sin texto.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ap = argparse.ArgumentParser()
for k in ("comun", "orden", "s1ter", "primera", "nueva", "out"):
    ap.add_argument(f"--{k}", type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.comun))
import comun_S1quater as Q     # noqa: E402  (sin cambios: mostradas_S1ter, la E0 y el orden sellado)

orden = json.loads(Q.leer_sellado(a.orden, Q.SHA_ORDEN_S1TER, "el orden de S1-ter"))
e = {"s1ter": Q.E0(a.s1ter), "primera": Q.E0(a.primera), "nueva": Q.E0(a.nueva)}
leidas = Q.mostradas_S1ter(orden, e["s1ter"])
cache: dict = {}


def unidad(k: str, uid: str):
    to = uid.split("::")[0]
    if (k, to) not in cache:
        cache[(k, to)] = {c["id"]: c for c in e[k].chunks(to)}
    return cache[(k, to)].get(uid)


def corte(c):
    return None if c is None else (c["sha256_propio"], c["paginas"])


def herencia(c):
    return None if c is None else c["herencia"]


filas = []
for uid, etapa in leidas.items():
    s, p, n = (unidad(k, uid) for k in ("s1ter", "primera", "nueva"))
    f = {"id": uid, "etapa": etapa}
    for campo, fn in (("corte", corte), ("herencia", herencia)):
        igual_s, igual_p = fn(n) == fn(s), fn(n) == fn(p)
        f[campo] = ("igual_a_las_dos" if igual_s and igual_p else "igual_a_S1ter" if igual_s
                    else "igual_a_la_primera" if igual_p else "distinta_de_las_dos")
    filas.append(f)
res = {"leidas": len(filas),
       "corte": dict(Counter(f["corte"] for f in filas)),
       "herencia": dict(Counter(f["herencia"] for f in filas)),
       "cambian_contra_S1ter": sum(1 for f in filas
                                   if not (f["corte"] in ("igual_a_las_dos", "igual_a_S1ter")
                                           and f["herencia"] in ("igual_a_las_dos", "igual_a_S1ter"))),
       "cambian_contra_la_primera": sum(1 for f in filas
                                        if not (f["corte"] in ("igual_a_las_dos", "igual_a_la_primera")
                                                and f["herencia"] in ("igual_a_las_dos", "igual_a_la_primera"))),
       "unidades": [f for f in filas if f["corte"] != "igual_a_las_dos" or f["herencia"] != "igual_a_las_dos"]}
a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "unidades"}, ensure_ascii=False))
