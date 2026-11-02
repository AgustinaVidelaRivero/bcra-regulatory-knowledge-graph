# Pre-registro — B6.0 tanda 0: test de caja negra del esquema congelado sobre cinco documentos nuevos

**FIRMADO por la autora — 2026-09-25** · Fecha: 2026-09-25 · B6.0 fase 1, primera
parte (diseño y pre-registro, sin correr) · HEAD del repo al redactar:
`d714582` (`git log -1 --format=%h`).

Este documento se escribe ANTES de correr extracción, agente o juez alguno
sobre los documentos de la tanda 0, y sin abrir el material sellado de EV2.
Las siete decisiones que lo gobiernan ya están tomadas por la autora
(asiento del 25/09/2026, `docs/plan_tesis.md:92` y `:661-664`); acá no se
re-deciden: se aplican, se verifican contra los artefactos del repo y se
dejan escritas con su comando y su salida. Todo Python de esta unidad corrió
con `PYTHONDONTWRITEBYTECODE=1`; ninguna llamada a API de modelos; gasto USD 0.
Lo que no pude verificar va marcado como NO ENCONTRADO o NO VERIFICADO, con
el motivo. Los mentores aparecen solo por rol.

Convención de nombres de este documento: los cinco documentos elegidos son el
**conjunto de la tanda 0**; los cinco TOs del subset (`pro`, `cla`, `cap`,
`ext`, `ric`) son el **conjunto de desarrollo**; los cinco no elegidos de la
lista de §4.5 son los **reservados**.

---

## A1. Objeto y alcance

La tanda 0 es un **test de caja negra del esquema congelado**
(`1be8304e3d77` / `e69feaaa…`, laudo `data/experiment/esq/laudo_esquema_congelado.md`
§4, firmado 03/09/2026, sello `2593d4d`) sobre **cinco documentos nuevos**,
con el pipeline completo **E0 a E5**, el perfil de producción **`v3_b54`**
(`data/experiment/reextraccion_v2/e1_extractor/perfil_e1.py:56,146-180`,
candados de sello `35e88c2dd0a2…` / `54a111e2175f` en `:61-64`), **los mismos
pasos y el mismo código que produjeron KG-Reextraído-r1**, y **sin anotación
manual del grafo**. Es la fila B6.0 del plan, `docs/plan_tesis.md:661`, con sus
sub-ítems `:662` (fase 1: diseño y pre-registro, sin correr) y `:663` (fase 2:
corrida y lectura, detrás del aviso al mentor).

Qué es y qué no es:

- **Es validación de diseño.** El resultado se reporta en el informe como
  validación de diseño, **no como resultado de la tesis** (`:661`, negrita
  del plan). No compite con B6.3, que sigue siendo la única evaluación final
  sobre el grafo escalado (`:671`).
- **Es caja negra.** El esquema no se toca durante la tanda; el grafo que sale
  no se anota ni se corrige a mano. Lo que la tanda revele va a la lectura de
  observaciones y vigilancias (A4) y, si corresponde, a la ventana del §7 por
  la vía de la enmienda (A8).
- **La autora lee los cinco documentos** para escribir preguntas y criterios
  sobre ellos (segunda parte de esta fase 1, posterior a este pre-registro).
  Esa lectura **no toca el esquema ni anota el grafo**: produce el material
  de evaluación, no el objeto evaluado. Las preguntas se escriben y sellan
  antes de correr (`:661`: «preguntas nuevas sobre esos 5 documentos, escritas
  y selladas antes de correr»).
- **El trabajo privado de la autora** (chequeo visual de tripletas y de aristas
  entre documentos distintos, `:664`) queda fuera del informe y no reemplaza
  a B4 ni a las observaciones (10) y (11).

---

## A2. Conjunto de la tanda 0

### A2.1 Universo y regla de elección (decisión 2)

Los cinco salen de los **diez reservados** del sorteo de ESQ-1
(`data/experiment/esq/scoping_esq1.md` §4.3 regla con semilla `20260827`,
§4.5 lista: `ctacte`, `depinv`, `lingob`, `rrci`, `polcre`, `gescre`, `pagjub`,
`retype`, `docvig`, `snp_atm`; 1.065 unidades, 301 páginas). No hay sorteo
nuevo. Regla: **ordenar los diez por unidades de extracción descendente,
desempatando por id ascendente, y tomar las posiciones 1, 3, 5, 7 y 9**. Los
otros cinco quedan reservados.

Fuente de unidades y páginas: `data/experiment/escalado_prep/inventario_unidades.csv`
(152 filas; campos `unidades_extraccion` y `paginas`; campo `veredicto`), que
es el CSV del que salen las cifras de `scoping_esq1.md` §4.5 (declarado en
§4.2: «Los 68 TOs con veredicto `digerible` de `inventario_unidades.csv`»).
Verifiqué que los diez valores del CSV coinciden uno a uno con la tabla de
§4.5 (388/86, 202/53, 139/24, 77/20, 61/32, 59/35, 52/16, 40/13, 31/14, 16/8).

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import csv
ids=['ctacte','depinv','lingob','rrci','polcre','gescre','pagjub','retype','docvig','snp_atm']
rows={r['id']:r for r in csv.DictReader(open('data/experiment/escalado_prep/inventario_unidades.csv'))}
orden=sorted(ids, key=lambda i:(-int(rows[i]['unidades_extraccion']), i))
for p,i in enumerate(orden,1):
    r=rows[i]; print(p, i, r['unidades_extraccion'], r['paginas'], r['veredicto'], 'ELEGIDO' if p%2==1 else 'reservado')
el=[i for p,i in enumerate(orden,1) if p%2==1]; res=[i for p,i in enumerate(orden,1) if p%2==0]
u=lambda L: sum(int(rows[i]['unidades_extraccion']) for i in L); pg=lambda L: sum(int(rows[i]['paginas']) for i in L)
print('elegidos', el, 'unidades', u(el), 'paginas', pg(el))
print('reservados', res, 'unidades', u(res), 'paginas', pg(res))
print('total 10', u(ids), pg(ids))
"
```

Salida:

```
1 ctacte 388 86 digerible ELEGIDO
2 depinv 202 53 digerible reservado
3 lingob 139 24 digerible ELEGIDO
4 rrci 77 20 digerible reservado
5 polcre 61 32 digerible ELEGIDO
6 gescre 59 35 digerible reservado
7 pagjub 52 16 digerible ELEGIDO
8 retype 40 13 digerible reservado
9 docvig 31 14 digerible ELEGIDO
10 snp_atm 16 8 digerible reservado
elegidos ['ctacte', 'lingob', 'polcre', 'pagjub', 'docvig'] unidades 671 paginas 172
reservados ['depinv', 'rrci', 'gescre', 'retype', 'snp_atm'] unidades 394 paginas 129
total 10 1065 301
```

No hay empates en unidades entre los diez, así que el desempate por id no
opera. Tabla de los diez ordenados (unidades y páginas del CSV; título del
campo `titulo_oficial`):

| pos. | id | unidades | páginas | título (CSV) | destino |
|--:|---|--:|--:|---|---|
| 1 | `ctacte` | 388 | 86 | Reglamentación de la cuenta corriente bancaria | **tanda 0** |
| 2 | `depinv` | 202 | 53 | Depósitos e inversiones a plazo | reservado |
| 3 | `lingob` | 139 | 24 | Lineamientos para el gobierno societario en entidades financieras. | **tanda 0** |
| 4 | `rrci` | 77 | 20 | Lineamientos para la respuesta y recuperación ante ciberincidentes (RRCI) | reservado |
| 5 | `polcre` | 61 | 32 | Política de crédito | **tanda 0** |
| 6 | `gescre` | 59 | 35 | Gestión crediticia | reservado |
| 7 | `pagjub` | 52 | 16 | Pago de beneficios de la seg. soc. por cuenta de la Adm. Nacional de la Seguridad Social (ANSES) | **tanda 0** |
| 8 | `retype` | 40 | 13 | Pago de retiros y pensiones militares | reservado |
| 9 | `docvig` | 31 | 14 | Documentos de identificación en vigencia | **tanda 0** |
| 10 | `snp_atm` | 16 | 8 | Sistema Nacional de Pagos - Cajeros automáticos | reservado |
| | **total** | **1.065** | **301** | | |

### A2.2 Lista final — conjunto de la tanda 0

| id | unidades | páginas |
|---|--:|--:|
| `ctacte` | 388 | 86 |
| `lingob` | 139 | 24 |
| `polcre` | 61 | 32 |
| `pagjub` | 52 | 16 |
| `docvig` | 31 | 14 |
| **total** | **671** | **172** |

Reservados: `depinv`, `rrci`, `gescre`, `retype`, `snp_atm` (394 unidades,
129 páginas). Comprobación de suma: 671 + 394 = 1.065 y 172 + 129 = 301.

Segunda fuente para las 671 unidades, independiente del CSV: los chunks de
E0 en seco de cada documento.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
tot=0
for to in ['ctacte','lingob','polcre','pagjub','docvig']:
    n=len(json.load(open(f'data/experiment/escalado_prep/e0_dry/{to}/chunks_{to}.json'))); tot+=n; print(to, n)
print('TOTAL', tot)"
```

