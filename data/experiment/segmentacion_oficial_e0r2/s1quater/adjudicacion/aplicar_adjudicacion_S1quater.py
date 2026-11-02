"""U-SEG-OFICIAL, S1-quater: aplica la adjudicación de la autora a las planillas de la lectora (mesa, 13/10/2026; USD 0). Sellado
antes de que la autora abra la pasada 1 (`sello_scripts_adjudicacion_S1quater_mesa.txt`).

Adaptado de `s1ter/scripts/aplicar_adjudicacion_S1ter.py`. Regla de la autora del 13/10/2026 (hoja de ruta de la mesa, §92): rige todo
lo del criterio final de S1-ter que dice cómo se juzga una unidad o cómo se cuenta la cifra; no rige lo que dependía de poblaciones o de
incidentes de S1-ter que S1-quater no tiene. Por eso no están:
- la regla del cierre de las 34 listas de (b) de la 1.16, con su reversión por lista (en S1-ter, un error confirmado en la unidad que
  sigue contaba como error de la lista solo en esas fichas);
- la regla de la herencia en la unidad de la sección 3 de ri_oc (en S1-ter, contaba como falla de la corrección de ri_oc).
Queda lo que S1-ter hacía en cualquier otra ficha: un error confirmado en la unidad que sigue, o en lo heredado, se registra en el JSON
y no cuenta; la marca de la fila no cambia por eso.

Uso: python3 -B aplicar_adjudicacion_S1quater.py --planilla-1 <planilla sellada de la etapa 1> --sha-planilla-1 <sha256 de su sello>
       --planilla-2 <de la etapa 2> --sha-planilla-2 <sha256> --orden <orden de lectura de S1-quater> --sha-orden <sha256 sellado>
       --adjudicacion-1 <tsv> --adjudicacion-2 <tsv> --out-planilla-1 <tsv> --out-planilla-2 <tsv> --out-json <json>

Entrada:
- las dos planillas de la lectora (columnas `ficha`, `paginas`, `marca`, `clase`, `subclase`, `subclase_adicional`, `limpieza`,
  `nota`), con el sha256 de su sello; el orden, con su sha256 sellado;
- un archivo de adjudicación por etapa (la salida de `pasada_2_S1quater.py armar`), con las columnas `ficha`, `marca`, `clase`,
  `subclase`, `subclase_adicional`, `limpieza`, `la_que_sigue`, `clase_que_sigue`, `subclase_que_sigue`, `herencia`, `nota`.
Reglas del script:
- la marca de la autora reemplaza a la de la lectora en las fichas que adjudica (`marca`, `clase`, `subclase`, `subclase_adicional` y
  `limpieza`); `nota` queda la de la autora si trae una, y si no, la de la lectora;
- `la_que_sigue` = `error` (solo en la etapa 2), con su clase y su subclase válidas: se registra y no cuenta;
- `herencia` = `error`: se registra y no cuenta;
- la fila adjudicada se valida con las reglas de `cifras_lectura_S1quater.py`.
Salida: una planilla adjudicada por etapa, con las columnas de la de la lectora, y el JSON. Un archivo mal formado se rechaza sin
escribir nada; si una salida ya existe, también.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cifras_lectura_S1quater as C  # noqa: E402

COLS = C.COLS
ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
MARCA = ("marca", "clase", "subclase", "subclase_adicional", "limpieza")


class MalFormado(Exception):
    pass


def leer_tsv(texto: str, columnas: tuple[str, ...], nombre: str) -> list[dict]:
    r = csv.DictReader(io.StringIO(texto, newline=""), delimiter="\t")
    if tuple(r.fieldnames or ()) != columnas:
        raise MalFormado(f"{nombre}: columnas {r.fieldnames}, se esperaban {list(columnas)}")
    filas = list(r)
    if any(None in f or any(v is None for v in f.values()) for f in filas) or len(filas) != texto.count("\n") - 1:
        raise MalFormado(f"{nombre}: renglón con otra cantidad de columnas")
    return filas


def escribir_tsv(filas: list[dict]) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=COLS, delimiter="\t", lineterminator="\n")
    w.writeheader()
    for f in filas:
        w.writerow({c: f[c] for c in COLS})
    return s.getvalue()


def aplicar(planillas: dict[int, list[dict]], adjud: dict[int, list[dict]], orden: dict) -> tuple[dict, dict]:
    salida, reg = {}, {"cierres_confirmados": [], "herencias_confirmadas": [], "fichas_adjudicadas": {}}
    for etapa in (1, 2):
        fichas = {x["id_opaco"]: x for x in orden[f"etapa_{etapa}"]["fichas"]}
        lec = planillas[etapa]
        if sorted(f["ficha"] for f in lec) != sorted(fichas) or len({f["ficha"] for f in lec}) != len(lec):
            raise MalFormado(f"planilla de la etapa {etapa}: no trae una vez cada ficha del orden sellado")
        por_ficha = {f["ficha"]: dict(f) for f in lec}
        vistos = set()
        for a in adjud[etapa]:
            op = a["ficha"]
            if op not in fichas or op in vistos:
                raise MalFormado(f"adjudicación de la etapa {etapa}: ficha desconocida o repetida «{op}»")
            vistos.add(op)
            if a["la_que_sigue"] not in ("", "error") or a["herencia"] not in ("", "error"):
                raise MalFormado(f"{op}: la_que_sigue o herencia con un valor que no es «error» ni vacío")
            if a["la_que_sigue"] == "error":
                if etapa == 1:
                    raise MalFormado(f"{op}: en la etapa 1 no hay unidad que sigue")
                validas = C.SUBCLASES_CORTE if a["clase_que_sigue"] == "corte" else (
                    C.SUBCLASES_LIMPIEZA if a["clase_que_sigue"] == "limpieza" else set())
                if a["subclase_que_sigue"] not in validas:
                    raise MalFormado(f"{op}: clase o subclase de la unidad que sigue no válidas")
            elif a["clase_que_sigue"] or a["subclase_que_sigue"]:
                raise MalFormado(f"{op}: clase de la unidad que sigue sin «error» en la_que_sigue")
            if etapa == 1 and a["herencia"]:
                raise MalFormado(f"{op}: en la etapa 1 no se marca la herencia")
            fila = por_ficha[op]
            antes = {k: fila[k] for k in MARCA}
            for k in MARCA:
                fila[k] = a[k]
            if a["nota"].strip():
                fila["nota"] = a["nota"]
            err = C.validar([fila])
            if err:
                raise MalFormado(f"marca de la autora no válida: {err}")
            if a["la_que_sigue"] == "error":
                reg["cierres_confirmados"].append({
                    "ficha": op, "clase_de_la_fila": fila["clase"] if fila["marca"] == "error" else None,
                    "clase_que_sigue": a["clase_que_sigue"], "subclase_que_sigue": a["subclase_que_sigue"], "cuenta": False,
                    "por_que": "se registra y no cuenta; la marca de la fila no cambia"})
            if a["herencia"] == "error":
                reg["herencias_confirmadas"].append({"ficha": op, "cuenta": False,
                                                     "por_que": "se registra y no cuenta; la marca de la fila no cambia"})
            reg["fichas_adjudicadas"][op] = {"lectora": antes, "adjudicada": {k: fila[k] for k in MARCA}}
        salida[etapa] = [por_ficha[f["ficha"]] for f in lec]
    return salida, reg


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("planilla_1", "sha_planilla_1", "planilla_2", "sha_planilla_2", "orden", "sha_orden", "adjudicacion_1",
              "adjudicacion_2", "out_planilla_1", "out_planilla_2", "out_json"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    a = ap.parse_args()
    try:
        if any(Path(p).exists() for p in (a.out_planilla_1, a.out_planilla_2, a.out_json)):
            raise MalFormado("una salida ya existe")
        crudos = {}
        for nombre, ruta, esperado in (("orden", a.orden, a.sha_orden), ("planilla 1", a.planilla_1, a.sha_planilla_1),
                                       ("planilla 2", a.planilla_2, a.sha_planilla_2)):
            crudos[nombre] = Path(ruta).read_bytes()
            if hashlib.sha256(crudos[nombre]).hexdigest() != esperado:
                raise MalFormado(f"{nombre}: no da su sha256 sellado")
        orden = json.loads(crudos["orden"])
        planillas = {e: leer_tsv(crudos[f"planilla {e}"].decode("utf-8"), COLS, f"planilla {e}") for e in (1, 2)}
        adjud = {e: leer_tsv(Path(getattr(a, f"adjudicacion_{e}")).read_text(encoding="utf-8"), ADJ, f"adjudicación {e}")
                 for e in (1, 2)}
        salida, reg = aplicar(planillas, adjud, orden)
    except MalFormado as ex:
        raise SystemExit(f"RECHAZADO: {ex}")
    Path(a.out_planilla_1).write_text(escribir_tsv(salida[1]), encoding="utf-8")
    Path(a.out_planilla_2).write_text(escribir_tsv(salida[2]), encoding="utf-8")
    Path(a.out_json).write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"fichas_adjudicadas": len(reg["fichas_adjudicadas"]), "cierres_confirmados": len(reg["cierres_confirmados"]),
                      "herencias_confirmadas": len(reg["herencias_confirmadas"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
