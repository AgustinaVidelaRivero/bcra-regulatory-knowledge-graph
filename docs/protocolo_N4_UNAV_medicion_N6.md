# N4 — el protocolo de medición de N6, sellado (U-NAV-DISENO)

Sellado el 26/10/2026, después del diagnóstico de A2.2 (N5b) y de la lectura de la autora, y antes de N6 (mandato v6 FIRMADO,
`c2ddf5f7`, §4, N4). Parte del borrador de la parte 1 (`N4_protocolo_BORRADOR_UNAV_parte1.md`, sha256 `0a4c421d…`, del 18/10/2026).
Lo que cambia al sellar va en el §8, cada cosa con su ancla; lo demás es el borrador tal cual. N5b puede sumar o sacar una candidata
dentro de una familia del §3, y lo declara; las seis familias y las 8 configuraciones no cambian.

## 1. Lo fijo

- **Grafo** (decisión 5): el acumulado de las tandas 0 y 1 sin cola, `tanda1/t3/acumulado/ens_treinta_r2b_sincola/r2/kg.json`, sha256
  `0435d41f9c7b…` (su `.gz` y su sello en `e2615b36`). En Neo4j va como `KG_Acumulado_Tandas0y1_r2b_sincola`, sin envoltorio.
- **El agente:** el del banco (`claude-sonnet-5`, CLI 2.1.241, `--bare`), con el R5 de A2.2: 30 llamadas en el prompt, `--max-turns` 32 y
  `--max-budget-usd` 1,80, iguales en los dos brazos (registro, §50, punto 4, `:1750`).
- **El prompt:** el texto del §5 del mandato, **sin los cinco nombres de TOs** de desarrollo, y en todas las configuraciones, la base
  incluida, **la parte común de la plantilla** (decisión 9; texto en N2). Se declara al comparar la base con las trazas que ya existen: la
  separan el texto del prompt, la parte común y el banco.
- **El juez:** el de EV2 (`data/experiment/ev2_juez/juez.py`, modelo y prompt por sha), 3 repeticiones por respuesta, veredicto por
  criterio modal.
- **Las preguntas:** las 30 de N3 (7 de cupo y 23 de la mezcla), selladas antes de usarse; las 3 de ejemplo de la familia 6 nunca se
  miden (decisión 10). EV2, las 20 de la tanda 0 y nada de B6.3 se usan para medir.

## 2. Las 8 configuraciones (decisión 3)

| id | configuración | herramientas | texto del bloque de herramientas |
|---|---|---|---|
| B | base | `buscar_nodos`, `ver_nodo`, `ver_vecinos` (firma v1), sin marcas | el de hoy |
| T | todas | B + familias 1 a 5 | el de hoy + familia 6 (instrucciones y 3 ejemplos) |
| T−F1 a T−F5 | todas menos una familia | T sin las herramientas de esa familia | familia 6 sin las líneas de las herramientas que salen |
| T−F6 | todas menos la estrategia | B + familias 1 a 5 | el de hoy, sin la familia 6 |

- **La familia 2 trae dos herramientas:** `ver_punto` y la candidata `ver_descendientes` (§9). Están en T y en toda «T−Fk» con k
  distinto de 2; «T−F2» saca las dos. B no las tiene.
- **B se corre 3 veces** (decisión 4), para medir la variación entre corridas; el resto, una vez. Corridas: (8 + 2) × 30 = 300.
- Las marcas de verificación entran con las aristas que muestran las familias 2, 3 y 5; B queda sin ellas.

## 3. Las preguntas de la necesidad de cada familia (§3)

| familia | preguntas de su necesidad en N3 |
|---|---|
| 1 entrada | la de cupo 1 |
| 2 vista de punto | las de cupo 4, 5, 6 y 7 |
| 3 cierre de remisiones | la de cupo 2 y las de la mezcla del subtipo «remisión» |
| 4 índice del TO | la de cupo 3 y las de la mezcla del subtipo «excepción en un hijo» |
| 5 vecinos selectivos | las de la mezcla que pasan por un hub, con la regla de abajo |
| 6 estrategia | las de la mezcla de varios puntos |

