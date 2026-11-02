"""U-SEG-OFICIAL, S1-ter-b2: aplica la adjudicación de la autora a las planillas de la lectora (USD 0). Fijado antes de
la lectura.

Uso: python -B aplicar_adjudicacion_S1ter.py --planilla-1 <planilla sellada de la etapa 1> --planilla-2 <de la etapa 2>
       [--sha-planilla-1 <sha256> --sha-planilla-2 <sha256>]
       --orden <tramo_b/orden_lectura_S1ter.json> --sha-orden <sha256 sellado>
       --poblaciones-finales <tramo_b/poblaciones_finales_S1ter.json> --sha-poblaciones-finales <sha256 sellado>
       --adjudicacion-1 <tsv> --adjudicacion-2 <tsv>
       --out-planilla-1 <tsv> --out-planilla-2 <tsv> --out-json <json>

Reglas de la autora, decididas antes de leer (10/10/2026, decisiones sobre el FRENO S1-ter-b, punto 7):
- **El cierre.** En las listas de (b), un error en el cierre (la unidad que sigue) que la autora confirme al adjudicar
  cuenta como error de la lista, con su clase. La reversión por lista vale solo para errores de corte: es lo que movió
  R5-a (decisión 4 sobre el FRENO S1-ter-a). En las demás fichas, esas notas se registran y no cuentan.
- **La herencia.** En la unidad de la sección 3 de ri_oc, una herencia que la autora confirme cuenta como falla de la
  corrección de ri_oc (despacho, tramo b, punto 4). En cualquier otra ficha se registra y no cuenta.

Entrada:
- las dos planillas de la lectora (columnas `ficha`, `paginas`, `marca`, `clase`, `subclase`, `subclase_adicional`,
  `limpieza`, `nota`), con sus sha256 si se pasan; el orden y las poblaciones finales, con sus sha256 sellados;
- un archivo de adjudicación por etapa, TSV con las columnas `ficha`, `marca`, `clase`, `subclase`,
  `subclase_adicional`, `limpieza`, `la_que_sigue`, `clase_que_sigue`, `subclase_que_sigue`, `herencia`, `nota`. Trae
  solo las fichas que la autora adjudica. Las seis primeras columnas son su marca de la ficha, con los valores de la
  planilla. `la_que_sigue` es `error` si confirma un error en la unidad que sigue, con su clase y su subclase, y queda
  vacía si no lo confirma (en la etapa 1, siempre vacía: no hay unidad que sigue). `herencia` es `error` si confirma un
  error en el texto heredado de la ficha, y queda vacía si no lo confirma.

Reglas del script:
- la marca de la autora reemplaza a la de la lectora en las fichas que adjudica (`marca`, `clase`, `subclase`,
  `subclase_adicional` y `limpieza`); `nota` queda la de la autora si trae una, y si no, la de la lectora;
- si `la_que_sigue` = `error` y la ficha es una de las 34 listas de (b) (`c116_b.listas` de las poblaciones finales), la
  fila queda `marca` = `error`, con la clase y la subclase del error de la unidad que sigue. Si la fila ya era un error,
  `corte` prevalece sobre `limpieza`: el error de limpieza que pierde pasa a la columna `limpieza`, y un segundo error de
  corte, a `subclase_adicional` si está vacía;
- el JSON registra las dos clases; la reversión por lista vale solo para un error de corte en el cierre;
- en cualquier otra ficha, el error confirmado en la unidad que sigue se registra en el JSON y la fila no cambia;
- si `herencia` = `error`, se registra en el JSON: en la unidad de la sección 3 de ri_oc cuenta como falla de la
  corrección de ri_oc; en cualquier otra ficha, no cuenta. La marca de la fila no cambia por esto.
Salida: una planilla adjudicada por etapa, con las columnas de la de la lectora (la que lee `cifras_lectura_S1ter.py`,
sin cambios), y el JSON. Un archivo mal formado se rechaza sin escribir nada.
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
import cifras_lectura_S1ter as C  # noqa: E402

COLS = ("ficha", "paginas", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "nota")
ADJ = ("ficha", "marca", "clase", "subclase", "subclase_adicional", "limpieza", "la_que_sigue", "clase_que_sigue",
       "subclase_que_sigue", "herencia", "nota")
MARCA = ("marca", "clase", "subclase", "subclase_adicional", "limpieza")


class MalFormado(Exception):
    pass


def leer_tsv(texto: str, columnas: tuple[str, ...], nombre: str) -> list[dict]:
    r = csv.DictReader(io.StringIO(texto), delimiter="\t")
    if tuple(r.fieldnames or ()) != columnas:
        raise MalFormado(f"{nombre}: columnas {r.fieldnames}, se esperaban {list(columnas)}")
    filas = list(r)
    for f in filas:
        if None in f or any(v is None for v in f.values()):
            raise MalFormado(f"{nombre}: renglón con otra cantidad de columnas")
    return filas


def escribir_tsv(filas: list[dict]) -> str:
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=COLS, delimiter="\t", lineterminator="\n")
    w.writeheader()
    for f in filas:
        w.writerow({c: f[c] for c in COLS})
    return s.getvalue()


def aplicar(planillas: dict[int, list[dict]], adjud: dict[int, list[dict]], orden: dict, finales: dict) -> tuple[dict, dict]:
    listas_b = set(finales["c116_b"]["listas"])
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
            fila = por_ficha[op]
            antes = {k: fila[k] for k in MARCA}
            for k in MARCA:
                fila[k] = a[k]
            if a["nota"].strip():
                fila["nota"] = a["nota"]
            err = C.validar([fila])
            if err:
                raise MalFormado(f"marca de la autora no válida: {err}")
            autora = {k: fila[k] for k in MARCA}
            entrada = fichas[op]["id"]
            if a["la_que_sigue"] == "error":
                cq, sq = a["clase_que_sigue"], a["subclase_que_sigue"]
                es_lista = entrada in listas_b
                rec = {"ficha": op, "clase_de_la_fila_de_la_autora": fila["clase"] if fila["marca"] == "error" else None,
                       "clase_que_sigue": cq, "subclase_que_sigue": sq, "cuenta": es_lista}
                if es_lista:
                    if fila["marca"] != "error":
                        fila.update({"marca": "error", "clase": cq, "subclase": sq, "subclase_adicional": ""})
                    elif fila["clase"] == "corte":
                        if cq == "corte" and not fila["subclase_adicional"] and sq != fila["subclase"]:
                            fila["subclase_adicional"] = sq
                        if cq == "limpieza" and not fila["limpieza"]:
                            fila["limpieza"] = sq
                    else:  # la fila era un error de limpieza
                        if cq == "corte":
                            perdida = fila["limpieza"] or fila["subclase"]
                            fila.update({"clase": "corte", "subclase": sq, "subclase_adicional": "", "limpieza": perdida})
                        elif not fila["subclase_adicional"] and sq != fila["subclase"]:
                            fila["subclase_adicional"] = sq
                    rec.update({"clase_de_la_fila_adjudicada": fila["clase"], "revierte_por_lista": cq == "corte",
                                "por_que": ("error de corte en el cierre de una lista de (b): cuenta como error de la lista "
                                            "y revierte por lista (es lo que movió R5-a)") if cq == "corte" else
                                           ("error de limpieza en el cierre de una lista de (b): cuenta como error de la "
                                            "lista y no revierte (la reversión vale solo para errores de corte)")})
                else:
                    rec.update({"clase_de_la_fila_adjudicada": fila["clase"] if fila["marca"] == "error" else None,
                                "revierte_por_lista": False,
                                "por_que": "la ficha no es una de las 34 listas de (b): se registra y no cuenta"})
                reg["cierres_confirmados"].append(rec)
            if a["herencia"] == "error":
                sec3 = fichas[op].get("poblacion") == "c116_b:seccion_3_ri_oc"
                reg["herencias_confirmadas"].append({
                    "ficha": op, "cuenta_como_falla_de_la_correccion_de_ri_oc": sec3,
                    "por_que": ("unidad de la sección 3 de ri_oc: cuenta como falla de la corrección (despacho, tramo b, "
                                "punto 4); la marca de la fila no cambia") if sec3 else
                               "otra ficha: se registra y no cuenta; la marca de la fila no cambia"})
            err = C.validar([fila])
            if err:
                raise MalFormado(f"la fila adjudicada no es válida: {err}")
            reg["fichas_adjudicadas"][op] = {"lectora": antes, "autora": autora,
                                             "adjudicada": {k: fila[k] for k in MARCA}}
        salida[etapa] = [por_ficha[f["ficha"]] for f in lec]
    return salida, reg


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("planilla_1", "planilla_2", "orden", "sha_orden", "poblaciones_finales", "sha_poblaciones_finales",
              "adjudicacion_1", "adjudicacion_2", "out_planilla_1", "out_planilla_2", "out_json"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, required=True)
    for k in ("sha_planilla_1", "sha_planilla_2"):
        ap.add_argument(f"--{k.replace('_', '-')}", dest=k, default=None)
    a = ap.parse_args()
    try:
        crudos = {}
        for nombre, ruta, esperado in (("orden", a.orden, a.sha_orden),
                                       ("poblaciones finales", a.poblaciones_finales, a.sha_poblaciones_finales),
                                       ("planilla 1", a.planilla_1, a.sha_planilla_1),
                                       ("planilla 2", a.planilla_2, a.sha_planilla_2)):
            crudos[nombre] = Path(ruta).read_bytes()
            if esperado and hashlib.sha256(crudos[nombre]).hexdigest() != esperado:
                raise MalFormado(f"{nombre}: no da su sha256 sellado")
        orden = json.loads(crudos["orden"])
        finales = json.loads(crudos["poblaciones finales"])
        planillas = {e: leer_tsv(crudos[f"planilla {e}"].decode("utf-8"), COLS, f"planilla {e}") for e in (1, 2)}
        adjud = {1: leer_tsv(Path(a.adjudicacion_1).read_text(encoding="utf-8"), ADJ, "adjudicación 1"),
                 2: leer_tsv(Path(a.adjudicacion_2).read_text(encoding="utf-8"), ADJ, "adjudicación 2")}
        salida, reg = aplicar(planillas, adjud, orden, finales)
    except MalFormado as ex:
        raise SystemExit(f"RECHAZADO: {ex}")
    Path(a.out_planilla_1).write_text(escribir_tsv(salida[1]), encoding="utf-8")
    Path(a.out_planilla_2).write_text(escribir_tsv(salida[2]), encoding="utf-8")
    Path(a.out_json).write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"fichas_adjudicadas": len(reg["fichas_adjudicadas"]),
                      "cierres_confirmados": len(reg["cierres_confirmados"]),
                      "herencias_confirmadas": len(reg["herencias_confirmadas"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
