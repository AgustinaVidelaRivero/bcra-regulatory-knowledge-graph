"""Foto sha256 del árbol de trabajo del repo (sin .git, .venv ni .venv-app): una línea por archivo, «sha256  ruta», ordenada.

Uso: python3 -I -B foto_repo.py <raíz del repo> <salida>
Imprime la cantidad de archivos y el sha256 de la foto. No abre el contenido de ningún archivo más que para hashearlo.
"""
import hashlib
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

EXCLUIR = {".git", ".venv", ".venv-app"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rutas(raiz):
    for d, subdirs, archivos in os.walk(raiz):
        if Path(d) == raiz:
            subdirs[:] = [s for s in subdirs if s not in EXCLUIR]
        subdirs.sort()
        for a in sorted(archivos):
            p = Path(d) / a
            if p.is_symlink():
                yield p, "ENLACE"
            elif p.is_file():
                yield p, None


def main():
    raiz, salida = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    lista = list(rutas(raiz))
    archivos = [p for p, e in lista if e is None]
    with ProcessPoolExecutor() as ex:
        hs = dict(zip(archivos, ex.map(sha, archivos, chunksize=64)))
    lineas = sorted(f"{hs.get(p, e)}  {p.relative_to(raiz)}" for p, e in lista)
    texto = "\n".join(lineas) + "\n"
    salida.write_text(texto, encoding="utf-8")
    print(len(lineas), "archivos;", sum(1 for _, e in lista if e), "enlaces; sha256 de la foto:",
          hashlib.sha256(texto.encode()).hexdigest())


if __name__ == "__main__":
    main()
