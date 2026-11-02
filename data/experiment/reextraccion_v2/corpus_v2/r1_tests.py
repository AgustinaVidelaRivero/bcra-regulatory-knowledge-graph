"""
r1_tests.py — B1.7: tests de respuesta conocida de KG-Reextraído-r1.
  T1-T3: los del ensamblador actual (ensamblar_corpus.tests_respuesta_conocida,
         IMPORTADO): BKL-0024 ext 3.9 con USD 200; cláusula 125 % separada;
         salvedad mutuales/cooperativas pro 1.1.2.5.
  T4 esqueleto: paridad con KG-Refinado (70 nodos / 82 aristas rol_fuente=
         esqueleto, por id y por tripla) presentes en r1.
  T5 referencias: las 30 aristas inspeccionadas (muestra sellada en el freno
         A2, corrida sin cola) existen en r1 con la misma evidencia.
  T6 TextoOrdenado = 5, uno por TO, id canónico desde provenance.
  T7 cuarentena sin padre inventado: todo Sujeto propuesto tiene nivel=
         propuesto + cuarentena=true; toda arista padre_sugerido apunta a un
         id del catálogo; ningún subclase_de sale de un propuesto; ningún
         Sujeto fuera del catálogo que no sea propuesto.
"""

from __future__ import annotations

import json

import r1_comun as C
import ensamblar_corpus as EC                      # noqa: E402 (importado)
from schema import SUJETOS_CATALOGO_SET, RELACIONES_ESQUELETO   # noqa: E402


def correr_tests(kg: dict, muestra30_sellada: list[dict]) -> dict:
    res = EC.tests_respuesta_conocida(kg)
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}

    # T4
    ref = json.loads(C.KG_REFINADO.read_text(encoding="utf-8"))
    ids_ref = {n["id"] for n in ref["nodes"] if n.get("rol_fuente") == "esqueleto"}
    trip_ref = {(e["source"], e["relation"], e["target"]) for e in ref["edges"]
                if e.get("rol_fuente") == "esqueleto"}
    trip_r1 = {(e["source"], e["relation"], e["target"]) for e in kg["edges"]
               if e["relation"] in RELACIONES_ESQUELETO}
    falt_n = sorted(ids_ref - set(nodes_by_id))
    falt_t = sorted(trip_ref - trip_r1)
    res["T4_esqueleto_paridad_kg_refinado"] = {
        "pass": not falt_n and not falt_t and len(trip_r1) == 82,
        "nodos_esqueleto_esperados": len(ids_ref), "faltan_nodos": falt_n,
        "aristas_esqueleto_r1": len(trip_r1), "faltan_triplas": falt_t}

    # T5
    trip_ev = {(e["source"], e["target"]): (e.get("properties") or {}).get("evidencia")
               for e in kg["edges"] if e["relation"] == "referencia"}
    fallas = []
    for x in muestra30_sellada:
        ev = trip_ev.get((x["source"], x["target"]))
        if ev is None or ev != x["evidencia_verbatim"]:
            fallas.append({"n": x["n"], "source": x["source"], "target": x["target"],
                           "presente": ev is not None})
    res["T5_referencias_muestra30"] = {"pass": not fallas, "n_muestra": len(muestra30_sellada),
                                       "fallas": fallas}

    # T6
    tos = [n for n in kg["nodes"] if n["type"] == "TextoOrdenado"]
    ids_esp = {f"TextoOrdenado_{__import__('e2_lib').slugify_full(C.archivo_de_to(to))}"
               for to in C.TOS_ORDEN}
    res["T6_texto_ordenado_5"] = {"pass": len(tos) == 5 and {n["id"] for n in tos} == ids_esp,
                                  "n": len(tos), "ids": sorted(n["id"] for n in tos)}

    # T7
    prop = [n for n in kg["nodes"] if n["type"] == "Sujeto"
            and n["properties"].get("nivel") == "propuesto"]
    malos = []
    for n in prop:
        # cuarentena con el criterio de `en_cuarentena` (scripts/shapes_validator.py):
        # True (generación 2) o la string "true" (generación 3); U-R2-CODIGO, R4.c
        c = n["properties"].get("cuarentena")
        if not (c is True or (isinstance(c, str) and c.strip().lower() == "true")):
            malos.append((n["id"], "sin cuarentena=true"))
        if n["id"] in SUJETOS_CATALOGO_SET:
            malos.append((n["id"], "propuesto con id de catálogo"))
    for e in kg["edges"]:
        if e["relation"] == "padre_sugerido" and e["target"] not in SUJETOS_CATALOGO_SET:
            malos.append((e["source"], f"padre_sugerido a {e['target']} fuera de catálogo"))
        if e["relation"] == "subclase_de" and nodes_by_id[e["source"]]["properties"].get("nivel") == "propuesto":
            malos.append((e["source"], "subclase_de desde propuesto"))
    fuera = [n["id"] for n in kg["nodes"] if n["type"] == "Sujeto"
             and n["id"] not in SUJETOS_CATALOGO_SET and n["properties"].get("nivel") != "propuesto"]
    res["T7_cuarentena_sin_padre_inventado"] = {
        "pass": not malos and not fuera, "n_propuestos": len(prop),
        "n_padre_sugerido": sum(1 for e in kg["edges"] if e["relation"] == "padre_sugerido"),
        "malos": malos, "sujetos_fuera_catalogo_no_propuestos": fuera}
    return res
