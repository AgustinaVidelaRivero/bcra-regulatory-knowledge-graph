# Backend Neo4j (experimental) — migración del índice de grafo

Migración experimental del backend de las 3 tools del agente KG-RAG
(`buscar_nodos` / `ver_nodo` / `ver_vecinos`) del índice in-memory del
harness a Neo4j Community, con índice full-text Lucene sobre las
descripciones. Referencia: issue #5.

**Estado: NO inyectado en el pipeline de evaluación.** El pipeline sigue
usando el `GraphIndex` in-memory del harness. El adaptador de este directorio
queda listo para inyección; el cuarteto hasheado
(`loader.py`/`harness.py`/`judge.py`/`llm_cache.py`) no se tocó — toda la
integración es por módulos nuevos que lo importan.

> **Nota de lectura (U-A1.1, 2026-08-17).** Las secciones "Setup reproducible"
> a "Limitaciones conocidas" describen el estado de la unidad original
> (commit c26cb9b: un grafo, un modo, `docker run` manual) y se conservan como
> registro histórico junto con sus resultados (`test_equivalencia_resultados.json`,
> `benchmark_resultados.json`). El estado VIGENTE del directorio — contenedor
> por `docker-compose`, dos grafos, `Neo4jIndex` con dos modos, inyección por
> subclase, selftest de paridad byte-a-byte y benchmark extendido — está en
> **§ Estado post-A1.1**, al final. Ante conflicto entre ambas partes manda
> la sección post-A1.1 (los comandos de setup de abajo siguen funcionando pero
> el `docker run` fue reemplazado por `docker compose up -d`).

## Setup reproducible

Requisitos: Docker; el `.venv` del repo con el driver `neo4j` (6.2.0):

```bash
.venv/bin/pip install neo4j
```

1. Levantar Neo4j Community 5.26.9 (GPLv3; sin Aura, sin Enterprise):

```bash
docker run -d --name neo4j-bcra-kg \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/bcra-kg-local \
  neo4j:5.26.9-community
```

   (5.26 es la serie LTS. `bcra-kg-local` es password de desarrollo local,
   configurable por `NEO4J_PASSWORD`; ver `conexion.py`. Sin volumen: la db
   se repuebla entera desde el kg.json en cada carga — el kg.json sellado es
   la única fuente de verdad, el contenedor es descartable.)

2. Cargar el grafo vigente (verifica sha256 sellado antes de cargar; aborta
   si difiere):

```bash
.venv/bin/python data/experiment/neo4j/cargar_kg.py
```

3. Crear el índice full-text y correr los tests de alcanzabilidad:

```bash
.venv/bin/python data/experiment/neo4j/indices.py
```

4. (Opcional) equivalencia contra el in-memory y benchmark:

```bash
.venv/bin/python data/experiment/neo4j/test_equivalencia.py
.venv/bin/python data/experiment/neo4j/benchmark_latencia.py
```

## Módulos

| Archivo | Qué hace |
|---|---|
| `conexion.py` | Driver compartido (env vars + defaults del contenedor local). |
| `cargar_kg.py` | Carga `reensamblado_v3/kg.json` (vía `load_graph_from_path`, adaptador nulo) + verificación de conteos y muestreo campo por campo. |
| `indices.py` | Índice full-text `nodos_fulltext` + tests dirigidos BKL-0003 / BKL-0027. |
| `neo4j_index.py` | `Neo4jIndex`: misma interfaz y formato que `GraphIndex` del harness, contra Neo4j. |
| `test_equivalencia.py` | 30 consultas adaptador vs in-memory (paridad exacta en ver_nodo/ver_vecinos; divergencias documentadas en buscar_nodos). |
| `benchmark_latencia.py` | Latencia con 50 consultas reales de las trazas × 50 reps × 3 backends. |

## Decisiones y su porqué

1. **Adaptador nulo del loader** (`adapter_key=None`): misma convención con
   la que la app registra `reensamblado_v3` — el loader pliega solo la
   `provenance` primaria; la lista acumulada `provenances` del JSON crudo y
   `rol_fuente` no llegan al harness (paridad de interfaz). Neo4j almacena
   exactamente la vista del loader para que la comparación con el
   `GraphIndex` sea 1:1.
