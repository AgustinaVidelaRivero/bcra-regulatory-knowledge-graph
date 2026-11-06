# Job de actualización ante cambio normativo — diseño (fase 1)

Unidad U-JOB-ACT, fase 1. Diseño sin red, sin código de descarga, USD 0.
Ejecuta la exigencia 7 del mapa de related work (`docs/mapa_related_work.md`
§2, fila 7: «Protocolo de actualización del recurso», estado PARCIAL — el
hueco real es el protocolo ante cambio normativo).

Lo que entrego acá es **el mecanismo**: qué consulta el job, qué persiste, cómo
clasifica los cambios, de dónde saca la procedencia documental y cómo llega
desde un documento modificado hasta los nodos y aristas del grafo que salieron
de él. No es un servicio: no hay cron, ni demonio, ni monitoreo, ni alertas. La
periodicidad se diseña y se declara operable; cuándo se dispara es una decisión
posterior.

Todo número de este documento se recomputa con el comando que lo acompaña.

---

## 0. La regla que gobierna el diseño entero

**El inventario sellado es solo lectura.** El job compara contra
`indice_oficial_raw.json`, el inventario y los sha256 ya registrados, y
**reporta** el delta; nunca los reescribe, ni «para dejarlos al día».

El motivo es concreto y verificable: esos artefactos respaldan números que ya
están impresos en el informe. El `main.tex` commiteado dice, en la Motivación,
que el índice oficial registraba **157** Textos Ordenados que suman **7.321**
páginas, y en el capítulo del esquema que los cinco del conjunto de desarrollo
suman **564** páginas:

```bash
git show HEAD:docs/tesis/main.tex | grep -n -E "157|7\.321|564 páginas"
```

Si el job actualizara el inventario, la prosa de la tesis se movería sola.
Cualquier actualización del inventario es una decisión de la autora, con laudo,
jamás un efecto del job. La regla vale igual para `desarrollo_5tos.json` y para
todo lo que cuelga de `escalado_prep/`.

Consecuencia de diseño, no solo de disciplina: **el job escribe únicamente en
su propio directorio**, `data/experiment/job_actualizacion/`. La línea base
entra al proceso como lectura y sale como columna `*_anterior` de la tabla de
deltas.

---

## 1. La cuenta del alcance, recomputada

El corpus a vigilar son **157 Textos Ordenados** cuyas huellas viven en dos
lugares distintos. Re-derivé la cuenta contra los artefactos commiteados antes
de diseñar nada:

```bash
python3 data/experiment/job_actualizacion/code/verificar_alcance.py
```

→ `verificacion_alcance.json`, veredicto **OK**, cero comprobaciones fallidas.

| Grupo | TOs | Páginas | Dónde vive la huella |
|---|---:|---:|---|
| Inventariados | 152 | 6.757 | `escalado_prep/manifest_pdfs.sha256` (152 líneas) y `descarga_log.json` (152 entradas, las 152 con `sha256` y `url`) |
| Conjunto de desarrollo | 5 | 564 | `reextraccion_v2/manifiestos/desarrollo_5tos.json`, campo `sha256_pdf` |
| **Total** | **157** | **7.321** | |

Comprobaciones que corren dentro del verificador y que cierran las dos puntas:

- **Índice oficial:** 158 entradas = 103 `textos_ordenados` + 55
  `regimenes_informativos`; **157 URLs únicas**; **1 duplicada**
  (`t-optico.pdf`, publicada en las dos listas). Uso la **misma regla de
  deduplicación** que `escalado_prep/code/construir_inventario.py`: dedup por
  URL. No hay diferencia que declarar.
- **Los dos grupos cubren el índice sin resto:** las URLs del inventario están
  todas en el índice, y las 5 que sobran del índice son exactamente los cinco
  del conjunto de desarrollo (`t-RI-CM`, `t-capmin`, `t-cladeu`, `t-excbio`,
  `t-pusf`), identificadas por título exacto contra `subset_excluido` de
  `inventario_resumen.json`. O sea: 152 ∪ 5 = las 157 URLs únicas del índice,
  sin solapamiento y sin faltante.
- **Coherencia de huellas:** el sha de `manifest_pdfs.sha256` coincide con el de
  `descarga_log.json` en los 152 (cero discrepantes), y el `sha256_pdf`
  declarado para los 5 coincide byte a byte con el PDF en disco.

**Hueco cubierto en el diseño:** `desarrollo_5tos.json` **no trae URL** (0 de 5
entradas con campo `url`). El job la resuelve contra `indice_oficial_raw.json`
por coincidencia exacta de título, y el mapeo queda materializado en
`verificacion_alcance.json` → `indice_oficial.url_por_id_desarrollo`. Es
derivación de artefactos sellados, no un dato nuevo inventado por el job.

