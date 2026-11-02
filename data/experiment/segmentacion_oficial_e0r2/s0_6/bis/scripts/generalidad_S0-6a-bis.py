"""La generalidad de cada regla de S0-6a-bis (U-SEG-OFICIAL; USD 0, sin API; mandato de S0-6a, §2, y el «seguí» de
S0-6a-bis): si cambia algo en al menos un documento donde no se vio su error.

Uso: python -B generalidad_S0-6a-bis.py --censo <censo por regla (censo_por_regla_S0-5a.py)>
       --tsv <errores_confirmados_S1ter.tsv> --out <json>

Las filas de cada regla son las de su letra en la nota de decisiones (§3), con las de segunda causa; las de L y M, las
de su decisión en el «seguí». El documento de cada fila sale del TSV. Un documento cambia con una regla si la
configuración de esa regla sola crea, quita o cambia al menos una unidad (`chunks_<to>.json`) frente a todas apagadas.
Si una regla solo cambia documentos donde se vio su error, esos documentos salen de la bolsa de la evaluación final
(`docs/plan_tesis.md:782`, punto 4).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FILAS_POR_REGLA = {
    "a": ("E1-008", "E1-010", "E2-007", "E2-039", "E2-056", "E2-057", "E2-058", "E2-099", "E2-002", "E2-006", "E2-008",
          "E2-096"),
    "b": ("E1-081", "E1-090", "E2-002", "E2-011", "E2-016", "E2-028", "E2-034", "E2-040", "E2-043", "E2-045", "E2-046",
          "E2-055"),
    "c": ("E2-033", "E2-045", "E2-006", "E2-008", "E2-096", "E2-097"),
    "d": ("E2-058", "E2-098", "E2-099"),
    "e": ("E2-002", "E2-065"),
    "f": ("E2-046", "E2-066"),
    "g": ("E2-094",),
    "h": ("E2-005",),
    "i": ("E2-006",),
    "j": ("E1-047",),
    "k": ("E2-006",),
    "l": ("E1-008",),     # S0-6a-bis, decisión 5
    "m": ("E2-002",),     # S0-6a-bis, decisión 6
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--censo", type=Path, required=True)
    ap.add_argument("--tsv", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    censo = json.loads(a.censo.read_text(encoding="utf-8"))
    doc = {f["ficha"]: f["documento"] for f in csv.DictReader(a.tsv.open(encoding="utf-8"), delimiter="\t")}
    out = {}
    for r, filas in FILAS_POR_REGLA.items():
        vistos = sorted({doc[f] for f in filas})
        por_to = censo["por_regla"][r]["por_to"]
        cambia = sorted(t for t, v in por_to.items() if v["creadas"] or v["quitadas"] or v["cambiadas"])
        fuera = sorted(set(cambia) - set(vistos))
        out[r] = {"filas": list(filas), "documentos_donde_se_vio": vistos, "documentos_que_cambia": len(cambia),
                  "documentos_que_cambia_donde_se_vio": sorted(set(cambia) & set(vistos)),
                  "documentos_que_cambia_donde_no_se_vio": len(fuera), "lista_donde_no_se_vio": fuera,
                  "unidades_que_cambia": sum(len(v["creadas"]) + len(v["quitadas"]) + len(v["cambiadas"])
                                             for v in por_to.values()),
                  "general": bool(fuera),
                  "salen_de_la_bolsa": [] if fuera else sorted(set(cambia) & set(vistos))}
    a.out.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for r, v in out.items():
        print(r, "general" if v["general"] else "NO general", v["documentos_que_cambia"], "docs;",
              v["documentos_que_cambia_donde_no_se_vio"], "donde no se vio;", v["unidades_que_cambia"], "unidades;",
              "salen de la bolsa:", v["salen_de_la_bolsa"])


if __name__ == "__main__":
    main()
