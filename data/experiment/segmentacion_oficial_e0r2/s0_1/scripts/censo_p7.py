"""Punto 7 de S0-1 (solo lectura): intersticiales de e0-r2 cuya primera línea es un número de punto de 2 o más
niveles (`^\\d+(\\.\\d+)+\\.?(\\s|$)`), con TO, id, unidad a la que quedan atribuidos y esa línea.
Uso: python -B censo_p7.py <dir de E0> <salida.json>"""
import json, re, sys
from collections import Counter
from pathlib import Path
RE = re.compile(r"^\d+(\.\d+)+\.?(\s|$)")
d, sal = Path(sys.argv[1]), Path(sys.argv[2])
filas = []
for p in sorted(d.glob("chunks_*.json")):
    for c in json.loads(p.read_text(encoding="utf-8")):
        if c["tipo"] == "mini_chunk" and c.get("rol_bloque") == "intersticial":
            l0 = c["texto"].split("\n")[0].strip()
            if RE.match(l0):
                filas.append({"to": c["to"], "id": c["id"], "unidad": c["unidad"],
                              "atribuido_a": "seccion" if c["unidad"].startswith("S") else "punto", "primera_linea": l0})
out = {"e0": d.name, "total": len(filas), "por_to": dict(Counter(f["to"] for f in filas)),
       "por_to_y_unidad": {f"{t}::{u}": n for (t, u), n in sorted(Counter((f["to"], f["unidad"]) for f in filas).items())},
       "atribuidos_a": dict(Counter(f["atribuido_a"] for f in filas)), "filas": filas}
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "filas"}, ensure_ascii=False))
