"""Compara una salida de E0 con un manifiesto de salida sellado (el de S0-5b: `sha256` por archivo), archivo por archivo
(U-SEG-OFICIAL, S0-6a-bis; solo lectura). Uso: python -B comparar_con_manifiesto_S0-6a-bis.py <dir> <manifiesto.json>"""
import hashlib
import json
import sys
from pathlib import Path

d, m = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
fa = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file()}
fb = {n: v["sha256"] for n, v in m["sha256"].items()}
dist = sorted(n for n in set(fa) | set(fb) if fa.get(n) != fb.get(n))
print(f"{len(fa)} archivos en la salida y {len(fb)} en el manifiesto; distintos {len(dist)}")
print("distintos:", dist)
print("unidades en la salida:", sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in d.glob("chunks_*.json")),
      "; en el manifiesto:", m["unidades"])