---

## 2. (a) Mecanismo del job

### 2.a.1 Qué consulta

Dos cosas, en este orden:

1. **El índice oficial**, una vez por corrida. La página
   `https://www.bcra.gob.ar/ordenamiento-y-resumenes/` monta la lista por
   JavaScript y no es accesible por HTTP plano; el endpoint que la alimenta
   está documentado en `escalado_prep/code/construir_inventario.py`:
   `/api/endpoints/ordenamiento-y-resumenes.php?lang=es`. Es el mismo endpoint
   cuya respuesta cruda quedó congelada como `indice_oficial_raw.json`, así que
   la corrida nueva y la línea base son comparables campo a campo (`titulo`,
   `titulo_truncado`, `archivo`, `url` — las cuatro claves de cada entrada).
2. **Los PDFs** de las URLs que el índice publique, uno por TO.

### 2.a.2 Reuso del scraper existente: envolver no, camino propio sí

El scraper idempotente con checkpoint existe (`src/scraper/download_bcra.py`,
subcomando B1 = TOs actuales). **El job no lo invoca ni lo envuelve: necesita
camino propio.** Tres motivos, los tres verificables en el propio archivo:

1. **B1 no consulta el índice: replica una lista fija.** Su cuerpo es una lista
   literal de pares (URL, destino) — un *snapshot* del índice tomado en su
   momento, según declara su propio docstring. Un job cuyo trabajo es detectar
   «nuevo en el índice» y «desaparecido del índice» no puede correr contra una
   lista congelada dentro del código: por construcción nunca vería un alta ni
   una baja.
2. **Su idempotencia es la contraria a la que necesito.** El docstring de B1 lo
   dice sin ambigüedad: `skip-existing` salta el archivo ya presente en disco y
   **no detecta el caso «mismo path, PDF actualizado»**, que es exactamente el
   caso que el job existe para detectar. Reusarlo sería reusar el mecanismo que
   ciega la medición.
3. **Escribe donde el job tiene prohibido escribir:** B1 persiste en
   `data/raw/`, con su manifiesto y su checkpoint. El job escribe solo en su
   directorio.

Lo que **sí** reuso, y es lo que vale del scraper: sus **patrones de cortesía y
robustez** (§6), replicados en el cliente propio; y la **regla de identidad** de
`construir_inventario.py` (id corto = stem del archivo publicado, sin prefijo
`t-`, minúsculas, no alfanuméricos a `_`), para que un alta nueva reciba un id
construido igual que los 152. El precedente directo de descarga es
`escalado_prep/code/descargar_pdfs.py`: stdlib, idempotente, sha256 por
archivo, y la normalización de *percent-encoding* del path — que no es un
detalle, porque el índice publica al menos un archivo con guion largo
(`t-RI–SPI.pdf`, U+2013) que rompe la petición si no se codifica.

Editar el scraper queda fuera de alcance: `src/scraper/` es solo lectura para
esta unidad.

### 2.a.3 Los cinco pasos de una corrida

```
1. LEER LÍNEA BASE   (solo lectura)   índice sellado + inventario + sha + manifiesto de desarrollo
2. TRAER ÍNDICE      (1 pedido)       endpoint oficial → indice_<fecha>.json crudo, sin normalizar
3. RESOLVER OBJETIVO (sin red)        dedup por URL; unir con línea base; clasificar altas y bajas
4. TRAER PDFs        (≤157 pedidos)   descarga + sha256 + páginas + procedencia + cabeceras HTTP
5. ADJUDICAR         (sin red)        tabla de deltas + mapeo al grafo + reporte regenerable
```

El paso 2 persiste la respuesta **cruda**, antes de cualquier normalización:
es la evidencia de qué publicaba la fuente ese día, y hace la corrida
re-adjudicable sin volver a la red. El paso 3 es el único que decide altas y
bajas, y lo hace por comparación de conjuntos de ids, no por heurística.

### 2.a.4 Qué persiste y dónde

```
data/experiment/job_actualizacion/
├── diseno_job_actualizacion.md          este documento
├── esquema_tabla_deltas.json            contrato de la tabla (§3)
├── verificacion_alcance.json            la cuenta del alcance recomputada
├── sonda_procedencia.json               cobertura de procedencia sobre los 157 (§4)
├── sonda_mapeo_grafo.json               cobertura del mapeo sobre el grafo vigente (§5)
├── .gitignore                           los PDFs descargados no se versionan
├── code/                                scripts regenerables, sin rutas absolutas
└── corridas/<AAAA-MM-DD>/
    ├── indice_crudo.json                respuesta cruda del endpoint
    ├── observaciones.json               una entrada por TO: sha, bytes, páginas, cabeceras, procedencia
    ├── tabla_deltas.json                la tabla acumulada tras esta corrida
    ├── mapeo_grafo.json                 partes afectadas, solo para TOs con contenido modificado
    ├── reporte.md                       lectura de la corrida, regenerable desde los tres anteriores
    └── pdfs/                            los PDFs bajados (ignorados por git)
```