Salida: `ctacte 388 · lingob 139 · polcre 61 · pagjub 52 · docvig 31 · TOTAL 671`.

### A2.3 Asertos

**Aserto 1 — ninguno de los cinco está en `documentos_excluidos_esq.json`.**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
q=sorted(x['id'] for x in json.load(open('data/experiment/esq/documentos_excluidos_esq.json'))['documentos'])
t=['ctacte','lingob','polcre','pagjub','docvig']
print('excluidos', len(q), q); print('interseccion', sorted(set(q)&set(t)))"
```

Salida: `excluidos 10 ['actgar', 'adrei', 'ayccef', 'cryl', 'ctacor', 'expaef', 'lavdin', 'opefci', 'prevmi', 'traval']` · `interseccion []`.

**Aserto 2 — ninguno es uno de los cinco TOs de desarrollo.** Los ids de
desarrollo son `pro`, `cla`, `ric`, `cap`, `ext`
(`data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json`, campo
`tos[].id`); ninguno figura en el inventario de 152 (`scoping_esq1.md` §4.2,
comando con salida `[]`), y la intersección con la lista de la tanda 0 es
vacía por inspección: `{'ctacte','lingob','polcre','pagjub','docvig'} ∩ {'pro','cla','ric','cap','ext'} = ∅`.

**Aserto 3 — los cinco tienen veredicto «digerible» en el artefacto de partición
de los 68.** El veredicto vive en `inventario_unidades.csv` (campo `veredicto`,
68 `digerible` / 84 `necesita reglas` sobre 152; `reporte_generalizacion.md:12`)
y la partición final de B5.8.4 los clasifica `reconocido_pleno` con el criterio
«S1 veredicto digerible + batería byte-idéntica vs e0_dry»
(`data/experiment/segmentacion_84/b584_particion/particion_152.json`, clave
`por_to.<id>.clase`).

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import csv, json
rows={r['id']:r['veredicto'] for r in csv.DictReader(open('data/experiment/escalado_prep/inventario_unidades.csv'))}
p=json.load(open('data/experiment/segmentacion_84/b584_particion/particion_152.json'))['por_to']
for t in ['ctacte','lingob','polcre','pagjub','docvig']: print(t, rows[t], p[t]['clase'], p[t]['unidades'], p[t]['paginas'])"
```

Salida: `ctacte digerible reconocido_pleno 388 86 · lingob digerible reconocido_pleno 139 24 · polcre digerible reconocido_pleno 61 32 · pagjub digerible reconocido_pleno 52 16 · docvig digerible reconocido_pleno 31 14`.

### A2.4 Hechos conocidos sobre los cinco que la fase 2 hereda (solo registro)

- **`docvig` es hueco del catálogo de sujetos v3**: sin entrada en
  `ROL_POR_TO_V3` (`data/experiment/b54_catalogo_v3/catalogo_sujetos_v3.md:124-126`;
  laudo `docs/laudo_B5.4_fase1_catalogo.md:20-22`: «SIN rol por defecto: sin
  entrada en `ROL_POR_TO`, con la válvula `sujeto_propuesto` abierta, y
  re-mirada en la tanda 1»). El cargador de manifiestos lo prevé: «TO sin
  entrada (huecos docvig/fimipyme y desconocidos): rol_alcance null
  obligatorio» (`data/experiment/reextraccion_v2/manifiesto_corpus.py:151-152`).
  Registro en `reporte_b584.md:147-149` (§3.f). El manifiesto de la tanda 0 lo
  declara así; no es decisión de este pre-registro.
- **`pagjub` está en la lista de excepciones de S15** (`Sujeto_rol_alcance_pagjub`,
  causa `aplanamiento_rechazado`; `data/experiment/esq_v3_miembros/esquema_v3_clases.json`,
  bloque `excepciones_s15`, 12 roles). S15 exige que la cuenta declarada
  coincida con la medida (`docs/plan_tesis.md:666`).
- **Salud de E0** (`data/experiment/segmentacion_84/b584_particion/<id>/healthcheck_<id>.json`):
  `ctacte`, `polcre`, `docvig` → `sano`; `lingob` y `pagjub` → `["cid"]` con 2
  líneas `(cid:NN)` cada uno (lingob páginas 13-14, encabezado «Versión»;
  pagjub página 1, portada). No es criterio de exclusión; se registra para la
  vigilancia (6) y para la lectura de incidencias.
- Los cinco son de categoría `normativa_general` (CSV, campo `categoria`): la
  tanda 0 no testea la familia de régimen informativo (límite ya declarado en
  `scoping_esq1.md` §4.2).

### A2.5 Salvedad de la fe de erratas, textual

`data/experiment/esq/fe_erratas_laudo_esquema_congelado_virgenes.md`, §3
(líneas 114-127), fija de qué son vírgenes los documentos elegidos fuera de
los diez de ESQ-2 y de qué no lo son:

> **ESQUEMA** (tipos, predicados, enum de `Obligacion.tipo`) — **Depende de la
> elección de los 20, y es alcanzable**: el esquema quedó informado por 15
> documentos (5 de desarrollo + 10 de ESQ-2). […] Si los 20 se eligen entre esos
> 58, el adjetivo es cierto en esta dimensión.
>
> **CATÁLOGO DE SUJETOS v3** — **NO, y no hay elección que lo arregle**: los 68
> digeribles […] tienen cada uno su pasaje de alcance leído y su entrada escrita
> a partir de esa lectura. No queda material digerible virgen para el catálogo.
>
> En una línea: **la tanda 1 puede ser test de generalización del esquema, si
> los 20 se eligen fuera de los diez de ESQ-2; no puede ser test de
> generalización del catálogo de sujetos, se elija como se elija.**

Aplicado a la tanda 0: los cinco elegidos **son vírgenes respecto del esquema
congelado** (no son ninguno de los diez de ESQ-2, aserto 1, ni de los cinco de
desarrollo, aserto 2) y **no son vírgenes respecto del catálogo de sujetos
v3**, que se escribió leyendo el pasaje de alcance de los 68 digeribles
(`tabla_to_rol_post_f1.md`, filas 15, 20, 37, 41 y 45 para los cinco). Las
vigilancias (7), (8) y (9) miden por lo tanto el catálogo sobre material que lo
informó, como la fe de erratas §4.2 ya declara para la tanda 1.

---

## A3. Grafo de desarrollo re-extraído y las cuatro celdas de EV2

### A3.1 Decisión 3, completa

