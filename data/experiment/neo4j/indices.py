"""
indices.py — Índices full-text Lucene POR GRAFO sobre Neo4j + tests dirigidos
contra los dos defectos conocidos de alcanzabilidad del índice léxico
in-memory (que solo tokeniza label + id).

Origen (c26cb9b): un único índice `nodos_fulltext` sobre :Nodo(label,
descripcion, description). U-A1.1 lo generaliza a un índice por grafo y suma
el id como campo buscable:

Índices creados (uno por grafo del registro grafos.py)
------------------------------------------------------
  nodos_fulltext_kg_refinado   : FULLTEXT FOR (n:KG_Refinado)
  nodos_fulltext_kg_reextraido : FULLTEXT FOR (n:KG_Reextraido)
  campos, en ambos: [label, descripcion, description, id_texto]
    - `label`: paridad con el índice in-memory.
    - `descripcion` y `description`: la mejora a demostrar — KG-Refinado usa
      ambas claves (1.863 / 1.101 nodos); KG-Reextraído solo `descripcion`
      (4.234). Indexar una sola dejaría parte del grafo sin cobertura.
    - `id_texto` (NUEVO en A1.1): `" ".join(_tokens(id))` calculado en la
      carga. Motivo medido: en el in-memory el id es un canal de recuperación
      REAL — 4.412/4.469 nodos de KG-Refinado y 6.139/6.178 de KG-Reextraído
      tienen tokens en el id que NO están en el label (prefijo de tipo
      "sujeto"/"excepcion", y slugs del texto original más largos que el
      label acortado). Indexar el `id` crudo no serviría: el tokenizer
      estándar de Lucene trata `_` como parte de la palabra (UAX#29,
      ExtendNumLet) y "Comunicacion_a_6312" sería UN token. Alternativa
      descartada: fallback de lookup exacto por id — solo cubre el caso en
      que el agente pega un id entero (13 de 10.788 llamadas reales a
      buscar_nodos en las trazas EV2+posthoc), no el canal de tokens.
      Efecto: el ranking del modo full-text cambia respecto de c26cb9b (los
      términos del label suelen repetirse en id_texto y ganan peso). Es una
      decisión revisable en una línea (`CAMPOS_FULLTEXT`).
    - `nota_fuente` EXCLUIDA (decisión original, se mantiene): 2 nodos, contenido
      meta-editorial sobre la extracción, no normativo.
  Analyzer: `spanish` (stemming + stopwords castellanas de Lucene). El default
  `standard-no-stop-words` no stemmea: "asociación mutual" no matchearía
  "asociaciones mutuales" de la descripcion — precisamente el caso BKL-0003.

  Por qué UN índice POR grafo y no uno compartido con filtro por label: el
  score BM25 de Lucene usa estadísticas del corpus indexado (IDF, largo
  medio de documento). Un índice compartido mezclaría las estadísticas de los
  dos grafos y el ranking de cada uno dejaría de ser el de "su" corpus; con
  índices separados cada grafo se comporta exactamente como si fuera la única
  base (equivalente a dos instancias, sin pagar dos contenedores).
  El índice legacy `nodos_fulltext` (sobre :Nodo, ambos grafos mezclados) se
  elimina si existe.

Tests dirigidos (se corren con `python indices.py [--grafo ...]`)
------------------------------------------------------------------
  (a) BKL-0003 — la búsqueda "asociación mutual" (y variantes) debe encontrar
      Excepcion_otros_proveedores_no_financieros_de_credito_alcanzados_por_
      las_normas_sobre_prov_5f95b9 (KG-Refinado; en KG-Reextraído el nodo con
      ese id no existe y el test se reporta como no aplicable).
      NOTA de estado: en KG-Refinado el label de ese nodo YA fue enriquecido
      en capa KG con "asociación mutual o cooperativa" (recuperación léxica,
      laudo C6), de modo que el índice de label+id también lo encuentra hoy.
      La mejora estructural del full-text se demuestra con el sub-test (a2):
      queries con texto verbatim del inciso que vive SOLO en la `descripcion`.
  (b) BKL-0027 — los 7 vecinos entrantes `miembro_de` de
      Sujeto_rol_sujeto_obligado_proteccion deben recuperarse tanto con
      query de dirección explícita como con query bidireccional (KG-Refinado).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conexion import abrir_driver  # noqa: E402
from grafos import GRAFOS, CLAVES, GRAFO_DEFAULT  # noqa: E402

# Compatibilidad c26cb9b: nombre del índice del grafo vigente.
INDICE_FULLTEXT = GRAFOS[GRAFO_DEFAULT]["indice_fulltext"]
INDICE_LEGACY = "nodos_fulltext"
CAMPOS_FULLTEXT = ["label", "descripcion", "description", "id_texto"]
ANALYZER = "spanish"

NODO_BKL0003 = ("Excepcion_otros_proveedores_no_financieros_de_credito_"
                "alcanzados_por_las_normas_sobre_prov_5f95b9")
NODO_BKL0027 = "Sujeto_rol_sujeto_obligado_proteccion"


def nombre_indice(clave: str) -> str:
    return GRAFOS[clave]["indice_fulltext"]


def crear_indice(driver, clave: str = GRAFO_DEFAULT) -> None:
    g = GRAFOS[clave]
    campos = ", ".join(f"n.{c}" for c in CAMPOS_FULLTEXT)
    with driver.session() as session:
        session.run(f"DROP INDEX {INDICE_LEGACY} IF EXISTS").consume()
        session.run(
            f"CREATE FULLTEXT INDEX {g['indice_fulltext']} IF NOT EXISTS "
            f"FOR (n:`{g['label']}`) ON EACH [{campos}] "
            f"OPTIONS {{indexConfig: {{`fulltext.analyzer`: '{ANALYZER}'}}}}"
        ).consume()
        session.run("CALL db.awaitIndexes(300)").consume()
    print(f"[{clave}] índice {g['indice_fulltext']} online "
          f"(campos={CAMPOS_FULLTEXT}, analyzer={ANALYZER}).")


def describir_indices(driver) -> list:
    with driver.session() as session:
        return session.run(
            "SHOW FULLTEXT INDEXES YIELD name, labelsOrTypes, properties, state, options "
            "RETURN name, labelsOrTypes, properties, state, "
            "options.indexConfig.`fulltext.analyzer` AS analyzer ORDER BY name"
        ).data()


def buscar_fulltext(session, consulta: str, limite: int = 10,
                    clave: str = GRAFO_DEFAULT) -> list:
    res = session.run(
        f"CALL db.index.fulltext.queryNodes('{nombre_indice(clave)}', $q) "
        "YIELD node, score RETURN node.id AS id, node.type AS type, "
        "node.label AS label, score ORDER BY score DESC LIMIT $lim",
        q=consulta, lim=limite,
    )
    return [dict(r) for r in res]


def _existe(session, clave: str, nid: str) -> bool:
    return session.run(f"MATCH (n:`{GRAFOS[clave]['label']}` {{id: $id}}) RETURN 1",
                       id=nid).single() is not None


def test_bkl_0003(driver, clave: str = GRAFO_DEFAULT) -> bool | None:
    """'asociación mutual' y variantes deben rankear el nodo de la excepción."""
    variantes = [
        "asociación mutual",
        "asociacion mutual",           # sin tilde
        "asociaciones mutuales",       # plural (forma de la descripcion)
        "mutual cooperativa crédito",
    ]
    ok_global = True
    with driver.session() as session:
        if not _existe(session, clave, NODO_BKL0003):
            print(f"  [BKL-0003] nodo {NODO_BKL0003[:40]}… no existe en {clave}: N/A")
            return None
        for v in variantes:
            hits = buscar_fulltext(session, v, limite=10, clave=clave)
            pos = next((i for i, h in enumerate(hits) if h["id"] == NODO_BKL0003), None)
            estado = f"✓ pos {pos + 1}/10" if pos is not None else "✗ NO aparece en top-10"
            print(f"  [BKL-0003] {v!r:38s} -> {estado}  ({len(hits)} hits)")
            if pos is None:
                ok_global = False
    return ok_global


def test_bkl_0003_descripcion(driver, clave: str = GRAFO_DEFAULT) -> bool | None:
    """Sub-test (a2): fragmentos verbatim del inciso presentes SOLO en la
    descripcion (no en label/id) deben rankear el nodo en el top-3."""
    fragmentos = [
        "excepto que se trate de asociaciones mutuales",   # verbatim inciso
        "otros proveedores no financieros de crédito",     # arranque verbatim
    ]
    ok_global = True
    with driver.session() as session:
        if not _existe(session, clave, NODO_BKL0003):
            print(f"  [BKL-0003/desc] nodo no existe en {clave}: N/A")
            return None
        for frag in fragmentos:
            hits = buscar_fulltext(session, frag, limite=10, clave=clave)
            pos = next((i for i, h in enumerate(hits) if h["id"] == NODO_BKL0003), None)
            estado = f"✓ pos {pos + 1}/10" if pos is not None and pos < 3 else \
                     (f"~ pos {pos + 1}/10 (fuera del top-3)" if pos is not None
                      else "✗ NO aparece en top-10")
            print(f"  [BKL-0003/desc] {frag!r:52s} -> {estado}")
            if pos is None or pos >= 3:
                ok_global = False
    return ok_global


def test_bkl_0027(driver, clave: str = GRAFO_DEFAULT) -> bool | None:
    """Los 7 miembro_de entrantes al rol deben salir en query dirigida y bidireccional."""
    ok = True
    label = GRAFOS[clave]["label"]
    with driver.session() as session:
        if not _existe(session, clave, NODO_BKL0027):
            print(f"  [BKL-0027] nodo {NODO_BKL0027} no existe en {clave}: N/A")
            return None
        n_miembro = session.run(
            f"MATCH (:`{label}`)-[r:miembro_de]->(:`{label}`) RETURN count(r) AS c"
        ).single()["c"]
        if n_miembro == 0:
            # BKL-0027 está definido sobre KG-Refinado (backlog: grafo
            # reensamblado_v3); KG-Reextraído no tiene la relación miembro_de
            # en su esquema (11 relaciones, docs/nomenclatura_grafos.md §3.a).
            print(f"  [BKL-0027] {clave} no tiene aristas miembro_de "
                  "(la relación no existe en su esquema): N/A")
            return None
        dirigida = session.run(
            f"MATCH (m:`{label}`)-[r:miembro_de]->(rol:`{label}` {{id: $id}}) "
            "RETURN m.id AS id ORDER BY id", id=NODO_BKL0027,
        ).value("id")
        print(f"  [BKL-0027] dirección explícita (entrantes): {len(dirigida)} miembros")
        for mid in dirigida:
            print(f"      - {mid}")
        if len(dirigida) != 7:
            ok = False

        bidi = session.run(
            f"MATCH (rol:`{label}` {{id: $id}})-[r:miembro_de]-(m:`{label}`) "
            "RETURN m.id AS id ORDER BY id", id=NODO_BKL0027,
        ).value("id")
        print(f"  [BKL-0027] bidireccional: {len(bidi)} miembros "
              f"({'mismo conjunto ✓' if sorted(bidi) == sorted(dirigida) else 'DIFIERE ✗'})")
        if sorted(bidi) != sorted(dirigida):
            ok = False
    return ok


def _fmt(v):
    return "N/A" if v is None else ("OK" if v else "FALLA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grafo", choices=CLAVES + ["todos"], default="todos")
    args = ap.parse_args()
    claves = CLAVES if args.grafo == "todos" else [args.grafo]

    driver = abrir_driver()
    fallas = 0
    try:
        for clave in claves:
            print(f"\n===== {clave} =====")
            crear_indice(driver, clave)
            print("\ntest BKL-0003 (variantes de 'asociación mutual'):")
            ok_a = test_bkl_0003(driver, clave)
            print("\ntest BKL-0003/desc (verbatim solo-descripcion — la mejora estructural):")
            ok_a2 = test_bkl_0003_descripcion(driver, clave)
            print("\ntest BKL-0027 (vecinos entrantes del rol de sujetos):")
            ok_b = test_bkl_0027(driver, clave)
            print(f"\nRESULTADO {clave}: BKL-0003 {_fmt(ok_a)} | "
                  f"BKL-0003/desc {_fmt(ok_a2)} | BKL-0027 {_fmt(ok_b)}")
            fallas += sum(1 for v in (ok_a, ok_a2, ok_b) if v is False)
        print("\nÍndices full-text en la db:")
        for d in describir_indices(driver):
            print(f"  {d['name']}: {d['labelsOrTypes']} {d['properties']} "
                  f"state={d['state']} analyzer={d['analyzer']}")
    finally:
        driver.close()
    sys.exit(0 if fallas == 0 else 1)


if __name__ == "__main__":
    main()
