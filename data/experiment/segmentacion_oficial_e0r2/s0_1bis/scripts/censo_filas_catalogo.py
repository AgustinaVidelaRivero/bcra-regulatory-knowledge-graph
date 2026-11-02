"""S0-1 bis, C: filas del catálogo 11.x de rdbcra según el PDF (pdfplumber, `find_tables` con los ajustes de
e0_tablas) y su estado en una salida de E0: el número de la fila es un nodo de E0 (terminal o no), o su renglón se
rechazó (con el motivo). Fila de catálogo = fila cuya primera celda es solo un número de punto. Solo lectura.

Uso: python -B censo_filas_catalogo.py <pdf> <dir de E0> <salida.json>"""
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

import pdfplumber

RE_CELDA = re.compile(r"^(\d+(?:\.\d+)+)\.?$")
pdf, d, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
e = json.loads((d / "estructura_rdbcra.json").read_text(encoding="utf-8"))
nodos = {}


def rec(n):
    nodos[n["numero"]] = "terminal" if not n["hijos"] else "con_hijos"
    for h in n["hijos"]:
        rec(h)


for s in e["secciones"]:
    rec(s)
rech = {}
for r in e["rechazos_header"]:
    m = re.match(r"^(\d+(?:\.\d+)+)\.?\s", r["texto"])
    if m:
        rech.setdefault(m.group(1), r["motivo"])
filas = []
with pdfplumber.open(str(pdf)) as doc:
    for pi, page in enumerate(doc.pages, start=1):
        for ti, tb in enumerate(page.find_tables()):
            ext = tb.extract()
            et = [RE_CELDA.match((f[0] or "").strip()) if f else None for f in ext]
            if sum(1 for m in et if m) < 3:
                continue
            for k, (row, f, m) in enumerate(zip(tb.rows, ext, et)):
                prim = (f[0] or "").strip() if f else ""
                filas.append(OrderedDict([
                    ("pagina", pi), ("tabla_en_pagina", ti), ("fila", k),
                    ("banda", [round(row.bbox[1], 1), round(row.bbox[3], 1)]),
                    ("numero", m.group(1) if m else None),
                    ("primera_celda", prim[:60]),
                    ("estado_e0", (nodos.get(m.group(1)) or ("rechazado:" + rech[m.group(1)] if m.group(1) in rech
                                                            else "ausente")) if m else None),
                    ("celdas", [(c or "").replace("\n", " ")[:80] for c in f])]))
cat = [f for f in filas if f["numero"]]
out = OrderedDict([
    ("pdf", pdf.name), ("e0", d.name),
    ("paginas", sorted({f["pagina"] for f in filas})),
    ("filas_de_catalogo", len(cat)),
    ("por_estado_e0", dict(Counter(f["estado_e0"].split(":")[0] for f in cat))),
    ("motivos_de_rechazo", dict(Counter(f["estado_e0"].split(":", 1)[1].split("_y_")[0] for f in cat
                                        if f["estado_e0"].startswith("rechazado")))),
    ("filas_sin_numero", [OrderedDict([("pagina", f["pagina"]), ("fila", f["fila"]),
                                       ("primera_celda", f["primera_celda"])]) for f in filas if not f["numero"]]),
    ("filas", filas)])
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("filas",)}, ensure_ascii=False)[:3000])
