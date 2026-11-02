"""
ensamblar_tanda0.py — U-TANDA0-2A (E1c, gate 1 del pre-registro): cableado
de r1 para un MANIFIESTO DE ENSAMBLADO. Código puro, cero LLM. Ningún módulo
sellado se edita: todos se IMPORTAN y sus rutas y tablas se REDIRIGEN EN
MEMORIA (monkeypatch de atributos de módulo, precedente del gate 6:
scripts/metricas_intrinsecas.py --reensamblar-r1, que redirige
r1_comun.SALIDA_R1 y llama ensamblar_r1.correr sin editar).

Produce, para un manifiesto de ensamblado (tanda0_ens_*.json o
desarrollo_5tos.json) y un directorio de ENTRADA con las salidas E1→E3 por TO
(runner_corpus.py --salida: <to>/grafo_<to>.json, reporte_e2_<to>.json,
extracciones_finales_<to>.jsonl, finales.jsonl, extracciones_e1_compact.jsonl):

  <salida>/kg.json                    E5 de ensamblar_corpus.ensamblar (merge
                                      determinístico + esqueleto v3 POR PERFIL
                                      + suite de tests si el manifiesto la declara)
  <salida>/reporte_ensamblado.json    reporte de ensamblar_corpus
  <salida>/r1/kg.json                 cadena r1 (E2 con cola flaggeada → merge
                                      guardado → E4 determinístico → esqueleto →
                                      referencias → provenance rica → orden final)
  <salida>/r1/*.json                  los mismos intermedios que salida_r1/
  <salida>/r1/reporte_ensamblado_r1.json

POR QUÉ UNA RÉPLICA DE LA CADENA Y NO ensamblar_r1.correr TAL CUAL. La cadena
de ensamblar_r1.correr (ensamblar_r1.py:72-194) está cableada al corpus de
desarrollo en cuatro puntos que un corpus con perfil v3_b54 no puede
compartir:
  (a) etapa_e2 llama e2_lib.ensamblar(chunks, registros) sin `esquema` ni
      `labels_catalogo` del perfil (ensamblar_r1.py:61), mientras la corrida
      E2 del runner sí los pasa (runner_corpus.py:696-698): sobre un corpus v3
      el E2 de la cadena no reproduciría grafo_<to>.json;
  (b) r1_e5_esqueleto.inyectar_esqueleto aborta si build_skeleton no tiene
      paridad con KG-Refinado (r1_e5_esqueleto.py:56-58), una guarda del
      esqueleto v2 que por construcción no vale para el catálogo v3
      (ensamblar_corpus.py:41-44 lo declara así);
  (c) r1_comun.CATALOGO_PATH, assemble.CATALOGO_PATH y
      r1_invariantes.SUJETOS_CATALOGO_SET son del catálogo v2;
  (d) r1_referencias.INVENTARIO_TOS cablea los cinco TOs de desarrollo
      (r1_referencias.py:54-61) y ensamblar_corpus.merge_grafos usa el orden
      default TOS_ORDEN cuando r1_invariantes lo llama sin orden.
Por eso este módulo replica la cadena PASO A PASO importando los mismos
módulos r1_* (r1_cola_flaggeada, r1_invariantes, r1_e4, r1_e5_esqueleto,
r1_referencias, r1_provenance) y redirige lo que corresponde. Con perfil
produccion_dev todas las redirecciones son identidad y la réplica debe
reproducir salida/kg.json (8e2eadee…) y salida_r1/kg.json (0226e947…) byte a
byte; `--selftest-dev` además compara la réplica con ensamblar_r1.correr
llamado directamente (motor `ensamblar_r1`, solo válido en perfil dev).

Pasos de ensamblar_r1.cerrar que leen artefactos propios de r1 y se SALTEAN
con nota (ensamblar_r1.py:213-222): tests T1-T7 (r1_tests lee la muestra
inspeccionada de r1 y KG-Refinado), recomputo de política de la cola y diff
contra el kg sellado 8e2eadee. La tabla propuestos antes/después de la cola
(corrida sin cola hasta e4) sí se replica: es genérica.

Uso:
  .venv/bin/python ensamblar_tanda0.py --manifiesto <ens.json> --entrada <dir E1-E3> --salida <dir>
      [--hasta final] [--sin-cola] [--motor replica|ensamblar_r1] [--selftest-dev]
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path

AQUI = Path(__file__).resolve().parent                    # tanda0/code
REPO = AQUI.parents[3]                                    # raíz del repo
REX = REPO / "data" / "experiment" / "reextraccion_v2"
CORPUS_V2 = REX / "corpus_v2"
GRAFO_V2_CODE = REPO / "data" / "experiment" / "grafo_v2" / "code"
ESQUEMA_V3 = REPO / "data" / "experiment" / "esq_v3_miembros" / "esquema_v3_clases.json"
PERFIL_V3 = "v3_b54"
# --union-comunicaciones (cadena r2): la normalización de la regla C1, que se carga de su archivo, con su candado, solo con
# la bandera prendida
NORMALIZACION_C1 = REPO / "data" / "experiment" / "med_desamb" / "parte2" / "tamanos_desamb_mesa.py"
NORMALIZACION_C1_SHA256 = "428a3cce394111a078a71f06918e90da5bb014a7111426476054a481429ca5d3"
MODULO_NORMALIZACION_C1 = "tamanos_desamb_mesa"

for _p in (str(REX), str(CORPUS_V2), str(GRAFO_V2_CODE), str(REX / "e2_reduce"),
           str(REX / "e1_extractor"), str(REX / "e3_verificador")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import manifiesto_corpus as MC          # noqa: E402  (sellados: solo import)
import perfil_e1                        # noqa: E402
import ensamblar_corpus as EC           # noqa: E402
import r1_comun as C                    # noqa: E402
import r1_invariantes as INV            # noqa: E402
import r1_e4 as E4                      # noqa: E402
import r1_e5_esqueleto as E5            # noqa: E402
import r1_referencias as REF            # noqa: E402
import r1_provenance as PROV            # noqa: E402
import r1_cola_flaggeada as COLA        # noqa: E402
import e2_lib                           # noqa: E402
import assemble                         # noqa: E402
from schema import RELACIONES_ESQUELETO  # noqa: E402

ETAPAS = ("e2", "merge", "e4", "esqueleto", "referencias", "provenance", "final")

SELLOS_DEV = {  # verdad conocida del corpus de desarrollo (desarrollo_5tos.json → sellos.kg; r1: nomenclatura)
    "kg_e5": "8e2eadee57b48e00ccb51ade9a953ba1469001fe089c45d97c4307ccf2725581",
    "kg_r1": "0226e9477baee02d772bbfecee78a49441b189d0e0512ca5e22956dfb084196a",
}


def sha256_texto(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _rel(p: Path) -> str:
    """Ruta relativa al repo cuando está adentro; absoluta si no (scratchpad)."""
    p = Path(p).resolve()
    try:
        return str(p.relative_to(REPO))
    except ValueError:
        return str(p)


# ------------------------------------------------------------------------- #
# Redirecciones en memoria                                                   #
# ------------------------------------------------------------------------- #
def inventario_desde_manifiesto(man: MC.Manifiesto) -> dict[str, tuple[str, ...]]:
    """r1_referencias.INVENTARIO_TOS a partir de `nombres_remision` del
    manifiesto, en orden alfabético de id (el mismo orden del dict cableado de
    r1_referencias, que resolver_norma recorre devolviendo el primer match)."""
    return {t["id"]: tuple(t["nombres_remision"]) for t in sorted(man.tos, key=lambda t: t["id"])}


def plan_redirecciones(man: MC.Manifiesto, perfil, entrada: Path, salida_r1: Path) -> list[tuple]:
    """(módulo, atributo, valor nuevo). En perfil dev los valores de catálogo
    e inventario coinciden con los cableados (se verifica en --selftest-dev)."""
    v3 = perfil.nombre == PERFIL_V3
    orden = tuple(man.orden_corrida)
    return [
        (C, "SALIDA", Path(entrada)),
        (C, "SALIDA_R1", Path(salida_r1)),
        (C, "E0_ENM01", Path(man.e0_salida)),
        (C, "TOS_ORDEN", orden),
        (C, "CATALOGO_PATH", ESQUEMA_V3 if v3 else C.CATALOGO_PATH),
        (EC, "TOS_ORDEN", orden),
        (assemble, "CATALOGO_PATH", ESQUEMA_V3 if v3 else assemble.CATALOGO_PATH),
        (INV, "SUJETOS_CATALOGO_SET",
         perfil.esquema.sujetos_catalogo_set if v3 else INV.SUJETOS_CATALOGO_SET),
        (REF, "INVENTARIO_TOS", inventario_desde_manifiesto(man)),
    ]


@contextlib.contextmanager
def redirigido(plan: list[tuple]):
    originales = [(m, a, getattr(m, a)) for m, a, _ in plan]
    try:
        for m, a, v in plan:
            setattr(m, a, v)
        yield
    finally:
        for m, a, v in originales:
            setattr(m, a, v)


def describir_plan(plan: list[tuple]) -> list[dict]:
    out = []
    for m, a, v in plan:
        if isinstance(v, (frozenset, set)):
            desc = f"<{len(v)} ids>"
        elif isinstance(v, dict):
            desc = {k: list(x) for k, x in v.items()}
        else:
            desc = str(v)
        out.append({"modulo": m.__name__, "atributo": a, "valor": desc})
    return out


# ------------------------------------------------------------------------- #
# E5: ensamblar_corpus.ensamblar con esqueleto v3 por perfil                 #
# ------------------------------------------------------------------------- #
def cargar_grafos(entrada: Path, orden: tuple) -> dict[str, dict]:
    grafos = {}
    for to in orden:
        p = Path(entrada) / to / f"grafo_{to}.json"
        if not p.exists():
            raise FileNotFoundError(f"falta {p} — la corrida de {to} no cerró su E2")
        grafos[to] = json.loads(p.read_text(encoding="utf-8"))
    return grafos


def ensamblar_e5(man: MC.Manifiesto, perfil, entrada: Path, salida: Path, escribir: bool) -> dict:
    orden = tuple(man.orden_corrida)
    esqueleto_v3 = EC.ESQUEMA_V3_DEFAULT if perfil.nombre == EC.PERFIL_CON_ESQUELETO_V3 else None
    if esqueleto_v3 is not None and not Path(esqueleto_v3).exists():
        raise FileNotFoundError(f"perfil {perfil.nombre} sin artefacto de esqueleto v3: {esqueleto_v3}")
    grafos = cargar_grafos(entrada, orden)
    res = EC.ensamblar(grafos, orden, man.tests_respuesta_conocida, esqueleto_v3)
    if escribir:
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "kg.json").write_text(res["kg_json"], encoding="utf-8")
        if res["tests"] is not None:
            (salida / "tests_respuesta_conocida.json").write_text(
                json.dumps(res["tests"], ensure_ascii=False, indent=1), encoding="utf-8")
        (salida / "reporte_ensamblado.json").write_text(
            json.dumps(res["reporte"], ensure_ascii=False, indent=1), encoding="utf-8")
    return {"sha256_kg": res["sha256_kg"], "kg_json": res["kg_json"], "reporte": res["reporte"],
            "esqueleto_v3": str(esqueleto_v3) if esqueleto_v3 else None}


# ------------------------------------------------------------------------- #
# Cadena r1 (réplica paso a paso de ensamblar_r1.correr)                     #
# ------------------------------------------------------------------------- #
def etapa_e2(perfil, con_cola: bool) -> dict:
    """ensamblar_r1.etapa_e2 (ensamblar_r1.py:49-69) con el esquema y los
    labels del PERFIL (None en dev = byte-idéntico al original)."""
    out = {}
    for to in C.TOS_ORDEN:
        chunks = C.cargar_chunks_enm01(to)
        registros = C.cargar_extracciones_finales(to)
        info_cola = None
        if con_cola:
            registros, info_cola = COLA.inyectar_cola(to, registros)
        ens = e2_lib.ensamblar(chunks, registros, esquema=perfil.esquema,
                               labels_catalogo=perfil.labels_catalogo)
        grafo = {"nodes": ens["nodes"], "edges": ens["edges"]}
        if con_cola:
            COLA.flaggear_grafo(grafo, info_cola)
        sha = C.sha256_bytes(C.dumps_kg(grafo).encode("utf-8"))
        out[to] = {"grafo": grafo, "ensamblado": ens, "sha": sha,
                   "paridad_sellado": sha == C.cargar_reporte_e2(to)["sha256_grafo"],
                   "cola": info_cola, "registros": registros}
    return out


def inyectar_esqueleto_v3(kg: dict, catalogo: dict) -> dict:
    """r1_e5_esqueleto.inyectar_esqueleto (r1_e5_esqueleto.py:54-131) SIN la
    guarda de paridad contra KG-Refinado, que es del esqueleto v2. Mismos
    pasos, mismos helpers importados (E5._prov_esqueleto, E5.REL_PADRE_SUGERIDO,
    assemble.build_skeleton con CATALOGO_PATH redirigido al catálogo v3). El
    campo `paridad_kg_refinado` declara la no aplicabilidad en vez de simular
    una comparación."""
    nodes_sk, edges_sk, counts_sk = assemble.build_skeleton()
    antes_rel = C.conteo(kg["edges"], "relation")
    nodes_by_id = {n["id"]: n for n in kg["nodes"]}
    creados, enriquecidos = [], []
    for sid, sk in nodes_sk.items():
        prov = E5._prov_esqueleto(sk["provenance"])
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
        prov = E5._prov_esqueleto(e["provenance"])
        kg["edges"].append({"source": s, "target": t, "relation": r,
                            "provenance": prov, "provenances": [prov],
                            "rol_fuente": "esqueleto"})
        triplas.add((s, r, t))
        n_esq += 1

    flag, sin_padre, padre_fuera = [], [], []
    for n in kg["nodes"]:
        if n["type"] != "Sujeto" or n["properties"].get("nivel") != "propuesto":
            continue
        padre = n["properties"].get("padre_sugerido")
        if not padre:
            sin_padre.append(n["id"])
            continue
        if padre not in nodes_sk:
            padre_fuera.append((n["id"], padre))
            continue
        k = (n["id"], E5.REL_PADRE_SUGERIDO, padre)
        if k in triplas:
            continue
        prov = dict(n["provenance"])
        kg["edges"].append({"source": n["id"], "target": padre, "relation": E5.REL_PADRE_SUGERIDO,
                            "provenance": prov, "provenances": [dict(p) for p in n["provenances"]],
                            "rol_fuente": "cuarentena_flaggeada",
                            "properties": {"flag": "padre_sugerido_no_laudado"}})
        triplas.add(k)
        flag.append(k)

    despues_rel = C.conteo(kg["edges"], "relation")
    rels = RELACIONES_ESQUELETO + (E5.REL_PADRE_SUGERIDO,)
    return {
        "paridad_kg_refinado": {
            "aplicable": False,
            "motivo": "guarda del esqueleto v2 (paridad de build_skeleton con KG-Refinado, "
                      "r1_e5_esqueleto.py:56-58); no vale para el catálogo v3 "
                      "(ensamblar_corpus.py:41-44). Salteada con nota; nada se simula.",
            "catalogo": str(assemble.CATALOGO_PATH),
        },
        "conteos_build_skeleton": counts_sk,
        "nodos_esqueleto_creados": len(creados),
        "nodos_esqueleto_enriquecidos": len(enriquecidos),
        "aristas_esqueleto_agregadas": n_esq,
        "aristas_padre_sugerido_flaggeadas": len(flag),
        "propuestos_sin_padre": sin_padre,
        "propuestos_padre_fuera_de_catalogo": padre_fuera,
        "relaciones_antes": {r: antes_rel.get(r, 0) for r in rels},
        "relaciones_despues": {r: despues_rel.get(r, 0) for r in rels},
        "declaracion_esquema": "padre_sugerido no está en schema.DOMAIN_RANGE; arista flaggeada "
                               "de cuarentena, no subclase_de. No se edita schema.py.",
        "ids_creados": creados,
    }


def correr_cadena(perfil, con_cola: bool, hasta: str = "final", w=None) -> dict:
    """Réplica de ensamblar_r1.correr (ensamblar_r1.py:72-194). `w(nombre, obj)`
    escribe intermedios (None = no escribe). Devuelve el mismo `estado`."""
    h = ETAPAS.index(hasta)
    w = w or (lambda *a, **k: None)
    resumen: dict = {"etapas": [], "con_cola": con_cola, "perfil_e1": perfil.nombre}

    por_to = etapa_e2(perfil, con_cola)
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
        return estado

    if perfil.nombre == PERFIL_V3:
        r_esq = inyectar_esqueleto_v3(kg, catalogo)
    else:
        r_esq = E5.inyectar_esqueleto(kg, catalogo)
    inv_e5 = INV.verificar_invariantes(kg)
    assert inv_e5["ok"], inv_e5["fallos"]
    resumen["esqueleto"] = {k: v for k, v in r_esq.items() if k != "ids_creados"}
    w("e5_esqueleto.json", r_esq)
    resumen["etapas"].append("esqueleto")
    print("[esqueleto]", json.dumps(resumen["esqueleto"], ensure_ascii=False), flush=True)
    if h == 3:
        return estado

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
        return estado

    r_prov = PROV.enriquecer(kg, por_to)
    resumen["provenance"] = r_prov["resumen"]
    w("provenance_verificacion.json", r_prov)
    resumen["etapas"].append("provenance")
    print("[provenance]", json.dumps(r_prov["resumen"], ensure_ascii=False), flush=True)
    if h == 5:
        return estado

    kg["nodes"].sort(key=lambda n: n["id"])
    kg["edges"].sort(key=lambda e: (e["source"], e["relation"], e["target"]))
    estado["kg_json"] = C.dumps_kg(kg)
    estado["sha256"] = C.sha256_bytes(estado["kg_json"].encode("utf-8"))
    resumen["etapas"].append("final")
    return estado


def correr_motor_ensamblar_r1(perfil, con_cola: bool, hasta: str) -> dict:
    """Motor literal: ensamblar_r1.correr con las rutas ya redirigidas. Solo
    válido en perfil dev (ver docstring del módulo, puntos a-d)."""
    if perfil.nombre != "produccion_dev":
        raise RuntimeError(
            f"el motor ensamblar_r1 solo vale con perfil produccion_dev: con {perfil.nombre} su E2 "
            "corre sin esquema/labels del perfil (ensamblar_r1.py:61) y su esqueleto exige paridad "
            "con KG-Refinado (r1_e5_esqueleto.py:56-58) — usar --motor replica")
    import ensamblar_r1 as ER  # noqa: PLC0415 — import diferido, módulo real sin modificar
    return ER.correr(con_cola=con_cola, hasta=hasta, escribir_salida=False)


# ------------------------------------------------------------------------- #
# Orquestación                                                               #
# ------------------------------------------------------------------------- #
def ensamblar_manifiesto(man: MC.Manifiesto, entrada: Path, salida: Path, hasta: str = "final",
                         con_cola: bool = True, motor: str = "replica") -> dict:
    perfil = perfil_e1.perfil(man.perfil_e1)
    entrada, salida = Path(entrada), Path(salida)
    salida_r1 = salida / "r1"
    plan = plan_redirecciones(man, perfil, entrada, salida_r1)

    # --- E5 (ensamblar_corpus) ---
    e5 = ensamblar_e5(man, perfil, entrada, salida, escribir=True)
    print(f"[e5] nodes={e5['reporte']['nodes_total']} edges={e5['reporte']['edges_total']} "
          f"sha256={e5['sha256_kg'][:12]}… esqueleto_v3={e5['esqueleto_v3']}", flush=True)

    # --- cadena r1 ---
    def w(nombre: str, obj) -> None:
        salida_r1.mkdir(parents=True, exist_ok=True)
        (salida_r1 / nombre).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    with redirigido(plan):
        if motor == "replica":
            print("=== cadena r1 (réplica), corrida 1 ===", flush=True)
            e1 = correr_cadena(perfil, con_cola, hasta, w)
            e2 = None
            e0 = None
            if hasta == "final":
                print("=== cadena r1 (réplica), corrida 2 (sin escribir) ===", flush=True)
                e2 = correr_cadena(perfil, con_cola, hasta, None)
                if con_cola:
                    print("=== cadena r1 sin cola hasta e4 (tabla antes/después) ===", flush=True)
                    e0 = correr_cadena(perfil, False, "e4", None)
        else:
            print("=== cadena r1 (motor ensamblar_r1.correr) ===", flush=True)
            e1 = correr_motor_ensamblar_r1(perfil, con_cola, hasta)
            e2 = correr_motor_ensamblar_r1(perfil, con_cola, hasta) if hasta == "final" else None
            e0 = None

    out = {"manifiesto": {"nombre": man.nombre, "path": _rel(man.path),
                          "sha256": hashlib.sha256(Path(man.path).read_bytes()).hexdigest(),
                          "perfil_e1": man.perfil_e1, "orden_corrida": list(man.orden_corrida),
                          "tests_respuesta_conocida": man.tests_respuesta_conocida,
                          "e0_salida": _rel(man.e0_salida)},
           "entrada": _rel(entrada), "salida": _rel(salida), "motor": motor, "hasta": hasta,
           "con_cola": con_cola, "redirecciones": describir_plan(plan),
           "e5": {"sha256_kg": e5["sha256_kg"], "nodes_total": e5["reporte"]["nodes_total"],
                  "edges_total": e5["reporte"]["edges_total"], "esqueleto_v3": e5["esqueleto_v3"],
                  "tests_respuesta_conocida": e5["reporte"]["tests_respuesta_conocida"]}}
    if hasta != "final":
        out["r1"] = {"hasta": hasta, "resumen": e1["resumen"]}
        return out

    kg = e1["kg"]
    doble = e2 is not None and e1["sha256"] == e2["sha256"] and e1["kg_json"] == e2["kg_json"]
    salida_r1.mkdir(parents=True, exist_ok=True)
    (salida_r1 / "kg.json").write_text(e1["kg_json"], encoding="utf-8")
    sha_disco = C.sha256_path(salida_r1 / "kg.json")
    inv = INV.verificar_invariantes(kg)

    def tabla_prop(t):
        return {"resueltos": sum(1 for f in t if f["estado"] == "resuelto"),
                "cuarentena": sum(1 for f in t if f["estado"] == "cuarentena"), "total": len(t)}
    prop_antes_despues = None
    if e0 is not None:
        antes, despues = tabla_prop(e0["e4_propuestos"]), tabla_prop(e1["e4_propuestos"])
        ids_antes = {f["id_propuesto"] for f in e0["e4_propuestos"]}
        nuevos = [f for f in e1["e4_propuestos"] if f["id_propuesto"] not in ids_antes]
        prop_antes_despues = {"sin_cola": antes, "con_cola": despues,
                              "nuevos_con_cola": [{"id": f["id_propuesto"], "label": f["label"],
                                                   "estado": f["estado"], "resuelto_a": f["resuelto_a"]}
                                                  for f in nuevos]}

    r = e1["resumen"]
    reporte = {
        "grafo": f"{man.nombre}/r1", "manifiesto": out["manifiesto"], "motor": motor,
        "sha256_kg": e1["sha256"], "sha256_kg_en_disco": sha_disco,
        "doble_corrida_byte_identica": doble,
        "entrada": _rel(entrada), "kg_e5_sha256": e5["sha256_kg"],
        "nodes_total": len(kg["nodes"]), "edges_total": len(kg["edges"]),
        "nodes_by_type": C.conteo(kg["nodes"], "type"),
        "edges_by_relation": C.conteo(kg["edges"], "relation"),
        "invariantes_final": inv,
        "e2_por_to": r["e2_por_to"],
        "merge": {k: v for k, v in r["merge"].items() if k != "invariantes"},
        "e4": {k: v for k, v in r["e4"].items() if k != "invariantes"},
        "propuestos_antes_despues_cola": prop_antes_despues,
        "esqueleto": r["esqueleto"],
        "referencias": r["referencias"],
        "provenance": r["provenance"],
        "cola_flaggeada": {to: v["cola"] for to, v in r["e2_por_to"].items()},
        "redirecciones": out["redirecciones"],
        "pasos_de_r1_salteados_con_nota": [
            "tests T1-T7 de r1_tests (ensamblar_r1.py:215-217): leen referencias_muestra30_inspeccionada_A2.json "
            "de salida_r1 y KG-Refinado — artefactos propios de r1; el manifiesto declara "
            f"tests_respuesta_conocida={man.tests_respuesta_conocida!r}.",
            "cola_recomputo_politica (ensamblar_r1.py:219-220): recomputo informativo de la política de "
            "la cola de r1; no forma parte del grafo.",
            "diff_vs_sellado (ensamblar_r1.py:222-235): compara contra salida/kg.json (8e2eadee…), sellado de "
            "desarrollo; no aplica a otro corpus.",
        ],
        "declaraciones_esquema": [
            "referencia nodo→nodo (B1.3) no está en schema.DOMAIN_RANGE (solo TextoOrdenado→Comunicacion).",
            "padre_sugerido (E5, cuarentena flaggeada) no está en schema.DOMAIN_RANGE.",
            "schema.py no se edita; las aristas nuevas llevan rol_fuente.",
        ],
    }
    w("reporte_ensamblado_r1.json", reporte)
    out["r1"] = {k: reporte[k] for k in ("sha256_kg", "sha256_kg_en_disco", "doble_corrida_byte_identica",
                                          "nodes_total", "edges_total", "invariantes_final")}
    out["r1"]["invariantes_ok"] = inv["ok"]
    return out


# ------------------------------------------------------------------------- #
# Perfil r2 (U-R2-CODIGO, R3): cadena r2 sobre la salida guardada E1→E3       #
# ------------------------------------------------------------------------- #
# Con --perfil-r2, el ensamblado aplica el perfil r2 (validador, política y
# catálogo r2) a la salida guardada del perfil de E1 del manifiesto: el
# manifiesto no cambia de perfil (perfil_e1.py y manifiesto_corpus.py no se
# editan), y la cadena r2 corre aparte de la r1, con salida en <salida>/r2/.
# Pasos: entrada r2 (crudo del intento aceptado, validador r2) → sujetos por
# relación y registro de no mapeados → E2 r2 por TO → fusión con la guarda
# cross-TO → E4 sin la pasada residual de propuestos (medida, no aplicada) →
# esqueleto del catálogo r2 → remite_a → establecida_en derivada → umbrales
# (par B) → procedencia rica → orden final. Las marcas de la cadena van al
# grafo, en el modelo de pyd_r2/code/modelos_r2: cola humana y colisión
# cross-TO en las properties del nodo (como en los grafos sellados), la base
# resuelta y la verificación en tabla en el elemento de umbral, el calificador
# en la arista de sujeto; las variantes del TextoOrdenado quedan en el reporte
# de E4 (e4_conflictos.json).
TIPOS_CONTENIDO_R2 = REF.TIPOS_CONTENIDO_R2


def sujetos_de_resolucion(cat: dict, M) -> frozenset:
    """R2 de U-RERESOL-CAT, W1: el conjunto de ids contra el que E2 y el merge
    entre TOs aceptan un sujeto. Con el catálogo de resolución
    (`r1_e4.catalogo_resolucion_r2`), el suyo; sin él, el del request
    (`modelos_r2.SUJETOS_R2_SET`), como siempre."""
    return cat["sujetos_set"] if "sujetos_set" in cat else M.SUJETOS_R2_SET


def plan_redirecciones_r2(man: MC.Manifiesto, perfil, entrada: Path, salida_r2: Path, cat: dict, M) -> list[tuple]:
    plan = [(m, a, v) for m, a, v in plan_redirecciones(man, perfil, entrada, salida_r2)
            if (m, a) not in ((C, "CATALOGO_PATH"), (assemble, "CATALOGO_PATH"), (INV, "SUJETOS_CATALOGO_SET"))]
    return plan + [(C, "CATALOGO_PATH", cat["entrada_esqueleto_path"]),
                   (assemble, "CATALOGO_PATH", cat["entrada_esqueleto_path"]),
                   (INV, "SUJETOS_CATALOGO_SET", sujetos_de_resolucion(cat, M)),
                   (REF, "TITULOS_TOS", REF.titulos_de_inventario(
                       sorted(t["id"] for t in man.tos), {t["id"]: t["nombres_remision"] for t in man.tos}))]


def derivar_establecida_en(kg: dict, canon: dict[str, str]) -> dict:
    """Decisión 11 del mandato: todo nodo de contenido sin `establecida_en`
    la recibe hacia el TextoOrdenado de cada TO de su procedencia, con
    `rol_fuente = derivada_de_procedencia`."""
    con = {e["source"] for e in kg["edges"] if e["relation"] == "establecida_en"}
    triplas = {(e["source"], e["relation"], e["target"]) for e in kg["edges"]}
    nuevas = []
    for n in sorted(kg["nodes"], key=lambda x: x["id"]):
        if n["type"] not in TIPOS_CONTENIDO_R2 or n["id"] in con:
            continue
        for to in sorted({p["to"] for p in n["provenances"] if p.get("to") in canon}):
            k = (n["id"], "establecida_en", canon[to])
            if k in triplas:
                continue
            provs = [dict(p) for p in n["provenances"] if p.get("to") == to]
            e = {"source": n["id"], "target": canon[to], "relation": "establecida_en",
                 "provenance": dict(provs[0]), "provenances": provs, "rol_fuente": "derivada_de_procedencia"}
            kg["edges"].append(e)
            triplas.add(k)
            nuevas.append(e)
    tipo = {n["id"]: n["type"] for n in kg["nodes"]}
    sin = [n["id"] for n in kg["nodes"] if n["type"] in TIPOS_CONTENIDO_R2
           and n["id"] not in {e["source"] for e in kg["edges"] if e["relation"] == "establecida_en"}]
    return {"aristas_derivadas": len(nuevas),
            "por_tipo": C.conteo([{"t": tipo[e["source"]]} for e in nuevas], "t"),
            "nodos_de_contenido_sin_establecida_en": len(sin), "ids_sin": sin[:20]}


def _texto_e0_nodo(n: dict, chunks: dict[str, dict], V) -> list[tuple[str, str]]:
    out = []
    for p in n.get("provenances", []):
        cid = p.get("chunk_id")
        if cid and cid in chunks and cid not in [c for c, _ in out]:
            out.append((cid, V.texto_completo(chunks[cid])))
    return out


def _rangos_unidad_repetida(texto: str, cs: list) -> list[str]:
    """Rangos «entre X <unidad> y Y <unidad>» con la unidad repetida (límite
    declarado en la fila 7 del plan: la cota inferior recibe máximo asumido)."""
    out = []
    for a, b in zip(cs, cs[1:]):
        if a.unidad and a.unidad == b.unidad and re.fullmatch(r"\s+y\s+", texto[a.fin:b.inicio]) \
                and re.search(r"\bentre\s+$", texto[:a.inicio], re.I):
            out.append(texto[max(0, a.inicio - 7):b.fin])
    return out


# U-OMISIONES-COD, grupo C, g2: la cita «punto(s) N» del texto de E0 de la unidad que, después de su enumeración
# («N. y M.», «N., M.»), sigue inmediatamente con el nombre de otra norma. Sobre el texto plegado (minúsculas, sin
# tildes, espacios unidos).
_NUM_PUNTO = r"\d+(?:\.\d+)*\.?"
RE_CITA_A_OTRA_NORMA = re.compile(
    r"\bpuntos?\s+(" + _NUM_PUNTO + r"(?:\s*(?:,|y|e|o|a|al)\s*" + _NUM_PUNTO + r")*)\s*"
    r"(?:del to sobre|de las normas sobre|del texto ordenado|de la ley|del decreto|de la comunicacion)\b")


def _plegar_texto(s: str) -> str:
    import unicodedata  # noqa: PLC0415
    s = unicodedata.normalize("NFD", s or "")
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())


def puntos_citados_de_otra_norma(textos: list[str]) -> set[str]:
    """g2: los N de las citas «punto(s) N … <otra norma>» de los textos, sin el punto final."""
    out = set()
    for t in textos:
        for m in RE_CITA_A_OTRA_NORMA.finditer(_plegar_texto(t)):
            out |= {x.rstrip(".") for x in re.findall(_NUM_PUNTO, m.group(1))}
    return out


def resolver_base(base: str | None, to: str, kg_def: dict[tuple[str, str], str], detector_r2: bool = False,
                  textos_unidad: list[str] | None = None, homonimos: set[tuple[str, str]] | None = None) -> dict:
    """L-ESQ-R2 §1.3 (c): la base literal se resuelve a su punto por el
    mecanismo de remisiones (detectar_menciones sobre la base) o a una
    Definicion del mismo TO cuyo `termino` normalizado es la base; si no
    resuelve, se marca. Con `detector_r2` (fase r2b; U-R2-CODIGO-2, C2,
    punto r), las menciones salen del mismo detector que `remite_a`
    (`REF.menciones_por_tramo`, que normaliza el texto y aplica
    `detectar_menciones_r2` con las reglas de REF.REGLAS_R2).
    U-OMISIONES-COD, grupo C (solo con `detector_r2`): g2, una remisión a un
    punto N no resuelve si el texto de E0 de la unidad (`textos_unidad`) cita
    ese N como punto de otra norma (`puntos_citados_de_otra_norma`); y g3, una
    Definicion con dos o más homónimas en el TO (`homonimos`) no resuelve. En
    los dos casos, la base queda marcada (`marca` con su motivo en `motivo`)."""
    if not base:
        return {"base_destino": None, "via": None, "marca": None}
    menciones = (REF.menciones_por_tramo([base], to, REF.REGLAS_R2) if detector_r2
                 else REF.detectar_menciones(base, to))
    otra_norma = puntos_citados_de_otra_norma(textos_unidad or []) if detector_r2 else set()
    for men in menciones:
        td = men["to_destino"]
        if td is None or td not in C.TOS_ORDEN:
            continue
        unidades = REF.unidades_e0(td)
        for d in men["puntos"] + [f"S{s}" for s in men["secciones"]]:
            if d in unidades:
                if d in otra_norma:
                    return {"base_destino": None, "via": None, "marca": "base_no_resuelta",
                            "motivo": "cita_a_otra_norma", "destino_descartado": f"{td}::{d}"}
                return {"base_destino": f"{td}::{d}", "via": "remision", "marca": None}
        if not men["puntos"] and not men["secciones"] and men["clase"] != "interna":
            return {"base_destino": f"{td}::TO", "via": "remision", "marca": None}
    nid = kg_def.get((to, C.norm(base)))
    if nid:
        if detector_r2 and homonimos and (to, C.norm(base)) in homonimos:
            return {"base_destino": None, "via": None, "marca": "base_no_resuelta", "motivo": "definicion_homonima",
                    "destino_descartado": nid}
        return {"base_destino": nid, "via": "definicion", "marca": None}
    return {"base_destino": None, "via": None, "marca": "base_no_resuelta"}


# U-OMISIONES-COD, grupo C, g1: las reglas cerradas de U-DIAG-LIMITES (límite 1), en su orden, sobre la base plegada
# (minúsculas, sin tildes); gana la primera que aplica. Con fecha, periodicidad, cantidad o evento/plazo la «base» no
# es una base y queda vacía, sin marca; el recorte que empieza mal (antes que evento/plazo) la conserva.
_NUM_BASE = r"(\d+|un|una|uno|dos|tres|cuatro|cinco|seis|doble|triple|cuarta|tercera|mitad|tercio|otras? (dos|tres))"
REGLAS_BASE_RELATIVA = (
    ("fecha", re.compile(r"^\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b"), True),
    ("periodicidad", re.compile(r"^(trimestral|semestral|mensual|anual|con periodicidad|una vez al ano)"), True),
    ("cantidad_no_detectada", re.compile(r"^(" + _NUM_BASE + r"\b|\"|“|que \d)"), True),
    ("recorte_empieza_mal", re.compile(r"^(que |tanto |en la |asignado |alcanzar |dar |previsto )"), False),
    ("evento_o_plazo", re.compile(r"^(fecha|dia|plazos?|mes|vencimiento)\b"), True),
)


def clase_de_base_relativa(base: str | None) -> tuple[str | None, bool]:
    """g1: (clase de la primera regla que aplica o None, si la base queda vacía)."""
    import unicodedata  # noqa: PLC0415
    b = unicodedata.normalize("NFD", base or "")
    b = "".join(c for c in b if not unicodedata.combining(c)).lower().strip()
    for nombre, rx, vacia in REGLAS_BASE_RELATIVA:
        if rx.search(b):
            return nombre, vacia
    return None, False


def tramo_de_e1(el: dict, tramo_e1: str, textos: list, V, RCMP, pol, M) -> tuple[dict, str]:
    """U-OMISIONES-COD, grupo L (solo r2b): el elemento de origen e1 armado por el ensamblado guarda el tramo de E1
    del que sale su cuantía (L-ESQ-R2 §1.3: «el tramo literal»), verificado contra el texto de E0 del nodo. Con
    «exacta», el tramo de E1; con «tokens», el literal mínimo del texto, si conserva la cuantía (mismo valor y misma
    unidad); si no verifica, o el literal pierde la cuantía, el elemento conserva la cuantía y su verificación, y se
    cuenta. Los demás campos no cambian. Devuelve (elemento, estado)."""
    mejor, literal = "no", None
    for _, t in textos:
        nivel, lit = V.verificar_tramo(tramo_e1, t, pol.holgura)
        if nivel == "exacta":
            mejor, literal = "exacta", None
            break
        if nivel == "tokens" and mejor == "no":
            mejor, literal = "tokens", lit
    nuevo_tramo = tramo_e1 if mejor == "exacta" else literal
    if nuevo_tramo is None or not any(c.valor == el.get("valor") and c.unidad == el.get("unidad")
                                      for c in RCMP.detectar_cuantias(nuevo_tramo)):
        return el, "conserva_la_cuantia"
    nuevo = dict(el, tramo=nuevo_tramo, tramo_verificado=mejor)
    return M.ElementoUmbral.model_validate(nuevo).model_dump(mode="json", exclude_defaults=True), mejor


def _base_del_validador(el: dict, to: str, kg_def: dict, homonimos: set, textos: list, cont: dict, M) -> dict:
    """U-OMISIONES-COD, grupo C (solo r2b): el elemento del límite relativo que dejó validador_r2 (punto o) y tiene
    base sin destino ni marca. g1: si la base no es una base (`clase_de_base_relativa`), queda vacía, sin marca; si
    no, g: `resolver_base` con el detector de `remite_a` y las guardas g2 y g3 escribe el destino y la vía, o la
    marca. Los demás elementos vuelven tal cual."""
    if (not str(el.get("regla_comparacion") or "").startswith("limite_relativo:") or not el.get("base")
            or el.get("base_destino") or el.get("base_no_resuelta")):
        return el
    bv = cont["base_del_validador"]
    bv["elementos_con_base"] += 1
    clase, vacia = clase_de_base_relativa(el["base"])
    nuevo = dict(el)
    if vacia:
        nuevo.pop("base")
        bv["vaciadas_g1"][clase] = bv["vaciadas_g1"].get(clase, 0) + 1
    else:
        b = resolver_base(el["base"], to, kg_def, detector_r2=True, textos_unidad=[t for _, t in textos],
                          homonimos=homonimos)
        nuevo.update(base_destino=b["base_destino"], base_via=b["via"], base_no_resuelta=b["marca"] == "base_no_resuelta")
        if b["base_destino"]:
            bv["resueltas"][b["via"]] = bv["resueltas"].get(b["via"], 0) + 1
        else:
            bv["marcadas"] += 1
            if b.get("motivo"):
                cont["base_no_resuelta_por_motivo"][b["motivo"]] = cont["base_no_resuelta_por_motivo"].get(b["motivo"], 0) + 1
    return M.ElementoUmbral.model_validate(nuevo).model_dump(mode="json", exclude_defaults=True)


def llenar_umbrales_r2(kg: dict, tramos_e1: dict[str, list[str]], tablas: dict[str, list[str]], M, V, RCMP,
                       pol, fase: str = "r2a") -> dict:
    """Par B en r2a (L-ESQ-R2 §1.3 y §1.4; mandato R3.f): la lista de umbrales
    de Restriccion, Obligacion, Condicion y Excepcion, armada en código con las
    reglas de U-PYD (reglas_comparacion.analizar), desde los tramos de E1 si
    los hay (r2b) o, en r2a, desde la descripción guardada y los
    campos_heredados_v3 (umbral, plazo). El tramo del elemento es la cuantía
    tal como está en esa fuente; se verifica contra el texto de E0 de los
    chunks del nodo y, si el chunk tiene tablas de e0-r2, contra sus celdas.
    Lo que no verifica queda marcado (`tramo_verificado = no`), sin
    corregirse. El plazo heredado que no es un plazo va a `frecuencia`.
    Con la fase r2b (U-R2-CODIGO-2, C2): el plazo sin marcador queda
    `no_determinada`, sin `comparacion_asumida` (punto m, enmienda 3 a
    L-ESQ-R2); la lista se completa, no se reemplaza, y el elemento del
    límite relativo que dejó validador_r2 se conserva junto a los de cuantía
    (punto o); y la base se resuelve con el detector de `remite_a` (punto
    r). En r2a, la regla anterior, para reproducir los grafos sellados."""
    r2b = fase == "r2b"
    plazo_sin_marcador = "no_determinada" if r2b else "maximo_asumido"
    chunks = {c["id"]: c for to in C.TOS_ORDEN for c in _chunks_r2(to)}
    kg_def, def_por_clave = {}, {}
    for n in kg["nodes"]:
        if n["type"] == "Definicion" and isinstance(n["properties"].get("termino"), str):
            for p in n["provenances"]:
                kg_def.setdefault((p.get("to"), C.norm(n["properties"]["termino"])), n["id"])
                def_por_clave.setdefault((p.get("to"), C.norm(n["properties"]["termino"])), set()).add(n["id"])
    # U-OMISIONES-COD, grupo C, g3: términos con dos o más Definicion en el TO (solo r2b)
    homonimos = {k for k, ids in def_por_clave.items() if len(ids) > 1} if r2b else set()
    rangos = []
    cont = {"nodos": 0, "nodos_con_lista": 0, "elementos": 0, "por_origen": {}, "por_comparacion": {},
            "comparacion_asumida": 0, "no_determinada": 0, "tramo_verificado": {}, "verificado_en_tabla": {},
            "base_resuelta": 0, "base_no_resuelta": 0, "frecuencia_desde_plazo": 0,
            "frecuencia_fuera_de_lista": 0}
    if r2b:
        cont["elementos_previos_conservados"] = 0
        cont["unidad_desde_rotulo"] = {"elementos": 0, "por_to": {}, "nodos": []}
        # U-OMISIONES-COD: la base de los elementos del validador (grupo C) y el tramo de E1 (grupo L)
        cont["base_del_validador"] = {"elementos_con_base": 0, "vaciadas_g1": {}, "resueltas": {}, "marcadas": 0}
        cont["base_no_resuelta_por_motivo"] = {}
        cont["base_por_origen"] = {}
        cont["tramo_de_e1"] = {"elementos": 0, "tramo_verificado": {}, "tramos_compartidos": 0}

    def suma(d, k):
        cont[d][k] = cont[d].get(k, 0) + 1

    for n in sorted(kg["nodes"], key=lambda x: x["id"]):
        if n["type"] not in M.TIPOS_CON_UMBRALES:
            continue
        cont["nodos"] += 1
        props = n["properties"]
        desc = props.get("descripcion")
        prim = n["provenance"].get("chunk_id")
        titulo = chunks[prim].get("titulo") if prim in chunks else None
        to = n["provenance"].get("to")
        fuentes = []
        if tramos_e1.get(n["id"]):
            fuentes = [(t, "e1") for t in tramos_e1[n["id"]]]
        else:
            if isinstance(desc, str) and desc:
                fuentes.append((desc, "descripcion"))
            for k, v in sorted((n.get("campos_heredados_v3") or {}).items()):
                if not isinstance(v, str) or not v.strip():
                    continue
                if n["type"] == "Obligacion" and k == "plazo" and not any(
                        c.unidad in M.UNIDADES_TEMPORALES + M.UNIDADES_TEMPORALES_FUERA
                        for c in RCMP.detectar_cuantias(v)):
                    if props.get("frecuencia") is None:
                        f = V.frecuencia_desde_tramo(v)
                        props["frecuencia"] = f or v
                        n.setdefault("originales", {}).setdefault("frecuencia", v)
                        if f is None:
                            n.setdefault("fuera_de_lista", []).append("frecuencia")
                            cont["frecuencia_fuera_de_lista"] += 1
                        cont["frecuencia_desde_plazo"] += 1
                    continue
                fuentes.append((v, "campo_v3"))
        textos = _texto_e0_nodo(n, chunks, V)
        celdas = "\n".join(t for cid, _ in textos for t in tablas.get(cid, []))
        elementos, vistos, tramos_l = [], set(), []
        for texto, origen in fuentes:
            cs = RCMP.analizar(texto, desc, titulo, plazo_sin_marcador)
            rangos += [{"id": n["id"], "tramo": r} for r in _rangos_unidad_repetida(texto, cs)]
            for c in cs:
                clave = (c.valor, c.unidad, c.moneda)
                if origen == "campo_v3" and clave in vistos:
                    continue
                vistos.add(clave)
                el = RCMP.elemento_umbral(c, c.texto, origen)
                niveles = [V.verificar_tramo(c.texto, t, pol.holgura)[0] for _, t in textos] or ["no"]
                el["tramo_verificado"] = ("exacta" if "exacta" in niveles else
                                          "tokens" if "tokens" in niveles else "no")
                en_tabla = (None if not celdas else
                            V.verificar_tramo(c.texto, celdas, pol.holgura)[0] in ("exacta", "tokens"))
                b = resolver_base(c.base, to, kg_def, detector_r2=r2b, textos_unidad=[t for _, t in textos],
                                  homonimos=homonimos)
                el.update(base_destino=b["base_destino"], base_via=b["via"],
                          base_no_resuelta=b["marca"] == "base_no_resuelta", verificado_en_tabla=en_tabla)
                elementos.append(M.ElementoUmbral.model_validate(el).model_dump(mode="json", exclude_defaults=True))
                # grupo L: el tramo de E1 del que sale la cuantía (solo r2b y origen e1); se pone después del rótulo
                tramos_l.append((texto, sum(1 for _ in cs)) if r2b and origen == "e1" else None)
                if r2b and b.get("motivo"):
                    suma("base_no_resuelta_por_motivo", b["motivo"])
                cont["elementos"] += 1
                suma("por_origen", origen)
                suma("por_comparacion", c.comparacion)
                suma("tramo_verificado", el["tramo_verificado"])
                suma("verificado_en_tabla", str(en_tabla))
                cont["comparacion_asumida"] += c.comparacion_asumida
                cont["no_determinada"] += c.comparacion == "no_determinada"
                cont["base_resuelta"] += b["base_destino"] is not None
                cont["base_no_resuelta"] += b["marca"] == "base_no_resuelta"
        desde_e1 = 0
        if elementos and r2b and props.get("umbrales"):
            cont["elementos_previos_conservados"] += len(props["umbrales"])
            desde_e1 = len(props["umbrales"])
            props["umbrales"] = list(props["umbrales"]) + elementos
            cont["nodos_con_lista"] += 1
        elif elementos:
            props["umbrales"] = elementos
            cont["nodos_con_lista"] += 1
        if r2b and props.get("umbrales"):
            # T3-bis de U-REEXT-T0, decisión 2: la cuantía que es una celda de una tabla serializada con rótulo
            # hereda la unidad del rótulo; el tramo no cambia.
            bloques = bloques_con_rotulo(textos)
            if bloques:
                nuevos = []
                for el in props["umbrales"]:
                    h = unidad_desde_rotulo(el, bloques, RCMP, M, desc, titulo, plazo_sin_marcador)
                    nuevos.append(h or el)
                    if h:
                        u = cont["unidad_desde_rotulo"]
                        u["elementos"] += 1
                        u["por_to"][to] = u["por_to"].get(to, 0) + 1
                        u["nodos"].append({"id": n["id"], "to": to, "tramo": h["tramo"], "valor": h.get("valor"),
                                           "unidad": h.get("unidad"), "moneda": h.get("moneda"),
                                           "tabla": h["originales"]["tabla"],
                                           "rotulo": h["originales"]["unidad_desde_rotulo"]})
                props["umbrales"] = nuevos
        if r2b and props.get("umbrales"):
            props["umbrales"] = [_base_del_validador(el, to, kg_def, homonimos, textos, cont, M)
                                 for el in props["umbrales"]]
            for j, x in enumerate(tramos_l):
                if x is None:
                    continue
                el, estado = tramo_de_e1(props["umbrales"][desde_e1 + j], x[0], textos, V, RCMP, pol, M)
                props["umbrales"][desde_e1 + j] = el
                tl = cont["tramo_de_e1"]
                tl["elementos"] += 1
                tl["tramo_verificado"][estado] = tl["tramo_verificado"].get(estado, 0) + 1
                tl["tramos_compartidos"] += x[1] > 1 and estado != "conserva_la_cuantia"
                if estado == "conserva_la_cuantia":
                    tl.setdefault("conservan_la_cuantia", []).append({"id": n["id"], "cuantia": el["tramo"],
                                                                      "tramo_e1": x[0]})
            for el in props["umbrales"]:
                if el.get("base"):
                    estado = ("resuelta" if el.get("base_destino") else "marcada" if el.get("base_no_resuelta")
                              else "sin_destino_ni_marca")
                    o = "validador" if str(el.get("regla_comparacion") or "").startswith("limite_relativo:") else \
                        str(el.get("origen"))
                    d = cont["base_por_origen"].setdefault(o, {})
                    d[estado] = d.get(estado, 0) + 1
    cont["rangos_con_unidad_repetida"] = len(rangos)
    return {"resumen": cont, "rangos": rangos}


# ------------------------------------------------------------------------- #
# T3-bis de U-REEXT-T0 (fase r2b): propuestos después del merge cross-TO,    #
# unidad del rótulo de tabla y marca de umbral no cuantificable              #
# ------------------------------------------------------------------------- #
# Decisión 1.b: una mención hecha solo de pronombres, determinantes o palabras funcionales (lista cerrada, sobre el
# texto normalizado por C.norm) no nombra un sujeto.
PALABRAS_VACIAS_SUJETO = frozenset((
    "se", "el", "ella", "ellos", "ellas", "ello", "este", "esta", "estos", "estas", "esto", "ese", "esa", "esos",
    "esas", "eso", "aquel", "aquella", "aquellos", "aquellas", "aquello", "cada", "uno", "una", "unos", "unas",
    "otro", "otra", "otros", "otras", "quien", "quienes", "quienquiera", "cual", "cuales", "la", "los", "las", "lo",
    "le", "les", "su", "sus", "mismo", "misma", "mismos", "mismas", "dicho", "dicha", "dichos", "dichas", "tal",
    "tales", "ambos", "ambas", "todo", "toda", "todos", "todas", "alguno", "alguna", "algunos", "algunas",
    "ninguno", "ninguna", "cualquiera", "que", "de", "del", "al", "a", "y", "o", "u", "e"))
MARCA_MENCION_VACIA = "mencion_pronombre_o_palabra_vacia"
TABLAS_FORZADAS_R2B = REX / "e1_extractor" / "tablas_residuales_forzadas_r2b.json"
MOTIVO_SIN_CUANTIA = "sin cuantía detectable"
MOTIVO_TABLA_FORZADA = "cuantías solo en tabla residual forzada"
RE_BLOQUE_TABLA = re.compile(r"\[TABLA (\S+) \|[^\]\n]*\]\n(.*?)\n\[FIN TABLA \1\]", re.S)
RE_ROTULO_TABLA = re.compile(r"^Rótulo: (.+)$", re.M)
RE_FILA_TABLA = re.compile(r"^Fila \d+: (.*)$", re.M)


def mencion_vacia(label: str) -> bool:
    toks = re.findall(r"\w+", C.norm(label))
    return bool(toks) and all(t in PALABRAS_VACIAS_SUJETO for t in toks)


def raiz_del_catalogo(entrada: dict) -> str:
    """La raíz de la jerarquía de la entrada del esqueleto: la única clase sin padre (las instancias tampoco lo
    llevan, pero tienen instancia_de). Frena si no hay exactamente una."""
    raices = sorted(c["id"] for c in entrada["clases"] if c.get("nivel") == "clase" and not c.get("padre"))
    if len(raices) != 1:
        raise ValueError(f"la entrada del esqueleto no tiene una única raíz: {raices}")
    return raices[0]


def normalizar_propuestos_r2b(kg: dict, registro: list[dict], renombres: dict[str, dict[str, str]], cat: dict) -> dict:
    """Decisión 1 de T3-bis de U-REEXT-T0 (fase r2b), después del merge cross-TO y antes del esqueleto, que arma
    las aristas padre_sugerido desde la propiedad del propuesto:
    a. el propuesto renombrado por la colisión cross-TO (sufijo __<to>) lleva su id nuevo en las filas de su TO del
       registro de no mapeados (LN-5, S28);
    b. el propuesto cuya mención es un pronombre o una palabra vacía se descarta: el nodo y sus aristas salen del
       grafo, sus filas del registro quedan con estado «descartado» y la marca, y las aristas quitadas se listan con
       la norma, la unidad, la mención y el tramo, sin asignarles rol. El padre_sugerido hacia un Sujeto de nivel
       instancia se reemplaza por la clase de la instancia (instancia_de; marca padre_sugerido_instancia) o, sin
       clase, se quita con la marca padre_sugerido_descartado (S3);
    b′. R2-3 y R2-3 bis de U-RERESOL-CAT (S19; decisiones de la autora del 07/10/2026): el propuesto sin
       padre_sugerido con filas del registro en cuarentena en un documento sin alcance, con cualquier motivo, recibe
       como padre la sugerencia guardada del modelo si esas filas traen una sola que está en el catálogo (marca
       padre_desde_sugerencia_modelo; una instancia pasa a su clase en el paso de b) y, si no, la raíz del catálogo
       (marca padre_por_defecto_generico); el detalle lista los motivos. Corre antes del reemplazo de las instancias;
    c. el propuesto sin padre_sugerido recibe el rol de alcance de su TO (rol_por_to del catálogo r2) con la marca
       padre_por_defecto (S19); si sus TOs no dan un único rol, queda sin padre y listado.
    Muta kg y las filas del registro. Devuelve el resumen y las filas de las aristas quitadas."""
    entrada = cat["entrada_esqueleto"]
    clases = {c["id"]: c for c in entrada["clases"]}
    roles = {r["id"] for r in entrada["roles"]}
    res = {"filas_renombradas": [], "descartados": [], "padre_desde_instancia": [], "padre_descartado": [],
           "padre_desde_sugerencia_modelo": [], "padre_por_defecto_generico": [], "padre_por_defecto": [],
           "sin_rol_de_alcance": []}
    for to, ren in sorted(renombres.items()):
        for f in registro:
            if f.get("to") == to and f.get("id_nodo") in ren:
                res["filas_renombradas"].append({"to": to, "chunk_id": f.get("chunk_id"),
                                                 "indice_relacion": f.get("indice_relacion"),
                                                 "id_anterior": f["id_nodo"], "id_nodo": ren[f["id_nodo"]]})
                f["id_nodo"] = ren[f["id_nodo"]]
    by_id = {n["id"]: n for n in kg["nodes"]}
    propuestos = sorted((n for n in kg["nodes"] if n["type"] == "Sujeto" and n["properties"].get("nivel") == "propuesto"),
                        key=lambda n: n["id"])
    descartar = {n["id"] for n in propuestos if mencion_vacia(n["label"])}
    quitadas = sorted((e for e in kg["edges"] if e["source"] in descartar or e["target"] in descartar),
                      key=lambda e: (e["source"], e["relation"], e["target"]))
    filas_quitadas = []
    for e in quitadas:
        prop = e["target"] if e["target"] in descartar else e["source"]
        otro = by_id.get(e["source"] if prop == e["target"] else e["target"], {})
        pv = e.get("provenance") or {}
        fila_reg = next((f for f in registro if f.get("id_nodo") == prop and f.get("chunk_id") == pv.get("chunk_id")),
                        {})
        filas_quitadas.append({
            "propuesto": prop, "mencion": by_id[prop]["label"], "marca": MARCA_MENCION_VACIA,
            "relacion": e["relation"], "source": e["source"], "target": e["target"],
            "to": pv.get("to"), "archivo": pv.get("archivo"), "chunk_id": pv.get("chunk_id"), "punto": pv.get("punto"),
            "sujeto_mencion": e.get("sujeto_mencion"), "mencion_verificada": e.get("mencion_verificada"),
            "indice_relacion": fila_reg.get("indice_relacion"),
            "extremo": otro.get("id"), "extremo_tipo": otro.get("type"), "extremo_label": otro.get("label"),
            "tramo_del_extremo": next((p.get("tramo") for p in otro.get("provenances", [])
                                       if p.get("chunk_id") == pv.get("chunk_id") and p.get("tramo")), None)})
    if descartar:
        kg["edges"][:] = [e for e in kg["edges"] if e["source"] not in descartar and e["target"] not in descartar]
        kg["nodes"][:] = [n for n in kg["nodes"] if n["id"] not in descartar]
        for f in registro:
            if f.get("id_nodo") in descartar:
                f["estado"] = "descartado"
                f["motivo_descarte"] = MARCA_MENCION_VACIA
    for i in sorted(descartar):
        res["descartados"].append({
            "id": i, "mencion": by_id[i]["label"], "padre_sugerido": by_id[i]["properties"].get("padre_sugerido"),
            "tos": sorted({p.get("to") for p in by_id[i].get("provenances", []) if p.get("to")}),
            "aristas_quitadas": sum(1 for x in filas_quitadas if x["propuesto"] == i),
            "filas_del_registro": sum(1 for f in registro if f.get("id_nodo") == i)})
    propuestos = [n for n in propuestos if n["id"] not in descartar]
    filas_sin_alcance: dict[str, list[dict]] = {}
    con_alcance: dict[str, bool] = {}
    for f in registro:
        if f.get("estado") != "cuarentena" or not f.get("id_nodo"):
            continue
        if f["to"] not in con_alcance:
            con_alcance[f["to"]] = C.archivo_de_to(f["to"]) in cat["rol_por_to"]
        if not con_alcance[f["to"]]:
            filas_sin_alcance.setdefault(f["id_nodo"], []).append(f)
    for n in propuestos:
        filas = filas_sin_alcance.get(n["id"])
        if not filas or n["properties"].get("padre_sugerido"):
            continue
        sugeridas = sorted({f["sujeto_id_modelo"] for f in filas if f.get("sujeto_id_modelo")})
        en_catalogo = [s for s in sugeridas if s in clases or s in roles]
        fila = {"id": n["id"], "mencion": n["label"], "tos": sorted({f["to"] for f in filas}), "filas": len(filas),
                "motivos": sorted({f["motivo"] for f in filas})}
        if len(en_catalogo) == 1:
            n["properties"]["padre_sugerido"] = en_catalogo[0]
            n["properties"]["padre_desde_sugerencia_modelo"] = "true"
            res["padre_desde_sugerencia_modelo"].append({**fila, "padre_sugerido": en_catalogo[0]})
        else:
            raiz = raiz_del_catalogo(entrada)
            n["properties"]["padre_sugerido"] = raiz
            n["properties"]["padre_por_defecto_generico"] = "true"
            res["padre_por_defecto_generico"].append({**fila, "sugerencias": sugeridas, "padre_sugerido": raiz})
    for n in propuestos:
        p = n["properties"].get("padre_sugerido")
        if not p or (clases.get(p) or {}).get("nivel") != "instancia":
            continue
        clase = clases[p].get("instancia_de")
        if clase and ((clases.get(clase) or {}).get("nivel") == "clase" or clase in roles):
            n["properties"]["padre_sugerido"] = clase
            n["properties"]["padre_sugerido_instancia"] = p
            res["padre_desde_instancia"].append({"id": n["id"], "instancia": p, "padre_sugerido": clase})
        else:
            del n["properties"]["padre_sugerido"]
            n["properties"]["padre_sugerido_descartado"] = p
            res["padre_descartado"].append({"id": n["id"], "instancia": p})
    for n in propuestos:
        if n["properties"].get("padre_sugerido"):
            continue
        tos = sorted({p.get("to") for p in n.get("provenances", []) if p.get("to")})
        rol = {to: (cat["rol_por_to"].get(C.archivo_de_to(to)) or {}).get("rol_id") for to in tos}
        candidatos = set(rol.values())
        if len(candidatos) == 1 and None not in candidatos:
            r = candidatos.pop()
            n["properties"]["padre_sugerido"] = r
            n["properties"]["padre_por_defecto"] = "true"
            res["padre_por_defecto"].append({"id": n["id"], "mencion": n["label"], "tos": tos, "padre_sugerido": r})
        else:
            res["sin_rol_de_alcance"].append({"id": n["id"], "mencion": n["label"], "rol_por_to": rol})
    resumen = {k: len(v) for k, v in res.items()}
    resumen.update(aristas_quitadas=len(filas_quitadas), detalle=res)
    return {"resumen": resumen, "aristas_quitadas": filas_quitadas}


def bloques_con_rotulo(textos: list[tuple[str, str]]) -> list[dict]:
    """Bloques de tabla serializada ([TABLA …] … [FIN TABLA …]) con una línea «Rótulo:», de los textos de E0 del
    nodo, con el conjunto de valores de sus celdas («columna = valor» de las líneas «Fila n:»)."""
    out, vistos = [], set()
    for cid, t in textos:
        for m in RE_BLOQUE_TABLA.finditer(t or ""):
            r = RE_ROTULO_TABLA.search(m.group(2))
            if not r or (cid, m.group(1)) in vistos:
                continue
            vistos.add((cid, m.group(1)))
            celdas = {c.split(" = ", 1)[1].strip() for f in RE_FILA_TABLA.findall(m.group(2))
                      for c in f.split(" | ") if " = " in c}
            out.append({"chunk_id": cid, "tabla": m.group(1), "rotulo": r.group(1).strip(), "celdas": celdas})
    return out


def unidad_desde_rotulo(el: dict, bloques: list[dict], RCMP, M, desc, titulo, plazo_sin_marcador) -> dict | None:
    """Decisión 2 de T3-bis: un elemento sin valor ni unidad cuyo tramo es el valor de una celda de un bloque con
    rótulo hereda la unidad del rótulo («-En millones de pesos-»): la cuantía se detecta sobre «<tramo> <unidad>»
    con las reglas de U-PYD y el elemento gana valor, unidad y moneda; tramo, comparación y verificación no
    cambian (si la comparación del texto compuesto fuera otra, no se aplica). La regla anterior, el rótulo y la
    tabla quedan en `originales`."""
    if el.get("valor") is not None or el.get("unidad") is not None:
        return None
    tramo = str(el.get("tramo") or "").strip()
    for b in bloques:
        if tramo not in b["celdas"]:
            continue
        frase = re.sub(r"^en\s+", "", b["rotulo"].strip(" -–—()[]"), flags=re.I).strip()
        compuesto = f"{tramo} {frase}"
        cs = RCMP.analizar(compuesto, desc, titulo, plazo_sin_marcador) if frase else []
        if len(cs) != 1 or cs[0].texto != compuesto or cs[0].valor is None or cs[0].comparacion != el.get("comparacion"):
            continue
        c = cs[0]
        nuevo = dict(el)
        nuevo.update(valor=c.valor, unidad=c.unidad, regla_comparacion=c.regla)
        for k in ("moneda", "dias_tipo"):
            if getattr(c, k) is not None:
                nuevo[k] = getattr(c, k)
        if c.fuera_de_lista:
            nuevo["fuera_de_lista"] = sorted(set(nuevo.get("fuera_de_lista") or []) | set(c.fuera_de_lista))
        nuevo["originales"] = {**(el.get("originales") or {}), "regla_comparacion": el.get("regla_comparacion"),
                               "unidad_desde_rotulo": b["rotulo"], "tabla": b["tabla"], "chunk_id": b["chunk_id"]}
        return M.ElementoUmbral.model_validate(nuevo).model_dump(mode="json", exclude_defaults=True)
    return None


def _celdas_por_tabla(tablas_dir: Path | None) -> dict[str, list[tuple[str, list[str]]]]:
    """chunk_id → [(id de tabla, textos de sus celdas)] de las tablas de e0-r2 (como `_celdas_por_chunk`, por tabla)."""
    out: dict[str, list[tuple[str, list[str]]]] = {}
    if tablas_dir is None:
        return out
    for to in C.TOS_ORDEN:
        p = Path(tablas_dir) / f"tablas_{to}.json"
        if not p.exists():
            continue
        for t in json.loads(p.read_text(encoding="utf-8"))["tablas"]:
            celdas = [str(c) for s in t.get("segmentos", []) for f in s.get("filas", []) for c in f if c]
            for cid in t.get("chunks", []):
                out.setdefault(cid, []).append((t["id"], celdas))
    return out


def marcar_umbral_no_cuantificable_r2b(kg: dict, tramos_e1: dict[str, list[str]], celdas_tabla: dict, RCMP) -> dict:
    """Decisión 3 de T3-bis (S18, primera pieza): la Restriccion limite_cuantitativo que queda sin lista de
    umbrales y sin cuantía detectable (RCMP.detectar_cuantias) en su descripción, sus tramos (los de umbral de E1 y
    el de la entidad, en la procedencia) y las celdas de las tablas de sus chunks lleva la marca r2b
    `umbral_no_cuantificable` con el sha256 del detector. Ampliación tomada en la sesión de T3-bis: también la lleva,
    con su propio motivo y el sha256 de la lista, la que solo tiene cuantías en celdas de tablas forzadas a residual
    (tablas_residuales_forzadas_r2b.json). La marca va en `properties_no_definidas`: NodoR2 y la shape S26 cierran
    las claves de `properties` por tipo."""
    det_sha = C.sha256_path(Path(RCMP.__file__))
    crudo = TABLAS_FORZADAS_R2B.read_bytes()
    forz_sha = C.sha256_bytes(crudo)
    forzadas = {t["tabla"] for t in json.loads(crudo.decode("utf-8"))["tablas"]}
    filas, sin_marca = [], []
    for n in sorted(kg["nodes"], key=lambda x: x["id"]):
        props = n["properties"]
        if n["type"] != "Restriccion" or props.get("tipo") != "limite_cuantitativo" or props.get("umbrales"):
            continue
        cids = sorted({p.get("chunk_id") for p in n.get("provenances", []) if p.get("chunk_id")})
        textos = ([("descripcion", props.get("descripcion"))] + [("tramo_de_umbral_e1", t) for t in tramos_e1.get(n["id"], [])]
                  + [("tramo", p.get("tramo")) for p in n.get("provenances", []) if p.get("tramo")])
        en_texto = sorted({o for o, t in textos if isinstance(t, str) and RCMP.detectar_cuantias(t)})
        tablas_con = sorted({tid for cid in cids for tid, cs in celdas_tabla.get(cid, [])
                             if any(RCMP.detectar_cuantias(x) for x in cs)})
        fila = {"id": n["id"], "to": n["provenance"].get("to"), "chunks": cids, "descripcion": props.get("descripcion"),
                "cuantias_en": en_texto, "tablas_con_cuantias": tablas_con}
        if not en_texto and not tablas_con:
            motivo = MOTIVO_SIN_CUANTIA
        elif not en_texto and all(t in forzadas for t in tablas_con):
            motivo = MOTIVO_TABLA_FORZADA
        else:
            sin_marca.append(fila)
            continue
        nd = n.setdefault("properties_no_definidas", {})
        nd["umbral_no_cuantificable"] = True
        nd["umbral_no_cuantificable_motivo"] = motivo
        nd["umbral_no_cuantificable_detector_sha256"] = det_sha
        if motivo == MOTIVO_TABLA_FORZADA:
            nd["umbral_no_cuantificable_tablas_forzadas_sha256"] = forz_sha
        filas.append({**fila, "motivo": motivo})
    return {"resumen": {"marcados": len(filas), "por_motivo": C.conteo([{"m": f["motivo"]} for f in filas], "m"),
                        "por_to": C.conteo(filas, "to"), "sin_marca_con_cuantia": [f["id"] for f in sin_marca],
                        "detector_sha256": det_sha, "tablas_forzadas_sha256": forz_sha},
            "filas": filas, "sin_marca": sin_marca}


def enriquecer_procedencias_r2(kg: dict) -> dict:
    """Procedencia rica (los campos de r1_provenance: chunk_id, paginas,
    ancestros) conservando el `chunk_id` que trae la procedencia del perfil r2
    (r1_provenance, que no se edita, lo reasignaría por regla)."""
    chunks = {to: {c["id"]: c for c in _chunks_r2(to)} for to in C.TOS_ORDEN}
    stats = {"provenances": 0, "extraccion": 0, "esqueleto": 0, "sin_chunk": 0}

    def una(p: dict) -> None:
        stats["provenances"] += 1
        rol, to = p.get("rol_documental") or "", p.get("to")
        if rol == "esqueleto" or to not in C.TOS_ORDEN:
            p.setdefault("chunk_id", None)
            p.setdefault("paginas", [])
            p.setdefault("ancestros", [])
            stats["esqueleto"] += 1
            return
        cid = p.get("chunk_id")
        ch = chunks[to].get(cid) if cid else None
        if ch is None:
            stats["sin_chunk"] += 1
            p.setdefault("paginas", [])
            p.setdefault("ancestros", [])
            return
        ancestros = []
        for h in ch.get("herencia", []):
            if h["unidad_origen"] not in ancestros:
                ancestros.append(h["unidad_origen"])
        punto = p["punto"]
        if rol.startswith("herencia_"):
            paginas = sorted({pg for h in ch.get("herencia", []) if h["unidad_origen"] == punto
                              for pg in h.get("paginas", [])})
            ancestros = ancestros[:ancestros.index(punto)] if punto in ancestros else ancestros
        else:
            paginas = list(ch.get("paginas", []))
            ancestros = [a for a in ancestros if a != punto]
        p["paginas"] = paginas
        p["ancestros"] = ancestros
        stats["extraccion"] += 1

    for obj in kg["nodes"] + kg["edges"]:
        una(obj["provenance"])
        for p in obj.get("provenances", []):
            if p is not obj["provenance"]:
                una(p)
    return stats


def titulos_oficiales_inventario(tos: list[str]) -> dict[str, str]:
    """U-R2-CODIGO-2, C2, punto n: el título oficial de cada TO, tal cual, sin
    el punto final, de las dos fuentes de `REF.titulos_de_inventario`
    (`inventario_tos.csv`, `titulo_oficial`; para los cinco de desarrollo,
    `inventario_resumen.json`, `subset_excluido`), sin normalizar: es la
    materia del TextoOrdenado. Frena si falta alguno."""
    import csv  # noqa: PLC0415
    tit = {r["id"]: r["titulo_oficial"] for r in csv.DictReader(REF.INVENTARIO_TITULOS.open(encoding="utf-8"))}
    for x in json.loads(REF.INVENTARIO_RESUMEN.read_text(encoding="utf-8"))["subset_excluido"]:
        tit[x["id_interno"]] = x["titulo"]
    faltan = [t for t in tos if t not in tit]
    if faltan:
        raise RuntimeError(f"TOs sin título en el inventario: {faltan}")
    return {t: re.sub(r"\.\s*$", "", tit[t].strip()) for t in tos}


def version_y_materia_r2b(kg: dict, canon: dict[str, str], e0_r2_dir: Path | None) -> dict:
    """U-R2-CODIGO-2, C2, punto n (fase r2b): `version` del TextoOrdenado = la
    versión vigente de `pies_<to>.json` de la E0 e0-r2 (el pie legible con la
    vigencia más reciente; en un empate, el de mayor número), con la forma
    «Comunicación A 8378 (vigencia 20/12/2025)»; `materia` = el título
    oficial del inventario (`titulos_oficiales_inventario`). Un TO sin
    `pies_<to>.json` o sin páginas legibles queda sin `version`, declarado.
    Lo que traía E1 queda en `originales`."""
    tit = titulos_oficiales_inventario(sorted(canon))
    nodos = {n["id"]: n for n in kg["nodes"]}
    filas, sin_version = {}, []
    for to in sorted(canon):
        n = nodos.get(canon[to])
        if n is None:
            continue
        pies = None
        if e0_r2_dir is not None and (Path(e0_r2_dir) / f"pies_{to}.json").exists():
            pies = json.loads((Path(e0_r2_dir) / f"pies_{to}.json").read_text(encoding="utf-8"))
        vig = (pies or {}).get("version_vigente")
        nuevos = {"materia": tit[to]}
        if vig:
            nuevos["version"] = vig["valor"]
        else:
            sin_version.append(to)
        props = n.setdefault("properties", {})
        for k, v in nuevos.items():
            previo = props.get(k)
            if previo is not None and previo != v:
                n.setdefault("originales", {}).setdefault(k, previo)
            props[k] = v
        if not vig and "version" in props:
            n.setdefault("originales", {}).setdefault("version", props.pop("version"))
        car = (pies or {}).get("caratula")
        filas[to] = {"id": n["id"], "materia": tit[to], "version": nuevos.get("version"),
                     "pagina_del_pie_vigente": (vig or {}).get("pagina"),
                     "caratula": (car or {}).get("ultima_comunicacion_incorporada"),
                     "coincide_con_la_caratula": (pies or {}).get("coincide_con_la_caratula")}
    return {"por_to": filas, "sin_version": sin_version,
            "coinciden_con_la_caratula": sum(1 for f in filas.values() if f["coincide_con_la_caratula"] is True),
            "no_coinciden_con_la_caratula": sorted(t for t, f in filas.items()
                                                   if f["coincide_con_la_caratula"] is False)}


def aristas_derivadas_de_cola(kg: dict, chunks_cola: set[str]) -> dict:
    """U-R2-CODIGO-2, C2, punto q (fase r2b): aristas sin la marca de la cola
    que tocan un nodo que solo viene de la cola humana (nodo con la marca y
    todas sus procedencias en chunks de la cola). Se cuentan aparte, después
    de derivar `remite_a` y `establecida_en`, por predicado; la arista no
    lleva marca (AristaR2 no la admite en esas aristas)."""
    def chunks_de(o):
        return {p.get("chunk_id") for p in o.get("provenances", [])}
    solo = {n["id"] for n in kg["nodes"] if (n.get("properties") or {}).get("cola_humana") == "true"
            and chunks_de(n) and chunks_de(n) <= chunks_cola}
    filas = [{"source": e["source"], "relation": e["relation"], "target": e["target"],
              "rol_fuente": e.get("rol_fuente"),
              "nodo_de_la_cola": [x for x in (e["source"], e["target"]) if x in solo]}
             for e in kg["edges"] if (e["source"] in solo or e["target"] in solo)
             and (e.get("properties") or {}).get("cola_humana") != "true"]
    filas.sort(key=lambda f: (f["source"], f["relation"], f["target"]))
    return {"nodos_solo_de_la_cola": len(solo), "aristas": len(filas),
            "por_predicado": C.conteo([{"r": f["relation"]} for f in filas], "r"), "filas": filas}


def sumar_paso_por_e3(conteos: list[dict]) -> dict:
    """U-R2-CODIGO-2, C2, punto s: suma de los conteos de
    `runner_corpus.conteo_paso_por_e3` de cada TO (claves numéricas y
    diccionarios de conteos, recursivamente)."""
    total: dict = {}
    for c in conteos:
        for k, v in c.items():
            if isinstance(v, dict):
                total[k] = sumar_paso_por_e3([total.get(k, {}), v])
            else:
                total[k] = total.get(k, 0) + v
    return {k: (dict(sorted(v.items())) if isinstance(v, dict) and k == "por_estado" else v)
            for k, v in total.items()}


# U-OMISIONES-COD, grupo G (variante G-r de U-DIAG-CAP3-GRAFO): procedencia por tramo, solo para las entidades de
# contenido cuyo `punto` es un ancestro de su unidad.
TIPOS_G_R = ("Operacion", "Restriccion", "Excepcion", "Obligacion", "Potestad", "Condicion", "Definicion")
_SEP_TRAMO_G_R = re.compile(r"\s*\[\s*(?:…|\.\.\.)\s*\]\s*")


def ubicar_tramo_g_r(tramo: str | None, ch: dict, V, holgura) -> tuple[str, str | None, str | None]:
    """Dónde está el tramo de la entidad, con `V.verificar_tramo` («exacta» o «tokens»): en el texto propio de la
    unidad (de un tramo compuesto «encabezado […] ítem», su segundo segmento); si no, en el bloque heredado de un
    ancestro, del más cercano al más lejano (párrafo, título o el cruce de los dos; en el cruce, el tipo del
    párrafo). Devuelve (lugar, ancestro, tipo de bloque). La regla de U-DIAG-CAP3-GRAFO
    (`udiag_b_procedencia.ubicar`), con la función del validador en lugar de su copia por AST."""
    import comun_e1  # noqa: PLC0415 — e1_extractor, en el sys.path de este módulo
    def ok(aguja, texto):
        return V.verificar_tramo(aguja, texto or "", holgura)[0] in ("exacta", "tokens")
    if not tramo:
        return "sin_tramo", None, None
    segs = _SEP_TRAMO_G_R.split(tramo)
    compuesto = len(segs) == 2
    aguja = segs[-1] if compuesto else tramo
    if ok(aguja, ch.get("texto")):
        return ("compuesto_item_en_texto_propio" if compuesto else "texto_propio"), ch["unidad"], None
    if compuesto:
        aguja = tramo.replace("[…]", " ").replace("[...]", " ")
    mini = comun_e1.es_mini_chunk(ch)
    orden = []
    for h in ch.get("herencia", []):
        if h["unidad_origen"] not in orden:
            orden.append(h["unidad_origen"])
    if mini:
        propios = [h["texto"] for h in ch.get("herencia", []) if h["unidad_origen"] == ch["unidad"]]
        if propios and ok(aguja, "\n".join(propios + [ch.get("texto") or ""])):
            return "texto_propio", ch["unidad"], None
    for q in reversed(orden):
        if mini and q == ch["unidad"]:
            continue
        bloques = [h for h in ch["herencia"] if h["unidad_origen"] == q]
        par = [h for h in bloques if h["tipo"] != "encabezado"]
        for h in par:
            if ok(aguja, h["texto"]):
                return "parrafo", q, h["tipo"]
        for h in bloques:
            if h["tipo"] == "encabezado" and ok(aguja, h["texto"]):
                return "titulo", q, "encabezado"
        if ok(aguja, "\n".join(h["texto"] for h in bloques)):
            return "cruza_titulo_y_parrafo", q, (par[0]["tipo"] if par else "encabezado")
    return "no_ubicado", None, None


def corregir_procedencia_g_r(regs: list[dict], chunks: dict[str, dict], V, holgura,
                             procedencia_heredada: bool = False) -> dict:
    """G-r, sobre los registros de `entrada_r2`, antes de la resolución y de E2 (solo r2b): en una entidad de
    contenido con `punto` en un ancestro de su unidad, el punto pasa a la unidad si su texto propio contiene el tramo
    (o el segmento del ítem del tramo compuesto), o al ancestro cuyo bloque heredado lo contiene, con el
    `rol_documental` de ese bloque. Si el tramo no se ubica, nada cambia. Muta las entidades y devuelve el detalle.
    `procedencia_heredada` (U-PROC-HERENCIA): después de G-r, C1 y C2 (`procedencia_heredada_c1_c2`), con el punto y
    el rol que declaró E1 tomados antes de G-r; su detalle va en la clave `procedencia_heredada`. Con False
    (default), la salida de siempre."""
    import comun_e1  # noqa: PLC0415
    declarado: dict[int, tuple] = {}
    if procedencia_heredada:
        for r in regs:
            for e in (r.get("validacion") or {}).get("entidades", []):
                p = e.get("provenance") or {}
                declarado[id(e)] = (p.get("punto"), p.get("rol_documental"))
    cambios = []
    for r in regs:
        ch = chunks.get(r["chunk_id"])
        for e in (r.get("validacion") or {}).get("entidades", []):
            p = e.get("provenance") or {}
            if ch is None or e.get("type") not in TIPOS_G_R or p.get("punto") == ch["unidad"]:
                continue
            lugar, q, tipo = ubicar_tramo_g_r(p.get("tramo"), ch, V, holgura)
            if lugar in ("texto_propio", "compuesto_item_en_texto_propio"):
                nuevo = (ch["unidad"], f"bloque_{ch['rol_bloque']}" if comun_e1.es_mini_chunk(ch) else "punto_propio")
            elif lugar in ("parrafo", "titulo", "cruza_titulo_y_parrafo"):
                nuevo = (q, f"herencia_{tipo}")
            else:
                continue
            if nuevo == (p.get("punto"), p.get("rol_documental")):
                continue
            cambios.append({"chunk_id": r["chunk_id"], "local_id": e.get("local_id"), "type": e.get("type"),
                            "label": e.get("label"), "punto": p.get("punto"), "punto_g_r": nuevo[0],
                            "rol": p.get("rol_documental"), "rol_g_r": nuevo[1], "lugar": lugar})
            p["punto"], p["rol_documental"] = nuevo
            e["punto"] = nuevo[0]
    res = {"entidades_que_cambian": len(cambios),
           "cambia_el_punto": sum(1 for c in cambios if c["punto"] != c["punto_g_r"]),
           "solo_el_rol": sum(1 for c in cambios if c["punto"] == c["punto_g_r"]),
           "cambios": cambios}
    if procedencia_heredada:
        res["procedencia_heredada"] = procedencia_heredada_c1_c2(regs, chunks, V, holgura, declarado)
    return res


def bloque_ubicado_g_r(tramo: str, ch: dict, q: str, V, holgura) -> int | None:
    """C1 de U-PROC-HERENCIA, condición 3: el índice, en `herencia`, del bloque en el que `ubicar_tramo_g_r` ubica
    el tramo cuando da «parrafo» en el ancestro `q`. Es el primer bloque de `q` que no es un encabezado y contiene
    la misma aguja (el tramo; el compuesto, sin «[…]») con la misma verificación (`V.verificar_tramo`, «exacta» o
    «tokens»)."""
    aguja = tramo.replace("[…]", " ").replace("[...]", " ") if len(_SEP_TRAMO_G_R.split(tramo)) == 2 else tramo
    for k, h in enumerate(ch.get("herencia", [])):
        if (h["unidad_origen"] == q and h["tipo"] != "encabezado"
                and V.verificar_tramo(aguja, h["texto"] or "", holgura)[0] in ("exacta", "tokens")):
            return k
    return None


def id_nodo_e2_r2(e: dict, chunk_id: str, punto: str | None = None) -> str:
    """El id del nodo de una entidad de TIPOS_G_R en E2 (fase r2b): la misma función (`e2_lib.entity_slug_r2`) con
    los mismos argumentos que `e2_lib.ensamblar_r2`. Con `punto`, el id que tendría con ese punto en la procedencia."""
    prov = {**e["provenance"], "chunk_id": chunk_id}
    if punto is not None:
        prov["punto"] = punto
    props = dict(e.get("properties") or {})
    slug = e2_lib.entity_slug_r2({"type": e["type"], "label": e.get("label"), "properties": props}, prov, "r2b")
    return f"{e['type']}_{slug}"


def procedencia_heredada_c1_c2(regs: list[dict], chunks: dict[str, dict], V, holgura,
                               declarado: dict[int, tuple]) -> dict:
    """U-PROC-HERENCIA, C1 y C2, después de G-r (solo r2b, con `procedencia_heredada`). El mensaje de E1 trae toda
    la herencia de la unidad; el texto de E3 (`comun_e3.fuente_integro` con el bloque de la lista) trae solo los
    títulos, el bloque que abre la lista y el texto propio. Condición 1: el tramo, normalizado con
    `comun_e3.normalizar_para_cita`, no está en el texto de E3 de la unidad, normalizado igual.
      - C1, en una entidad de TIPOS_G_R que E1 declaró con el punto propio: con la condición 1, si
        `ubicar_tramo_g_r` ubica el tramo como «parrafo» en el bloque heredado de un ancestro (2) y ese bloque no es
        el que abre la lista (3; `comun_e3.indices_bloque_lista`), el punto pasa a ese ancestro y el rol a
        `herencia_<tipo del bloque>`, como en G-r. Lo que declaró E1 queda en `punto_declarado_e1` y
        `rol_declarado_e1`. El `chunk_id` no cambia: las páginas y los ancestros los rehace
        `enriquecer_procedencias_r2`.
      - C1 sin uniones (opción D): C1 no se aplica si, con el punto nuevo, la entidad pasaría a tener el id de otro
        nodo del ensamblado (`id_nodo_e2_r2`): el de un nodo que ya existe antes de C1, o el que C1 le dio a otra
        entidad antes en el orden de E2 (orden de E0 de los chunks). La entidad queda con el punto y el rol que
        declaró E1, C2 la marca igual y va a `uniones_evitadas`. Cuentan las entidades que E2 lleva al grafo
        (registros aceptados de un chunk del TO); el id empieza con el tipo y lleva el TO, así que solo puede
        coincidir con el de un nodo del mismo tipo y del mismo TO.
      - C2, en toda entidad, de cualquier tipo y punto: `tramo_fuera_del_texto_de_e3` True en la procedencia si el
        tramo cumple la condición 1 y está, normalizado igual, en un bloque heredado que no es un título ni el que
        abre la lista.
    `declarado`: id de la entidad → (punto, rol) de su procedencia antes de G-r. Muta las procedencias y devuelve
    las filas de C1, las de C2, las de las uniones evitadas y las de las entidades de C1 que cumplen la condición 1 y
    no las otras dos, con el lugar que da `ubicar_tramo_g_r`."""
    import comun_e3  # noqa: PLC0415 — e3_verificador, en el sys.path de este módulo
    norm = comun_e3.normalizar_para_cita
    orden = {cid: i for i, cid in enumerate(chunks)}
    regs = sorted(regs, key=lambda r: orden.get(r["chunk_id"], len(orden)))
    c1, c2, sin_c1, evitadas, candidatas, marcadas = [], [], [], [], [], []
    for r in regs:
        ch = chunks.get(r["chunk_id"])
        if ch is None:
            continue
        lista = set(comun_e3.indices_bloque_lista(ch))
        texto_e3 = norm(comun_e3.fuente_integro(ch, bloque_de_lista=True))
        solo_e1 = [norm(h["texto"] or "") for k, h in enumerate(ch.get("herencia", []))
                   if h["tipo"] != "encabezado" and k not in lista]
        for e in (r.get("validacion") or {}).get("entidades", []):
            p = e.get("provenance") or {}
            tramo = p.get("tramo")
            t = norm(tramo) if tramo else ""
            if not t or t in texto_e3:
                continue
            fila = {"chunk_id": r["chunk_id"], "local_id": e.get("local_id"), "type": e.get("type"),
                    "label": e.get("label"), "tramo": tramo}
            punto_e1, rol_e1 = declarado[id(e)]
            if e.get("type") in TIPOS_G_R and punto_e1 == ch["unidad"]:
                lugar, q, tipo = ubicar_tramo_g_r(tramo, ch, V, holgura)
                k = bloque_ubicado_g_r(tramo, ch, q, V, holgura) if lugar == "parrafo" else None
                if lugar == "parrafo" and q != ch["unidad"] and k is not None and k not in lista:
                    candidatas.append((r["chunk_id"], e, {**fila, "punto": punto_e1, "punto_c1": q, "rol": rol_e1,
                                                          "rol_c1": f"herencia_{tipo}"}))
                else:
                    sin_c1.append({**fila, "punto": punto_e1, "rol": rol_e1, "lugar": lugar, "ancestro": q,
                                   "bloque_que_abre_la_lista": None if k is None else k in lista})
            if any(t in b for b in solo_e1):
                marcadas.append((e, fila))
    en_e2 = {r["chunk_id"] for r in regs if r["chunk_id"] in orden and e2_lib._estado_registro(r)[0] == "aceptado"}
    existentes = {id_nodo_e2_r2(e, r["chunk_id"]) for r in regs if r["chunk_id"] in en_e2
                  for e in r["validacion"].get("entidades", []) if e.get("type") in TIPOS_G_R}
    de_c1: set[str] = set()
    for cid, e, f in candidatas:
        nuevo = id_nodo_e2_r2(e, cid, f["punto_c1"])
        if cid in en_e2 and (nuevo in existentes or nuevo in de_c1):
            evitadas.append({**f, "id": id_nodo_e2_r2(e, cid), "id_c1": nuevo,
                             "con": "nodo_existente" if nuevo in existentes else "c1_en_otra_entidad"})
            continue
        if cid in en_e2:
            de_c1.add(nuevo)
        c1.append(f)
        p = e["provenance"]
        p["punto"], p["rol_documental"] = f["punto_c1"], f["rol_c1"]
        p["punto_declarado_e1"], p["rol_declarado_e1"] = f["punto"], f["rol"]
        e["punto"] = f["punto_c1"]
    for e, fila in marcadas:
        p = e["provenance"]
        p["tramo_fuera_del_texto_de_e3"] = True
        c2.append({**fila, "punto": p.get("punto"), "rol": p.get("rol_documental")})
    return {"c1": c1, "c2": c2, "uniones_evitadas": evitadas, "c1_sin_las_otras_dos": sin_c1}


# U-OMISIONES-COD, grupo A: marcas del registro de omisiones y de los supuestos dentro de una norma (solo r2b). No
# tocan kg.json: van a omisiones.jsonl, a supuestos_en_norma.jsonl y al reporte.
_COPULA_REC = r"(es|son|sea|sean|sera|seran|seria|serian|resulta|resultan|resulte|resulten|resultaria|resultarian)"
RECOMENDACION_OMISION = {
    "copula_deseable": re.compile(r"\b" + _COPULA_REC + r"( (muy|altamente|particularmente))? "
                                  r"(deseables?|convenientes?|recomendables?|aconsejables?)\b"),
    "se_recomienda": re.compile(r"\bse (recomienda|recomiendan|recomendara|aconseja|aconsejan|sugiere|sugieren)\b"),
    "deberia": re.compile(r"\b(deberia|deberian)\b"),
    "buena_practica": re.compile(r"\bbuenas? practicas?\b"),
}
CONECTORES_SUPUESTO = {
    "cuando": re.compile(r"\bcuando\b"),
    "siempre_que": re.compile(r"\bsiempre (y cuando|que)\b"),
    "en_tanto": re.compile(r"\ben tanto\b"),
    "mientras": re.compile(r"\bmientras\b"),
    "en_la_medida": re.compile(r"\ben la medida (en )?que\b"),
    "en_caso": re.compile(r"\ben (el )?casos? (de|en que|que)\b|\ben los casos (en )?que\b"),
    "a_condicion": re.compile(r"\b(a|con la) condicion de\b"),
    "de_no": re.compile(r"\bde no\b"),
    "si": re.compile(r"\bsi\b(?! bien\b)"),
}
TIPOS_SUPUESTO_EN_NORMA = ("Obligacion", "Restriccion", "Potestad", "Excepcion", "Operacion", "Definicion")
TIPOS_SIN_CONTENIDO_A = ("TextoOrdenado", "Sujeto", "Comunicacion")


def _sin_numeracion(toks: list[str]) -> list[str]:
    i = 0
    while i < len(toks) and toks[i].isdigit():
        i += 1
    return toks[i:]


def donde_tramo_omision(tramo: str, chunk: dict, V, holgura) -> str:
    """La ubicación que `V.verificar_tramo_omision` cuenta en su registro, sin el registro: propio, heredado,
    orden_de_lectura o no."""
    if V.verificar_tramo(tramo, chunk.get("texto") or "", holgura)[0] != "no":
        return "propio"
    donde, nivel = "no", V.verificar_tramo(tramo, V.texto_completo(chunk), holgura)[0]
    if nivel != "no":
        donde = "heredado"
    if nivel != "exacta" and V._mini_a_mitad(chunk):
        if V._ORDEN_NIVEL[V.verificar_tramo(tramo, V.texto_en_orden_de_lectura(chunk), holgura)[0]] > V._ORDEN_NIVEL[nivel]:
            donde = "orden_de_lectura"
    return donde


def marcar_omision(o: dict, chunk: dict, con_extraccion: bool, V, holgura) -> dict:
    """(a) `tramo_en_heredado`: el tramo (el que recibió el validador) se ubica solo en el texto heredado; la
    omisión cuenta fuera de la pérdida propia de la unidad. (b) `revisar`, en `meta_normativo`: con marca del
    contador (`V.marcas_meta_normativo`) o con una recomendación (RECOMENDACION_OMISION; decisión 3 de la autora
    sobre el FRENO T4), con sus motivos. (c) `texto_propio_entero`: el tramo cubre todo el texto propio de la unidad
    sin la numeración inicial, con `es_item` y `con_extraccion` como atributos descriptivos."""
    t = o.get("tramo_modelo") or o.get("tramo")
    out = dict(o)
    if not t:
        return out
    donde = donde_tramo_omision(t, chunk, V, holgura)
    if donde == "heredado":
        out["tramo_en_heredado"] = True
    if o.get("categoria") == "meta_normativo":
        tn = " ".join(V.norm_tokens(t))
        motivos = [f"contador:{c}" for c in V.marcas_meta_normativo(t)] + [
            f"recomendacion:{k}" for k, rx in RECOMENDACION_OMISION.items() if rx.search(tn)]
        if motivos:
            out["revisar"] = motivos
    if donde == "propio":
        propio = _sin_numeracion(V.norm_tokens(chunk.get("texto") or ""))
        tt = _sin_numeracion(V.norm_tokens(o.get("tramo") or ""))
        if propio and tt and len(tt) == len(propio) and tt == propio:
            out["texto_propio_entero"] = {"es_item": bool(V._es_item(chunk)), "con_extraccion": con_extraccion}
    return out


def supuestos_en_norma(regs: list[dict], to: str, V) -> list[dict]:
    """(d) `supuesto_en_norma`: la entidad de contenido (no Condicion) cuya descripción o tramo lleva un supuesto,
    por un conector condicional de la lista cerrada CONECTORES_SUPUESTO. Mide y no corrige."""
    out = []
    for r in regs:
        for e in (r.get("validacion") or {}).get("entidades", []):
            if e.get("type") not in TIPOS_SUPUESTO_EN_NORMA:
                continue
            props = e.get("properties") if isinstance(e.get("properties"), dict) else {}
            textos = [x for x in (props.get("descripcion"), (e.get("provenance") or {}).get("tramo"))
                      if isinstance(x, str) and x]
            tn = " ".join(" ".join(V.norm_tokens(x)) for x in textos)
            marcadores = [k for k, rx in CONECTORES_SUPUESTO.items() if rx.search(tn)]
            if marcadores:
                out.append({"chunk_id": r["chunk_id"], "to": to, "local_id": e.get("local_id"), "type": e.get("type"),
                            "label": e.get("label"), "marcadores": marcadores})
    return out


def aristas_por_origen(kg: dict) -> dict:
    """U-OMISIONES-COD, grupo D, ítem h: las aristas de extracción separadas de las derivadas, con la clasificación
    de la observación 10 del tablero (`reext_t0/t3/medicion_tablero_r2b.py`, `obs10`)."""
    def rf(e):
        return e.get("rol_fuente") or (e.get("properties") or {}).get("rol_fuente")
    c = {"extraccion": 0, "remite_a": 0, "establecida_en_derivada": 0, "referencia_texto_ordenado_comunicacion": 0,
         "esqueleto": 0}
    for e in kg["edges"]:
        if e["relation"] == "remite_a" or (e["relation"] == "referencia" and rf(e) == "referencia_cruzada"):
            c["remite_a"] += 1
        elif e["relation"] == "referencia":
            c["referencia_texto_ordenado_comunicacion"] += 1
        elif rf(e) == "esqueleto":
            c["esqueleto"] += 1
        elif e["relation"] == "establecida_en" and rf(e) == "derivada_de_procedencia":
            c["establecida_en_derivada"] += 1
        else:
            c["extraccion"] += 1
    return c


CAUSA_UNIDAD_EXCLUIDA = "destino_en_unidad_excluida"


def irresolubles_en_unidad_excluida(registro: list[dict], excluidas: list[str]) -> dict:
    """U-OMISIONES-COD, grupo K (ENS-05): sin la cola, la cita irresoluble por «punto_sin_nodos» cuyo destino es una
    unidad excluida (o la contiene: `c == destino` o `c` empieza por `destino::`; la regla de
    `sincola_t0/registro_vista_r2b_sincola.py`) pasa a su causa propia. No cambia aristas. Devuelve las citas por
    causa con la unidad de cita del detector (chunk de origen, tramo, unidad citada)."""
    def excluido(dest):
        return bool(dest) and any(c == dest or c.startswith(dest + "::") for c in excluidas)
    for c in registro:
        for x in c["irresolubles"]:
            if x["causa"] == "punto_sin_nodos" and excluido(x.get("destino")):
                x["causa"] = CAUSA_UNIDAD_EXCLUIDA
    citas: dict[tuple, str] = {}
    for c in registro:
        for x in c["irresolubles"]:
            citas.setdefault((c.get("chunk_id") or C.prov_key(c["procedencia"]), c["evidencia"], x["destino"]),
                             x["causa"])
    por_causa: dict[str, int] = {}
    for v in citas.values():
        por_causa[v] = por_causa.get(v, 0) + 1
    return dict(sorted(por_causa.items()))


def descartar_cola_r2(regs: list[dict], con_cola: bool) -> tuple[list[dict], list[str]]:
    """U-SINCOLA-T0, enmienda 1 al mandato (06/10/2026), punto 3.c: con
    `con_cola` False, los registros de la cola humana que devuelve
    `runner_corpus.entrada_r2` (`cola_humana` True) se descartan antes de
    `resolver_relaciones_r2` y de `ensamblar_r2`, en ese único punto; el
    registro de omisiones, el paso por E3, `cola_estados`, `flaggear_cola_r2`
    y `aristas_derivadas_de_cola` se computan sobre lo que queda. Con True, los
    registros vuelven tal cual. Devuelve (registros, chunk_ids descartados en
    el orden de E0)."""
    if con_cola:
        return regs, []
    return ([r for r in regs if not r.get("cola_humana")],
            [r["chunk_id"] for r in regs if r.get("cola_humana")])


# ------------------------------------------------------------------------- #
# C1: la unión de las Comunicacion (--union-comunicaciones, cadena r2)       #
# ------------------------------------------------------------------------- #
def _leer_con_sha256(p: Path) -> tuple[bytes, str]:
    datos = Path(p).read_bytes()
    return datos, hashlib.sha256(datos).hexdigest()


def cargar_union_comunicaciones(ruta: Path, sha256: str, ruta_nodos: Path | None = None,
                                sha256_nodos: str | None = None) -> dict:
    """La regla C1 (solo en la cadena r2): lee la lista de los códigos que no se unen (`{"no_unir": [<codigo_normalizado>,
    ...]}`, que puede ir vacía) y, si se pasa, la de los nodos que no se unen (la lista de sus ids en el ensamblado con
    la guarda), cada una controlada con su sha256, y carga la normalización (`codigo_normalizado` de NORMALIZACION_C1)
    de su archivo, sin copiarla, con su candado. Frena (RuntimeError) si un sha256 no coincide o si una lista no tiene
    su forma."""
    import importlib.util               # noqa: PLC0415 — solo con --union-comunicaciones
    datos, sha = _leer_con_sha256(ruta)
    if sha != sha256:
        raise RuntimeError(f"candado de --union-comunicaciones: {ruta} tiene sha256 {sha}, no {sha256}")
    lista = json.loads(datos)
    if (not isinstance(lista, dict) or set(lista) != {"no_unir"} or not isinstance(lista["no_unir"], list)
            or not all(isinstance(c, str) for c in lista["no_unir"])):
        raise RuntimeError(f'--union-comunicaciones: {ruta} no es {{"no_unir": [<codigo_normalizado>, ...]}}')
    nodos, sha_nodos = None, None
    if ruta_nodos is not None:
        datos_n, sha_nodos = _leer_con_sha256(ruta_nodos)
        if sha_nodos != sha256_nodos:
            raise RuntimeError(f"candado de --union-comunicaciones-nodos: {ruta_nodos} tiene sha256 {sha_nodos}, "
                               f"no {sha256_nodos}")
        nodos = json.loads(datos_n)
        if not isinstance(nodos, list) or not all(isinstance(i, str) for i in nodos):
            raise RuntimeError(f"--union-comunicaciones-nodos: {ruta_nodos} no es una lista de ids")
    fuente, sha_norm = _leer_con_sha256(NORMALIZACION_C1)
    if sha_norm != NORMALIZACION_C1_SHA256:
        raise RuntimeError(f"candado de la normalización de C1: {_rel(NORMALIZACION_C1)} tiene sha256 {sha_norm}, "
                           f"no el sellado {NORMALIZACION_C1_SHA256}")
    spec = importlib.util.spec_from_file_location(MODULO_NORMALIZACION_C1, NORMALIZACION_C1)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[MODULO_NORMALIZACION_C1] = mod
    exec(compile(fuente, str(NORMALIZACION_C1), "exec"), mod.__dict__)   # los bytes del candado, sin releer el archivo
    return {"codigo_normalizado": mod.codigo_normalizado, "no_unir": frozenset(lista["no_unir"]), "no_unir_sha256": sha,
            "no_unir_nodos": None if nodos is None else frozenset(nodos), "no_unir_nodos_sha256": sha_nodos}


def ids_con_la_guarda(grafos: dict[str, dict]) -> dict[tuple[str, str], str]:
    """(to, id) → el id que la guarda (`INV.merge_grafos_guardado` sin C1) le da al nodo cuando lo renombra: el sufijo
    __<to> en los TOs posteriores al primero de una colisión de id entre TOs que no es Sujeto del catálogo. Un nodo
    que no está acá conserva su id."""
    por_to_id = {to: {n["id"]: n for n in grafos[to]["nodes"]} for to in C.TOS_ORDEN}
    return {(to, nid): f"{nid}__{to}" for nid, tos in INV.colisiones_cross_to(grafos).items()
            if not INV._es_sujeto_catalogo(por_to_id[tos[0]][nid]) for to in tos[1:]}


def preparar_union_c1(grafos: dict[str, dict], union: dict) -> dict:
    """La regla C1 con sus dos listas, antes de la guarda. Arma los grupos de las Comunicacion por código normalizado, en
    el orden de los TOs, y decide el código que recibe la guarda (`codigo_comunicacion`, nodo -> código o None):
      - un código de la lista de códigos queda con None en todos sus nodos: la guarda de siempre;
      - un nodo de la lista de nodos (por su id con la guarda) queda con None; si los nodos que quedan de su código son
        menos de 2 o están en menos de 2 TOs, no se une ninguno de los nodos de ese código (todos con None);
      - si un nodo de la lista comparte su id con nodos de otros TOs y alguno de ellos se une, los nodos de ese id
        reciben antes el renombre de la guarda (sufijo __<to>, `colision_cross_to` y sus aristas), como en
        `INV.merge_grafos_guardado`: así el nodo de la lista queda como con la bandera apagada y la unión no lo absorbe.
    La unión es la de `INV._unir_comunicaciones_c1`, que no une un código de un solo TO. La función reconoce los nodos
    por identidad: vale para los nodos de los grafos que devuelve. Devuelve esos grafos (los mismos objetos, o una copia
    con los renombres), la función, el id con la guarda de cada nodo (para el registro de las uniones) y las cuentas
    del resumen, sin contenido."""
    norm, no_unir = union["codigo_normalizado"], union["no_unir"]
    lista_nodos = union["no_unir_nodos"] or frozenset()
    ren = ids_con_la_guarda(grafos)
    guarda = {(to, i): ren.get((to, n["id"]), n["id"]) for to in C.TOS_ORDEN for i, n in enumerate(grafos[to]["nodes"])}
    grupos: dict[str, list[tuple[str, int]]] = {}
    for to in C.TOS_ORDEN:
        for i, n in enumerate(grafos[to]["nodes"]):
            if n.get("type") == "Comunicacion":
                c = norm(n)
                if c is not None:
                    grupos.setdefault(c, []).append((to, i))
    codigo: dict[tuple[str, int], str] = {}
    no_por_lista = no_por_muestra = 0
    unidos, de_la_lista = set(), []
    for c, ns in grupos.items():
        se_uniria = len({to for to, _ in ns}) > 1
        if c in no_unir:
            no_por_lista += se_uniria
            continue
        quedan = [k for k in ns if guarda[k] not in lista_nodos]
        if len(quedan) < len(ns) and (len(quedan) < 2 or len({to for to, _ in quedan}) < 2):
            no_por_muestra += se_uniria
            continue
        codigo.update({k: c for k in quedan})
        if len({to for to, _ in quedan}) > 1:
            unidos |= set(quedan)
            de_la_lista += [k for k in ns if k not in quedan]
    # el renombre de la guarda, antes de C1, para los ids que comparte un nodo de la lista con un nodo que se une
    id_de = {k: grafos[k[0]]["nodes"][k[1]]["id"] for k in guarda}
    ids_unidos = {id_de[k] for k in unidos}
    familias = {id_de[k] for k in de_la_lista if id_de[k] in ids_unidos}
    salida = grafos
    if familias:
        salida = {}
        for to in C.TOS_ORDEN:
            g = deepcopy(grafos[to])
            r = {nid: ren[(to, nid)] for nid in familias if (to, nid) in ren}
            for n in g["nodes"]:
                if n["id"] in r:
                    n["id"] = r[n["id"]]
                    n.setdefault("properties", {})["colision_cross_to"] = "true"
            for e in g["edges"]:
                if e["source"] in r:
                    e["source"] = r[e["source"]]
                if e["target"] in r:
                    e["target"] = r[e["target"]]
            salida[to] = g
    por_objeto = {id(salida[to]["nodes"][i]): c for (to, i), c in codigo.items()}
    guarda_de = {(to, salida[to]["nodes"][i]["id"]): gid for (to, i), gid in guarda.items()}
    ids_com = {gid for (to, i), gid in guarda.items() if grafos[to]["nodes"][i].get("type") == "Comunicacion"}
    cuentas = {"no_unir_sha256": union["no_unir_sha256"], "codigos_en_la_lista": len(no_unir),
               "codigos_que_no_se_unen_por_la_lista": no_por_lista,
               "nodos_sha256": union["no_unir_nodos_sha256"],
               "nodos_de_la_lista": None if union["no_unir_nodos"] is None else len(lista_nodos),
               "nodos_de_la_lista_en_el_grafo": None if union["no_unir_nodos"] is None else len(lista_nodos & ids_com),
               "codigos_que_no_se_unen_por_la_lista_de_nodos": no_por_muestra,
               "ids_con_el_renombre_de_la_guarda_antes_de_unir": len(familias)}
    return {"grafos": salida, "codigo_comunicacion": lambda n: por_objeto.get(id(n)), "guarda_de": guarda_de,
            "cuentas": cuentas}


def correr_cadena_r2(man: MC.Manifiesto, perfil, w=None, wl=None, tablas_dir: Path | None = None,
                     fase: str | None = None, con_cola: bool = True, cat_resolucion: dict | None = None,
                     procedencia_heredada: bool = False, union_comunicaciones: dict | None = None,
                     remisiones_a_subpuntos: bool = False) -> dict:
    """Cadena r2. `w(nombre, obj)` y `wl(nombre, filas)` escriben JSON y JSONL
    en <salida>/r2/ (None = no escriben). `fase`: «r2a» o «r2b»; por defecto,
    la del perfil del crudo (r2b con la forma r2). Pasarla explícita sirve a
    los controles (U-R2-CODIGO-2, C2): el crudo de r2a ensamblado con las
    reglas de r2b. Con r2b rigen además, solo en esta cadena, los puntos (m)
    a (s) de C2 de U-R2-CODIGO-2: versión y materia del TextoOrdenado (n),
    lista de umbrales completada (o), registro de omisiones (p), aristas
    derivadas que tocan un nodo de la cola contadas aparte (q), base con el
    detector de `remite_a` (r) y el conteo de elementos sin verificar por E3
    en el reporte (s); el plazo sin marcador (m) va por `llenar_umbrales_r2`.
    `con_cola` (U-SINCOLA-T0, enmienda 1, 06/10/2026): con False, los registros
    de la cola humana se descartan después de `entrada_r2`, en ese único punto
    (`descartar_cola_r2`), y lo que sigue se computa sobre lo que queda.
    `cat_resolucion` (R2 de U-RERESOL-CAT, W1): el catálogo de resolución de
    `r1_e4.catalogo_resolucion_r2`; reemplaza al del request en E4, en E2
    (labels y conjunto de ids) y en la normalización de los propuestos, y el
    resumen lleva sus tres versiones. Con None (default), la salida de siempre.
    `procedencia_heredada` (U-PROC-HERENCIA, solo r2b): C1 y C2 después de G-r
    (`corregir_procedencia_g_r`), con C1 sin uniones (opción D), y el detector
    de remisiones lee y resuelve las procedencias de C1 con el punto y el rol
    que declaró E1 (`punto_declarado_e1` de r1_referencias); su detalle va a
    procedencia_heredada.json y sus conteos, al resumen. La prende la
    re-aplicación única; el grafo de cada tanda se arma sin ella. Con False
    (default), la salida de siempre.
    `union_comunicaciones` (la regla C1, con --union-comunicaciones; lo que
    devuelve `cargar_union_comunicaciones`): la guarda une las Comunicacion de
    TOs distintos con el mismo código normalizado, salvo los códigos y los
    nodos de sus listas (`preparar_union_c1`); el registro va a uniones_c1.json
    y sus cuentas y su sha256, al resumen. La prende la re-aplicación única.
    Con None (default), la salida de siempre.
    `remisiones_a_subpuntos` (opción B): la cita a un punto padre o a una
    sección sin nodos anclados va al primer nivel con nodos de su subárbol, en
    una segunda pasada del detector que no toca las `remite_a` de la
    resolución exacta (`remisiones_a_subpuntos` de r1_referencias); sin la
    cola, la cita a una unidad excluida sigue con su causa. Sus conteos van a
    la clave `remisiones_a_subpuntos` de `remite_a` del resumen. Con False
    (default), la salida de siempre."""
    import runner_corpus as RC          # noqa: PLC0415 — solo con --perfil-r2
    w = w or (lambda *a, **k: None)
    wl = wl or (lambda *a, **k: None)
    M = E4.modulo_modelos_r2()
    V = E4.modulo_validador_r2()
    import reglas_comparacion as RCMP   # noqa: PLC0415 — pyd_r2/code, en el path por modulo_modelos_r2
    cat = cat_resolucion if cat_resolucion is not None else E4.catalogo_r2()
    validar, pol = RC.validador_perfil_r2(perfil)
    fase = fase or ("r2b" if RC.perfil_forma_r2(perfil) else "r2a")
    if fase not in e2_lib.FASES_R2:
        raise ValueError(f"fase desconocida: {fase!r}")
    r2b = fase == "r2b"
    if procedencia_heredada and not r2b:
        raise ValueError("procedencia_heredada es de la fase r2b: va después de G-r")
    versiones = {"catalogo_sha256": cat["catalogo_sha256"], "politica_sha256": pol.sha256,
                 "perfil": "r2", "prefijo_hash": perfil.prefijo_hash}
    resumen: dict = {"perfil_e1_del_crudo": perfil.nombre, **versiones, "etapas": []}
    if r2b:
        resumen["fase"] = fase
    resumen["con_cola"] = con_cola
    resumen["cola_descartada_por_to"] = {}
    if cat_resolucion is not None:
        resumen["catalogo_resolucion"] = cat_resolucion["versiones_catalogo"]
    omisiones: list[dict] = []
    paso_por_e3: dict[str, dict] = {}
    chunks_cola: set[str] = set()
    grafos, registro_total, resolucion_total, tramos_e1 = {}, [], [], {}
    conflictos_intra: list[dict] = []
    procedencia_g_r: list[dict] = []
    heredada: dict[str, list[dict]] = {"c1": [], "c2": [], "uniones_evitadas": [], "c1_sin_las_otras_dos": []}
    supuestos: list[dict] = []
    resumen["e2_por_to"] = {}
    for to in C.TOS_ORDEN:
        chunks = _chunks_r2(to)
        regs = RC.entrada_r2(to, C.SALIDA / to, chunks, perfil, validar)
        regs, descartadas = descartar_cola_r2(regs, con_cola)
        resumen["cola_descartada_por_to"][to] = {"n": len(descartadas), "chunks": descartadas}
        if r2b:
            g_r = corregir_procedencia_g_r(regs, {c["id"]: c for c in chunks}, V, pol.holgura, procedencia_heredada)
            procedencia_g_r += [{**c, "to": to} for c in g_r["cambios"]]
            for k, filas in g_r.get("procedencia_heredada", {}).items():
                heredada[k] += [{**c, "to": to} for c in filas]
        res = E4.resolver_relaciones_r2(regs, cat["indice"], cat["rol_por_to"], versiones, parte_a=r2b)
        ens = e2_lib.ensamblar_r2(chunks, regs, cat["labels"], sujetos_de_resolucion(cat, M), M.firma_r2,
                                  M.TIPOS_ENTIDAD, M.PREDICADOS, res["registro"], fase=fase)
        grafos[to] = {"nodes": ens["nodes"], "edges": ens["edges"]}
        cola_estados = {r["chunk_id"]: r["estado_e3"] for r in regs if r.get("cola_humana")}
        if r2b:
            # puntos p y s: el registro de omisiones (lo lee LN-7) y el conteo de elementos sin verificar por E3
            chunk_de = {c["id"]: c for c in chunks}
            omisiones += [marcar_omision({"chunk_id": r["chunk_id"], "to": to, **o}, chunk_de[r["chunk_id"]],
                                         any(e.get("type") not in TIPOS_SIN_CONTENIDO_A
                                             for e in (r.get("validacion") or {}).get("entidades", [])),
                                         V, pol.holgura)
                          for r in regs for o in (r.get("validacion") or {}).get("omisiones", [])]
            supuestos += supuestos_en_norma(regs, to, V)
            paso_por_e3[to] = RC.conteo_paso_por_e3(regs)
            chunks_cola |= set(cola_estados)
        r_cola = e2_lib.flaggear_cola_r2(grafos[to], cola_estados)
        tramos_e1.update(ens["tramos_umbral"])
        conflictos_intra += [{**c, "to": to} for c in ens["conflictos_properties"]]
        wl(f"por_to/{to}/no_mapeados_sujetos.jsonl", res["registro"])
        wl(f"por_to/{to}/resolucion_sujetos.jsonl", res["resolucion"])
        registro_total += res["registro"]
        resolucion_total += res["resolucion"]
        resumen["e2_por_to"][to] = {
            "nodes": len(ens["nodes"]), "edges": len(ens["edges"]),
            "origen_crudo": C.conteo([{"o": r["origen_crudo"]} for r in regs], "o"),
            "rechazados": sum(1 for r in regs if r.get("validacion") is None),
            "rechazos_validador": sum(len((r.get("validacion") or {}).get("rechazos", [])) for r in regs),
            "relaciones_no_verificadas_e3": sum(1 for r in regs for x in (r.get("validacion") or {}).get(
                "relaciones", []) if x.get("no_verificada_e3")),
            "cola_flaggeada": r_cola, "stats": ens["stats"], "rechazos_e2": len(ens["rechazos_e2"]),
            "conflictos_properties": len(ens["conflictos_properties"]), "resolucion_sujetos": res["resumen"]}
    resumen["etapas"].append("entrada_r2+sujetos+e2")
    print("[e2-r2]", json.dumps({to: (v["nodes"], v["edges"]) for to, v in resumen["e2_por_to"].items()}),
          flush=True)

    if union_comunicaciones is None:
        m = INV.merge_grafos_guardado(grafos)
    else:
        c1 = preparar_union_c1(grafos, union_comunicaciones)
        m = INV.merge_grafos_guardado(c1["grafos"], codigo_comunicacion=c1["codigo_comunicacion"])
    kg = {"nodes": m["nodes"], "edges": m["edges"]}
    inv = INV.verificar_invariantes(kg, m["grafos_pre_merge"], merges_nodo=len(m["merges_cross_to"]),
                                    merges_arista=INV.merges_arista_de(m["grafos_pre_merge"], kg["edges"]))
    assert inv["ok"], inv["fallos"]
    if union_comunicaciones is not None:
        # el registro de las uniones de la guarda, con el id que cada nodo tiene con la bandera apagada
        uniones = [{**u, "nodos": [{**x, "id_con_la_guarda": c1["guarda_de"][(x["to"], x["id_antes"])]}
                                   for x in u["nodos"]]} for u in m["uniones_c1"]]
        w("uniones_c1.json", uniones)
        resumen["union_comunicaciones"] = {
            **c1["cuentas"], "codigos_que_se_unen": len(uniones),
            "nodos_que_se_unen": sum(len(u["nodos"]) for u in uniones),
            "uniones_c1_sha256": sha256_texto(json.dumps(uniones, ensure_ascii=False, indent=1))}
    if r2b:
        r_prop = normalizar_propuestos_r2b(kg, registro_total, m["renombres"], cat)
        resumen["propuestos_r2b"] = r_prop["resumen"]
        wl("propuestos_descartados_aristas_quitadas.jsonl", r_prop["aristas_quitadas"])
    resumen["merge"] = {"merges_cross_to": len(m["merges_cross_to"]),
                        "nodos_con_colision_cross_to": sum(1 for n in kg["nodes"] if n.get("properties", {}).get(
                            "colision_cross_to") == "true"),
                        "adjudicacion_cross_to": len(m["adjudicacion_cross_to"]),
                        "conflictos_cross_to": len(m["conflictos"])}
    w("adjudicacion_cross_to.json", m["adjudicacion_cross_to"])

    r_to = E4.canonizar_texto_ordenado(kg)
    r_conf = E4.filtrar_conflictos(conflictos_intra, m["conflictos"])
    catalogo = C.cargar_catalogo()
    # U-R2-CODIGO-2, C2, punto e: la pasada residual de E4 se retira del perfil r2 (decisión 1 del mandato; en
    # la medición de r2a propuso 0 resoluciones sobre 24 propuestos). La clave queda, marcada como retirada,
    # porque la lee medicion_r2a/m2_medicion.py.
    resumen["e4"] = {"texto_ordenado": {"canonicos": r_to["canonicos"], "eliminados": len(r_to["eliminados"])},
                     "conflictos_cross_to": {k: v for k, v in r_conf.items()
                                             if k in ("n_total", "n_variantes_to", "n_reales")},
                     "pasada_residual_de_propuestos_medida_no_aplicada": {
                         "retirada": True, "motivo": "retirada del perfil r2 (U-R2-CODIGO-2, decisión 1 del "
                                                     "mandato): en r2a propuso 0 resoluciones sobre 24 propuestos"}}
    w("e4_texto_ordenado.json", r_to)
    w("e4_conflictos.json", r_conf)
    canon = {to: E4.id_texto_ordenado_canonico(C.archivo_de_to(to)) for to in C.TOS_ORDEN}
    if r2b:
        resumen["texto_ordenado_version_materia"] = version_y_materia_r2b(kg, canon, tablas_dir)

    r_esq = inyectar_esqueleto_v3(kg, catalogo)
    resumen["esqueleto"] = {k: v for k, v in r_esq.items() if k not in ("ids_creados", "paridad_kg_refinado")}
    inv = INV.verificar_invariantes(kg)
    assert inv["ok"], inv["fallos"]

    partes = {c["id"]: c for to in C.TOS_ORDEN for c in _chunks_r2(to) if "sub_chunk" in c}
    # grupo K: las unidades excluidas sin la cola (también las lee la opción B del detector)
    excluidas = ([c for x in resumen["cola_descartada_por_to"].values() for c in x["chunks"]]
                 if r2b and not con_cola else None)
    r_ref = REF.detectar_y_resolver(kg, perfil="r2", chunks_e0_r2=_chunks_e0_r2(tablas_dir),
                                    chunks_partes=partes or None, procedencia_propia=r2b, agrupar_sin_rol=r2b,
                                    punto_declarado_e1=procedencia_heredada,
                                    remisiones_a_subpuntos=remisiones_a_subpuntos, unidades_excluidas=excluidas)
    resumen["remite_a"] = r_ref["resumen"]
    if r2b and not con_cola:
        # grupo K: la causa propia de la cita a una unidad excluida, en el registro y en el reporte
        resumen["remite_a"]["irresolubles_por_causa"] = irresolubles_en_unidad_excluida(r_ref["registro"], excluidas)
    tipo_de = {n["id"]: n["type"] for n in kg["nodes"]}
    resumen["referencia_con_origen_distinto_de_texto_ordenado"] = sum(
        1 for e in kg["edges"] if e["relation"] == "referencia" and tipo_de[e["source"]] != "TextoOrdenado")
    resumen["comunicaciones"] = {k: v for k, v in r_ref["comunicaciones"].items() if k != "filas"}
    w("remisiones_registro.json", r_ref["registro"])
    w("comunicaciones_registro.json", r_ref["comunicaciones"])

    resumen["establecida_en_derivada"] = derivar_establecida_en(kg, canon)
    if r2b:
        r_der = aristas_derivadas_de_cola(kg, chunks_cola)
        resumen["aristas_derivadas_que_tocan_un_nodo_solo_de_la_cola"] = {k: v for k, v in r_der.items()
                                                                         if k != "filas"}
        w("aristas_derivadas_cola_humana.json", r_der["filas"])
        wl("omisiones.jsonl", omisiones)
        resumen["omisiones"] = {"filas": len(omisiones), "por_categoria": C.conteo(omisiones, "categoria")}
        # grupo A: (a) a (c) en el registro de omisiones, (d) en su propio registro
        resumen["omisiones"]["tramo_en_heredado"] = {
            "filas": sum(1 for o in omisiones if o.get("tramo_en_heredado")),
            "por_categoria": C.conteo([o for o in omisiones if o.get("tramo_en_heredado")], "categoria")}
        resumen["omisiones"]["perdida_propia_por_categoria"] = C.conteo(
            [o for o in omisiones if not o.get("tramo_en_heredado")], "categoria")
        rev = [o for o in omisiones if o.get("revisar")]
        resumen["omisiones"]["revisar"] = {
            "filas": len(rev), "con_marca_del_contador": sum(1 for o in rev if any(
                m.startswith("contador:") for m in o["revisar"])),
            "de_recomendacion": sum(1 for o in rev if any(m.startswith("recomendacion:") for m in o["revisar"])),
            "de_recomendacion_sin_marca_del_contador": sum(1 for o in rev if not any(
                m.startswith("contador:") for m in o["revisar"]))}
        ent = [o for o in omisiones if o.get("texto_propio_entero")]
        resumen["omisiones"]["texto_propio_entero"] = {
            "filas": len(ent), "por_categoria": C.conteo(ent, "categoria"),
            "es_item": sum(1 for o in ent if o["texto_propio_entero"]["es_item"]),
            "con_extraccion": sum(1 for o in ent if o["texto_propio_entero"]["con_extraccion"])}
        wl("supuestos_en_norma.jsonl", supuestos)
        resumen["supuestos_en_norma"] = {"entidades": len(supuestos), "unidades": len({x["chunk_id"] for x in supuestos}),
                                         "por_tipo": C.conteo(supuestos, "type"), "por_to": C.conteo(supuestos, "to")}
        w("procedencia_g_r.json", procedencia_g_r)
        resumen["procedencia_g_r"] = {"entidades_que_cambian": len(procedencia_g_r),
                                      "cambia_el_punto": sum(1 for c in procedencia_g_r if c["punto"] != c["punto_g_r"]),
                                      "solo_el_rol": sum(1 for c in procedencia_g_r if c["punto"] == c["punto_g_r"]),
                                      "cambia_el_punto_por_tipo": C.conteo([c for c in procedencia_g_r
                                                                            if c["punto"] != c["punto_g_r"]], "type")}
        if procedencia_heredada:
            w("procedencia_heredada.json", heredada)
            resumen["procedencia_heredada"] = {
                "c1": len(heredada["c1"]), "c1_por_tipo": C.conteo(heredada["c1"], "type"),
                "c1_por_to": C.conteo(heredada["c1"], "to"),
                "c2": len(heredada["c2"]), "c2_por_tipo": C.conteo(heredada["c2"], "type"),
                "c2_por_to": C.conteo(heredada["c2"], "to"),
                "uniones_evitadas": len(heredada["uniones_evitadas"]),
                "uniones_evitadas_por_to": C.conteo(heredada["uniones_evitadas"], "to"),
                "uniones_evitadas_por_causa": C.conteo(heredada["uniones_evitadas"], "con"),
                "c1_sin_las_otras_dos": len(heredada["c1_sin_las_otras_dos"]),
                "c1_sin_las_otras_dos_por_lugar": C.conteo(heredada["c1_sin_las_otras_dos"], "lugar")}
        resumen["paso_por_e3"] = {"por_to": paso_por_e3, "total": sumar_paso_por_e3(list(paso_por_e3.values()))}

    r_umb = llenar_umbrales_r2(kg, tramos_e1, _celdas_por_chunk(tablas_dir), M, V, RCMP, pol, fase)
    resumen["umbrales"] = r_umb["resumen"]
    w("umbrales_rangos_unidad_repetida.json", r_umb["rangos"])
    if r2b:
        r_nc = marcar_umbral_no_cuantificable_r2b(kg, tramos_e1, _celdas_por_tabla(tablas_dir), RCMP)
        resumen["umbral_no_cuantificable"] = r_nc["resumen"]
        w("umbral_no_cuantificable.json", {"marcados": r_nc["filas"], "sin_marca_con_cuantia": r_nc["sin_marca"]})

    resumen["procedencia"] = enriquecer_procedencias_r2(kg)
    inv = INV.verificar_invariantes(kg)
    assert inv["ok"], inv["fallos"]

    resumen["registro_no_mapeados"] = {
        "filas": len(registro_total), "por_estado": C.conteo([{"e": f["estado"]} for f in registro_total], "e"),
        "por_motivo": C.conteo([{"m": f["motivo"]} for f in registro_total], "m"),
        "cuarentena_sin_nodo": sum(1 for f in registro_total if f["estado"] == "cuarentena" and not f.get("id_nodo")),
        "propuestos_en_grafo_sin_fila": sorted(
            n["id"] for n in kg["nodes"] if n["type"] == "Sujeto" and n["properties"].get("nivel") == "propuesto"
            and n["id"] not in {f.get("id_nodo") for f in registro_total})}
    wl("no_mapeados_sujetos.jsonl", registro_total)
    wl("resolucion_sujetos.jsonl", resolucion_total)
    resumen["resolucion_sujetos"] = {
        "relaciones_de_sujeto": len(resolucion_total),
        "por_metodo": C.conteo([{"m": f["metodo_resolucion"]} for f in resolucion_total], "m"),
        "desacuerdos_regla_modelo": sum(f["desacuerdo_regla_modelo"] for f in resolucion_total)}


    kg["nodes"].sort(key=lambda n: n["id"])
    kg["edges"].sort(key=lambda e: (e["source"], e["relation"], e["target"]))
    tipo = {n["id"]: n["type"] for n in kg["nodes"]}
    con_arista = {e["source"] for e in kg["edges"]} | {e["target"] for e in kg["edges"]}
    resumen["aislados_por_tipo"] = C.conteo([{"t": n["type"]} for n in kg["nodes"] if n["id"] not in con_arista], "t")
    resumen["aristas_no_verificadas_e3"] = {
        "total": sum(1 for e in kg["edges"] if e.get("no_verificada_e3")),
        "por_firma": C.conteo([{"f": f"{tipo[e['source']]}-{e['relation']}-{tipo[e['target']]}"}
                               for e in kg["edges"] if e.get("no_verificada_e3")], "f")}
    resumen["validacion_modelos_r2"] = validar_grafo_r2(kg, M)
    if r2b:
        resumen["aristas_por_origen"] = aristas_por_origen(kg)
    kg_json = C.dumps_kg(kg)
    return {"kg": kg, "kg_json": kg_json, "sha256": C.sha256_bytes(kg_json.encode("utf-8")), "resumen": resumen}


def _chunks_r2(to: str) -> list[dict]:
    """Chunks de E0 del TO para la cadena r2: con las unidades partidas por
    corte en E1 (runner_corpus.py --perfil-r2, R4.b; particiones_por_corte.json
    de la salida del TO) reemplazadas por sus partes. Sin particiones, los de
    E0."""
    import runner_corpus as RC          # noqa: PLC0415 — solo con --perfil-r2
    return RC.chunks_con_partes(C.cargar_chunks_enm01(to), C.SALIDA / to)


def _chunks_e0_r2(e0_r2_dir: Path | None) -> dict[str, dict] | None:
    """chunk_id → chunk de e0-r2 (chunks_<to>.json de `correr_e0.py
    --version-e0 e0-r2`), para detectar las remisiones sobre su texto (regla b
    del perfil r2); None sin el directorio."""
    if e0_r2_dir is None:
        return None
    out: dict[str, dict] = {}
    for to in C.TOS_ORDEN:
        p = Path(e0_r2_dir) / f"chunks_{to}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for c in d["chunks"] if isinstance(d, dict) else d:
            out[c["id"]] = c
    return out


def _celdas_por_chunk(tablas_dir: Path | None) -> dict[str, list[str]]:
    """chunk_id → textos de celdas de las tablas de e0-r2 (tablas_<to>.json de
    `correr_e0.py --version-e0 e0-r2`); vacío sin el directorio."""
    out: dict[str, list[str]] = {}
    if tablas_dir is None:
        return out
    for to in C.TOS_ORDEN:
        p = Path(tablas_dir) / f"tablas_{to}.json"
        if not p.exists():
            continue
        for t in json.loads(p.read_text(encoding="utf-8"))["tablas"]:
            celdas = [str(c) for s in t.get("segmentos", []) for f in s.get("filas", []) for c in f if c]
            for cid in t.get("chunks", []):
                out.setdefault(cid, []).extend(celdas)
    return out


def validar_grafo_r2(kg: dict, M) -> dict:
    """Cada nodo con NodoR2 y cada arista con AristaR2 (pyd_r2), y la firma de
    cada arista con los tipos de sus extremos (modelos_r2.firma_arista: matriz
    r2, remite_a y esqueleto). Devuelve los conteos fuera del modelo, que deben
    ser 0, y los primeros errores."""
    from pydantic import ValidationError  # noqa: PLC0415
    tipo = {n["id"]: n["type"] for n in kg["nodes"]}
    nodos_fuera, aristas_fuera = [], []
    for n in kg["nodes"]:
        try:
            M.NodoR2.model_validate(n)
        except ValidationError as e:
            nodos_fuera.append({"objeto": n["id"], "error": str(e).splitlines()[0:3]})
    for e in kg["edges"]:
        clave = f"{e['source']}|{e['relation']}|{e['target']}"
        try:
            M.AristaR2.model_validate(e)
        except ValidationError as x:
            aristas_fuera.append({"objeto": clave, "error": str(x).splitlines()[0:3]})
            continue
        if not M.firma_arista(tipo[e["source"]], e["relation"], tipo[e["target"]]):
            aristas_fuera.append({"objeto": clave, "error": [f"firma {tipo[e['source']]} --{e['relation']}--> "
                                                             f"{tipo[e['target']]}"]})
    return {"nodos": len(kg["nodes"]), "aristas": len(kg["edges"]), "nodos_fuera_del_modelo": len(nodos_fuera),
            "aristas_fuera_del_modelo": len(aristas_fuera), "primeros": (nodos_fuera + aristas_fuera)[:20]}


def ensamblar_manifiesto_r2(man: MC.Manifiesto, entrada: Path, salida: Path,
                            tablas_dir: Path | None = None, con_cola: bool = True,
                            cat_resolucion: dict | None = None, procedencia_heredada: bool = False,
                            union_comunicaciones: dict | None = None, remisiones_a_subpuntos: bool = False) -> dict:
    """`con_cola` (U-SINCOLA-T0, enmienda 1 al mandato, 06/10/2026): con False,
    las dos corridas de `correr_cadena_r2` descartan los registros de la cola
    humana (`descartar_cola_r2`); el reporte declara `con_cola` y las unidades
    descartadas por TO. Con True (default), la salida de siempre.
    `cat_resolucion` (R2 de U-RERESOL-CAT, W1): el catálogo de resolución, en
    las redirecciones (esqueleto y conjunto de ids del merge entre TOs) y en las
    dos corridas; el reporte lleva sus tres versiones. Con None (default), el
    catálogo del request, como siempre.
    `procedencia_heredada` (U-PROC-HERENCIA): C1 (sin uniones) y C2, y las
    remisiones de C1 con el punto que declaró E1, en las dos corridas; el
    reporte lleva sus conteos. Con False (default), la salida de siempre.
    `union_comunicaciones` (la regla C1, con --union-comunicaciones): la unión
    de las Comunicacion con el mismo código normalizado, con sus listas, en las
    dos corridas; escribe uniones_c1.json y el reporte lleva sus cuentas y su
    sha256. Con None (default), la salida de siempre.
    `remisiones_a_subpuntos` (opción B): la remisión a un punto padre o a una
    sección cuyos subpuntos tienen nodos, en las dos corridas; el reporte lleva
    sus conteos. Con False (default), la salida de siempre."""
    perfil = perfil_e1.perfil(man.perfil_e1)
    entrada, salida = Path(entrada), Path(salida)
    salida_r2 = salida / "r2"
    M = E4.modulo_modelos_r2()
    cat = cat_resolucion if cat_resolucion is not None else E4.catalogo_r2()
    plan = plan_redirecciones_r2(man, perfil, entrada, salida_r2, cat, M)

    def w(nombre: str, obj) -> None:
        p = salida_r2 / nombre
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    def wl(nombre: str, filas: list[dict]) -> None:
        p = salida_r2 / nombre
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for r in filas:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with redirigido(plan):
        print("=== cadena r2, corrida 1 ===", flush=True)
        a = correr_cadena_r2(man, perfil, w, wl, tablas_dir, con_cola=con_cola, cat_resolucion=cat_resolucion,
                             procedencia_heredada=procedencia_heredada, union_comunicaciones=union_comunicaciones,
                             remisiones_a_subpuntos=remisiones_a_subpuntos)
        print("=== cadena r2, corrida 2 (sin escribir) ===", flush=True)
        b = correr_cadena_r2(man, perfil, None, None, tablas_dir, con_cola=con_cola, cat_resolucion=cat_resolucion,
                             procedencia_heredada=procedencia_heredada, union_comunicaciones=union_comunicaciones,
                             remisiones_a_subpuntos=remisiones_a_subpuntos)
    salida_r2.mkdir(parents=True, exist_ok=True)
    (salida_r2 / "kg.json").write_text(a["kg_json"], encoding="utf-8")
    reporte = {"grafo": f"{man.nombre}/r2", "perfil": "r2",
               "manifiesto": {"nombre": man.nombre, "path": _rel(man.path), "perfil_e1": man.perfil_e1,
                              "orden_corrida": list(man.orden_corrida), "e0_salida": _rel(man.e0_salida)},
               "entrada": _rel(entrada), "tablas_e0_r2": _rel(tablas_dir) if tablas_dir else None,
               "sha256_kg": a["sha256"], "sha256_kg_en_disco": C.sha256_path(salida_r2 / "kg.json"),
               "doble_corrida_byte_identica": a["kg_json"] == b["kg_json"],
               "nodes_total": len(a["kg"]["nodes"]), "edges_total": len(a["kg"]["edges"]),
               "nodes_by_type": C.conteo(a["kg"]["nodes"], "type"),
               "edges_by_relation": C.conteo(a["kg"]["edges"], "relation"),
               "redirecciones": describir_plan(plan), **a["resumen"]}
    w("reporte_ensamblado_r2.json", reporte)
    return {"r2": {k: reporte[k] for k in ("sha256_kg", "sha256_kg_en_disco", "doble_corrida_byte_identica",
                                            "nodes_total", "edges_total")},
            "validacion_modelos_r2": reporte["validacion_modelos_r2"]}


# ------------------------------------------------------------------------- #
# Selftest sobre el corpus de desarrollo (verdad conocida)                   #
# ------------------------------------------------------------------------- #
def selftest_dev(man: MC.Manifiesto, entrada: Path, salida: Path, resultado: dict) -> dict:
    """Comprueba, con perfil dev: (1) kg.json == 8e2eadee…; (2) r1/kg.json ==
    0226e947…; (3) réplica ≡ ensamblar_r1.correr directo (mismo kg_json);
    (4) inyector v3 local ≡ r1_e5_esqueleto.inyectar_esqueleto cuando ambos
    apuntan al catálogo v2 (mismo kg tras el esqueleto); (5) las redirecciones
    dev son identidad (inventario de remisión y orden iguales a los cableados)."""
    perfil = perfil_e1.perfil(man.perfil_e1)
    assert perfil.nombre == "produccion_dev", "el selftest de verdad conocida es del corpus de desarrollo"
    checks = {}
    checks["kg_e5_byte_identico_8e2eadee"] = (resultado["e5"]["sha256_kg"] == SELLOS_DEV["kg_e5"]
                                              and C.sha256_path(Path(salida) / "kg.json") == SELLOS_DEV["kg_e5"])
    checks["kg_r1_byte_identico_0226e947"] = (resultado["r1"]["sha256_kg"] == SELLOS_DEV["kg_r1"]
                                              and C.sha256_path(Path(salida) / "r1" / "kg.json") == SELLOS_DEV["kg_r1"])
    checks["cmp_con_salida_kg"] = ((Path(salida) / "kg.json").read_bytes()
                                   == (CORPUS_V2 / "salida" / "kg.json").read_bytes())
    checks["cmp_con_salida_r1_kg"] = ((Path(salida) / "r1" / "kg.json").read_bytes()
                                      == (CORPUS_V2 / "salida_r1" / "kg.json").read_bytes())

    plan = plan_redirecciones(man, perfil, entrada, Path(salida) / "r1")
    inv_man = inventario_desde_manifiesto(man)
    checks["inventario_remision_igual_al_cableado"] = inv_man == REF.INVENTARIO_TOS
    checks["orden_igual_al_cableado"] = tuple(man.orden_corrida) == C.TOS_ORDEN == EC.TOS_ORDEN
    # en dev, catálogo y conjunto de sujetos del plan son los cableados (identidad)
    valores = {(m.__name__, a): v for m, a, v in plan}
    checks["catalogo_dev_sin_cambio"] = (
        valores[("r1_comun", "CATALOGO_PATH")] == C.CATALOGO_PATH
        and valores[("assemble", "CATALOGO_PATH")] == assemble.CATALOGO_PATH
        and valores[("r1_invariantes", "SUJETOS_CATALOGO_SET")] == INV.SUJETOS_CATALOGO_SET
        and Path(entrada).resolve() == C.SALIDA.resolve()
        and Path(man.e0_salida).resolve() == C.E0_ENM01.resolve())
    with redirigido(plan):
        directo = correr_motor_ensamblar_r1(perfil, True, "final")
        replica = correr_cadena(perfil, True, "final", None)
        checks["replica_igual_a_ensamblar_r1_correr"] = (directo["kg_json"] == replica["kg_json"]
                                                          and directo["sha256"] == SELLOS_DEV["kg_r1"])
        # (4) inyector local vs r1_e5_esqueleto sobre el catálogo v2
        base = correr_cadena(perfil, True, "e4", None)
        kg_a, kg_b = deepcopy(base["kg"]), deepcopy(base["kg"])
        catalogo = C.cargar_catalogo()
        ra = E5.inyectar_esqueleto(kg_a, catalogo)
        rb = inyectar_esqueleto_v3(kg_b, catalogo)   # con assemble.CATALOGO_PATH = v2 (dev)
        checks["inyector_local_igual_a_r1_e5_esqueleto"] = C.dumps_kg(kg_a) == C.dumps_kg(kg_b)
        checks["inyector_local_mismo_reporte_salvo_paridad"] = (
            {k: v for k, v in ra.items() if k != "paridad_kg_refinado"}
            == {k: v for k, v in rb.items() if k != "paridad_kg_refinado"})
    checks["ok"] = all(v for k, v in checks.items())
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--manifiesto", type=Path, required=True, help="manifiesto de ensamblado (JSON)")
    ap.add_argument("--entrada", type=Path, required=True,
                    help="directorio con las salidas E1→E3 por TO (runner_corpus.py --salida)")
    ap.add_argument("--salida", type=Path, required=True, help="directorio de salida del ensamblado")
    ap.add_argument("--hasta", choices=ETAPAS, default="final")
    ap.add_argument("--sin-cola", action="store_true",
                    help="no inyectar la cola flaggeada (r1 corrió CON cola: default con cola); en la cadena r2 "
                         "(U-SINCOLA-T0, enmienda 1) descarta los registros de la cola humana después de entrada_r2")
    ap.add_argument("--motor", choices=("replica", "ensamblar_r1"), default="replica",
                    help="replica (default) = cadena r1 paso a paso; ensamblar_r1 = ensamblar_r1.correr "
                         "directo (solo perfil produccion_dev)")
    ap.add_argument("--selftest-dev", action="store_true",
                    help="tras ensamblar, verificar la verdad conocida del corpus de desarrollo")
    ap.add_argument("--resumen-json", type=Path, default=None, help="escribir el resumen de la corrida acá")
    ap.add_argument("--perfil-r2", action="store_true",
                    help="U-R2-CODIGO R3: cadena r2 (validador, política y catálogo r2) sobre la salida "
                         "guardada, en <salida>/r2/; no corre la cadena r1 ni el E5")
    ap.add_argument("--e0-r2", "--tablas-e0-r2", dest="tablas_e0_r2", type=Path, default=None,
                    help="con --perfil-r2: salida de correr_e0.py --version-e0 e0-r2 (chunks_<to>.json y "
                         "tablas_<to>.json): texto de las remisiones y verificación de umbrales contra las tablas")
    ap.add_argument("--catalogo-resolucion", dest="catalogo_resolucion", type=Path, default=None,
                    help="solo en la cadena r2 (R2 de U-RERESOL-CAT, W1): directorio con los generados del catálogo "
                         "de resolución (r1_e4.catalogo_resolucion_r2, con su candado); sin la opción, el catálogo "
                         "del request, como siempre")
    ap.add_argument("--procedencia-heredada", dest="procedencia_heredada", action="store_true",
                    help="solo en la cadena r2, fase r2b (U-PROC-HERENCIA): C1 (sin uniones) y C2 después de G-r, "
                         "la procedencia de los tramos que solo vio E1, y las remisiones de C1 con el punto que "
                         "declaró E1; sin la opción, el ensamblado de siempre")
    ap.add_argument("--union-comunicaciones", dest="union_comunicaciones", type=Path, default=None,
                    help="solo en la cadena r2 (la regla C1): une las Comunicacion de TOs distintos con el mismo código "
                         "normalizado, salvo los códigos de esta lista (JSON {\"no_unir\": [...]}, que puede ir vacía); va "
                         "con --union-comunicaciones-sha256; sin la opción, el ensamblado de siempre")
    ap.add_argument("--union-comunicaciones-sha256", dest="union_comunicaciones_sha256", default=None,
                    help="el sha256 de la lista de --union-comunicaciones: si no coincide, frena")
    ap.add_argument("--union-comunicaciones-nodos", dest="union_comunicaciones_nodos", type=Path, default=None,
                    help="con --union-comunicaciones: la lista de los nodos que no se unen (JSON con la lista de sus ids "
                         "en el ensamblado con la guarda); va con --union-comunicaciones-nodos-sha256; sin la opción, no "
                         "se excluye ningún nodo")
    ap.add_argument("--union-comunicaciones-nodos-sha256", dest="union_comunicaciones_nodos_sha256", default=None,
                    help="el sha256 de la lista de --union-comunicaciones-nodos: si no coincide, frena")
    ap.add_argument("--remisiones-a-subpuntos", dest="remisiones_a_subpuntos", action="store_true",
                    help="solo en la cadena r2 (opción B): la remisión a un punto padre o a una sección sin nodos "
                         "anclados va al primer nivel con nodos de su subárbol, sin tocar las remite_a de la "
                         "resolución exacta; sin la opción, el ensamblado de siempre")
    args = ap.parse_args()
    if (args.union_comunicaciones is None) != (args.union_comunicaciones_sha256 is None):
        ap.error("--union-comunicaciones y --union-comunicaciones-sha256 van juntas")
    if (args.union_comunicaciones_nodos is None) != (args.union_comunicaciones_nodos_sha256 is None):
        ap.error("--union-comunicaciones-nodos y --union-comunicaciones-nodos-sha256 van juntas")
    if args.union_comunicaciones_nodos is not None and args.union_comunicaciones is None:
        ap.error("--union-comunicaciones-nodos va con --union-comunicaciones")

    man = MC.cargar(args.manifiesto)
    # U-PROMPT-R2 (decisión 1 del mandato): un manifiesto con un perfil de forma «r2» (r2b) corre la cadena r2,
    # como --perfil-r2, con las tablas de su propia E0 (e0-r2) salvo que se indique otra. Los perfiles existentes
    # siguen con el camino por defecto.
    esq = perfil_e1.perfil(man.perfil_e1).esquema
    forma_r2 = esq is not None and getattr(esq, "forma_salida", "v3") == "r2"
    if args.perfil_r2 or forma_r2:
        tablas = args.tablas_e0_r2 if args.tablas_e0_r2 is not None else (man.e0_salida if forma_r2 else None)
        cat_res = (E4.catalogo_resolucion_r2(args.catalogo_resolucion) if args.catalogo_resolucion is not None
                   else None)
        union_c1 = (cargar_union_comunicaciones(args.union_comunicaciones, args.union_comunicaciones_sha256,
                                                args.union_comunicaciones_nodos, args.union_comunicaciones_nodos_sha256)
                    if args.union_comunicaciones is not None else None)
        res = ensamblar_manifiesto_r2(man, args.entrada, args.salida, tablas, con_cola=not args.sin_cola,
                                      cat_resolucion=cat_res, procedencia_heredada=args.procedencia_heredada,
                                      union_comunicaciones=union_c1, remisiones_a_subpuntos=args.remisiones_a_subpuntos)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        if args.resumen_json:
            args.resumen_json.parent.mkdir(parents=True, exist_ok=True)
            args.resumen_json.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0 if res["r2"]["doble_corrida_byte_identica"] else 1
    if args.catalogo_resolucion is not None:
        ap.error("--catalogo-resolucion es solo de la cadena r2")
    if args.procedencia_heredada:
        ap.error("--procedencia-heredada es solo de la cadena r2")
    if args.union_comunicaciones is not None:
        ap.error("--union-comunicaciones es solo de la cadena r2")
    if args.remisiones_a_subpuntos:
        ap.error("--remisiones-a-subpuntos es solo de la cadena r2")
    res = ensamblar_manifiesto(man, args.entrada, args.salida, hasta=args.hasta,
                               con_cola=not args.sin_cola, motor=args.motor)
    if args.selftest_dev:
        res["selftest_dev"] = selftest_dev(man, args.entrada, args.salida, res)
    print(json.dumps({k: v for k, v in res.items() if k != "redirecciones"}, ensure_ascii=False, indent=1))
    if args.resumen_json:
        args.resumen_json.parent.mkdir(parents=True, exist_ok=True)
        args.resumen_json.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = res.get("r1", {}).get("invariantes_ok", True)
    if "selftest_dev" in res:
        ok = ok and res["selftest_dev"]["ok"]
    if args.hasta == "final":
        ok = ok and res["r1"]["doble_corrida_byte_identica"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