2. **Modelo de datos**: label común `:Nodo` (constraint de unicidad de `id`,
   queries globales) + un label por `type` (7 tipos); relationship type =
   `relation` (16 tipos). Properties aplanadas con su nombre original (sin
   colisiones, tipos nativos) para indexación/consulta + `props_json` /
   `provenances_json` como fuente canónica de reconstrucción exacta en
   `ver_nodo`/`ver_vecinos`.
3. **`r.orden`** (posición de la arista en `kg.edges`): reproduce en
   `ver_vecinos` el orden de inserción del in-memory — Neo4j no garantiza
   orden sin `ORDER BY`; sin esto la paridad exacta sería incomprobable.
4. **Índice full-text sobre `label` + `descripcion` + `description`** con
   analyzer `spanish` (stemming + stopwords). El grafo usa AMBAS claves de
   descripción (1.863 `descripcion`, 1.101 `description`): indexar una sola
   dejaría ~25 % del grafo sin cobertura semántica. El analyzer default no
   stemmea ("asociación mutual" no matchearía "asociaciones mutuales").
5. **`nota_fuente` excluida del índice**: 2 nodos, contenido
   meta-editorial sobre la extracción ("descripcion verbatim del inciso…"),
   no contenido normativo; indexarla mete ruido léxico sin ganar
   alcanzabilidad.
6. **Paridad de payload estricta en `buscar_nodos`**: el score de Lucene NO
   se expone; `tokens_matcheados` se calcula con la fórmula del harness
   (helpers importados, no reimplementados). Un hit con `tokens_matcheados=0`
   es señal honesta de que ese nodo era inalcanzable con el índice viejo.
7. **Agregación server-side en `buscar_nodos`**: el conteo total se resuelve
   en Cypher y solo el top-K viaja al cliente. Sin esto la mediana era
   ~12.4 ms (todos los hits + `props_json` al cliente); con esto, ~1.7 ms.

## Resultados (2026-08-06, MacBook local, Docker)

- **E2 carga**: 4.469 nodos / 8.073 aristas exactos; muestreo de 20 nodos
  (seed 20260806) campo por campo: 20/20 ✓.
