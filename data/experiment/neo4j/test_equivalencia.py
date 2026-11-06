"""
test_equivalencia.py — Selftest de PARIDAD: Neo4jIndex vs GraphIndex in-memory,
por tool × grafo × modo (U-A1.1; extiende las 30 consultas de c26cb9b).

Criterio de paridad: BYTE-IDENTIDAD de `json.dumps(resultado, ensure_ascii=False)`
— exactamente la serialización con la que el harness entrega el output de cada
tool al modelo (harness.py, GraphAgent.ask: `result_str = json.dumps(result,
ensure_ascii=False)`). Comparar dicts con `==` no alcanza: ignora el orden de
claves, y el modelo ve bytes.

Dónde rige la paridad (falla = exit 1):
  - ver_nodo      : ambos modos, ambos grafos.
  - ver_vecinos   : ambos modos, ambos grafos.
  - buscar_nodos  : modo 'paridad', ambos grafos.
  - subclase      : GraphAgentNeo4j._run_tool == GraphAgent._run_tool (in-memory)
                    en modo paridad, y == Neo4jIndex directo en ambos modos.
Dónde NO rige (se reporta estructurado, no dispara freno):
  - buscar_nodos en modo 'fulltext' (divergencia deliberada: Lucene BM25 sobre
    label + descripcion + description + id_texto).

Casos (por grafo):
  A. Heredados de c26cb9b (solo KG-Refinado, ids fijos): 10 ver_nodo /
     10 ver_vecinos / 10 buscar_nodos.
  B. Generados determinísticamente desde el propio grafo (ambos grafos): un
     nodo por type, nodo aislado, hub máximo (truncamiento >40 en ambas
     direcciones), nodos en el BORDE de la ventana de 40 (mayor grado ≤40 y
     menor grado >40, por dirección), label más largo/más corto, nodo sin
     description/descripcion con ≥3 properties (camino orden-dependiente de
     _short_props), nodo con properties list/bool, descripcion más larga
     (truncado a 160 en resumen_propiedades), id inexistente, dirección
     inválida/None/mayúsculas, limite explícito en ver_vecinos.
  C. buscar_nodos de borde (ambos grafos): matches múltiples con empates de
     score (desempate por largo de label e id), sin resultados, consulta
     vacía / solo puntuación / solo stopwords, búsqueda por id pegado y por
     tokens del id, mayúsculas/acentos, numérica, caracteres reservados de
     Lucene, consulta muy larga, `limite` en 0 / negativo / >50 / no entero /
     None / str numérica / 1 / 50 / 51.
  D. Respuesta conocida (KG-Refinado):
     - BKL-0027 (asimetría direccional): ver_vecinos(rol, 'salientes') = 0
       salientes con n_entrantes_total=168; en 'entrantes' los 7 miembro_de
       ocupan las posiciones 1..7 de la ventana de 40.
     - BKL-0022 (huérfano léxico, orden-dependiente bajo ventana 40): ningún
       token del label trae al nodo al top-10; el label completo lo trae en
       pos 3; el nodo aparece en la ventana de 40 de ver_vecinos(
       Sujeto_entidad_financiera, entrantes) en una posición fija (medida y
       registrada) — su visibilidad depende del orden de kg.edges (r.orden).
     Ambos backends deben coincidir byte a byte Y con el valor esperado.

Salida: resumen por caso en stdout + detalle JSON en
  test_equivalencia_resultados_A11.json (junto a este script). El archivo
  test_equivalencia_resultados.json de c26cb9b se CONSERVA intacto (resultado
  histórico pre-A1.1, un solo grafo, un solo modo).
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

NEO4J_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(NEO4J_DIR))

from grafos import GRAFOS, CLAVES, cargar_vista_runtime, verificar_sha  # noqa: E402
from harness import GraphIndex, GraphAgent, _tokens  # noqa: E402  (solo IMPORT)
from conexion import abrir_driver  # noqa: E402
from neo4j_index import Neo4jIndex, MODOS  # noqa: E402
from agente_neo4j import GraphAgentNeo4j  # noqa: E402
from cargar_kg import KG_PATH  # noqa: E402,F401  (compatibilidad c26cb9b)

SALIDA_JSON = NEO4J_DIR / "test_equivalencia_resultados_A11.json"

# ============================================================================ #
# A. Casos heredados de c26cb9b (KG-Refinado)                                  #
# ============================================================================ #
CASOS_VER_NODO = [
    "Obligacion_cumplir_requerimientos_informacion_bcra_2d1942",
    "Operacion_compra_simultanea_con_liquidacion_de_divisas_ed538c",
    "Restriccion_prohibicion_de_incremento_de_posicion_a_primera_perdida_b9fc82",
    "Comunicacion_a_6146",           # crudo trae 3 provenances (vista loader: 1)
    "Excepcion_otros_proveedores_no_financieros_de_credito_alcanzados_por_las_normas_sobre_prov_5f95b9",
    "Sujeto_rol_sujeto_obligado_proteccion",
    "TextoOrdenado_to_proteccion_usuarios_servicios_financieros_actual_pdf",
    "Sujeto_entidad_financiera",
    "Operacion_clasificacion_de_deudor_de_la_cartera_comercial_con_seguimiento_especial_6_5_2_s_1d1a4b",  # con nota_fuente
    "Nodo_Inexistente_XYZ",          # error dict idéntico esperado
]

CASOS_VER_VECINOS = [
    ("Sujeto_rol_sujeto_obligado_proteccion", "entrantes"),   # BKL-0027
    ("Sujeto_rol_sujeto_obligado_proteccion", "ambas"),
    ("Sujeto_entidad_financiera", "ambas"),                   # hub (truncamiento)
    ("Sujeto_entidad_financiera", "salientes"),
    ("Comunicacion_a_6312", "ambas"),
    ("Excepcion_otros_proveedores_no_financieros_de_credito_alcanzados_por_las_normas_sobre_prov_5f95b9", "ambas"),
    ("TextoOrdenado_to_exterior_cambios_actual_pdf", "entrantes"),  # hub máximo (1512 aristas)
    ("Operacion_compra_de_opciones_0f6162", "ambas"),
    ("Obligacion_cumplir_requerimientos_informacion_bcra_2d1942", "direccion_invalida"),  # cae a "ambas"
    ("Nodo_Inexistente_XYZ", "ambas"),                        # error dict
]

CASOS_BUSCAR = [
    "efectivo mínimo",
    "tarjetas de crédito",
    "asociación mutual",
    "asociaciones mutuales o cooperativas",
    "excepto que se trate de asociaciones mutuales",   # verbatim solo-descripcion
    "sujetos obligados protección de usuarios",
    "liquidación de divisas exportaciones",
    "comunicacion a 6312",
    "posición global neta de moneda extranjera",
    "graduación del crédito",
]

# ============================================================================ #
# C. buscar_nodos de borde (ambos grafos): (etiqueta, consulta, limite)        #
#    limite=_DEF -> no se pasa (default de la firma)                           #
# ============================================================================ #
_DEF = object()
CASOS_BUSCAR_BORDE = [
    ("multiples_empate_score", "sujeto", _DEF),               # cientos de hits con score 1: desempate largo/id
    ("multiples_dos_tokens", "entidad financiera", _DEF),
    ("sin_resultados", "zzzz qqqq", _DEF),
    ("consulta_vacia", "", _DEF),
    ("solo_puntuacion", "¿?¡!...", _DEF),
    ("solo_espacios", "   ", _DEF),
    ("solo_stopwords", "de la", _DEF),                        # in-memory miles; full-text 0 (stopwords)
    ("solo_stopwords_2", "que se", _DEF),
    ("id_pegado_existente", "Sujeto_entidad_financiera", _DEF),
    ("id_pegado_hash", "Comunicacion_a_6312", _DEF),
    ("tokens_id_hash6", "0f6162", _DEF),                      # sufijo hash del id (canal id)
    ("mayusculas_acentos", "EFECTIVO MÍNIMO", _DEF),
    ("sin_acentos", "efectivo minimo", _DEF),
    ("numerica", "6312", _DEF),
    ("lucene_reservados_operadores", "efectivo AND minimo OR NOT tarjetas", _DEF),
    ("lucene_reservados_simbolos", "+efectivo -minimo efectivo* label:foo (a OR b) \"efectivo mínimo\" ~2 ^3 /regex/", _DEF),
    ("muy_larga", " ".join(["entidades financieras deberan informar al banco central"] * 30), _DEF),
    ("limite_1", "efectivo mínimo", 1),
    ("limite_0", "efectivo mínimo", 0),                       # -> 1
    ("limite_negativo", "efectivo mínimo", -3),               # -> 1
    ("limite_50", "sujeto", 50),
    ("limite_51", "sujeto", 51),                              # -> 50
    ("limite_100", "sujeto", 100),                            # -> 50
    ("limite_str_numerica", "efectivo mínimo", "7"),          # int("7") -> 7
    ("limite_str_no_numerica", "efectivo mínimo", "abc"),     # -> 10
    ("limite_none", "efectivo mínimo", None),                 # -> 10
    ("limite_float", "efectivo mínimo", 3.9),                 # int(3.9) -> 3
]

# ============================================================================ #
# D. Respuestas conocidas (KG-Refinado)                                        #
# ============================================================================ #
NODO_BKL0027 = "Sujeto_rol_sujeto_obligado_proteccion"
NODO_BKL0022 = "Sujeto_propuesto_entidades_financieras_del_grupo_2"
HUB_BKL0022 = "Sujeto_entidad_financiera"
ESPERADO_BKL0027 = {"n_salientes": 0, "n_entrantes_total": 168,
                    "posiciones_miembro_de_en_ventana": [1, 2, 3, 4, 5, 6, 7]}
ESPERADO_BKL0022 = {"pos_label_completo": 3,
                    "tokens_label_en_top10": [],           # ninguno lo trae al top-10
                    "pos_en_ventana_entrantes_hub": 7,     # medido sobre 26fac8b4 (post-C7);
                                                           # la nota post-C4 del backlog registraba 6
                    "n_entrantes_total_hub": 145}


# ============================================================================ #
def ser(x) -> str:
    """Serialización del harness (harness.py, GraphAgent.ask)."""
    return json.dumps(x, ensure_ascii=False)


def casos_generados(kg, clave: str) -> dict:
    """Casos B derivados determinísticamente del grafo (mismo grafo -> mismos casos)."""
    outc = collections.Counter(e.source for e in kg.edges)
    inc = collections.Counter(e.target for e in kg.edges)
    grado = {n.id: outc[n.id] + inc[n.id] for n in kg.nodes}
    uno_por_tipo = {}
    for n in kg.nodes:                       # primer nodo de cada type en orden de kg.nodes
        uno_por_tipo.setdefault(n.type, n.id)
    aislado = next(n.id for n in kg.nodes if grado[n.id] == 0)
    hub = max(kg.nodes, key=lambda n: (grado[n.id], n.id)).id

    def borde(cnt, cond, key):
        cands = [nid for nid, c in cnt.items() if cond(c)]
        return key(cands, key=lambda nid: (cnt[nid], nid)) if cands else None

    out_le40 = borde(outc, lambda c: c <= 40, max)
    out_gt40 = borde(outc, lambda c: c > 40, min)
    in_le40 = borde(inc, lambda c: c <= 40, max)
    in_gt40 = borde(inc, lambda c: c > 40, min)
    label_largo = max(kg.nodes, key=lambda n: (len(n.label or ""), n.id)).id
    label_corto = min(kg.nodes, key=lambda n: (len(n.label or ""), n.id)).id
    sin_desc = next(n.id for n in kg.nodes
                    if not (n.properties.get("description") or n.properties.get("descripcion"))
                    and len(n.properties) >= 3)
    con_list_bool = next((n.id for n in kg.nodes
                          if any(isinstance(v, (bool, list)) for v in n.properties.values())),
                         None)
    desc_larga = max(kg.nodes, key=lambda n: (len(str(n.properties.get("descripcion")
                                                        or n.properties.get("description") or "")),
                                                n.id)).id
    ver_nodo = [("tipo_" + t, nid) for t, nid in sorted(uno_por_tipo.items())] + [
        ("aislado", aislado), ("hub_max", hub), ("label_mas_largo", label_largo),
        ("label_mas_corto", label_corto), ("sin_desc_3props_orden", sin_desc),
        ("desc_mas_larga_trunc160", desc_larga), ("inexistente", "Nodo_Inexistente_XYZ"),
        ("inexistente_vacio", ""),
    ]
    if con_list_bool:
        ver_nodo.append(("props_list_bool", con_list_bool))
    ver_vecinos = [
        ("hub_max_ambas", hub, "ambas", _DEF),
        ("hub_max_salientes", hub, "salientes", _DEF),
        ("hub_max_entrantes", hub, "entrantes", _DEF),
        ("aislado_ambas", aislado, "ambas", _DEF),
        ("borde_out_le40", out_le40, "salientes", _DEF),
        ("borde_out_gt40", out_gt40, "salientes", _DEF),
        ("borde_in_le40", in_le40, "entrantes", _DEF),
        ("borde_in_gt40", in_gt40, "entrantes", _DEF),
        ("direccion_none", aislado, None, _DEF),
        ("direccion_mayusculas", hub, "ENTRANTES", _DEF),
        ("direccion_invalida", hub, "hacia_adelante", _DEF),
        ("limite_explicito_5", hub, "ambas", 5),
        ("limite_explicito_0", hub, "ambas", 0),
        ("inexistente", "Nodo_Inexistente_XYZ", "ambas", _DEF),
    ] + [("tipo_" + t + "_ambas", nid, "ambas", _DEF) for t, nid in sorted(uno_por_tipo.items())]
    ver_vecinos = [c for c in ver_vecinos if c[1] is not None]
    # buscar_nodos con el label completo de algunos nodos generados (matches múltiples reales)
    by_id = {n.id: n for n in kg.nodes}
    buscar = [("label_completo_" + t, by_id[nid].label) for t, nid in sorted(uno_por_tipo.items())]
    return {"ver_nodo": ver_nodo, "ver_vecinos": ver_vecinos, "buscar": buscar}


# ============================================================================ #
class Registro:
    def __init__(self):
        self.filas = []
        self.fallas_paridad = 0

    def paridad(self, grafo, modo, tool, caso, a, b, extra=None):
        sa, sb = ser(a), ser(b)
        igual = sa == sb
        fila = {"grafo": grafo, "modo": modo, "tool": tool, "caso": caso,
                "rige_paridad": True, "igual": igual, "bytes": len(sa)}
        if extra:
            fila.update(extra)
        if not igual:
            fila["in_memory"] = a
            fila["neo4j"] = b
            self.fallas_paridad += 1
        self.filas.append(fila)
        print(f"  {'✓' if igual else '✗'} [{grafo}/{modo}/{tool}] {caso}"
              + ("" if igual else "  <-- DIVERGE (paridad exigida)"))
        return igual

    def divergencia(self, grafo, modo, tool, caso, consulta, a, b):
        """buscar_nodos en modo fulltext: se describe, no se juzga."""
        ids_a = [r["id"] for r in a.get("resultados", [])]
        ids_b = [r["id"] for r in b.get("resultados", [])]
        solap = len(set(ids_a) & set(ids_b))
        identico = ser(a) == ser(b)
        fila = {
            "grafo": grafo, "modo": modo, "tool": tool, "caso": caso,
            "rige_paridad": False, "identico": identico, "consulta": consulta,
            "total_in_memory": a.get("total_con_match", a.get("total")),
            "total_neo4j": b.get("total_con_match", b.get("total")),
            "top_in_memory": ids_a, "top_neo4j": ids_b,
            "solapamiento_top": f"{solap}/{max(len(ids_a), len(ids_b), 1)}",
            "mismo_primer_resultado": (ids_a[:1] == ids_b[:1]),
            "hits_neo4j_con_0_tokens_label_id": sum(
                1 for r in b.get("resultados", []) if r.get("tokens_matcheados") == 0),
        }
        self.filas.append(fila)
        marca = "=" if identico else "≠"
        print(f"  {marca} [{grafo}/{modo}/buscar_nodos] {caso}: total "
              f"{fila['total_in_memory']} vs {fila['total_neo4j']}, solapamiento top "
              f"{fila['solapamiento_top']}, 1er resultado "
              f"{'igual' if fila['mismo_primer_resultado'] else 'DISTINTO'}")
        return identico


def _llamar_buscar(idx, consulta, limite):
    return idx.buscar_nodos(consulta) if limite is _DEF else idx.buscar_nodos(consulta, limite)


def _llamar_vecinos(idx, nid, direccion, limite):
    if limite is _DEF:
        return idx.ver_vecinos(nid, direccion=direccion)
    return idx.ver_vecinos(nid, direccion=direccion, limite=limite)


def correr_grafo(driver, clave: str, reg: Registro) -> dict:
    g = GRAFOS[clave]
    print(f"\n################ {clave} ({g['nombre_canonico']}, {g['sha256'][:8]}) ################")
    verificar_sha(clave)
    kg = cargar_vista_runtime(clave)
    gi = GraphIndex(kg)
    gen = casos_generados(kg, clave)
    conocidas = {}

    for modo in MODOS:
        ni = Neo4jIndex(driver, grafo=clave, modo=modo)
        print(f"\n== {clave} / modo={modo} / ver_nodo (paridad exigida) ==")
        if clave == "KG_Refinado":
            for nid in CASOS_VER_NODO:
                reg.paridad(clave, modo, "ver_nodo", f"heredado:{nid}",
                            gi.ver_nodo(nid), ni.ver_nodo(nid))
        for etiqueta, nid in gen["ver_nodo"]:
            reg.paridad(clave, modo, "ver_nodo", f"{etiqueta}:{nid}",
                        gi.ver_nodo(nid), ni.ver_nodo(nid))

        print(f"\n== {clave} / modo={modo} / ver_vecinos (paridad exigida) ==")
        if clave == "KG_Refinado":
            for nid, d in CASOS_VER_VECINOS:
                reg.paridad(clave, modo, "ver_vecinos", f"heredado:{nid} [{d}]",
                            gi.ver_vecinos(nid, direccion=d), ni.ver_vecinos(nid, direccion=d))
        for etiqueta, nid, d, lim in gen["ver_vecinos"]:
            a = _llamar_vecinos(gi, nid, d, lim)
            b = _llamar_vecinos(ni, nid, d, lim)
            extra = {}
            if "error" not in a:
                extra = {"n_salientes_total": a["n_salientes_total"],
                         "n_entrantes_total": a["n_entrantes_total"],
                         "salientes_truncado": a.get("salientes_truncado"),
                         "entrantes_truncado": a.get("entrantes_truncado")}
            reg.paridad(clave, modo, "ver_vecinos", f"{etiqueta}:{nid} [{d}]", a, b, extra)

        print(f"\n== {clave} / modo={modo} / buscar_nodos "
              f"({'paridad exigida' if modo == 'paridad' else 'divergencia deliberada, se reporta'}) ==")
        casos_b = ([("heredado", q, _DEF) for q in CASOS_BUSCAR] if clave == "KG_Refinado" else []) \
            + CASOS_BUSCAR_BORDE + [(e, q, _DEF) for e, q in gen["buscar"]]
        for etiqueta, q, lim in casos_b:
            a = _llamar_buscar(gi, q, lim)
            b = _llamar_buscar(ni, q, lim)
            caso = f"{etiqueta}:{q[:60]!r}" + ("" if lim is _DEF else f" limite={lim!r}")
            if modo == "paridad":
                reg.paridad(clave, modo, "buscar_nodos", caso, a, b,
                            {"total_con_match": a.get("total_con_match", a.get("total")),
                             "n_resultados": len(a.get("resultados", []))})
            else:
                reg.divergencia(clave, modo, "buscar_nodos", caso, q, a, b)

        # --- D. respuestas conocidas (KG-Refinado) ------------------------------
        if clave == "KG_Refinado":
            print(f"\n== {clave} / modo={modo} / respuestas conocidas BKL-0027 / BKL-0022 ==")
            a = gi.ver_vecinos(NODO_BKL0027, direccion="salientes")
            b = ni.ver_vecinos(NODO_BKL0027, direccion="salientes")
            reg.paridad(clave, modo, "ver_vecinos", "BKL-0027:salientes", a, b)
            a_e = gi.ver_vecinos(NODO_BKL0027, direccion="entrantes")
            b_e = ni.ver_vecinos(NODO_BKL0027, direccion="entrantes")
            reg.paridad(clave, modo, "ver_vecinos", "BKL-0027:entrantes", a_e, b_e)
            obs27 = {"n_salientes": len(b["salientes"]),
                     "n_entrantes_total": b["n_entrantes_total"],
                     "posiciones_miembro_de_en_ventana": [
                         i + 1 for i, x in enumerate(b_e["entrantes"]) if x["relation"] == "miembro_de"]}
            ok27 = obs27 == ESPERADO_BKL0027
            print(f"  {'✓' if ok27 else '✗'} BKL-0027 valor esperado {ESPERADO_BKL0027} "
                  f"observado(neo4j) {obs27}")

            label22 = gi.by_id[NODO_BKL0022].label
            toks_label = _tokens(label22)
            en_top10 = []
            for t in toks_label:
                a = gi.buscar_nodos(t)
                b = ni.buscar_nodos(t)
                if modo == "paridad":
                    reg.paridad(clave, modo, "buscar_nodos", f"BKL-0022:token_label:{t!r}", a, b)
                else:
                    reg.divergencia(clave, modo, "buscar_nodos", f"BKL-0022:token_label:{t!r}", t, a, b)
                if NODO_BKL0022 in [r["id"] for r in a["resultados"]]:
                    en_top10.append(t)
            a = gi.buscar_nodos(label22)
            b = ni.buscar_nodos(label22)
            if modo == "paridad":
                reg.paridad(clave, modo, "buscar_nodos", f"BKL-0022:label_completo:{label22!r}", a, b)
            else:
                reg.divergencia(clave, modo, "buscar_nodos", f"BKL-0022:label_completo:{label22!r}",
                                label22, a, b)
            ids = [r["id"] for r in a["resultados"]]
            ids_ft = [r["id"] for r in b["resultados"]]
            a_h = gi.ver_vecinos(HUB_BKL0022, direccion="entrantes")
            b_h = ni.ver_vecinos(HUB_BKL0022, direccion="entrantes")
            reg.paridad(clave, modo, "ver_vecinos", "BKL-0022:hub_entrantes", a_h, b_h)
            pos_v = [i + 1 for i, x in enumerate(b_h["entrantes"]) if x["vecino_id"] == NODO_BKL0022]
            obs22 = {"pos_label_completo": (ids.index(NODO_BKL0022) + 1) if NODO_BKL0022 in ids else None,
                     "tokens_label_en_top10": en_top10,
                     "pos_en_ventana_entrantes_hub": pos_v[0] if pos_v else None,
                     "n_entrantes_total_hub": b_h["n_entrantes_total"]}
            ok22 = obs22 == ESPERADO_BKL0022
            print(f"  {'✓' if ok22 else '✗'} BKL-0022 valor esperado {ESPERADO_BKL0022} "
                  f"observado(in-memory=neo4j paridad) {obs22}")
            if modo == "fulltext":
                print(f"    (informativo) full-text: label completo -> pos "
                      f"{(ids_ft.index(NODO_BKL0022) + 1) if NODO_BKL0022 in ids_ft else None}, "
                      f"total {b['total_con_match']}")
            conocidas[modo] = {"BKL-0027": {"esperado": ESPERADO_BKL0027, "observado": obs27, "ok": ok27},
                               "BKL-0022": {"esperado": ESPERADO_BKL0022, "observado": obs22, "ok": ok22,
                                            "label": label22, "tokens_label": toks_label,
                                            "fulltext_pos_label_completo": (
                                                (ids_ft.index(NODO_BKL0022) + 1) if NODO_BKL0022 in ids_ft else None)}}
            if not (ok27 and ok22):
                reg.fallas_paridad += 1

    # --- subclase: GraphAgentNeo4j._run_tool ------------------------------------
    print(f"\n== {clave} / subclase GraphAgentNeo4j._run_tool ==")
    ga = GraphAgent(kg, client=object())          # in-memory, cliente dummy (sin API)
    llamadas = [
        ("buscar_nodos", {"consulta": "efectivo mínimo"}),
        ("buscar_nodos", {"consulta": "efectivo mínimo", "limite": 3}),
        ("buscar_nodos", {}),                                     # consulta ausente -> ""
        ("ver_nodo", {"id": gen["ver_nodo"][0][1]}),
        ("ver_nodo", {}),                                         # id ausente -> ""
        ("ver_vecinos", {"id": gen["ver_vecinos"][0][1]}),
        ("ver_vecinos", {"id": gen["ver_vecinos"][0][1], "direccion": "entrantes"}),
        ("tool_desconocida", {"x": 1}),
    ]
    for modo in MODOS:
        ni = Neo4jIndex(driver, grafo=clave, modo=modo)
        agn = GraphAgentNeo4j(ni, client=object())
        assert agn.index is ni and agn.backend["modo"] == modo
        for name, args in llamadas:
            r_sub = agn._run_tool(name, dict(args))
            # (i) la subclase despacha exactamente al Neo4jIndex inyectado
            if name == "buscar_nodos":
                r_dir = ni.buscar_nodos(args.get("consulta", ""), args.get("limite", 10))
            elif name == "ver_nodo":
                r_dir = ni.ver_nodo(args.get("id", ""))
            elif name == "ver_vecinos":
                r_dir = ni.ver_vecinos(args.get("id", ""), args.get("direccion", "ambas"))
            else:
                r_dir = {"error": f"tool desconocida: {name}"}
            reg.paridad(clave, modo, "subclase", f"despacho==Neo4jIndex:{name}{args}", r_dir, r_sub)
            # (ii) en paridad, la subclase == GraphAgent in-memory (bytes)
            if modo == "paridad":
                reg.paridad(clave, modo, "subclase", f"GraphAgent(in-mem)==GraphAgentNeo4j:{name}{args}",
                            ga._run_tool(name, dict(args)), r_sub)
    def _s(x):
        return "<default>" if x is _DEF else str(x)
    return {"casos_generados": {k: [[_s(x) for x in c] for c in v] for k, v in gen.items()},
            "respuestas_conocidas": conocidas}


def main():
    driver = abrir_driver()
    reg = Registro()
    detalle_grafos = {}
    try:
        for clave in CLAVES:
            detalle_grafos[clave] = correr_grafo(driver, clave, reg)
    finally:
        driver.close()

    # Resumen por (grafo, modo, tool)
    resumen = collections.OrderedDict()
    for f in reg.filas:
        k = f"{f['grafo']}/{f['modo']}/{f['tool']}"
        r = resumen.setdefault(k, {"casos": 0, "iguales": 0, "rige_paridad": f["rige_paridad"]})
        r["casos"] += 1
        r["iguales"] += 1 if f.get("igual", f.get("identico")) else 0
    print("\n================ RESUMEN ================")
    for k, r in resumen.items():
        marca = "paridad" if r["rige_paridad"] else "informativo"
        print(f"  {k:45s} {r['iguales']:4d}/{r['casos']:<4d} idénticos  [{marca}]")
    total_par = sum(r["casos"] for r in resumen.values() if r["rige_paridad"])
    ok_par = sum(r["iguales"] for r in resumen.values() if r["rige_paridad"])
    print(f"\n  PARIDAD: {ok_par}/{total_par} casos byte-idénticos; fallas={reg.fallas_paridad}")

    SALIDA_JSON.write_text(
        json.dumps({"criterio": "byte-identidad de json.dumps(x, ensure_ascii=False) (serialización del harness)",
                    "resumen": resumen,
                    "paridad_total": f"{ok_par}/{total_par}",
                    "fallas_paridad": reg.fallas_paridad,
                    "detalle_grafos": detalle_grafos,
                    "filas": reg.filas},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  detalle -> {SALIDA_JSON.name}")
    sys.exit(0 if reg.fallas_paridad == 0 else 1)


if __name__ == "__main__":
    main()
