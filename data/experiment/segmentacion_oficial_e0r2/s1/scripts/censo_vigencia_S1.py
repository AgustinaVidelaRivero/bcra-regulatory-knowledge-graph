"""U-SEG-OFICIAL, S1.5: censo de vigencia de los 152 TOs (USD 0, sin API).

Uso: python -B censo_vigencia_S1.py --copia <raíz de una copia> --e0 <salida de la corrida> --manifiesto <json>
       --lineas <caché de renglones de lineas_152.py> --out <json>

Marcas buscadas, sin distinguir mayúsculas ni tildes: «derogad…», «vigente hasta», «vigente al».
- Carátula: la página 1 del PDF, renglón por renglón (`e0_lib.extraer_lineas`, número de renglón desde 1).
- Además, las otras páginas con rol `portada` en la salida de e0-r2 (`pies_<to>.json`), aparte.
- Título en el índice del sitio: `escalado_prep/indice_oficial_raw.json`, entrada del archivo oficial del TO
  (`escalado_prep/inventario_tos.csv`), con su lista y su posición.
Marcas conocidas: manual y ri_ao (enmiendas firmadas a las adendas 1 y 2 del laudo B5.5, Parte III). Una marca en otro
TO es hallazgo y se reporta; la decisión es de la autora.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

PATRONES = {"derogado": re.compile(r"\bderogad"), "vigente hasta": re.compile(r"\bvigente\s+hasta\b"),
            "vigente al": re.compile(r"\bvigente\s+al\b")}
CONOCIDOS = {"manual", "ri_ao"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).casefold()


def marcas(texto: str) -> list[str]:
    n = norm(texto)
    return [k for k, rx in PATRONES.items() if rx.search(n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("copia", "e0", "manifiesto", "lineas", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args()
    ex = a.copia / "data/experiment"
    man = json.loads(a.manifiesto.read_text(encoding="utf-8"))
    inv = {r["id"]: r for r in csv.DictReader(open(ex / "escalado_prep/inventario_tos.csv", encoding="utf-8"))}
    raw = json.loads((ex / "escalado_prep/indice_oficial_raw.json").read_text(encoding="utf-8"))
    por_archivo = {}
    for lista in ("textos_ordenados", "regimenes_informativos"):
        for i, e in enumerate(raw[lista]):
            por_archivo.setdefault(e["archivo"], []).append({"lista": lista, "posicion": i + 1, "titulo": e["titulo"]})
    out, nuevos = {}, []
    for t in man["tos"]:
        to = t["id"]
        lin = json.loads((a.lineas / f"{to}.json").read_text(encoding="utf-8"))
        roles = [d["rol"] for d in json.loads((a.e0 / f"pies_{to}.json").read_text(encoding="utf-8"))["paginas_detalle"]]
        car = [{"pagina": 1, "renglon": i + 1, "texto": l[3], "marcas": marcas(l[3])}
               for i, l in enumerate(lin[0]) if marcas(l[3])] if lin else []
        otras = [{"pagina": p + 1, "renglon": i + 1, "texto": l[3], "marcas": marcas(l[3])}
                 for p, pag in enumerate(lin) if p > 0 and roles[p] == "portada"
                 for i, l in enumerate(pag) if marcas(l[3])]
        ent = por_archivo.get(inv[to]["archivo_oficial"], [])
        idx = [{**e, "marcas": marcas(e["titulo"])} for e in ent]
        con_marca = bool(car) or any(e["marcas"] for e in idx)
        out[to] = {"caratula": car, "otras_paginas_portada": otras, "indice_del_sitio": idx,
                   "archivo_oficial": inv[to]["archivo_oficial"], "marca": con_marca,
                   "vigente_en_el_manifiesto": t["vigencia"]["vigente"],
                   "conocido": to in CONOCIDOS}
        if con_marca and to not in CONOCIDOS:
            nuevos.append(to)
    res = {"patrones": {k: v.pattern for k, v in PATRONES.items()},
           "tos": len(out), "con_marca": sorted(t for t, v in out.items() if v["marca"]),
           "conocidos_con_marca": sorted(t for t in CONOCIDOS if t in out and out[t]["marca"]),
           "marcas_nuevas": nuevos,
           "sin_entrada_en_el_indice_del_sitio": sorted(t for t, v in out.items() if not v["indice_del_sitio"]),
           "con_marca_en_otras_paginas_portada": sorted(t for t, v in out.items() if v["otras_paginas_portada"]),
           "por_to": out}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_to"}, ensure_ascii=False, indent=1))
    for t in res["con_marca"] + res["con_marca_en_otras_paginas_portada"]:
        v = out[t]
        print(t, json.dumps({"caratula": v["caratula"], "indice": [e for e in v["indice_del_sitio"] if e["marcas"]],
                             "otras": v["otras_paginas_portada"][:5]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
