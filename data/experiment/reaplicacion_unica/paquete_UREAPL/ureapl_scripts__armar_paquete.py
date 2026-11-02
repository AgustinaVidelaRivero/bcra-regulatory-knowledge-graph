"""U-REAPL: arma el paquete `revision_UREAPL/` desde una lista «origen<TAB>nombre en el paquete<TAB>descripción» (CLAUDE.md, §4.g).

Copia cada archivo con su nombre único y escribe `manifest.txt`: «sha256  nombre  descripción» por archivo; los `NO_ABRIR_` van solo
con su sha256 y su nombre, sin descripción. Frena si un nombre se repite o un origen no existe. No abre el contenido de ningún archivo
más que para copiarlo y hashearlo.
Uso: python3 -I -B armar_paquete.py <lista.tsv> <carpeta del paquete>
"""
import hashlib
import shutil
import sys
from pathlib import Path

lista, dest = Path(sys.argv[1]), Path(sys.argv[2])
filas = [x.split("\t") for x in lista.read_text(encoding="utf-8").splitlines() if x.strip()]
nombres = [f[1] for f in filas]
if len(set(nombres)) != len(nombres):
    raise SystemExit("FRENO: hay nombres repetidos en el paquete")
dest.mkdir(parents=True, exist_ok=True)
lineas = []
for origen, nombre, *desc in filas:
    o = Path(origen)
    if not o.is_file():
        raise SystemExit(f"FRENO: no existe el origen de {nombre}")
    shutil.copyfile(o, dest / nombre)
    h = hashlib.sha256((dest / nombre).read_bytes()).hexdigest()
    lineas.append(f"{h}  {nombre}" + ("" if nombre.startswith("NO_ABRIR_") else f"  {desc[0] if desc else ''}"))
(dest / "manifest.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
print(len(lineas), "archivos; manifest", hashlib.sha256((dest / "manifest.txt").read_bytes()).hexdigest())
