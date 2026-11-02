"""
loader.py — Adaptador uniforme de los 5 kg.json de la Fase 2.2 (BCRA KG).

Carga cualquiera de los 5 grafos congelados (read-only) y devuelve un modelo
en memoria COMÚN, normalizando las desviaciones de schema documentadas en
`data/experiment/evaluacion/00_inventario.md` §2.2.

Modelo normalizado
------------------
  Node:  id (str), type (str), label (str),
         properties (dict),            # atributos semánticos, sin las claves de provenance
         provenances (list[dict])      # [{"source_doc", "location"}, ...]  (>=1, deduplicada)
  Edge:  source (str), target (str), relation (str),
         properties (dict),
         provenances (list[dict])

Cada provenance se normaliza a SÓLO `source_doc` + `location` (decisión 4 de la
Fase 2.3: provenance uniforme, sin resolución a chunk → se descarta `chunk_id`).

Decisiones aplicadas
--------------------
  (1) Los kg.json NO se modifican. Toda normalización es en memoria.
  (2) Run 5: nodos con id idéntico se mergean (unión de properties + provenances).
      Cada merge queda registrado en `kg.merges` y se vuelca a
      `evaluacion/logs/run5_merges.json` vía `dump_merge_log()`.
  (4) Provenance uniforme source_doc + location (sin chunk_id).

Adaptadores por run (§2.2) — de dónde sale la provenance múltiple
----------------------------------------------------------------
  run_1: nodos/edges -> properties.other_locations
  run_2: nodos -> properties.additional_provenances ; edges -> additional_provenances (top-level)
  run_3: nodos -> additional_provenance (top-level)  ; edges -> (ninguna)
  run_4: nodos -> properties.all_provenances (incluye la primaria; se deduplica)
  run_5: (ninguna provenance múltiple) + política de merge por id

Uso
---
  from loader import load_graph, RUN_KEYS, dump_merge_log
  kg = load_graph("run_5")          # KnowledgeGraph
  print(len(kg.nodes), len(kg.edges), kg.merges)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- #
# Rutas (el loader vive en data/experiment/evaluacion/)                        #
# --------------------------------------------------------------------------- #
EVAL_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = EVAL_DIR.parent
LOGS_DIR = EVAL_DIR / "logs"

RUN_FILES = {
    "run_1": EXPERIMENT_DIR / "run_1_cookbook" / "kg.json",
    "run_2": EXPERIMENT_DIR / "run_2_papers" / "kg.json",
    "run_3": EXPERIMENT_DIR / "run_3_ppf_core" / "kg.json",
    "run_4": EXPERIMENT_DIR / "run_4_schema_light" / "kg.json",
    "run_5": EXPERIMENT_DIR / "run_5_hybrid" / "kg.json",
}
RUN_KEYS = list(RUN_FILES.keys())

# Config de adaptador por run. `extra_*` indica dónde vive la lista de
# provenances adicionales: ("properties", clave) o ("top", clave); None = no hay.
ADAPTERS = {
    "run_1": {"node_extra": ("properties", "other_locations"),
              "edge_extra": ("properties", "other_locations")},
    "run_2": {"node_extra": ("properties", "additional_provenances"),
              "edge_extra": ("top", "additional_provenances")},
    "run_3": {"node_extra": ("top", "additional_provenance"),
              "edge_extra": None},
    "run_4": {"node_extra": ("properties", "all_provenances"),
              "edge_extra": None},
    "run_5": {"node_extra": None,
              "edge_extra": None},
}


# --------------------------------------------------------------------------- #
# Modelo en memoria                                                            #
# --------------------------------------------------------------------------- #
@dataclass
class Node:
    id: str
    type: str
    label: str
    properties: dict
    provenances: list  # list[dict] con claves source_doc, location


@dataclass
class Edge:
    source: str
    target: str
    relation: str
    properties: dict
    provenances: list


@dataclass
class KnowledgeGraph:
    run_key: str
    path: Path
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    # Estadísticas crudas (pre-normalización) para validación cruzada:
    raw_node_count: int = 0
    raw_edge_count: int = 0
    # Registros de merge (decisión 2). Vacío en runs sin duplicados.
    merges: list = field(default_factory=list)

    @property
    def merged_instances(self) -> int:
        """Cantidad de instancias de nodo absorbidas por merges (raw - final)."""
        return sum(m["n_merged"] - 1 for m in self.merges)

    @property
    def total_node_provenances(self) -> int:
        return sum(len(n.provenances) for n in self.nodes)

    @property
    def total_edge_provenances(self) -> int:
        return sum(len(e.provenances) for e in self.edges)


# --------------------------------------------------------------------------- #
# Normalización de provenance                                                  #
# --------------------------------------------------------------------------- #
def _norm_prov(p) -> Optional[dict]:
    """Reduce una entrada de provenance a {source_doc, location} (decisión 4)."""
    if not isinstance(p, dict):
        return None
    sd = p.get("source_doc")
    loc = p.get("location")
    if sd is None and loc is None:
        return None
    return {"source_doc": sd, "location": loc}


def _collect_provenances(item: dict, extra_path) -> list:
    """Primaria (`provenance`) + lista adicional del adaptador, deduplicada por
    (source_doc, location), preservando orden de aparición."""
    provs, seen = [], set()

    def add(p):
        np = _norm_prov(p)
        if np is None:
            return
        key = (np["source_doc"], np["location"])
        if key in seen:
            return
        seen.add(key)
        provs.append(np)

    add(item.get("provenance"))
    if extra_path:
        where, key = extra_path
        container = item if where == "top" else (item.get("properties") or {})
        extra = container.get(key)
        if isinstance(extra, list):
            for p in extra:
                add(p)
    return provs


def _clean_properties(item: dict, extra_path) -> dict:
    """Copia de properties sin la clave de provenance ya plegada en provenances."""
    props = dict(item.get("properties") or {})
    if extra_path and extra_path[0] == "properties":
        props.pop(extra_path[1], None)
    return props


# --------------------------------------------------------------------------- #
# Merge de nodos con id idéntico (decisión 2 — relevante para Run 5)           #
# --------------------------------------------------------------------------- #
def _merge_nodes(raw_nodes: list):
    """Agrupa por id; funde grupos >1 en un solo Node (unión de properties +
    provenances). Devuelve (nodes, merge_records).

    Política de conflicto: se conserva el valor de la PRIMERA instancia para
    type, label y para cada clave de property; las variantes se registran.
    El merge es genérico (no-op si todos los id son únicos, p. ej. runs 1-4)."""
    order, groups = [], {}
    for n in raw_nodes:
        if n.id not in groups:
            groups[n.id] = []
            order.append(n.id)
        groups[n.id].append(n)

    nodes, merges = [], []
    for nid in order:
        grp = groups[nid]
        if len(grp) == 1:
            nodes.append(grp[0])
            continue

        # --- fusionar ---
        canon = grp[0]
        merged_props = dict(canon.properties)
        prop_conflicts = {}            # clave -> [valores variantes descartados]
        for other in grp[1:]:
            for k, v in other.properties.items():
                if k not in merged_props:
                    merged_props[k] = v
                elif _jeq(merged_props[k], v):
                    pass
                else:
                    prop_conflicts.setdefault(k, []).append(v)

        # provenances: unión deduplicada por (source_doc, location)
        merged_provs, seen = [], set()
        for node in grp:
            for p in node.provenances:
                key = (p["source_doc"], p["location"])
                if key not in seen:
                    seen.add(key)
                    merged_provs.append(p)

        types = [g.type for g in grp]
        labels = [g.label for g in grp]
        merged = Node(id=nid, type=canon.type, label=canon.label,
                      properties=merged_props, provenances=merged_provs)
        nodes.append(merged)

        merges.append({
            "id": nid,
            "n_merged": len(grp),
            "type_kept": canon.type,
            "type_variants": sorted(set(types)) if len(set(types)) > 1 else [],
            "label_kept": canon.label,
            "label_variants": sorted(set(labels)) if len(set(labels)) > 1 else [],
            "property_conflicts": sorted(prop_conflicts.keys()),
            "provenances_after_merge": len(merged_provs),
        })
    return nodes, merges


def _jeq(a, b) -> bool:
    """Igualdad estructural estable para valores de property."""
    return json.dumps(a, ensure_ascii=False, sort_keys=True) == \
           json.dumps(b, ensure_ascii=False, sort_keys=True)


# --------------------------------------------------------------------------- #
# API pública                                                                  #
# --------------------------------------------------------------------------- #
def load_graph(run_key: str) -> KnowledgeGraph:
    """Carga y normaliza el kg.json del run indicado ('run_1'..'run_5')."""
    if run_key not in RUN_FILES:
        raise KeyError(f"run desconocido: {run_key!r}. Válidos: {RUN_KEYS}")
    path = RUN_FILES[run_key]
    adapter = ADAPTERS[run_key]

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    raw_nodes_json = data.get("nodes", [])
    raw_edges_json = data.get("edges", [])

    # --- nodos crudos normalizados (antes de merge) ---
    raw_nodes = [
        Node(
            id=n.get("id"),
            type=n.get("type"),
            label=n.get("label"),
            properties=_clean_properties(n, adapter["node_extra"]),
            provenances=_collect_provenances(n, adapter["node_extra"]),
        )
        for n in raw_nodes_json
    ]
    nodes, merges = _merge_nodes(raw_nodes)

    edges = [
        Edge(
            source=e.get("source"),
            target=e.get("target"),
            relation=e.get("relation"),
            properties=_clean_properties(e, adapter["edge_extra"]),
            provenances=_collect_provenances(e, adapter["edge_extra"]),
        )
        for e in raw_edges_json
    ]

    return KnowledgeGraph(
        run_key=run_key,
        path=path,
        nodes=nodes,
        edges=edges,
        raw_node_count=len(raw_nodes_json),
        raw_edge_count=len(raw_edges_json),
        merges=merges,
    )


def dump_merge_log(kg: KnowledgeGraph, out_path: Optional[Path] = None) -> Path:
    """Vuelca los registros de merge a JSON. Por defecto a
    evaluacion/logs/<run_key>_merges.json (Run 5 -> run5_merges.json)."""
    if out_path is None:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        # run_5 -> run5_merges.json (nombre pedido en la decisión 2)
        fname = kg.run_key.replace("_", "") + "_merges.json"
        out_path = LOGS_DIR / fname
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_key": kg.run_key,
        "source_kg": str(kg.path),
        "raw_node_count": kg.raw_node_count,
        "final_node_count": len(kg.nodes),
        "groups_merged": len(kg.merges),
        "instances_absorbed": kg.merged_instances,
        "merges": kg.merges,
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out_path


def load_graph_from_path(path, adapter_key=None) -> KnowledgeGraph:
    """Carga un kg.json por ruta arbitraria (uso: app/); adapter_key declara el schema de provenance si se conoce (None = adaptador nulo)."""
    if adapter_key is None:
        adapter = {"node_extra": None, "edge_extra": None}
    elif adapter_key in ADAPTERS:
        adapter = ADAPTERS[adapter_key]
    else:
        raise KeyError(
            f"adapter_key desconocido: {adapter_key!r}. "
            f"Válidos: {sorted(ADAPTERS)} o None (adaptador nulo)."
        )

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo kg.json: {path}")
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido en {path}: {e}") from e

    raw_nodes_json = data.get("nodes", [])
    raw_edges_json = data.get("edges", [])

    raw_nodes = [
        Node(
            id=n.get("id"),
            type=n.get("type"),
            label=n.get("label"),
            properties=_clean_properties(n, adapter["node_extra"]),
            provenances=_collect_provenances(n, adapter["node_extra"]),
        )
        for n in raw_nodes_json
    ]
    nodes, merges = _merge_nodes(raw_nodes)

    edges = [
        Edge(
            source=e.get("source"),
            target=e.get("target"),
            relation=e.get("relation"),
            properties=_clean_properties(e, adapter["edge_extra"]),
            provenances=_collect_provenances(e, adapter["edge_extra"]),
        )
        for e in raw_edges_json
    ]

    return KnowledgeGraph(
        run_key=path.resolve().parent.name,
        path=path,
        nodes=nodes,
        edges=edges,
        raw_node_count=len(raw_nodes_json),
        raw_edge_count=len(raw_edges_json),
        merges=merges,
    )


if __name__ == "__main__":
    for rk in RUN_KEYS:
        g = load_graph(rk)
        line = (f"{rk}: nodes={len(g.nodes)} (raw {g.raw_node_count}) "
                f"edges={len(g.edges)} merges={len(g.merges)} "
                f"node_provs={g.total_node_provenances} "
                f"edge_provs={g.total_edge_provenances}")
        print(line)
        if g.merges:
            p = dump_merge_log(g)
            print(f"   merge log -> {p}")
