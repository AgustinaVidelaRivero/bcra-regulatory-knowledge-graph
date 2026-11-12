"""
selftest_e2.py — Selftest offline de E2 (T4). Cero LLM, cero red.

Cubre:
  1. Paridad de la convención de ids contra el fuente vigente: extrae
     slugify_full/_id_estable/entity_slug_v3 de assemble_v3.py por AST
     (assemble_v3 no es importable sin el SDK de API) y compara salida a
     salida contra la copia de e2_lib, sobre casos borde + las entidades
     reales de la corrida pro.
  2. Determinismo del ensamblado: mismo insumo dos veces ⇒ bytes idénticos;
     insumo con orden de llegada barajado ⇒ bytes idénticos (el orden
     canónico es el documental de E0, no el de llegada).
  3. Fixtures: colisión exacta (dedup + provenances acumuladas), no-colisión
     (contenido distinto ⇒ nodos distintos), refs rotas, firma inválida
     re-validada contra la matriz, set parcial (aborta sin flag / ensambla
     marcado con flag), chunk_id duplicado (precedente RX-01), chunk
     inesperado, sujeto propuesto en cuarentena.
  4. Censo estructural: unidad sin nodos listada como ausencia con
     diagnóstico cruzado con fan-in; ric 4.4 presente en el registro de
     limitaciones conocidas de E0 con su explicación ex ante (BKL-0024 como
     test conceptual: la ausencia se reporta, no se inventa).
  5. Integración: corrida real sobre pro (fan-in 88 = 87 + 1 rechazado
     contabilizado; conteos de entrada consistentes con resumen_faseB.json).
  6. Perfil r2, fase r2b (U-PROMPT-R2, P3b-2): la Operacion se une solo
     dentro de su punto, las properties_no_definidas de la relación pasan a la
     arista y stats["p3b"] cuenta las claves nuevas y las marcas de E3; con la
     fase r2a (default), lo de siempre.

Uso: python3 selftest_e2.py
"""

from __future__ import annotations

import ast
import copy
import json
import random
import sys

import e2_lib
from e2_lib import (
    ASSEMBLE_V3_PATH,
    BASE,
    FanInError,
    LIMITACIONES_E0,
    REEXTRACCION,
    censo_estructural,
    ensamblar,
    entity_slug_v3,
    guarda_fanin,
    reducir,
)

EXTRACCIONES_PRO = (REEXTRACCION / "e1_extractor" / "salida" / "faseB_pro"
                    / "extracciones.jsonl")
RESUMEN_PRO = EXTRACCIONES_PRO.parent / "resumen_faseB.json"

OK = 0
TOTAL = 0


def check(nombre: str, cond: bool, detalle: str = "") -> None:
    global OK, TOTAL
    TOTAL += 1
    estado = "ok" if cond else "FALLA"
    if cond:
        OK += 1
    print(f"[{TOTAL:02d}] {estado:5s} {nombre}" + (f" — {detalle}" if detalle else ""),
          flush=True)


# =========================================================================
# 1. Paridad de ids contra assemble_v3.py (por AST)
# =========================================================================

def funciones_v3_desde_fuente():
    """Compila slugify_full/_id_estable/entity_slug_v3 desde el texto de
    assemble_v3.py, sin importar el módulo (su cadena de imports requiere el
    SDK de API, ausente acá)."""
    arbol = ast.parse(ASSEMBLE_V3_PATH.read_text(encoding="utf-8"))
    quiero = {"slugify_full", "_id_estable", "entity_slug_v3"}
    modulo = ast.Module(
        body=[n for n in arbol.body
              if isinstance(n, ast.FunctionDef) and n.name in quiero],
        type_ignores=[])
    assert len(modulo.body) == 3, "assemble_v3.py ya no define las 3 funciones esperadas"
    ns = {"hashlib": __import__("hashlib"), "re": __import__("re"),
          "unicodedata": __import__("unicodedata"), "Any": object}
    exec(compile(ast.fix_missing_locations(modulo), str(ASSEMBLE_V3_PATH), "exec"), ns)
    return ns["entity_slug_v3"]


