"""
resolucion.py — Resolución por-grafo de anclas de provenance (censo del §4).

Dada un ancla (TO + punto normativo) y un kg.json, devuelve los nodos que la
portan: aquellos con al menos una provenance PDF cuyo location parsea a ese
punto exacto. El gold de cada pregunta viaja en anclas (invariantes entre
grafos); la métrica se computa contra los nodos resueltos LOCALMENTE en cada
grafo por este censo.

Semántica de match (decisión documentada): igualdad EXACTA de punto
normalizado ('2.7' == '2.7'; '2.7' != '2.7.1'). No se incluyen descendientes:
el ancla se extrae con el mismo parser con el que se censa, así que el nodo
que originó el ancla siempre se re-encuentra a sí mismo; incluir descendencia
inflaría el gold con nodos de otros subpuntos. Si un uso futuro necesita
descendencia, `resolver` acepta `incluir_descendientes=True` explícito.

Censo previo por grafo (§4): un ancla que resuelve a 0 nodos en un grafo es
AUSENCIA de ese grafo (dato de fidelidad) y el caso se excluye de la métrica
de navegabilidad de ese grafo — los dos ejes no se mezclan.

Filtro de CONTENEDORES (decisión documentada, medida sobre el grafo vigente):
un nodo que porta más de `contenedor_max_anclas` anclas distintas no está
anclado en ningún punto — es un contenedor (los 5 TextoOrdenado portan 18-125
anclas; las Comunicacion grandes, 12-65; el 99,6 % de los nodos porta <= 10).
Incluirlos en el censo haría trivialmente "visto" cualquier ancla de su TO en
cuanto el agente cruza el nodo contenedor en una búsqueda. Por defecto el
censo los EXCLUYE; `incluir_contenedores=True` los repone explícitamente.
"""

from __future__ import annotations

from pathlib import Path

from comun import anclas_de_nodo, load_kg_raw


CONTENEDOR_MAX_ANCLAS = 10


class AnclaIndex:
    """Índice (to, ancla) -> [ids de nodo] sobre un kg.json crudo."""

    def __init__(self, kg_raw: dict,
                 contenedor_max_anclas: int = CONTENEDOR_MAX_ANCLAS):
        self.por_ancla: dict[tuple, list] = {}
        self.sin_parsear: list[dict] = []
        self.contenedores: dict[str, int] = {}   # id -> n anclas distintas
        for n in kg_raw.get("nodes", []):
            anclas, sin_parsear = anclas_de_nodo(n)
            if len(anclas) > contenedor_max_anclas:
                self.contenedores[n["id"]] = len(anclas)
            for a in anclas:
                self.por_ancla.setdefault((a["to"], a["ancla"]), []).append(n["id"])
            for s in sin_parsear:
                self.sin_parsear.append({"node_id": n["id"], **s})

    @classmethod
    def desde_path(cls, path: Path, verificar_sha: bool = True) -> "AnclaIndex":
        return cls(load_kg_raw(Path(path), verificar_sha=verificar_sha))

    def resolver(self, to: str, ancla: str,
                 incluir_descendientes: bool = False,
                 incluir_contenedores: bool = False) -> list:
        """Ids de los nodos que portan el ancla (orden de aparición en el kg)."""
        if not incluir_descendientes:
            ids = list(self.por_ancla.get((to, ancla), []))
        else:
            ids, vistos = [], set()
            prefijo = ancla + "."
            for (t, a), nodos in self.por_ancla.items():
                if t == to and (a == ancla or a.startswith(prefijo)):
                    for nid in nodos:
                        if nid not in vistos:
                            vistos.add(nid)
                            ids.append(nid)
        if not incluir_contenedores:
            ids = [i for i in ids if i not in self.contenedores]
        return ids

    def censo(self, anclas: list[dict]) -> dict:
        """Censo de una lista de anclas [{'to','ancla'}] contra este grafo.

        -> {'resueltas': {(to,ancla)->[ids]}, 'ausentes': [(to,ancla)],
            'nodos_gold': [ids únicos en orden]}
        """
        resueltas, ausentes, nodos, vistos = {}, [], [], set()
        for a in anclas:
            key = (a["to"], a["ancla"])
            ids = self.resolver(*key)
            if ids:
                resueltas[key] = ids
                for nid in ids:
                    if nid not in vistos:
                        vistos.add(nid)
                        nodos.append(nid)
            else:
                ausentes.append(key)
        return {"resueltas": resueltas, "ausentes": ausentes,
                "nodos_gold": nodos}