- **E3 alcanzabilidad**:
  - BKL-0003: "asociación mutual" y 3 variantes → nodo
    `Excepcion_…_5f95b9` en posición 1/10 en todas. Nota: en el grafo
    vigente el label de ese nodo ya fue enriquecido en capa KG
    (recuperación léxica, laudo C6), así que el índice de label+id también
    lo encuentra hoy; la mejora estructural se demostró con fragmentos
    verbatim que viven solo en la `descripcion` ("excepto que se trate de
    asociaciones mutuales…"): full-text pos 1 con 111 matches vs in-memory
    pos 5 entre 3.080 matches (los tokens "que/se/de" matchean sin señal).
    El full-text vuelve innecesario el parche de labels como mecanismo de
    alcanzabilidad.
  - BKL-0027: los 7 `miembro_de` entrantes a
    `Sujeto_rol_sujeto_obligado_proteccion` se recuperan completos con
    query dirigida (`(m)-[:miembro_de]->(rol)`) y bidireccional
    (`(rol)-[:miembro_de]-(m)`), mismo conjunto.
- **E4 equivalencia** (30 consultas): `ver_nodo` 10/10 y `ver_vecinos`
  10/10 idénticos (incluye errores de id inexistente, dirección inválida,
  hub con truncamiento >40). `buscar_nodos`: 10/10 divergen — esperado y
  deseado; detalle en `test_equivalencia_resultados.json`.
- **E5 latencia** (50 consultas reales × 50 reps, ms):

  | backend | N | mediana | p95 |
  |---|---|---|---|
  | in-memory (`GraphIndex`) | 2500 | 0.529 | 1.040 |
  | Neo4j full-text (`Neo4jIndex`) | 2500 | 2.479 | 4.199 |
  | Neo4j label exacto (RANGE) | 2500 | 0.346 | 0.777 |

  Los números de la tabla corresponden a la MISMA corrida que persistió
  `benchmark_resultados.json`. Varianza run-to-run observada: la mediana
  del full-text osciló ~±20 % entre corridas sucesivas (1.7–2.5 ms) —
  los decimales no deben sobre-interpretarse; el orden de magnitud es el
  dato. El overhead del full-text (~2 ms de mediana sobre el in-memory) es
  despreciable frente a la latencia de cada llamada LLM del agente
  (segundos). El baseline por label exacto muestra que el round-trip bolt
  no es el costo dominante.

## Limitaciones conocidas

- El `id` NO está en el índice full-text (el alcance definido fue
  label+descripcion): consultas estilo lookup ("comunicacion a 6312") que
  el in-memory resuelve 1º vía tokens del id pueden rankear más abajo
  (pos 3 en ese caso). Para la inyección conviene evaluar sumar `id` como
  campo del índice o un fallback de lookup exacto.
- El ranking de Lucene (TF-IDF/BM25 con stemming) reordena los top-10
  respecto del conteo de tokens del in-memory: `total_con_match` cambia de
  semántica (hits Lucene vs nodos con ≥1 token). Cualquier comparación de
  métricas de evaluación pre/post inyección debe tener esto presente.
- La db no persiste entre recreaciones del contenedor (decisión: el
  kg.json sellado es la fuente; recargar toma segundos).
- El benchmark corre contra localhost en la misma máquina; latencias de red
  reales serían mayores.
- `neo4j==6.2.0` (driver) quedó instalado en el `.venv` local; no hay
  requirements versionado en este directorio.

---

## Estado post-A1.1 (2026-08-17) — dos grafos, dos modos, paridad verificada

Unidad U-A1.1 (plan de tesis, carril A, bloque A1 / issue #5): infraestructura
para atacar las clases `alcanzabilidad` y `vista_no_consultada` del mapa causal
de U-A0 (`data/experiment/ev2_reporte/salida/atribucion_fallas.md` §1.a:
techo de retrieval alcanz+vista 14/7/6 para KG-Base/KG-Refinado/KG-Reextraído)
sin tocar el harness congelado. Costo de API: USD 0 (solo Docker local +
selftests determinísticos). Contexto vinculante: `docs/decision_backend_grafo.md`
(Neo4j Community adoptado; plan B SQLite FTS5 solo por laudo).

Grafos servidos (nomenclatura `docs/nomenclatura_grafos.md`; registro en
`grafos.py`, sha verificado ANTES de cada carga):

| Grafo | kg.json | sha256 | nodos / aristas | label Neo4j | índice full-text |
|---|---|---|---|---|---|
| KG-Refinado (`26fac8b4`) | `data/experiment/grafo_v2/reensamblado_v3/kg.json` | `26fac8b49f6c08c1aa364b47273d36958d831f240d4e6b4ee7700b6a0bff3571` | 4.469 / 8.073 | `:KG_Refinado` | `nodos_fulltext_kg_refinado` |
| KG-Reextraído (`8e2eadee`) | `data/experiment/reextraccion_v2/corpus_v2/salida/kg.json` | `8e2eadee57b48e00ccb51ade9a953ba1469001fe089c45d97c4307ccf2725581` | 6.178 / 11.415 | `:KG_Reextraido` | `nodos_fulltext_kg_reextraido` |

### A. Setup reproducible (comandos exactos, desde la raíz del repo)

```bash
# 0. (una vez) driver pinneado
.venv/bin/pip install -r data/experiment/neo4j/requirements.txt      # neo4j==6.2.0
# 1. contenedor (Neo4j 5.26.9 Community, puertos 7474/7687 en localhost)
docker stop neo4j-bcra-kg 2>/dev/null || true    # legacy de c26cb9b, si sigue corriendo
docker compose -f data/experiment/neo4j/docker-compose.yml up -d
docker compose -f data/experiment/neo4j/docker-compose.yml ps        # esperar "healthy"
# 2. carga determinística de los DOS grafos (verifica sha; idempotente)
.venv/bin/python data/experiment/neo4j/cargar_kg.py --verificar-idempotencia
# 3. índices full-text por grafo + tests dirigidos BKL-0003 / BKL-0027
.venv/bin/python data/experiment/neo4j/indices.py
# 4. selftest de paridad (exit 0 = todos los casos byte-idénticos donde rige)
.venv/bin/python data/experiment/neo4j/test_equivalencia.py
# 5. latencia informativa
.venv/bin/python data/experiment/neo4j/benchmark_latencia.py
```

Los volúmenes (`volumen/data`, `volumen/logs`, ~520 MB) son bind mounts
locales gitignorados en el `.gitignore` de ESTE directorio (precedente
`data/experiment/ev2_juez/.gitignore`; el `.gitignore` raíz no se toca). La
db persiste entre reinicios; borrar `volumen/` deja una db virgen que la
carga reconstruye en ~15 s desde los kg.json sellados.

### B. Decisiones de esta unidad y su porqué

1. **Un contenedor, dos grafos separados por label** (`:KG_Refinado` /
   `:KG_Reextraido`), no dos instancias. Community no tiene multi-database.
   Efecto sobre índices/constraints: (i) los ids **colisionan** entre grafos
   (682 ids en común, p. ej. `Comunicacion_a_5831`), así que la constraint de
   unicidad de `id` es **por label de grafo** (`kg_refinado_id`,
   `kg_reextraido_id`); la legacy `nodo_id` sobre `:Nodo` se elimina;
   (ii) el índice **full-text es uno por grafo**: el score BM25 de Lucene usa
   estadísticas del corpus indexado (IDF, largo medio), y un índice
   compartido con filtro por label mezclaría las estadísticas de los dos
   grafos — con índices separados cada grafo rankea exactamente como si fuera
   la única base (equivalente a dos instancias, sin dos contenedores);
   (iii) TODA query de tools filtra por el label del grafo; `:Nodo` sigue
   como label común solo para conteos globales. Aristas entre grafos: 0
   (verificado en cada carga).
2. **Vista runtime EV2 como fuente** (`grafos.cargar_vista_runtime`, import
   de `ev2_corrida/code/comun_ev2.py`): KG-Refinado vía
   `load_graph_from_path(adapter_key=None)` (idéntico a c26cb9b);
   KG-Reextraído con la provenance primaria mapeada a `{source_doc, location}`
   — es la vista exacta que vio el agente en EV2, sobre la que se midió el
   mapa causal de U-A0. Sin ese mapeo el adaptador nulo dejaría a
   KG-Reextraído sin provenances.
3. **`props_json` preserva el orden de claves del loader** (c26cb9b usaba
   `sort_keys=True`). `_short_props` del harness recorre `props.items()` en
   orden de inserción cuando el nodo no tiene description/descripcion
   (1.506 nodos en KG-Refinado, 1.944 en KG-Reextraído): con claves
   ordenadas, `resumen_propiedades` no era byte-idéntico. Hallazgo sobre el
   código de c26cb9b (el test original comparaba dicts con `==`, que ignora
   el orden, y no exigía paridad en buscar_nodos).
4. **`tokens` e `id_texto` calculados en la carga con `_tokens` importado.**
   `tokens = sorted(set(_tokens(label) + _tokens(id)))` es exactamente el
   conjunto que `GraphIndex._node_tokens` construye en memoria;
   `id_texto = " ".join(_tokens(id))`.
5. **id buscable en ambos modos — por full-text (`id_texto`), no por
   fallback exacto.** Medido: 4.412/4.469 nodos de KG-Refinado y 6.139/6.178
   de KG-Reextraído tienen tokens en el id que NO están en el label (prefijo
   de tipo y slugs largos del texto original): el id es un canal de
   recuperación real del in-memory. Indexar el `id` crudo no serviría (el
   tokenizer estándar de Lucene trata `_` como parte de la palabra:
   `Comunicacion_a_6312` sería un solo token). Un fallback exacto solo
   cubriría el id pegado entero (13 de 10.788 llamadas reales a
   `buscar_nodos` en trazas EV2+posthoc). Efecto: el ranking full-text cambia
   respecto de c26cb9b (los términos del label suelen repetirse en `id_texto`
   y ganan peso); revisable en una línea (`indices.CAMPOS_FULLTEXT`).
6. **sha256 del kg.json como propiedad del grafo cargado**: nodo
   `(:KG_Meta {grafo, nombre_canonico, kg_sha256, kg_path, commit_sellado,
   n_nodos, n_aristas, vista_runtime, version_carga})`, sin timestamps para
   que dos cargas dejen el mismo estado. Consulta:
   `MATCH (m:KG_Meta) RETURN m.grafo, m.kg_sha256, m.n_nodos, m.n_aristas`.

### C. Carga (E2 post-A1.1) — salida de `cargar_kg.py --verificar-idempotencia`

| Grafo | nodos | aristas | colgantes | KG_Meta.kg_sha256 | huella contenido loader = Neo4j | huella estado carga 1 = carga 2 |
|---|---|---|---|---|---|---|
| KG_Refinado | 4.469 ✓ | 8.073 ✓ | 0 | `26fac8b4…bff3571` ✓ | `1a796f2d…a5898` ✓ | `b250ef73…4383f` ✓ |
| KG_Reextraido | 6.178 ✓ | 11.415 ✓ | 0 | `8e2eadee…725581` ✓ | `f756e220…82c742` ✓ | `f9685fbf…9545c8` ✓ |

Muestreo campo por campo 20/20 ✓ en cada grafo (seed 20260806; compara
type/label/grafo/properties (crudo y loader, bytes y orden)/provenances/
labels Neo4j/tokens/id_texto). Una tercera carga posterior (KG_Refinado solo)
volvió a dar la huella de estado `b250ef73…`. Verificación sin recargar:
`cargar_kg.py --solo-verificar`.

### D. `Neo4jIndex(driver, grafo, modo)` — dos modos declarados

| | `modo='paridad'` (default) | `modo='fulltext'` |
|---|---|---|
| buscar_nodos | Réplica del índice léxico del harness sobre datos servidos por Neo4j: Neo4j devuelve todos los nodos con ≥1 token en común (`any(t IN n.tokens WHERE t IN $q)`); score `len(q ∩ tokens)`, orden `(-score, len(label), id)`, clamp de `limite`, `_short_props` importado — todo en Python con las mismas expresiones que `GraphIndex.buscar_nodos`. **Paridad byte-idéntica exigida.** | Índice Lucene por grafo (label + descripcion + description + id_texto, analyzer `spanish`, BM25); ranking score desc + desempate largo de label/id; score no expuesto; `tokens_matcheados` con la fórmula del harness (0 = hit solo vía descripcion). **Divergencia deliberada, no dispara freno.** |
| ver_nodo | Cypher por id (constraint por label), reconstrucción desde `props_json`/`provenances_json`. Byte-idéntico. | idéntico (mismo código) |
| ver_vecinos | Cypher por id, `ORDER BY r.orden` (posición en kg.edges), misma ventana/`n_*_total`/flags de truncado. Byte-idéntico. | idéntico (mismo código) |
| `total_con_match` | = `len(scored)` del harness (nodos con score > 0). | = cantidad de hits de `db.index.fulltext.queryNodes` **sin** opción `limit` (devuelve todos): nodos con ≥1 término de la consulta (tras stemming/stopwords) en alguno de los 4 campos. Leído del comportamiento real: consulta solo de stopwords `"de la"` → in-memory 3.065 / full-text **0** (KG-Refinado); `"que se"` → 758 / 0; `"efectivo mínimo"` → 95 / 255; `"excepto que se trate de asociaciones mutuales"` → 3.080 / 111. |
| id buscable | sí (tokens del id en `tokens`) | sí, vía `id_texto` (decisión B.5) |
| Punto de extensión | `modo='bm25_agente'` → `NotImplementedError` ("A1.2: BM25 como retriever del agente + tools v2"). No se implementa acá. | |

**Inyección por subclase** (`agente_neo4j.GraphAgentNeo4j(indice, client)`):
llama al `__init__` de `GraphAgent` con un `KnowledgeGraph` vacío y reemplaza
`self.index` por el `Neo4jIndex`; `ask`, prompt, TOOLS, MODEL, límite de
tool calls y truncado de trazas quedan idénticos. Sin API en esta unidad:
solo se prueba el despacho de `_run_tool`.

### E. Selftest de paridad — `test_equivalencia.py` (exit 0)

Criterio: byte-identidad de `json.dumps(x, ensure_ascii=False)` (la
serialización con la que `GraphAgent.ask` entrega cada output al modelo,
harness.py línea 512). Casos: heredados de c26cb9b (30, KG-Refinado) +
generados desde cada grafo (uno por type, aislado, hub máximo, borde de la
ventana de 40 por dirección, label más largo/corto, sin descripcion con ≥3
props, props list/bool, descripcion más larga, inexistente, dirección
inválida/None/mayúsculas, `limite` explícito) + buscar_nodos de borde
(empates de score, sin resultados, vacía/puntuación/espacios/stopwords, id
pegado y tokens del id, mayúsculas/acentos, numérica, sintaxis reservada de
Lucene, muy larga, `limite` 0/−3/50/51/100/"7"/"abc"/None/3.9) + respuestas
conocidas BKL-0027 y BKL-0022 + subclase.

| grafo / modo / tool | idénticos | régimen |
|---|---|---|
| KG_Refinado / paridad / ver_nodo | 26/26 | paridad |
| KG_Refinado / paridad / ver_vecinos | 34/34 | paridad |
| KG_Refinado / paridad / buscar_nodos | 50/50 | paridad |
| KG_Refinado / fulltext / ver_nodo | 26/26 | paridad |
| KG_Refinado / fulltext / ver_vecinos | 34/34 | paridad |
| KG_Refinado / fulltext / buscar_nodos | 6/50 | informativo (divergencia deliberada) |
| KG_Refinado / paridad / subclase | 16/16 | paridad |
| KG_Refinado / fulltext / subclase | 8/8 | paridad |
| KG_Reextraido / paridad / ver_nodo | 15/15 | paridad |
| KG_Reextraido / paridad / ver_vecinos | 20/20 | paridad |
| KG_Reextraido / paridad / buscar_nodos | 34/34 | paridad |
| KG_Reextraido / fulltext / ver_nodo | 15/15 | paridad |
| KG_Reextraido / fulltext / ver_vecinos | 20/20 | paridad |
| KG_Reextraido / fulltext / buscar_nodos | 6/34 | informativo (divergencia deliberada) |
| KG_Reextraido / paridad / subclase | 16/16 | paridad |
| KG_Reextraido / fulltext / subclase | 8/8 | paridad |
| **PARIDAD TOTAL** | **322/322** | fallas = 0 |

Los 6 casos full-text idénticos por grafo son los de resultado vacío
(sin resultados / vacía / puntuación / espacios) y los de un único hit
(`0f6162`, `6312`); todo lo demás diverge en total y/o ranking, como se espera.

Respuestas conocidas (KG-Refinado, ambos modos, in-memory = Neo4j byte a byte
y = valor esperado):
- **BKL-0027** (asimetría direccional): `ver_vecinos(Sujeto_rol_sujeto_obligado_proteccion, 'salientes')`
  → 0 salientes, `n_entrantes_total=168`; en `'entrantes'` los 7 `miembro_de`
  ocupan las posiciones 1–7 de la ventana de 40. ✓
- **BKL-0022** (huérfano léxico, orden-dependiente): ningún token del label
  "Entidades financieras del grupo 2" (`entidades`/`financieras`/`del`/`grupo`/`2`)
  trae al nodo al top-10; el label completo lo trae en pos 3 (in-memory y
  paridad; full-text también pos 3, total 1.247 vs 710); el nodo está en la
  posición **7** de la ventana de 40 de `ver_vecinos(Sujeto_entidad_financiera,
  'entrantes')` (145 entrantes, truncado). ✓ — Nota: la nota post-C4 del
  backlog (2026-08-02) registraba posición 6; sobre el sha vigente `26fac8b4`
  (post-C7) la posición medida es 7. Es la fragilidad que la propia nota
  describe (visibilidad dependiente del orden de `kg.edges`), no una
  discrepancia del backend: ambos backends coinciden.

Casos borde encontrados en los datos: ningún grafo tiene nodos con exactamente
39–42 aristas por dirección; los bordes medidos son el mayor grado ≤40 y el
menor >40 por dirección (KG-Refinado: 26 → no truncado / 57 → truncado
salientes; 12 / 145 entrantes. KG-Reextraído: 27 salientes; 23 / 48
entrantes; **no tiene nodos con >40 salientes** — hub máximo saliente 13 —
así que el caso `borde_out_gt40` no aplica ahí). Sin self-loops ni aristas
duplicadas en ninguno; 144 / 131 nodos aislados. **Ningún caso de no-paridad
por naturaleza del backend**: no hubo que documentar excepciones ni frenar.

Divergencias full-text (informativo, `test_equivalencia_resultados_A11.json`,
`rige_paridad=false`): totales in-memory vs full-text para las consultas
de borde en KG-Refinado — `sujeto` 105/246 (29 de los 50 hits full-text con
`tokens_matcheados=0`: stemming `sujet` sobre descripciones), `entidad
financiera` 314/1.170, `de la` 3.065/0, `Comunicacion_a_6312` 1.366/670
(mismo primer resultado), sintaxis Lucene `+efectivo -minimo …` 1.480/469 (los
símbolos se neutralizan al tokenizar), consulta muy larga 615/1.400.

### F. Latencia informativa — `benchmark_latencia.py` (solo registro)

Bloque 1 (heredado): buscar_nodos, 50 consultas reales × 50 reps, KG-Refinado (ms):

| backend | N | mediana | p95 | med.min | med.max |
|---|---|---|---|---|---|
| in-memory (GraphIndex) | 2500 | 0.511 | 1.037 | 0.379 | 1.231 |
| neo4j full-text (modo=fulltext) | 2500 | 2.714 | 5.207 | 1.011 | 4.770 |
| neo4j paridad (modo=paridad) | 2500 | 11.806 | 59.497 | 4.336 | 73.954 |
| neo4j label exacto (RANGE) | 2500 | 1.877 | 2.883 | 1.572 | 6.321 |

Bloque 2: casos del selftest × 20 reps (ms):

| grafo | tool | backend | casos | mediana | p95 | med.min | med.max |
|---|---|---|---|---|---|---|---|
| KG_Refinado | buscar_nodos | in-memory | 45 | 0.428 | 1.791 | 0.001 | 1.878 |
| KG_Refinado | buscar_nodos | neo4j paridad | 45 | 10.219 | 115.672 | 0.003 | 115.895 |
| KG_Refinado | buscar_nodos | neo4j fulltext | 45 | 2.036 | 4.525 | 0.003 | 4.688 |
| KG_Refinado | ver_nodo | in-memory | 26 | 0.001 | 0.002 | 0.001 | 0.002 |
| KG_Refinado | ver_nodo | neo4j (ambos modos) | 26 | 0.959 | 1.553 | 0.708 | 1.289 |
| KG_Refinado | ver_vecinos | in-memory | 34 | 0.006 | 0.502 | 0.000 | 0.648 |
| KG_Refinado | ver_vecinos | neo4j (ambos modos) | 34 | 4.517 | 36.896 | 0.446 | 36.212 |
| KG_Reextraido | buscar_nodos | in-memory | 34 | 0.580 | 2.617 | 0.001 | 2.659 |
| KG_Reextraido | buscar_nodos | neo4j paridad | 34 | 9.580 | 190.348 | 0.000 | 192.802 |
| KG_Reextraido | buscar_nodos | neo4j fulltext | 34 | 2.330 | 6.227 | 0.000 | 7.578 |
| KG_Reextraido | ver_nodo | in-memory | 15 | 0.001 | 0.001 | 0.001 | 0.001 |
| KG_Reextraido | ver_nodo | neo4j (ambos modos) | 15 | 0.965 | 1.905 | 0.686 | 1.857 |
| KG_Reextraido | ver_vecinos | in-memory | 20 | 0.003 | 0.496 | 0.000 | 0.510 |
| KG_Reextraido | ver_vecinos | neo4j (ambos modos) | 20 | 3.034 | 53.006 | 0.531 | 51.224 |

Registro del mecanismo (no conclusión): el máximo del modo paridad
corresponde a consultas de solo stopwords que traen miles de filas de tokens
al cliente (`de la`: 3.065 / 4.754 nodos); el de ver_vecinos, al hub máximo
(1.512 / 2.180 aristas). Los mínimos ~0 ms son las consultas que retornan
antes de tocar Neo4j (sin tokens).

### G. Qué cambia / qué no — `GraphIndex` (harness) vs `Neo4jIndex` (tabla para Metodología)

| Aspecto | GraphIndex (in-memory, harness congelado) | Neo4jIndex modo `paridad` | Neo4jIndex modo `fulltext` |
|---|---|---|---|
| Fuente de datos | `KnowledgeGraph` del loader en RAM (kg.json leído por proceso) | Neo4j (db `neo4j`, label del grafo), cargado desde la MISMA vista del loader; sha del kg.json en `KG_Meta` | ídem |
| Interfaz de tools (firmas, claves del payload, mensajes de error) | contrato original | **igual** | **igual** |
| buscar_nodos — tokenización de la consulta | `_tokens` (lowercase, sin acentos, `[a-z0-9]+`) | **igual** (`_tokens` importado) | `_tokens` importado, unido con espacios → query Lucene OR; analyzer `spanish` (stemming + stopwords) sobre los términos |
| buscar_nodos — campos indexados | label + id | **igual** (`tokens` precalculado con `_tokens`) | label + descripcion + description + id_texto |
| buscar_nodos — score / ranking | conteo de tokens comunes; orden `(-score, len(label), id)` | **igual** (calculado en Python) | BM25 de Lucene desc; desempate `(size(label), id)` en Cypher; score no expuesto |
| buscar_nodos — `total_con_match` | nodos con ≥1 token común | **igual** | hits Lucene (≥1 término tras analyzer, cualquier campo); consultas solo-stopwords → 0 |
| buscar_nodos — `tokens_matcheados` | tokens comunes label+id | **igual** | misma fórmula sobre label+id (puede ser 0) |
| buscar_nodos — `resumen_propiedades` | `_short_props(properties)` | **igual** (`_short_props` importado sobre `props_json` con orden del loader) | **igual** |
| buscar_nodos — clamp de `limite` | 1..50; no entero → 10 | **igual** | **igual** |
| ver_nodo | dict por id | **byte-idéntico** (props/provenances desde JSON canónico) | **byte-idéntico** |
| ver_vecinos | listas por orden de inserción de `kg.edges`, ventana 40, `n_*_total`, flags truncado | **byte-idéntico** (`ORDER BY r.orden`) | **byte-idéntico** |
| Grafo | uno por proceso (`GraphAgent(kg)`) | seleccionable por `grafo=` (label) | ídem |
| Latencia (mediana buscar_nodos, 50 consultas reales) | 0.5 ms | ~12 ms | ~2.7 ms |
| Inyección en el agente | `GraphAgent.__init__` crea `GraphIndex(kg)` | subclase `GraphAgentNeo4j` reemplaza `self.index` (harness sin editar) | ídem |
| Namespace de caché LLM | el vigente | sin cambio (payloads idénticos ⇒ mismas llamadas) | **requiere namespace propio** cuando se corra con API (payloads distintos) — fuera de A1.1 |
| Lo que NO cambia en ningún modo | prompt del sistema, TOOLS, MODEL, `MAX_TOOL_CALLS`, truncado de trazas, colección de provenances vistas, juez, verificador, capa determinística | | |

### H. Inventario del directorio (post-A1.1)

Commiteable (versionado): `README.md` (extendido), `docker-compose.yml`
(nuevo), `requirements.txt` (nuevo, `neo4j==6.2.0`), `.gitignore` (nuevo,
local), `grafos.py` (nuevo), `conexion.py` (sin cambios), `cargar_kg.py`
(extendido), `indices.py` (extendido), `neo4j_index.py` (extendido: modos +
grafo), `agente_neo4j.py` (nuevo), `test_equivalencia.py` (extendido),
`benchmark_latencia.py` (extendido), `test_equivalencia_resultados.json` y
`benchmark_resultados.json` (c26cb9b, intactos),
`test_equivalencia_resultados_A11.json` y `benchmark_resultados_A11.json`
(nuevos, salidas de esta unidad).
Gitignorado (local): `volumen/` (db + logs del contenedor), `dumps/`,
`__pycache__/`.

### I. Limitaciones y notas post-A1.1

- Sigue **sin inyectarse** en el pipeline de evaluación; `GraphAgentNeo4j`
  existe y su despacho está probado, pero ninguna corrida con API la usó.
- El modo `paridad` trae al cliente los tokens de todos los nodos con match
  (decisión: no delegar el orden a la collation del servidor); su latencia
  crece con consultas de stopwords. Es informativo — la unidad no optimiza.
- La db persiste en `volumen/`; el estado es reproducible desde los kg.json
  (huellas en §C). Cambiar `CAMPOS_FULLTEXT` o el analyzer exige recrear el
  índice (`DROP INDEX … ; indices.py`).
- BKL-0003 y BKL-0027 están definidos sobre KG-Refinado; en KG-Reextraído
  el nodo de BKL-0003 no existe y la relación `miembro_de` no está en su
  esquema (`indices.py` los reporta N/A, no como falla).
- El índice RANGE `nodo_label` sobre `:Nodo` (baseline del benchmark) cubre
  ambos grafos; solo se usa para el piso de round-trip.
