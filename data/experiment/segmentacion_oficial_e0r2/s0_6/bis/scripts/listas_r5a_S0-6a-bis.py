"""Las listas de R5-a con C ajustada (U-SEG-OFICIAL, S0-6a-bis, decisión 3; USD 0, solo lectura): por cada lista de
LISTAS_R5A_S0_5, si queda C o R5-a por lista (LISTAS_R5A_S0_6), si era de las 13 donde C daba otra cosa en S0-6a, si es de
diseño (alguna de sus unidades está entre las 286 leídas en S1-ter o en las filas del TSV), y si el texto de sus unidades
en la E0 de S1-ter (el último ítem o sus partes y el cierre de la madre) sigue entero en la E0 dada (por sha256 propio).

Uso: python -B listas_r5a_S0-6a-bis.py --codigo <dir de correr_e0.py> --comun <dir de comun_S1quater.py>
       --orden <orden_lectura_S1ter.json> --base <E0 de S1-ter> --final <E0> --tsv <TSV> --out <json>
       [--out-detalle <json>]

`--out` nombra el ítem solo de las listas de diseño; las demás van por documento (el «seguí»: sin ids de unidades que no
son de diseño en s0_6/bis/). `--out-detalle` (NO_ABRIR_) las nombra todas, con sus unidades.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

TRECE = {("adfsp", "1.1.10"), ("apnf", "1.3.1.2"), ("cryl", "4.2.2"), ("depaho", "3.11.5.5"), ("manori", "1.1.6.5"),
         ("manori", "1.4.1.3"), ("manori", "3.4.1.3"), ("ri2_ae", "14.3"), ("ri_oc", "B.1.28"), ("ri_oc", "B.2.4"),
         ("ri_oc", "B.3.4"), ("ri_rml", "1.4.2"), ("ri_spi", "C.1.3")}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("codigo", "comun", "orden", "base", "final", "tsv", "out"):
        ap.add_argument(f"--{k}", type=Path, required=True)
    ap.add_argument("--out-detalle", dest="out_detalle", type=Path)
    a = ap.parse_args()
    sys.path.insert(0, str(a.codigo))
    import correr_e0 as CE
    sys.path.insert(0, str(a.comun))
    import comun_S1quater as Q     # sin cambios: mostradas_S1ter, con la E0 y el orden sellado que necesita
    orden = json.loads(Q.leer_sellado(a.orden, Q.SHA_ORDEN_S1TER, "el orden de S1-ter"))
    leidas = set(Q.mostradas_S1ter(orden, Q.E0(a.base)))
    filas = {f["id_unidad_e0"] for f in csv.DictReader(a.tsv.open(encoding="utf-8"), delimiter="\t")}
    out, det = [], []
    for to, items in sorted(CE.LISTAS_R5A_S0_5.items()):
        base = json.loads((a.base / f"chunks_{to}.json").read_text(encoding="utf-8"))
        fin = {c["sha256_propio"] for c in json.loads((a.final / f"chunks_{to}.json").read_text(encoding="utf-8"))}
        for it in items:
            madre = it.rsplit(".", 1)[0] if "." in it else f"S{it}"
            madres = {madre, f"S{madre}"} if "." not in madre else {madre}
            us = [c for c in base if c["id"] == f"{to}::{it}" or c["id"].startswith(f"{to}::{it}::parte")
                  or any(c["id"] == f"{to}::{m}::cierre" or c["id"].startswith(f"{to}::{m}::cierre::") for m in madres)]
            ids = sorted(c["id"] for c in us)
            diseno = any(i in leidas or i in filas or any(i.startswith(f + "::parte") for f in filas) for i in ids)
            fila = {"to": to, "queda": "R5-a" if it in CE.LISTAS_R5A_S0_6.get(to, {}) else "C",
                    "de_las_13": (to, it) in TRECE, "de_diseno": diseno, "unidades": len(us),
                    "texto_entero_en_la_E0": sum(1 for c in us if c["sha256_propio"] in fin)}
            det.append({"item": it, **fila, "ids": ids})
            out.append(({"item": it} if diseno else {}) | fila)
    res = {"listas": len(out), "quedan_en_R5a": sum(1 for x in out if x["queda"] == "R5-a"),
           "quedan_en_C": sum(1 for x in out if x["queda"] == "C"),
           "de_las_13": {"R5-a": sum(1 for x in out if x["de_las_13"] and x["queda"] == "R5-a"),
                         "C": sum(1 for x in out if x["de_las_13"] and x["queda"] == "C")},
           "no_de_diseno": {"listas": sum(1 for x in out if not x["de_diseno"]),
                            "en_R5a_por_documento": dict(sorted(__import__("collections").Counter(
                                x["to"] for x in out if not x["de_diseno"] and x["queda"] == "R5-a").items()))},
           "por_lista": out}
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if a.out_detalle:
        a.out_detalle.write_text(json.dumps({"por_lista": det}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "por_lista"}, ensure_ascii=False))
    for x in out:
        if x["de_las_13"] or x["queda"] == "R5-a" or x["texto_entero_en_la_E0"] < x["unidades"]:
            print(x)


if __name__ == "__main__":
    main()