def test_paridad_ids():
    slug_v3 = funciones_v3_desde_fuente()
    casos = [
        {"type": "Obligacion", "label": "Etiqueta", "properties": {"descripcion": "Descripción con acentos, ñ y   espacios  dobles."}},
        {"type": "Obligacion", "label": "Sólo label", "properties": {}},
        {"type": "Restriccion", "label": "", "properties": {"descripcion": "x" * 300}},
        {"type": "Excepcion", "label": "Salvedad", "properties": {"descripcion": ""}},
        {"type": "Operacion", "label": "Compra de moneda extranjera", "properties": {"tipo": "cambiaria"}},
        {"type": "Operacion", "label": "", "properties": {"tipo": "cambiaria"}},
        {"type": "TextoOrdenado", "label": "TO X", "properties": {"archivo": "TO_x_actual.pdf"}},
        {"type": "TextoOrdenado", "label": "TO X", "properties": {"materia": "Materia Y"}},
        {"type": "Comunicacion", "label": "A 7825", "properties": {"codigo": "A-7825"}},
        {"type": "Comunicacion", "label": "A 7825", "properties": {}},
    ]
    registros = [json.loads(l) for l in EXTRACCIONES_PRO.open(encoding="utf-8")]
    for reg in registros:
        val = reg.get("validacion") or {}
        for e in val.get("entidades", []):
            casos.append({"type": e["type"], "label": e["label"],
                          "properties": e.get("properties") or {}})
    difs = [c for c in casos if entity_slug_v3(c) != slug_v3(c)]
    check("paridad ids e2_lib vs assemble_v3.py (AST)", not difs,
          f"{len(casos)} casos comparados (10 borde + entidades reales de pro)")


# =========================================================================
# Fixtures sintéticas
# =========================================================================

def chunk_fx(cid: str, unidad: str, to: str = "pro",
             flags: dict | None = None) -> dict:
    return {"id": cid, "to": to, "archivo": "fx.pdf", "unidad": unidad,
            "titulo": f"t {unidad}", "tipo": "punto_terminal",
            "herencia": [], "flags": flags or {}}


def prov_fx(punto: str) -> dict:
    return {"to": "pro", "archivo": "fx.pdf", "punto": punto,
            "rol_documental": "punto_propio"}


def ent_fx(local_id: str, etype: str, label: str, punto: str,
           props: dict | None = None) -> dict:
    return {"local_id": local_id, "type": etype, "label": label,
            "properties": props or {}, "provenance": prov_fx(punto)}


def rel_fx(source, target, pred: str, punto: str, sujeto_id=None,
           sujeto_propuesto=None, padre=None) -> dict:
    return {"source": source, "target": target, "predicate": pred,
            "sujeto_id": sujeto_id, "sujeto_propuesto": sujeto_propuesto,
            "sujeto_propuesto_padre_sugerido": padre,
            "provenance": prov_fx(punto)}


def reg_fx(cid: str, entidades: list, relaciones: list,
           rechazos: list | None = None, error=None) -> dict:
    return {"chunk_id": cid, "error": error,
            "validacion": {"chunk_id": cid, "entidades": entidades,
                           "relaciones": relaciones, "omisiones_no_prosa": [],
                           "rechazos": rechazos or [], "advertencias": [],
                           "metricas": {}}}


CHUNKS_FX = [chunk_fx("pro::9.1", "9.1"), chunk_fx("pro::9.2", "9.2")]
DESC = "Las entidades deberán informar el saldo diario."
REGS_FX = [
    reg_fx("pro::9.1",
           [ent_fx("to", "TextoOrdenado", "TO fx", "9.1", {"archivo": "fx.pdf"}),
            ent_fx("e1", "Obligacion", "Informar saldo", "9.1", {"descripcion": DESC})],
           [rel_fx("e1", "to", "establecida_en", "9.1"),
            rel_fx("e1", None, "aplica_a", "9.1",
                   sujeto_id="Sujeto_entidad_financiera")]),
    reg_fx("pro::9.2",
           [ent_fx("to", "TextoOrdenado", "TO fx", "9.2", {"archivo": "fx.pdf"}),
            ent_fx("e1", "Obligacion", "Informar saldo", "9.2", {"descripcion": DESC}),
            ent_fx("e2", "Obligacion", "Otra obligación", "9.2",
                   {"descripcion": "Contenido distinto."})],
           [rel_fx("e1", "to", "establecida_en", "9.2")]),
]


