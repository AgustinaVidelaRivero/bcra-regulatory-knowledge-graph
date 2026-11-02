"""U-SEG-OFICIAL, S1, punto 8: anotación POSTERIOR de los renglones del censo (USD 0). No cambia la cifra del censo.

Uso: python -B explicar_censo_S1.py --e0 <salida de la corrida> --censo <censo_renglones_S1.json> --out <json>

Escrita después de ver el censo, y declarada así: la cifra del censo es la de la regla sellada
(`regla_censo_renglones_S1.md`, versión 2). Esta anotación solo agrega a cada renglón de la lista una explicación
cuando la hay, para que la revisión lea primero los que no tienen ninguna:
- `sin_unidad_ni_rol`:
  1. `igual_salvo_puntuacion`: en minúsculas y con solo letras y números, es igual a un renglón del texto de una
     unidad o de un título heredado del mismo TO (E0 escribe el título heredado como «N. Título», con punto después
     del número, y el PDF a veces no lo trae);
  2. `contenido_en_unidad_de_la_pagina`: con la misma forma, tiene 20 caracteres o más y está dentro del texto
     (incluidas las tablas serializadas) de una unidad cuyas páginas incluyen la del renglón;
  3. `parte_de_un_titulo_heredado`: con la misma forma, tiene 4 caracteres o más y está dentro de un título heredado
     (tramo `encabezado`) del TO: un título envuelto en dos renglones, o un rótulo que E0 reescribe;
  4. `sin_explicacion`: lo demás.
- `encabezado_o_pie_no_repetido`: `forma_de_encabezado_o_pie` si empieza con una de las formas del encabezado o del
  pie del BCRA (B.C.R.A., Versión, Vigencia, Comunicación, Página, una fecha, un número solo) o está en mayúsculas;
  si no, las clases 1 a 3 de arriba; si no, `sin_explicacion`.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

RE_ENC = re.compile(r"^(B\.?\s?C\.?\s?R\.?\s?A\.?|versi[oó]n|vigencia|comunicaci[oó]n|p[aá]gina|-?\s*\d+\s*-?$|"
                    r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{2}\.\d{2}\.\d{2})", re.I)


def laxa(s: str) -> str:
    return re.sub(r"[^0-9a-záéíóúñü]", "", s.casefold())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e0", type=Path, required=True)
    ap.add_argument("--censo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    cen = json.loads(a.censo.read_text(encoding="utf-8"))
    out, tot = {}, Counter()
    for to, v in cen["por_to"].items():
        if not v["lista"]:
            continue
        ch = json.loads((a.e0 / f"chunks_{to}.json").read_text(encoding="utf-8"))
        renglones = set()
        titulos = set()
        por_pagina = defaultdict(list)
        for c in ch:
            for r in c["texto"].split("\n"):
                renglones.add(laxa(r))
            for tr in c["herencia"]:
                if tr["tipo"] == "encabezado":
                    for r in tr["texto"].split("\n"):
                        renglones.add(laxa(r))
                    titulos.add(laxa(tr["texto"]))
            lx = laxa(c["texto"])
            for p in c["paginas"]:
                por_pagina[p].append(lx)
        filas = []
        for x in v["lista"]:
            k = laxa(x["texto"])
            if k and k in renglones:
                e = "igual_salvo_puntuacion"
            elif len(k) >= 20 and any(k in t for t in por_pagina.get(x["pagina"], [])):
                e = "contenido_en_unidad_de_la_pagina"
            elif len(k) >= 4 and any(k in t for t in titulos):
                e = "parte_de_un_titulo_heredado"
            else:
                e = "sin_explicacion"
            if x["clase"] != "sin_unidad_ni_rol" and (RE_ENC.match(x["texto"].strip())
                                                       or (x["texto"].isupper() and len(x["texto"]) > 8)):
                e = "forma_de_encabezado_o_pie"
            tot[(x["clase"], e)] += 1
            filas.append({**x, "explicacion_posterior": e})
        out[to] = filas
    res = {"nota": "anotación posterior al censo; no cambia su cifra",
           "por_clase_y_explicacion": {f"{c}|{e}": n for (c, e), n in sorted(tot.items())},
           "sin_explicacion": sum(n for (c, e), n in tot.items() if e == "sin_explicacion"),
           "por_to": out}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False, indent=1))
    for to, fs in out.items():
        for f in fs:
            if f["explicacion_posterior"] == "sin_explicacion":
                print(" ", to, f["pagina"], f["renglon"], f["clase"][:12], f["texto"][:90])


if __name__ == "__main__":
    main()
