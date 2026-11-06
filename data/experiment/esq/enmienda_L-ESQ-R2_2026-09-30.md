# Enmienda al laudo de esquema congelado — L-ESQ-R2: el esquema de la release r2

**FIRMADA por la autora** el 01/10/2026 · Redactada: 2026-09-30.

Enmienda con fecha al laudo `data/experiment/esq/laudo_esquema_congelado.md` (FIRMADO 03/09/2026, sellado
en `2593d4d`). El laudo no se edita: esta enmienda vive al lado y se lee junto con él y con sus dos enmiendas
firmadas, la del 25/09 (`enmienda_ventana_correccion_2026-09-25.md`, `c80b03f`) y la de uso de la ventana del
30/09 (`enmienda_uso_ventana_2026-09-30.md`, `30f106c`). Es la unidad 5 del ciclo de corrección posterior a la
tanda 0 (plan, fila B2.11, `docs/plan_tesis.md:394` en `9e411a0`).

**Cómo leerlo.** Hay una sección por decisión. Cada una tiene cinco partes:
1. qué dicen los documentos del BCRA y qué midió el pipeline, con la unidad y el commit que lo respaldan;
2. las opciones;
3. la orientación de la autora ya registrada en el plan (fila B2.11, unidad 5) y, donde no la había, la
   **Decisión de la autora (30/09)**. Ni una ni otra reemplazan la firma: la decisión formal es la firma de
   este laudo;
4. qué va a código sobre la salida guardada (**r2a**) y qué exige el prompt nuevo con re-extracción (**r2b**);
5. qué cambia en la suite de regresión y en las shapes.

Rótulos: **NO MEDIDO** (dato que ninguna unidad midió, con la unidad que lo mediría). Toda cifra lleva su
artefacto; las de los artefactos se reproducen con el comando que cada uno declara.

**Criterio general de las decisiones de la autora del 30/09.** El esquema se decide por lo que dicen los
documentos (principio 11). El prompt queda completo, para no tener que volver a cambiarlo. Todo lo que se puede
decidir en código se decide en código, sobre la salida guardada (principio 12).

---

## 0. Contexto para leer sin el repo

### 0.1 El pipeline, una línea por etapa

- **E0** segmenta cada Texto Ordenado (TO) del BCRA en unidades (chunks) por su numeración. Marca los chunks con
  tabla o fórmula y les agrega el contexto heredado de sus puntos padre. Un parser aparte, `e0_tablas`, detecta
  tablas lógicas, pero hoy no está conectado a las marcas de E0.
- **E1** es un modelo (Claude Haiku) que extrae de cada chunk entidades y relaciones. Usa un prompt cuyo
  **prefijo** está sellado por hash (la caché y la reproducibilidad dependen de él) y un **tool schema** que fija
  la forma de la salida. Un **validador** en código rechaza lo que no cumple: tipo, predicado, firma
  dominio → rango y catálogo de sujetos.
- **E3** es un verificador (otro llamado al modelo) que contrasta la extracción con el chunk; si falla, E1
  reintenta.
- **E2** reduce y fusiona los nodos de todos los chunks en un grafo por TO.
- **E4** resuelve en código los sujetos que E1 propuso fuera del catálogo; **E5** agrega el esqueleto (TOs,
  roles, jerarquía de sujetos).
- El **agente** responde preguntas navegando el grafo con tres herramientas: `buscar_nodos`, `ver_nodo` y
  `ver_vecinos`.

### 0.2 El esquema congelado hoy

- **Tipos y propiedades** (prefijo v3, `data/experiment/b54_catalogo_v3/code/prompt_v3_b54.py`,
  `PREFIJO_SISTEMA_V3`, líneas 12-44 del texto; idéntico al prefijo congelado `e69feaaa…` fuera del bloque
  de catálogo y del enum, según el selftest de B5.4):

  | tipo | propiedades |
  |---|---|
  | Comunicacion | `codigo`, `tipo` («A», «B» o «C»), `numero` |
  | TextoOrdenado | `materia`, `archivo`, `version` |
  | Operacion | `tipo` (texto libre), `descripcion` |
  | Restriccion | `descripcion`, `tipo` («prohibicion», «limite_cuantitativo» o «limite_cualitativo»), `umbral` opcional |
  | Excepcion | `descripcion` |
  | Obligacion | `descripcion`, `tipo` (6 valores: «presentacion_informativa», «calculo», «asignacion», «comunicacion_a_cliente», «reporte_al_supervisor», «otra»), plazo o frecuencia opcional |
  | Potestad | `descripcion` |
  | Condicion | `descripcion` |
  | Definicion | `termino`, `descripcion` |

- **Predicados y matriz de firmas** (`data/experiment/esq/code/prompt_congelado.py:96-109`, la del v2 sin
  cambio): `establecida_en` (normas y Operacion → TextoOrdenado); `referencia` y `modificada_por`
  (TextoOrdenado → Comunicacion); `aplica_a` ({Excepcion, Obligacion, Operacion, Potestad, Restriccion} →
  Sujeto); `regula` ({Obligacion, Restriccion} → Operacion); `exceptua` (Excepcion → Restriccion);
  `exceptua_obligacion` (Excepcion → Obligacion); `prohibe` y `limita` (Restriccion → Operacion); `ejecuta`
  (Sujeto → Operacion); `requiere` (Operacion → Obligacion); `condiciona` (Obligacion → Operacion);
  `condicion_de` (Condicion → {Excepcion, Obligacion, Restriccion}).
- **Catálogo de sujetos v3**: 102 ids en el bloque del prompt (62 clases, 5 instancias y 35 roles; laudos de
  B5.4, `dea56ba` y `docs/laudo_B5.4_cierre_catalogo.md`). El modelo elige el `sujeto_id` de ese bloque.
- **Regla 9**: el contenido meta-normativo no se extrae (R4 del laudo, regla de omisión declarada).
- **El tool schema** declara las `properties` de una entidad como valores string
  (`data/experiment/reextraccion_v2/e1_extractor/prompt_e1.py:288-292`) y no admite `properties` en las
  relaciones (`additionalProperties: false`, `:323`).

### 0.3 La ventana y el ciclo B2.11

- El §7 del laudo admite un único ciclo de corrección del esquema, con re-extracción, antes de sellar el
  pre-registro de la evaluación final (B6.3). Este ciclo la usa (enmienda de uso de la ventana, `30f106c`).
  La tanda 1 corre sin ventana, y los cinco documentos de la tanda 0 salen del conjunto fresco de B6.3 (a).
- La corrección en código sobre la salida ya guardada, sin cambiar el prefijo ni el formato de salida de E1,
  no consume la ventana (misma enmienda, §2.7).
- Después del ciclo, un cambio de esquema, prefijo o formato es release posterior declarada y no entra al
  grafo que evalúa B6.3 (§3.3).
- **r2a** es la medición solo con código, a USD 0, sobre la salida guardada de la tanda 0 (plan, B2.11,
  unidad 9). **r2b** es el prompt nuevo (unidad 10) más la re-extracción de los diez TOs de la tanda 0
  (unidad 11).
- Rigen dos principios del plan (`docs/plan_tesis.md:298-299` en `9e411a0`):
  - **11**: el esquema se decide por el contenido y el uso de los documentos, no por el pipeline; un límite
    del extractor se declara como límite del pipeline y no se resuelve recortando el esquema;
  - **12**: toda regla determinística sobre la salida guardada vive en código y se re-aplica sin re-extraer;
    el prompt lleva lo que el modelo necesita para extraer y lo que hace falta guardar para reprocesar.

### 0.4 El principio 11 frente al principio de gobierno del §1

El §1 del laudo dice: «Se retira lo que produce falsedad en campo estructurado en material fresco; se acepta
con residuo declarado lo que produce omisión visible o error con tasa medida y balance favorable; nada entra
al congelado con delimitaciones sin verificar.» Con esa regla salió `requisito_de_estructura`: el extractor lo
llenaba mal, no porque los documentos no tuvieran la categoría.

El principio 11 pide lo contrario para ese caso: un límite del extractor se declara y no recorta el esquema.
Los dos se pueden leer juntos de dos maneras:
- **(A)** el principio 11 decide qué debe representar el esquema; el §1 decide qué entra a una release
  sellada. Una categoría que el extractor no llena con fiabilidad queda en el diseño como límite declarado del
  pipeline, sin emitirse hasta verificarse;
- **(B)** el principio 11 reemplaza la cláusula de retiro del §1 para las decisiones de este ciclo.

**Decisión de la autora (30/09): lectura (A).** El principio 11 decide qué representa el esquema; el §1 decide
qué se emite en una release sellada. Una categoría que el extractor no llena con fiabilidad queda en el diseño
como límite declarado del pipeline, sin emitirse hasta verificarse. Esta lectura rige las secciones 2
(Obligacion.tipo) y 8 (R6b).

### 0.5 Grafos y grupos de las cifras

- **desarrollo**: KG-Tanda0-Desarrollo-r1 (`eab2fdd0…`), los cinco TOs de desarrollo con el pipeline de la
  tanda 0.
- **diez**: KG-Tanda0-Diez-r1 (`dd42d6d9…`) o el crudo de E1 de los diez TOs de la tanda 0.
- **cinco**: los cinco TOs de la tanda 0 sola (`4097d4fd…`).
- **r1**: KG-Reextraído-r1 (`0226e947…`), la generación anterior del pipeline.
- Capas: crudo del primer intento de E1, entrada de E2 y grafo.

---

## 1. Umbrales

### 1.1 Qué dicen los documentos y qué midió el pipeline

Fuentes: U-UMBRAL, U1 (`e81ed69`, `reports/u_umbral/u1_mediciones.json`) y U2 (`e4d053b`,
`reports/u_umbral/u2_muestra_trazas.json` y `reporte_u_umbral.md`). Cifras de desarrollo salvo aviso.
Denominadores: U-UMBRAL usa 605 nodos con cuantía; el tablero corregido cita 606, por un nodo con «diez (10)
años» que la regex del mandato no veía. En la tesis se citan los del tablero.