def test_colision_exacta():
    ens = ensamblar(CHUNKS_FX, REGS_FX)
    obligaciones = [n for n in ens["nodes"] if n["type"] == "Obligacion"]
    misma = [n for n in obligaciones if len(n["provenances"]) == 2]
    check("colisión exacta dedupea en 1 nodo con 2 provenances",
          len(obligaciones) == 2 and len(misma) == 1,
          f"{len(obligaciones)} Obligacion, provenances del dedupeado: "
          f"{[p['punto'] for p in misma[0]['provenances']] if misma else '—'}")
    tos = [n for n in ens["nodes"] if n["type"] == "TextoOrdenado"]
    check("contenido distinto NO se fusiona (solo colisiones idénticas)",
          len(tos) == 1 and len(obligaciones) == 2)
    aristas_dedup = [e for e in ens["edges"] if e["relation"] == "establecida_en"]
    check("arista repetida dedupea con provenances acumuladas",
          len(aristas_dedup) == 1 and len(aristas_dedup[0]["provenances"]) == 2)
    suj = [n for n in ens["nodes"] if n["id"] == "Sujeto_entidad_financiera"]
    check("sujeto de catálogo materializado con label del catálogo",
          len(suj) == 1 and suj[0]["label"] != "" and
          any(e["relation"] == "aplica_a" and e["target"] == "Sujeto_entidad_financiera"
              for e in ens["edges"]))


def test_ref_rota():
    regs = copy.deepcopy(REGS_FX)
    regs[0]["validacion"]["relaciones"].append(
        rel_fx("e1", "no_existe", "condiciona", "9.1"))
    ens = ensamblar(CHUNKS_FX, regs)
    rotas = [r for r in ens["rechazos_e2"] if r["motivo"] == "ref_colgante"]
    check("ref rota ⇒ rechazo registrado, sin arista y sin excepción",
          len(rotas) == 1 and len(ens["edges"]) == len(ensamblar(CHUNKS_FX, REGS_FX)["edges"]),
          rotas[0]["detalle"] if rotas else "—")


def test_firma_invalida():
    regs = copy.deepcopy(REGS_FX)
    # TextoOrdenado --condiciona--> Obligacion no está en la matriz DOMAIN_RANGE.
    regs[0]["validacion"]["relaciones"].append(
        rel_fx("to", "e1", "condiciona", "9.1"))
    ens = ensamblar(CHUNKS_FX, regs)
    firmas = [r for r in ens["rechazos_e2"] if r["motivo"] == "firma_invalida"]
    check("firma inválida re-validada contra la matriz ⇒ rechazo E2",
          len(firmas) == 1, firmas[0]["detalle"] if firmas else "—")


def test_set_parcial_y_duplicados():
    parcial = [REGS_FX[0]]
    fanin = guarda_fanin(CHUNKS_FX, parcial)
    check("fan-in detecta ausente y bloquea (apto=False)",
          fanin["ausentes"] == 1 and not fanin["apto_para_ensamblar"]
          and fanin["lista_ausentes"] == ["pro::9.2"])

    dup = REGS_FX + [copy.deepcopy(REGS_FX[0])]
    fanin_dup = guarda_fanin(CHUNKS_FX, dup)
    check("chunk_id duplicado detectado y bloquea (precedente RX-01)",
          fanin_dup["duplicados"] == ["pro::9.1"]
          and not fanin_dup["apto_para_ensamblar"])

    ines = REGS_FX + [reg_fx("pro::777", [], [])]
    fanin_in = guarda_fanin(CHUNKS_FX, ines)
    check("chunk inesperado detectado y bloquea",
          fanin_in["inesperados"] == ["pro::777"]
          and not fanin_in["apto_para_ensamblar"])

    rech = [REGS_FX[0], reg_fx("pro::9.2", [], [],
            rechazos=[{"nivel": "chunk", "motivo": "entities_o_relations_invalidos",
                       "detalle": "fx"}])]
    fanin_re = guarda_fanin(CHUNKS_FX, rech)
    check("rechazado contabilizado NO bloquea (apto=True)",
          fanin_re["rechazados"] == 1 and fanin_re["apto_para_ensamblar"]
          and fanin_re["rechazados_detalle"][0]["chunk_id"] == "pro::9.2")


