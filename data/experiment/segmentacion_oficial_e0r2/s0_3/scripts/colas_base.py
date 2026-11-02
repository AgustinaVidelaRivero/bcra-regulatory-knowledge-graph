"""Censo de las colas de título que acepta separar_encabezado_pie (código de una copia), con el x0 de la
línea de sección y el del renglón. Reproduce las páginas de cuerpo de la etapa final de cada TO a partir de
la salida de E0 (estructura_<to>.json: detalle_descartes) y llama a separar_encabezado_pie con los argumentos de e0-r2.
Uso: colas_base.py <codigo> <dir_salida_e0> <salida.json> [tos...]"""
import json, sys
from pathlib import Path
sys.dont_write_bytecode = True
raiz = Path(sys.argv[1]).resolve(); dsal = Path(sys.argv[2])
sys.path.insert(0, str(raiz / "data/experiment/reextraccion_v2/e0_chunking"))
import e0_lib as E0
import correr_e0 as CE
pdfs = raiz / "data/experiment/escalado_prep/pdfs"
out = []
tos = sys.argv[4:] or sorted(p.name[len("estructura_"):-5] for p in dsal.glob("estructura_*.json"))
for to in tos:
    e = json.loads((dsal / f"estructura_{to}.json").read_text())
    pdf = pdfs / f"{to}.pdf"
    if not pdf.exists():
        pdf = raiz / "data/experiment/subset" / e["archivo"]
    pag = E0.extraer_lineas(pdf)
    desc = {}
    for d in e["accounting"]["detalle_descartes"]:
        desc.setdefault(d["pagina"], []).append(d["texto"])
    for p, ls in enumerate(pag, 1):
        if p not in desc:
            continue
        # buscar en los descartes el renglón de sección y los que siguen (orden del encabezado)
        textos = [l.texto for l in ls[:7]]
        secc = [i for i, l in enumerate(ls[:6]) if E0._match_seccion_r2(l.texto.strip(), True, "0") or E0.RE_SECCION_EN_LINEA.search(l.texto.strip()) and "B.C.R.A." in l.texto]
        if not secc:
            continue
        i0 = secc[0]
        for j in range(i0 + 1, min(i0 + 4, len(ls))):
            l = ls[j]
            if l.texto in desc[p] and "B.C.R.A." not in l.texto and not E0._es_titulo_mayusculas(l.texto.strip()):
                out.append({"to": to, "pagina": p, "x0_seccion": ls[i0].x0, "x0": l.x0, "dtop": round(l.top - ls[j-1].top, 1),
                            "seccion": ls[i0].texto[:60], "renglon": l.texto[:80]})
            else:
                break
Path(sys.argv[3]).write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(len(out))
