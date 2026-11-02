"""Control de que el repo no cambie (CLAUDE.md §4.l), con las exclusiones de la convivencia con U-REEXT-T0.

Uso: python -B snapshot_repo.py <repo> <salida.json>          toma la foto
     python -B snapshot_repo.py --comparar <a.json> <b.json>   compara dos fotos

Recorre todo el repo salvo .git y las rutas que U-REEXT-T0 escribe mientras corre (declaradas abajo): no
entra en ellas, ni siquiera para listar. Los archivos de base de datos (.db, .db-wal, .db-shm, .sqlite) fuera de
esas rutas no se abren: se registra solo su stat (tamaño y mtime). Los demás, sha256 del contenido.
"""
import hashlib
import json
import os
import sys

EXCLUIDAS = (
    "data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b",
    "data/experiment/reextraccion_v2/e1_extractor/cache",
    "data/experiment/reextraccion_v2/e3_verificador/cache",
    "logs",
    "data/experiment/reext_t0",
    "data/experiment/neo4j/volumen",
)
SOLO_STAT = (".db", ".db-wal", ".db-shm", ".db-journal", ".sqlite")


def foto(repo: str) -> dict:
    out = {}
    for raiz, dirs, archivos in os.walk(repo):
        rel = os.path.relpath(raiz, repo)
        rel = "" if rel == "." else rel
        keep = []
        for d in dirs:
            r = os.path.join(rel, d) if rel else d
            if r == ".git" or r in EXCLUIDAS:
                continue
            keep.append(d)
        dirs[:] = sorted(keep)
        for f in sorted(archivos):
            r = os.path.join(rel, f) if rel else f
            p = os.path.join(raiz, f)
            if os.path.islink(p):
                out[r] = "link:" + os.readlink(p)
                continue
            st = os.stat(p)
            if f.endswith(SOLO_STAT):
                out[r] = f"stat:{st.st_size}:{st.st_mtime_ns}"
                continue
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for b in iter(lambda: fh.read(1 << 20), b""):
                    h.update(b)
            out[r] = h.hexdigest()
    return out


def main():
    if sys.argv[1] == "--comparar":
        a = json.load(open(sys.argv[2]))
        b = json.load(open(sys.argv[3]))
        nuevos = sorted(set(b) - set(a))
        borrados = sorted(set(a) - set(b))
        cambiados = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        print(json.dumps({"archivos_a": len(a), "archivos_b": len(b), "nuevos": nuevos, "borrados": borrados,
                          "cambiados": cambiados, "exclusiones": EXCLUIDAS}, ensure_ascii=False, indent=1))
        return
    repo, salida = sys.argv[1], sys.argv[2]
    f = foto(repo)
    with open(salida, "w") as fh:
        json.dump(f, fh, ensure_ascii=False, indent=0, sort_keys=True)
    print(len(f), "archivos")


if __name__ == "__main__":
    main()
