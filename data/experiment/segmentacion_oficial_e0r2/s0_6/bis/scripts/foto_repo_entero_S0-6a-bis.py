"""Foto sha256 del repo entero, sin .git y sin excluir ninguna otra ruta (U-SEG-OFICIAL, S0-6a-bis; solo lectura).
Uso: python -B foto_repo_entero_S0-6a-bis.py <repo> <salida.json>          toma la foto
     python -B foto_repo_entero_S0-6a-bis.py --comparar <a.json> <b.json>   compara dos fotos
Los enlaces simbólicos se registran por su destino (no se siguen)."""
import hashlib, json, os, sys, time
from pathlib import Path

def foto(repo: Path) -> dict:
    out = {}
    for raiz, dirs, archivos in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if not (Path(raiz) == repo and d == ".git"))
        for a in sorted(archivos):
            p = Path(raiz) / a
            rel = p.relative_to(repo).as_posix()
            if p.is_symlink():
                out[rel] = "enlace:" + os.readlink(p)
                continue
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
            out[rel] = h.hexdigest()
    return out

if sys.argv[1] == "--comparar":
    a, b = (json.loads(Path(x).read_text())["archivos"] for x in sys.argv[2:4])
    res = {"archivos_a": len(a), "archivos_b": len(b), "nuevos": sorted(set(b) - set(a)),
           "borrados": sorted(set(a) - set(b)), "cambiados": sorted(k for k in set(a) & set(b) if a[k] != b[k])}
    print(json.dumps(res, ensure_ascii=False, indent=1))
else:
    repo, sal = Path(sys.argv[1]), Path(sys.argv[2])
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    f = foto(repo)
    sal.write_text(json.dumps({"tomada": t, "archivos": f}, ensure_ascii=False, indent=0) + "\n")
    print(len(f), "archivos", t)
