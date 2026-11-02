"""S0-1 bis, C: muestra de 10 filas del catálogo 11.x de rdbcra para leerlas contra el PDF. Semilla 20261005 sobre las
filas de catálogo ordenadas por (página, fila). Por cada fila guarda el recorte de la página (ancho de la tabla, banda
de la fila con 6 puntos de margen) como PNG a 200 dpi y, en un JSON, las celdas que lee pdfplumber y el texto de la
unidad de su número en una salida de E0. Solo lectura sobre el PDF y la salida.

Uso: python -B muestra_filas_r9.py <pdf> <dir de E0> <dir de salida>"""
import json
import random
import re
import sys
from pathlib import Path

import pdfplumber

SEMILLA, N = 20261005, 10
RE_CELDA = re.compile(r"^(\d+(?:\.\d+)+)\.?$")
pdf, d, sal = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sal.mkdir(parents=True, exist_ok=True)
chunks = {c["id"]: c for c in json.loads((d / "chunks_rdbcra.json").read_text(encoding="utf-8"))}
with pdfplumber.open(str(pdf)) as doc:
    filas = []
    for pi, page in enumerate(doc.pages, start=1):
        for tb in page.find_tables():
            ext = tb.extract()
            if sum(1 for f in ext if f and RE_CELDA.match((f[0] or "").strip())) < 3:
                continue
            for k, (row, f) in enumerate(zip(tb.rows, ext)):
                m = RE_CELDA.match((f[0] or "").strip()) if f else None
                if m:
                    filas.append((pi, k, m.group(1), tb.bbox, row.bbox, f))
    filas.sort(key=lambda x: (x[0], x[1]))
    muestra = sorted(random.Random(SEMILLA).sample(range(len(filas)), N))
    out = {"semilla": SEMILLA, "filas_de_catalogo": len(filas), "muestra": []}
    for j in muestra:
        pi, k, num, tbb, rb, f = filas[j]
        page = doc.pages[pi - 1]
        caja = (tbb[0] - 4, max(rb[1] - 6, 0), tbb[2] + 4, min(rb[3] + 6, page.height))
        png = sal / f"fila_{num.replace('.', '_')}_p{pi}.png"
        page.crop(caja).to_image(resolution=200).save(str(png))
        c = chunks.get(f"rdbcra::{num}")
        out["muestra"].append({"indice": j, "numero": num, "pagina": pi, "fila_en_tabla": k,
                               "banda": [round(rb[1], 1), round(rb[3], 1)], "png": png.name,
                               "celdas_pdfplumber": f, "unidad": c["id"] if c else None,
                               "tipo": c["tipo"] if c else None, "texto_unidad": c["texto"] if c else None})
(sal / "muestra_filas_r9.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(out["filas_de_catalogo"], "filas; muestra:", [m["numero"] for m in out["muestra"]])
