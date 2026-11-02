#!/usr/bin/env python3
"""tools_juguete.py — Tools de juguete de U-A2.0-gate (entregable 2).

Imitan el contrato de las tools del grafo sobre el mini-grafo sintético propio
de esta unidad (`gate/grafo_juguete.json`). No tocan Neo4j, no leen ningún
`kg.json` sellado, no abren material EV2.

DOS CONTRATOS, a propósito:

  · `--contrato v1` — las tres tools del harness congelado:
        buscar_nodos(consulta, limite) / ver_nodo(id) / ver_vecinos(id, direccion)
    Implementadas por `harness.GraphIndex` sobre el mini-grafo, es decir: son
    LA MISMA función pura que el replay determinístico re-ejecuta. No es un
    atajo — es el requisito. El replay de A0.2 (`metrica._reejecutar_step`)
    re-ejecuta cada step contra un `GraphIndex`; si la tool de juguete fuera
    una reimplementación aproximada, ninguna traza replayaría jamás y el gate
    mediría el error de la imitación en vez de medir el transporte. A2.0-banco
    declara el mismo principio para el servidor MCP real ("reusa Neo4jIndex y
    las tools v2 — nada se reimplementa").

  · `--contrato v2` — el contrato de A1.2 (`agente_v2/tools_v2.py`), el que el
    laudo C11 de A1.4 dejó elegido para el banco: `ver_vecinos` cambia de firma
    (`relacion`, `pagina`, `por_pagina`) y de payload (bloques paginados).
    Acá se imita en Python puro sobre el mini-grafo — sin Neo4j — replicando el
    payload de `ToolsV2.ver_vecinos_v2` campo por campo, para poder medir si el
    driver de replay congelado sobrevive al cambio de contrato.

Salida: el payload serializado con `json.dumps(..., ensure_ascii=False)`, que
es exactamente la serialización que usa `metrica.evaluar_traza` para el replay
estándar. Una sola llamada por invocación (una tool call = un step).

Uso:
  tools_juguete.py [--contrato v1|v2] [--caso ID] buscar_nodos --consulta X [--limite N]
  tools_juguete.py [--contrato v1|v2] [--caso ID] ver_nodo --id X
  tools_juguete.py [--contrato v1] [--caso ID] ver_vecinos --id X [--direccion ambas|salientes|entrantes]
  tools_juguete.py --contrato v2 [--caso ID] ver_vecinos --id X [--relacion R] [--pagina N] [--por-pagina N]

`--caso` no altera la salida: es la marca que el adaptador usa para agrupar los
steps de una sesión en casos (ver adaptador_cc.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GATE_DIR = Path(__file__).resolve().parents[1]              # data/experiment/banco_mcp/gate
EXPERIMENT_DIR = GATE_DIR.parents[1]                        # data/experiment
EVAL_DIR = EXPERIMENT_DIR / "evaluacion"
SINTETICAS_DIR = EXPERIMENT_DIR / "exploracion" / "sinteticas"
for _p in (str(EVAL_DIR), str(SINTETICAS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from harness import GraphIndex                      # noqa: E402  (cuarteto sellado: se importa)
from loader import Edge, KnowledgeGraph, Node       # noqa: E402
from resolucion import AnclaIndex                   # noqa: E402

GRAFO_JUGUETE = GATE_DIR / "grafo_juguete.json"

# Defaults del contrato v2 (agente_v2/tools_v2.py)
LIMITE_DEFAULT = 10
POR_PAGINA_DEFAULT = 40
POR_PAGINA_MAX = 40


# --------------------------------------------------------------------------- #
# Carga del mini-grafo                                                         #
# --------------------------------------------------------------------------- #
def cargar_raw(path: Path | None = None) -> dict:
    return json.loads((path or GRAFO_JUGUETE).read_text(encoding="utf-8"))


def cargar_index(path: Path | None = None) -> GraphIndex:
    raw = cargar_raw(path)
    kg = KnowledgeGraph(
        run_key="gate_juguete", path=path or GRAFO_JUGUETE,
        nodes=[Node(n["id"], n["type"], n["label"], n["properties"], n["provenances"])
               for n in raw["nodes"]],
        edges=[Edge(e["source"], e["target"], e["relation"], e["properties"], e["provenances"])
               for e in raw["edges"]])
    return GraphIndex(kg)


def cargar_ancla_index(path: Path | None = None) -> AnclaIndex:
    return AnclaIndex(cargar_raw(path))


# --------------------------------------------------------------------------- #
# Contrato v2 imitado (payload de ToolsV2, sin Neo4j)                          #
# --------------------------------------------------------------------------- #
class ToolsJugueteV2:
    """Imitación fiel del PAYLOAD de `agente_v2.tools_v2.ToolsV2` sobre el
    mini-grafo. `buscar_nodos_v2` y `ver_nodo_v2` son adaptadores finos sobre
    el índice (igual que en v2, donde delegan en Neo4jIndex); `ver_vecinos_v2`
    replica la paginación y los bloques de conteo por relación.

    Diferencia declarada con el v2 real: allá el ranking de `buscar_nodos` es
    BM25 (índice full-text de Neo4j) y acá es el léxico del harness. El gate no
    mide calidad de retrieval: mide si el REPLAY sobrevive al cambio de FIRMA y
    de PAYLOAD de `ver_vecinos`, que es lo que rompe al driver congelado.
    """

    def __init__(self, index: GraphIndex):
        self.index = index

    def buscar_nodos(self, consulta: str, limite: int = LIMITE_DEFAULT) -> dict:
        return self.index.buscar_nodos(consulta, limite)

    def ver_nodo(self, id: str) -> dict:
        return self.index.ver_nodo(id)

    @staticmethod
    def _entero(v, default: int, minimo: int, maximo: int | None) -> int:
        try:
            x = int(v)
        except (TypeError, ValueError):
            return default
        if isinstance(v, bool):
            return default
        x = max(minimo, x)
        return min(x, maximo) if maximo is not None else x

    def ver_vecinos(self, id: str, relacion: str | None = None, pagina: int = 1,
                    por_pagina: int = POR_PAGINA_DEFAULT) -> dict:
        pagina = self._entero(pagina, 1, 1, None)
        por_pagina = self._entero(por_pagina, POR_PAGINA_DEFAULT, 1, POR_PAGINA_MAX)
        if relacion == "":
            relacion = None
        n = self.index.by_id.get(id)
        if n is None:
            return {"error": f"No existe un nodo con id '{id}'.",
                    "sugerencia": "Usá buscar_nodos para encontrar el id correcto."}
        skip = (pagina - 1) * por_pagina

        def _items(edges, campo_vecino):
            out = []
            for e in edges:
                vid = getattr(e, campo_vecino)
                vecino = self.index.by_id.get(vid)
                out.append({"relation": e.relation, "vecino_id": vid,
                            "vecino_label": vecino.label if vecino else None,
                            "provenances": e.provenances})
            return out

        def _conteos(edges):
            c = {}
            for e in edges:
                c[e.relation] = c.get(e.relation, 0) + 1
            return {k: v for k, v in sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))}

        out_edges = self.index.out_edges.get(id, [])
        in_edges = self.index.in_edges.get(id, [])
        out_rel, in_rel = _conteos(out_edges), _conteos(in_edges)
        out_all = [x for x in _items(out_edges, "target")
                   if relacion is None or x["relation"] == relacion]
        in_all = [x for x in _items(in_edges, "source")
                  if relacion is None or x["relation"] == relacion]

        def _bloque(prefijo: str, por_rel: dict, items: list) -> dict:
            total_sf = sum(por_rel.values())
            total = por_rel.get(relacion, 0) if relacion is not None else total_sf
            paginas = (total + por_pagina - 1) // por_pagina if total else 0
            return {f"{prefijo}_total": total, f"{prefijo}_paginas": paginas,
                    f"{prefijo}_pagina_siguiente": (pagina + 1) if pagina < paginas else None,
                    f"{prefijo}_por_relacion": por_rel,
                    prefijo: items[skip:skip + por_pagina]}

        res = {"id": id, "label": n.label,
               "n_salientes_total": sum(out_rel.values()),
               "n_entrantes_total": sum(in_rel.values()),
               "filtro_relacion": relacion, "pagina": pagina, "por_pagina": por_pagina}
        res.update(_bloque("salientes", out_rel, out_all))
        res.update(_bloque("entrantes", in_rel, in_all))
        return res


# --------------------------------------------------------------------------- #
# Despacho                                                                     #
# --------------------------------------------------------------------------- #
def ejecutar(contrato: str, tool: str, args: dict, index: GraphIndex) -> dict:
    """Ejecuta UNA tool call. Misma semántica que `metrica._reejecutar_step`
    para v1 (y por eso mismo replayeable), y la firma v2 para v2."""
    if contrato == "v1":
        if tool == "buscar_nodos":
            return index.buscar_nodos(args.get("consulta", ""), args.get("limite", 10))
        if tool == "ver_nodo":
            return index.ver_nodo(args.get("id", ""))
        if tool == "ver_vecinos":
            return index.ver_vecinos(args.get("id", ""), args.get("direccion", "ambas"))
        return {"error": f"tool desconocida: {tool}"}
    t2 = ToolsJugueteV2(index)
    if tool == "buscar_nodos":
        return t2.buscar_nodos(args.get("consulta", ""), args.get("limite", LIMITE_DEFAULT))
    if tool == "ver_nodo":
        return t2.ver_nodo(args.get("id", ""))
    if tool == "ver_vecinos":
        return t2.ver_vecinos(args.get("id", ""), args.get("relacion"),
                              args.get("pagina", 1), args.get("por_pagina", POR_PAGINA_DEFAULT))
    return {"error": f"tool desconocida: {tool}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Tools de juguete del gate (U-A2.0-gate)")
    ap.add_argument("--contrato", choices=("v1", "v2"), default="v1")
    ap.add_argument("--caso", default=None, help="marca de agrupamiento; no altera la salida")
    ap.add_argument("--grafo", type=Path, default=None)
    sub = ap.add_subparsers(dest="tool", required=True)

    p = sub.add_parser("buscar_nodos"); p.add_argument("--consulta", required=True); p.add_argument("--limite", type=int, default=None)
    p = sub.add_parser("ver_nodo"); p.add_argument("--id", required=True)
    p = sub.add_parser("ver_vecinos")
    p.add_argument("--id", required=True)
    p.add_argument("--direccion", default=None, help="solo v1")
    p.add_argument("--relacion", default=None, help="solo v2")
    p.add_argument("--pagina", type=int, default=None, help="solo v2")
    p.add_argument("--por-pagina", dest="por_pagina", type=int, default=None, help="solo v2")

    a = ap.parse_args()
    index = cargar_index(a.grafo)

    if a.tool == "buscar_nodos":
        args = {"consulta": a.consulta}
        if a.limite is not None:
            args["limite"] = a.limite
    elif a.tool == "ver_nodo":
        args = {"id": a.id}
    else:
        args = {"id": a.id}
        if a.contrato == "v1":
            if a.direccion is not None:
                args["direccion"] = a.direccion
        else:
            if a.relacion is not None:
                args["relacion"] = a.relacion
            if a.pagina is not None:
                args["pagina"] = a.pagina
            if a.por_pagina is not None:
                args["por_pagina"] = a.por_pagina

    print(json.dumps(ejecutar(a.contrato, a.tool, args, index), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