def test_abort_reducir_parcial(tmp_dir):
    """reducir() aborta con FanInError sin flag y ensambla marcado con flag."""
    ex_path = tmp_dir / "fx_parcial.jsonl"
    ex_path.write_text(json.dumps(REGS_FX[0], ensure_ascii=False) + "\n",
                       encoding="utf-8")
    chunks_orig = e2_lib.cargar_chunks_e0
    e2_lib.cargar_chunks_e0 = lambda to, e0_dir=None: CHUNKS_FX
    oraculo_fx = {"pro": {"coincidencias": ["9.1", "9.2"], "solo_mapa": [],
                          "solo_parser": []}}
    try:
        try:
            reducir("pro", ex_path, censo_oraculo=oraculo_fx)
            abortado = False
        except FanInError as e:
            abortado = e.fanin["ausentes"] == 1
        check("reducir() aborta ante set parcial sin flag", abortado)
        res = reducir("pro", ex_path, permitir_parcial=True,
                      censo_oraculo=oraculo_fx)
        check("con --permitir-parcial ensambla y marca parcial=true",
              res["reporte"]["parcial"] is True and res["reporte"]["nodes_total"] > 0)
    finally:
        e2_lib.cargar_chunks_e0 = chunks_orig


def test_cuarentena():
    regs = copy.deepcopy(REGS_FX)
    regs[1]["validacion"]["relaciones"].append(
        rel_fx("e2", None, "aplica_a", "9.2",
               sujeto_propuesto="Cooperativa de crédito fx",
               padre="Sujeto_entidad_financiera"))
    ens = ensamblar(CHUNKS_FX, regs)
    props = [n for n in ens["nodes"] if n["id"].startswith("Sujeto_propuesto_")]
    check("sujeto propuesto ⇒ nodo en cuarentena + registro",
          len(props) == 1 and props[0]["properties"].get("cuarentena") == "true"
          and len(ens["cuarentena"]) == 1
          and ens["cuarentena"][0]["padres_sugeridos"] == ["Sujeto_entidad_financiera"])


def test_determinismo():
    ens_a = ensamblar(CHUNKS_FX, REGS_FX)
    ens_b = ensamblar(CHUNKS_FX, copy.deepcopy(REGS_FX))
    a = json.dumps({"nodes": ens_a["nodes"], "edges": ens_a["edges"]},
                   ensure_ascii=False, sort_keys=True)
    b = json.dumps({"nodes": ens_b["nodes"], "edges": ens_b["edges"]},
                   ensure_ascii=False, sort_keys=True)
    check("determinismo fixture: doble corrida ⇒ bytes idénticos", a == b)

    registros = [json.loads(l) for l in EXTRACCIONES_PRO.open(encoding="utf-8")]
    chunks = e2_lib.cargar_chunks_e0("pro")
    ens_1 = ensamblar(chunks, registros)
    barajados = list(registros)
    random.Random(20260810).shuffle(barajados)
    ens_2 = ensamblar(chunks, barajados)
    j1 = json.dumps({"nodes": ens_1["nodes"], "edges": ens_1["edges"]},
                    ensure_ascii=False, sort_keys=True)
    j2 = json.dumps({"nodes": ens_2["nodes"], "edges": ens_2["edges"]},
                    ensure_ascii=False, sort_keys=True)
    check("determinismo pro: orden de llegada barajado ⇒ grafo idéntico",
          j1 == j2, f"{len(ens_1['nodes'])} nodos, {len(ens_1['edges'])} aristas")


