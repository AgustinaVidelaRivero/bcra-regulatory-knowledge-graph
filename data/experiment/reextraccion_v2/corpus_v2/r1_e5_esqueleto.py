"""
r1_e5_esqueleto.py — B1.1: E5 esqueleto. Inyecta clases, instancias y roles
del catálogo (esquema_v2_clases.json) y las aristas subclase_de /
instancia_de / parte_de / miembro_de usando build_skeleton() IMPORTADO de
data/experiment/grafo_v2/code/assemble.py (no se porta ni se reescribe),
con paridad verificada contra KG-Refinado (reensamblado_v3/kg.json,
rol_fuente=esqueleto: 70 nodos / 82 aristas) por id y por tripla.

Reglas:
  - Nodo Sujeto del catálogo ya presente en el grafo (extraído): se conserva
    con sus provenances de extracción y se le AGREGA la provenance de
    esqueleto (rol_documental=esqueleto) — aditivo.
  - Nodo del catálogo ausente: se crea desde build_skeleton con provenance
    de esqueleto únicamente.
  - Aristas de esqueleto: provenance {to: null, archivo: source_doc,
    punto: location, rol_documental: "esqueleto"}, rol_fuente=esqueleto.
  - Propuestos en cuarentena con padre_sugerido: arista
    `padre_sugerido` (NO subclase_de) propuesto → padre, flaggeada
    (rol_fuente=cuarentena_flaggeada, properties.flag=padre_sugerido_no_laudado).
    Sin padre_sugerido: sin arista (nada se inventa).
  - `padre_sugerido` no está en DOMAIN_RANGE de schema.py (declarado en el
    reporte; no se edita el esquema).
"""

from __future__ import annotations

import r1_comun as C

import assemble                                   # noqa: E402 (importado)
from schema import RELACIONES_ESQUELETO           # noqa: E402

REL_PADRE_SUGERIDO = "padre_sugerido"


def _prov_esqueleto(p: dict) -> dict:
    return {"to": None, "archivo": p.get("source_doc"), "punto": p.get("location"),
            "rol_documental": "esqueleto"}


def paridad_con_kg_refinado(nodes_by_id: dict, edges_set: dict) -> dict:
    import json
    ref = json.loads(C.KG_REFINADO.read_text(encoding="utf-8"))
    ids_ref = {n["id"] for n in ref["nodes"] if n.get("rol_fuente") == "esqueleto"}
    trip_ref = {(e["source"], e["relation"], e["target"]) for e in ref["edges"]
                if e.get("rol_fuente") == "esqueleto"}
    return {"nodos_build_skeleton": len(nodes_by_id), "nodos_kg_refinado": len(ids_ref),
            "paridad_ids": set(nodes_by_id) == ids_ref,
            "aristas_build_skeleton": len(edges_set), "aristas_kg_refinado": len(trip_ref),
            "paridad_triplas": set(edges_set) == trip_ref,
            "solo_en_build": sorted(set(nodes_by_id) - ids_ref),
            "solo_en_refinado": sorted(ids_ref - set(nodes_by_id))}


def inyectar_esqueleto(kg: dict, catalogo: dict) -> dict:
    nodes_sk, edges_sk, counts_sk = assemble.build_skeleton()
    paridad = paridad_con_kg_refinado(nodes_sk, edges_sk)
    if not (paridad["paridad_ids"] and paridad["paridad_triplas"]):
        raise RuntimeError(f"build_skeleton sin paridad con KG-Refinado: {paridad}")

    antes_rel = C.conteo(kg["edges"], "relation")
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    creados, enriquecidos = [], []
    for sid, sk in nodes_sk.items():
        prov = _prov_esqueleto(sk["provenance"])
        n = nodes_by_id.get(sid)
        if n is None:
            n = {"id": sid, "type": "Sujeto", "label": sk["label"],
                 "properties": dict(sk["properties"]),
                 "provenance": prov, "provenances": [prov], "rol_fuente": "esqueleto"}
            kg["nodes"].append(n)
            nodes_by_id[sid] = n
            creados.append(sid)
        else:
            for k, v in sk["properties"].items():
                n["properties"].setdefault(k, v)
            if C.prov_key(prov) not in {C.prov_key(p) for p in n["provenances"]}:
                n["provenances"].append(prov)
            n["rol_fuente"] = "extraido+esqueleto"
            enriquecidos.append(sid)

    triplas = {(e["source"], e["relation"], e["target"]) for e in kg["edges"]}
    n_esq = 0
    for (s, r, t), e in edges_sk.items():
        if (s, r, t) in triplas:
            continue
        prov = _prov_esqueleto(e["provenance"])
        kg["edges"].append({"source": s, "target": t, "relation": r,
                            "provenance": prov, "provenances": [prov],
                            "rol_fuente": "esqueleto"})
        triplas.add((s, r, t))
        n_esq += 1

    # padre_sugerido flaggeado para los propuestos en cuarentena
    flag, sin_padre, padre_fuera = [], [], []
    for n in kg["nodes"]:
        if n["type"] != "Sujeto" or n["properties"].get("nivel") != "propuesto":
            continue
        padre = n["properties"].get("padre_sugerido")
        if not padre:
            sin_padre.append(n["id"])
            continue
        if padre not in nodes_sk:
            padre_fuera.append((n["id"], padre))   # jamás se inventa el padre
            continue
        k = (n["id"], REL_PADRE_SUGERIDO, padre)
        if k in triplas:
            continue
        prov = dict(n["provenance"])
        kg["edges"].append({"source": n["id"], "target": padre, "relation": REL_PADRE_SUGERIDO,
                            "provenance": prov, "provenances": [dict(p) for p in n["provenances"]],
                            "rol_fuente": "cuarentena_flaggeada",
                            "properties": {"flag": "padre_sugerido_no_laudado"}})
        triplas.add(k)
        flag.append(k)

    despues_rel = C.conteo(kg["edges"], "relation")
    return {
        "paridad_kg_refinado": {k: v for k, v in paridad.items()},
        "conteos_build_skeleton": counts_sk,
        "nodos_esqueleto_creados": len(creados),
        "nodos_esqueleto_enriquecidos": len(enriquecidos),
        "aristas_esqueleto_agregadas": n_esq,
        "aristas_padre_sugerido_flaggeadas": len(flag),
        "propuestos_sin_padre": sin_padre,
        "propuestos_padre_fuera_de_catalogo": padre_fuera,
        "relaciones_antes": {r: antes_rel.get(r, 0) for r in RELACIONES_ESQUELETO + (REL_PADRE_SUGERIDO,)},
        "relaciones_despues": {r: despues_rel.get(r, 0) for r in RELACIONES_ESQUELETO + (REL_PADRE_SUGERIDO,)},
        "declaracion_esquema": "padre_sugerido no está en schema.DOMAIN_RANGE; arista flaggeada "
                               "de cuarentena, no subclase_de. No se edita schema.py.",
        "ids_creados": creados,
    }
