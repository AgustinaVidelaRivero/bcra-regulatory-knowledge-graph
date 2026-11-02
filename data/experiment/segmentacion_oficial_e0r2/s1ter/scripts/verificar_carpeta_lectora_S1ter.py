"""U-SEG-OFICIAL, S1-ter-b: verifica la carpeta de la lectora contra el `manifest.txt` de cada etapa (USD 0).

Uso: python -B verificar_carpeta_lectora_S1ter.py <carpeta de la lectora>

En cada subcarpeta `etapa_N/`: sha256 y bytes de cada archivo listado, y ningún archivo sin listar. Un `.DS_Store` no se
lista ni cuenta como sin listar (decisión 13 de la autora sobre el FRENO S1-ter-a): se informa aparte.
"""
import hashlib
import sys
from pathlib import Path

raiz = Path(sys.argv[1])
todo_bien = True
for d in sorted(p for p in raiz.iterdir() if p.is_dir()):
    filas = [l for l in (d / "manifest.txt").read_text(encoding="utf-8").splitlines()[2:] if l.strip()]
    ok, mal, listados = 0, [], set()
    for l in filas:
        sha, nbytes, resto = l.split("  ", 2)
        nombre = resto.split(" — ", 1)[0]
        listados.add(nombre)
        p = d / nombre
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == sha and p.stat().st_size == int(nbytes):
            ok += 1
        else:
            mal.append(nombre)
    ds = sorted(p.name for p in d.iterdir() if p.name == ".DS_Store")
    sin_listar = sorted(p.name for p in d.iterdir() if p.name not in listados | {"manifest.txt", ".DS_Store"})
    todo_bien &= ok == len(filas) and not mal and not sin_listar
    print(f"{d.name}: {ok} de {len(filas)} iguales a su manifest.txt (sha256 y bytes); distintos o ausentes: {mal}; "
          f"sin listar: {sin_listar}; .DS_Store: {ds}")
otros = sorted(p.name for p in raiz.iterdir() if not p.is_dir() and p.name != ".DS_Store")
print(f"en la raíz de la carpeta, fuera de las etapas: {otros}")
sys.exit(0 if todo_bien and not otros else 1)