- **Los documentos.**
  - Los umbrales son frecuentes: 605 nodos con cuantía (638 en r1, 682 en diez).
  - A menudo son relativos a otro valor: 122 de 605, como «25 % de la RPC» (135 de 638 en r1, 128 de 682 en
    diez) [U2: `dim_relacionales`].
  - A veces hay varios en un mismo punto: 34 de los 287 nodos sin campo tienen más de un valor [U1:
    `medicion_6`].
  - Algunos viven en tablas: en `cap::1.2`, el parser asigna Bancos 5.000 y Restantes entidades 2.500, y las
    dos Restricciones del grafo tienen los montos invertidos [U2: `cap_1_2_contra_tabla`].
- **El campo actual.**
  - Solo Restriccion (`umbral`) y Obligacion (plazo) tienen dónde llevar el valor. Hay 177 nodos con cuantía
    en Condicion (134) y Excepcion (43), tipos sin campo [U1: `medicion_3`].
  - El campo no es literal en buena parte de los casos: 219 de 498 campos están en la descripción y en el
    texto de E0. Obligacion.plazo: 76 de 248; 156 no están en ninguno de los dos textos; 28 tienen un valor de
    relleno [U1: `medicion_1`].
  - El agente no ve el campo en el resumen de `buscar_nodos`, que muestra los primeros 160 caracteres de la
    descripción (`data/experiment/evaluacion/harness.py:110-124`). En 157 de 605 nodos todas las cuantías
    empiezan después del carácter 160 [U1: `medicion_3`].
- **La relación como alternativa.**
  - Falta la arista portadora en 62 de 248 Restricciones con umbral sin `limita`, en 77 de 134 Condiciones con
    cuantía sin `condicion_de`, en 170 de 248 Obligacion con plazo sin `regula` ni `condiciona` y en 21 de 43
    Excepciones con cuantía sin `exceptua` [U1: `limita`; U2: `cobertura_otros_portadores`].
  - `limita` es inestable entre generaciones: 1.041 aristas en r1 y 284 en desarrollo [U1: `limita`].
  - Ninguna implementación de `ver_vecinos` devuelve atributos de arista, y la del harness está sellada.
- **El uso.**
  - En los 8 criterios de EV2 con cuantía, el valor ya está en nodos del ancla. Por celda (C3 y C4): llega en
    3; se pierde en la búsqueda en 4; el octavo se pierde en la generación (C3) o en la navegación (C4) [U2:
    `medicion_5`]. EV2 es material de desarrollo: esto es un diagnóstico, no un resultado (principio 7).
  - En las tres corridas del agente sobre el ejemplo del préstamo (U-MED-EJEMPLO-2, sobre r1), dos
    invirtieron la regla (`reports/u_insumos_cap/recorrido_prestamo.md:200-202`, `f32f20c`).
- **El llenado en código.**
  - Un prototipo por regex coincide con el campo en 295 de 498 casos y no difiere en ninguno.
  - Extrae un solo valor en 240 de los 287 nodos sin campo y no extrae nada en 13 [U1: `medicion_6`].
  - Verificado contra `e0_tablas`, detecta la inversión de `cap::1.2`. Verificado solo contra la descripción,
    la copia [U1: `medicion_6`; U2: `cap_1_2_contra_tabla`].

**Precisión de `limita`** (U-LECTURA-LIMITA; plan, B2.11, unidad 4b, cerrada; mandato
`docs/mandatos/ULECTURA_LIMITA_lectura_asistida.md`, firmado en `67a9e6b`; lectura en `bf4709d`).
- Es la lectura asistida de la muestra sellada de 30 aristas de desarrollo
  (`reports/u_umbral/muestra_limita_30.csv`, sha256 `8e981817…`, igual al inicio y al cierre): si el destino es
  el objeto del tope.
- Leyó una instancia de modelo y revisó la autora. Modelo y versión de la instancia: `claude-opus-5-5`
  (Claude Opus 5.5), confirmado por la autora el 30/09 con el registro de la sesión de Claude Code
  `deda25f2-7092-4eb5-acd8-56ae8d1fba91.jsonl`: 117 entradas de respuesta (53 mensajes distintos), todas con
  ese modelo. Es la única sesión del proyecto que escribió `conteo_lectura.py`.