La tabla de deltas es **acumulativa**: cada corrida la reescribe entera dentro
de su propio directorio, arrastrando `visto_primera_vez` y `corridas_observado`
de la corrida anterior. Nunca hay una tabla «viva» compartida que se pueda
corromper a mitad de camino; cada corrida es un artefacto cerrado y comparable.

### 2.a.5 Política de retención

Qué se conserva de cada corrida **no es housekeeping: es load-bearing**. El
mapeo fino (§5.b) compara el PDF de la corrida anterior contra el nuevo, y la
fuente **solo sirve la versión vigente**: una versión que se borra del disco no
se puede volver a pedir. La política se fija acá, antes de correr.

**Se conserva siempre, y se versiona** — los artefactos JSON/Markdown de cada
corrida (`indice_crudo.json`, `observaciones.json`, `tabla_deltas.json`,
`mapeo_grafo.json`, `verificacion_corrida.json`, `reporte.md`). Pesan pocos
MiB, son la serie temporal del corpus, y sin ellos no hay historia: son la
única evidencia de qué publicaba la fuente cada día.

**Se conserva sin versionar** — la bitácora `corrida.log`. El `.gitignore` raíz
del repositorio excluye `*.log`, y esta unidad no lo edita: las estadísticas de
cortesía que la bitácora respalda (pedidos, reintentos, activaciones del modo
lento) se derivan a `verificacion_corrida.json`, que sí se versiona, de modo
que ningún número del reporte depende de un archivo que git no guarda.

**Se conserva condicionalmente, y no se versiona** — los PDFs, bajo
`corridas/<AAAA-MM-DD>/pdfs/<id>.pdf` (el `id` es la clave de la tabla):

| Qué | Por cuánto | Por qué |
|---|---|---|
| PDFs de la **última corrida**, los 157 | hasta que exista una corrida posterior completa | son la línea base de comparación de la corrida siguiente; sin ellos el mapeo fino se degrada al grueso |
| PDFs de los TOs con `contenido_modificado`, en la corrida que detectó el cambio | **permanente** | son la evidencia del cambio y la única copia de una versión que la fuente ya no sirve |
| El resto | purgable | reproducible desde la fuente mientras siga siendo la versión vigente |

Costo: ~166 MiB por la última corrida completa, más lo que acumulen los TOs que
efectivamente cambien. A ritmo mensual con pocos cambios, crece despacio.

**La línea base de la primera corrida sale gratis.** Los PDFs originales ya
están en disco, en zonas selladas: `escalado_prep/pdfs/<id>.pdf` los 152 y
`data/experiment/subset/<archivo>.pdf` los 5. El job los **lee**; no los copia,
no los mueve, no los toca.

**La purga es manual y explícita: el job nunca borra.** Un job que hace limpieza
automática es un job que puede destruir la única copia de una versión
irrecuperable. Borrar es decisión de la autora, con la tabla de deltas a la
vista.

**Qué pasa si falta el PDF anterior.** El job no adivina y no intenta
re-descargarlo (es imposible: la fuente ya no lo publica). Registra
`paginas_modificadas: null` y el motivo en `motivo_sin_diff_fino`, con tres
valores posibles: `pdf_anterior_ausente`, `pdf_anterior_ilegible`,
`distinta_cantidad_de_paginas_sin_alineacion`. El mapeo cae entonces al salto
grueso (el TO entero) y lo declara. **Un delta sin diff fino sigue siendo un
delta válido**: pierde precisión, no validez — el cambio de sha ya está probado.

### 2.a.6 Periodicidad

**Mensual** es la cadencia adecuada y la declaro operable, no instalada. Tres
razones, la segunda ahora **medida** por la primera corrida:

1. El volumen de una corrida es chico (§7: 158 pedidos, ~166 MiB).
2. El objeto vigilado cambia despacio. La corrida del 2026-09-07 midió la tasa:
   **8 de 152 TOs (5,3 %) cambiaron en ~3,5 semanas**, y **3 de 5 (60 %) en
   ~4 meses** — ver `corridas/2026-09-07/tabla_deltas.json`. Una cadencia
   mensual cae en el orden correcto: ni corre en vano ni deja acumular meses.
3. Mantiene la ventana lo bastante corta como para que un cambio sea
   adjudicable a un puñado de comunicaciones identificables en lugar de a un
   bloque indistinguible.

