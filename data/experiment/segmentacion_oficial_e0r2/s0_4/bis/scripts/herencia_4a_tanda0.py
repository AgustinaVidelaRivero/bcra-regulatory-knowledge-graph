"""S0-4a-bis (U-SEG-OFICIAL), USD 0, solo lectura: para los puntos de la clase 4a de la tanda 0 (censo de S0-4a,
`tanda0_limite_declarado`), ¿la oración que E0 tomó como título está en el texto heredado de las unidades hijas, o
sea, la veía E1? La oración es el título del punto (como lo leyó E0, `estructura_<to>.json`) más los renglones de su
intro hasta el primero que termina en punto o en dos puntos (el criterio de `e0_lib.clase_titulo_4ab`). Para cada
unidad descendiente del punto (`chunks_<to>.json` de `salida_tanda0_r2b/`, ids que empiezan con «<to>::<punto>.»),
se busca, con los espacios y saltos de renglón normalizados, el título en sus tramos de herencia y la continuación en
sus tramos de herencia. Un punto es «sí» si todas sus unidades descendientes tienen las dos partes; si no, «no», con
lo que falta. Uso: python -B herencia_4a_tanda0.py <censo_4ab_sobre_S0-3.json> <salida_tanda0_r2b> <salida.json>"""
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

censo, d, salida = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
casos = [c for c in json.loads(censo.read_text(encoding="utf-8"))["tanda0_limite_declarado"]["casos"]
         if c["clase"] == "4a"]


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def nodo(est: dict, num: str):
    def rec(n):
        if n["tipo"] == "punto" and n["numero"] == num:
            return n
        for h in n["hijos"]:
            r = rec(h)
            if r is not None:
                return r
        return None
    for s in est["secciones"]:
        r = rec(s)
        if r is not None:
            return r
    return None


cache_est, cache_ch, filas = {}, {}, []
for c in casos:
    to, num = c["to"], c["unidad"]
    est = cache_est.setdefault(to, json.loads((d / f"estructura_{to}.json").read_text(encoding="utf-8")))
    ch = cache_ch.setdefault(to, json.loads((d / f"chunks_{to}.json").read_text(encoding="utf-8")))
    n = nodo(est, num)
    intro = [s for s in n["segmentos"] if s["rol"] == "intro"]
    lin = intro[0]["texto"].split("\n")
    orac = [lin[0].rstrip()]
    for x in lin[1:]:
        if orac[-1].endswith((".", ":")):
            break
        orac.append(x.rstrip())
    titulo, cont = n["titulo"].rstrip(), "\n".join(orac)
    desc = [u for u in ch if u["id"].startswith(f"{to}::{num}.")]
    faltan = []
    for u in desc:
        her = norm(" ".join(t["texto"] for t in u["herencia"]))
        f = [p for p, x in (("titulo", titulo), ("continuacion", cont)) if norm(x) not in her]
        if f:
            faltan.append({"unidad": u["id"], "falta": f})
    filas.append(OrderedDict([("to", to), ("punto", num), ("titulo", titulo), ("continuacion", cont),
                              ("unidades_descendientes", len(desc)), ("sin_la_oracion", faltan),
                              ("e1_la_veia", bool(desc) and not faltan)]))
si = [f for f in filas if f["e1_la_veia"]]
no = [f for f in filas if not f["e1_la_veia"]]
out = OrderedDict([("criterio", __doc__.split("Uso:")[0].strip()), ("puntos", len(filas)), ("si", len(si)),
                   ("no", len(no)), ("no_detalle", [{k: f[k] for k in ("to", "punto", "titulo", "continuacion",
                                                                       "unidades_descendientes", "sin_la_oracion")}
                                                    for f in no]),
                   ("por_to", OrderedDict((t, {"si": sum(f["to"] == t for f in si), "no": sum(f["to"] == t for f in no)})
                                          for t in sorted({f["to"] for f in filas}))),
                   ("detalle", filas)])
salida.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(len(filas), "puntos:", len(si), "sí,", len(no), "no")