**Regla de la familia 5** (de la medición 4 de N1; queda fija con este sello): una pregunta pasa por un hub si (a) un nodo de su gold es
hub del 1 % del acumulado (grado ≥ 38: 216 nodos, `comun_unav.hubs`), o (b) desde el primer resultado de `buscar_nodos` con la pregunta,
el camino más corto al gold con todas las aristas es más corto que sin pasar por hubs del 1 % ni por TextoOrdenado, o sin ellos no hay
camino en 6 pasos. Gold: los portadores de sus criterios por R-CITA (la cita sin los cortes de palabra) en el TO del ancla; si no hay,
los nodos del ancla. **La lista** sale de aplicar la regla a las 30 de N3, fuera de línea y a USD 0, con `scripts/m234_acumulado_unav.py`
(la función de los pasos), en el paso 0 de N6, antes de la primera llamada; va con su sha256 en el FRENO de ese paso (§8, punto 6).

## 4. Lo que se mide

Por configuración, sobre las 30 y sobre las preguntas de la necesidad de cada familia:
- **fidelidad por criterio:** criterios cumplidos / criterios, con el modal de las 3 repeticiones del juez;
- **precisión de citas:** fundada, existente y al ancla, con el instrumento de exactitud de cita adaptado a las citas del banco, el mismo
  de B6.3, sellado antes de ver cualquier resultado (§8, punto 7);
- **costo por pregunta:** R9 (tokens × `agentes/precios_sellados.json`, nunca `total_cost_usd`);
- **llamadas a herramientas y respuestas que llegan al tope;**
- **las cuatro clases de N1 sobre los criterios no cumplidos,** con la regla sellada (`n1/regla_n1_cuatro_clases_UNAV.md`, `db2cc290…`)
  sobre el acumulado, y su lectura asistida para los no decidibles;
- **lo verificado y lo no verificado, aparte:** las mismas medidas para las respuestas que abren o citan un nodo o una arista con una
  marca de verificación o de sujeto derivado, y para las demás. En el grafo sin cola no hay nodos de la cola; las marcas de las aristas
  llegan con N5.

## 5. La regla de decisión, escrita antes de medir (§6)

- **Variación entre corridas de la base:** para un conjunto de preguntas Q, V(Q) = la diferencia entre la mayor y la menor fidelidad por
  criterio de B sobre Q en sus 3 corridas.
- **Comparación pareada por pregunta:** dos configuraciones se comparan sobre las mismas preguntas: Δ(Q) = fidelidad por criterio de una
  menos la de la otra sobre Q, y al lado cuántas preguntas suben, bajan o quedan igual.
- **Por familia (cambio de la v6):** cada familia k se informa en las preguntas de su necesidad, Qk. «T−Fk» solo es elegible si
  fidelidad(T, Qk) − fidelidad(T−Fk, Qk) ≤ V(Qk). Así ninguna familia se descarta porque otra la compensa en el total.
- **Elección:** entre B, T y las «T−Fk» elegibles, la de mayor fidelidad por criterio sobre las 30. Si dos quedan dentro de V(30), gana la
  que llega menos veces al tope de llamadas, y después la más barata (R9 medio por pregunta).
- **Requisito, no resultado:** la configuración que se pre-registre pasa el caso obligatorio de la jerarquía. En el acumulado, la
  Definicion de `cla::5.1.1` (no `cla::5.1.1::intro`, que no tiene nodos) y la Excepcion de `cla::5.1.1.1` están a 2 aristas solo
  pasando por un hub, y sin hubs no se conectan (`n4/salidas/caso_jerarquia_UNAV.json`, `scripts/caso_jerarquia_unav.py`). El caso se
  prueba en el selftest de N5 (sin modelo): con las herramientas de la configuración, desde la Definicion se llega a la Excepcion en 2
  llamadas como mucho. Si la regla deja afuera la familia que lo cubre, la configuración no se pre-registra así y vuelve a la autora.

## 6. La híbrida en el brazo de fragmentos (§6 bis)

- **F1:** la configuración BM25 de A2.2, 3 veces, contra la misma con la forma de fragmentos de la familia 1 (la híbrida: BM25 más el
  denso, con los filtros por TO y por punto), una vez. **Las dos llevan la parte común de la plantilla, así que F1 mide solo la híbrida.**
  El denso no cambia y no se mide contra la híbrida.
