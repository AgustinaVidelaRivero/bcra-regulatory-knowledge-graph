"""Compara dos salidas de E0 archivo por archivo (los de primer nivel), por sha256, y cuenta las unidades de la primera
(U-SEG-OFICIAL, S0-6a; solo lectura). Uso: python -B comparar_archivos_S0-6a.py <dir a> <dir b>"""
import hashlib
import json
import sys
from pathlib import Path

a, b = Path(sys.argv[1]), Path(sys.argv[2])
fa = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.iterdir() if p.is_file()}
fb = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in b.iterdir() if p.is_file()}
dist = sorted(n for n in set(fa) | set(fb) if fa.get(n) != fb.get(n))
print(f"{len(fa)} y {len(fb)} archivos; distintos {len(dist)}; iguales {len(set(fa) & set(fb)) - len([n for n in dist if n in fa and n in fb])}")
print("distintos:", dist)
print("unidades en a:", sum(len(json.loads(p.read_text(encoding="utf-8"))) for p in a.glob("chunks_*.json")))
