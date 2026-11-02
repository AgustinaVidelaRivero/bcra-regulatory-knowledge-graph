"""rutas_que_difieren_mesa.py — Mesa, §387 (01/11/2026): si una salida reproducida no da el sha256 de la de la autora, qué rutas de
claves difieren entre los dos JSON. Imprime solo las rutas (con los índices de las listas como [i]) y cuántas son: ningún valor.
  python3 -I -B rutas_que_difieren_mesa.py <json de la autora> <json reproducido>
"""
import json
import sys
from pathlib import Path


def rutas(a, b, ruta=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                yield f"{ruta}.{k} (solo en {'la reproducida' if k in b else 'la de la autora'})"
            else:
                yield from rutas(a[k], b[k], f"{ruta}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield f"{ruta} (largos distintos)"
        for i, (x, y) in enumerate(zip(a, b)):
            yield from rutas(x, y, f"{ruta}[{i}]")
    elif a != b:
        yield ruta


A, B = (json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:3])
d = list(rutas(A, B))
print(f"    rutas que difieren: {len(d)}")
for r in d[:40]:
    print("    " + r)
