"""Foto sha256 del repo entero, sin .git y sin excluir ninguna otra ruta (R0, fase 2; solo lectura).

Igual que segmentacion_oficial_e0r2/s0_6/bis/scripts/foto_repo_entero_S0-6a-bis.py, salvo los archivos de entorno
(nombre `.env`, `.env.*` o `*.env`, cláusula de la mesa del 13/10/2026): esos NO se abren; se registran con os.stat,
solo por su tamaño y su fecha de modificación. Los enlaces simbólicos se registran por su destino (no se siguen).
El JSON tiene la forma de la foto de S0-6a-bis ({"tomada", "archivos"}), así que su --comparar sirve igual.
Uso: python -B foto_repo_sin_env_R0.py <repo> <salida.json>
"""
import fnmatch
import hashlib
import json
import os
import sys
import time
from pathlib import Path

PATRONES_ENV = (".env", ".env.*", "*.env")


def es_env(nombre: str) -> bool:
    return any(fnmatch.fnmatch(nombre, p) for p in PATRONES_ENV)


def foto(repo: Path) -> tuple[dict, list]:
    out, envs = {}, []
    for raiz, dirs, archivos in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if not (Path(raiz) == repo and d == ".git"))
        for a in sorted(archivos):
            p = Path(raiz) / a
            rel = p.relative_to(repo).as_posix()
            if p.is_symlink():
                out[rel] = "enlace:" + os.readlink(p)
                continue
            if es_env(a):
                st = os.stat(p)
                out[rel] = f"env_sin_abrir:tamaño={st.st_size};mtime={int(st.st_mtime)}"
                envs.append(rel)
                continue
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
            out[rel] = h.hexdigest()
    return out, envs


if __name__ == "__main__":
    repo, sal = Path(sys.argv[1]), Path(sys.argv[2])
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    f, envs = foto(repo)
    sal.write_text(json.dumps({"tomada": t, "archivos": f}, ensure_ascii=False, indent=0) + "\n")
    print(len(f), "archivos", t, "| de entorno, registrados sin abrir:", len(envs))
