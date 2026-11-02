"""Compara byte a byte los cinco archivos por TO (chunks, estructura, indice, tablas, pies) de dos corridas de E0, en
los TOs de una lista. Uso: python -B por_to_iguales.py <a> <b> <to,to,…>"""
import sys
from pathlib import Path
a, b, tos = Path(sys.argv[1]), Path(sys.argv[2]), [t for t in sys.argv[3].split(",") if t]
dist, n = [], 0
for to in tos:
    for pref in ("chunks", "estructura", "indice", "tablas", "pies"):
        n += 1
        pa, pb = a / f"{pref}_{to}.json", b / f"{pref}_{to}.json"
        if not (pa.exists() and pb.exists() and pa.read_bytes() == pb.read_bytes()):
            dist.append(f"{pref}_{to}.json")
print(f"{len(tos)} TOs, {n - len(dist)} de {n} archivos por TO iguales" + (f"; distintos: {dist}" if dist else ""))