La misma corrida de la tanda 0 **re-extrae los cinco TOs de desarrollo**
(`pro`, `cla`, `cap`, `ext`, `ric`) con el esquema congelado y el perfil
`v3_b54`. Sus unidades son **1.763**, recontadas sobre los chunks sellados de
E0 con la enmienda 01:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
b='data/experiment/reextraccion_v2/e0_chunking/salida_enm01'
n={t:len(json.load(open(f'{b}/chunks_{t}.json'))) for t in ['pro','cla','cap','ext','ric']}
print(n, sum(n.values()))"
```

Salida: `{'pro': 101, 'cla': 143, 'cap': 462, 'ext': 973, 'ric': 84} 1763`
(misma cifra en `escalado_prep/resumen_escalado.md:48` y en
`docs/nomenclatura_grafos.md:134`).

Sobre **EV2** (40 preguntas, 164 criterios; `data/experiment/exploracion/ev2_fidelidad/preguntas_ev2_fidelidad.json`,
sha256 `1d58733699c325c90510e1ead5f18eac6c3cd970ee3b0ab7ff141da539162b40`
verificado con `shasum -a 256`; conteo `40` preguntas y `164` criterios en
`gold.criterios`) se pre-registran **cuatro celdas, una medición cada una,
todas declaradas acá antes de mirar ninguna**:

| celda | grafo | índice de texto | agente | juez EV2 | estado |
|---|---|---|---|---|---|
| C1 | KG-Reextraído-r1 (`0226e947…`, esquema v2) | `GraphIndex` en memoria (`harness.py:148-162`) | harness congelado, firma v1 | v1 `fd446f8e…`, N=3, voto modal | **SELLADA** — commit `774acac`; tabla 6 / 26 / 8 (`ev2_r1/cierre/reporte_final_r1.md:12`). No se re-corre: sus cifras se **agregan**. |
| C2 | KG-Reextraído-r1 (`0226e947…`, esquema v2) | Neo4j fulltext (`nodos_fulltext_kg_reextraido_r1`) | harness congelado, firma v1, sobre `GraphAgentNeo4j` modo `fulltext` | v1 `fd446f8e…`, N=3, voto modal | **A CORRER** |
| C3 | desarrollo re-extraído con el congelado (5 TOs, 1.763 unidades) | `GraphIndex` en memoria | harness congelado, firma v1 | v1 `fd446f8e…`, N=3, voto modal | **A CORRER** |
| C4 | desarrollo re-extraído con el congelado (5 TOs, 1.763 unidades) | Neo4j fulltext (índice nuevo por grafo) | harness congelado, firma v1, sobre `GraphAgentNeo4j` modo `fulltext` | v1 `fd446f8e…`, N=3, voto modal | **A CORRER** |

Componentes fijos en las cuatro celdas:

- **Agente**: el harness congelado del principio 8 —
  `data/experiment/evaluacion/harness.py` (sha256 `fd267e83…`, último commit
  `7e8b91e`), modelo `claude-haiku-4-5-20251001` (`:47`), temperatura 0
  (`:48`), tope de 15 llamadas a herramientas (`:50`), **firma v1 de sus tres
  herramientas** `buscar_nodos` / `ver_nodo` / `ver_vecinos` (`TOOLS`,
  `:240-271`). En C2 y C4 corre sobre `GraphAgentNeo4j`
  (`data/experiment/neo4j/agente_neo4j.py:56`, subclase de `GraphAgent`; la
  inyección es el único punto de contacto con el harness, `:64-65`) en modo
  `fulltext`, tal como lo sirve la app según el laudo A1.6 §3
  (`docs/laudo_promocion_backend.md:60-62`; `app/main.py:351-356`). **Las
  tools v2 de A1.2 no se usan** (laudo A1.6:47-51: «NO se promueven como
  default»; la bidireccionalidad de `ver_vecinos` queda como capacidad del
  backend, no entra en ninguna medición sin declararse como variable).
- **Juez**: el juez v1 congelado de EV2, prompt
  `data/experiment/ev2_juez/prompt_juez_v1.md` (sha256
  `fd446f8e61f46033d7de9b862121c698b2c52dcc2696b7f10993f44e509f5455`,
  verificado), `juez.py` (`claude-sonnet-4-6`, `:37`; temperatura 0.0, `:38`),
  **tres corridas por respuesta y voto modal** por criterio, mapping fijo §2 a
  veredicto de pregunta (`mapping.py:40-54`: `requiere_adjudicacion` si algún
  modal es `dudoso`/`sin_consenso`; `correcto` si todos `cumplido`;
  `incorrecto` si todos `no_cumplido`; `parcial` en el resto), mediante el
  pipeline ciego de la corrida base (`ev2_fidelidad_eval/code/pipeline_fidelidad.py`,
  `b624865`) sin editar. Mismo protocolo que C1 (`ev2_r1/preregistro_ev2_r1.md`
  §1 y §4), incluido el encadenamiento §7 y la adjudicación ciega.
- **Set**: las 40 preguntas / 164 criterios de fidelidad; el eje de
  navegabilidad no se corre.

**Ninguna celda se repite.** C1 está sellada y no se re-corre (principio 8:
«Nada sellado se re-corre para reemplazarse»). C2, C3 y C4 se corren **una vez
cada una**; si una corrida se corta por causa técnica, la retoma sigue el
precedente de r1 (`docs/plan_tesis.md:305`: recuperación declarada como
desvío, con evidencia), nunca una segunda medición.

### A3.2 Configuración de Neo4j, sellada por su definición

- Índice full-text por grafo sobre los campos `indices.CAMPOS_FULLTEXT`:

  `data/experiment/neo4j/indices.py:77-78`:
  ```python
  CAMPOS_FULLTEXT = ["label", "descripcion", "description", "id_texto"]
  ANALYZER = "spanish"
  ```
- Analizador `spanish` (stemming + stopwords castellanas de Lucene,
  `indices.py:35-37`); similitud **BM25 por defecto de Lucene** (constantes no
  fijadas en el código: `docs/plan_tesis.md:747` las declara «no verificadas»
  y así lo repito acá). Comportamiento del modo `fulltext` leído del código:
  `neo4j_index.py:32-55` (query OR entre términos tokenizados, `queryNodes`
  sin `limit`, ranking score desc con desempate por largo de label e id, score
  no expuesto, `tokens_matcheados` con la fórmula del harness). Servidor
  `neo4j:5.26.9-community` (`data/experiment/neo4j/docker-compose.yml:34`;
  contenedor `Up` y `healthy` al redactar, `docker ps --filter name=neo4j`).
- Es la **elección tomada en el laudo A1.6 sobre material propio**
  (`docs/laudo_promocion_backend.md` §1-§2: ablación factorial `68c79dc`/`ffc6ff6`
  de 400 trazas sobre KG-Refinado, «Configuración que se promueve: la sellada
  en el pre-registro de la ablación»). No se ajusta mirando EV2 (laudo A1.6
  §4; principio 7).
- **Advertencia del README de Neo4j sobre `id_texto` y el ranking**, transcrita
  de `data/experiment/neo4j/README.md:257-259` (el mandato la ubica en
  `:257-260`; la línea 260 ya abre el ítem 6, «sha256 del kg.json como
  propiedad del grafo cargado»):

  > `buscar_nodos` en trazas EV2+posthoc). Efecto: el ranking full-text cambia
  > respecto de c26cb9b (los términos del label suelen repetirse en `id_texto`
  > y ganan peso); revisable en una línea (`indices.CAMPOS_FULLTEXT`).

  Contexto de las líneas anteriores (`:250-256`): el id es un canal de
  recuperación real del índice en memoria (6.139/6.178 nodos de KG-Reextraído
  con tokens en el id que no están en el label), indexar el id crudo no
  serviría por la tokenización de `_` en Lucene, y por eso se indexa
  `id_texto` = `" ".join(_tokens(id))` calculado en la carga
  (`cargar_kg.py`, docstring). La definición vigente es la de
  `indices.py:77-78` citada arriba; el índice de r1 se llama
  `nodos_fulltext_kg_reextraido_r1` (`grafos.py:80`).

### A3.3 Qué compara cada par de celdas, y en qué se aparta de EV2-r1

Este pre-registro **compara esquema y retriever a la vez**, y lo dice así, en
contraste explícito con `data/experiment/ev2_r1/preregistro_ev2_r1.md:25-33`,
que declaraba:

> Rige el principio 7: r1 se mide sobre EV2 UNA sola vez […]
> **NO ES** una comparación de retrievers (harness congelado, índice booleano
> in-memory, mismas condiciones que la corrida base: la única variable es el
> grafo); **NO** corrige nada de r1 (principio 9: lo que falle va a r2); **NO**
> re-mide KG-Base / KG-Refinado / KG-Reextraído (sus tablas están selladas en
> `64de678` / `40603a9` / `85d9fdb` y se citan).

Acá, en cambio, hay dos variables y cada par aísla una:

| par | variable aislada | lo demás, fijo |
|---|---|---|
| C1 vs C2 | índice de texto (memoria vs Neo4j fulltext) | grafo r1, agente, juez |
| C3 vs C4 | índice de texto | grafo de desarrollo re-extraído, agente, juez |
| C1 vs C3 | esquema (v2 → congelado, mismo pipeline E0-E5) | índice en memoria, agente, juez |
| C2 vs C4 | esquema | índice Neo4j fulltext, agente, juez |

Ninguna tabla cruza C1-C4 con resultados del banco Claude Code + MCP
(principio 8b). Cada tabla de resultados declara qué índice usó
(`docs/plan_tesis.md:747`, vigilancia de la escritura).

### A3.4 Uso único de EV2 (principio 7) y multiplicidad

Las tres celdas nuevas (C2, C3, C4) cuentan **cada una como uso único de EV2**
bajo el principio 7, con el precedente de A1.5, A2.3 y A3.1
(`docs/plan_tesis.md:265`, `:277`, `:289`). Nada de lo que salga de C2-C4 se
usa para ajustar componente alguno y volver a medir en EV2.

Transcripción de los principios y la nota, `docs/plan_tesis.md`:

> **:209-212 — 7.** EV2 es examen, no set de desarrollo: cada sistema o
> configuración nueva se evalúa sobre EV2 UNA sola vez, con pre-registro
> sellado previo; ningún componente se ajusta mirando resultados de EV2 para
> volver a medirse en EV2. Las iteraciones de desarrollo usan material propio
> (pares sintéticos nuevos, preguntas frescas tipo U6), nunca el examen.

> **:213-219 — 8. Dos instrumentos, declarados y no intercambiables.** (a) el
> **harness congelado** (Haiku 4.5, 3 tools, 15 tool calls, juez v2.1.1)
> sostiene todo lo sellado — Fase 2.3, escalón 1/1b, EV2, A1.4; (b) el **banco
> Claude Code + MCP** (A2.0-gate → A2.0-banco) sostiene el head-to-head, donde
> la validez viene de que **los dos brazos comparten la misma caja negra**. Los
> resultados de un instrumento **no se cruzan** con los del otro en una misma
> tabla; el puente entre ambos es A1.7, medido con material propio. Nada
> sellado se re-corre para reemplazarse: los resultados nuevos se **agregan**,
> nunca sustituyen.

> **:286 — Nota de multiplicidad:** con 40 preguntas y varios brazos, las
> diferencias de 1–3 preguntas **no se leen como señal** — se reportan con IC y
> se dice explícitamente cuándo el n no alcanza.

Aplicación: **con n = 40 y cuatro celdas, las diferencias de 1 a 3 preguntas
entre celdas no se leen como señal y se reportan con intervalo** (el mismo
formato de lectura de `ev2_r1/preregistro_ev2_r1.md` §7: una fila por
comparación, número observado, intervalo, y la frase explícita de si el n
alcanza). No hay predicción de superioridad de ninguna celda sobre otra en
este documento.

### A3.5 Supuestos sobre la composición de los grafos (a fijar en el mandato de fase 2; no se deciden acá)

Dos requisitos se desprenden de las decisiones y los dejo escritos como
supuestos, porque las decisiones no los nombran y la mecánica es del mandato
de fase 2:

1. **El grafo de C3 y C4 contiene solo los cinco TOs de desarrollo**, ensamblado
   con el mismo inventario que r1. Si se ensamblara junto con los cinco de la
   tanda 0, cambiarían el espacio de búsqueda del agente y las estadísticas de
   corpus del índice BM25 (`indices.py:39-40`), y el par C1 vs C3 dejaría de
   aislar el esquema.
2. **La observación (11) de A4 necesita un ensamblado cuyo inventario de
   remisiones incluya los diez TOs** (cinco de desarrollo + cinco de la tanda
   0): «cuántas de esas 106 pasan a resolverse al entrar sus normas al
   inventario» (`docs/plan_tesis.md:669`) solo se puede medir si las normas
   entran al inventario. Cómo se materializa (un ensamblado de diez para la
   lectura de (11) además de los dos de cinco, u otra mecánica) lo fija el
   mandato de fase 2 sobre el cableado de r1 en `ensamblar_corpus.py` (A5).

Decisión de la autora (25/09/2026): una sola extracción y tres ensamblados
determinísticos. C3 y C4 se corren sobre el ensamblado de los cinco TOs de
desarrollo solos; la observación (10) de la tanda 0 se lee sobre el ensamblado
de la tanda 0 sola; la observación (11) y las preguntas nuevas sobre los cinco se
corren sobre el ensamblado de los diez TOs.

---

## A4. Predicciones, escritas antes de correr, con línea de base y fuente

Rige la decisión 6: las observaciones (10) y (11) y las vigilancias (1) a (9)
**se miden contra sus líneas de base, sin umbral**; el único criterio de
retiro es el principio de gobierno del laudo congelado §1 («Se retira lo que
produce falsedad en campo estructurado en material fresco; se acepta con
residuo declarado lo que produce omisión visible o error con tasa medida y
balance favorable»). Las bandas que escribo abajo son **ayudas de lectura
pre-declaradas**, no umbrales: una observación fuera de banda es un hecho a
explicar en el reporte, no un retiro.

### A4.1 Observación (10) — relaciones de extracción por unidad

**Línea de base** (`docs/plan_tesis.md:669`), recomputada sobre
`data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json` (sha256
`0226e9477baee02d772bbfecee78a49441b189d0e0512ca5e22956dfb084196a`,
`shasum -a 256`):

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
E=json.load(open('data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json'))['edges']
rf=lambda e: e.get('rol_fuente') or (e.get('provenance') or {}).get('rol_fuente')
tot=len(E); ref=sum(e['relation']=='referencia' for e in E); esq=sum(rf(e)=='esqueleto' for e in E); ps=sum(e['relation']=='padre_sugerido' for e in E)
ext=tot-ref-esq
print('total',tot,'referencia',ref,'esqueleto',esq,'padre_sugerido',ps)
print('extraccion',ext,'por unidad',round(ext/1763,2),'| sin padre_sugerido',ext-ps,round((ext-ps)/1763,2))"
```