Operarla es una línea de `cron` o un `launchd` disparando el runner; el
mecanismo no depende de eso y no lo instalo. Lo único que el diseño exige del
disparo es que **dos corridas no se pisen**: como cada una escribe en su propio
directorio fechado, dos corridas del mismo día colisionarían — el runner falla
temprano si el directorio ya existe, en vez de sobrescribir.

---

## 3. (b) Esquema de la tabla de deltas

El contrato completo, campo por campo con su origen, está en
`esquema_tabla_deltas.json` (24 campos, 5 clases de cambio). Acá va lo que
decide.

**Identidad documental.** La clave es el `id` corto derivado del nombre de
archivo que publica la fuente, con la misma regla que construyó el inventario
sellado. Es estable y auditable contra la fuente, y no depende del título (que
la fuente edita) ni del orden del índice.

**Los campos que el mandato pide, y qué los alimenta:**

| Campo | Contenido |
|---|---|
| `id`, `titulo_indice`, `archivo_indice`, `categoria` | identidad documental y su lugar en el índice |
| `url`, `url_linea_base` | URL vigente y la de la descarga original; que difieran es republicación bajo otro nombre |
| `sha_anterior`, `sha_actual` | huella de la línea base y de esta corrida — **la señal de cambio** |
| `visto_primera_vez`, `visto_ultima_vez`, `corridas_observado` | historia de observación |
| `clasificacion` | `sin_cambio` / `contenido_modificado` / `nuevo_en_indice` / `desaparecido_del_indice` / `no_verificable` |

**Una clase más que las cuatro del mandato, y por qué.** Agrego
`no_verificable`: el TO figura en el índice pero la descarga falló o no
devolvió un PDF válido. Sin esa clase, un 503 o un timeout se clasificaría como
desaparición — es decir, un problema de red se registraría como un hecho
regulatorio. Es la diferencia entre «el BCRA dio de baja este texto» y «no pude
verlo hoy». Se resuelve reintentando en la corrida siguiente.

**Un TO que desaparece del índice se declara, no se borra.** La fila se
conserva con su última observación intacta y `visto_ultima_vez` **no** avanza:
esa fecha detenida es justamente la evidencia de cuándo dejó de estar. La baja
de un texto regulatorio es un hecho del dominio, y borrar la fila destruiría el
único registro de que existió.

**Renombres: anotación, no clasificación.** Si en una misma corrida aparece un
`nuevo_en_indice` cuyo título coincide exactamente con el de un
`desaparecido_del_indice`, el job lo anota en `presunta_renombrada_de` y deja
las dos filas con su clasificación propia. No fusiona. Decidir que son el mismo
documento es una adjudicación con consecuencias sobre la trazabilidad del
grafo, y es de la autora.

**Las cabeceras HTTP se registran pero no deciden.** `Last-Modified`, `ETag`,
`Content-Length` y `Content-Type` van a la tabla porque habilitan pedidos
condicionales en corridas futuras (§6) y porque son gratis. Pero la señal de
cambio es **el sha256 del contenido**, no la cabecera: un servidor puede
regenerar el PDF y mover `Last-Modified` sin que el texto cambie, o servirlo
desde caché con la cabecera vieja. La línea base, además, no tiene cabeceras
guardadas: las siete claves de cada entrada de `descarga_log.json` son
`estado`, `http`, `bytes`, `content_type`, `intentos`, `sha256` y `url`, sin
`Last-Modified` ni `ETag`, así que en la primera corrida no hay con qué
comparar aunque quisiera.

---

## 4. (c) Procedencia documental

La pregunta es de qué resolución o comunicación proviene cada versión. La
respondí midiendo, no suponiendo:

```bash
python3 data/experiment/job_actualizacion/code/sonda_procedencia.py
```

→ `sonda_procedencia.json`, 157 de 157 leídos, cero errores de lectura.

**Lo que el sitio expone y dónde.** El índice **no** trae procedencia: sus
entradas tienen exactamente cuatro claves (`titulo`, `titulo_truncado`,
`archivo`, `url`). Pero **el PDF sí la imprime**, en dos formas distintas:

- **P (portada)** — «`-Última comunicación incorporada: "A" NNNN-`» y «`Texto
  ordenado al DD/MM/AA`» en la carátula. Es procedencia **por documento**.
- **F (pie de página)** — «`Versión: Na. COMUNICACIÓN "A" NNNN`» al pie, junto a
  «`Vigencia: DD/MM/AAAA`». Es procedencia **por página**, y es la forma que
  vale para el mapeo fino.

**Cobertura medida sobre los 157** (leyendo 3 páginas de cabecera más una
muestra de hasta 5 páginas repartidas por el cuerpo):

