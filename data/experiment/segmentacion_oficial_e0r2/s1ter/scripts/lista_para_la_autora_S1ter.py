"""U-SEG-OFICIAL, S1-ter-b: la lista para la autora, desde las planillas marcadas (USD 0). Fijada antes de leer.

Uso: python -B lista_para_la_autora_S1ter.py --orden <tramo_b/orden_lectura_S1ter.json> --sha-orden <sha256 sellado>
       --planilla-1 <planilla de la etapa 1> --planilla-2 <planilla de la etapa 2> --out <md> [--out-json <json>]
     python -B lista_para_la_autora_S1ter.py --vacia --out <md>   (la lista vacía, con su estructura)

Despacho de S1-ter, tramo b, punto 3, con las semillas selladas en la nota del mandato de `1548843` (`:846` y `:848`):
- los errores y las dudosas de las dos etapas (y las fichas con la columna `limpieza`);
- las fichas marcadas `correcta` que traen una nota de la lectora, en las dos etapas, con la misma regla para todas: así
  llega a la autora una nota sobre la herencia de la unidad de la sección 3 de ri_oc (que cuenta como falla de la
  corrección) sin marcar esa ficha;
- 20 correctas de la etapa 1: `random.Random("U-SEG-OFICIAL:cortes:S1-ter:revision").sample(sorted(c), 20)`, con `c` = los
  ids de las unidades marcadas `correcta` (todas, si son menos de 20), como en S1-bis;
- 5 correctas de las 66 con cifra de la etapa 2: `random.Random("U-SEG-OFICIAL:1_16:S1-ter:revision").sample(sorted(c66), 5)`,
  con `c66` = los ids de las entradas marcadas `correcta` (el id de la lista en (b)), sin la regresión.
La lista usa solo los ids opacos de las fichas, sin decir a qué población pertenece cada una (decisión 6 sobre el FRENO
S1-ter-a): la población solo se usa adentro, para separar las 66 de la regresión al sortear las 5 correctas.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

SEMILLA_CORTES = "U-SEG-OFICIAL:cortes:S1-ter:revision"
SEMILLA_1_16 = "U-SEG-OFICIAL:1_16:S1-ter:revision"
COLS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
CABECERA = ["# U-SEG-OFICIAL, S1-ter — lista para la autora", "",
            "Cada ficha se nombra por su id opaco (las fichas están en la carpeta de la lectora). La lista no dice a qué "
            "población pertenece cada ficha. La autora adjudica cada fila: confirma la marca de la lectora o la cambia, con "
            "su clase y subclase.", ""]


def leer(p: Path) -> list[dict]:
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def tabla(filas: list[dict]) -> list[str]:
    L = ["| " + " | ".join(COLS) + " | adjudicación |", "|" + "---|" * (len(COLS) + 1)]
    L += ["| " + " | ".join(f.get(c, "").replace("|", "/") for c in COLS) + " |  |" for f in filas]
    return L + [""]


def armar(orden: dict | None, p1: list[dict], p2: list[dict]) -> tuple[list[str], dict]:
    f1 = {x["id_opaco"]: x for x in orden["etapa_1"]["fichas"]} if orden else {}
    f2 = {x["id_opaco"]: x for x in orden["etapa_2"]["fichas"]} if orden else {}
    malas = lambda ps: [f for f in ps if f["marca"] in ("error", "dudosa") or f["limpieza"]]
    con_nota = lambda ps: [f for f in ps if f["marca"] == "correcta" and not f["limpieza"] and f["nota"].strip()]
    c = sorted(f1[f["ficha"]]["id"] for f in p1 if f["marca"] == "correcta")
    sel = random.Random(SEMILLA_CORTES).sample(c, 20) if len(c) >= 20 else c
    op1 = {f1[k]["id"]: k for k in f1}
    c66 = sorted(f2[f["ficha"]]["id"] for f in p2 if f["marca"] == "correcta" and f2[f["ficha"]]["poblacion"] != "regresion")
    sel66 = random.Random(SEMILLA_1_16).sample(c66, 5) if len(c66) >= 5 else c66
    op2 = {f2[k]["id"]: k for k in f2 if f2[k]["poblacion"] != "regresion"}
    corr1 = sorted(op1[i] for i in sel)
    corr2 = sorted(op2[i] for i in sel66)
    por1 = {f["ficha"]: f for f in p1}
    por2 = {f["ficha"]: f for f in p2}
    L = list(CABECERA)
    L += ["## Etapa 1", "", "### Errores y dudosas", ""] + tabla(malas(p1))
    L += ["### Correctas con nota de la lectora", ""] + tabla(con_nota(p1))
    L += [f"### 20 correctas, sorteadas con `{SEMILLA_CORTES}`", ""] + tabla([por1[k] for k in corr1])
    L += ["## Etapa 2", "", "### Errores y dudosas", ""] + tabla(malas(p2))
    L += ["### Correctas con nota de la lectora", ""] + tabla(con_nota(p2))
    L += [f"### 5 correctas, sorteadas con `{SEMILLA_1_16}`", ""] + tabla([por2[k] for k in corr2])
    js = {"etapa_1": {"errores_y_dudosas": [f["ficha"] for f in malas(p1)],
                      "correctas_con_nota": [f["ficha"] for f in con_nota(p1)], "correctas_sorteadas": corr1,
                      "correctas_en_la_poblacion_del_sorteo": len(c), "semilla": SEMILLA_CORTES},
          "etapa_2": {"errores_y_dudosas": [f["ficha"] for f in malas(p2)],
                      "correctas_con_nota": [f["ficha"] for f in con_nota(p2)], "correctas_sorteadas": corr2,
                      "correctas_en_la_poblacion_del_sorteo": len(c66), "semilla": SEMILLA_1_16}}
    return L, js


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vacia", action="store_true")
    for k in ("orden", "sha_orden", "planilla_1", "planilla_2", "out_json"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.vacia:
        L, _ = armar(None, [], [])
        L[2] += " Vacía: se completa después de la lectura, con este script."
        Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
        print("lista vacía escrita")
        return
    raw = Path(a.orden).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.sha_orden, "el orden no da su sha256 sellado"
    L, js = armar(json.loads(raw), leer(Path(a.planilla_1)), leer(Path(a.planilla_2)))
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    if a.out_json:
        Path(a.out_json).write_text(json.dumps(js, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in js.items()},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