- Resultado en `reports/u_umbral/lectura_limita/resultado_lectura_limita.md`. Comando:
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B reports/u_umbral/lectura_limita/conteo_lectura.py`.

| medida | valor |
|---|---|
| «sí» / «no» / «no decidible» sobre 30 | 21 / 7 / 2 |
| Wilson al 95 % de «sí» | sobre los 30: 21 de 30, 0,521–0,833; sobre los 28 decididos: 21 de 28, 0,566–0,873 |
| revisión de la autora (30/09) | sin cambios. Aceptó los seis casos límite (filas 8, 9, 14, 17, 20 y 21) contra el texto de E0 y la precisión de «tope» declarada para esta lectura |

Es una fracción sobre n = 30, de una sola muestra de un solo grafo, y no había un criterio fijado de antemano:
el dato es descriptivo.

**Qué muestra la lectura.**
- **Dónde falla el destino.** Cuando está mal, apunta a algo vecino del objeto acotado:
  - la base de la proporción (fila 13);
  - la finalidad del tope (9);
  - la consecuencia (20 y 25);
  - el supuesto que lo habilita (14);
  - otra modalidad de la operación (17);
  - otro objeto (7).

  Las 2 «no decidible» son una lista de códigos linealizada (`ric::5.2.5`, filas 27 y 30).
- **Ponderadores.** 10 de las 30 aristas son ponderadores de riesgo (filas 1, 3, 6, 7, 10, 11, 12, 18, 22 y
  29), modelados como Restriccion «limite_cuantitativo» con `limita`. Un ponderador no acota: el valor
  multiplica la exposición.
- **Fila 21 (observación de la autora).** El 30 % es una condición del ponderador 0 más que un tope. Con
  `condicion_de` → Operacion se representaría como Condicion. Va con el hallazgo de los ponderadores.
- **Fila 26.** La descripción de la Restriccion invierte el sentido del texto: el texto exceptúa el 20 % de la
  obligación de ingreso, y la descripción dice que el 20 % es la obligación. El destino es correcto, así que la
  fila cuenta «sí».

Un dato de contexto de U1: en desarrollo, las 284 `limita` salen de Restricciones «limite_cuantitativo» 201,
«limite_cualitativo» 76, «limite_temporal» 3 y «prohibicion» 4 (`u1_mediciones.json`,
`limita.desarrollo.limita_por_Restriccion_tipo`).

**Nota: 4 `limita` desde Restricciones «prohibicion».** Contradicen la tabla de predicados del prefijo, que manda
`prohibe` desde una prohibición (`PREFIJO_SISTEMA_V3`, líneas 59-60 y 288-290 del texto).
- Recómputo de la mesa: son las mismas 4 en KG-Tanda0-Diez-r1. En KG-Reextraído-r1 hay 3 del mismo patrón, en
  otros nodos.
- El validador de E1 controla la firma dominio → rango, pero no la coherencia entre Restriccion.tipo y el
  predicado. Cuál de los dos está mal en cada caso no está adjudicado.
- Registradas como candidato de backlog: `BKL-0038` (`data/backlog/backlog.jsonl:89`), con release candidata r2.
- **Decisión de la autora (30/09):** U-PYD suma un control en código de la coherencia entre el tipo de la
  Restricción y su predicado (prohibicion → `prohibe`; limite_* → `limita`), como marca (plan, B2.11, unidad
  7).

### 1.2 Opciones

U-UMBRAL separó dos ejes (`reporte_u_umbral.md` §1-§2):
- **Dónde vive el umbral:** propiedad del nodo o atributo de la relación.
- **Cómo se llena:** lo emite E1, lo calcula un paso posterior en código o lo llena un modelo.

Propuesta y alternativa (§4 del reporte):
- **Par A:** propiedad del nodo, con el tramo literal emitido por E1 y normalizado y verificado en código.
- **Par B:** la misma propiedad, llenada en código sobre la descripción guardada, sin re-extraer.
- **No propuestos:** el atributo de la relación, por cobertura, porque es invisible para el agente y porque
  reabre ESQ-RI-3 / C1.7; y el llenado por un modelo, estimado en USD 0,25 a 0,51 (ESTIMACIÓN NO VERIFICADA),
  que no agrega verificación.

### 1.3 Orientación de la autora (plan, B2.11, unidad 5)

- **(a) Representación.** La propiedad de umbral es una lista, en Restriccion, Obligacion, Condicion y
  Excepcion. Cada elemento lleva:
  - el tramo literal;
  - el valor;
  - la unidad;
  - la comparación, explícita para que el agente no tenga que interpretarla;
  - la base.
- **(b) Llenado.** Par B en r2a y par A en r2b.
  - E1 copia el tramo literal.
  - La normalización y la verificación contra E0 y `e0_tablas` son código, construido una sola vez en
    U-R2-CODIGO y re-aplicable sin re-extraer.
  - Lo que no verifica se marca, sin corregirlo.
- **(c) Umbrales relacionales.** La base se guarda como texto literal y se resuelve a su punto o definición por
  el mecanismo de remisiones. Si no resuelve, se marca, igual que un sujeto no mapeable.
- **(d) Plazos de relleno.** El campo queda vacío y la verificación lo marca. Con el par A, un valor sin tramo
  literal no pasa.
- **(e)** La muestra de `limita` se lee antes de este laudo (unidad 4b, cerrada; resultado en §1.1).
- **(f)** Vincular cada valor de un nodo con varios umbrales a su sujeto u operación queda como trabajo futuro
  (C1.7). Es la limitación de hechos con valor n-arios que el laudo ya difirió a ESQ-RI-3 / C1.7 (§2).

**Decisión de la autora (30/09)**, dentro de la orientación:
1. **Obligacion.plazo.** El plazo pasa a la lista como un elemento con unidad temporal. La frecuencia va a un
   campo propio, con lista cerrada (diaria, semanal, mensual, trimestral, semestral y anual) y marca de fuera de
   lista. Así se resuelve la clave `plazo_o_frecuencia`, que no es unívoca (U-LISTAS-NOMAP, P-a8).
2. **Valores cerrados de `comparacion`:** máximo inclusivo, máximo estricto, mínimo inclusivo, mínimo estricto,
   igual, coeficiente y `no_determinada`. La distinción entre «superior a» e «igual o superior a» cambia la
   respuesta correcta.
   - «Coeficiente» es para los ponderadores de riesgo: el valor multiplica, no acota (§1.1).
3. **Cómo se fija `comparacion`.** La comparación sale del tramo por reglas en código, definidas por su sentido.
   Valen para todos los elementos de la lista.
   - **Coeficiente:** cuando aparece «pondera», «ponderador», «ponderación», «coeficiente» o «factor».
   - **Raíces (formas simples).**
     - Mínimo estricto: las formas de raíz «super-» y «exced-» (supere, superen, superar, superior, exceda,
       excedan, exceder), más «más de» y «mayor» o «mayores a».
     - Máximo estricto: «inferior» o «inferiores a», «menos de», «menor» o «menores a».
   - **Negación general.** «No» o «sin» delante del verbo o del comparativo, con hasta tres palabras en el
     medio, invierte el sentido. Ejemplos: «no podrá superar», «no deberá superar», «no podrán ser superiores
     a», «sin exceder», «no excedan, al momento de los acuerdos, del».
     - La negación de un mínimo estricto es máximo inclusivo.
     - La negación de un máximo estricto («no inferior a», «no menos de») es mínimo inclusivo.
   - **Compuestas.**
     - «igual o superior» o «igual o mayor» → mínimo inclusivo;
     - «igual o inferior», «igual o menor», «como máximo», «hasta» y «dentro de» → máximo inclusivo;
     - «al menos», «como mínimo» y «un mínimo de» → mínimo inclusivo.
   - **Adyacencia.** Los marcadores de comparación se buscan en el tramo, junto a la cuantía, no en cualquier
     parte de la descripción. El marcador de coeficiente es la excepción: puede venir de la descripción o del
     título del punto.
     - «Mínimo» o «máximo», en cualquier género y número (mínima, mínimos, máximas…), cuentan como marcador
       cuando van seguidos inmediatamente de la cuantía, con o sin «de» en el medio: mínimo inclusivo o máximo
       inclusivo. Ejemplos: «plazo mínimo de 10 días hábiles», «vida promedio mínima 2 años», «un mínimo de».
       Tienen el nivel de precedencia de las compuestas.
     - Como adjetivo de un sustantivo sin la cuantía a continuación («capital mínimo»), no cuentan.
   - **Precedencia:** primero coeficiente, después la negación, después las compuestas y por último las
     simples.
   - **Sin marcador:** en un plazo, máximo inclusivo con la marca `comparacion_asumida`; en cualquier otra
     cuantía, `no_determinada`.

   El laudo fija el sentido de cada forma. La implementación exacta y su calibración son de U-PYD: frecuencia de
   cada forma en los tramos de r2a, falsos positivos de «factor» y regla de «igual», que no tiene regla
   inicial. Los casos de control son prueba obligatoria.

   Casos de control (§1.5):
   - **Ejemplo del préstamo** (`cla::5.1.1.1`, texto de E0): «superen el equivalente a dos veces el importe de
     referencia establecido en el punto 3.7.» → mínimo estricto, valor 2, unidad «veces», base «importe de
     referencia establecido en el punto 3.7».
   - **Fila 9 de la lectura de `limita`** (`cap::2.8.3.2`): «no deberá superar el 0,2%» → máximo inclusivo.
   - **Fila 21** (`cap::2.12.2.3`): «no excedan, al momento de los acuerdos, del 30%» → máximo inclusivo, sin
     disparar coeficiente.
   - **Fila 15** (`cap::4.3.3.1`): «con un plazo mínimo de 10 días hábiles» → mínimo inclusivo.

   Historia de la regla, con cinco correcciones de la autora (30/09 y 01/10):
   - **Primera versión:** «comparación máximo» para el plazo. Se corrigió porque en desarrollo hay plazos de
     Obligacion enunciados como mínimos: una regex de la mesa encontró al menos 3, por ejemplo «mínimo 180 días»
     y «al menos un año».
   - **Segunda versión** (commiteada en `697bdf6`): sin marcador, máximo inclusivo con `comparacion_asumida` para
     toda cuantía, y ninguna regla para «coeficiente». Se corrigió porque un ponderador sin marcador recibía un
     máximo asumido, que es falso.
   - **Tercera versión** (30/09, no commiteada): «coeficiente» por marcadores; «dentro de» o «hasta» → máximo
     inclusivo; «mínimo», «al menos» o «no menos de» → mínimo inclusivo; sin marcador, el plazo con
     `comparacion_asumida` y el resto `no_determinada`. Se corrigió el 01/10 porque no cubría las formas
     habituales de los topes ni la negación, y el ejemplo del préstamo («superen el equivalente a dos veces…»)
     quedaba `no_determinada`.
   - **Cuarta versión** (01/10, no commiteada): listas de frases exactas por grupo (por ejemplo, «no supere», «no
     podrá superar», «no deberá exceder» y «no excedan» para máximo inclusivo, y «supere», «superen» y «exceda»
     para mínimo estricto), con la misma precedencia. Se corrigió el 01/10 porque la lista de frases exactas no
     reconocía variantes: aplicada literalmente, falló la fila 9 («no deberá superar» no estaba en la lista y
     «superar» no coincide con «supere»).
   - **Quinta versión** (01/10, no commiteada): las reglas por sentido, con la adyacencia, pero «mínimo» o «máximo»
     como adjetivo de un sustantivo nunca contaba. Se corrigió el 01/10 porque la fila 15 («con un plazo mínimo de
     10 días hábiles») quedaba sin marcador y, por ser un plazo, con máximo asumido, que es falso.
4. **Valores cerrados de `unidad`:** porcentaje, moneda con su código, días (corridos o hábiles), meses, años y
   «veces», más UVA, con marca de fuera de lista.
5. **Potestad.** Queda fuera de la lista según (a). Su clave `umbral`, emitida alguna vez (U-LISTAS-NOMAP,
   tabla a.2), va a `properties_no_definidas` (§2).
6. **Ponderadores: límite declarado del esquema.** Siguen como Restriccion con `limita`, y su valor lleva la
   comparación «coeficiente». Quedan como límite declarado del esquema (lectura A del §0.4) dos cosas:
   - si los ponderadores deben ser otro tipo de nodo;
   - si sus condiciones de elegibilidad deben ser una Condicion (fila 21 de la lectura de §1.1).

### 1.4 r2a y r2b

- **r2a (código, USD 0).**
  - Un paso nuevo lee la descripción guardada (y el campo actual donde existe) y arma la lista.
  - Verifica cada tramo como subcadena del texto de E0 y, en los chunks con tabla, contra `e0_tablas`.
  - Marca lo que no verifica; los campos de relleno quedan vacíos y marcados.
  - Fija `comparacion` por las reglas del punto 3 de §1.3, en su orden de precedencia. Busca los marcadores en
    el tramo, junto a la cuantía; el de coeficiente, también en la descripción y en el título del punto.
    «Mínimo» o «máximo», en cualquier género y número, seguidos inmediatamente de la cuantía (con o sin «de»),
    cuentan como mínimo o máximo inclusivo. Sin marcador, un plazo recibe máximo inclusivo con la marca `comparacion_asumida`, y cualquier otra cuantía
    `no_determinada`.
  - Lleva al campo de frecuencia lo que hoy está en la clave de plazo o frecuencia y no es un plazo, con marca
    de fuera de lista si no está en la lista cerrada.
  - Depende de la detección de tablas de U-R2-CODIGO: los 4 chunks de ponderadores de `cap` que nadie detecta,
    y los 12 en que `e0_tablas` detecta tabla sin marca de E0 (plan, B2.11, unidad 8).
  - Formato: el grafo guarda la lista como valor de propiedad del nodo, no de la salida de E1, así que no
    consume la ventana (§0.3). La carga en Neo4j conserva un valor que no es string ni lista de strings solo en
    `props_json` (`data/experiment/neo4j/cargar_kg.py:105-115`). Cómo lo muestra `ver_nodo` es NO VERIFICADO;
    lo verifica U-R2-CODIGO.
- **r2b (prompt nuevo).**
  - E1 emite, por entidad de los cuatro tipos, la lista de tramos literales, y en Obligacion el tramo de la
    frecuencia.
  - Como el tool schema solo admite valores string en `properties`, hace falta un campo nuevo en el ítem de
    entidad o un valor de tipo lista: es cambio de tool schema, con la forma a fijar en U-PYD y U-PROMPT-R2.
  - La regla contra copiar celdas de tabla se extiende a los chunks que detecte el parser (RX-10).
  - **Instrucción nueva para U-PROMPT-R2** (decisión de la autora del 30/09, ajustada el 01/10 para los
    ponderadores): «el destino de `limita` es el acto o la magnitud que el tope acota o, si es un ponderador, la
    exposición que pondera; no su base, su finalidad, su consecuencia ni el supuesto que lo habilita». Responde a
    los errores de destino que encontró la lectura de §1.1. La versión del 30/09 no nombraba los ponderadores,
    que son 10 de las 30 aristas de la muestra.
  - El código de r2a se re-aplica sin cambios sobre los tramos de E1.
- **Límite declarado de la verificación (fila 26 de §1.1).** La verificación por tramo literal comprueba que el
  valor esté en el texto de E0, no que la descripción conserve su sentido. En la fila 26 el «20 %» está en el
  texto, pero la descripción invierte lo que el texto dice de él (exceptuado frente a obligado), y la
  verificación no lo detecta. Una inversión de sentido con el valor literal queda fuera de lo que verifica el
  código.

### 1.5 Suite y shapes

- **Suite:** los matchers de `BKL-0006` y `BKL-0023` leen `umbral` como string
  (`scripts/regression_kg.py:572`, `:615`); pasan a leer el valor normalizado de la lista. Test nuevo: toda
  lista cumple la forma de (a), todo elemento tiene el tramo verificado o una marca, y `comparacion`, `unidad`
  y la frecuencia están en su lista cerrada o llevan la marca de fuera de lista.
- **Selftests de las reglas de `comparacion`:**
  - cada sentido del punto 3 de §1.3: raíces de mínimo y máximo estricto, negación general (con cero a tres
    palabras en el medio), compuestas y coeficiente;
  - la adyacencia: un marcador fuera del tramo no cuenta; «mínimo» o «máximo» seguidos de la cuantía, con o sin
    «de» y en cualquier género y número, cuentan; «capital mínimo», sin cuantía a continuación, no cuenta;
  - la precedencia: una forma con negación que contiene una simple, como «no inferior a» frente a «inferior a»;
  - los dos casos sin marcador: un plazo, con `comparacion_asumida`, y otra cuantía, con `no_determinada`;
  - los cuatro casos de control, como prueba obligatoria:
    - el ejemplo del préstamo → mínimo estricto, con su base;
    - la fila 9 de la lectura de `limita` → máximo inclusivo;
    - la fila 21 → máximo inclusivo, sin disparar coeficiente;
    - la fila 15 («con un plazo mínimo de 10 días hábiles») → mínimo inclusivo.

  Los elementos con `comparacion_asumida` y con `no_determinada` se cuentan aparte.
- **Shapes:** S18 está reservada con un enunciado que no se implementó: «si una Restricción tiene `limita`,
  tiene `umbral`» (`scripts/shapes_validator.py:160-163`). Así enunciada, marcaría por construcción toda
  Restricción «limite_cualitativo», que usa `limita` sin monto según la tabla de predicados del prefijo. Se
  reescribe en el perfil nuevo como «Restricción limite_cuantitativo ⇒ lista no vacía o marca».
  Shape informativa nueva: «cuantía en la descripción ⇒ elemento en la lista» (`reporte_u_umbral.md` §2).

---

## 2. Listas cerradas y política por campo

### 2.1 Qué dicen los documentos y qué midió el pipeline

Fuentes: U-LISTAS-NOMAP, N1 (`9c5331c`, `reports/u_listas_nomap/n1_inventario.json`) y N2 (`acc310e`,
`reports/u_listas_nomap/diseno_listas_nomap.md`).

- **Hoy** (`validador_e1.py`):
  - el validador rechaza por tipo, predicado, `sujeto_id` y firma;
  - normaliza Obligacion.tipo a «otra» (`:212-215`) y deja el original solo en el texto de una advertencia;
  - convierte las `properties` a string sin controlar claves ni valores (`:202-206`): Restriccion.tipo,
    Comunicacion.tipo y las claves no tienen control;
  - descarta sin registro las omisiones que llegan como string (`:154-156`);
  - anula sin registro un padre sugerido fuera del catálogo (`:313`).
- **Fuera de lista, en el crudo** (diseño, tabla a.2):
  - tipos de entidad: 4 en diez;
  - predicados: 2 en diez;
  - `sujeto_id`: 0 en todos los grupos;
  - Obligacion.tipo: 3 en cinco;
  - Restriccion.tipo: 4 en desarrollo («limite_temporal» 3, «obligacion_cualitativa» 1);
  - Comunicacion.tipo: 5 en diez y 14 en r1;
  - claves fuera de la definición: 10 en diez, entre ellas `plazo_o_frecuencia`, `umbral` en Obligacion y
    Potestad y `Operacion.etapa`.
- **Lo que dicen los documentos** (principio 11):
  - **Obligacion.tipo:** «otra» es 1.398 de 2.365 valores en el crudo de diez, y 1.411 de 2.367 en el grafo.
    El laudo ya registró que la cola larga del subtipado queda bajo el corte en 233 de 236 grupos
    (U-R9-FREQ, §3: «las obligaciones resisten lista cerrada»). `requisito_de_estructura` salió por falsedad
    en campo estructurado, con un caso de promoción armado para r2: 22 unidades del grupo `cont`, 5 emisiones
    avaladas y 2 reversiones (§2). Qué contienen las Obligaciones marcadas «otra» es NO MEDIDO: N1 midió
    valores fuera de lista, no el contenido del residuo.
  - **Comunicacion.tipo:** de los 14 valores fuera de lista del crudo de r1, 5 nombran otra clase de norma
    (`Decreto`, `decreto`, `LEY`, `MINISTERIAL`, `Resolución`), 7 son referencias genéricas y 2 están vacíos. La
    clasificación es de la instancia que escribió N2. El esquema no tiene tipo para una norma externa.
  - **Restriccion.tipo:** «limite_temporal» aparece 3 veces y el enum no tiene residuo. Si es una categoría
    real del corpus es NO MEDIDO.

### 2.2 Opciones

Por campo, tres modos: rechazar, normalizar con contador o registrar sin cambiar. Las consecuencias de cada
uno están en la tabla a.1 del diseño. Propuestas del diseño (P-a0 a P-a10):

| campo | modo propuesto |
|---|---|
| política (P-a0) | tabla de configuración versionada, campo → modo, con sha256 registrado por corrida |
| tipo de entidad (P-a1) | normaliza solo alias de forma («Restriction»); el resto se rechaza con registro y pasa a omisión `fuera_de_tipos` |
| predicado (P-a2) | normaliza por forma (espacios, camelCase); sin distancia de edición; un alias semántico solo por tabla laudada |
| `sujeto_id` (P-a3) | fuera de catálogo va al registro de no mapeados, sin rechazar la relación |
| padre sugerido (P-a4) | normaliza conservando el original; un solo catálogo |
| Obligacion.tipo (P-a5) | sigue normalizando a «otra» y guarda `tipo_original` |
| Restriccion.tipo (P-a6) | registra con marca `fuera_de_lista`; no se normaliza ni se rechaza |
| Comunicacion.tipo (P-a7) | deriva el tipo del `codigo` si tiene forma de Comunicación; si no, registra con marca |
| claves (P-a8) | fuera de la definición pasan a `properties_no_definidas`; nunca se rechaza por una clave |
| valores (P-a9) | tipados por clave; vacío equivale a ausente |
| omisiones como string (P-a10) | un string no vacío pasa a lista de un elemento |

Sobre los valores de las listas:
- **Obligacion.tipo:**
  - (i) seis valores más el original guardado;
  - (ii) valores nuevos, lo que exige antes medir el contenido del residuo «otra»;
  - (iii) re-proponer `requisito_de_estructura` con su caso de promoción.
- **Restriccion.tipo:**
  - (i) sin cambio, con marca;
  - (ii) «limite_temporal» como cuarto valor;
  - (iii) sin valor nuevo, derivado en código como «limite_cuantitativo» cuya lista de umbrales tiene unidad
    temporal (§1).
- **Comunicacion.tipo:**
  - (i) «A», «B» o «C», con la marca;
  - (ii) un valor para norma externa;
  - (iii) un tipo de entidad nuevo para normas externas (leyes, decretos, resoluciones).

### 2.3 Orientación de la autora (plan, B2.11, unidad 5)

- **(1)** La tabla de modos por campo propuesta, conservando siempre el valor original.
- **(2)** Revisar en este laudo las listas de Restriccion.tipo, Comunicacion.tipo y Obligacion.tipo con los
  valores observados, por el principio 11. Ver en el corpus si «limite_temporal» es una categoría real.

**Decisión de la autora (30/09):**
- **Obligacion.tipo:** opción (i), los seis valores, con el original guardado. `requisito_de_estructura` queda
  en el diseño como límite declarado del pipeline, sin emitirse (lectura A del §0.4). La reclasificación desde
  la descripción queda posible en código.
- **Restriccion.tipo:** opción (iii), sin valor nuevo. Lo temporal se deriva en código de la unidad del umbral
  (§1). Los valores fuera de lista siguen el modo de P-a6.
- **Comunicacion.tipo:**
  - se deriva en código del `codigo` cuando tiene forma de Comunicación;
  - se agrega el valor «externa» para leyes, decretos y resoluciones, con el nombre original guardado;
  - el tipo de entidad para normas externas queda como trabajo futuro.
- **Alias:**
  - se aceptan los de forma para tipos y predicados;
  - se acepta el alias semántico `exceptua_restriccion` → `exceptua`, el único observado, en el crudo de r1;
  - no hay renombres de claves.
- Con estas decisiones, la medición previa del residuo «otra» y de los umbrales temporales deja de ser
  condición para fijar los valores.

### 2.4 r2a y r2b

- **r2a:** toda la política por campo es código (U-PYD, módulo Pydantic único) y se re-aplica sobre el crudo
  guardado. El grafo de la tanda 0 no cambia de valores: 0 fuera de lista en el grafo en Obligacion.tipo. Sí
  cambia la visibilidad: marcas, contadores, originales y `properties_no_definidas`. Prerrequisito: el crudo
  del reintento de E3 persistido (U-R2-CODIGO). En la tanda 0 se lee de `e1_reintentos.db`.
  - Comunicacion.tipo se deriva del `codigo`, y los valores que nombran una ley, un decreto o una resolución
    pasan a «externa», con el original guardado.
  - Los valores «limite_temporal» quedan con su marca, y lo temporal se lee de la unidad del umbral.
- **r2b:** solo un valor nuevo de enum exige prompt nuevo (diseño, tabla f). El único valor nuevo es «externa»
  en Comunicacion.tipo; entra al prompt y al tool schema de U-PROMPT-R2.

### 2.5 Suite y shapes

- **Suite** (diseño, g):
  - LN-1: ningún valor fuera de lista sin tratar;
  - LN-2: `properties` dentro de la definición del tipo;
  - selftests de U-PYD con los valores reales de N1.
- **Shapes** (perfil nuevo; `shapes_validator` sigue solo con stdlib, como control independiente de
  Pydantic):
  - S24: enum de Restriccion.tipo, sin valores nuevos;
  - S25: enum de Comunicacion.tipo, con «externa»;
  - S26: claves cerradas por tipo;
  - S20, el enum de Obligacion.tipo, ya existe.

  S24 y S25 son bloqueantes salvo la marca `fuera_de_lista`.
- **Suite, además:** los alias aceptados (de forma y `exceptua_restriccion` → `exceptua`) entran a los selftests
  de U-PYD con los valores reales de N1.

---

## 3. Mención y resolución de sujetos

### 3.1 Qué dicen los documentos y qué midió el pipeline

Fuentes: N1 y N2 de U-LISTAS-NOMAP. Cifras del crudo de diez salvo aviso.

- **Los documentos nombran al sujeto de maneras que el catálogo no copia.**
  - Hay 1.737 pares con el sujeto por defecto del TO; en 1.470 su label no está en el texto
    (`sujetos_forzados.diez.defecto_del_to`). Es el caso de las expresiones colectivas, como «las entidades»
    (diseño, P-c1).
  - En 61 de 398 pares de otras clases o instancias, ni el label ni un alias están en el texto (posibles
    forzados, `sujetos_forzados.diez.otra_clase_o_instancia`).
- **Hoy no se guarda la mención.** El único antecedente es `sujeto_propuesto`, «nombre del sujeto tal como
  aparece en el texto» (`prompt_e1.py:314`). De 63 propuestos, 18 no son subcadena exacta del chunk y 10
  fallan también por tokens (`sujeto_propuesto_literal.por_grupo`).
- **Proyección, no medición.** Con la mención en las 4.099 relaciones `aplica_a` y `ejecuta`, fallarían la
  subcadena del orden de 1.171 y los tokens del orden de 651. La población de propuestos no representa las
  menciones del catálogo; la tasa real la mide U-PROMPT-R2 o U-REEXT-T0.
- **E4 resuelve hoy por nodo y después de la fusión** (`r1_e4.py:121-175`).
- Completar el catálogo JSON con los seis ids que le faltan no resuelve ningún propuesto más: 3/1/4 antes y
  después (`reresolucion_contrafactica`).

### 3.2 Opciones (diseño, secciones b y c)

- **Campo.** `sujeto_mencion` (P-b1): el tramo que nombra al sujeto, copiado tal cual, obligatorio en `aplica_a`
  y `ejecuta`. El tool schema no expresa obligatoriedad condicional: lo exige el validador.
- **Rol de `sujeto_id`.**
  - P-b2: pasa a ser sugerencia del modelo (`sujeto_id_modelo`), y `sujeto_propuesto` deja de ser campo del
    modelo, porque se deriva de la mención.
  - P-b2': todo como hoy, más la mención.
- **Verificación.**
  - Nivel 1 (P-b3): subcadena normalizada en el texto propio o heredado.
  - Nivel 2 (P-b4): tokens dentro de una ventana; el código guarda el tramo literal mínimo.
  - Nunca se rechaza la relación por la mención. Marca `mencion_verificada` ∈ {`exacta`, `tokens`, `no`,
    `ausente`}.
- **Resolución por relación, entre E3 y E2** (P-c1):
  - R1: label o alias exacto;
  - R2: slug, singular y alias entre paréntesis;
  - R3: expresión colectiva → sujeto por defecto del TO;
  - R4: sugerencia del modelo;
  - ambigüedad o sin resolver → registro (§4).
- **Desacuerdos entre regla y modelo.**
  - P-c2: gana la regla con R1 o R2, y el modelo con R3.
  - P-c2': gana siempre el modelo.
- **Registro del método** (P-c3): `metodo_resolucion` en la arista y el detalle en `resolucion_sujetos.jsonl`.

### 3.3 Orientación de la autora (plan, B2.11, unidad 5)

- **(3)** `sujeto_mencion` obligatoria por validador y `sujeto_id` como sugerencia (P-b2, no P-b2').
- **(4)** La verificación por tokens como nivel 2, con la ventana medida en U-PYD.
- **(5)** En un desacuerdo, la regla textual gana solo con coincidencia exacta de label o alias (R1). Con las
  reglas aproximadas (R2 y R3) gana la sugerencia del modelo. Siempre se registran los dos ids. Es una
  combinación de P-c2 y P-c2': R2 pasa del lado del modelo.

**Consecuencia ya escrita en una enmienda firmada.** La enmienda de uso de la ventana (§3.4) re-expresa el
remedio de la vigilancia (9) de B5.4 en dos ramas. Con (3) y (5) rige la primera:
- el retiro de un id que pida la tanda 1 se hace en la resolución en código;
- no cambia el prefijo;
- sigue el ciclo de releases del pipeline antes de sellar el pre-registro de B6.3.

Se confirma con la firma.

**Decisión de la autora (30/09):**
- **Lista de expresiones colectivas de R3:** una lista inicial cerrada, tomada de la redacción del propio prompt
  (`prompt_e1.py:110`), que se amplía en código con las menciones de r2b.
- **Menciones que califican una clase existente** («Entidades del Grupo A»): se resuelven a la clase y se guarda
  el calificador. Los calificadores frecuentes quedan en el registro de no mapeados (§4) como candidatos a id.
- **Lecturas** (checklist P15 y Q12): lectura asistida con revisión de la autora, declarada, sobre datos de
  r2b. La muestra sellada de 30 posibles forzados (`muestra_forzados_30.csv`) se puede leer, opcionalmente,
  como línea de base.

### 3.4 r2a y r2b

- **r2a:**
  - la resolución por relación con R1, R2 y R4 sobre `sujeto_propuesto` y `sujeto_id` guardados, con la
    resolución a la clase y el calificador guardado donde el propuesto califica una clase existente;
  - la verificación en dos niveles sobre las 63 relaciones con propuesto de diez;
  - R3 y los desacuerdos necesitan la mención.
- **r2b:**
  - el campo `sujeto_mencion` y la salida de `sujeto_propuesto` del tool schema;
  - instrucciones nuevas: copiar la mención tal cual, con artículos y en el orden del texto; una mención por
    sujeto en una enumeración, lo que extiende la regla 7; copiarla del contexto heredado si el sujeto está ahí.

### 3.5 Suite y shapes

- **Suite:**
  - LN-3: toda arista de sujeto que no es de esqueleto lleva mención y `mencion_verificada`; hoy son 0 de
    3.019 en desarrollo;
  - LN-4: `metodo_resolucion` en toda arista de sujeto, con los desacuerdos contados.
- **Shapes:** S27, arista de sujeto con mención y método: informativa en r2a, bloqueante desde r2b.

---

## 4. Registro de no mapeados

### 4.1 Qué dicen los documentos y qué midió el pipeline

- Hoy E2 crea los nodos `Sujeto_propuesto` desde `sujeto_propuesto` (`e2_lib.py:382-407`), y la cuarentena no
  deja un registro con la mención y el motivo.
- En diez hay 34 propuestos, 30 en cuarentena (N1, `propuestos_e4`).
- Cuántos de los 30 son un sujeto ausente del catálogo, una calificación de una clase existente, una
  enumeración sin partir o un error de extracción es NO MEDIDO: requiere lectura.
- Los ids de chunk repetidos en 4 TOs de la partición (`BKL-0037`) obligan a identificar cada fila por el
  sha256 del texto de E0, además del id.

### 4.2 Opciones (diseño, sección d)

- **P-d1:** un archivo `no_mapeados_sujetos.jsonl` por TO y uno por ensamblado. Lo escribe el paso de
  resolución en forma determinística, y E2 crea los nodos en cuarentena desde el registro: registro y grafo
  coinciden por construcción.
- **P-d2:** una fila por relación sin resolver, con:
  - clave: TO, chunk, sha256 de E0, índice y punto;
  - mención y verificación;
  - sugerencias del modelo;
  - motivo: `sin_match`, `ambiguo`, `mencion_no_verificada` o `id_fuera_de_catalogo`;
  - candidatos;
  - `categoria_no_mapeo`, que se llena por lectura;
  - versiones de catálogo y de política;
  - estado.
- **P-d3:** re-resolución por programa cuando cambia el sha256 del catálogo, y re-ensamblado de E2 a E5 a USD 0.
- **P-d4:** métricas:
  - no mapeados por cada 1.000 relaciones con sujeto;
  - distribución por motivo y categoría;
  - resueltos por versión del catálogo;
  - ranking de menciones para el crecimiento del catálogo.

### 4.3 Orientación de la autora (plan, B2.11, unidad 5)

- **(7)** Sin meta de resueltos hasta medir después de U-REEXT-T0.
- El diseño del registro (P-d1 a P-d4) no está entre las siete decisiones abiertas del diseño; su adopción
  formal es la firma de este laudo.

**Decisión de la autora (30/09):** `categoria_no_mapeo` se llena por lectura asistida con revisión de la
autora, declarada, sobre datos de r2b (la misma regla de lecturas de §3.3).

### 4.4 r2a y r2b

- **r2a:** se construye ya desde `sujeto_propuesto`. En diez: 63 relaciones en el crudo y 61 en la entrada de
  E2 (N1, `forma_sujeto`, `sujeto_propuesto_literal`).
- **r2b:** la mención completa en toda relación de sujeto.

### 4.5 Suite y shapes

- **Suite:**
  - LN-5: registro y grafo coinciden;
  - LN-6: la re-resolución es idempotente y, con el catálogo ampliado, reproduce el contrafáctico de N1 (3/1/4).
- **Shapes:** S28, todo `Sujeto_propuesto` con fila en el registro, bloqueante.

---

## 5. Omisiones

### 5.1 Qué dicen los documentos y qué midió el pipeline

- **Los documentos tienen tres clases de contenido que el esquema no extrae como prosa:**
  - tablas;
  - fórmulas;
  - contenido meta-normativo: finalidad, vigencia, interpretación y alcance de una norma (regla 9; R4 del
    laudo).

  Tienen además contenido que no encaja en ningún tipo; la regla 4 del prefijo prefiere no extraer a forzar.
- **Hoy:**
  - `omisiones_no_prosa` es una lista de strings libres, pedida solo en chunks marcados por E0
    (`prompt_e1.py:158-165`);
  - la regla 9 omite sin dejar registro.
- **Unidades con omisión** (N1, `omisiones`, sobre `salida_dirigida/`): 81 de 1.763 en r1, 78 de 1.763 en
  desarrollo, 7 de 671 en cinco y 85 de 2.434 en diez. De esas, están en chunks sin marca de E0: 20, 21, 2 y
  23.
- Las omisiones de la regla 9 son NO MEDIBLES hoy.
- D2 de U-PRE-R2-DIAG atribuye a tablas las 8 pérdidas reales de contenido de las celdas de EV2
  (`reports/u_pre_r2/d2_ausencias.md`, `159c1e2`).

### 5.2 Opciones (diseño, sección e)

- **P-e1:** campo `omisiones`, una lista de objetos {categoría, tramo, nota}, obligatoria en todo chunk.
  Categorías: `meta_normativo`, `tabla`, `formula` y `fuera_de_tipos`. La regla 9 pasa de «no se extrae» a
  «no se extrae y se registra con su tramo»; la regla 4 registra lo no extraído.
- **P-e2:** validación del tramo:
  - subcadena del texto propio;
  - nivel por tokens;
  - longitud mínima;
  - una omisión `tabla` en un chunk sin marca cuenta como señal de tabla no detectada.
- **P-e3:** una entidad rechazada por tipo se registra como `fuera_de_tipos`.
- **P-e4:** reproceso dirigido por categoría, con costo proporcional a las unidades con esa categoría.

### 5.3 Orientación de la autora (plan, B2.11, unidad 5)

- **(6)** Las cuatro categorías de omisión, con el largo mínimo del tramo fijado con datos en U-PYD.
- Efecto sobre el laudo: el residuo que la regla 9 declaró (R4) se vuelve medible por TO. Su línea de base
  empieza en r2b.

**Decisión de la autora (30/09):**
- **Quinta categoría.** Por la decisión del §8 se agrega `relacion_sin_predicado`, para toda relación que el
  texto expresa y el esquema no puede representar. La orientación (6) pasa a cinco categorías: `meta_normativo`,
  `tabla`, `formula`, `fuera_de_tipos` y `relacion_sin_predicado`.
- **Muestra de control de `meta_normativo`** (P-e4.3), para vigilar el contenido habilitante que la regla 9 no
  debe excluir: lectura asistida con revisión de la autora, declarada, sobre datos de r2b (checklist P15 y Q12).

### 5.4 r2a y r2b

- **r2a:** cada string de `omisiones_no_prosa` se lee como omisión sin categoría y sin tramo, y P-e3 se aplica
  sobre el crudo.
- **r2b:** el campo `omisiones` con las cinco categorías, y las instrucciones de las reglas 4 y 9, de la
  sección de contenido no-prosa y de las relaciones sin predicado.

### 5.5 Suite y shapes

- **Suite:** LN-7, toda omisión con categoría del enum de cinco valores y tramo verificado o marcado; 0 chunks
  marcados con extracción y sin omisión.
- **Shapes:** el diseño no propone ninguna.

---

## 6. Matriz de firmas (checklist X1 y X11)

### 6.1 Qué dicen los documentos y qué midió el pipeline

- **Los documentos.** Una Condicion es el antecedente de otra norma. La matriz congelada solo la deja
  condicionar una Excepcion, una Obligacion o una Restriccion (`condicion_de`). En el texto, las condiciones
  condicionan también operaciones: en la lectura asistida de abajo, en 27 de 29 casos decididos la Condicion
  es, según el chunk, el antecedente de la Operacion de destino.
- **Qué rechaza la matriz.** E1 emitió 982 relaciones que el validador rechazó por firma inválida en los diez
  TOs. De ellas, 834 caen en 11 pares candidatos (`reports/u_estudio_matriz/uestmat_reporte_U-ESTUDIO-MATRIZ.md`,
  `7e72051`).
- **Efecto de ampliar la matriz** sobre KG-Tanda0-Desarrollo-r1, con la población final (misma fuente):
  - `condicion_de` → Operacion: +388 aristas;
  - `condicion_de` → Potestad: +239 aristas;
  - las dos juntas: +627.

  Es una cota superior: supone que lo que pasa a válido entra sin re-verificar en E3.
- **Protocolo.** El criterio se fijó el 28/09, antes de abrir la muestra: se amplía un par si el piso de Wilson
  al 95 % es de al menos 0,75 y los no decidibles no pasan de 6. Resultado
  (`reports/u_estudio_matriz/lectura/resultado_lectura_matriz.md`, `c671b52`; lecturas en `bb90861`):
  - → Operacion: 27 correctas de 29 decididas, piso 0,780. **Cumple.**
  - → Potestad: 27 de 30, piso 0,744. **No cumple**: le falta una correcta.
  - Los otros nueve pares, con 5 filas cada uno, no se amplían con esta evidencia. Excepcion `exceptua` →
    Operacion dio 5 de 5, y es el caso de R6a (§8).
- **Desvío declarado.** La lectura la hizo una instancia de modelo y la revisó la autora (misma fuente,
  «Desvío declarado»).
- **Causa de ausencias.** D2 de U-PRE-R2-DIAG: la matriz no es causa principal de ninguna ausencia, y es causa
  secundaria de 3. Su valor es de completitud del grafo.
- **Aristas entre nodos de igual descripción.** 5 de las 12 incorrectas unen dos nodos con la misma
  descripción. Una sexta del mismo tipo, M50, es correcta. Es candidato del §4 del laudo de r2, con el alcance
  en el grafo aceptado sin medir.

### 6.2 Opciones

- **(i)** Ampliar solo → Operacion, según el criterio fijado.
- **(ii)** Ampliar → Operacion y → Potestad, declarando el desvío del criterio.
- **(iii)** No ampliar hasta una validación adicional (X11).

Ya decidido (checklist X2, 30/09): si se amplía, cambia el prompt (U-PROMPT-R2) y la tanda 0 se re-extrae
(U-REEXT-T0).

### 6.3 Decisión de la autora (30/09)

No había orientación registrada.
- **X1: opción (ii).** Se amplían `condicion_de` → Operacion y `condicion_de` → Potestad.
  - **Desvío declarado:** → Potestad quedó a una correcta del criterio fijado antes de leer (27 de 30, piso de
    Wilson 0,744 frente a 0,75). Se amplía igual por el principio 11: los documentos expresan condiciones sobre
    potestades (27 de 30 correctas en la lectura, frente a 27 de 29 de → Operacion).
  - La diferencia entre los dos pares está dentro del error de una muestra de 30: los intervalos de Wilson
    (0,780–0,981 y 0,744–0,965) se superponen casi por completo (resultado de la lectura, tabla del criterio).
- **Confirmación.** En r2b, E3 verifica cada relación nueva. Sobre el grafo re-extraído se lee una muestra de
  los dos pares, con lectura asistida y revisión de la autora. Es un paso posterior a U-REEXT-T0 y anterior a
  la tanda 1 (plan, B2.11, unidad 11). Si → Potestad no se confirma, se retira en el validador, en código, sin
  re-extraer.
- **X11:** la lectura asistida alcanza para esta decisión, y queda declarado. La validación de dominio se
  reserva para la evaluación final.

### 6.4 r2a y r2b

- **r2a:** el perfil nuevo del validador, con la matriz ampliada, se re-aplica sobre el crudo guardado y
  recupera las relaciones rechazadas: hasta 388 en desarrollo para → Operacion y 239 para → Potestad (627
  juntas). Esas relaciones no pasaron por E3. **Decisión de la autora (30/09):** entran a r2a marcadas como no
  verificadas por E3 y se cuentan aparte en el tablero. El grafo de la release lleva solo las verificadas en
  r2b.
- **r2b:** cambian la tabla de firmas del prompt y la instrucción de Condicion, que hoy manda conectarla «a la
  Excepcion, Obligacion o Restriccion del mismo chunk» (`prompt_congelado.py`, prefijo `e69feaaa…`; resultado
  de la lectura, sección «Pendiente de la decisión»). E3 verifica lo nuevo.

### 6.5 Suite y shapes

- **Shapes:** S3 (matriz de firmas) lee en el perfil nuevo la matriz que fije este laudo
  (`scripts/shapes_validator.py:102`, `:648`).
- **Suite:**
  - una entrada que fije las dos firmas nuevas;
  - un conteo aparte de las relaciones marcadas como no verificadas por E3 (r2a), que debe ser 0 en el grafo de
    la release;
  - el control de aristas entre nodos de igual descripción entra primero como censo informativo, sin regla de
    retiro: en la muestra, esa regla habría retirado M50, que es correcta.

---

## 7. Catálogo de sujetos

### 7.1 Qué dicen los documentos y qué midió el pipeline

- **Dos fuentes.** El bloque del prompt tiene 102 ids; `data/experiment/esq_v3_miembros/esquema_v3_clases.json`,
  que usan E4, el esqueleto y S19, tiene 101. Seis están solo en el bloque y cinco solo en el JSON (plan, fila
  B6.0 fase 2a, hallazgo E1; tablero, fila «Catálogo de sujetos en dos fuentes»).
- **Verificación de la mesa (30/09, por nombre):** la diferencia coincide con los cambios del laudo firmado de
  B5.4 fase 1 (`docs/laudo_B5.4_fase1_catalogo.md`, `dea56ba`) que llegaron al bloque y no al JSON.
  - Los seis del bloque son las adiciones de F1.4 (`:46-49`): los cuatro roles del sistema de pagos
    (`entidad_girada`, `entidad_depositaria`, `entidad_receptora`, `entidad_originante_de_transferencia`),
    `banco_central_del_exterior` y `fmi`. La séptima adición, las cámaras electrónicas de compensación, está en
    los dos.
  - Los cinco del JSON son los retiros con lápida de F1.5 (`:70-75`): `acreedor_del_exterior`,
    `autoridad_nacional_de_aplicacion` y las secretarías de comercio, energía y transporte. Las lápidas están
    en `data/experiment/b54_catalogo_v3/catalogo_sujetos_v3.md:51-55`.
- **Fuente única, ya decidida** (checklist X15; plan, B2.11, unidad 6, U-CAT-UNICO): un JSON del que se
  generan el bloque, los enums del tool schema, `ROL_POR_TO`, los labels de E2, el índice de E4, el esqueleto,
  S19 y la suite. El primer selftest regenera el bloque v3 byte a byte.
- **Lo que dicen los documentos, en las entradas del backlog** (`data/backlog/backlog.jsonl`):
  - **`BKL-0028`** (`:73`). El catálogo no tiene id para la variante extranjera de tres clases:
    `Sujeto_entidad_financiera`, `Sujeto_banco` y `Sujeto_entidad_cambiaria` llevan alias «del exterior» con una
    definición doméstica. En uso, la clase es la unión. El TO distingue «del país» de «del exterior»
    (`ctacor::1.1` y `1.4`). Remedio del backlog: abrir ids para las variantes del exterior y quitar esos alias.
  - **`BKL-0029`** (`:74`). El colectivo con que convca delimita su alcance, «titulares de cuenta corriente en
    el BCRA», no tiene id. El rol se adjudicó a `Sujeto_entidad_financiera`, una aproximación: la cuenta es
    optativa para cajas de crédito y entidades cambiarias (`ccbcra::1.1`). Remedio: abrir el id y re-adjudicar
    el miembro del rol.
  - **`BKL-0034`** (`:79`; diagnóstico corregido a lectura asistida en `:84`). El catálogo no tiene sujeto de
    nivel órgano. En `lingob::2.3.2::intro` el obligado es el Directorio, y lingob separa Directorio, Alta
    Gerencia y Comité de auditoría. Remedio: abrir un id de nivel órgano para el Directorio.
- **Otros destinos «r2» del catálogo en laudos firmados de B5.4:**
  - `ministerio_de_economia` y `sociedad_de_proposito_especial` se mantuvieron con marca de revisión en r2
    (`laudo_B5.4_fase1_catalogo.md:68-69`);
  - `bis` quedó con caso de promoción documentado (`:50-53`).

  Su uso en la tanda 0 es NO MEDIDO.
- **Criterio de admisión de ids:** crecimiento aditivo bajo las mismas reglas (`docs/esquema_v2_diseño.md:348`).
- **Límite del remedio en código:** un id agregado solo al JSON se aplica en código a las menciones guardadas,
  pero el modelo solo lo sugiere cuando se regenera el bloque del prompt. E1 valida contra el bloque (diseño,
  premisa 6; `BKL-0034`, campo `propuesta`).

### 7.2 Opciones

- **Diferencia 6/5.**
  - (i) Aplicar el laudo de B5.4: el JSON incorpora los seis y registra los cinco como lápidas no vigentes.
  - (ii) Otra composición, que exigiría revisar ese laudo.
- **`BKL-0028`.**
  - (i) Tres ids del exterior, quitando los alias de las entradas domésticas.
  - (ii) Mantener la clase unión y reescribir su definición para que cubra las dos variantes.
  - (iii) Residuo declarado.
- **`BKL-0029`.**
  - (i) Abrir el id y re-adjudicar.
  - (ii) Mantener la aproximación con su residuo declarado.
- **`BKL-0034`.**
  - (i) Un id para el Directorio.
  - (ii) Ids para los tres órganos que lingob separa.
  - (iii) Residuo declarado.

  Con (i) o (ii) hay que decidir además cómo entra el nivel órgano: como clase del árbol actual o como un nivel
  nuevo junto a clase, instancia y rol.
- **Marcas de revisión de B5.4:** revisar ahora con el uso medido en la tanda 0, o dejarlas para la tanda 1.

### 7.3 Decisión de la autora (30/09)

No había orientación registrada sobre el contenido del catálogo. Los remedios entran al ciclo (checklist X6 y
X7; laudo de r2, §1.6) y los aplica U-CAT-UNICO.
- **Diferencia 6/5:** opción (i), se aplica el laudo de B5.4. El JSON incorpora los seis y registra los cinco
  como lápidas no vigentes.
- **`BKL-0028`:** opción (i). Tres ids del exterior, quitando los alias de las entradas domésticas.
- **`BKL-0029`:** opción (i). Se abre el id para «titulares de cuenta corriente en el BCRA» y se re-adjudica el
  miembro del rol de convca.
- **`BKL-0034`:** opción (ii). Ids para Directorio, Alta Gerencia y Comité de auditoría, como clases bajo una
  clase nueva «órgano de gobierno», dentro del árbol actual y sin nivel nuevo. Los nombres de los ids los fija
  U-CAT-UNICO.
- **Marcas de revisión de B5.4** (`ministerio_de_economia`, `sociedad_de_proposito_especial`): se revisan con
  los datos de la tanda 1 (mención y registro de no mapeados), en código.

### 7.4 r2a y r2b

- **r2a:**
  - el JSON único y todo lo que se genera de él;
  - la re-resolución en código (§4) sobre las menciones guardadas.

  Con `BKL-0028`, quitar alias cambia R1 solo para los propuestos guardados. Las relaciones en que el modelo
  eligió el id doméstico no cambian sin la mención.
- **r2b:** el bloque del prompt regenerado desde el JSON entra al prefijo nuevo de U-PROMPT-R2. Lleva los ids
  nuevos: tres del exterior, el de titulares de cuenta corriente, la clase «órgano de gobierno» y sus tres
  clases.

### 7.5 Suite y shapes

- **Suite:**
  - LN-8: bloque y JSON sin diferencias; es el primer selftest de U-CAT-UNICO;
  - T7 y E4-a7 pasan con el catálogo único (plan, B2.11, unidad 8);
  - una entrada por cada id nuevo decidido, leída contra su chunk (condiciones de cierre de `BKL-0028`,
    `BKL-0029` y `BKL-0034`).
- **Shapes:**
  - S19 lee la fuente única, y el FAIL conocido por los seis ids desaparece;
  - S29, destino de `padre_sugerido` en el catálogo único: informativa hasta U-CAT-UNICO.

---

## 8. R6b (checklist X10)

### 8.1 Qué dicen los documentos y qué midió el pipeline

- R6b es el predicado `instrumenta`, la relación de un documento con la operación que instrumenta.
- ESQ-3a lo rechazó por evidencia bajo el criterio: 1 ficha dirigida y 0 azarosas (f. 74, `cryl::11.3`;
  `data/experiment/esq/laudo_ESQ-3a_retoques.md:163-168`). El fundamento fue que sería incoherente aprobarlo
  mientras la candidata (e), con 4 fichas, quedaba diferida.
- El laudo lo envió a r2 (§2). El laudo de r2 (§1.6) dijo que no entraba salvo por la vía de A8. Con la ventana
  usada, se decide aquí.
- No hay evidencia nueva desde ESQ-3a: ninguna unidad midió la demanda de `instrumenta` en la tanda 0
  (NO MEDIDO).
- Las cuatro categorías de omisión de la orientación (6) no registran una relación sin predicado, así que con
  ellas la evidencia no se acumularía sola.

### 8.2 Opciones

- **(i)** Sigue fuera, como residuo declarado para una release posterior.
- **(ii)** Sigue fuera y se agrega una forma de acumular evidencia: una categoría de omisión para relaciones sin
  predicado. Eso extiende las cuatro categorías de la orientación (6).
- **(iii)** Entra en r2b, con delimitación y verificación en la prueba pareada de U-PROMPT-R2. Choca con la
  cláusula «nada entra al congelado con delimitaciones sin verificar» del §1, según la lectura del §0.4.

### 8.3 Decisión de la autora (30/09)

No había orientación registrada. **Opción (ii), generalizada.**
- R6b sigue fuera, como residuo declarado.
- Se agrega la categoría de omisión `relacion_sin_predicado`, para toda relación que el texto expresa y el
  esquema no puede representar, no solo `instrumenta`.
- Extiende la orientación (6) a cinco categorías (§5.3). Así la evidencia de un predicado faltante se acumula
  por forma y queda disponible para una release posterior (lectura A del §0.4).

Relacionado, sin pedido de decisión: R6a (`exceptua_operacion`, Excepcion → Operacion) también fue a r2, con 0
emisiones en 43 unidades (laudo, §2). El par `exceptua` → Operacion de la matriz (§6) cubre ese caso sin
predicado nuevo, con 5 de 5 correctas en la lectura asistida, sin ampliarse con esa evidencia.

### 8.4 r2a, r2b, suite y shapes

Con la decisión (ii):
- **r2a:** nada; el crudo guardado no tiene la categoría.
- **r2b:** la categoría `relacion_sin_predicado` en el enum de omisiones del tool schema y su instrucción en el
  prompt.
- **Suite:** LN-7 con el enum de cinco valores.
- Ningún predicado nuevo: la matriz y S3 no cambian por R6b.

---

## 9. Resumen

| # | decisión | estado | r2a (código) | r2b (prompt) | suite / shapes |
|---|---|---|---|---|---|
| 0.4 | principio 11 frente al §1 | decisión (30/09): lectura (A) | — | — | — |
| 1 | umbrales como lista (tramo, valor, unidad, comparación, base) en 4 tipos | orientación (a)–(f); decisión (30/09): plazo en la lista, frecuencia en campo propio, listas de `comparacion` (con coeficiente) y `unidad` (con UVA), comparación por reglas definidas por su sentido desde el tramo (coeficiente, raíces, negación general, compuestas, adyacencia con «mínimo»/«máximo» + cuantía, y precedencia; sin marcador, el plazo con `comparacion_asumida` y el resto `no_determinada`), implementadas y calibradas en U-PYD; ponderadores como límite declarado; inversión de sentido como límite de la verificación | par B con verificación; frecuencia separada; reglas de comparación | par A, tool schema | matchers `BKL-0006`/`0023`; S18 reescrita; control cuantía ⇒ elemento; enums con marca; selftests de las reglas, con cuatro casos de control obligatorios (préstamo, filas 9, 21 y 15) |
| 1′ | precisión de `limita` | medida (U-LECTURA-LIMITA, `bf4709d`): 21 «sí», 7 «no» y 2 «no decidible» de 30; revisión de la autora sin cambios | — | instrucción sobre el destino de `limita`, con los ponderadores | — |
| 1″ | 4 `limita` desde «prohibicion» | nota; candidato `BKL-0038`; decisión (30/09): control en U-PYD, como marca | control de coherencia tipo–predicado | — | control nuevo |
| 2 | política por campo | orientación (1) | toda | solo valores nuevos | LN-1, LN-2; S24–S26 |
| 2′ | valores de las listas y alias | orientación (2); decisión (30/09): Obligacion.tipo (i), Restriccion.tipo (iii), Comunicacion.tipo con «externa», alias aceptados | derivaciones y alias | «externa» | S20, S24, S25 |
| 3 | mención y resolución de sujetos | orientación (3)–(5); decisión (30/09): R3 con lista inicial, calificador guardado, lecturas asistidas | R1, R2, R4; calificador | campo y reglas | LN-3, LN-4; S27 |
| 4 | registro de no mapeados | orientación (7); decisión (30/09): lectura asistida sobre r2b | sí | mención completa | LN-5, LN-6; S28 |
| 5 | omisiones con categoría y tramo | orientación (6); decisión (30/09): cinco categorías, lectura asistida de `meta_normativo` | lectura de lo guardado | campo y reglas 4 y 9; relaciones sin predicado | LN-7 (cinco valores) |
| 6 | matriz (X1, X11) | decisión (30/09): (ii), las dos ampliaciones, con desvío declarado; X11 alcanza la lectura asistida | re-validación, marcadas sin E3 y contadas aparte | tabla de firmas; E3; lectura de confirmación | S3; firmas nuevas; conteo de no verificadas |
| 7 | catálogo: 6/5, `BKL-0028`, `0029`, `0034` | decisión (30/09): (i), (i), (i) y (ii) con «órgano de gobierno»; marcas de B5.4 con la tanda 1 | JSON único | bloque regenerado | LN-8, T7, E4-a7; S19, S29; entradas por id nuevo |
| 8 | R6b (X10) | decisión (30/09): (ii) generalizada, `relacion_sin_predicado` | — | categoría de omisión | LN-7 |

## 10. Qué no cambia

- El texto del laudo congelado y sus dos enmiendas firmadas.
- Los grafos de la tanda 0 (KG-Tanda0-Desarrollo-r1, KG-Tanda0-Diez-r1 y el ensamblado de los cinco): quedan
  sellados. El ciclo produce una versión posterior.
- Los nueve tipos de entidad: no se agrega ninguno. El tipo para normas externas queda como trabajo futuro
  (§2.3), y los órganos de gobierno son clases del catálogo de sujetos, no un tipo nuevo (§7.3).
- Los trece predicados: no se agrega ninguno (R6b sigue fuera, §8.3). Cambia la matriz de firmas (§6.3).
- El prompt de E3 (laudo de r2, §3.2).
- El esquema congelado, que sigue vigente hasta la firma de esta enmienda.

## 11. Fuera de este laudo

- La guarda de modalidad (un deber emitido como Condicion): depende de la vigilancia (1) (laudo de r2, §1.6).
- Los pendientes de ensamblado de U-B1a (laudo de r2, §1.6).
- El laudo de los 15 `triaged` de B2.4 (checklist X9).
- Los candidatos de pipeline de U-R2-CODIGO: tablas, `BKL-0006`, `BKL-0037`, fusión y crudo del reintento.

## 12. Dependencias

- **Antes de firmar:** ninguna unidad pendiente. U-LECTURA-LIMITA cerró (unidad 4b, `bf4709d`) y su resultado está en §1.1.
- **Después de la firma:**
  - U-CAT-UNICO aplica §7;
  - U-PYD aplica §2, la verificación de §3 y §5, el control de coherencia de `BKL-0038` (§1.1) y las
    mediciones pendientes (ventana de tokens, largo mínimo del tramo, y frecuencia de cada forma de `comparacion` y `unidad` en los tramos de r2a); además, la implementación exacta de las reglas de §1.3 y su calibración, con los falsos positivos de «factor» y la regla de «igual», y con los cuatro casos de control como prueba obligatoria;
  - U-R2-CODIGO aplica §1 (r2a), la resolución de §3 y el registro de §4;
  - la medición r2a separa lo que corrige el código;
  - U-PROMPT-R2 lleva lo marcado r2b;
  - U-REEXT-T0 re-extrae y abre la medición de la tasa real de menciones y de la meta de §4;
  - después de U-REEXT-T0 y antes de la tanda 1, la lectura de confirmación de las dos firmas nuevas de
    `condicion_de` (§6.3; plan, B2.11, unidad 11);
  - las lecturas asistidas de §3.3, §4.3 y §5.3, sobre datos de r2b.

## Firma

FIRMADA por la autora el 01/10/2026. Rige desde esta firma.

## Notas posteriores a la firma

El texto firmado no se edita; estas notas se leen junto con él.

- **01/10/2026 — §7.3, nombre de la clase que agrupa los órganos (decisión de la autora).**
  - La clase que agrupa Directorio, Alta Gerencia y Comité de auditoría se llama «Instancias de
    gobierno societario» (`Sujeto_instancia_de_gobierno_societario`), no «órgano de gobierno».
  - Motivo, por el principio 11: en el corpus, «órgano de gobierno» es la asamblea de accionistas o
    socios. `lavdin::1.3.1.2` distingue los órganos de gobierno (accionistas, socios), de
    administración (directores, consejeros) y de fiscalización (síndicos); `lingeef::1.2::intro`
    habla de la «Asamblea de Accionistas u órgano de gobierno». «Órgano(s) de gobierno» aparece 23
    veces en 11 TOs.
  - Con el nombre firmado, la resolución en código habría asignado esas menciones a la clase nueva.
  - El nombre nuevo se ancla en `lingob::1.2::intro`: «El código de gobierno societario se refiere
    a la manera en la que el Directorio y la Alta Gerencia de la entidad financiera dirigen sus
    actividades».
  - Aplicado en el catálogo r2 (U-CAT-UNICO C2, `bd2122d`).
  - La asamblea queda sin id en el catálogo, como candidata del registro de no mapeados (§4).
- **01/10/2026 — §1.3, punto 3: «mayor», «menor» e «inferior» (aclaración, decisión de la autora).**
  - Las formas son «mayor a», «mayores a», «menor a», «menores a», «inferior a» e «inferiores a».
    «Mayor», «menor» e «inferior» sin «a» no son marcadores.
  - Esa era la decisión de la autora. La redacción firmada («“mayor” o “mayores a”», «“inferior” o
    “inferiores a”», «“menor” o “menores a”») la dejaba ambigua: se podía leer que «mayor», «menor»
    o «inferior» solos ya eran marcadores.
  - Caso que lo mostró: en `cap::4.3.3.1` (fila 15 de la lectura de `limita`), «el menor entre 1 año
    y el plazo residual» quedaba como máximo estricto. Con la aclaración, «1 año» queda sin marcador
    y, por ser un plazo, recibe máximo inclusivo con `comparacion_asumida`. Así se lee el texto: el
    horizonte es como mucho 1 año.
  - Lo aplica U-PYD (plan, B2.11, unidad 7) en sus reglas de comparación.
- **02/10/2026 — §1.5, la «marca» de S18 (decisión de la autora, tras el FRENO R5 de U-R2-CODIGO, `92b45d6`).**
  - §1.5 reescribe S18 como «Restricción limite_cuantitativo ⇒ lista no vacía o marca» sin definir la
    marca. La marca es un elemento de umbral sin `valor`, con su `comparacion` y su `base`, para los
    límites relativos: los que comparan con otra magnitud y no con un número («no podrá exceder el
    nivel alcanzado durante el mes…», «no supere el monto del aporte oportunamente ingresado…»).
    `ElementoUmbral` ya admite `valor` nulo (`data/experiment/pyd_r2/code/modelos_r2.py`).
  - En la prueba r2a de desarrollo, 25 de las 273 Restricciones `limite_cuantitativo` no tienen
    lista ni umbral guardado (26 de 301 en diez), y ninguna de las 25 tiene cuantía numérica en su
    descripción (`data/experiment/r2_codigo/r5_freno.md`, §R5; `scripts/shapes_validator.py --perfil r2`).
  - S18 sigue bloqueante. En r2a el elemento no se puede armar sin el tramo: el NO PASA de S18 sobre
    la prueba r2a queda declarado y no frena la medición r2a (plan, B2.11, unidad 9). En r2b, E1
    emite el tramo del límite relativo y el código arma el elemento (plan, unidad 10).
