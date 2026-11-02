"""
comun_ev2.py — Infraestructura común de la corrida EV2 (issue #10, fase agente).

Protocolo vinculante: docs/protocolo_corrida_ev2.md (sellado en el manifest
data/experiment/exploracion/ev2_sellado/manifest_ev2.txt). Este módulo NO
edita ningún artefacto sellado: importa el cuarteto de evaluación
(loader/harness/judge/llm_cache) y los módulos del pipeline de sintéticas
(resolucion/comun/metrica) tal cual están en el repo.

Provee:
  - Rutas y sha256 esperados de los TRES grafos a medir (verificación
    obligatoria antes de cualquier operación).
  - Vista de CENSO por grafo: kg.json crudo con provenances COMPLETAS,
    normalizadas al shape {source_doc, location} que consume
    sinteticas.comun.anclas_de_nodo. Adaptadores documentados abajo.
  - Vista RUNTIME por grafo: el KnowledgeGraph que ven las tools del harness,
    replicando la vista establecida de cada grafo en el proyecto.
  - Carga del set sellado (solo lectura) y construcción del ORDEN de
    ejecución con la semilla declarada `orden-ev2-v1`.

Adaptadores de provenance (decisión de esta unidad, documentada):
  - v2 (reextraccion_v2/corpus_v2/salida/kg.json): sus provenances vienen como
    {to, archivo, punto, rol_documental}. Se mapean en memoria a
    {source_doc: archivo, location: "Punto <punto>" | "Sección <N>"} — el
    mismo shape y formato de location que produce el pipeline v3, de modo que
    el parser de anclas del censo (sinteticas.comun.parse_ancla) hace el
    round-trip identidad: punto '6.11' -> location 'Punto 6.11' -> ancla
    '6.11'; punto 'S14' -> location 'Sección 14' -> ancla 'S14'. El kg.json
    NO se toca: la transformación es en memoria.
  - v3 (grafo_v2/reensamblado_v3/kg.json): crudo tal cual (ya trae la clave
    `provenances` completa en shape {source_doc, location}).
  - run_3 (run_3_ppf_core/kg.json): el crudo no tiene clave `provenances`;
    se pliega [provenance] + additional_provenance (adaptador del loader
    congelado para run_3, replicado sobre el crudo para el censo).

Vistas RUNTIME (qué grafo ve el agente):
  - run_3: loader.load_graph("run_3") — exactamente la vista de la medición
    congelada de Fase 2.3.
  - v3: loader.load_graph_from_path(path, adapter_key=None) — el patrón
    run_escalon1b / posthoc sobre reensamblado_v3 (provenance primaria).
  - v2: análogo del adaptador nulo: provenance PRIMARIA transformada al shape
    {source_doc, location} (sin la transformación el loader nulo descartaría
    todas las provenances de v2 y el agente no podría citar). Construida con
    las mismas dataclasses y merge del loader congelado.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

EV2_DIR = Path(__file__).resolve().parents[1]          # data/experiment/ev2_corrida
EXPERIMENT_DIR = EV2_DIR.parent                        # data/experiment
REPO_DIR = EXPERIMENT_DIR.parents[1]
EVAL_DIR = EXPERIMENT_DIR / "evaluacion"
SINTETICAS_DIR = EXPERIMENT_DIR / "exploracion" / "sinteticas"

for _p in (str(EVAL_DIR), str(SINTETICAS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Cuarteto congelado (se importa, jamás se edita) + módulos de sintéticas.
from loader import (  # noqa: E402
    Node, Edge, KnowledgeGraph, load_graph, load_graph_from_path,
    _merge_nodes,
)
from resolucion import AnclaIndex  # noqa: E402

# --------------------------------------------------------------------------- #
# Grafos a medir — rutas y sha256 esperados (protocolo §2 + mandato)          #
# --------------------------------------------------------------------------- #
GRAFOS = {
    "v2": {
        "path": EXPERIMENT_DIR / "reextraccion_v2" / "corpus_v2" / "salida" / "kg.json",
        "sha256": "8e2eadee57b48e00ccb51ade9a953ba1469001fe089c45d97c4307ccf2725581",
        "label": "ev2_base_v2",
    },
    "v3": {
        "path": EXPERIMENT_DIR / "grafo_v2" / "reensamblado_v3" / "kg.json",
        "sha256": "26fac8b49f6c08c1aa364b47273d36958d831f240d4e6b4ee7700b6a0bff3571",
        "label": "ev2_base_v3",
    },
    "run_3": {
        "path": EXPERIMENT_DIR / "run_3_ppf_core" / "kg.json",
        "sha256": "12c226e22b8fdc8f46999cae7f1eb808930e71f5dfe803f3a4f637a88348c410",
        "label": "ev2_base_run3",
    },
}
GRAFO_KEYS = list(GRAFOS.keys())

# Set sellado (SOLO LECTURA)
FIDELIDAD_JSON = (EXPERIMENT_DIR / "exploracion" / "ev2_fidelidad"
                  / "preguntas_ev2_fidelidad.json")
FASEB_JSON = SINTETICAS_DIR / "out" / "preguntas_faseB.json"

SEMILLA_ORDEN = "orden-ev2-v1"


def rel_repo(path: Path | str) -> str:
    """Ruta relativa a la raíz del repo, para PERSISTIR en artefactos (las
    rutas absolutas incluyen el home del usuario y no viajan entre máquinas)."""
    return str(Path(path).resolve().relative_to(REPO_DIR))


def sha256_de(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verificar_grafos(verbose: bool = True) -> dict:
    """Verifica el sha256 de los tres grafos. Aborta si alguno no coincide."""
    out = {}
    for k, g in GRAFOS.items():
        got = sha256_de(g["path"])
        if got != g["sha256"]:
            raise RuntimeError(
                f"SHA256 INESPERADO para {k} ({g['path']}): {got} != {g['sha256']}. "
                "FRENAR: no correr nada sobre un grafo no verificado.")
        out[k] = got
        if verbose:
            print(f"  sha256 OK  {k}: {got}  {g['path'].relative_to(REPO_DIR)}")
    return out


# --------------------------------------------------------------------------- #
# Vistas de CENSO (crudo, provenances completas, shape uniforme)              #
# --------------------------------------------------------------------------- #
def _map_prov_v2(p: dict) -> dict | None:
    """{to, archivo, punto, rol_documental} -> {source_doc, location}."""
    if not isinstance(p, dict):
        return None
    punto = (p.get("punto") or "").strip()
    if not punto:
        return None
    if punto.startswith("S") and punto[1:].isdigit():
        location = f"Sección {punto[1:]}"
    else:
        location = f"Punto {punto}"
    return {"source_doc": p.get("archivo"), "location": location}


def cargar_censo_raw(grafo: str) -> dict:
    """kg.json crudo con `provenances` completas en shape {source_doc, location}."""
    path = GRAFOS[grafo]["path"]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if grafo == "v3":
        return data
    nodes = []
    for n in data.get("nodes", []):
        n = dict(n)
        if grafo == "v2":
            provs = [_map_prov_v2(p) for p in (n.get("provenances") or
                                               ([n.get("provenance")] if n.get("provenance") else []))]
            n["provenances"] = [p for p in provs if p]
        elif grafo == "run_3":
            provs = ([n.get("provenance")] if n.get("provenance") else []) \
                    + list(n.get("additional_provenance") or [])
            n["provenances"] = provs
        nodes.append(n)
    return {"nodes": nodes, "edges": data.get("edges", [])}


def indice_anclas(grafo: str) -> AnclaIndex:
    """AnclaIndex (resolucion.py, regla sellada: match exacto de punto,
    contenedores >10 anclas excluidos) sobre la vista de censo del grafo."""
    return AnclaIndex(cargar_censo_raw(grafo))


# --------------------------------------------------------------------------- #
# Vistas RUNTIME (lo que ven las tools del harness)                           #
# --------------------------------------------------------------------------- #
def cargar_runtime(grafo: str) -> KnowledgeGraph:
    if grafo == "run_3":
        return load_graph("run_3")
    if grafo == "v3":
        return load_graph_from_path(GRAFOS["v3"]["path"], adapter_key=None)
    if grafo == "v2":
        return _cargar_runtime_v2()
    raise KeyError(f"grafo desconocido: {grafo!r}")


def _cargar_runtime_v2() -> KnowledgeGraph:
    """Vista runtime de v2: provenance PRIMARIA mapeada a {source_doc, location},
    construida con las dataclasses y el merge del loader congelado (idéntico
    comportamiento que load_graph_from_path con adaptador nulo, salvo el mapeo
    de shape sin el cual v2 quedaría sin provenances)."""
    path = GRAFOS["v2"]["path"]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    raw_nodes = []
    for n in data.get("nodes", []):
        p = _map_prov_v2(n.get("provenance") or {})
        raw_nodes.append(Node(
            id=n.get("id"), type=n.get("type"), label=n.get("label"),
            properties=dict(n.get("properties") or {}),
            provenances=[p] if p else [],
        ))
    nodes, merges = _merge_nodes(raw_nodes)
    edges = []
    for e in data.get("edges", []):
        p = _map_prov_v2(e.get("provenance") or {})
        edges.append(Edge(
            source=e.get("source"), target=e.get("target"),
            relation=e.get("relation"),
            properties=dict(e.get("properties") or {}),
            provenances=[p] if p else [],
        ))
    return KnowledgeGraph(
        run_key="corpus_v2", path=path, nodes=nodes, edges=edges,
        raw_node_count=len(data.get("nodes", [])),
        raw_edge_count=len(data.get("edges", [])),
        merges=merges,
    )


# --------------------------------------------------------------------------- #
# Set sellado (solo lectura) + orden de ejecución                             #
# --------------------------------------------------------------------------- #
def cargar_fidelidad() -> list[dict]:
    """40 preguntas del eje de fidelidad, tal cual el JSON sellado."""
    with open(FIDELIDAD_JSON, encoding="utf-8") as f:
        return json.load(f)["preguntas"]


def cargar_aptos() -> list[dict]:
    """64 registros aptos del eje de navegabilidad, tal cual el JSON sellado."""
    with open(FASEB_JSON, encoding="utf-8") as f:
        b = json.load(f)
    return [r for r in b["registros"] if r["veredicto"] == "apto"]


def construir_casos() -> list[dict]:
    """Lista COMPLETA de casos de la corrida (ambos ejes, antes de descontar
    ausencias): 40 fidelidad + 64×2 navegabilidad = 168.

    id de caso:  fidelidad -> el id sellado (EV2F-nnn)
                 navegabilidad -> "<sample_id>::literal" | "<sample_id>::antilexica"
    """
    casos = []
    for p in cargar_fidelidad():
        casos.append({"caso_id": p["id"], "eje": "fidelidad",
                      "pregunta": p["pregunta"]})
    for r in cargar_aptos():
        for variante in ("literal", "antilexica"):
            casos.append({"caso_id": f"{r['sample_id']}::{variante}",
                          "eje": "navegabilidad",
                          "sample_id": r["sample_id"],
                          "variante": variante,
                          "estrato": r["estrato"],
                          "pregunta": r[variante]})
    return casos


def orden_resuelto() -> list[dict]:
    """Orden de ejecución del protocolo §5: lista de casos ordenada por id,
    luego random.Random('orden-ev2-v1').shuffle. Idéntico en los tres grafos;
    las ausencias por grafo se SALTEAN sin re-barajar (el orden relativo de
    los casos presentes se conserva)."""
    casos = sorted(construir_casos(), key=lambda c: c["caso_id"])
    random.Random(SEMILLA_ORDEN).shuffle(casos)
    return casos