| | TOs |
|---|---:|
| con portada | 94 |
| con pie | 152 |
| **con alguna de las dos** | **153** |
| solo portada | 1 |
| solo pie | 59 |
| con ambas | 93 |
| **sin ninguna** | **4** |

Recomputo: 153 = 1 + 59 + 93, y 157 = 153 + 4. Por grupo: 148 de los 152
inventariados y **5 de 5** del conjunto de desarrollo. En páginas muestreadas,
**839 de 1.076** llevan el pie con su número de comunicación.

**Los límites, declarados y no inferidos:**

- **4 TOs no imprimen procedencia en ninguna forma** (`ri_cc`, `ri_ccna`,
  `ri_ccpnp`, `ri_spi`). Para ellos el job registra el cambio de sha y deja
  `procedencia.limite_declarado` con el motivo. **No se infiere** la
  comunicación cruzando fechas ni buscando en otro lado: eso sería inventar
  procedencia, que es peor que no tenerla.
- **7 TOs imprimen la portada pero sus dígitos no se extraen**, porque el PDF
  usa glifos no mapeados y el número sale como `(cid:NN)` (`afiltr`, `coltit`,
  `incuca`, `lavdin`, `pagjub`, `retype`, `venliq`). Es una falla de extracción,
  no de la fuente, y se registra como tal — los siete tienen pie legible, así
  que no quedan sin procedencia.
- La lectura es de **texto extraído**, con las variantes de comilla
  (tipográfica y recta) y de año (2 o 4 dígitos) que el propio corpus exhibe.
  Cuando el patrón no matchea, el campo queda `null` con su motivo; nunca se
  rellena con el valor de otro TO ni con el de la corrida anterior.

**Cómo se registra.** Por cada versión observada, el job guarda
`procedencia_anterior` (leída del PDF de la línea base) y `procedencia_actual`
(del PDF nuevo). Un cambio de `portada_comunicacion` de `"A" 8378` a `"A" 84xx`
es la respuesta directa a «de qué resolución salió esta versión». Y como el pie
es por página, un cambio localizado en la página 131 se atribuye a la
comunicación que esa página declara — que es lo que convierte el delta en algo
accionable en lugar de un «este documento cambió».

---

## 5. (d) Mapeo delta → procedencia → partes afectadas del grafo

```bash
python3 data/experiment/job_actualizacion/code/sonda_mapeo_grafo.py
```

→ `sonda_mapeo_grafo.json`, sobre el grafo vigente
`data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json` (6.529 nodos /
17.772 aristas, el que declara `docs/tablero.md` §1).

### 5.a El grafo registra procedencia por elemento, y la medí

Cada nodo y cada arista traen un bloque `provenance` (y una lista
`provenances` cuando el elemento fue reforzado desde más de un lugar) con los
campos `to`, `archivo`, `punto`, `rol_documental`, `chunk_id`, `paginas` y
`ancestros`. Cobertura:

| | Nodos | Aristas |
|---|---:|---:|
| total | 6.529 | 17.772 |
| con `to`, `chunk_id` y `paginas` | 6.510 | 17.690 |
| sin `to` pero recuperables por `archivo` | 15 | 78 |
| no atribuibles a ningún TO | 4 | 4 |

Los 19 nodos y 82 aristas sin `to` son `rol_documental: esqueleto`. De ellos,
15 nodos y 78 aristas **sí** traen `archivo`, y el mapa `archivo → to` es
**1:1 sin ambigüedad** (verificado: `archivo_a_to_ambiguo` vacío), así que el
job los recupera por esa vía. Los 4 nodos y 4 aristas restantes vienen de
`esquema_v2_clases.json` — son esqueleto del esquema, no de un documento — y
quedan **correctamente fuera** de todo mapeo por TO.

### 5.b El mapeo, en tres saltos

```
TO con contenido_modificado
   │  sha_actual ≠ sha_anterior
   ▼
páginas cuyo texto difiere        ← diff página a página entre PDF viejo y nuevo
   │  cada página declara su comunicación en el pie
   ▼
chunk_ids que tocan esas páginas  ← provenance.paginas ∩ páginas_modificadas
   │
   ▼
nodos y aristas de esos chunk_ids ← el conjunto a revisar
```

El salto grueso (TO entero) siempre está disponible: basta `provenance.to`. El
salto fino (por página) está disponible cuando el diff por página es aplicable
—ambos PDFs presentes y alineables—; cuando no lo es, el job lo declara
(`paginas_modificadas: null`) y cae al salto grueso. No estima.

### 5.c Cuánto se toca, medido

Si cambiara un TO entero, el conjunto a revisar es:

| TO | Nodos | Aristas |
|---|---:|---:|
| `ext` | 3.059 | 9.179 |
| `cap` | 2.157 | 5.442 |
| `cla` | 508 | 1.060 |
| `pro` | 421 | 1.056 |
| `ric` | 388 | 953 |