Salida: `total 17772 referencia 5680 esqueleto 82 padre_sugerido 41` ·
`extraccion 12010 por unidad 6.81 | sin padre_sugerido 11969 6.79`.

Es decir: **17.772 − 5.680 − 82 = 12.010 aristas de extracción, 6,81 por unidad
sobre 1.763** (11.969 y 6,79 sin las 41 `padre_sugerido` de cuarentena). La
cifra 11.509 que circuló en la mesa no es de aristas del grafo y no se usa
(`:669`).

**Nota sobre la comparabilidad**: la línea de base es del **esquema v2** sobre
los TOs de desarrollo; el congelado tiene **13 predicados** (los 12 de
producción + `condicion_de`) y **9 tipos** (los 6 de producción + `Potestad`,
`Condicion`, `Definicion`) (`laudo_esquema_congelado.md:106-108`), más la
regla 9 de omisión de contenido meta-normativo y el retiro de
`requisito_de_estructura` (que se normaliza a «otra», no borra aristas:
`validador_e1.py:109-111`). La comparación es orientativa, como el plan la
declara.

**Predicciones (10):**

| objeto | métrica | línea de base | predicción |
|---|---|---|---|
| desarrollo re-extraído con el congelado (1.763 unidades) | aristas de extracción / unidad (misma resta: total − `referencia` − `rol_fuente=esqueleto`) | 6,81 (r1, esquema v2) | **igual o mayor que la base**: 6,81 a 8,0. Tres tipos y un predicado nuevos abren canales de emisión; la regla 9 y R4 solo restan en unidades meta-normativas (minoritarias). Menos de 6,0 sería vaciamiento sistemático a leer con la vigilancia (2). |
| conjunto de la tanda 0 (671 unidades) | aristas de extracción / unidad | 6,81 (misma base, distinta composición) | **banda ancha, 5,0 a 8,0**, declarada ancha porque `ctacte` aporta 388 de 671 unidades (58 %) y es reglamentación operativa densa, sin precedente medido bajo este esquema. No hay cifra de relaciones por unidad bajo el congelado en ESQ-2/ESQ-3b (grep «por unidad» en `data/experiment/esq/` sin resultado aplicable: NO ENCONTRADO). |

Fuente de la métrica en la fase 2: el `kg.json` de cada ensamblado, con el
mismo comando de arriba y el denominador de unidades de A2.2 y A3.1.

### A4.2 Observación (11) — aristas entre documentos distintos y remisiones «fuera del subset»

**Línea de base** (`docs/plan_tesis.md:669`), recomputada sobre
`data/experiment/reextraccion_v2/corpus_v2/salida_r1/reporte_ensamblado_r1.json`
→ clave `referencias`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
r=json.load(open('data/experiment/reextraccion_v2/corpus_v2/salida_r1/reporte_ensamblado_r1.json'))['referencias']
print({k:r[k] for k in ('menciones','resueltas','parciales','irresolubles','aristas_referencia_nuevas','aristas_cross_to')})
print('fuera del inventario', r['irresolubles_por_motivo']['norma fuera del inventario del subset'], 'normas', len(r['normas_fuera_inventario']), 'suma', sum(r['normas_fuera_inventario'].values()))"
```

Salida: `{'menciones': 1089, 'resueltas': 837, 'parciales': 20, 'irresolubles': 252, 'aristas_referencia_nuevas': 5645, 'aristas_cross_to': 188}` ·
`fuera del inventario 106 normas 54 suma 106`.

Es decir: **`aristas_cross_to` = 188**; 1.089 menciones = 837 resueltas (20
parciales) + 252 irresolubles; **106 con motivo «norma fuera del inventario
del subset» sobre 54 normas distintas**.

**Cruce de las 106 contra los cinco documentos elegidos**, por título
normalizado (sin tildes, minúsculas) sobre las claves de
`normas_fuera_inventario`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json, unicodedata
norm=lambda s: ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c)!='Mn')
nf=json.load(open('data/experiment/reextraccion_v2/corpus_v2/salida_r1/reporte_ensamblado_r1.json'))['referencias']['normas_fuera_inventario']
claves={'ctacte':['cuenta corriente'],'lingob':['gobierno societario'],'polcre':['politica de credito'],'pagjub':['seguridad social','anses','pago de beneficios'],'docvig':['documentos de identificacion']}
tot=0
for to,ks in claves.items():
    h=[(k,v) for k,v in nf.items() if any(x in norm(k) for x in ks)]; s=sum(v for _,v in h); tot+=s; print(to, s, h)
print('TOTAL', tot, 'de', sum(nf.values()))
for to,ks in {'depinv':['depositos e inversiones a plazo'],'rrci':['ciberincidentes'],'gescre':['gestion crediticia'],'retype':['retiros y pensiones'],'snp_atm':['cajeros']}.items():
    print('(reservado)', to, sum(v for k,v in nf.items() if any(x in norm(k) for x in ks)))"
```

