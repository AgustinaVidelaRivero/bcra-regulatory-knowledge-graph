# Pre-registro de ESQ-3b — Verificación pre-congelado del esquema retocado

**FIRMADO por la autora — 02/09/2026** (lista final de R9 fijada en §0;
firmado ANTES de correr nada). Segundo tiempo del gate ESQ-3;
ejecuta el laudo ESQ-3a (`0a76549`) según la estructura aprobada
(`esq3_estructura_borrador.md`). Regla rectora: **ningún retoque entra al
esquema congelado sin sus dos brazos pasando.**

## §0. Lista final de R9 (decisión de autora, 02/09/2026, sobre la tabla de U-R9-FREQ)

**Dos valores nuevos** (el laudo fija un TECHO de 3, no una cuota: usar 2
es cumplimiento del laudo):

1. **`reporte_al_supervisor`** — anclado por el laudo ESQ-3a; daño
   documentado en f. 67 (reporte a la SEFyC etiquetado
   `comunicacion_a_cliente`: el esquema afirmaba algo falso; error ×3 con
   f. 13 y 45).
2. **`requisito_de_estructura`** — grupo `cont` de U-R9-FREQ: 22
   obligaciones, 20 unidades, 7 TOs. El deber de DISPONER de algo
   (políticas, procesos, sistemas, autorización previa): clase real,
   distinta de informar/calcular/asignar/comunicar, y discrimina en
   consulta.

**Rechazo fundado registrado**: `cumplimiento_normativo` (fusión de los
grupos `cumpl` + `observ`, ambos sobre el corte) queda FUERA por falta de
poder discriminativo — «deber de cumplir/observar normas» es coextensivo
con el tipo Obligacion mismo, y el riesgo concreto es que se convierta en
el nuevo cajón por defecto, reemplazando «otra» sin ganancia informativa
(la caja válida escondería que no hubo clasificación: la versión en enum
del hallazgo conforme ≠ fiel). La lectura alternativa de la mesa (son
obligaciones que REMITEN a otra norma en vez de prescribir conducta, y esa
distinción podría interesar en consulta) queda registrada como argumento
considerado y no adoptado, **promovible en r2 si la evidencia de uso lo
pide**.

**Nota del proceso de adjudicación** (registrada a pedido de la autora):
la autora había despachado los tres grupos que pasaron el corte como
«gramática, no subtipos», y la mesa corrigió esa lectura para `cont` — el
contenido de ese grupo sí es una clase de deber; el despacho se había
hecho por superficie verbal y no por contenido.

**Adjudicación de la lectura sellada de la autora: RESULTADO INTERMEDIO.**
Ninguna de las dos ramas disparó limpia: pasaron 3 grupos pero al borde
del corte (15–20 unidades contra mínimo de 15; el mayor es el 4 % de
«otra»), con **233 de 236 grupos por debajo**. La cola larga es el
hallazgo y va a **C1.7** sin reinterpretar la lectura previa: el grueso de
las obligaciones del corpus no se subtipa con lista cerrada; el enum
captura clases frecuentes y honestas, no agota el espacio.

**Dato de registro para el laudo de congelado**: U-R9-FREQ detectó
`registro_contable` (2 apariciones, 1 unidad, prevmi) **fuera del enum
vigente** — `properties.tipo` funciona hoy como texto libre, no como
clasificación validada; el endurecimiento del validador es territorio B5,
no de este pre-registro.

**Lectura sellada por la autora ANTES de ver la tabla de U-R9-FREQ** (para
que el resultado no se interprete a posteriori): si tres o más grupos
superan el corte holgadamente, el 76 % de «otra» era vocabulario faltante
y R9 lo corrige. Si ningún grupo llega al corte, el 76 % NO es un problema
de valores del enum sino de que las obligaciones del corpus no se dejan
subtipar con una lista cerrada — y eso es un **hallazgo para el capítulo
del esquema (C1.7)**, no un fracaso del retoque.

## §1. Objeto y diseño

Re-extracción **pareada**: mismas unidades, prompt viejo (extracciones ya
persistidas en `cobertura/`, sellos `a7788c1` — brazo base a costo cero)
vs prompt retocado (esquema del laudo ESQ-3a). Mide **fidelidad de
extracción** (cláusula §2 del laudo): NO evalúa respuestas del agente; el
efecto en respuestas sería otra unidad, con expectativa declarada de
no-movimiento.

## §2. Brazo OBJETIVO — unidades y predicciones selladas por retoque

Las unidades se derivan mecánicamente del worksheet (`ficha n → chunk_id`).
Cada predicción se adjudica por separado; un retoque PASA su objetivo si
su(s) predicción(es) se cumplen en la extracción nueva.

