"""U-SEG-OFICIAL, S1-bis-b: la lista para la autora, desde las planillas marcadas (USD 0). Fijada antes de leer.

Uso: python -B lista_para_la_autora_S1bis.py --muestra <muestra_cortes_S1bis.json> --planilla <planilla_marcas…tsv>
       --planilla-116 <planilla_1_16…tsv> --out <json>

`acta_sorteo_S1bis.md`, §5, con las semillas selladas en `a757b32`:
- los errores y las dudosas del primer grupo y de ri_spi; los juicios dudosos;
- 20 correctas: `random.Random("U-SEG-OFICIAL:cortes:S1-bis:revision").sample(sorted(c), 20)`, con `c` = las unidades
  marcadas `correcta` del primer grupo y de ri_spi (todas, si son menos de 20);
- del censo del 1.16: los marcados con error y los dudosos, y 5 correctos:
  `random.Random("U-SEG-OFICIAL:1_16:S1-bis:revision").sample(sorted(c116), 5)`, con `c116` = los candidatos `correcta`.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

SEMILLA_REVISION = "U-SEG-OFICIAL:cortes:S1-bis:revision"
SEMILLA_1_16 = "U-SEG-OFICIAL:1_16:S1-bis:revision"


def leer(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def lista(muestra: dict, planilla: list[dict], planilla116: list[dict]) -> dict:
    leidas = [f for f in planilla if f["grupo"].startswith("G1-") or f["grupo"] == "ri_spi"]
    juicios = [f for f in planilla if f["grupo"] == "G3-juicio"]
    correctas = sorted(f["id"] for f in leidas if f["marca"] == "correcta")
    sel = random.Random(SEMILLA_REVISION).sample(correctas, 20) if len(correctas) >= 20 else correctas
    c116 = sorted(f["id"] for f in planilla116 if f["marca"] == "correcta")
    sel116 = random.Random(SEMILLA_1_16).sample(c116, 5) if len(c116) >= 5 else c116
    fila = lambda f: {k: f[k] for k in ("fila", "grupo", "id", "to", "paginas", "marca", "clase", "subclase",
                                        "subclase_adicional", "limpieza", "nota")}
    return {"errores_y_dudosas": [fila(f) for f in leidas if f["marca"] in ("error", "dudosa") or f["limpieza"]],
            "juicios_dudosos": [fila(f) for f in juicios if f["marca"] == "dudosa"],
            "correctas_sorteadas": {"semilla": SEMILLA_REVISION, "poblacion": len(correctas),
                                    "ids": sel, "filas": [fila(f) for f in leidas if f["id"] in set(sel)]},
            "censo_1_16": {"marcados_y_dudosos": [fila(f) for f in planilla116 if f["marca"] in ("error", "dudosa")],
                           "correctos_sorteados": {"semilla": SEMILLA_1_16, "poblacion": len(c116), "ids": sel116,
                                                   "filas": [fila(f) for f in planilla116 if f["id"] in set(sel116)]}}}


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("muestra", "planilla", "planilla_116", "out"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, type=Path, required=True)
    a = ap.parse_args()
    m = json.loads(a.muestra.read_text(encoding="utf-8"))
    res = lista(m, leer(a.planilla), leer(a.planilla_116))
    a.out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"errores_y_dudosas": len(res["errores_y_dudosas"]), "juicios_dudosos": len(res["juicios_dudosos"]),
                      "correctas_sorteadas": len(res["correctas_sorteadas"]["ids"]),
                      "1_16_marcados_y_dudosos": len(res["censo_1_16"]["marcados_y_dudosos"]),
                      "1_16_correctos_sorteados": len(res["censo_1_16"]["correctos_sorteados"]["ids"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