- **Regla:** la híbrida entra al brazo de fragmentos si fidelidad(BM25 con la híbrida, 30) ≥ fidelidad(BM25, 30) − Vfrag(30), con Vfrag la
  variación entre las 3 corridas de BM25. Si entra, reemplaza a BM25 y el denso queda: dos comparaciones principales con Holm (decisión 7,
  (a)). Si no, el brazo queda como en A2.2, y se declara.
- Se declara que la parte común no se midió en fragmentos (decisión 9).

## 7. El costo y el tope

- **El tope de N6:** USD 130, con freno en 100 (registro, §51, `:1795`, decisión del 19/10/2026; el borrador decía 85 y 64).
- **Lo medido para N6 con A2.2,** sin la candidata: USD 56,48 con la media por sesión de cada brazo y 180,09 con el máximo en todas
  (paquete de la mesa, §284, `costo_por_caracter_de_herramienta_A2_2_mesa.py`). El central entra con o sin la candidata, hasta 70,97;
  el máximo no entra con ninguna, y lo corta el freno. Las herramientas de N6 no son las de A2.2: es una estimación (NO VERIFICADA para
  N6).
- **La candidata:** con el marginal medido en las 97 sesiones del grafo de A2.2 (USD 0,00335 por cada 1.000 caracteres de resultado),
  entre USD 3,02 (una llamada de 5.000 caracteres por sesión) y 14,49 (tres llamadas al tope de 8.000) más, en las 180 sesiones donde
  está. Es una cota hacia arriba.
- El cálculo del borrador (`n4/salidas/costo_n6_UNAV.json`, `scripts/costo_n4_unav.py`) queda como referencia: opción A, 300 corridas,
  central 28,12 y alto 58,08; N6 entero (A + F1), alto 81,37. Rige la A (decisión 3).

## 8. Lo que cambia al sellar, respecto del borrador

1. **R5:** el de A2.2 (30, 32 y 1,80). El borrador decía 10, 12 y 0,30, el de antes de firmar el pre-registro de A2.2.
2. **La plantilla:** sin los cinco nombres de TOs. Hoy `data/experiment/banco_mcp/agentes/plantilla_prompt.txt` los nombra en su renglón
   1 (sha256 `dd99bfd3…`) y la configuración de prueba de N6 (`paralelo/config_agentes_n6_prueba.json`, `:72`) la usa. La de A2.2,
   `a2_2/plantilla_prompt_a2_2.txt` (`ff6c3d0a…`), no los nombra. El pre-registro de B6.3 (`:325-326`) dice lo mismo desde N6. El paso
   0 de N6 controla, por código, que la plantilla de cada una de sus configuraciones no nombre ninguno de los cinco TOs de desarrollo y
   que lleve la parte común; N7 y B6.3 heredan la de N6.
3. **La familia 2 suma `ver_descendientes`** (§9). Las configuraciones siguen siendo 8 y las corridas, 300 del grafo y 120 de F1.
4. **El tope de N6:** 130 y 100 (§7).
5. **El grafo, sin envoltorio:** desde N5 el cargador acepta toda clave de `grafos.py`.
6. **La lista de la familia 5:** la regla queda fija con este sello; la lista se calcula y se sella en el paso 0 de N6, antes de la
   primera llamada (§3). El borrador decía que la lista entraba a este sello: pide Neo4j con el acumulado y las 30 preguntas de N3, que la
   mesa no abre. La regla es mecánica y queda escrita antes de medir.
7. **La precisión de citas:** el instrumento de B6.3 (`scripts/ucita2_indicadores.py`) lee citas con `source_doc` y `location`, aborta
   con más de un ancla y pide `seen_provenances`, que el banco no arma. Se mide con su adaptación al banco, la misma de B6.3, sellada antes
   de ver cualquier resultado, a partir de lo que guarda cada sesión: la meta (`final_json_R4.citas`) y el log R1 (la salida de cada
   llamada). Lo que mide no cambia.

## 9. La candidata de F2: `ver_descendientes`

**La decisión de la autora, tal cual** (26/10/2026, recibida a las 22:04:09, después de su lectura de N5b): «La candidata va en F2,
ver_descendientes, como la propusiste (opción a), y se implementa esta noche, como ya está despachada.»