def test_censo_fixture():
    # 9.2 rechazado ⇒ 0 nodos de contenido en 9.2 ⇒ ausencia diagnosticada.
    regs = [REGS_FX[0], reg_fx("pro::9.2", [], [],
            rechazos=[{"nivel": "chunk", "motivo": "entities_o_relations_invalidos",
                       "detalle": "fx"}])]
    fanin = guarda_fanin(CHUNKS_FX, regs)
    ens = ensamblar(CHUNKS_FX, regs)
    oraculo_fx = {"pro": {"coincidencias": ["9.1", "9.2"], "solo_mapa": [],
                          "solo_parser": []}}
    censo = censo_estructural("pro", CHUNKS_FX, ens["nodes"], fanin, oraculo_fx)
    aus = censo["nivel_chunk"]["ausencias"]
    check("censo: unidad sin nodos listada como ausencia con diagnóstico fan-in",
          len(aus) == 1 and aus[0]["unidad"] == "9.2"
          and "rechazado" in aus[0]["diagnostico"],
          aus[0]["diagnostico"] if aus else "—")
    check("censo: la ausencia NO se inventa (0 nodos anclados a 9.2)",
          not any(p["punto"] == "9.2" for n in ens["nodes"]
                  for p in n["provenances"]))


def test_censo_ric_44():
    lim = LIMITACIONES_E0.get(("ric", "4.4"))
    check("registro de limitaciones E0 contiene ric 4.4 con cita ex ante",
          lim is not None and lim["clase"] == "defecto_documento_fuente"
          and "padre_4.4_no_abierto" in lim["cita"] and lim["cubierta_por"] == [])
    # Censo de ric con grafo vacío (ninguna extracción de ric existe aún):
    # 4.4 debe salir como ausencia CONOCIDA citando la explicación ex ante,
    # y las unidades de granularidad (S1, S12, 3.2) también quedan
    # diagnosticadas — nada queda como ausencia sin diagnóstico salvo las
    # unidades reales no extraídas (que en grafo vacío son todas).
    chunks_ric = e2_lib.cargar_chunks_e0("ric")
    fanin_vacio = guarda_fanin(chunks_ric, [])
    censo = censo_estructural("ric", chunks_ric, [], fanin_vacio)
    aus_44 = [a for a in censo["nivel_mapa"]["ausencias"] if a["unidad"] == "4.4"]
    check("censo ric (grafo vacío): 4.4 listada citando la explicación ex ante",
          len(aus_44) == 1 and "padre_4.4_no_abierto" in aus_44[0]["diagnostico"]
          and "ausencia conocida ex ante" in aus_44[0]["diagnostico"])
    lim_aplicadas = {l["unidad"] for l in
                     censo["nivel_mapa"]["limitaciones_conocidas_aplicadas"]}
    check("censo ric: limitaciones conocidas aplicadas incluyen 4.4",
          "4.4" in lim_aplicadas)


# =========================================================================
# 5. Integración: corrida real sobre pro
# =========================================================================

