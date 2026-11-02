# Enmienda al pre-registro de la tanda 0 — observación (12): tasa de aristas de extracción correctas contra el texto

**FIRMADO por la autora — 2026-09-27** · Fecha: 2026-09-27.

Enmienda con fecha a `docs/preregistro_tanda0.md` (FIRMADO por la autora el
2026-09-25, sellado en `c80b03f`, sha256
`4b45145d7d7f8f50…`, verificado con `git show c80b03f:docs/preregistro_tanda0.md | shasum -a 256`
el 27/09/2026). El pre-registro **no se edita**: esta enmienda vive al lado,
como la enmienda al §7 del laudo congelado
(`data/experiment/esq/enmienda_ventana_correccion_2026-09-25.md`) vive al lado
del laudo, y se lee junto con él. Cumple la cláusula de cierre del propio
pre-registro (`:909-911`): «toda modificación posterior es enmienda separada,
nunca ajuste silencioso». Se escribe **antes de correr la fase 2** (A9 paso 1
sin cerrar al 27/09) y agrega una observación pre-registrada; no cambia
ninguna decisión sellada.

## 1. Lo que el pre-registro dice hoy, transcrito tal como está

A4, preámbulo (`:451-458`):

> Rige la decisión 6: las observaciones (10) y (11) y las vigilancias (1) a (9)
> **se miden contra sus líneas de base, sin umbral**; el único criterio de
> retiro es el principio de gobierno del laudo congelado §1 («Se retira lo que
> produce falsedad en campo estructurado en material fresco; se acepta con
> residuo declarado lo que produce omisión visible o error con tasa medida y
> balance favorable»). Las bandas que escribo abajo son **ayudas de lectura
> pre-declaradas**, no umbrales: una observación fuera de banda es un hecho a
> explicar en el reporte, no un retiro.

A3.5, decisión de la autora del 25/09 (`:445-448`):

> Decisión de la autora (25/09/2026): una sola extracción y tres ensamblados
> determinísticos. C3 y C4 se corren sobre el ensamblado de los cinco TOs de
> desarrollo solos; la observación (10) de la tanda 0 se lee sobre el ensamblado
> de la tanda 0 sola; la observación (11) y las preguntas nuevas sobre los cinco se
> corren sobre el ensamblado de los diez TOs.

A4.1, definición del universo de aristas de extracción (`:466-476`, comando
sobre r1): aristas de extracción = total − `relation == 'referencia'` −
`rol_fuente == 'esqueleto'`; sobre r1, 17.772 − 5.680 − 82 = 12.010.

A5, regla (`:608-610`):

> Regla: **la fase 2 no arranca con instrumentos PENDIENTES.** Cada PENDIENTE
> de esta tabla es un gate técnico de A9 que se cierra por su unidad del plan o
> por el mandato de fase 2, y se reporta cerrado antes del ok de la autora.

A8, decisión 6 transcrita (`:845-847`):

> **Decisión 6, transcrita:** «Las observaciones (10) y (11) y las vigilancias
> (1) a (9) de B6.1 se miden en la tanda 0 contra sus líneas de base, sin
> umbral; el único criterio de retiro es el principio de gobierno.»

A9, pasos afectados (`:876-882`, `:887-890`, `:897-898`): paso 1 (gates
técnicos de A5 en verde, con la lista de siete), paso 4 (corrida E0 → E5 sobre
los diez TOs con el manifiesto de la tanda 0) y paso 7 (lectura de
observaciones y vigilancias contra sus líneas de base, sin umbral).

## 2. Texto nuevo — decisión de la autora del 27/09/2026

### 2.1 Se agrega a A4 la sección A4.4 — Observación (12): tasa de aristas de extracción correctas contra el texto

**Qué mide.** De las aristas de extracción del ensamblado de la tanda 0 sola
(el mismo ensamblado sobre el que se lee la observación (10), A3.5), una
muestra aleatoria de 30 se lee contra el texto del punto ancla y recibe un
veredicto por arista. Se reporta la tasa de correctas como observación.

**Universo.** Las aristas de extracción tal como A4.1 las define: todas las
aristas del `kg.json` del ensamblado de la tanda 0 sola, menos las de
`relation == 'referencia'` y menos las de `rol_fuente == 'esqueleto'`
(mismo comando de A4.1, aplicado a ese `kg.json`; la cifra del universo se
reporta con el sha256 del grafo).

**Sorteo, reproducible por regla y no solo por semilla.** Las aristas del
universo se ordenan por la tripla `(source, relation, target)` en orden
lexicográfico de cadenas; sobre esa lista se toma
`random.Random(20260927).sample(range(n), 30)` y los 30 índices se ordenan
ascendentes, como en el precedente de la muestra de referencias de U-B1a
(`data/experiment/reextraccion_v2/corpus_v2/r1_referencias.py:304-305`,
semilla 20260823). Semilla de esta observación: **20260927**. El sorteo lo
ejecuta el instrumento de 2.2 y su salida se sella por commit **antes de
que nadie lea una arista**.

**Material permitido para leer cada arista.** Origen (id, tipo, label,
propiedades), relación, destino (id, tipo, label, propiedades), propiedades
de la arista, y el texto del punto ancla de la provenance de la arista, tal
como E0 lo delimita para el `chunk_id` de esa provenance. No se consulta
ninguna traza, veredicto de juez, respuesta del agente ni métrica de las
celdas C1–C4.

