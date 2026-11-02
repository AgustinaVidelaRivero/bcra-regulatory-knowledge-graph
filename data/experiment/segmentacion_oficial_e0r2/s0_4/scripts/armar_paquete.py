"""Arma el paquete de revisión: copia cada archivo de una lista (origen, nombre en el paquete, descripción) al directorio
del paquete y escribe `manifest.txt` con el sha256, el tamaño y la descripción de cada uno (CLAUDE.md §4.g).
Uso: python -B armar_paquete.py <lista.tsv> <dir paquete>   (lista: origen<TAB>nombre<TAB>descripción; rutas relativas
al directorio desde el que se corre)"""
import hashlib
import shutil
import sys
from pathlib import Path

lista, dest = Path(sys.argv[1]), Path(sys.argv[2])
if dest.exists():
    shutil.rmtree(dest)
dest.mkdir(parents=True)
filas = []
nombres = set()
for ln in lista.read_text(encoding="utf-8").splitlines():
    if not ln.strip() or ln.startswith("#"):
        continue
    origen, nombre, desc = ln.split("\t")
    if nombre in nombres:
        raise SystemExit(f"nombre repetido en el paquete: {nombre}")
    nombres.add(nombre)
    shutil.copyfile(origen, dest / nombre)
    b = (dest / nombre).read_bytes()
    filas.append((nombre, hashlib.sha256(b).hexdigest(), len(b), desc))
filas.sort()
with open(dest / "manifest.txt", "w", encoding="utf-8") as fh:
    fh.write(f"Paquete de revisión: {dest.name} — {len(filas)} archivos (más este manifest)\n")
    fh.write("sha256  bytes  archivo — descripción\n")
    for n, h, sz, d in filas:
        fh.write(f"{h}  {sz}  {n} — {d}\n")
print(len(filas), "archivos en", dest)
