"""
agente_neo4j.py — Inyección del backend Neo4j en el agente del harness POR
SUBCLASE (U-A1.1). GraphAgent / GraphIndex del cuarteto hasheado NO se editan:
se importan y se especializan.

GraphAgent construye su índice en __init__ (`self.index = GraphIndex(kg)`) y
despacha las tools en `_run_tool` contra `self.index`. La subclase reemplaza
`self.index` por un `Neo4jIndex` (grafo + modo declarados) DESPUÉS de llamar
al __init__ original, sin tocar `ask` ni el resto del loop (prompt del
sistema, TOOLS, MODEL, límite de tool calls, truncado de trazas, colección de
provenances vistas: todo idéntico).

Detalle: el __init__ original exige un KnowledgeGraph para armar el índice
in-memory. Para que el agente Neo4j NO cargue el kg.json ni tenga un índice
in-memory paralelo (sería una segunda fuente de verdad silenciosa), se le pasa
un KnowledgeGraph VACÍO; el GraphIndex resultante queda vacío y es
inmediatamente reemplazado. `self.kg` queda con ese grafo vacío — ningún
método de GraphAgent lo usa fuera del __init__ (verificado en harness.py).

Sin API en A1.1: la clase se define y se prueba solo su despacho de tools
(test_equivalencia.py, sección "subclase"), con un cliente dummy. Correr el
agente real contra Neo4j (con costo) es materia de unidades posteriores, y
requerirá declarar el namespace de caché correspondiente (llm-capture).

Uso
---
  from agente_neo4j import GraphAgentNeo4j
  from neo4j_index import Neo4jIndex
  from conexion import abrir_driver
  idx = Neo4jIndex(abrir_driver(), grafo="KG_Refinado", modo="paridad")
  agente = GraphAgentNeo4j(idx)            # client=None -> anthropic.Anthropic()
  # agente.ask(qid, pregunta)  -> igual que GraphAgent (paga API)
"""

from __future__ import annotations

import sys
from pathlib import Path

NEO4J_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(NEO4J_DIR))

from grafos import GRAFOS  # noqa: E402  (agrega EVAL_DIR al path)
from harness import GraphAgent  # noqa: E402  (solo IMPORT del cuarteto)
from loader import KnowledgeGraph  # noqa: E402
from neo4j_index import Neo4jIndex  # noqa: E402


def _kg_vacio(grafo: str) -> KnowledgeGraph:
    g = GRAFOS[grafo]
    return KnowledgeGraph(run_key=f"neo4j:{grafo}", path=g["path"],
                          nodes=[], edges=[], raw_node_count=0, raw_edge_count=0,
                          merges=[])


class GraphAgentNeo4j(GraphAgent):
    """GraphAgent del harness cuyas tools resuelven contra Neo4j."""

    def __init__(self, indice: Neo4jIndex, client=None, cache_conversation=False):
        if not isinstance(indice, Neo4jIndex):
            raise TypeError("indice debe ser un Neo4jIndex")
        super().__init__(_kg_vacio(indice.grafo), client=client,
                         cache_conversation=cache_conversation)
        # Inyección: el único punto de contacto con el harness.
        self.index = indice

    @property
    def backend(self) -> dict:
        """Metadatos del backend inyectado (para trazas / reportes)."""
        g = GRAFOS[self.index.grafo]
        return {"backend": "neo4j", "grafo": self.index.grafo,
                "nombre_canonico": g["nombre_canonico"], "kg_sha256": g["sha256"],
                "modo": self.index.modo, "indice_fulltext": self.index.indice}