def test_integracion_pro():
    registros = [json.loads(l) for l in EXTRACCIONES_PRO.open(encoding="utf-8")]
    chunks = e2_lib.cargar_chunks_e0("pro")
    fanin = guarda_fanin(chunks, registros)
    check("fan-in pro: 88 esperados = 87 aceptados + 1 rechazado, 0 ausentes",
          fanin["esperados"] == 88 and fanin["aceptados"] == 87
          and fanin["rechazados"] == 1 and fanin["ausentes"] == 0
          and not fanin["duplicados"] and not fanin["inesperados"]
          and fanin["apto_para_ensamblar"],
          f"rechazado: {fanin['rechazados_detalle']}")

    res = reducir("pro", EXTRACCIONES_PRO)
    resumen = json.loads(RESUMEN_PRO.read_text(encoding="utf-8"))
    st = res["reporte"]["stats"]
    check("entradas del ensamblado == aceptadas por E1 (resumen_faseB)",
          st["entidades_in"] == resumen["elementos"]["entidades_aceptadas"]
          and st["relaciones_in"] == resumen["elementos"]["relaciones_aceptadas"],
          f"{st['entidades_in']} entidades, {st['relaciones_in']} relaciones")
    check("re-validación E2 sin rechazos nuevos (E1 ya validó firmas y refs)",
          res["reporte"]["rechazos_e2"] == [],
          f"{len(res['reporte']['rechazos_e2'])} rechazos")
    n_cont = st["entidades_in"] - st["merges_exactos"]
    check("conservación de nodos: entidades_in = nodos de contenido + merges "
          "(+ sujetos aparte)",
          res["reporte"]["nodes_total"] ==
          n_cont + sum(1 for n in res["grafo"]["nodes"] if n["type"] == "Sujeto"),
          f"{res['reporte']['nodes_total']} nodos = {n_cont} de extracción + "
          f"{sum(1 for n in res['grafo']['nodes'] if n['type'] == 'Sujeto')} sujetos")
    check("conservación de aristas: relaciones_in = aristas + prov acumuladas "
          "+ repetidas exactas + rechazos",
          st["relaciones_in"] == res["reporte"]["edges_total"]
          + st["prov_arista_acumuladas"] + st["aristas_repetidas_exactas"]
          + sum(1 for r in res["reporte"]["rechazos_e2"]
                if r["motivo"] in ("ref_colgante", "firma_invalida",
                                   "predicado_invalido", "sujeto_extremo_ausente",
                                   "sujeto_id_fuera_de_catalogo")),
          f"{st['relaciones_in']} = {res['reporte']['edges_total']} + "
          f"{st['prov_arista_acumuladas']} + {st['aristas_repetidas_exactas']} + 0")
    ids = [n["id"] for n in res["grafo"]["nodes"]]
    check("ids únicos y grafo sin refs rotas",
          len(ids) == len(set(ids)) and
          all(e["source"] in set(ids) and e["target"] in set(ids)
              for e in res["grafo"]["edges"]))
    nc = res["censo"]["nivel_chunk"]
    aus_rech = [a for a in nc["ausencias"] if a["chunk_id"] == "pro::3.1.1.2"]
    check("censo pro: la unidad del chunk rechazado figura como ausencia "
          "diagnosticada por fan-in",
          len(aus_rech) == 1 and "rechazado" in aus_rech[0]["diagnostico"])
    diag_por_chunk = {a["chunk_id"]: a["diagnostico"] for a in nc["ausencias"]}
    check("censo pro: ausencia por anclaje solo-herencia diagnosticada "
          "(pro::3.2.3.8 → chapeau 3.2.3)",
          "herencia" in diag_por_chunk.get("pro::3.2.3.8", ""))
    check("censo pro: ausencias por extracción solo-meta diagnosticadas "
          "(enumeración de sujetos 1.1.2.x)",
          all("solo meta" in diag_por_chunk.get(f"pro::1.1.2.{i}", "")
              for i in (1, 2, 3, 4, 6)))
    res2 = reducir("pro", EXTRACCIONES_PRO)
    check("determinismo end-to-end: doble reducir() ⇒ mismo sha256 del grafo",
          res["reporte"]["sha256_grafo"] == res2["reporte"]["sha256_grafo"],
          res["reporte"]["sha256_grafo"][:16])


