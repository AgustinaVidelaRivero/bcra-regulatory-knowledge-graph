"""S0-1 bis: tablas serializadas de una salida de E0 (`serializacion.serializada` en `tablas_<to>.json`), en total y
por TO para los TOs pedidos. Solo lectura. Uso: python -B tablas_serializadas.py <dir de E0> [tos,coma]"""
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
tos = sys.argv[2].split(",") if len(sys.argv) > 2 else []
tot = ser = 0
por = {}
for p in sorted(d.glob("tablas_*.json")):
    t = json.loads(p.read_text(encoding="utf-8"))
    n = sum(1 for x in t["tablas"] if (x.get("serializacion") or {}).get("serializada"))
    tot += len(t["tablas"])
    ser += n
    if t["to"] in tos:
        por[t["to"]] = [n, len(t["tablas"])]
print(json.dumps({"e0": d.name, "tablas": tot, "serializadas": ser, "por_to_serializadas_de": por}))
