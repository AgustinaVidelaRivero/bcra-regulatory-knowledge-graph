# Enmienda al pre-registro de la tanda 0 — partición de la fase 2 en 2a y 2b, y arranque de 2a sin esperar la respuesta del mentor

**FIRMADO por la autora — 2026-09-27** · Fecha: 2026-09-27.

Enmienda con fecha a `docs/preregistro_tanda0.md` (FIRMADO por la autora el
2026-09-25, sellado en `c80b03f`, sha256 `4b45145d…`), a la enmienda de la
observación (12) (`docs/enmienda_preregistro_tanda0_2026-09-27_observacion12.md`,
sellada en `8e13be3`) y a la fila B6.0 del plan. Ninguno de los tres se
edita: esta enmienda vive al lado y se lee junto con ellos, por la cláusula
de cierre del pre-registro (`:909-911`, «toda modificación posterior es
enmienda separada, nunca ajuste silencioso»). Se escribe antes de que la
fase 2 arranque.

## 1. Lo que hoy dice el pre-registro, y el plan, transcrito tal como está

A1, alcance (`:34-35`): «… con sus sub-ítems `:662` (fase 1: diseño y
pre-registro, sin correr) y `:663` (fase 2: corrida y lectura, detrás del
aviso al mentor).»

A1, tercer punto (`:51-56`): «**La autora lee los cinco documentos** para
escribir preguntas y criterios sobre ellos (segunda parte de esta fase 1,
posterior a este pre-registro). Esa lectura **no toca el esquema ni anota el
grafo**: produce el material de evaluación, no el objeto evaluado. Las
preguntas se escriben y sellan antes de correr (`:661`: «preguntas nuevas
sobre esos 5 documentos, escritas y selladas antes de correr»).»

A5, regla (`:608-610`): «Regla: **la fase 2 no arranca con instrumentos
PENDIENTES.** Cada PENDIENTE de esta tabla es un gate técnico de A9 que se
cierra por su unidad del plan o por el mandato de fase 2, y se reporta
cerrado antes del ok de la autora.»

A9, pasos 2 y 3 (`:883-887`): «2. **Preguntas de la segunda parte de la fase
1 selladas**: la autora lee los cinco documentos, escribe preguntas y
criterios, y se sellan por commit antes de correr; la estimación de A7 se
revisa con su número. 3. **Ok escrito de la autora**, que a su vez espera
respuesta del mentor (decisión 5: la corrida no arranca sin ese ok).»

Decisión 5, tal como la transcribe el plan en la fila de gates técnicos de
B6.0: «La fase 2 (corrida) no arranca sin ok escrito de la autora, que a su
vez espera respuesta del mentor.»

Plan, sub-ítem de B6.0 (hoy `:696`; el ancla es el id): «**B6.0 fase 2 —
corrida y lectura**, detrás del aviso al mentor; reporte como validación de
diseño.»

Enmienda de la observación (12), §2.3: el sorteo (paso 4bis) inmediatamente
después del ensamblado de la tanda 0 sola y sellado por commit antes de
toda lectura; la lectura de las 30 aristas por la autora como parte del
paso 7.

## 2. Texto nuevo — decisión de la autora del 27/09/2026

### 2.1 La fase 2 se parte en 2a y 2b

**Fase 2a — corrida y lectura de la tanda 0 (arranca hoy).** Contiene: los
gates técnicos 1, 5 y 7 de A5 (cableado de r1 en el ensamblador, registro y
carga en Neo4j de los grafos nuevos, manifiesto de la tanda 0), que se
cierran dentro de 2a, cada uno con FRENO antes de la etapa que gasta; la
corrida completa E0 a E5 sobre los diez TOs con perfil `v3_b54` y esquema
congelado; los tres ensamblados determinísticos de A3.5; el gate de release
de A9 paso 5 (shapes con perfil congelado, regression suite sin `--esperado`
con salida como línea de base observada, intrínsecas `--gen3`, indicadores
de cita); el sorteo sellado de la observación (12) (paso 4bis); las celdas
C2, C3 y C4 con su juez, una corrida cada una; la celda C5 si sus preguntas
llegan selladas a tiempo (2.3); y la lectura de las observaciones (10) y
(11) y de las vigilancias (1) a (9) contra A4. Tope USD 100 (decisión 7). Ok
escrito de la autora **sin esperar la respuesta del mentor**, que está
leyendo el capítulo 3 y será informado después con el reporte de 2a.