Salida:

```
ctacte 0 []
lingob 0 []
polcre 2 [('politica de credito', 1), ('politica de credito, segun corresponda', 1)]
pagjub 0 []
docvig 2 [('documentos de identificacion en vigencia', 2)]
TOTAL 4 de 106
(reservado) depinv 1
(reservado) rrci 0
(reservado) gescre 5
(reservado) retype 0
(reservado) snp_atm 0
```

Cruce, tabla:

| documento de la tanda 0 | menciones de las 106 que lo nombran | claves matcheadas |
|---|--:|---|
| `ctacte` | 0 | — |
| `lingob` | 0 | — |
| `polcre` | 2 | «politica de credito» (1), «politica de credito, segun corresponda» (1) |
| `pagjub` | 0 | — |
| `docvig` | 2 | «documentos de identificacion en vigencia» (2) |
| **total** | **4** | de 106 (54 normas) |

(Informativo, no predicción: los reservados suman 6 — `gescre` 5, `depinv` 1;
la regla de elección no miraba este cruce.)

**Predicciones (11):**

| métrica | línea de base | predicción |
|---|---|---|
| menciones «fuera del inventario» que pasan a resolverse al entrar los cinco al inventario | 0 de 106 (r1, inventario de 5 TOs) | **4 de 106** (las 2 de `polcre` y las 2 de `docvig`), bajo el mismo resolutor de r1 (`r1_referencias.py`) y con la salvedad del supuesto 2 de A3.5. Cuántas de las 4 resuelven a nodo (no a TextoOrdenado) depende de que el punto citado exista en E0 del destino; no lo predigo. |
| `aristas_cross_to` en el ensamblado que incluye los diez TOs | 188 (5 TOs de desarrollo) | **mayor que 188**: al menos 188 + 4 si las cuatro resuelven, más las remisiones entre los cinco nuevos y hacia los cinco de desarrollo, que no censé (no hay E1 de los cinco). No fijo cifra: es la primera medición de remisiones de estos documentos. |
| `aristas_cross_to` en el grafo de desarrollo re-extraído (5 TOs) | 188 | **188 ± 20** (mismo inventario, mismo resolutor; varía solo por lo que el esquema congelado emita distinto en las unidades que remiten). |

Sin umbral: si un conteo no sube, es observación a explicar, no retiro
(`:669`).

### A4.3 Vigilancias (1) a (9) de B6.1 — líneas de base y fuentes

Las vigilancias se declaran en `docs/plan_tesis.md:665` y en el laudo
congelado §7 (`laudo_esquema_congelado.md:178-187`, ítems 1-5) más los laudos
de B5.4 (ítems 6-9). Se miden en la tanda 0 contra estas líneas de base, sin
umbral; el muestreo, donde hace falta, lo fija el mandato de fase 2.

| # | vigilancia | línea de base | fuente | instrumento en la tanda 0 |
|--:|---|---|---|---|
| 1 | Migraciones tipo-Condicion contra la guarda de modalidad (deber explícito emitido como `Condicion`) | 1/12 en fresca (balance 1-1) | `laudo_esquema_congelado.md:97` (§3, fila «Migración de modalidad a Condicion»); §2 R2 `:38-41` | muestreo de `Condicion` a definir en fase 2 |
| 2 | Conteo de vaciamientos (unidad con extracción vacía cuyo texto porta contenido normativo) | v1: 2/43 · v2: 2/27 (+1 declarada +1 simétrica) | `laudo_esquema_congelado.md:94` (§3) | unidades con 0 relaciones aceptadas en `extracciones_e1.jsonl` × lectura de muestra |
| 3 | Duplicación de contenido entre cajas (mismo pasaje en ≥ 2 nodos) | 5 casos v1; persiste en el ancla de P8 | `laudo_esquema_congelado.md:96` (§3) | muestreo a definir en fase 2 |
| 4 | Rótulos de TO: unificación de nodos TO solo por identidad documental (archivo/id), nunca por rótulo | 2 archivos afectados en lecturas | `laudo_esquema_congelado.md:99` (§3); regla que B5 hereda (`:183-185`) | conteo de nodos `TextoOrdenado` por archivo en el `kg.json`: debe ser 1 por TO |
| 5 | Emisiones residuales de vocabulario retirado (`requisito_de_estructura`) | 0 por construcción | `laudo_esquema_congelado.md:186-187`; contador `tipo_obligacion_requisito_de_estructura` (`validador_e1.py:131-132`, fluye al resumen de corrida `runner_corpus.py:557-559`, U-CABLE-V3 `d61c491`) | el contador del resumen de corrida; debe ser 0 |
| 6 | Unidades propias vacías (sección del índice del PDF sin unidad E0) | **SIN LÍNEA DE BASE numérica**: caso testigo «Entidades alcanzadas» de `fimipyme`; tasa nunca medida | `docs/plan_tesis.md:665` (agregada por laudo B5.4-f1, `docs/laudo_B5.4_fase1_catalogo.md:95-99`) | `healthcheck_e0.py` (B5.2) sobre los cinco; hoy los cinco tienen `avisos_pagina_cuerpo_sin_seccion` = 0 y `cobertura_no_exacta` = None (A2.4) |
| 7 | Roles de alcance en `ejecuta` sin apoyo textual (tasa) | **SIN LÍNEA DE BASE como tasa**: n = 1 (`cryl::1.3`, `rol_alcance_cryl` en `ejecuta`) en la muestra pareada de B5.4 | `docs/laudo_B5.4_cierre_catalogo.md:64-80` (H2; resolución (a)+(c)) | tasa sobre las aristas `ejecuta` cuyo sujeto es un `Sujeto_rol_alcance_<to>`, muestreo a definir |
| 8 | Tasa de `sujeto_propuesto` contra la base 3,1 % | **3,1 %** = 124 / (3.905 + 124) = 124 / 4.029 relaciones con sujeto (`round(124/4029*100,2)` → 3,08) | `data/experiment/esq/cobertura/frecuencia_sujetos_suj_freq.md:120` (U-SUJ-FREQ); `laudo_B5.4_cierre_catalogo.md:89-98` | conteo de `sujeto_propuesto` vs `sujeto_id` en las relaciones aceptadas de E1; el umbral que el laudo pide para B6.1 **no se fija acá** (decisión 6: sin umbral) |
| 9 | Emisiones de `entidad_originante_de_transferencia` fuera del dominio de pagos | **SIN LÍNEA DE BASE como tasa**: 13 menciones / 5 TOs del id `originante` en el censo de adiciones de fase 1; 2→1 emisiones en la unidad adversarial | `docs/laudo_B5.4_cierre_catalogo.md:155-164` (R1 = residuo + vigilancia (9)) | muestreo de las emisiones de ese id en los diez TOs; ninguno de los cinco de la tanda 0 es del dominio de pagos (`pagjub` es pago de beneficios por cuenta de ANSES, no transferencias) |

---

## A5. Instrumentos, con su estado real hoy

Regla: **la fase 2 no arranca con instrumentos PENDIENTES.** Cada PENDIENTE
de esta tabla es un gate técnico de A9 que se cierra por su unidad del plan o
por el mandato de fase 2, y se reporta cerrado antes del ok de la autora.

