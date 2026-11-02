"""Imprime los renglones de páginas de un PDF con x0, top y el rol de página de la escalera e0-r2 (exploración).
Uso: python -B ver_paginas.py <raíz de código> <to> <p1>[-<p2>] [--max N]"""
import sys
from pathlib import Path
raiz = Path(sys.argv[1]); to = sys.argv[2]; rango = sys.argv[3]
mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 999
sys.dont_write_bytecode = True
for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking", raiz / "data/experiment/reextraccion_v2"):
    sys.path.insert(0, str(p))
import e0_lib as E0
pdf = raiz / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf"
paginas = E0.extraer_lineas(pdf)
roles = E0.clasificar_paginas(paginas, continuacion_con_titulo=True)
a, _, b = rango.partition("-"); a = int(a); b = int(b or a)
for pi in range(a, b + 1):
    print(f"=== p. {pi} rol={roles[pi-1]} ({len(paginas[pi-1])} renglones)")
    for i, l in enumerate(paginas[pi - 1][:mx]):
        print(f"{i:3d} x0={l.x0:6.1f} top={l.top:6.1f} g={l.ngaps} | {l.texto[:110]}")