def test_minichunks_fixture():
    """Enmienda 01: los mini-chunks son unidades esperadas del fan-in; sus
    elementos (rol bloque_<rol>) cuentan como contenido PROPIO; la cobertura
    del censo para un mini va por su aporte de chunk id (no por el punto, que
    otro chunk de la misma unidad pudo cubrir)."""
    mini = {"id": "pro::9.0::intro", "to": "pro", "archivo": "fx.pdf",
            "unidad": "9.0", "titulo": "[bloque intro] t 9.0",
            "tipo": "mini_chunk", "rol_bloque": "intro",
            "herencia": [], "flags": {}}
    chunks = [mini] + CHUNKS_FX

    # fan-in: el mini es esperado — su ausencia bloquea
    fanin_sin = guarda_fanin(chunks, REGS_FX)
    check("fan-in: mini-chunk ausente bloquea (unidad esperada del mapa)",
          fanin_sin["ausentes"] == 1 and fanin_sin["lista_ausentes"] == ["pro::9.0::intro"]
          and not fanin_sin["apto_para_ensamblar"])

    prov_mini = {"to": "pro", "archivo": "fx.pdf", "punto": "9.0",
                 "rol_documental": "bloque_intro"}
    reg_mini = {"chunk_id": "pro::9.0::intro", "error": None,
                "validacion": {"chunk_id": "pro::9.0::intro",
                               "entidades": [
                                   {"local_id": "to", "type": "TextoOrdenado",
                                    "label": "TO fx", "properties": {"archivo": "fx.pdf"},
                                    "provenance": prov_mini},
                                   {"local_id": "e1", "type": "Obligacion",
                                    "label": "Obligación del bloque",
                                    "properties": {"descripcion": "Contenido del intro."},
                                    "provenance": prov_mini}],
                               "relaciones": [
                                   {"source": "e1", "target": "to",
                                    "predicate": "establecida_en", "sujeto_id": None,
                                    "sujeto_propuesto": None,
                                    "sujeto_propuesto_padre_sugerido": None,
                                    "provenance": prov_mini}],
                               "omisiones_no_prosa": [], "rechazos": [],
                               "advertencias": [], "metricas": {}}}
    regs = [reg_mini] + REGS_FX
    fanin = guarda_fanin(chunks, regs)
    ens = ensamblar(chunks, regs)
    ap = ens["aporte_por_chunk"]["pro::9.0::intro"]
    check("aporte del mini: elemento bloque_intro cuenta como contenido propio",
          ap["contenido_propio"] == 1 and ap["contenido_herencia"] == 0)
    oraculo_fx = {"pro": {"coincidencias": ["9.0", "9.1", "9.2"], "solo_mapa": [],
                          "solo_parser": []}}
    censo = censo_estructural("pro", chunks, ens["nodes"], fanin, oraculo_fx,
                              aporte_por_chunk=ens["aporte_por_chunk"])
    check("censo: mini con contenido propio cubierto",
          censo["nivel_chunk"]["cubiertas"] == 3
          and not censo["nivel_chunk"]["ausencias"])

    # mini vacío (solo meta) → ausencia con diagnóstico de mini, aunque el
    # punto 9.1 esté cubierto por otro chunk (acá el mini es de la unidad 9.1)
    mini91 = dict(mini, id="pro::9.1::cierre", unidad="9.1", rol_bloque="cierre",
                  titulo="[bloque cierre] t 9.1")
    prov91 = {"to": "pro", "archivo": "fx.pdf", "punto": "9.1",
              "rol_documental": "bloque_cierre"}
    reg91 = {"chunk_id": "pro::9.1::cierre", "error": None,
             "validacion": {"chunk_id": "pro::9.1::cierre",
                            "entidades": [{"local_id": "to", "type": "TextoOrdenado",
                                           "label": "TO fx",
                                           "properties": {"archivo": "fx.pdf"},
                                           "provenance": prov91}],
                            "relaciones": [], "omisiones_no_prosa": [],
                            "rechazos": [], "advertencias": [], "metricas": {}}}
    chunks2 = CHUNKS_FX + [mini91]
    regs2 = REGS_FX + [reg91]
    fanin2 = guarda_fanin(chunks2, regs2)
    ens2 = ensamblar(chunks2, regs2)
    censo2 = censo_estructural("pro", chunks2, ens2["nodes"], fanin2,
                               {"pro": {"coincidencias": ["9.1", "9.2"],
                                        "solo_mapa": [], "solo_parser": []}},
                               aporte_por_chunk=ens2["aporte_por_chunk"])
    aus = censo2["nivel_chunk"]["ausencias"]
    check("censo: mini solo-meta es ausencia con diagnóstico propio aunque su "
          "punto esté cubierto por el chunk del punto",
          len(aus) == 1 and aus[0]["chunk_id"] == "pro::9.1::cierre"
          and "mini-chunk" in aus[0]["diagnostico"],
          aus[0]["diagnostico"] if aus else "—")