**Fase 2b — preguntas nuevas sobre los cinco (segunda parte de la fase 1) y
su evaluación.** Las preguntas y criterios **no los escribe la autora: los
genera una instancia sin contexto del repo, del grafo ni de esta
conversación, a partir de los PDF de los cinco documentos**, con el mismo
procedimiento con que se generaron las 40 de EV2
(`data/experiment/exploracion/ev2_fidelidad/registro_generacion_ev2_fidelidad.md`
§1 aislamiento y fuentes, §4 procedimiento y semilla: una pregunta natural
por unidad seleccionada, ancla exacta y 2 a 5 criterios verificables con
cita textual del PDF, orden de unidades por semilla declarada). La autora
las revisa y aprueba, se clasifican con la regla v2 (`41abf18`) por el
procedimiento de U-EV2-TIPO (clasificación a ciegas más control del modelo)
con las cuotas de la decisión del 25/09 (al menos una de varios puntos por
documento y dos de abstención en total), y se sellan por commit **antes de
correrlas**. La ceguera respecto de las salidas de 2a queda garantizada
**por construcción**: la instancia que genera no ve el repo ni el grafo ni
esta conversación; la autora aprueba preguntas, no lee salidas. La
evaluación de esas preguntas (cuando no entren como C5 en 2a, 2.3) y la
**lectura de las 30 aristas de la observación (12)** (paso 7 de su enmienda)
quedan en 2b. El sorteo de las 30 se sella en 2a; la autora no lo lee hasta
2b.

### 2.2 Qué reemplaza esta enmienda

- **Decisión 5** pasa a: «La fase 2a arranca con ok escrito de la autora,
  sin esperar la respuesta del mentor, que será informado con el reporte de
  2a. La fase 2b arranca con las preguntas nuevas selladas por commit.»
- **A1, tercer punto, y A9 paso 2**: «la autora lee los cinco documentos
  para escribir preguntas y criterios … escritas y selladas antes de
  correr» pasa a «las preguntas las genera una instancia aislada a partir
  de los PDF, la autora las revisa y aprueba, se clasifican con la regla v2
  y se sellan por commit antes de correrlas». La corrida de extracción (2a)
  puede preceder al sellado de las preguntas; lo que se preserva es que el
  objeto evaluado no se toca (A1, «es caja negra») y que quien genera las
  preguntas no ve ninguna salida de 2a. Este es un apartamiento del orden
  sellado en A9 y se declara como tal.
- **A5, regla**: «la fase 2 no arranca con instrumentos PENDIENTES» pasa a
  «la fase 2a arranca con los instrumentos 2, 3, 4, 6 y 8 en verde (commits
  `f4c8e93`, `2012832`, `271f324`, `a48d229`, `d3f7d2e`); los instrumentos
  1, 5 y 7 se cierran dentro de 2a, con FRENO y reporte antes de la primera
  etapa que gasta, y ninguna etapa que gasta arranca con un instrumento de
  su etapa PENDIENTE».
- **A5, dos instrumentos que el pre-registro no listó y 2a necesita,
  agregados como PENDIENTES 9 y 10, USD 0, a cerrar dentro de 2a antes de
  E5**: (9) registro en memoria de los grafos nuevos para el runner en
  memoria de C3 y C5 (patrón `ev2_r1/code/comun_r1.py:148-158`: entrada en
  `GRAFOS` y vista runtime con la provenance mapeada), porque `runner_ev2`
  y `comun_ev2` solo conocen los grafos sellados; (10) juez v1 y
  re-corridas del §7 parametrizados por módulo nuevo para las celdas C2 a
  C5, porque `ev2_r1/code/juez_r1.py:46` y `enc_r1.py` cablean las trazas,
  labels, dbs y sales de r1.
