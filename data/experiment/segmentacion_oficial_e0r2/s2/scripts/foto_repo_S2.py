"""Foto sha256 del repo entero, sin .git (U-SEG-OFICIAL, S2; solo lectura).

Uso: python -B foto_repo_S2.py <repo> <salida.json>
     python -B foto_repo_S2.py --comparar <antes.json> <despues.json>

- Cada archivo regular: sha256 y bytes.
- Los `.env`, `.env.*` y `*.env`, y los archivos cuyo nombre empieza con `NO_ABRIR_`: solo tamaño y fecha de
  modificación (no se abren).
- Los enlaces simbólicos: su destino (`os.readlink`), sin seguirlos.
- Las rutas van relativas a <repo>.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time


def es_env(nombre: str) -> bool:
    return nombre == ".env" or nombre.startswith(".env.") or nombre.endswith(".env")


def sin_abrir(nombre: str) -> bool:
    return es_env(nombre) or nombre.startswith("NO_ABRIR_")


def foto(repo: str) -> dict:
    out: dict[str, dict] = {}
    for raiz, dirs, archivos in os.walk(repo):
        rel_raiz = os.path.relpath(raiz, repo)
        if rel_raiz == ".":
            dirs[:] = [d for d in dirs if d != ".git"]
        dirs.sort()
        for d in list(dirs):
            p = os.path.join(raiz, d)
            if os.path.islink(p):
                out[os.path.normpath(os.path.join(rel_raiz, d))] = {"enlace": os.readlink(p)}
                dirs.remove(d)
        for n in sorted(archivos):
            p = os.path.join(raiz, n)
            rel = os.path.normpath(os.path.join(rel_raiz, n))
            if os.path.islink(p):
                out[rel] = {"enlace": os.readlink(p)}
                continue
            st = os.stat(p)
            if sin_abrir(n):
                out[rel] = {"bytes": st.st_size, "mtime": st.st_mtime, "sin_abrir": True}
                continue
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
            out[rel] = {"sha256": h.hexdigest(), "bytes": st.st_size}
    return out


def main() -> None:
    if sys.argv[1] == "--comparar":
        a = json.load(open(sys.argv[2], encoding="utf-8"))["archivos"]
        b = json.load(open(sys.argv[3], encoding="utf-8"))["archivos"]
        nuevos = sorted(set(b) - set(a))
        borrados = sorted(set(a) - set(b))
        cambiados = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        print(json.dumps({"antes": len(a), "despues": len(b), "nuevos": nuevos, "borrados": borrados,
                          "cambiados": cambiados}, ensure_ascii=False, indent=1))
        return
    repo, salida = sys.argv[1], sys.argv[2]
    t0 = time.strftime("%Y-%m-%d %H:%M:%S")
    f = foto(repo)
    t1 = time.strftime("%Y-%m-%d %H:%M:%S")
    json.dump({"inicio": t0, "fin": t1, "n": len(f),
               "sin_abrir": sum(1 for v in f.values() if v.get("sin_abrir")),
               "enlaces": sum(1 for v in f.values() if "enlace" in v), "archivos": f},
              open(salida, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(t0, t1, len(f), "entradas")


if __name__ == "__main__":
    main()
