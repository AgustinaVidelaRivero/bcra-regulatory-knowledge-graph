"""Vista por página de un TO: los primeros renglones (con x0) de cada página y los renglones que parecen rótulos de
sub-documento (Anexo, Parte, romano, Capítulo, Régimen). Exploración, sin escribir nada.
Uso: python -B vista_tos.py <raíz de código> <to> [n_primeros]"""
import re
import sys
from pathlib import Path
raiz = Path(sys.argv[1]); to = sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 7
sys.dont_write_bytecode = True
for p in (raiz / "data/experiment/reextraccion_v2/e0_chunking", raiz / "data/experiment/reextraccion_v2"):
    sys.path.insert(0, str(p))
import e0_lib as E0
RX = re.compile(r"^(ANEXO|Anexo|PARTE|Parte|CAP[IÍ]TULO|Cap[ií]tulo|R[ÉE]GIMEN|R\.I\.|[IVX]{1,5}[.\-–]\s|APARTADO|T[IÍ]TULO)")
pdf = raiz / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf"
paginas = E0.extraer_lineas(pdf)
for pi, ls in enumerate(paginas, start=1):
    print(f"--- p. {pi} ({len(ls)})")
    for i, l in enumerate(ls):
        if i < n or RX.match(l.texto.strip()):
            print(f"  {i:3d} x0={l.x0:6.1f} top={l.top:6.1f} | {l.texto[:100]}")
