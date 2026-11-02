"""
comun_tanda0.py — U-TANDA0-2A (instrumento 9 del pre-registro, enmienda
a551c57 §2.2): registro EN MEMORIA de los grafos r1 de la tanda 0 en el
circuito sellado de EV2, con el patrón de ev2_r1/code/comun_r1.py:106-158.
Ningún módulo sellado se edita en disco.

Qué hace al importarse (idempotente):
  - agrega a comun_ev2.GRAFOS (el mismo dict que ven runner_ev2 y
    verificar_grafos) una entrada por grafo de la tanda 0, con path, sha256 y
    el label de corrida EV2 de su celda (C3: ev2_c3_dev_mem; C5:
    ev2_c5_diez_mem);
  - reemplaza en memoria el despachador de vista runtime
    (comun_ev2.cargar_runtime y la referencia importada runner_ev2.cargar_runtime)
    por uno que atiende las claves de la tanda 0 y DELEGA todas las demás en
    el despachador que estuviera vigente al importarse (el original o el de
    comun_r1: el orden de import entre ambos módulos no altera el resultado).

Vista runtime de un grafo de generación 3 (idéntica a la de r1, comun_r1.
_cargar_runtime_r1, y a la v2 de la corrida base, comun_ev2._cargar_runtime_v2):
provenance PRIMARIA {to, archivo, punto, ...} mapeada a {source_doc, location}
con comun_ev2._map_prov_v2, dataclasses y merge del loader congelado. El
kg.json no se toca.

Uso desde el registro de Neo4j (data/experiment/neo4j/grafos.py): las
entradas KG_Tanda0_* declaran como `ev2_key` la clave de este módulo y
`requiere_registro_modulo = "comun_tanda0"`. grafos.cargar_vista_runtime
importa este módulo cuando la entrada declara ese campo (por defecto importa
comun_r1) y recién después resuelve la vista, así que no hace falta
importarlo a mano.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent            # data/experiment/tanda0/code
EXP_DIR = CODE_DIR.parents[1]                         # data/experiment
REPO_DIR = EXP_DIR.parents[1]
CORRIDA_CODE = EXP_DIR / "ev2_corrida" / "code"
EVAL_DIR = EXP_DIR / "evaluacion"

for _p in (str(CORRIDA_CODE), str(EVAL_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import comun_ev2 as ce                                 # noqa: E402  (corrida base, sin editar)
import runner_ev2 as rv                                # noqa: E402  (runner base, sin editar)
from loader import Edge, KnowledgeGraph, Node, _merge_nodes  # noqa: E402  (cuarteto, solo import)

ENS_DIR = EXP_DIR / "reextraccion_v2" / "corpus_tanda0"

# Grafos de la tanda 0 servidos por EV2 en memoria. sha256 = el de los
# r1/kg.json commiteados en 1b8916c (E3.a).
TANDA0 = {
    "tanda0_ens_desarrollo": {
        "path": ENS_DIR / "ens_desarrollo" / "r1" / "kg.json",
        "sha256": "eab2fdd01dec4dad026d596a793919e666920fab127d7efb14b5b00857ae64ef",
        "label": "ev2_c3_dev_mem",
    },
    "tanda0_ens_diez": {
        "path": ENS_DIR / "ens_diez" / "r1" / "kg.json",
        "sha256": "dd42d6d9c0c8379da90ec4ed4e4659157a960a0d1ceaf8af5a008bdd9cad9010",
        "label": "ev2_c5_diez_mem",
    },
}


def cargar_runtime_gen3(clave: str) -> KnowledgeGraph:
    """Vista runtime de un grafo de generación 3 de la tanda 0 (patrón exacto
    de comun_r1._cargar_runtime_r1, parametrizado por clave)."""
    g = TANDA0[clave]
    path = g["path"]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    raw_nodes = []
    for n in data.get("nodes", []):
        p = ce._map_prov_v2(n.get("provenance") or {})
        raw_nodes.append(Node(
            id=n.get("id"), type=n.get("type"), label=n.get("label"),
            properties=dict(n.get("properties") or {}),
            provenances=[p] if p else [],
        ))
    nodes, merges = _merge_nodes(raw_nodes)
    edges = []
    for e in data.get("edges", []):
        p = ce._map_prov_v2(e.get("provenance") or {})
        edges.append(Edge(
            source=e.get("source"), target=e.get("target"),
            relation=e.get("relation"),
            properties=dict(e.get("properties") or {}),
            provenances=[p] if p else [],
        ))
    return KnowledgeGraph(
        run_key=clave, path=path, nodes=nodes, edges=edges,
        raw_node_count=len(data.get("nodes", [])),
        raw_edge_count=len(data.get("edges", [])),
        merges=merges,
    )


_DESPACHADOR_PREVIO = None


def _cargar_runtime_ext(grafo: str) -> KnowledgeGraph:
    if grafo in TANDA0:
        return cargar_runtime_gen3(grafo)
    return _DESPACHADOR_PREVIO(grafo)


def registrar_tanda0() -> None:
    """Registro EN MEMORIA (idempotente): entradas en comun_ev2.GRAFOS y
    despachador de runtime en comun_ev2 y en la referencia de runner_ev2."""
    global _DESPACHADOR_PREVIO
    for clave, g in TANDA0.items():
        ce.GRAFOS[clave] = g
    if ce.cargar_runtime is not _cargar_runtime_ext:
        _DESPACHADOR_PREVIO = ce.cargar_runtime
        ce.cargar_runtime = _cargar_runtime_ext
    rv.cargar_runtime = _cargar_runtime_ext


registrar_tanda0()
