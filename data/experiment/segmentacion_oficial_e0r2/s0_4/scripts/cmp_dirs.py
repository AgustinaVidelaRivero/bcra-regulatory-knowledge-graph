"""Compara byte a byte los archivos *.json del primer nivel de dos directorios. Uso: cmp_dirs.py <a> <b> [--solo-de-b]
Con --solo-de-b compara solo los archivos que están en b (p. ej., los 25 de la tanda 0 dentro de los 152)."""
import sys
from pathlib import Path
a, b = Path(sys.argv[1]), Path(sys.argv[2])
fa = {p.name for p in a.glob("*.json")}
fb = {p.name for p in b.glob("*.json")}
nombres = sorted(fb) if "--solo-de-b" in sys.argv else sorted(fa | fb)
dist = [n for n in nombres if not (a / n).exists() or not (b / n).exists() or (a / n).read_bytes() != (b / n).read_bytes()]
print(f"{len(nombres)} archivos comparados; {len(nombres) - len(dist)} iguales; {len(dist)} distintos")
for n in dist[:40]:
    print("  distinto:", n)
