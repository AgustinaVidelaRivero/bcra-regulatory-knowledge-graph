"""
cargar_kg.py — Carga determinística de los grafos de EV2 en Neo4j Community.

Origen (c26cb9b): cargaba solo el grafo vigente (reensamblado_v3 = KG-Refinado)
bajo el label :Nodo. U-A1.1 lo extiende a los DOS grafos del registro
`grafos.py` (KG-Refinado 26fac8b4 / KG-Reextraído 8e2eadee) conservando el
modelo de datos y las verificaciones originales, y agregando:

  * un label de grafo por nodo (:KG_Refinado / :KG_Reextraido) — Community no
    soporta multi-database; los dos grafos conviven en la db `neo4j` y TODA
    query de tools filtra por ese label (los ids colisionan entre grafos, así
    que la constraint de unicidad de `id` es POR LABEL DE GRAFO, no global);
  * el sha256 del kg.json como propiedad del grafo cargado: nodo
    (:KG_Meta {grafo, nombre_canonico, kg_sha256, kg_path, commit_sellado,
    n_nodos, n_aristas, vista_runtime, version_carga}) — sin timestamps, para
    que dos cargas sucesivas dejen exactamente el mismo estado;
  * `tokens` (lista ordenada y única de `_tokens(label) + _tokens(id)` del
    harness, calculada con la función IMPORTADA en el momento de la carga) e
    `id_texto` (`" ".join(_tokens(id))`) — insumos del modo paridad y del
    índice full-text con id buscable (ver neo4j_index.py / indices.py);
  * `props_json` PRESERVA el orden de claves del loader (antes: sort_keys=True).
    Motivo: `_short_props` del harness recorre `props.items()` en orden de
    inserción cuando el nodo no tiene description/descripcion (1.506 nodos en
    KG-Refinado, 1.944 en KG-Reextraído); con claves ordenadas el
    `resumen_propiedades` de buscar_nodos no era byte-idéntico. Es un hallazgo
    de esta unidad sobre el código de c26cb9b, no una regresión del cuarteto;
  * carga IDEMPOTENTE verificable: `--verificar-idempotencia` carga dos veces
    y compara una huella sha256 del estado completo en Neo4j (todas las
    propiedades de nodos y aristas, labels, orden) — debe ser idéntica — y una
    huella de contenido calculada por igual desde el loader y desde Neo4j.

Se lee el kg.json vía la vista runtime EV2 (`grafos.cargar_vista_runtime`,
solo IMPORT del cuarteto y de comun_ev2). El kg.json es read-only; antes de
cargar se verifica su sha256 contra el valor sellado.

Modelo de datos en Neo4j (por nodo)
-----------------------------------
- Labels: :Nodo (común, queries globales entre grafos, SIN constraint) +
  :<grafo> (:KG_Refinado | :KG_Reextraido; constraint de unicidad de id por
  label) + :<type> (:Obligacion, :Sujeto, … — 7 tipos por grafo).
- Propiedades: `id`, `type`, `label`, `grafo`, `tokens`, `id_texto`,
  `props_json`, `provenances_json` + las properties semánticas aplanadas con su
  nombre original (verificado en ambos grafos: sin colisiones con las
  reservadas; valores str, bool o list[str] — tipos nativos de Neo4j).
- Aristas: relationship type = `relation` (16 tipos en KG-Refinado, 11 en
  KG-Reextraído), con `orden` (posición en kg.edges: reproduce el orden de
  inserción del in-memory en ver_vecinos) y `provenances_json`.
- Propiedades de las aristas (U-NAV-DISENO, N5; decisión 6 del mandato firmado
  en c2ddf5f7): además, las que muestran las herramientas de navegación
  (banco_mcp/mcp_kg/familias_nav.py), con su nombre original y solo si la arista
  las trae:
    · de `properties`: `alcance`, `destino` y `evidencia` (remite_a) y las marcas
      de la cola humana (`cola_humana`, `cola_chunks`, `estado_e3`);
    · de fuera de `properties`, que la vista runtime no lleva: `no_verificada_e3`
      y `rol_fuente` (la marca del sujeto derivado, si la parte B de la enmienda 6
      a L-ESQ-R2 llega a regir). Se leen del kg.json crudo, por posición, solo si
      las aristas de la vista están alineadas con las del crudo (misma cantidad y
      la misma tripla en cada posición); si no, no se exportan y se informa.
  Las tres tools de hoy no las leen: sus salidas no cambian. `huella_neo4j`
  conserva sus dos huellas de HEAD (`contenido` no mira estas propiedades;
  `estado`, que mira todas, cambia) y suma `estado_sin_props_n5`, el estado sin
  ellas, comparable con el `estado` de antes de N5. La paridad de estas
  propiedades se verifica aparte (`huella_props_aristas_*`). KG_Meta suma
  `props_aristas` (la lista exportada): el servidor de navegación exige esa clave.

Uso
---
  python cargar_kg.py                          # ambos grafos: verifica sha, recarga, verifica
  python cargar_kg.py --grafo KG_Refinado      # solo uno
  python cargar_kg.py --solo-verificar         # conteos + muestreo + huellas, sin recargar
  python cargar_kg.py --verificar-idempotencia # carga 2 veces y compara huellas
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

NEO4J_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(NEO4J_DIR))

from grafos import (  # noqa: E402
    GRAFOS, CLAVES, GRAFO_DEFAULT, verificar_sha, cargar_vista_runtime, rel_repo,
)
from conexion import abrir_driver  # noqa: E402
from harness import _tokens  # noqa: E402  (solo IMPORT del cuarteto hasheado)

# Compatibilidad con los módulos de c26cb9b que importaban estas constantes
# (test_equivalencia.py / benchmark_latencia.py): apuntan al grafo vigente.
KG_PATH = GRAFOS[GRAFO_DEFAULT]["path"]
KG_SHA256 = GRAFOS[GRAFO_DEFAULT]["sha256"]
NODOS_ESPERADOS = GRAFOS[GRAFO_DEFAULT]["n_nodos"]
ARISTAS_ESPERADAS = GRAFOS[GRAFO_DEFAULT]["n_aristas"]

VERSION_CARGA = "A1.1"
BATCH = 1000
SEED_MUESTREO = 20260806  # se conserva el de la unidad original (muestreo reproducible)

PROPS_RESERVADAS = {"id", "type", "label", "grafo", "tokens", "id_texto",
                    "props_json", "provenances_json"}

# U-NAV-DISENO, N5 (decisión 6): propiedades de arista exportadas (ver docstring).
PROPS_ARISTA_N5 = ("alcance", "destino", "evidencia", "cola_humana", "cola_chunks", "estado_e3")
MARCAS_ARISTA_N5 = ("no_verificada_e3", "rol_fuente")
EXPORTADAS_ARISTA_N5 = PROPS_ARISTA_N5 + MARCAS_ARISTA_N5
CLAVE_META_N5 = "props_aristas"


def cargar_kg(clave: str = GRAFO_DEFAULT):
    return cargar_vista_runtime(clave)


def _fila_nodo(n, clave: str) -> dict:
    fila = {
        "id": n.id,
        "type": n.type,
        "label": n.label,
        "grafo": clave,
        # orden de claves del loader preservado (ver docstring); sin sort_keys.
        "props_json": json.dumps(n.properties, ensure_ascii=False),
        "provenances_json": json.dumps(n.provenances, ensure_ascii=False),
        "tokens": sorted(set(_tokens(n.label) + _tokens(n.id))),
        "id_texto": " ".join(_tokens(n.id)),
    }
    for k, v in n.properties.items():
        if k in PROPS_RESERVADAS:
            continue  # sin colisiones verificadas; defensa por las dudas
        if isinstance(v, (str, bool, int, float)) or (
                isinstance(v, list) and v and all(isinstance(x, str) for x in v)):
            fila[k] = v
        # otros tipos (dict, listas heterogéneas) no son propiedad válida de
        # Neo4j: quedan solo en props_json (fuente canónica). No ocurre en
        # los dos grafos del registro (verificado), se deja como defensa.
    return fila


def _valor_arista(v):
    """Valor de una propiedad exportada de arista como tipo nativo de Neo4j: str, bool, int, float o lista de str tal
    cual; cualquier otro (dict, lista mixta), como su json (ensure_ascii=False)."""
    if isinstance(v, (str, bool, int, float)) or (isinstance(v, list) and v and all(isinstance(x, str) for x in v)):
        return v
    return json.dumps(v, ensure_ascii=False)


def props_aristas_n5(kg, clave: str) -> dict:
    """Las propiedades de arista de N5 (decisión 6), una por arista de kg.edges en su orden: {"filas": [dict],
    "alineadas": bool}. Las de `properties` salen de la vista; las marcas de fuera de `properties`, del kg.json crudo
    por posición, solo si la vista está alineada con el crudo. Un valor None no se exporta (Neo4j no guarda nulos)."""
    crudo = json.loads(GRAFOS[clave]["path"].read_text(encoding="utf-8")).get("edges", [])
    alineadas = len(crudo) == len(kg.edges) and all(
        (c.get("source"), c.get("relation"), c.get("target")) == (e.source, e.relation, e.target)
        for c, e in zip(crudo, kg.edges))
    filas = []
    for i, e in enumerate(kg.edges):
        p = {}
        for k in PROPS_ARISTA_N5:
            v = (e.properties or {}).get(k)
            if v is not None:
                p[k] = _valor_arista(v)
        if alineadas:
            for k in MARCAS_ARISTA_N5:
                v = crudo[i].get(k)
                if v is not None:
                    p[k] = _valor_arista(v)
        filas.append(p)
    return {"filas": filas, "alineadas": alineadas}


def cargar_en_neo4j(driver, kg, clave: str = GRAFO_DEFAULT) -> dict:
    """Recarga completa del grafo `clave`: borra SOLO sus nodos/aristas y los
    vuelve a crear en el orden del kg.json. Devuelve conteos de lo creado y de
    aristas colgantes (source/target inexistente: no se crean; el in-memory
    las contaría en n_*_total, así que deben ser 0 para que haya paridad)."""
    g = GRAFOS[clave]
    label = g["label"]
    with driver.session() as session:
        # Constraint legacy de c26cb9b (unicidad global sobre :Nodo): incompatible
        # con dos grafos que comparten ids -> se elimina si existe.
        session.run("DROP CONSTRAINT nodo_id IF EXISTS").consume()
        session.run(
            f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
            f"FOR (n:`{label}`) REQUIRE n.id IS UNIQUE"
        ).consume()
        session.run(
            "CREATE CONSTRAINT kg_meta_grafo IF NOT EXISTS "
            "FOR (m:KG_Meta) REQUIRE m.grafo IS UNIQUE"
        ).consume()
        # Base limpia SOLO para este grafo (el otro grafo no se toca).
        session.run(
            f"MATCH (n:`{label}`) CALL (n) {{ DETACH DELETE n }} "
            "IN TRANSACTIONS OF 2000 ROWS"
        ).consume()

        # Nodos, agrupados por type (labels: :Nodo + :<grafo> + :<type>).
        por_tipo = {}
        for n in kg.nodes:
            por_tipo.setdefault(n.type, []).append(_fila_nodo(n, clave))
        for tipo, filas in por_tipo.items():
            for i in range(0, len(filas), BATCH):
                session.run(
                    f"UNWIND $filas AS fila CREATE (n:Nodo:`{label}`:`{tipo}`) SET n = fila",
                    filas=filas[i:i + BATCH],
                ).consume()

        # Aristas, agrupadas por relation; `orden` = posición en kg.edges. N5: más las
        # propiedades de la decisión 6 (`props`, vacío si la arista no trae ninguna).
        n5 = props_aristas_n5(kg, clave)
        por_rel = {}
        for idx, e in enumerate(kg.edges):
            por_rel.setdefault(e.relation, []).append({
                "source": e.source,
                "target": e.target,
                "orden": idx,
                "provenances_json": json.dumps(e.provenances, ensure_ascii=False),
                "props": n5["filas"][idx],
            })
        creadas = 0
        for rel, filas in por_rel.items():
            for i in range(0, len(filas), BATCH):
                rec = session.run(
                    "UNWIND $filas AS fila "
                    f"MATCH (s:`{label}` {{id: fila.source}}), (t:`{label}` {{id: fila.target}}) "
                    f"CREATE (s)-[r:`{rel}`]->(t) "
                    "SET r.orden = fila.orden, "
                    "    r.provenances_json = fila.provenances_json, "
                    "    r += fila.props "
                    "RETURN count(r) AS c",
                    filas=filas[i:i + BATCH],
                ).single()
                creadas += rec["c"]
        colgantes = len(kg.edges) - creadas

        # Metadatos del grafo cargado (sha del kg.json como propiedad).
        session.run(
            "MERGE (m:KG_Meta {grafo: $grafo}) SET m = $props",
            grafo=clave,
            props={
                "grafo": clave,
                "nombre_canonico": g["nombre_canonico"],
                "kg_sha256": g["sha256"],
                "kg_path": rel_repo(g["path"]),
                "commit_sellado": g["commit_sellado"],
                "n_nodos": len(kg.nodes),
                "n_aristas": len(kg.edges),
                "vista_runtime": g["vista_runtime"],
                "version_carga": VERSION_CARGA,
                # N5: las propiedades de arista que esta carga exporta (sin las marcas de fuera de
                # `properties` si la vista no está alineada con el crudo).
                CLAVE_META_N5: list(EXPORTADAS_ARISTA_N5 if n5["alineadas"] else PROPS_ARISTA_N5),
            },
        ).consume()
    return {"nodos": len(kg.nodes), "aristas_creadas": creadas,
            "aristas_colgantes": colgantes}


def leer_meta(driver, clave: str) -> dict | None:
    with driver.session() as session:
        rec = session.run("MATCH (m:KG_Meta {grafo: $g}) RETURN properties(m) AS p",
                          g=clave).single()
    return dict(rec["p"]) if rec else None


def huella_neo4j(driver, clave: str) -> dict:
    """Huellas sha256 del grafo tal como está en Neo4j.
    - `estado`: TODAS las propiedades de nodos (incluidas las aplanadas) y
      labels, y todas las propiedades/tipo/extremos de aristas, más el KG_Meta.
      Sirve para verificar que dos cargas sucesivas dejan el mismo estado.
    - `contenido`: solo (id, type, label, props_json, provenances_json, tokens,
      id_texto) por nodo y (source, relation, target, orden, provenances_json)
      por arista — comparable 1:1 con `huella_loader`."""
    label = GRAFOS[clave]["label"]
    with driver.session() as session:
        nodos = session.run(
            f"MATCH (n:`{label}`) RETURN properties(n) AS p, labels(n) AS ls "
            "ORDER BY n.id"
        ).data()
        aristas = session.run(
            f"MATCH (s:`{label}`)-[r]->(t:`{label}`) "
            "RETURN s.id AS s, type(r) AS rel, t.id AS t, properties(r) AS p "
            "ORDER BY r.orden"
        ).data()
    meta = leer_meta(driver, clave)
    estado = hashlib.sha256()
    contenido = hashlib.sha256()
    # N5: el estado sin las propiedades de arista de la decisión 6 ni la clave `props_aristas` de KG_Meta, con la
    # misma serialización que `estado`: es el `estado` de una carga de antes de N5 del mismo grafo.
    estado_sin_n5 = hashlib.sha256()
    for r in nodos:
        p = r["p"]
        b = json.dumps({"p": p, "ls": sorted(r["ls"])}, ensure_ascii=False, sort_keys=True).encode()
        estado.update(b)
        estado_sin_n5.update(b)
        contenido.update(json.dumps(
            [p["id"], p["type"], p["label"], p["props_json"],
             p["provenances_json"], list(p["tokens"]), p["id_texto"]],
            ensure_ascii=False).encode())
    for r in aristas:
        estado.update(json.dumps(r, ensure_ascii=False, sort_keys=True).encode())
        sin = dict(r, p={k: v for k, v in r["p"].items() if k not in EXPORTADAS_ARISTA_N5})
        estado_sin_n5.update(json.dumps(sin, ensure_ascii=False, sort_keys=True).encode())
        contenido.update(json.dumps(
            [r["s"], r["rel"], r["t"], r["p"]["orden"], r["p"]["provenances_json"]],
            ensure_ascii=False).encode())
    estado.update(json.dumps(meta, ensure_ascii=False, sort_keys=True).encode())
    meta_sin = None if meta is None else {k: v for k, v in meta.items() if k != CLAVE_META_N5}
    estado_sin_n5.update(json.dumps(meta_sin, ensure_ascii=False, sort_keys=True).encode())
    return {"estado": estado.hexdigest(), "contenido": contenido.hexdigest(),
            "estado_sin_props_n5": estado_sin_n5.hexdigest(),
            "n_nodos": len(nodos), "n_aristas": len(aristas)}


def _huella_props(filas) -> str:
    """sha256 de las propiedades de arista de N5, una entrada por arista en el orden de kg.edges: [orden, {clave:
    valor}] con las claves ordenadas. Misma serialización para el loader y para Neo4j."""
    h = hashlib.sha256()
    for orden, p in filas:
        h.update(json.dumps([orden, p], ensure_ascii=False, sort_keys=True).encode())
    return h.hexdigest()


def huella_props_aristas_loader(kg, clave: str) -> str:
    return _huella_props(enumerate(props_aristas_n5(kg, clave)["filas"]))


def huella_props_aristas_neo4j(driver, clave: str) -> str:
    label = GRAFOS[clave]["label"]
    with driver.session() as session:
        filas = session.run(
            f"MATCH (:`{label}`)-[r]->(:`{label}`) RETURN r.orden AS o, properties(r) AS p ORDER BY r.orden").data()
    return _huella_props((f["o"], {k: v for k, v in f["p"].items() if k in EXPORTADAS_ARISTA_N5}) for f in filas)


def huella_loader(kg, clave: str) -> str:
    """Huella de contenido calculada desde la vista del loader con la MISMA
    serialización que `huella_neo4j['contenido']`."""
    h = hashlib.sha256()
    filas = sorted((_fila_nodo(n, clave) for n in kg.nodes), key=lambda f: f["id"])
    for f in filas:
        h.update(json.dumps(
            [f["id"], f["type"], f["label"], f["props_json"],
             f["provenances_json"], f["tokens"], f["id_texto"]],
            ensure_ascii=False).encode())
    for idx, e in enumerate(kg.edges):
        h.update(json.dumps(
            [e.source, e.relation, e.target, idx,
             json.dumps(e.provenances, ensure_ascii=False)],
            ensure_ascii=False).encode())
    return h.hexdigest()


def verificar_carga(driver, kg, clave: str = GRAFO_DEFAULT, n_muestra: int = 20) -> bool:
    """Conteos exactos + meta con sha + muestreo reproducible campo por campo +
    huella de contenido loader vs Neo4j.

    La comparación de id/type/label/properties es contra el kg.json CRUDO (las
    properties normalizadas por el loader son idénticas a las crudas en ambos
    grafos). Las provenances almacenadas son la vista runtime (primaria; en
    KG-Reextraído además mapeada de shape) — la diferencia con el crudo se
    reporta, no se oculta.
    """
    import random

    g = GRAFOS[clave]
    label = g["label"]
    crudo = json.loads(g["path"].read_text(encoding="utf-8"))
    crudo_por_id = {n["id"]: n for n in crudo["nodes"]}

    ok = True
    with driver.session() as session:
        n_nodos = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()["c"]
        n_aristas = session.run(
            f"MATCH (:`{label}`)-[r]->(:`{label}`) RETURN count(r) AS c").single()["c"]
        n_cruzadas = session.run(
            f"MATCH (:`{label}`)-[r]->(t) WHERE NOT t:`{label}` RETURN count(r) AS c"
        ).single()["c"]

        print(f"[{clave}] conteo nodos   Neo4j={n_nodos}  esperado={g['n_nodos']} "
              f"{'✓' if n_nodos == g['n_nodos'] else '✗'}")
        print(f"[{clave}] conteo aristas Neo4j={n_aristas}  esperado={g['n_aristas']} "
              f"{'✓' if n_aristas == g['n_aristas'] else '✗'}")
        print(f"[{clave}] aristas hacia otro grafo: {n_cruzadas} "
              f"{'✓' if n_cruzadas == 0 else '✗'}")
        ok = ok and n_nodos == g["n_nodos"] and n_aristas == g["n_aristas"] and n_cruzadas == 0

        meta = leer_meta(driver, clave)
        if not meta or meta.get("kg_sha256") != g["sha256"]:
            print(f"[{clave}] ✗ KG_Meta ausente o sha distinto: {meta}")
            ok = False
        else:
            print(f"[{clave}] KG_Meta.kg_sha256={meta['kg_sha256']} ✓ "
                  f"(path={meta['kg_path']}, commit={meta['commit_sellado']}, "
                  f"n={meta['n_nodos']}/{meta['n_aristas']}, version_carga={meta['version_carga']})")

        rng = random.Random(SEED_MUESTREO)
        muestra = rng.sample(kg.nodes, n_muestra)
        print(f"[{clave}] muestreo de {n_muestra} nodos (seed={SEED_MUESTREO}):")
        for n in muestra:
            rec = session.run(
                f"MATCH (m:`{label}` {{id: $id}}) "
                "RETURN m.type AS type, m.label AS label, m.grafo AS grafo, "
                "       m.props_json AS pj, m.provenances_json AS vj, labels(m) AS ls, "
                "       m.tokens AS tokens, m.id_texto AS id_texto",
                id=n.id,
            ).single()
            if rec is None:
                print(f"  ✗ {n.id}: NO ESTÁ en Neo4j")
                ok = False
                continue
            raw = crudo_por_id[n.id]
            fallas = []
            if rec["type"] != raw["type"]:
                fallas.append(f"type: {rec['type']!r} != {raw['type']!r}")
            if rec["label"] != raw["label"]:
                fallas.append("label difiere")
            if rec["grafo"] != clave:
                fallas.append(f"grafo: {rec['grafo']!r}")
            if json.loads(rec["pj"]) != (raw.get("properties") or {}):
                fallas.append("properties difieren del kg.json crudo")
            if rec["pj"] != json.dumps(n.properties, ensure_ascii=False):
                fallas.append("props_json difiere del loader (bytes/orden)")
            if json.loads(rec["vj"]) != n.provenances:
                fallas.append("provenances difieren del loader")
            if set(rec["ls"]) != {"Nodo", label, raw["type"]}:
                fallas.append(f"labels Neo4j inesperados: {rec['ls']}")
            if list(rec["tokens"]) != sorted(set(_tokens(n.label) + _tokens(n.id))):
                fallas.append("tokens difieren de _tokens(label)+_tokens(id)")
            if rec["id_texto"] != " ".join(_tokens(n.id)):
                fallas.append("id_texto difiere")
            n_prov_crudo = len(raw.get("provenances") or [])
            nota_prov = ("" if n_prov_crudo <= 1 else
                         f"  [crudo trae {n_prov_crudo} provenances; "
                         "almacenada la primaria (vista runtime)]")
            if fallas:
                print(f"  ✗ {n.id}: " + "; ".join(fallas))
                ok = False
            else:
                print(f"  ✓ {n.id} ({raw['type']}){nota_prov}")

    hn = huella_neo4j(driver, clave)
    hl = huella_loader(kg, clave)
    print(f"[{clave}] huella contenido loader={hl}")
    print(f"[{clave}] huella contenido neo4j ={hn['contenido']} "
          f"{'✓ idéntica' if hn['contenido'] == hl else '✗ DIFIERE'}")
    print(f"[{clave}] huella estado neo4j    ={hn['estado']}")
    ok = ok and hn["contenido"] == hl
    # N5 (decisión 6): paridad loader = Neo4j de las propiedades de arista exportadas.
    pl = huella_props_aristas_loader(kg, clave)
    pn = huella_props_aristas_neo4j(driver, clave)
    print(f"[{clave}] huella props aristas loader={pl}")
    print(f"[{clave}] huella props aristas neo4j ={pn} {'✓ idéntica' if pl == pn else '✗ DIFIERE'}")
    ok = ok and pl == pn
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--grafo", choices=CLAVES + ["todos"], default="todos",
                    help="grafo a cargar (default: todos)")
    ap.add_argument("--solo-verificar", action="store_true",
                    help="no recarga: solo conteos + muestreo + huellas")
    ap.add_argument("--verificar-idempotencia", action="store_true",
                    help="carga DOS veces y exige huella de estado idéntica")
    args = ap.parse_args()
    claves = CLAVES if args.grafo == "todos" else [args.grafo]

    driver = abrir_driver()
    ok_global = True
    try:
        for clave in claves:
            g = GRAFOS[clave]
            print(f"\n===== {clave} ({g['nombre_canonico']}, {g['sha256'][:8]}) =====")
            print(f"sha256 verificado: {verificar_sha(clave)} ✓")
            kg = cargar_kg(clave)
            print(f"loader (vista runtime EV2): {len(kg.nodes)} nodos / {len(kg.edges)} aristas "
                  f"(raw {kg.raw_node_count}/{kg.raw_edge_count}, merges={len(kg.merges)})")
            if not args.solo_verificar:
                r = cargar_en_neo4j(driver, kg, clave)
                print(f"carga completa: {r}")
                if r["aristas_colgantes"]:
                    print(f"✗ {r['aristas_colgantes']} aristas colgantes (no creadas)")
                    ok_global = False
                if args.verificar_idempotencia:
                    h1 = huella_neo4j(driver, clave)
                    r2 = cargar_en_neo4j(driver, kg, clave)
                    h2 = huella_neo4j(driver, clave)
                    igual = h1 == h2
                    print(f"idempotencia: huella estado carga1={h1['estado']}")
                    print(f"              huella estado carga2={h2['estado']} "
                          f"{'✓ idéntica' if igual else '✗ DIFIERE'} "
                          f"(conteos {h2['n_nodos']}/{h2['n_aristas']}, {r2})")
                    ok_global = ok_global and igual
            ok = verificar_carga(driver, kg, clave)
            ok_global = ok_global and ok
    finally:
        driver.close()

    print("\nVERIFICACIÓN:", "OK" if ok_global else "CON FALLAS")
    sys.exit(0 if ok_global else 1)


if __name__ == "__main__":
    main()
