"""
ensamblar_r1.py — B1.7: re-ensamblado determinístico → KG-Reextraído-r1
(docs/nomenclatura_grafos.md). Código puro, cero LLM, cero escrituras bajo
salida/ (sellada). Salida: corpus_v2/salida_r1/.

Etapas (cada una en su módulo nuevo; los módulos sellados se IMPORTAN):
  1. B1.6 cola humana flaggeada (r1_cola_flaggeada): las unidades de cola
     ingresan con su E1 válido y estado_e3 visible; recomputo de política.
  2. E2 por TO con e2_lib.ensamblar (paridad byte a byte con grafo_<to>.json
     cuando se corre --sin-cola) + flag estado_e3 en nodos/aristas de cola.
  3. B1.5 merge cross-TO GUARDADO (r1_invariantes.merge_grafos_guardado).
  4. B1.2 E4 determinístico (r1_e4): propuestos → catálogo, TextoOrdenado
     desde provenance, filtro de conflictos.
  5. B1.1 E5 esqueleto (r1_e5_esqueleto): build_skeleton importado + aristas
     padre_sugerido flaggeadas.
  6. B1.3 referencias norma→norma (r1_referencias).
  7. B1.4 provenance rica (r1_provenance).
  8. cierre: invariantes I1-I5, tests T1-T7 (r1_tests), kg.json + sha,
     doble corrida byte-idéntica, reporte_ensamblado_r1.json, diff de conteos
     vs KG-Reextraído sellado, tabla de propuestos antes/después de la cola.

Uso:
  .venv/bin/python3 ensamblar_r1.py                        # corrida completa (cierre)
  .venv/bin/python3 ensamblar_r1.py --hasta e4 --sin-cola  # freno A1
  .venv/bin/python3 ensamblar_r1.py --hasta referencias --sin-cola  # freno A2
"""

from __future__ import annotations

import argparse
import json
import sys

import r1_comun as C
import r1_invariantes as INV
import r1_e4 as E4

import e2_lib                                     # noqa: E402 (importado)

ETAPAS = ("e2", "merge", "e4", "esqueleto", "referencias", "provenance", "final")


