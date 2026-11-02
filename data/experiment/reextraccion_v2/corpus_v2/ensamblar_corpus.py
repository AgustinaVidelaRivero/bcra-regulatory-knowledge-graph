"""
ensamblar_corpus.py — Ensamblado FINAL del GRAFO v2 COMPLETO: merge
determinístico de los 5 grafos por TO producidos por la corrida de corpus
(runner_corpus.py → salida/<to>/grafo_<to>.json) en UN solo kg.json, más los
tests de respuesta conocida verificables sin gold externo.

Código puro, cero LLM. Reglas de merge (mismas que E2, extendidas cross-TO):
  - Nodos con el mismo id (= mismo type + slug de contenido, convención v3)
    se fusionan: provenances acumuladas con dedup exacto; properties
    first-write-wins EN ORDEN DE CORRIDA (pro → cla → ric → cap → ext, el
    mismo orden documental de la corrida) con todo conflicto REGISTRADO.
    Cross-TO solo colisionan nodos de contenido idéntico tras normalizar
    (en la práctica: Sujetos del catálogo compartido).
  - Aristas con la misma (source, relation, target) se fusionan igual.

Uso:  .venv/bin/python3 ensamblar_corpus.py [--salida DIR] [--manifiesto RUTA]
Escribe: salida/kg.json, salida/reporte_ensamblado.json,
         salida/tests_respuesta_conocida.json

U-B5.1: el orden de merge y la suite de tests de respuesta conocida salen del
manifiesto de corpus (default: manifiestos/desarrollo_5tos.json — orden y
suite idénticos a los históricos). Los tests son ESPECÍFICOS de cada corpus:
un manifiesto con tests_respuesta_conocida null los saltea con nota explícita
en el reporte (jamás se corre la suite de otro corpus en silencio).

U-ESQ-V3: el paso de ESQUELETO deja de ser un paso suelto corrido a mano y se
invoca acá, al producir el kg.json global. La inyección es ADITIVA y
CONDICIONAL: solo corre cuando el manifiesto declara `perfil_e1: "v3_b54"`
(o cuando se pasa --esquema-v3 explícitamente), y entonces lee el artefacto
`esq_v3_miembros/esquema_v3_clases.json`, que trae los 35 roles con sus
miembros. Sin perfil v3, el comportamiento es BYTE-IDÉNTICO al histórico: el
import de assemble es diferido y `ensamblar()` no toca el grafo.

La activación es por PERFIL DECLARADO y nunca por la mera presencia del
archivo en disco: un cambio de comportamiento que se dispara porque alguien
dejó un archivo en una ruta es acoplamiento invisible, justo lo que el
circuito evita. Sin artefacto y con perfil v3, se FRENA.

`build_skeleton()` de grafo_v2/code/assemble.py se REUSA tal cual (no se
porta ni se reescribe): lo único que cambia es a qué catálogo apunta. El
inyector replica el patrón de r1_e5_esqueleto — nodo del catálogo ya presente
se enriquece con la provenance de esqueleto, nodo ausente se crea, arista
ausente se agrega — sin su chequeo de paridad contra KG-Refinado, que es una
guarda del esqueleto v2 y por construcción no puede valer para el v3.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from copy import deepcopy
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REX = AQUI.parent
sys.path.insert(0, str(REX))

import manifiesto_corpus  # noqa: E402

TOS_ORDEN = ("pro", "cla", "ric", "cap", "ext")  # default legacy (cadena r1)

REPO = REX.parents[2]
GRAFO_V2_CODE = REPO / "data" / "experiment" / "grafo_v2" / "code"
ESQUEMA_V3_DEFAULT = (REPO / "data" / "experiment" / "esq_v3_miembros"
                      / "esquema_v3_clases.json")
PERFIL_CON_ESQUELETO_V3 = "v3_b54"


def _prov_esqueleto(p: dict) -> dict:
    """Provenance de esqueleto, con el formato de r1_e5_esqueleto."""
    return {"to": None, "archivo": p.get("source_doc"), "punto": p.get("location"),
            "rol_documental": "esqueleto"}


def _prov_key(p: dict) -> str:
    return json.dumps(p, ensure_ascii=False, sort_keys=True)


def inyectar_esqueleto_v3(kg: dict, ruta_catalogo: Path) -> dict:
    """Inyecta nodos y aristas de esqueleto desde el artefacto v3, ADITIVO.

    Reusa build_skeleton() de grafo_v2/code/assemble.py apuntándolo al
    catálogo v3; el import es diferido para que el camino por defecto no
    cargue nada de esto."""
    if str(GRAFO_V2_CODE) not in sys.path:
        sys.path.insert(0, str(GRAFO_V2_CODE))
    import assemble  # noqa: PLC0415 — import diferido (ver docstring del módulo)

    previo = assemble.CATALOGO_PATH
    assemble.CATALOGO_PATH = Path(ruta_catalogo)
    try:
        nodes_sk, edges_sk, counts_sk = assemble.build_skeleton()
    finally:
        assemble.CATALOGO_PATH = previo

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
            n.setdefault("provenances", [])
            if _prov_key(prov) not in {_prov_key(p) for p in n["provenances"]}:
                n["provenances"].append(prov)
            n["rol_fuente"] = "extraido+esqueleto"
            enriquecidos.append(sid)

    triplas = {(e["source"], e["relation"], e["target"]) for e in kg["edges"]}
    agregadas = 0
    for (s, r, t), e in edges_sk.items():
        if (s, r, t) in triplas:
            continue
        prov = _prov_esqueleto(e["provenance"])
        kg["edges"].append({"source": s, "target": t, "relation": r,
                            "provenance": prov, "provenances": [prov],
                            "rol_fuente": "esqueleto"})
        triplas.add((s, r, t))
        agregadas += 1

    cat = json.loads(Path(ruta_catalogo).read_text(encoding="utf-8"))
    exc = cat.get("excepciones_s15") or {}
    return {
        "catalogo": str(ruta_catalogo),
        "conteos_build_skeleton": counts_sk,
        "nodos_esqueleto_creados": len(creados),
        "nodos_esqueleto_enriquecidos": len(enriquecidos),
        "aristas_esqueleto_agregadas": agregadas,
        "roles_en_el_catalogo": sum(1 for r in cat.get("roles", [])),
        "roles_sin_miembro_declarados": exc.get("total"),
        "roles_sin_miembro_por_causa": exc.get("por_causa"),
    }


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def merge_grafos(grafos: dict[str, dict], orden: tuple | list | None = None) -> dict:
    if orden is None:
        orden = TOS_ORDEN  # forma de un argumento: la cadena r1 la importa tal cual
    nodes: dict[str, dict] = {}
    edges: dict[tuple, dict] = {}
    conflictos: list[dict] = []
    merges_nodo_cross_to: list[dict] = []

    for to in orden:
        for n in grafos[to]["nodes"]:
            nid = n["id"]
            if nid not in nodes:
                nodes[nid] = deepcopy(n)
                nodes[nid]["_tos"] = [to]
            else:
                m = nodes[nid]
                if to not in m["_tos"]:
                    merges_nodo_cross_to.append(
                        {"id": nid, "type": m.get("type"),
                         "label": m.get("label"), "tos": m["_tos"] + [to]})
                    m["_tos"].append(to)
                vistos = {json.dumps(p, ensure_ascii=False, sort_keys=True)
                          for p in m.get("provenances", [])}
                for p in n.get("provenances", []):
                    k = json.dumps(p, ensure_ascii=False, sort_keys=True)
                    if k not in vistos:
                        m.setdefault("provenances", []).append(p)
                        vistos.add(k)
                for k, v in (n.get("properties") or {}).items():
                    props = m.setdefault("properties", {})
                    if k not in props:
                        props[k] = v
                    elif props[k] != v:
                        conflictos.append({"nivel": "nodo", "id": nid,
                                           "property": k, "gana": props[k],
                                           "pierde": v, "to_perdedor": to})
                if n.get("label") != m.get("label"):
                    conflictos.append({"nivel": "nodo", "id": nid,
                                       "property": "label", "gana": m.get("label"),
                                       "pierde": n.get("label"), "to_perdedor": to})
        for e in grafos[to]["edges"]:
            k = (e["source"], e["relation"], e["target"])
            if k not in edges:
                edges[k] = deepcopy(e)
            else:
                m = edges[k]
                vistos = {json.dumps(p, ensure_ascii=False, sort_keys=True)
                          for p in m.get("provenances", [])}
                for p in e.get("provenances", []):
                    pk = json.dumps(p, ensure_ascii=False, sort_keys=True)
                    if pk not in vistos:
                        m.setdefault("provenances", []).append(p)
                        vistos.add(pk)

    for n in nodes.values():
        n.pop("_tos", None)
    return {"nodes": list(nodes.values()), "edges": list(edges.values()),
            "conflictos": conflictos, "merges_cross_to": merges_nodo_cross_to}


# --------------------- tests de respuesta conocida ----------------------- #
def _nodos_con(nodes: list[dict], pred) -> list[dict]:
    return [n for n in nodes if pred(n)]


def _texto_nodo(n: dict) -> str:
    partes = [n.get("label", "")]
    for v in (n.get("properties") or {}).values():
        partes.append(str(v))
    return _norm(" ".join(partes))


def _puntos(n: dict) -> set[str]:
    return {p.get("punto", "") for p in n.get("provenances", [])}


def _archivos(n: dict) -> set[str]:
    return {p.get("archivo", "") for p in n.get("provenances", [])}


def tests_respuesta_conocida(kg: dict) -> dict:
    nodes = kg["nodes"]
    res = {}

    # T1 — BKL-0024: ext 3.9 tiene nodos de contenido, con el tope USD 200.
    ext39 = _nodos_con(nodes, lambda n: any(
        a.startswith("TO_exterior") for a in _archivos(n)) and any(
        p == "3.9" or p.startswith("3.9.") for p in _puntos(n)))
    con_200 = [n for n in ext39 if "200" in _texto_nodo(n)]
    res["T1_bkl0024_ext_3_9"] = {
        "pass": bool(ext39) and bool(con_200),
        "nodos_anclados_3_9": len(ext39),
        "puntos": sorted({p for n in ext39 for p in _puntos(n)
                          if p == "3.9" or p.startswith("3.9.")}),
        "nodos_con_usd_200": [{"id": n["id"], "label": n["label"]}
                              for n in con_200][:8],
    }

    # T2 — cláusula del 125 % (caso rector anti-fusión U6-008): las variantes
    # casi idénticas del tope "125 %" de ext deben ser nodos SEPARADOS con
    # provenance separada (puntos distintos), no una fusión.
    n125 = _nodos_con(nodes, lambda n: ("125 %" in _texto_nodo(n)
                                        or "125%" in _texto_nodo(n))
                      and any(p.get("to") == "ext"
                              for p in n.get("provenances", [])))
    puntos_125 = sorted({p for n in n125 for p in _puntos(n)})
    res["T2_clausula_125"] = {
        "pass": len(n125) >= 5 and len(puntos_125) >= 4,
        "n_nodos_separados_ext": len(n125),
        "puntos_distintos": puntos_125,
        "nodos": [{"id": n["id"], "label": n["label"],
                   "puntos": sorted(_puntos(n))} for n in n125][:12],
    }

    # T3 — pro 1.1.2.5: la salvedad de mutuales/cooperativas está.
    pro1125 = _nodos_con(nodes, lambda n: any(
        a.startswith("TO_proteccion") for a in _archivos(n)) and
        "1.1.2.5" in _puntos(n))
    con_salvedad = [n for n in pro1125 if "mutual" in _texto_nodo(n)
                    or "cooperativ" in _texto_nodo(n)]
    excepciones = [n for n in con_salvedad if n.get("type") == "Excepcion"]
    res["T3_pro_1_1_2_5_salvedad"] = {
        "pass": bool(con_salvedad),
        "nodos_anclados": len(pro1125),
        "nodos_con_salvedad": [{"id": n["id"], "type": n["type"],
                                "label": n["label"]} for n in con_salvedad][:6],
        "de_los_cuales_excepcion": len(excepciones),
    }
    return res


# Suites de tests de respuesta conocida registradas: cada corpus declara la
# suya en el manifiesto (o null = sin suite). "dev5" es la del desarrollo.
SUITES = {"dev5": tests_respuesta_conocida}


def ensamblar(grafos: dict[str, dict], orden: tuple, suite: str | None,
              esqueleto_v3: Path | None = None) -> dict:
    """Cómputo puro del ensamblado final: merge + tests + reporte. Compartido
    entre main() y el selftest de paridad (que compara bytes sin escribir en
    la salida sellada).

    `esqueleto_v3` None (default) = comportamiento histórico BYTE-IDÉNTICO:
    no se importa assemble ni se toca el grafo."""
    m = merge_grafos(grafos, orden)
    kg = {"nodes": m["nodes"], "edges": m["edges"]}
    r_esq = None
    if esqueleto_v3 is not None:
        r_esq = inyectar_esqueleto_v3(kg, esqueleto_v3)
    kg_json = json.dumps(kg, ensure_ascii=False, indent=2)
    sha = hashlib.sha256(kg_json.encode("utf-8")).hexdigest()

    if suite is not None:
        tests = SUITES[suite](kg)
        tests_reporte = {k: v["pass"] for k, v in tests.items()}
    else:
        tests = None
        tests_reporte = ("sin_suite_declarada (tests_respuesta_conocida: null "
                         "en el manifiesto — los tests son por corpus)")

    reporte = {
        "orden_merge": list(orden),
        "nodes_total": len(kg["nodes"]),
        "edges_total": len(kg["edges"]),
        "nodes_by_type": dict(Counter(n["type"] for n in kg["nodes"]).most_common()),
        "por_to_pre_merge": {to: {"nodes": len(g["nodes"]),
                                  "edges": len(g["edges"])}
                             for to, g in grafos.items()},
        "merges_cross_to": m["merges_cross_to"],
        "conflictos_properties_cross_to": m["conflictos"],
        "sha256_kg": sha,
        "tests_respuesta_conocida": tests_reporte,
    }
    if r_esq is not None:
        reporte["esqueleto_v3"] = r_esq
    return {"kg_json": kg_json, "sha256_kg": sha, "tests": tests,
            "reporte": reporte}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=AQUI / "salida")
    ap.add_argument("--manifiesto", type=Path,
                    default=REX / "manifiestos" / "desarrollo_5tos.json",
                    help="manifiesto de corpus (U-B5.1); default: desarrollo")
    ap.add_argument("--esquema-v3", type=Path, default=None,
                    help="fuerza la inyección del esqueleto v3 desde esta ruta "
                         "(U-ESQ-V3); por default se decide por el perfil del manifiesto")
    args = ap.parse_args()

    man = manifiesto_corpus.cargar(args.manifiesto)
    orden = tuple(man.orden_corrida)

    # U-ESQ-V3: activación por PERFIL DECLARADO (o por --esquema-v3 explícito).
    esqueleto_v3 = args.esquema_v3
    if esqueleto_v3 is None and man.perfil_e1 == PERFIL_CON_ESQUELETO_V3:
        esqueleto_v3 = ESQUEMA_V3_DEFAULT
    if esqueleto_v3 is not None and not Path(esqueleto_v3).exists():
        print(f"FRENO: el manifiesto declara perfil_e1 '{man.perfil_e1}' pero el artefacto "
              f"del esqueleto v3 no existe: {esqueleto_v3}")
        return 1

    grafos = {}
    for to in orden:
        p = args.salida / to / f"grafo_{to}.json"
        if not p.exists():
            print(f"falta {p} — la corrida de {to} no cerró su E2")
            return 1
        grafos[to] = json.loads(p.read_text(encoding="utf-8"))

    res = ensamblar(grafos, orden, man.tests_respuesta_conocida, esqueleto_v3)
    (args.salida / "kg.json").write_text(res["kg_json"], encoding="utf-8")
    if res["tests"] is not None:
        (args.salida / "tests_respuesta_conocida.json").write_text(
            json.dumps(res["tests"], ensure_ascii=False, indent=1),
            encoding="utf-8")
    reporte = res["reporte"]
    (args.salida / "reporte_ensamblado.json").write_text(
        json.dumps(reporte, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: reporte[k] for k in
                      ("nodes_total", "edges_total", "sha256_kg",
                       "tests_respuesta_conocida")},
                     ensure_ascii=False, indent=1))
    print(f"-> {args.salida / 'kg.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
