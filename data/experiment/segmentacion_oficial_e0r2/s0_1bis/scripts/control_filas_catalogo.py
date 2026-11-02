"""S0-1 bis, C: control automático de las filas del catálogo 11.x de rdbcra en una salida de E0. Para cada fila de
catálogo del PDF (banda de `find_tables()`), compara los renglones de la banda (caché de líneas, dentro del ancho de
la tabla) con los renglones del texto de la unidad de su número: la fila está limpia si la unidad existe, es un
punto terminal y lleva todos los renglones de su banda y ninguno de otra banda. Solo lectura.

Uso: python -B control_filas_catalogo.py <pdf> <caché de líneas de rdbcra> <dir de E0> <salida.json>"""
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

import pdfplumber

RE_CELDA = re.compile(r"^(\d+(?:\.\d+)+)\.?$")
TOL = 2.0     # TOL_TOP_TABLA de correr_e0
pdf, cache, d, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
paginas = json.loads(cache.read_text(encoding="utf-8"))
chunks = {c["id"]: c for c in json.loads((d / "chunks_rdbcra.json").read_text(encoding="utf-8"))}
filas = []
with pdfplumber.open(str(pdf)) as doc:
    for pi, page in enumerate(doc.pages, start=1):
        for tb in page.find_tables():
            ext = tb.extract()
            if sum(1 for f in ext if f and RE_CELDA.match((f[0] or "").strip())) < 3:
                continue
            for row, f in zip(tb.rows, ext):
                m = RE_CELDA.match((f[0] or "").strip()) if f else None
                y0, y1 = row.bbox[1], row.bbox[3]
                lineas = [x[3] for x in paginas[pi - 1]
                          if y0 - TOL <= x[1] < y1 - TOL and tb.bbox[0] - 5 <= x[2] <= tb.bbox[2]]
                filas.append({"pagina": pi, "numero": m.group(1) if m else None, "banda": [round(y0, 1), round(y1, 1)],
                              "lineas": lineas})
# a qué banda pertenece cada renglón (por página y texto; un texto repetido en dos bandas de una página es ambiguo)
banda_de: dict = {}
for k, f in enumerate(filas):
    for t in f["lineas"]:
        banda_de.setdefault((f["pagina"], t), set()).add(k)
out_filas = []
for k, f in enumerate(filas):
    if not f["numero"]:
        continue
    c = chunks.get(f"rdbcra::{f['numero']}")
    r = OrderedDict([("numero", f["numero"]), ("pagina", f["pagina"]), ("banda", f["banda"]),
                     ("renglones_de_la_banda", len(f["lineas"]))])
    if c is None or c["tipo"] != "punto_terminal":
        r["estado"] = "sin_unidad_terminal"
        out_filas.append(r)
        continue
    propias = c["texto"].split("\n")
    faltan = [t for t in f["lineas"] if t not in propias]
    ajenas = [t for t in propias if t not in f["lineas"]]
    de_otra_fila = [t for t in ajenas if any(j != k for p in c["paginas"] for j in banda_de.get((p, t), ()))]
    r.update({"unidad": c["id"], "faltan": faltan, "de_otra_fila": de_otra_fila,
              "fuera_de_toda_banda": [t for t in ajenas if t not in de_otra_fila],
              "estado": "limpia" if not faltan and not de_otra_fila else "con_defecto"})
    out_filas.append(r)
out = OrderedDict([("e0", d.name), ("filas", len(out_filas)),
                   ("por_estado", dict(Counter(r["estado"] for r in out_filas))),
                   ("con_renglones_fuera_de_toda_banda", [(r["numero"], r["fuera_de_toda_banda"]) for r in out_filas
                                                          if r.get("fuera_de_toda_banda")]),
                   ("detalle", out_filas)])
sal.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "detalle"}, ensure_ascii=False))
for r in out_filas:
    if r["estado"] == "con_defecto":
        print(" ", r["numero"], "faltan", r["faltan"][:3], "de otra fila", r["de_otra_fila"][:3])