Y el salto fino paga: por página hay entre **14,1** (`ric`) y **32,3** (`ext`)
nodos en promedio. Un cambio de tres páginas señala del orden de cien nodos en
lugar de miles — que es exactamente la diferencia entre «actualizar solo esas
partes» y re-extraer el documento entero.

### 5.d El caso que rompe el reemplazo ingenuo

**16 nodos están anclados en más de un TO** (11 en dos, 4 en tres, 1 en cinco);
ninguna arista lo está. Son sujetos compartidos entre documentos
(`Sujeto_banco` responde a `cap` y `cla`; `Sujeto_bcra` a `cap`, `ext` y `pro`).

Consecuencia de diseño: el mapeo emite `compartidos_con_otros_tos` como lista
aparte, y esos elementos se marcan **para revisar, nunca para reemplazar por
TO**. Borrarlos y regenerarlos desde el TO que cambió perdería la anclada del
otro documento. Es poco volumen y alta consecuencia: por eso va como campo
propio de la tabla y no como nota al pie.

### 5.e El alcance real, declarado

El grafo vigente cubre **los 5 TOs del conjunto de desarrollo, y solo esos**
(`tos_cubiertos_por_el_grafo`: `cap`, `cla`, `ext`, `pro`, `ric`). Entonces:

- El mapeo se **diseña en general** —la lógica no sabe cuántos TOs cubre el
  grafo— y se **ejercita sobre lo que existe**.
- Para un TO cambiado que el grafo no cubre (cualquiera de los otros 152), el
  mapeo no aplica y se declara con `fuera_de_alcance`. **No es un error del job
  ni un hueco del diseño**: es el alcance actual del grafo, y el propio delta es
  el insumo que dirá si conviene ampliarlo.
- El ejercicio con datos va en la fase 2, no acá.

**El job no toca el grafo.** Produce el conjunto de partes afectadas y ahí se
detiene. Aplicar la actualización es una release declarada, con su propio
laudo. Un job automático que edite el grafo vigente sería exactamente la clase
de efecto silencioso que la regla del §0 existe para impedir.

---

## 6. (e) Cortesía y robustez con el sitio de terceros

El sitio es de un tercero y el job va a golpearlo periódicamente. Los
parámetros salen del scraper existente, que ya los tiene calibrados contra este
mismo host:

| Aspecto | Valor | Origen |
|---|---|---|
| Ritmo | 1 pedido cada 0,5 s (2 req/s), global | `DEFAULT_DELAY` del scraper; `descargar_pdfs.py` usa 0,4 s |
| Concurrencia | **ninguna**, un pedido por vez | 158 pedidos no justifican paralelismo |
| Timeout | 60 s por pedido | intermedio entre los 15 s del scraper y los 120 s de `descargar_pdfs.py`; los PDFs llegan a 4,6 MiB |
| Reintentos | 3, con espera creciente 2/4/6 s | `descargar_pdfs.py` (`REINTENTOS=3`, `ESPERA=2.0`) |
| Ante 503 repetido | ≥5 consecutivos → pausa 60 s y baja a 1 req/s | patrón `slow-mode` del scraper |
| Identificación | User-Agent propio del job, descriptivo y sin datos personales | — |
| Validación | `%PDF` al inicio y tamaño > 1 KiB antes de aceptar | `is_valid_pdf` del scraper |

**Qué hace ante una caída.** El job **no** reintenta indefinidamente ni aborta
la corrida entera. Un TO que no se puede traer queda `no_verificable` con su
error textual, la corrida sigue con los demás, y el reporte encabeza con
cuántos quedaron sin verificar. Si el endpoint del índice no responde, **la
corrida se aborta antes de bajar un solo PDF**: sin índice no hay forma de
distinguir «desapareció» de «no pude preguntar», y una corrida que clasificara
157 bajas por una caída de red sería peor que no correr.

**Pedidos condicionales, a partir de la segunda corrida.** Una vez que el job
guardó `ETag` y `Last-Modified`, puede mandarlos como `If-None-Match` /
`If-Modified-Since` y aceptar un `304` como «sin cambio», ahorrando el cuerpo
del PDF. En la primera corrida no aplica: la línea base no tiene cabeceras
guardadas. Y aun con condicionales, un `200` siempre se verifica por sha256 —
la cabecera decide si hay que bajar, el sha decide si cambió.

**Idempotencia dentro de la corrida.** Si un TO ya se bajó a
`corridas/<fecha>/pdfs/` con tamaño > 0, una re-ejecución no vuelve a pedirlo:
una corrida interrumpida se retoma sin castigar al sitio con lo ya traído.

---

## 7. (f) Plan de la fase 2, con su costo declarado