- **A9**: el paso 2 (preguntas selladas) deja de ser prerrequisito de la
  corrida y pasa a condición de la celda C5 (2.3) o a 2b; el paso 3 pasa a
  «ok escrito de la autora para 2a»; entre los pasos 4 y 5 queda el 4bis de
  la enmienda (12); el paso 6 admite C5 (2.3); el paso 7 se parte: (10),
  (11) y vigilancias en 2a, lectura de (12) en 2b; el paso 8 se emite dos
  veces, un reporte de 2a y uno de 2b.
- **Plan, sub-ítem «B6.0 fase 2 — corrida y lectura, detrás del aviso al
  mentor»**: pasa a dos sub-ítems, «fase 2a — corrida y lectura, con ok
  escrito de la autora; el mentor es informado con el reporte» y «fase 2b —
  preguntas nuevas generadas por instancia aislada, aprobadas por la autora,
  selladas antes de correrlas; evaluación y lectura de (12)». Se asienta en
  el plan con esta enmienda sellada.

### 2.3 Celda C5, condicional al sellado de las preguntas

Si las preguntas nuevas sobre los cinco quedan **selladas por commit antes
de la etapa E5 del mandato de 2a** (revisadas y aprobadas por la autora,
clasificadas con la regla v2), **se corren en 2a como celda C5**: grafo
`ens_diez/r1/kg.json` (el ensamblado de los diez TOs, A3.5), runner en
memoria (`GraphIndex`, harness congelado firma v1), el mismo juez v1
`fd446f8e…` N=3 voto modal y las re-corridas del §7 con su juez, una sola
corrida, dentro del tope parcial de E5, que para ese caso se amplía de
USD 30 a **USD 40** (referencia A7.3: USD 0,18 por pregunta). Si no están
selladas al llegar a E5, C5 no se corre en 2a y la evaluación queda en 2b,
con tope propio. En ningún caso E5 espera a las preguntas: el orden de 2a
no se detiene por 2b.

### 2.4 Costo

La estimación de 2a es la de A7 sin las preguntas nuevas: **USD 69,18**
(extracción 47,31, tres celdas de EV2 21,87), bajo el tope de USD 100. Si
C5 entra en 2a, suma su costo dentro del tope parcial ampliado de E5 (2.3)
y el total sigue bajo los 100 (A7.3: ≈ 76,5 con 40 preguntas). Freno por
proyección en cada etapa; gasto real desde las dbs.

## 3. Qué no cambia

- Las cuatro celdas C1 a C4, sus componentes fijos (harness congelado firma
  v1, juez v1 `fd446f8e…` N=3 modal), la configuración de Neo4j (A3.2), las
  comparaciones por pares (A3.3) y el uso único de EV2 (A3.4, principio 7).
  C5 no compara con C1 a C4: mide preguntas distintas sobre un grafo
  distinto y se reporta aparte.
- La decisión 6, las observaciones (10) y (11), las vigilancias (1) a (9) y
  la observación (12) con su sorteo sellado antes de toda lectura.
- A8: nada de 2a autoriza abrir la ventana del §7 por sí solo; la vía es la
  de A8.
- El esquema congelado y el grafo de la tanda 0 no se anotan ni se corrigen
  a mano; las preguntas de 2b no informan el esquema.
- El tope de USD 100 (decisión 7) y el registro del id de modelo devuelto
  por la API por llamada (A6, regla de C1.9).
- El reporte de 2a se publica como validación de diseño, no como resultado
  de la tesis (A1).

## Firma

Firmada por la autora el 2026-09-27.
