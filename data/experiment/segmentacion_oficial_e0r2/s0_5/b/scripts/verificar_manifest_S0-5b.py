"""Verifica un paquete de revisión contra su manifest.txt: sha256 y bytes de cada archivo listado, y ningún archivo
sin listar. Uso: python -B verificar_manifest.py <dir del paquete>"""
import hashlib
import sys
from pathlib import Path

P = Path(sys.argv[1])
filas = [l for l in (P / "manifest.txt").read_text(encoding="utf-8").splitlines()[2:] if l.strip()]
ok, mal, listados = 0, [], set()
for l in filas:
    sha, nbytes, resto = l.split("  ", 2)
    nombre = resto.split(" — ", 1)[0]
    listados.add(nombre)
    p = P / nombre
    if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == sha and p.stat().st_size == int(nbytes):
        ok += 1
    else:
        mal.append(nombre)
sin_listar = sorted(p.name for p in P.iterdir() if p.name != "manifest.txt" and p.name not in listados)
print(f"{P}: {ok} de {len(filas)} iguales a su manifest.txt (sha256 y bytes); distintos o ausentes: {mal}; "
      f"sin listar: {sin_listar}")
sys.exit(0 if ok == len(filas) and not mal and not sin_listar else 1)