| instrumento | ruta | commit / sha | estado | cómo lo verifiqué |
|---|---|---|---|---|
| Shapes con perfil congelado (B2.2 fase 2) | `scripts/shapes_validator.py` (v0) | `b01eb18` · sha256 `d226f19c…` | **PENDIENTE (B2.2 fase 2, `docs/plan_tesis.md:317`)**: v0 exige provenance `{source_doc, location}` (`:138-140`, S4) que la generación 3 no emite; no codifica el esquema congelado (9/13/26 pares). Mandato de fase 2 redactado como borrador, no despachado. | `grep -n "perfil\|source_doc" scripts/shapes_validator.py` → sin opción `--perfil`; 9 ocurrencias de `source_doc` |
| Regression suite (B2.1 fase 2) | `scripts/regression_kg.py` (nombre que da el plan) | — | **NO ENCONTRADO → PENDIENTE (B2.1 fase 2, `:315`)**: mandato de fase 2 redactado como borrador, no despachado. | `ls scripts/regression_kg.py` → `No such file or directory`; `ls scripts/` no lista ninguna suite |
| Cableado de r1 en `ensamblar_corpus.py` («la tanda pasa por r1») | `data/experiment/reextraccion_v2/corpus_v2/ensamblar_corpus.py` | `b01eb18` · sha256 `7e5d190e…` | **PENDIENTE (checklist del gate, `:668`)**: los pasos de r1 (E4 determinístico, `padre_sugerido`, referencias nodo→nodo, provenance rica) viven en `ensamblar_r1.py` (`185e042`) y sus módulos `r1_*`; `ensamblar_corpus.py` no los importa. Mecánica a fijar en el mandato de fase 2. | `grep -n "^from\|^import" ensamblar_corpus.py` → importa `manifiesto_corpus`, ningún `r1_*`; `grep -n "r1_" ensamblar_corpus.py` → solo menciones en docstring («replica el patrón de r1_e5_esqueleto») |
| Esqueleto v3 + S15 | `ensamblar_corpus.py:70,83-140,290-352` (inyección condicional a `perfil_e1: "v3_b54"`); `data/experiment/esq_v3_miembros/esquema_v3_clases.json` (12 excepciones); S15 en `shapes_validator.py:397-457` | `b01eb18` · json sha256 `dad88cc9…` | **DISPONIBLE** (U-ESQ-V3, `:666`). Nota: S15 corre dentro de `shapes_validator.py` v0, cuyas S4-S6 fallan sobre gen 3; el gate de S15 debe leerse aparte hasta que exista el perfil de B2.2. | `python3 scripts/shapes_validator.py --help` lista `--excepciones`; `ORDEN_SHAPES` `:89` |
| Intrínsecas | `scripts/metricas_intrinsecas.py`; salidas `data/experiment/metricas_intrinsecas/{grafo_v2,reensamblado_v3,run_3_ppf_core}.json` | `c6f808e` · sha256 `d5a88b79…` | **PENDIENTE de extensión**: el script está cableado a tres grafos de generaciones 1 y 2 (`:28`, `:64-66`) con custodia por re-ensamblado (`assemble.py`/`assemble_v3.py`); no hay medición intrínseca de r1 ni soporte de gen 3. | `grep -l "0226e947\|salida_r1" data/experiment/metricas_intrinsecas/*` → vacío |
| Indicadores de cita (U-CITA-2) | `scripts/ucita2_indicadores.py`; `reports/ucita2_indicadores.{md,json}` | `fb6ef69` · sha256 `bdd00cf7…` | **DISPONIBLE sobre r1, PENDIENTE de parametrización**: `TANDAS` cableadas a `ev2_r1_*` (`:78`) con sha de trazas esperados (`:94`); para C2-C4 y para las preguntas de los cinco hace falta apuntarlo a otras trazas y otro índice E0. Línea de base r1 base (N=40): cita fundada 38/40, cita existente 40/40, cita al ancla 32/40 (`reports/ucita2_indicadores.json` → `agregados.ev2_r1_base.todas`). | `grep -c ev2_r1 scripts/ucita2_indicadores.py` → 17 |
| Atribución A0.2 | `data/experiment/ev2_reporte/regla_atribucion.md` | **`40603a9`** · sha256 `20040e94…` | **DISPONIBLE** (regla sellada; aplicada a r1 en `774acac` con replay 40/40 + 71/71). Para C3/C4 el censo de anclas corre sobre el grafo nuevo con la misma regla (`resolucion.AnclaIndex`, match exacto, contenedores > 10 excluidos). | `git log -1 -- data/experiment/ev2_reporte/regla_atribucion.md` → `40603a9 2026-08-17` |
| Juez EV2 | `data/experiment/ev2_juez/{prompt_juez_v1.md,juez.py,mapping.py}`; pipeline `ev2_fidelidad_eval/code/pipeline_fidelidad.py` | `1a0ac5c` · prompt sha256 **`fd446f8e…`** (verificado) · pipeline `b624865` | **DISPONIBLE** | `shasum -a 256 data/experiment/ev2_juez/prompt_juez_v1.md` |
| Harness congelado (agente, firma v1) | `data/experiment/evaluacion/harness.py` (+ `loader`, `judge`, `llm_cache`) | `7e8b91e` · sha256 `fd267e83…` | **DISPONIBLE** (cuarteto hasheado; no se edita) | `grep -n "MODEL\|TEMPERATURE\|MAX_TOOL_CALLS" harness.py` → `:47-50` |
| `GraphAgentNeo4j` en modo fulltext | `data/experiment/neo4j/agente_neo4j.py:56`; `neo4j_index.py` modos `paridad`/`fulltext` | `9e131bf` · sha256 `403a9b42…` / `5f38db1b…` | **DISPONIBLE como clase**; **PENDIENTE el runner de EV2 que la instancie**: `runner_ev2.correr_grafo` arma `FullCaptureAgent(GraphAgent)` sobre `GraphIndex` (`ev2_corrida/code/runner_ev2.py:64,143`); ningún runner de EV2 instancia `GraphAgentNeo4j` (la instancian `app/main.py`, `agente_v2.py` y los tests de paridad). Precedente de captura completa sobre `Neo4jIndex`: `ablacion_retrieval/corrida/agente_celda.py` (patrón `FullCaptureAgent`). Extensión por módulo nuevo sin editar módulos sellados (patrón `ev2_r1/code/comun_r1.py`). | `grep -rl GraphAgentNeo4j --include=*.py data/experiment app scripts` |
| Índice fulltext de Neo4j | `data/experiment/neo4j/indices.py:77-78`; registro `grafos.py`; carga `cargar_kg.py` | `9e131bf` (indices, cargar) · `81587f9` (grafos) | **DISPONIBLE para r1** (label `KG_Reextraido_r1`, índice `nodos_fulltext_kg_reextraido_r1`, `grafos.py:63-82`; carga verificada en U-MIG-r1 según `docs/tablero.md` §1 — **NO VERIFICADO en esta sesión** el estado de la base: solo comprobé el contenedor `Up (healthy)`). **PENDIENTE para el grafo de desarrollo re-extraído**: exige entrada nueva en el registro `grafos.py` (path, sha256, label, índice), carga con `cargar_kg.py` y creación del índice con `indices.py`; es edición de registro, no del cuarteto. | `docker ps --filter name=neo4j`; `grep -n '"KG_' grafos.py` → tres entradas |
| Pipeline E0-E5 con manifiesto y perfil `v3_b54` | `runner_corpus.py` (E1→E3, `--manifiesto`), `perfil_e1.py`, `validador_e1.py`, `ensamblar_corpus.py` (E4/E5 + esqueleto v3) | `d61c491` (runner, cliente_e1, validador) · `b01eb18` (ensamblar) | **DISPONIBLE el código; PENDIENTE el manifiesto de la tanda 0**: solo existe `manifiestos/desarrollo_5tos.json` (`perfil_e1` ausente → `produccion_dev`, `manifiesto_corpus.py:69`). El manifiesto de la tanda 0 declara `perfil_e1: "v3_b54"`, los diez TOs con sus PDF y sha, `rol_alcance` por TO (null para `docvig`), tope y límites; lo escribe el mandato de fase 2. | `ls data/experiment/reextraccion_v2/manifiestos/` → un archivo |
| Health-check de E0 (B5.2) | `data/experiment/reextraccion_v2/e0_chunking/healthcheck_e0.py` | `b45d341` · sha256 `179da6ad…` | **DISPONIBLE**, ya corrido sobre los cinco (A2.4) | `find data/experiment -name "healthcheck_<id>.json"` → cinco archivos en `segmentacion_84/b584_particion/` |

Resumen: **DISPONIBLES** esqueleto v3 + S15, atribución A0.2, juez EV2, harness,
`GraphAgentNeo4j` (clase), índice de r1, código del pipeline, health-check.
**PENDIENTES**: shapes con perfil congelado (B2.2 fase 2), regression suite
(B2.1 fase 2), cableado de r1 en `ensamblar_corpus.py`, extensión de
intrínsecas y de U-CITA-2, runner de EV2 sobre `GraphAgentNeo4j`, registro y
carga en Neo4j del grafo de desarrollo re-extraído, manifiesto de la tanda 0.
**La fase 2 no arranca con instrumentos PENDIENTES.**

---

## A6. Modelos

Ids de modelo tal como están en el código hoy, por etapa y por celda, con
archivo y línea; verificados con `grep -n "claude-" <archivos>` y
`grep -n "temperature\|TEMPERATURE" <archivos>` (salidas abajo). Vía: **API**
en todos los casos (cliente Anthropic vía `llm_cache.CachingClient`, patrón
del repo).

