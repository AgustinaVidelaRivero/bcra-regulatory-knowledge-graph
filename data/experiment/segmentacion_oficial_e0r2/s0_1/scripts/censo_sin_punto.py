"""Rótulos aceptados sin punto final (RE_NUM_TOKEN_SIN_PUNTO), en los 152 TOs: modo, ngaps y si el primer hueco de
columna (> GAP_COL) cae justo después del número (forma de fila «código  descripción»). Solo lectura."""
import json, sys
from collections import Counter
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun_s01 as C
import pdfplumber
raiz, cache, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
CE, E0 = C.cargar_codigo(raiz)
filas = []
for to in C.tos_particion(raiz):
    paginas = C.paginas_de(cache, to, E0)
    res, roles, modo, _ = C.parsear(CE, E0, to, paginas)
    cands = [n for n in C.nodos(res) if n.tipo == "punto" and n.linea_label is not None
             and not n.linea_label.texto.split()[0].endswith(".")]
    if not cands:
        continue
    with pdfplumber.open(str(raiz / "data/experiment/escalado_prep/pdfs" / f"{to}.pdf")) as pdf:
        for n in cands:
            l = n.linea_label
            ws = [w for w in pdf.pages[l.pagina - 1].extract_words() if abs(w["top"] - l.top) <= E0.TOL_TOP + 0.6]
            ws.sort(key=lambda w: w["x0"])
            gaps = [i for i, (a, b) in enumerate(zip(ws, ws[1:])) if b["x0"] - a["x1"] > E0.GAP_COL]
            filas.append({"to": to, "modo": modo, "numero": n.numero, "pagina": l.pagina, "ngaps": l.ngaps,
                          "hueco_tras_numero": bool(gaps) and gaps[0] == 0, "hijos": len(n.hijos),
                          "linea": l.texto[:110]})
out = {"resumen": {"rotulos_sin_punto": len(filas), "por_to": dict(Counter(f["to"] for f in filas)),
                   "con_hueco_tras_numero": dict(Counter(f["to"] for f in filas if f["hueco_tras_numero"]))},
       "filas": filas}
Path(sal).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(out["resumen"], ensure_ascii=False, indent=1))
