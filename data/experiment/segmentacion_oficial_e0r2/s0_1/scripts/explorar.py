"""Exploración de solo lectura: líneas de E0 de un TO que matchean una expresión (página, índice en la página,
x0, top, rol de la página). Corre con el código de la copia.

Uso: python -B explorar.py <raíz de la copia> <to> <regex> [--pag N] [--todas]
"""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
raiz = Path(sys.argv[1])
sys.path.insert(0, str(raiz / "data/experiment/reextraccion_v2/e0_chunking"))
import e0_lib as E0  # noqa: E402

to, pat = sys.argv[2], re.compile(sys.argv[3])
pag = int(sys.argv[sys.argv.index("--pag") + 1]) if "--pag" in sys.argv else None
pdf = raiz / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf"
paginas = E0.extraer_lineas(pdf)
roles = E0.clasificar_paginas(paginas)
print(f"{to}: {len(paginas)} páginas; roles {dict((r, roles.count(r)) for r in sorted(set(roles)))}")
for pi, (ls, rol) in enumerate(zip(paginas, roles), 1):
    if pag is not None and pi != pag:
        continue
    for i, l in enumerate(ls):
        if "--todas" in sys.argv or pat.search(l.texto):
            print(f"p{pi:>4} [{rol[:6]}] #{i:<3} x0={l.x0:<6} top={l.top:<6} | {l.texto[:150]}")