def test_fase_r2b():
    """U-PROMPT-R2, P3b-2: la fase r2b de ensamblar_r2, sobre registros sintéticos."""
    def prov(punto):
        return {"to": "x", "archivo": "a.pdf", "punto": punto, "rol_documental": "punto_propio"}

    def op(lid, punto):
        return {"local_id": lid, "type": "Operacion", "label": "Venta de cambio", "properties": {},
                "provenance": prov(punto)}
    ob = {"local_id": "ob1", "type": "Obligacion", "label": "O", "provenance": prov("1"),
          "properties": {"descripcion": "d1", "tipo": "otra"},
          "properties_no_definidas": {"modalidad": "se recomienda", "modalidad_clasificada": "recomendacion"}}
    rel = {"source": "ob1", "target": "op1", "predicate": "regula", "provenance": prov("1"),
           "properties_no_definidas": {"plazo_relativo": "previo"}}
    marcas = {"copia_nota_e3": [{"indice_crudo": 1, "campos": {"descripcion": ["a b c d e"]}}]}
    regs = [{"chunk_id": "x::1", "validacion": {"entidades": [op("op1", "1"), ob], "relaciones": [rel],
                                                "rechazos": [], "marcas_e3": marcas}},
            {"chunk_id": "x::2", "validacion": {"entidades": [op("op2", "2"), op("op3", "1")], "relaciones": [],
                                                "rechazos": []}}]
    chunks = [{"id": "x::1"}, {"id": "x::2"}]

    def ens(fase=None):
        kw = {} if fase is None else {"fase": fase}
        return e2_lib.ensamblar_r2(chunks, copy.deepcopy(regs), {}, frozenset(), lambda s, p, t: True,
                                   ("Operacion", "Obligacion"), ("regula",), [], **kw)
    a, a2, b = ens(), ens("r2a"), ens("r2b")
    ops = lambda e: sorted(sorted(p["chunk_id"] + "@" + p["punto"] for p in n["provenances"])  # noqa: E731
                           for n in e["nodes"] if n["type"] == "Operacion")
    check("r2b: fase r2a por defecto, igual byte a byte; sin stats p3b ni la clave en la arista",
          json.dumps(a, sort_keys=True) == json.dumps(a2, sort_keys=True) and "p3b" not in a["stats"]
          and "properties_no_definidas" not in a["edges"][0])
    check("r2a: las tres Operacion con la misma etiqueta se unen aunque sean de puntos distintos",
          ops(a) == [["x::1@1", "x::2@1", "x::2@2"]])
    check("r2b: la Operacion se une solo dentro de su punto (la del punto 1 de dos unidades sigue unida)",
          ops(b) == [["x::1@1", "x::2@1"], ["x::2@2"]])
    check("r2b: las properties_no_definidas de la relación pasan a la arista",
          b["edges"][0].get("properties_no_definidas") == {"plazo_relativo": "previo"})
    check("r2b: stats p3b cuenta las claves nuevas del nodo, la arista y las marcas de E3 de la unidad",
          b["stats"]["p3b"] == {"nodos_con_clave": {"modalidad": 1, "consecuencia": 0, "modalidad_clasificada": 1,
                                                    "copia_nota_e3": 0},
                                "modalidad_clasificada": {"recomendacion": 1},
                                "aristas_con_properties_no_definidas": 1,
                                "unidades_con_marca_e3": {"copia_nota_e3": 1}}, str(b["stats"].get("p3b")))
    try:
        ens("r2c")
        check("fase desconocida: error", False)
    except ValueError:
        check("fase desconocida: error", True)


def main() -> int:
    tmp = BASE / "salida" / "_selftest_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    test_paridad_ids()
    test_colision_exacta()
    test_ref_rota()
    test_firma_invalida()
    test_set_parcial_y_duplicados()
    test_abort_reducir_parcial(tmp)
    test_cuarentena()
    test_determinismo()
    test_censo_fixture()
    test_censo_ric_44()
    test_minichunks_fixture()
    test_integracion_pro()
    test_fase_r2b()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    print(f"\nselftest E2: {OK}/{TOTAL}", flush=True)
    return 0 if OK == TOTAL else 1


if __name__ == "__main__":
    sys.exit(main())
