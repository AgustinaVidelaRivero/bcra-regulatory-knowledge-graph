"""U-REAPL: el gate de un paso para el paquete, sin contenido de nodos: por regla de shapes, el resultado, la severidad y los conteos,
sin los textos de resumen (algunos llevan ids) y con cada lista de textos de los conteos (S18, S20, S24 y S25 listan ids o labels)
cambiada por su cantidad y el sha256 de la lista ordenada; la suite, por ítem, su estado; y la regresión.
Uso: python3 -I -B gate_sin_resumenes.py <gate.json> <salida>"""
import hashlib
import json
import sys


def sin_listas(x):
    if isinstance(x, dict):
        return {k: sin_listas(v) for k, v in x.items()}
    if isinstance(x, list) and x and all(isinstance(v, str) for v in x):
        return {"n": len(x), "sha256": hashlib.sha256("\n".join(sorted(x)).encode("utf-8")).hexdigest()}
    if isinstance(x, list):
        return [sin_listas(v) for v in x]
    return x


g = json.load(open(sys.argv[1], encoding="utf-8"))
for k in ("shapes_e0_del_grafo", "shapes_e0_con_partes"):
    g[k]["reglas"] = {r: {"result": v["result"], "severidad": v["severidad"], "conteos": sin_listas(v["conteos"])}
                      for r, v in g[k]["reglas"].items()}
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(g, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