**Qué hace:** una corrida completa del job sobre los 157, con toda la escritura
a `data/experiment/job_actualizacion/corridas/<fecha>/`.

**Costo de API: USD 0.** No hay LLM en ningún paso: descarga, sha256, conteo de
páginas, expresiones regulares sobre texto extraído y operaciones de conjuntos
sobre el grafo. Nada de eso llama a un modelo.

**Costo real, recomputado:**

| Magnitud | Valor | Cómo se recompone |
|---|---|---|
| Pedidos | **158** | 1 índice + 157 PDFs |
| Tráfico | **166,21 MiB** | suma de `bytes` de la línea base: 151,55 MiB (los 152) + 14,66 MiB (los 5) |
| PDF más grande | 4,56 MiB | máximo de `bytes` en `descarga_log.json` |
| Tiempo de pared | **~4 a 8 min** | piso de 79 s solo por el ritmo (158 × 0,5 s), más transferencia y hasheo |
| Escritura en disco | ~166 MiB de PDFs (ignorados por git) + ~pocos MiB de JSON | |

```bash
python3 -c "import json; d=json.load(open('data/experiment/escalado_prep/descarga_log.json')); r=json.load(open('data/experiment/escalado_prep/referencia_subset.json')); b=sum(v.get('bytes',0) for v in d.values())+sum(int(v['bytes']) for v in r.values()); print(b, round(b/1048576,2), 'MiB;', 1+len(d)+len(r), 'pedidos')"
```

**Qué escribe:** los seis artefactos de `corridas/<fecha>/` del §2.a.4. Nada
fuera del directorio de la unidad. Cero escrituras sobre `escalado_prep/`,
`reextraccion_v2/manifiestos/`, `data/raw/` o el grafo.

**Entregables nombrados de la fase 2:**

1. **`delta_conjunto_desarrollo`** — el resultado sobre los 5 TOs del conjunto
   de desarrollo, reportado aparte y **al frente del reporte**, hayan cambiado o
   no. Si alguno cambió es hallazgo mayor y se declara con su sha anterior y el
   actual: no invalida nada, porque el trabajo está anclado por sha —que es
   precisamente la defensa que el informe ya declara—, pero cambia lo que la
   autora puede narrar. Si ninguno cambió, se declara explícitamente que los 5
   siguen idénticos a los inventariados.
2. **`delta_inicial_vs_descarga_original`** — el delta acumulado desde la
   descarga original hasta la corrida, sobre los 157, con la lectura de §8.

**Riesgo declarado de la fase 2:** el endpoint del índice puede haber cambiado
de forma o de ruta desde que se congeló la respuesta cruda. Si responde algo
que no tiene las dos listas esperadas, la corrida **se aborta y lo reporta**;
no intenta adivinar el formato nuevo. Recuperarse de eso sería rediseñar la
consulta, y eso es una decisión con laudo, no un `except` del runner.

---

## 8. (g) La sinergia con la exigencia 6

El corpus fue descargado y **congelado por sha**. Esa congelación tiene una
consecuencia que no es un subproducto: **la primera corrida del job mide el
delta acumulado desde entonces**, y ese delta es material normativo **posterior
al corte de construcción** del grafo — que es exactamente el insumo que la
exigencia 6 del mapa de related work necesita («Validación contra material
posterior a la construcción», estado ABIERTA, con el precedente de PrimeKG
validando contra terapias aprobadas después de su corte de datos).

Un diseño alimenta dos exigencias. La 7 pide el mecanismo de actualización; la
6 pide material posterior con el que validar. El delta inicial es las dos
cosas: la salida del mecanismo y el material.

**Qué material quedaría disponible, y de qué tamaño es la ventana.** Acá tengo
que corregir un supuesto que circula en tres documentos del repo.

Tres documentos (`docs/registro_reunion_mentores_2026-09-04.md`,
`docs/plan_tesis.md`, `docs/laudo_B5.5_alcance_corpus_y_catalogo.md`) dicen que
el corpus congelado es **de marzo de 2026**. **Ningún artefacto lo respalda**, y
el repo lo contradice: su primer commit es del **2026-04-26**, posterior a esa
fecha.

```bash
git log --format="%ad" --date=short | tail -1
```

Las fechas de adquisición que **sí** están ancladas en artefactos son dos, y
son distintas por grupo:

| Grupo | Adquisición | Evidencia |
|---|---|---|
| Los 5 de desarrollo | **2026-05-07 y 2026-05-10** | `fecha_descarga` de `data/raw/manifiesto.csv`; los 161 `TO_actual` del manifiesto crudo son todos de 2026-05 |
| Los 152 | **2026-08-13** | commit de alta de `escalado_prep/descarga_log.json` (`111ed19`), coincidente con el mtime de `pdfs/` y de `indice_oficial_raw.json` |