- **R1 (Potestad)** — unidades de f. 26 y f. 15. Predicciones: la
  habilitación «podrán negociar contratos de opciones» (f. 26) produce un
  nodo Potestad; «se encuentran facultadas para» (f. 15) deja de tipar
  como Obligacion y cae en Potestad.
- **R2 (Condicion + condicion_de)** — unidad de f. 39. Predicción: la
  unidad produce Condicion, no una Obligacion con deber autónomo (el
  vínculo cross-unidad queda para E3, que ahora tiene firma posible).
- **R3 (Definicion)** — unidades de f. 25 y f. 46; contraste f. 37.
  Predicciones: f. 25 y f. 46 producen nodo Definicion con el término
  (en f. 46, «cuenta de registro»); **anti-atracción específica**: el
  atesoramiento de f. 37 SIGUE en Operacion.
- **R4 (regla de omisión de meta-normativo)** — unidades de f. 46 y
  f. 19. Predicción: la cláusula interpretativa (f. 46) y la finalidad
  (f. 19) no generan ningún nodo prescriptivo (Restriccion/Obligacion);
  la pérdida aparece como omisión (cota superior), no como falsedad.
- **R5 (partición consecuencias)** — unidades de f. 63 y f. 38.
  Predicciones: la revocación discrecional (f. 63) cae en Potestad; las
  consecuencias prohibitivas (f. 38) siguen en Restriccion. Si la
  partición no cubre, R5 se reabre en el laudo de congelado (no se
  improvisa un tipo).
- **R6a (exceptua_operacion)** — unidad de f. 44 (chunk-local limpia);
  corroboran f. 62 y f. 65. Predicción: las tres Excepcion de f. 44
  emiten `exceptua_operacion` hacia las tres Operacion del mismo chunk.
- **R7 (descripcion en Operacion)** — unidad de f. 32. Predicción: «con
  personal y/o recursos técnicos propios» se aloja en la descripcion de
  la Operacion.
- **R8 (dominio de aplica_a)** — unidades de las 75 fichas cuyas
  extracciones persistidas contienen tripletas `aplica_a` descartadas por
  `firma_invalida` (derivación mecánica desde el campo de validación; 11
  tripletas medidas transversalmente, f. 39). Predicción: esas tripletas
  se emiten como válidas en la extracción nueva.
- **R9 (enum de subtipo)** — unidad de f. 67. Predicción: el nodo del
  reporte a la SEFyC no vuelve a `comunicacion_a_cliente`.

## §3. Brazo REGRESIÓN — selección mecánica y regla sellada

- **Selección** (mecánica, sellada acá): todas las fichas con
  q1 = sí_completo y q2 = ninguna, más — hasta completar **35 unidades** —
  fichas azarosas con q2 = ninguna en orden por `chunk_id`; excluidas las
  unidades del brazo objetivo. La lista exacta se deriva del worksheet y
  se persiste antes de correr.
- **Métrica** (robusta al ruido inherente de re-extracción, P1″): se mide
  **migración a caja nueva** — ninguna entidad hoy bien tipada debe
  aparecer re-tipada en un tipo nuevo del laudo (Potestad, Condicion,
  Definicion) ni desaparecer reemplazada por un nodo de tipo nuevo.
  Variaciones de label/descripcion sin cambio de tipo NO cuentan como
  falla (ruido base conocido).
- **Predicción única sellada**: «las unidades del brazo de regresión no
  cambian de tipo ni pierden relaciones válidas».
- **Falla del brazo**: ≥1 migración a caja nueva adjudicada INCORRECTA
  por la autora.
- **REGLA SELLADA (verbatim del diseño aprobado)**: «si el brazo de
  regresión falla, el retoque se revisa aunque el objetivo pase». La
  revisión ajusta la definición/delimitación del tipo que atrajo, re-sella
  su predicción y re-corre SOLO ese par, bajo el mismo tope.

## §4. Adjudicación

- **De la autora, exclusivamente**, con fichas pareadas viejo-vs-nuevo por
  unidad (patrón de ESQ-2; el ejecutor arma las fichas, no adjudica).
- **Regla de cegado (entrada 10 de la cola)**: ninguna lectura ajena
  visible durante la adjudicación; el spot-check de mesa es posterior e
  independiente (semilla declarada al momento).
- **Instrumento (entrada 11)**: el arreglo para textos largos se
  implementa y verifica ANTES de esta lectura (multilínea o archivo;
  selftest que pruebe > 1024 bytes sin pérdida).
- **DUDA**: categoría propia, no cuenta para ningún lado, se lista.

## §5. Costo y tope