| etapa / celda | rol | id en el código | archivo:línea | temperatura | vía |
|---|---|---|---|---|---|
| E1 (extracción, tanda 0 y desarrollo re-extraído) | extractor | `claude-haiku-4-5` (sin fecha) | `reextraccion_v2/corpus_v2/runner_corpus.py:89`; también `e1_extractor/runner_faseB_e1.py:40` | **no fijada** (default del proveedor): 0 líneas `temperature` en `cliente_e1.py` y `comun_e1.py` | API |
| E3 (verificación) | verificador | `claude-sonnet-5` (sin fecha) | `runner_corpus.py:92`; también `e3_verificador/runner_faseB_e3.py:48` | **no fijada**: 0 líneas `temperature` en `e3_verificador/*.py` | API |
| E4 / E5 (ensamblado, esqueleto) | — | sin LLM | `ensamblar_corpus.py`, `ensamblar_r1.py` | — | — |
| C1-C4 agente | respondedor | `claude-haiku-4-5-20251001` (con fecha) | `evaluacion/harness.py:47` | 0 (`harness.py:48`) | API |
| C1-C4 juez | juez v1 EV2 | `claude-sonnet-4-6` (sin fecha) | `ev2_juez/juez.py:37` | 0.0 (`juez.py:38`) | API |
| (referencia, no se usa en la tanda) juez de Fase 2.3 | juez v2.1.1 | `claude-sonnet-4-6` | `evaluacion/judge.py:87` | 0 (`judge.py:88`) | API |
| (referencia) extractor gen 2 | — | `claude-haiku-4-5-20251001` | `grafo_v2/code/extract.py:57` | no fijada | API |
| (referencia) verificador diagnóstico | — | `claude-opus-4-8` | `evaluacion/verificador.py:55`; `verifier_pilot.py:38-40` | rechaza temperature (comentario en `:55`) | API |
| (referencia) banco MCP, control ESQ | — | `claude-sonnet-5` / `claude-haiku-4-5` | `banco_mcp/gate/code/faseB_runner.py:38`; `esq/code/comun_control_esq.py:85` | — | — |

Salida del grep de ids (recortada a las líneas con constante):

```
grafo_v2/code/extract.py:57:MODEL = "claude-haiku-4-5-20251001"
evaluacion/harness.py:47:MODEL = "claude-haiku-4-5-20251001"   # FIJO para los 5 grafos
corpus_v2/runner_corpus.py:89:MODEL_E1 = "claude-haiku-4-5"
corpus_v2/runner_corpus.py:92:MODEL_E3 = "claude-sonnet-5"
evaluacion/verifier_pilot.py:38:MODEL_MAP = "claude-haiku-4-5-20251001"
evaluacion/verifier_pilot.py:39:MODEL_VERIF = "claude-opus-4-8"
evaluacion/verifier_pilot.py:40:MODEL_EVALA = "claude-sonnet-4-6"
e3_verificador/runner_faseB_e3.py:48:MODEL_E3 = "claude-sonnet-5"
e3_verificador/runner_faseB_e3.py:51:MODEL_E1 = "claude-haiku-4-5"
e1_extractor/runner_faseB_e1.py:40:MODEL = "claude-haiku-4-5"
ev2_juez/juez.py:37:MODELO = "claude-sonnet-4-6"
banco_mcp/gate/code/faseB_runner.py:38:MODELO = "claude-sonnet-5"
evaluacion/judge.py:87:JUDGE_MODEL = "claude-sonnet-4-6"
evaluacion/verificador.py:55:MODEL_VERIF = "claude-opus-4-8"
esq/code/comun_control_esq.py:85:MODEL_E1 = "claude-haiku-4-5"
```

Salida del grep de temperatura: `harness.py:48:TEMPERATURE = 0` ·
`ev2_juez/juez.py:38:TEMPERATURE = 0.0` · `judge.py:88:JUDGE_TEMPERATURE = 0`;
`cliente_e1.py`: 0 líneas · `comun_e1.py`: 0 líneas · `e3_verificador/*.py`: 0
líneas · `runner_corpus.py`: 0 líneas.

Registro de la medición sellada C1 (`ev2_r1/trazas/ev2_r1_base/EV2F-*.json`,
`meta.model`): `claude-haiku-4-5-20251001` en 40/40 trazas (comando en A7).

**Decisión 7, tal cual:** «Tope de gasto de la tanda 0: USD 100. E1 corre como
corrió r1, sin temperatura fijada (default del proveedor); el registro de
modelos lo declara como límite de reproducibilidad y no se edita
`cliente_e1.py` ni ningún código del pipeline para esta tanda.»

**Regla de C1.9** (`docs/plan_tesis.md:751`): la fase 2 **registra el id exacto
devuelto por la API por cada llamada** (campo `model` de la respuesta, como ya
lo guardan las trazas de EV2 en `meta.model` y `raw_turns_agent[].raw.model`,
y el control de U-EV2-TIPO en `modelo_segun_api`), junto con la temperatura
(fijada o «default del proveedor») y la vía. Para las corridas pasadas el id se
toma solo de la traza que lo guardó; donde no esté, la celda del registro dice
NO ENCONTRADO con el archivo donde se buscó. El documento `docs/registro_modelos.md`
que el plan prevé **no existe todavía** (`ls docs/registro_modelos.md` →
`No such file or directory`); es borrador de la mesa hasta que la autora lo
apruebe, y la tanda 0 aporta sus filas cuando corra.

---

## A7. Costo

### A7.1 Tarifas

`data/experiment/escalado_prep/resumen_escalado.md:38-39`:

```
| E1 | 0.007062 | 0.006274 | 0.008798 | 1.175e-05 |
| E3 | 0.012375 | 0.009972 | 0.013495 | 2.051e-05 |
```

(columnas: fase, USD/unidad agregado, mín. por TO, máx. por TO, USD/char).
Las recomputé desde su fuente declarada (`resumen_escalado.md:7`:
`corpus_v2/salida/estado_corpus.json`, clave `fases_cerradas`): el agregado
**excluye `pro`**, cuyo E1 costó USD 0 por caché poblada (`:30-32`).

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
d=json.load(open('data/experiment/reextraccion_v2/corpus_v2/salida/estado_corpus.json'))['fases_cerradas']
for f in ('e1','e3'):
    g=sum(v['gasto_usd'] for k,v in d.items() if k.endswith(':'+f) and not k.startswith('pro:'))
    n=sum(v['resumen']['n'] for k,v in d.items() if k.endswith(':'+f) and not k.startswith('pro:'))
    print(f, 'sin pro: gasto', round(g,4), 'n', n, 'USD/unidad', round(g/n,6))"
```

Salida: `e1 sin pro: gasto 11.7378 n 1662 USD/unidad 0.007062` ·
`e3 sin pro: gasto 20.4938 n 1656 USD/unidad 0.012375`. Coinciden con
`:38-39`. Precios de lista que las produjeron: `runner_corpus.py:90-94`
(Haiku 4.5 1,00/5,00/1,25/0,10; Sonnet 5 2,00/10,00/2,50/0,20 USD/MTok). La
re-extracción de desarrollo con el congelado **no** hereda caché: el prefijo
cambia y con él el namespace (`perfil_e1.py:173-174`), así que se paga entera,
`pro` incluida.

### A7.2 EV2: costo real de la medición sobre r1

`docs/plan_tesis.md:305` (fila B1.8): «costo real USD 7,29 desde dbs vs ~$3
estimados, bajo tope escalonado laudado 3,5 + 5,5». Incluye agente base, juez
base N=3, agente §7 N=3 y juez §7 N=3. Recomputado desde los archivos de
gasto de la unidad:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json
e1=json.load(open('data/experiment/ev2_r1/reporte/gasto_etapa1_r1.json')); s7=json.load(open('data/experiment/ev2_r1/reporte/gasto_s7_r1.json'))
print(e1['total_etapa1_usd'], s7['total_s7_usd'], round(e1['total_etapa1_usd']+s7['total_s7_usd'],4))"
```

Salida: `2.8505 4.4378 7.2883` → **USD 7,29**.