```bash
git log --diff-filter=A --format="%ad %h" --date=short -- data/experiment/escalado_prep/descarga_log.json
python3 -c "import csv,collections; r=[x for x in csv.DictReader(open('data/raw/manifiesto.csv')) if x['categoria']=='TO_actual']; print(len(r), dict(collections.Counter(x['fecha_descarga'][:7] for x in r)))"
```

Verifiqué además que los PDFs del conjunto de desarrollo son byte-idénticos
entre `data/raw/`, `data/experiment/subset/` y el `sha256_pdf` del manifiesto,
así que la fecha del manifiesto crudo es efectivamente la de adquisición de los
archivos que el grafo usó.

**Lo que esto cambia para la exigencia 6, dicho sin maquillaje.** La ventana de
delta no es de ~6 meses sino de **~4 meses para los 5 del conjunto de
desarrollo** (mayo → hoy) y de **~3,5 semanas para los 152** (13/08 → hoy). La
ventana de los 152 es corta: es esperable que produzca pocos cambios, y esa es
una lectura honesta que conviene tener **antes** de correr, no después.

La consecuencia práctica es que la exigencia 6 se apoya, si el delta llega,
sobre los **5 del conjunto de desarrollo** —que son los que el grafo cubre y los
que tienen la ventana larga—, no sobre el volumen de los 152. Y hay una señal
previa que lo hace plausible: de los 5, **cuatro declaran su comunicación en la
portada** con fechas de texto ordenado que van de 2025-08-25 a 2026-05-06
(`ext` "A" 8307 al 25/08/2025; `cla` "A" 8378 al 19/12/2025; `cap` "A" 8418 al
09/04/26; `pro` "A" 8433 al 06/05/26). Un TO cuyo texto ordenado es de mayo de
2026 y fue bajado el 7 o el 10 de mayo es candidato razonable a haber
incorporado comunicaciones nuevas desde entonces.

Si el delta resulta vacío, eso también es un resultado publicable —el corpus se
mantuvo estable en la ventana— y la exigencia 6 tendría que buscar material por
otra vía. Pero eso se decide **con la medición hecha**, y la decisión de usar el
delta como validación temporal sigue siendo de la autora.

---

## 9. Hallazgos y límites, en una lista

1. **B1 del scraper no sirve como base del job**: replica una lista fija
   embebida en el código, y su `skip-existing` no detecta el caso «mismo path,
   PDF actualizado» —el caso que el job existe para detectar—. Camino propio,
   reusando patrones de cortesía y la regla de identidad. (§2.a.2)
2. **El índice no expone procedencia**, pero el PDF sí, en dos formas. Cobertura
   medida: **153 de 157**; **4** no la imprimen y quedan con límite declarado;
   **7** la imprimen pero sus dígitos no se extraen por glifos no mapeados. (§4)
3. **El pie de página da procedencia por página**, no por documento: es lo que
   habilita atribuir un cambio localizado a una comunicación concreta. **839 de
   1.076** páginas muestreadas lo llevan. (§4)
4. **`desarrollo_5tos.json` no trae URL** (0 de 5). Se resuelve por título
   exacto contra el índice sellado, mapeo materializado en
   `verificacion_alcance.json`. (§1)
5. **16 nodos del grafo están anclados en más de un TO**: no se pueden
   reemplazar por TO sin revisar el otro origen. Va como campo propio de la
   tabla. (§5.d)
6. **4 nodos y 4 aristas no son atribuibles a ningún TO** (vienen de
   `esquema_v2_clases.json`): quedan correctamente fuera del mapeo. (§5.a)
7. **La fecha «marzo de 2026» del corpus congelado no tiene respaldo** y el
   primer commit del repo (2026-04-26) la contradice. Las fechas ancladas son
   2026-05-07/10 para los 5 y 2026-08-13 para los 152, lo que **acorta la
   ventana de delta** —especialmente la de los 152, de ~3,5 semanas— y cambia
   lo que la exigencia 6 puede esperar. (§8)
8. **Una clase de cambio más que las cuatro del mandato** (`no_verificable`),
   para que un fallo de red no se registre como una baja regulatoria. (§3)
9. **El job no toca el grafo ni el inventario.** Produce el delta y el conjunto
   de partes afectadas, y se detiene. Aplicar la actualización es una release
   con laudo propio. (§0, §5.e)

---

## 10. Qué falta para la fase 2

El runner de la corrida (`code/correr_job.py`) y el adjudicador
(`code/adjudicar_deltas.py`) **no están escritos**: la fase 1 es diseño sin red
y sin código de descarga. Se escriben en la fase 2, que no arranca sin
aprobación explícita de este freno.