Volumen: ~9–12 unidades objetivo + 35 regresión ≈ 45–50 re-extracciones
con prefijo nuevo (namespace de caché nuevo; decisiones de
`docs/decisiones_caching_extraccion.md` vinculantes; patrón llm-capture,
db propia de la unidad). Estimación ≈ USD 0,30 (0,0054/unidad promedio de
ESQ-2 + escritura de prefijo). **TOPE PROPIO: USD 1,00**, dentro del
remanente de la saga ESQ (van 5,03 de 9,00). Re-corridas de pares
revisados (§3) van contra el mismo tope.

## §6. Salida y decisión

Tabla por retoque: objetivo PASA/NO PASA · regresión PASA/FALLA · veredicto
(entra / se revisa / se rechaza). Con los dos brazos pasando para el
conjunto final de retoques: **laudo de esquema congelado** (sha del
esquema, posición de la exigencia 10, política post-congelado §8 del laudo
ESQ-3a). Un retoque rechazado en ESQ-3b NO frena a los demás: la lista
final del congelado es el subconjunto que pasó.

## §7. Artefactos

Pre-registro (este archivo, firmado ANTES de correr) · código de la unidad
en `esq/code/` · db de caché propia (ignorada, con sellos sha256) · fichas
pareadas · tabla de resultados por retoque · reporte del ejecutor con
freno antes de toda adjudicación.

## Firma

Firmado por la autora, 02/09/2026, con el §0 completo (lista de R9,
rechazo fundado de la fusión tautológica, adjudicación del resultado
intermedio). Las predicciones de §2, la selección y regla de regresión de
§3 y el tope de §5 quedan sellados: ninguna se modifica después de la
primera llamada de la corrida.

## Adenda 1 — laudos del freno 1 de U-ESQ-3b (post-sello `01bf046`)

**FIRMADA por la autora — 02/09/2026.** Corrige y completa por declaración,
ANTES de toda llamada de la corrida (gasto a la fecha del freno 1:
USD 0,00). Sellos del manifiesto del freno 1: prefijo retocado sha256
`fc53fd8f8a2022c4…` (24.241 chars; producción `427f6473cc53bba5…`), hash
de prefijo (system+tools) `4793d6152608` → `f0a421fb9466`, namespace
`esq3b_pareado_e1|cv=esq3b-pareado-v1-pf0a421fb9466|think=0`.

1. **Dominio de `establecida_en`**: `Condicion` y `Definicion` entran al
   dominio junto con `Potestad` — **decisión de autora**, no de
   implementación (deja de ser la decisión declarada unilateral del
   ejecutor). Fundamento: analogía con el dominio de producción (todo tipo
   de contenido ancla al TextoOrdenado) y no fabricar huérfanos por
   construcción (defecto medido en la f. 40).
2. **Brazo de regresión — fe de erratas del §3**: el «35» original era el
   conteo bruto de fichas q2=ninguna del worksheet SIN aplicar la
   exclusión del brazo objetivo; con la exclusión, la regla sellada
   producía 22 y 35 era inalcanzable por construcción. **Regla
   corregida**: el completado se abre a fichas **dirigidas** con
   q2=ninguna, en orden de `chunk_id`, DESPUÉS de las azarosas, hasta 35;
   con el worksheet actual eso da **26 unidades**. El ejecutor re-deriva y
   re-persiste la selección con sha nuevo. La métrica (migración a caja
   nueva), la predicción única y la regla de falla del §3 **no cambian**.
3. **R6a — alcance del veredicto**: las unidades de las f. 62 y f. 65
   quedan en el brazo objetivo como **corroboración sin predicción
   sellada**: fila aparte en la tabla de resultados y NO cuentan para el
   veredicto de R6a, que se adjudica **solo sobre la f. 44**.
4. **R8 — reconciliación numérica (sin cambio de selección)**: las «11
   tripletas» citadas (f. 39) son 9 `firma_invalida` + 2
   `sujeto_extremo_invalido` (verificado por recomputo independiente de
   mesa); R8 aplica a las 4 `aplica_a` con firma inválida — todas
   `Operacion --aplica_a--> Sujeto` — en las unidades de las f. 21, 24,
   32 y 66.
5. **Cuestionario de las fichas pareadas — APROBADO**: las tres preguntas
   del ejecutor (¿cambió la extracción? / fidelidad mejora–empeora–igual /
   migración a caja nueva correcta–incorrecta), con **DUDA como respuesta
   válida en las tres** (regla del §4: no cuenta para ningún lado, se
   lista) y un campo de **observaciones libre por unidad** (patrón ESQ-2).
   Sin campo de brazo, retoque ni origen.

**Costo estimado actualizado**: 43 unidades a re-extraer (17 objetivo +
26 regresión) ≈ **USD 0,35** contra tope USD 1,00 (fórmula del manifiesto
del freno 1: lecturas por unidad ancladas en el usage real de ESQ-2 +
techo de 4 escrituras de prefijo).