Contraste pedido: suma de `trace.cost_usd` de las 40 trazas de la corrida base
de r1 (solo agente base, N=1):

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
import json, glob, collections
fs=sorted(glob.glob('data/experiment/ev2_r1/trazas/ev2_r1_base/EV2F-*.json'))
c=collections.Counter(json.load(open(f))['meta']['model'] for f in fs)
print(len(fs), round(sum(json.load(open(f))['trace']['cost_usd'] for f in fs),4), dict(c))"
```

Salida: `40 1.409 {'claude-haiku-4-5-20251001': 40}`. Coincide con
`gasto_etapa1_r1.json → agente_base.usd = 1.409`. Es decir: el agente base es
USD 1,41 de los 7,29; el resto es juez (1,44), agente §7 (2,46) y juez §7
(1,97).

### A7.3 Aritmética

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -c "
e1=0.007062; e3=0.012375; u5=671; udev=1763; u=u5+udev
print('unidades', u5, '+', udev, '=', u)
print('E1', u, 'x', e1, '=', round(u*e1,4)); print('E3', u, 'x', e3, '=', round(u*e3,4))
print('extraccion', round(u*(e1+e3),4), '| solo 5 nuevos', round(u5*(e1+e3),4), '| solo desarrollo', round(udev*(e1+e3),4))
print('EV2 3 x 7.29 =', round(3*7.29,4)); print('TOTAL', round(u*(e1+e3)+3*7.29,4)); print('por pregunta EV2', round(7.29/40,4))"
```

Salida:

```
unidades 671 + 1763 = 2434
E1 2434 x 0.007062 = 17.1889
E3 2434 x 0.012375 = 30.1208
extraccion 47.3097 | solo 5 nuevos 13.0422 | solo desarrollo 34.2674
EV2 3 x 7.29 = 21.87
TOTAL 69.1797
por pregunta EV2 0.1822
```

| rubro | volumen | tarifa | USD |
|---|--:|--:|--:|
| E1 sobre los cinco de la tanda 0 + desarrollo | 2.434 unidades | 0,007062 / unidad | 17,19 |
| E3 sobre los mismos | 2.434 unidades | 0,012375 / unidad | 30,12 |
| *subtotal extracción* | | | *47,31* (13,04 tanda 0 + 34,27 desarrollo) |
| C2 — r1 con Neo4j fulltext | 40 preguntas, agente + juez + §7 | 7,29 por celda | 7,29 |
| C3 — desarrollo re-extraído, memoria | ídem | 7,29 | 7,29 |
| C4 — desarrollo re-extraído, Neo4j fulltext | ídem | 7,29 | 7,29 |
| *subtotal EV2 (tres celdas nuevas)* | | | *21,87* |
| E4 / E5, shapes, S15, intrínsecas, indicadores de cita, atribución | determinísticos | 0 | 0,00 |
| **TOTAL estimado** | | | **69,18** |

Contraste con M-3: la extracción del grafo de desarrollo costó USD 32,97
según `docs/plan_tesis.md:661` («si entra la re-extracción de los 5 TOs de
desarrollo, sumar el orden del grafo de desarrollo, USD 32,97 según M-3»); la
tarifa agregada da 34,27 para las mismas 1.763 unidades porque no descuenta la
caché de `pro`. Uso la cifra mayor.

**No incluido, declarado**: el costo del agente y del juez sobre las preguntas
nuevas de los cinco documentos (segunda parte de la fase 1), porque su número
no está fijado. Referencia para cuando se sellen: USD 0,18 por pregunta
(7,29 / 40, con §7 y adjudicación incluidos), es decir, 40 preguntas ≈ USD 7,3
adicionales; el total quedaría en ≈ 76,5, todavía bajo el tope. La estimación
se revisa en el mandato de fase 2 con las preguntas selladas y con los precios
verificados el día de la corrida.

### A7.4 Tope (decisión 7)

**Tope de gasto de la tanda 0: USD 100.** Si la estimación revisada del
mandato de fase 2 (preguntas selladas, precios del día, volúmenes reales de E0
sobre los diez PDF) supera el tope, **la fase 2 frena y pregunta antes de
gastar**; no se recorta silenciosamente ninguna celda ni ningún documento.
Freno por proyección activo en cada etapa (patrón `runner_corpus.py`: tope
global duro + freno por proyección al cierre de cada TO; y el de
`ev2_r1/preregistro_ev2_r1.md` §4 para las celdas de EV2); gasto real desde
las dbs, nunca de memoria.

---

## A8. Qué autoriza cada resultado

**Decisión 4, transcrita:** «La ventana de corrección única del §7 del laudo
congelado puede abrirse después de la tanda 0 si aparece una falla de esquema
que el principio de gobierno del §1 obligue a retirar. Sigue siendo una sola
ventana: si se usa en la tanda 0, la tanda 1 ya no la tiene. Si se usa, los 5
documentos de la tanda 0 pasan a haber informado el esquema y el eval set
fresco de B6.3 (a) los excluye igual que a los 15. Esto se escribe como
enmienda con fecha, sin modificar el texto original del laudo.»

La enmienda es `data/experiment/esq/enmienda_ventana_correccion_2026-09-25.md`
(borrador, pendiente de firma, escrita junto con este pre-registro).

**Decisión 6, transcrita:** «Las observaciones (10) y (11) y las vigilancias
(1) a (9) de B6.1 se miden en la tanda 0 contra sus líneas de base, sin
umbral; el único criterio de retiro es el principio de gobierno.»

Consecuencias, y nada más:

- **Si la tanda 0 no revela ninguna falla de esquema que el §1 obligue a
  retirar**: el reporte se publica como validación de diseño; la ventana del
  §7 sigue intacta para la tanda 1; los cinco documentos siguen fuera del
  conjunto que informó el esquema (solo el catálogo v3 los leyó, A2.5); nada
  cambia en el esquema congelado.
- **Si revela una falla de esquema que el §1 obligue a retirar**: la autora
  puede abrir la ventana única del §7 después de la tanda 0, con laudo
  propio; **usada acá, la tanda 1 ya no la tiene**; los cinco documentos de la
  tanda 0 **pasan a haber informado el esquema** y el eval set fresco de B6.3
  (a) los excluye igual que a los 15 (5 de desarrollo + 10 de ESQ-2), lo que
  se registra en `documentos_excluidos_esq.json` o en el artefacto que B6.3
  cite al construir su conjunto.
- **Toda otra falla** (de pipeline, de catálogo, de índice) va a su destino
  de siempre (release r2 por principio 9, backlog, C1.7) y no abre la ventana.
- Los resultados de C2-C4 **no autorizan** ajustar componente alguno para
  volver a medir en EV2 (principio 7). Tampoco deciden la promoción de ningún
  grafo ni de ningún índice: eso es laudo de la autora fuera de este
  documento.

**Nada más se decide en este documento.**

---

## A9. Orden de la fase 2, sin fechas

1. **Gates técnicos de A5 en verde**: shapes con perfil congelado (B2.2 fase
   2), regression suite (B2.1 fase 2), cableado de r1 en `ensamblar_corpus.py`
   con la mecánica fijada, extensión de intrínsecas y de U-CITA-2 a
   generación 3, runner de EV2 sobre `GraphAgentNeo4j`, registro y carga en
   Neo4j del grafo de desarrollo re-extraído, manifiesto de la tanda 0 con
   `perfil_e1: "v3_b54"` y `rol_alcance` null para `docvig`; supuestos de A3.5
   resueltos en el mandato.
2. **Preguntas de la segunda parte de la fase 1 selladas**: la autora lee los
   cinco documentos, escribe preguntas y criterios, y se sellan por commit
   antes de correr; la estimación de A7 se revisa con su número.
3. **Ok escrito de la autora**, que a su vez espera respuesta del mentor
   (decisión 5: la corrida no arranca sin ese ok).
4. **Corrida**: E0 → E1 → E3 → E4 → E5 sobre los diez TOs con el manifiesto de
   la tanda 0 (mismo código que produjo r1; tope USD 100; freno por
   proyección); registro del id de modelo devuelto por la API en cada
   llamada (A6).
5. **Gate de release**: S15 en PASS con `--out` explícito y fechado en la ruta
   del release (`docs/plan_tesis.md:666`); ausencia de las tres `aplica_a`
   adjudicadas como falsedad (`:667`); shapes con perfil congelado; regression
   suite; contador de vocabulario retirado = 0. **Si S15 falla, el release no
   sale.**
6. **Las tres celdas de EV2** (C2, C3, C4), una vez cada una, con el protocolo
   de C1; C1 se agrega desde `774acac`.
7. **Lectura de observaciones y vigilancias** (A4) contra sus líneas de base,
   sin umbral; atribución A0.2 sobre C3/C4; indicadores de cita; intrínsecas.
8. **Reporte** como validación de diseño, con la tabla de las cuatro celdas
   (intervalos; declaración de si el n alcanza), las predicciones de A4 en el
   formato de una fila por predicción (predicho / observado / veredicto), el
   costo real desde dbs contra la estimación de A7, las incidencias, y la
   posición sobre la ventana del §7 (A8).

---

*Sello pendiente: este borrador se sella por commit de la autora antes de la
segunda parte de la fase 1; toda modificación posterior es enmienda separada,
nunca ajuste silencioso.*