**Quién lee y qué anota.** La autora, arista por arista, en el orden del
sorteo, con veredicto **correcta / incorrecta / no decidible** y una nota de
una línea. En cada **incorrecta**, además, la regla del pipeline implicada,
con el vocabulario de `capa_pipeline` que B2.5 fija para el backlog:
`E0`, `E1-prompt`, `E1-validador`, `catálogo`, `E2`, `E3`, `ensamblado`
(`retriever` y `agente` no aplican a una arista). Los veredictos se guardan en
un archivo aparte del sorteo, con el sha256 del archivo sorteado que
anotan, y se sellan por commit.

**Línea de base: SIN LÍNEA DE BASE.** El único precedente de lectura por
muestra es la inspección de 30 aristas `referencia` sobre r1 (30 OK, 0
DUDOSA, 0 MAL; `salida_r1/referencias_muestra30_estado_inspeccion.json`,
2026-08-23), que cubre una sola relación y otra escala de veredicto, y no es
comparable. Se declara sin línea de base, como las vigilancias 6, 7 y 9 de
A4.3.

**Cómo se reporta.** Tasa cruda «correctas de 30», con las no decidibles
contadas aparte y sin sacarlas del denominador, e **intervalo de Wilson al
95 %** sobre correctas / 30, en cumplimiento de la exigencia 4 del mapa
(`docs/plan_tesis.md:352-353`: intervalos de Wilson para toda proporción
reportada). Sin umbral y sin banda: rige la decisión 6 tal como está
transcrita en §1; el único criterio de retiro sigue siendo el principio de
gobierno del laudo congelado §1. Una tasa baja es un hecho a explicar en el
reporte, no un retiro.

**Destino de cada incorrecta.** Entrada propia en el backlog con su
`capa_pipeline` (vía de corrección en pipeline, B2.5) para la release r2,
por el principio 9; solo una incorrecta que sea falsedad de esquema en campo
estructurado se lee además por la vía de A8, que no cambia.

**Las 30 aristas leídas son candidatas a sellarse como tests de respuesta
conocida de la regression suite** (B2.1), con el precedente de T5: la
muestra de 30 referencias inspeccionada en U-B1a se selló como test
(`r1_tests.py:48-53`). Si se sellan, es decisión de la autora al cerrar la
lectura, con la misma regla de direccionamiento de B2.1 (nunca por
`provenance[0]` ni por id de nodo).

### 2.2 Se agrega a A5 una fila y un gate — instrumento nuevo, PENDIENTE (gate 8)

| instrumento | ruta | commit / sha | estado | cómo lo verifiqué |
|---|---|---|---|---|
| Sorteo de la observación (12) | `scripts/muestra_aristas_obs12.py` (nombre previsto) | — | **NO ENCONTRADO → PENDIENTE (gate 8; se escribe en el mandato de fase 2 o en unidad propia, USD 0)**: toma `--kg`, `--semilla`, `--n` y `--out`; aplica el universo de A4.1 y el orden y el sorteo de 2.1; escribe un JSON con el sha256 del grafo, la semilla, el tamaño del universo, los 30 índices y, por arista, origen, relación, destino, propiedades, provenance y el texto del punto ancla resuelto en E0; determinístico (doble corrida byte-idéntica); selftest sobre un grafo sintético. | `ls scripts/muestra_aristas_obs12.py` → no existe (27/09) |

Al resumen de A5 se agrega «sorteo de la observación (12)» a la lista de
PENDIENTES. La regla no cambia: **la fase 2 no arranca con instrumentos
PENDIENTES.**

### 2.3 Se agrega a A9 un paso, después del ensamblado de la tanda 0 sola

**Paso 4bis — Sorteo de la observación (12).** Inmediatamente después del
paso 4, cuando existe el `kg.json` del ensamblado de la tanda 0 sola y antes
del gate de release y de toda lectura: se corre el instrumento de 2.2 con
la semilla 20260927 sobre ese `kg.json`, y su salida se sella por commit con
el sha256 del grafo. La **lectura** de las 30 aristas por la autora es parte
del paso 7 (lectura de observaciones y vigilancias), y sus veredictos se
sellan por commit antes del paso 8. En el paso 8, la observación (12) entra
al reporte en el mismo formato que (10) y (11): una fila, sin predicción
numérica («SIN LÍNEA DE BASE»), con la tasa cruda, el intervalo de Wilson,
la lista de incorrectas con su `capa_pipeline` y la de no decidibles.

## 3. Qué no cambia

- **A8 no cambia.** Ningún resultado de la observación (12) autoriza abrir la
  ventana del §7 por sí solo; rige la vía de A8 tal como está sellada. Las
  incorrectas de pipeline, catálogo o ensamblado van a su destino de siempre
  (backlog con `capa_pipeline`, release r2, principio 9).
- **La decisión 6 no cambia**: (12) se lee sin umbral y sin banda; el único
  criterio de retiro es el principio de gobierno.
- **Las celdas C1–C4, las observaciones (10) y (11) y las vigilancias (1) a
  (9) no cambian**; (12) se lee sobre el ensamblado que (10) ya usa, sin
  ensamblado adicional ni extracción adicional. Costo de API: USD 0; el costo
  es tiempo de lectura de la autora, 30 aristas.
- **El esquema congelado no se toca** y el grafo de la tanda 0 no se anota ni
  se corrige a mano (A1, «es caja negra»): los veredictos viven en un archivo
  aparte, nunca en el `kg.json`.
- **No se agrega ninguna predicción** para (12): declarar una tasa esperada
  sin línea de base sería inventarla.

## Firma

Firmada por la autora el 2026-09-27.