- **La herramienta:** `ver_descendientes(punto, niveles=2, desde=0)`. Da, en una sola llamada, el texto propio entero de cada
  descendiente del punto hasta `niveles` (1 a 3), en orden de lectura, cada uno con su unidad, su título y su cantidad de nodos. Tope de
  8.000 caracteres por llamada, con el pie de `desde` como el de `buscar_puntos`.
- **Por qué:** la 2c del diagnóstico (§10). El portador estaba en un hijo del punto que el agente vio y no abrió, y ninguna candidata de
  N6 le muestra al agente el contenido de los descendientes en una llamada.
- **Por qué F2 y no F4:** la necesidad de F2 es «lo que el nodo no lleva» y «las varias llamadas por punto» (mandato, §3); F4 es la
  estructura para llegar al punto, y su ablación separaría estructura de contenido.
- **Su marca:** propia del grafo, como F2. El texto sale de la E0, que los dos brazos comparten.
- **Su implementación:** sobre una copia, con su selftest sobre el índice por punto de N5, y su prueba sobre los tres TOs del grafo
  evaluado con secciones repetidas, con la regla de la unión por clave. Su commit va antes del paso 0 de N6.

## 10. El diagnóstico de N5b y sus límites

Fuente: `FRENO_UNAV_N5b.md` (`99d8a518…`) y su paquete (`fb844b98…`), revisados por la mesa por código (8 de 8). La regla de N1
(`db2cc290…`), igual antes y después de clasificar; la de N5b (`7b1c3c38…`), sellada antes.

**La población:** 39 criterios no cumplidos de 20 pares del brazo del grafo de A2.2 con final parcial (19) o incorrecto (1).

| clase | con la regla sola | con la lectura asistida |
|---|---:|---:|
| 3 el contenido no estaba en el grafo | 0 | 0 |
| 1 no encontró el nodo | 7 | 8 |
| 2a apareció y no lo abrió | 1 | 2 |
| 2b vecino de un nodo abierto | 4 | 4 |
| 2c bajo un punto visto | 18 | 18 |
| 4 llegó bien y generó mal | 6 | 6 |
| no decidible | 3 | 1 |
| **total** | **39** | **39** |

- **Navegación** (1 y 2): 30 de 39 con la regla y 32 con la lectura.
- **La 2c**, 18, con los 6 criterios cuya traza llegó al tope de llamadas.
- **El portador** estaba en el punto del ancla en 17 criterios y solo bajo el ancla en 21; fuera del subárbol del ancla, en ninguno.
- **La lectura de la autora,** tal cual (26/10/2026, recibida a las 18:19:05): «el portador estaba solo debajo del ancla en 21 de los 39
  criterios, y en el punto del ancla en 17; fuera de su subárbol, en ninguno. La 2c da 18, y los 6 criterios con la sesión al tope de
  llamadas son de la 2c.»
- **Fuera de `ver_descendientes`, no se suma ni se saca ninguna candidata** (la autora, 18:19:05: «No saco ninguna candidata»).

**Sus límites, declarados:**
1. Sin la cota por herramienta de N1 (decisión de la autora del 26/10/2026, recibida a las 11:59:01): para los 32 criterios de navegación
   no se sabe qué familia los habría alcanzado.
2. Sin el cruce con A0.2 ni las uniones de operaciones de N1.
3. La lectura asistida es enmascarada: decide por la cobertura de claves y tres explicaciones, y deja 1 no decidible.
4. «A la vista», con el contenido repartido, pide que el agente haya abierto todos los portadores: es estricto.
5. El patrón (a) de N1 da 0 en el r2b; el (a′) es una adaptación declarada en la regla de N5b.
6. n chico: 39 criterios de 20 pares, de un solo agente y un solo grafo, el de desarrollo y no el de N6. En los pares a N = 3 se
   clasifica una sola re-corrida.
7. La exposición de EV2: en la consola de la sesión de N5b salieron fragmentos de citas y preguntas de EV2. Ningún archivo de N5b los
   trae, y todos son texto de la norma (registro, §125). EV2 se usa solo para diagnosticar, nunca para ajustar.
