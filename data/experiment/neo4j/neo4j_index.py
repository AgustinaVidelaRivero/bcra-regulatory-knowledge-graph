"""
neo4j_index.py — Adaptador de las 3 tools del agente contra Neo4j, con DOS
modos declarados y un grafo seleccionado por label (U-A1.1).

Expone la MISMA interfaz que `GraphIndex` del harness (buscar_nodos /
ver_nodo / ver_vecinos, mismas firmas y mismos formatos de retorno), pero
resolviendo contra el grafo cargado en Neo4j por cargar_kg.py. El cuarteto
hasheado (loader/harness/judge/llm_cache) NO se edita: los helpers léxicos
`_tokens` y `_short_props` se IMPORTAN del harness. La inyección en el
agente es por subclase (agente_neo4j.GraphAgentNeo4j), no por edición.

Modos
-----
  modo='paridad'  (default) — buscar_nodos reproduce el índice léxico del
      harness sobre datos servidos por Neo4j:
        · la consulta se tokeniza con `_tokens` importado;
        · Neo4j devuelve TODOS los nodos del grafo con al menos un token en
          común (`any(t IN n.tokens WHERE t IN $q)`; `n.tokens` fue calculado
          en la carga como `sorted(set(_tokens(label) + _tokens(id)))`, con la
          misma función importada) junto con sus tokens;
        · el score `len(q ∩ tokens)`, el orden `(-score, len(label), id)`,
          el recorte de `limite` (1..50, default 10 si no es entero) y el
          payload se calculan en Python con las MISMAS expresiones que
          GraphIndex.buscar_nodos (no se delega el orden a la collation de
          Neo4j: la paridad byte-a-byte no depende de cómo compara strings el
          servidor);
        · `resumen_propiedades` = `_short_props(json.loads(props_json))`
          importado, sobre el props_json que preserva el orden del loader;
        · `total_con_match` = cantidad de nodos con score > 0 (idéntico a
          `len(scored)` del harness).
      Paridad byte-idéntica exigida en las tres tools (test_equivalencia.py).
  modo='fulltext' — buscar_nodos usa el índice Lucene por grafo
      (indices.py: label + descripcion + description + id_texto, analyzer
      spanish, BM25). Divergencia DELIBERADA en buscar_nodos (es la mejora
      que motiva la migración; NO dispara freno). Comportamiento REAL leído
      del índice (verificado en test_equivalencia.py, sección fulltext):
        · la consulta se tokeniza con `_tokens` y se une con espacios ⇒ query
          Lucene con semántica OR entre términos (neutraliza la sintaxis
          reservada de Lucene y replica la tolerancia del in-memory);
        · `db.index.fulltext.queryNodes` sin opción `limit` devuelve TODOS
          los hits ⇒ `total_con_match` = cantidad de nodos con al menos un
          término de la consulta (tras analyzer: stemming + stopwords) en
          alguno de los cuatro campos indexados. Consecuencias medidas: una
          consulta hecha SOLO de stopwords castellanas ("de la", "que se")
          da total 0 en full-text y miles en el in-memory; una consulta con
          términos que solo viven en la descripcion da total > 0 en full-text
          y 0 en el in-memory;
        · ranking: score de Lucene desc, desempate por largo de label y id
          (mismos desempates que el in-memory) — el score NO se expone;
        · `tokens_matcheados` se calcula con la fórmula del harness sobre
          label+id: puede valer 0 para hits que Lucene encontró vía
          descripcion — señal honesta de que ese nodo era inalcanzable con
          el índice viejo;
        · el id es buscable vía `id_texto` (ver indices.py; decisión y
          alternativa descartada documentadas allí).
  ver_nodo / ver_vecinos: IDÉNTICOS en ambos modos (Cypher por id con la
      constraint de unicidad por label de grafo; provenances/properties
      reconstruidas desde props_json/provenances_json; ver_vecinos ordena por
      `r.orden` = posición de la arista en kg.edges). Paridad byte-idéntica
      exigida en ambos modos.

Punto de extensión declarado (NO implementado en A1.1 — corresponde a A1.2):
  modo='bm25_agente' — BM25 como retriever del agente con tools v2 (firma /
  payload distintos, p. ej. exponer score, paginación o filtro de relación en
  ver_vecinos). Hoy lanza NotImplementedError con ese mensaje; cuando se
  implemente, requiere su propia definición de TOOLS y namespace de caché.

Uso
---
  from neo4j_index import Neo4jIndex
  from conexion import abrir_driver
  idx = Neo4jIndex(abrir_driver(), grafo="KG_Refinado", modo="paridad")
  idx.buscar_nodos("asociación mutual")
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

NEO4J_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(NEO4J_DIR))

from grafos import GRAFOS, GRAFO_DEFAULT  # noqa: E402  (agrega EVAL_DIR al path)
# Solo IMPORT del cuarteto hasheado (no se edita): helpers léxicos idénticos.
from harness import _tokens, _short_props  # noqa: E402

MODOS = ("paridad", "fulltext")
MODOS_FUTUROS = {"bm25_agente": "A1.2: BM25 como retriever del agente + tools v2"}


class Neo4jIndex:
    """Las 3 tools del agente resueltas contra Neo4j (misma interfaz que GraphIndex)."""

    def __init__(self, driver, grafo: str = GRAFO_DEFAULT, modo: str = "paridad",
                 indice_fulltext: str | None = None):
        if grafo not in GRAFOS:
            raise KeyError(f"grafo desconocido: {grafo!r}; válidos: {list(GRAFOS)}")
        if modo in MODOS_FUTUROS:
            raise NotImplementedError(
                f"modo {modo!r} no implementado en A1.1 ({MODOS_FUTUROS[modo]})")
        if modo not in MODOS:
            raise ValueError(f"modo desconocido: {modo!r}; válidos: {MODOS}")
        self.driver = driver
        self.grafo = grafo
        self.label = GRAFOS[grafo]["label"]
        self.modo = modo
        self.indice = indice_fulltext or GRAFOS[grafo]["indice_fulltext"]

    # ------------------------------------------------------------------ #
    @staticmethod
    def _limite(limite) -> int:
        # Misma expresión que GraphIndex.buscar_nodos.
        try:
            return max(1, min(int(limite), 50))
        except (TypeError, ValueError):
            return 10

    # --- tool 1 ---
    def buscar_nodos(self, consulta: str, limite: int = 10) -> dict:
        toks = _tokens(consulta)
        if not toks:
            return {"consulta": consulta, "resultados": [], "total": 0}
        limite = self._limite(limite)
        if self.modo == "paridad":
            return self._buscar_paridad(consulta, toks, limite)
        return self._buscar_fulltext(consulta, toks, limite)

    def _buscar_paridad(self, consulta: str, toks: list, limite: int) -> dict:
        q = set(toks)
        with self.driver.session() as session:
            filas = session.run(
                f"MATCH (n:`{self.label}`) WHERE any(t IN n.tokens WHERE t IN $q) "
                "RETURN n.id AS id, n.type AS type, n.label AS label, n.tokens AS tokens",
                q=sorted(q),
            ).data()
            # Score y orden en Python, con las mismas expresiones del harness.
            scored = []
            for f in filas:
                score = len(q & set(f["tokens"]))
                if score:  # siempre > 0 por el filtro; se conserva la forma del harness
                    scored.append((score, len(f["label"] or ""), f))
            scored.sort(key=lambda t: (-t[0], t[1], t[2]["id"]))
            top = scored[:limite]
            # props_json solo para el top-K (segunda consulta, liviana).
            ids = [f["id"] for _, _, f in top]
            pj = {}
            if ids:
                for r in session.run(
                        f"MATCH (n:`{self.label}`) WHERE n.id IN $ids "
                        "RETURN n.id AS id, n.props_json AS pj", ids=ids):
                    pj[r["id"]] = r["pj"]
        return {
            "consulta": consulta,
            "total_con_match": len(scored),
            "resultados": [
                {
                    "id": f["id"],
                    "type": f["type"],
                    "label": f["label"],
                    "tokens_matcheados": score,
                    "resumen_propiedades": _short_props(json.loads(pj[f["id"]])),
                }
                for score, _, f in top
            ],
        }

    def _buscar_fulltext(self, consulta: str, toks: list, limite: int) -> dict:
        q_lucene = " ".join(toks)
        # Agregación server-side: el conteo total se resuelve en Neo4j y solo
        # el top-K viaja al cliente (props_json se lee únicamente para el
        # slice). Traer todos los hits al cliente multiplicaba ~20x la
        # latencia en consultas con cientos de matches.
        with self.driver.session() as session:
            rec = session.run(
                f"CALL db.index.fulltext.queryNodes('{self.indice}', $q) "
                "YIELD node, score "
                "WITH node, score "
                "ORDER BY score DESC, size(node.label) ASC, node.id ASC "
                "WITH collect(node) AS ns "
                "RETURN size(ns) AS total, "
                "       [x IN ns[0..$lim] | {id: x.id, type: x.type, "
                "        label: x.label, pj: x.props_json}] AS top",
                q=q_lucene, lim=limite,
            ).single()
        q_set = set(toks)
        resultados = [
            {
                "id": r["id"],
                "type": r["type"],
                "label": r["label"],
                "tokens_matcheados": len(q_set & set(_tokens(r["label"] or "")
                                                     + _tokens(r["id"] or ""))),
                "resumen_propiedades": _short_props(json.loads(r["pj"])),
            }
            for r in rec["top"]
        ]
        return {
            "consulta": consulta,
            "total_con_match": rec["total"],
            "resultados": resultados,
        }

    # --- tool 2 ---
    def ver_nodo(self, id: str) -> dict:
        with self.driver.session() as session:
            rec = session.run(
                f"MATCH (n:`{self.label}` {{id: $id}}) "
                "RETURN n.type AS type, n.label AS label, "
                "       n.props_json AS pj, n.provenances_json AS vj",
                id=id,
            ).single()
        if rec is None:
            return {"error": f"No existe un nodo con id '{id}'.",
                    "sugerencia": "Usá buscar_nodos para encontrar el id correcto."}
        return {
            "id": id,
            "type": rec["type"],
            "label": rec["label"],
            "properties": json.loads(rec["pj"]),
            "provenances": json.loads(rec["vj"]),
        }

    # --- tool 3 ---
    def ver_vecinos(self, id: str, direccion: str = "ambas", limite: int = 40) -> dict:
        with self.driver.session() as session:
            rec = session.run(
                f"MATCH (n:`{self.label}` {{id: $id}}) RETURN n.label AS label", id=id,
            ).single()
            if rec is None:
                return {"error": f"No existe un nodo con id '{id}'.",
                        "sugerencia": "Usá buscar_nodos para encontrar el id correcto."}
            direccion = (direccion or "ambas").lower()
            if direccion not in ("ambas", "salientes", "entrantes"):
                direccion = "ambas"

            out = session.run(
                f"MATCH (n:`{self.label}` {{id: $id}})-[r]->(v:`{self.label}`) "
                "RETURN type(r) AS relation, v.id AS vecino_id, "
                "       v.label AS vecino_label, r.provenances_json AS vj "
                "ORDER BY r.orden", id=id,
            ).data()
            inn = session.run(
                f"MATCH (n:`{self.label}` {{id: $id}})<-[r]-(v:`{self.label}`) "
                "RETURN type(r) AS relation, v.id AS vecino_id, "
                "       v.label AS vecino_label, r.provenances_json AS vj "
                "ORDER BY r.orden", id=id,
            ).data()

        def _fila(r):
            return {
                "relation": r["relation"],
                "vecino_id": r["vecino_id"],
                "vecino_label": r["vecino_label"],
                "provenances": json.loads(r["vj"]),
            }

        res = {
            "id": id,
            "label": rec["label"],
            "n_salientes_total": len(out),
            "n_entrantes_total": len(inn),
        }
        if direccion in ("ambas", "salientes"):
            filas = [_fila(r) for r in out]
            res["salientes"] = filas[:limite]
            res["salientes_truncado"] = len(filas) > limite
        if direccion in ("ambas", "entrantes"):
            filas = [_fila(r) for r in inn]
            res["entrantes"] = filas[:limite]
            res["entrantes_truncado"] = len(filas) > limite
        return res