def escribir(nombre: str, obj, indent: int = 1) -> None:
    C.SALIDA_R1.mkdir(parents=True, exist_ok=True)
    (C.SALIDA_R1 / nombre).write_text(
        json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


def etapa_e2(con_cola: bool) -> dict:
    out = {}
    cola_mod = None
    if con_cola:
        import r1_cola_flaggeada as COLA
        cola_mod = COLA
    for to in C.TOS_ORDEN:
        chunks = C.cargar_chunks_enm01(to)
        registros = C.cargar_extracciones_finales(to)
        info_cola = None
        if cola_mod is not None:
            registros, info_cola = cola_mod.inyectar_cola(to, registros)
        ens = e2_lib.ensamblar(chunks, registros)
        grafo = {"nodes": ens["nodes"], "edges": ens["edges"]}
        if cola_mod is not None:
            cola_mod.flaggear_grafo(grafo, info_cola)
        sha = C.sha256_bytes(C.dumps_kg(grafo).encode("utf-8"))
        out[to] = {"grafo": grafo, "ensamblado": ens, "sha": sha,
                   "paridad_sellado": sha == C.cargar_reporte_e2(to)["sha256_grafo"],
                   "cola": info_cola, "registros": registros}
    return out


def correr(con_cola: bool, hasta: str = "final", escribir_salida: bool = True) -> dict:
    """Corre el pipeline hasta la etapa `hasta`. Devuelve {kg, resumen, por_to, m, ...}."""
    h = ETAPAS.index(hasta)
    resumen: dict = {"etapas": [], "con_cola": con_cola}
    w = escribir if escribir_salida else (lambda *a, **k: None)

    por_to = etapa_e2(con_cola)
    resumen["e2_por_to"] = {to: {"nodes": len(d["grafo"]["nodes"]), "edges": len(d["grafo"]["edges"]),
                                 "sha256": d["sha"], "paridad_con_grafo_sellado": d["paridad_sellado"],
                                 "conflictos_properties": len(d["ensamblado"]["conflictos_properties"]),
                                 "cuarentena_propuestos": len(d["ensamblado"]["cuarentena"]),
                                 "rechazos_e2": len(d["ensamblado"]["rechazos_e2"]),
                                 "cola": (d["cola"] or {}).get("resumen")}
                            for to, d in por_to.items()}
    if not con_cola:
        assert all(d["paridad_sellado"] for d in por_to.values()), \
            "sin cola, E2 por TO debe reproducir grafo_<to>.json byte a byte"
    resumen["etapas"].append("e2")
    print("[e2]", json.dumps({to: (v["nodes"], v["edges"], v["paridad_con_grafo_sellado"])
                             for to, v in resumen["e2_por_to"].items()}), flush=True)
    estado = {"resumen": resumen, "por_to": por_to}
    if h == 0:
        w("resumen_parcial.json", resumen)
        return estado

    grafos = {to: d["grafo"] for to, d in por_to.items()}
    m = INV.merge_grafos_guardado(grafos)
    kg = {"nodes": m["nodes"], "edges": m["edges"]}
    inv_merge = INV.verificar_invariantes(
        kg, m["grafos_pre_merge"], merges_nodo=len(m["merges_cross_to"]),
        merges_arista=INV.merges_arista_de(m["grafos_pre_merge"], kg["edges"]))
    assert inv_merge["ok"], inv_merge["fallos"]
    resumen["merge"] = {"invariantes": inv_merge, "merges_cross_to": len(m["merges_cross_to"]),
                        "merges_por_tipo": C.conteo(m["merges_cross_to"], "type"),
                        "adjudicacion_cross_to": len(m["adjudicacion_cross_to"]),
                        "conflictos_cross_to": len(m["conflictos"])}
    w("adjudicacion_cross_to.json", m["adjudicacion_cross_to"])
    resumen["etapas"].append("merge")
    print("[merge]", json.dumps({k: v for k, v in resumen["merge"].items() if k != "invariantes"}), flush=True)
    estado.update({"kg": kg, "m": m})
    if h == 1:
        w("resumen_parcial.json", resumen)
        return estado

    catalogo = C.cargar_catalogo()
    r_prop = E4.resolver_propuestos(kg, catalogo)
    r_to = E4.canonizar_texto_ordenado(kg)
    intra = [{**c, "to": to} for to, d in por_to.items() for c in d["ensamblado"]["conflictos_properties"]]
    r_conf = E4.filtrar_conflictos(intra, m["conflictos"])
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    for tid, props in r_conf["variantes_texto_ordenado"].items():
        n = nodes_by_id.get(tid)
        if n is not None:
            for p, vals in props.items():
                n["properties"][f"{p}_variantes"] = list(vals)
    inv_e4 = INV.verificar_invariantes(kg)
    assert inv_e4["ok"], inv_e4["fallos"]
    resumen["e4"] = {
        "propuestos": {"resueltos": r_prop["n_resueltos"], "cuarentena": r_prop["n_cuarentena"],
                       "motivos": r_prop["motivos"], "aristas_reapuntadas": r_prop["aristas_reapuntadas"]},
        "texto_ordenado": {"canonicos": r_to["canonicos"],
                           "eliminados": [{"id": e["id_eliminado"], "reasignado_a": e["reasignado_a"],
                                           "n_provenances": len(e["provenances"])} for e in r_to["eliminados"]],
                           "aristas_reapuntadas": r_to["aristas_reapuntadas"],
                           "n_final": sum(1 for n in kg["nodes"] if n["type"] == "TextoOrdenado")},
        "conflictos": {k: v for k, v in r_conf.items()
                       if k in ("n_total", "n_variantes_to", "n_reales", "reales_por_tipo_property")},
        "invariantes": inv_e4,
    }
    w("e4_propuestos.json", r_prop["tabla"])
    w("e4_texto_ordenado.json", r_to)
    w("e4_conflictos.json", r_conf)
    resumen["etapas"].append("e4")
    print("[e4]", json.dumps({k: v for k, v in resumen["e4"].items() if k != "invariantes"},
                             ensure_ascii=False), flush=True)
    estado["e4_propuestos"] = r_prop["tabla"]
    if h == 2:
        w("resumen_parcial.json", resumen)
        return estado

    import r1_e5_esqueleto as E5
    r_esq = E5.inyectar_esqueleto(kg, catalogo)
    inv_e5 = INV.verificar_invariantes(kg)
    assert inv_e5["ok"], inv_e5["fallos"]
    resumen["esqueleto"] = {k: v for k, v in r_esq.items() if k != "ids_creados"}
    w("e5_esqueleto.json", r_esq)
    resumen["etapas"].append("esqueleto")
    print("[esqueleto]", json.dumps(resumen["esqueleto"], ensure_ascii=False), flush=True)
    if h == 3:
        w("resumen_parcial.json", resumen)
        return estado

    import r1_referencias as REF
    r_ref = REF.detectar_y_resolver(kg)
    inv_ref = INV.verificar_invariantes(kg)
    assert inv_ref["ok"], inv_ref["fallos"]
    resumen["referencias"] = r_ref["resumen"]
    w("referencias_remisiones.json", r_ref["remisiones"])
    w("referencias_muestra30.json", r_ref["muestra"])
    w("referencias_irresolubles.json", r_ref["irresolubles"])
    resumen["etapas"].append("referencias")
    print("[referencias]", json.dumps(r_ref["resumen"], ensure_ascii=False), flush=True)
    if h == 4:
        w("resumen_parcial.json", resumen)
        return estado

    import r1_provenance as PROV
    r_prov = PROV.enriquecer(kg, por_to)
    resumen["provenance"] = r_prov["resumen"]
    w("provenance_verificacion.json", r_prov)
    resumen["etapas"].append("provenance")
    print("[provenance]", json.dumps(r_prov["resumen"], ensure_ascii=False), flush=True)
    if h == 5:
        w("resumen_parcial.json", resumen)
        return estado

    # canonicalización final: orden estable de nodos y aristas
    kg["nodes"].sort(key=lambda n: n["id"])
    kg["edges"].sort(key=lambda e: (e["source"], e["relation"], e["target"]))
    estado["kg_json"] = C.dumps_kg(kg)
    estado["sha256"] = C.sha256_bytes(estado["kg_json"].encode("utf-8"))
    resumen["etapas"].append("final")
    return estado


def cerrar() -> int:
    import r1_tests as T
    import r1_cola_flaggeada as K

    # corrida 1 y 2 (doble corrida byte-idéntica)
    print("=== corrida 1 (con cola) ===", flush=True)
    e1 = correr(con_cola=True, escribir_salida=True)
    print("=== corrida 2 (con cola, sin escribir) ===", flush=True)
    e2 = correr(con_cola=True, escribir_salida=False)
    doble = e1["sha256"] == e2["sha256"] and e1["kg_json"] == e2["kg_json"]
    print("=== corrida sin cola hasta e4 (tabla antes/después) ===", flush=True)
    e0 = correr(con_cola=False, hasta="e4", escribir_salida=False)

    kg = e1["kg"]
    (C.SALIDA_R1 / "kg.json").write_text(e1["kg_json"], encoding="utf-8")
    sha_disco = C.sha256_path(C.SALIDA_R1 / "kg.json")

    inv = INV.verificar_invariantes(kg)
    muestra = json.loads((C.SALIDA_R1 / "referencias_muestra30_inspeccionada_A2.json").read_text(encoding="utf-8"))
    tests = T.correr_tests(kg, muestra)
    escribir("tests_respuesta_conocida_r1.json", tests)

    recomp = K.recomputar_politica()
    escribir("cola_recomputo_politica.json", recomp)

    sellado = json.loads((C.SALIDA / "kg.json").read_text(encoding="utf-8"))
    diff = {
        "nodes": {"sellado": len(sellado["nodes"]), "r1": len(kg["nodes"]),
                  "delta": len(kg["nodes"]) - len(sellado["nodes"])},
        "edges": {"sellado": len(sellado["edges"]), "r1": len(kg["edges"]),
                  "delta": len(kg["edges"]) - len(sellado["edges"])},
        "nodes_by_type": {}, "edges_by_relation": {},
    }
    a, b = C.conteo(sellado["nodes"], "type"), C.conteo(kg["nodes"], "type")
    for t in sorted(set(a) | set(b)):
        diff["nodes_by_type"][t] = {"sellado": a.get(t, 0), "r1": b.get(t, 0), "delta": b.get(t, 0) - a.get(t, 0)}
    a, b = C.conteo(sellado["edges"], "relation"), C.conteo(kg["edges"], "relation")
    for t in sorted(set(a) | set(b)):
        diff["edges_by_relation"][t] = {"sellado": a.get(t, 0), "r1": b.get(t, 0), "delta": b.get(t, 0) - a.get(t, 0)}

    def tabla_prop(t):
        return {"resueltos": sum(1 for f in t if f["estado"] == "resuelto"),
                "cuarentena": sum(1 for f in t if f["estado"] == "cuarentena"), "total": len(t)}
    antes, despues = tabla_prop(e0["e4_propuestos"]), tabla_prop(e1["e4_propuestos"])
    ids_antes = {f["id_propuesto"] for f in e0["e4_propuestos"]}
    nuevos = [f for f in e1["e4_propuestos"] if f["id_propuesto"] not in ids_antes]

    r = e1["resumen"]
    reporte = {
        "grafo": "KG-Reextraído-r1", "sha256_kg": e1["sha256"], "sha256_kg_en_disco": sha_disco,
        "doble_corrida_byte_identica": doble,
        "entrada_sellada": {"kg": C.SHA_KG_SELLADO, "reporte": C.SHA_REPORTE_SELLADO},
        "nodes_total": len(kg["nodes"]), "edges_total": len(kg["edges"]),
        "nodes_by_type": C.conteo(kg["nodes"], "type"),
        "edges_by_relation": C.conteo(kg["edges"], "relation"),
        "invariantes_final": inv,
        "e2_por_to": r["e2_por_to"],
        "merge": {k: v for k, v in r["merge"].items() if k != "invariantes"},
        "e4": {k: v for k, v in r["e4"].items() if k != "invariantes"},
        "propuestos_antes_despues_cola": {"sin_cola": antes, "con_cola": despues,
                                          "nuevos_con_cola": [{"id": f["id_propuesto"], "label": f["label"],
                                                               "estado": f["estado"], "resuelto_a": f["resuelto_a"]}
                                                              for f in nuevos]},
        "esqueleto": r["esqueleto"],
        "referencias": r["referencias"],
        "provenance": r["provenance"],
        "cola_flaggeada": {to: v["cola"] for to, v in r["e2_por_to"].items()},
        "cola_recomputo_politica": {k: recomp[k] for k in ("total", "transiciones", "caveats")},
        "tests": {k: v["pass"] for k, v in tests.items()},
        "diff_vs_sellado": diff,
        "declaraciones_esquema": [
            "referencia nodo→nodo (B1.3) no está en schema.DOMAIN_RANGE (solo TextoOrdenado→Comunicacion).",
            "padre_sugerido (E5, cuarentena flaggeada) no está en schema.DOMAIN_RANGE.",
            "schema.py no se edita en esta unidad; las aristas nuevas llevan rol_fuente.",
        ],
        "comando_neo4j_no_ejecutado": (
            "python data/experiment/neo4j/cargar_kg.py --grafo KG_Reextraido_r1  "
            "(requiere registrar KG-Reextraído-r1 en data/experiment/neo4j/grafos.py con path "
            f"corpus_v2/salida_r1/kg.json y sha256 {e1['sha256']}; cargar_kg.py verifica el sha antes de cargar)"),
    }
    escribir("reporte_ensamblado_r1.json", reporte)
    print(json.dumps({k: reporte[k] for k in ("sha256_kg", "doble_corrida_byte_identica", "nodes_total",
                                               "edges_total", "tests", "invariantes_final")},
                     ensure_ascii=False, indent=1))
    print(f"-> {C.SALIDA_R1 / 'kg.json'}")
    ok = doble and inv["ok"] and all(v["pass"] for v in tests.values()) and sha_disco == e1["sha256"]
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hasta", choices=ETAPAS, default="final")
    ap.add_argument("--sin-cola", action="store_true")
    args = ap.parse_args()
    if args.hasta == "final" and not args.sin_cola:
        return cerrar()
    correr(con_cola=not args.sin_cola, hasta=args.hasta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
