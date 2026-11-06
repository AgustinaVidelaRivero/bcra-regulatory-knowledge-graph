# Mandato U-COMP-E1 — comparación chica del modelo de E1 antes de la tanda 1

**FIRMADO por la autora el 06/10/2026** (firma por mensaje de la autora; versión para firmar en `f36b01d`). **Decisiones al firmar:** (1)
nombre U-COMP-E1; (2) lectura cegada con códigos; (3) tope USD 35 con doble corrida en los dos brazos. **Ajustes a la firma** (revisión
de la mesa tras el FRENO de U-DIAG-E3-LISTAS, 06/10/2026): los brazos se comparan en su intento 0 y sin E3, porque el verificador no
recibe el bloque que abre la lista en 1.015 de 1.054 ítems y reclama en falso sobre ellos, y los ítems son la mayoría de las 87 unidades;
la línea de base de Haiku es su intento 0 (`extracciones_e1.jsonl`), que coincide con la extracción final leída en T4 en 79 de las 87
unidades, con una relectura de la mesa en las 8 que tuvieron reintento; el tramo se verifica por código (`validador_r2.verificar_tramo_entidad`,
texto propio y heredado), no por E3. Re-redacción del borrador postergado P6 de U-PROMPT-R2 (`docs/mandatos/UPROMPT_R2_P6_exploracion_modelo_E1.md`,
05/10/2026), por decisión de la autora del 06/10/2026: la comparación se adelanta antes de la tanda 1, acotada a las dos fallas mayores
que dejó T4 de U-REEXT-T0 y a unidades ya leídas, con un gasto de API de hasta USD 35. Toda llamada al modelo respeta `docs/decisiones_caching_extraccion.md` (cinco decisiones vinculantes).

QUÉ PREGUNTA. Con el prefijo congelado de la release r2b (`322c5a23e9b7`) y `claude-haiku-4-5` a temperatura 0, T4 midió dos fallas
(`data/experiment/reext_t0/reporte_u_reext_t0.md` §2, `0a3ac81`; `t4/salida/tasas_t4.json`, `889b2f9`): (1) el supuesto de una norma
casi nunca sale como Condicion con su relación hacia ella: 43 de 137 supuestos (Wilson al 95 % [0,242; 0,396]), 77 dentro de la norma;
(2) las omisiones `meta_normativo` tienen contenido normativo: 19 de 30 sin marca del contador y 27 de 30 con marca (46 de 60 leídas),
entre 400 y 525 en el tramo propio de la tanda 0. La pregunta es si esas fallas son del modelo o del diseño: ¿un modelo más grande, con
el mismo prefijo y un pedido adaptado, las corrige?

QUÉ NO DECIDE. El modelo de E1 de la release r2b sigue siendo `claude-haiku-4-5` con temperatura 0 (decisión de la autora del 05/10/2026,
`1d8fe9f`; plan `:400`). Esta unidad mide y aplica el criterio de abajo; si un brazo cambia el cuadro, la autora abre, aparte, la
decisión de una release nueva con sus costos; si ninguno lo cambia, las dos fallas se declaran límite del diseño con las cifras de los
tres modelos. El experimento completo de B6.4 (plan `:778`) queda para después del escalado.

LÍNEA DE BASE. `claude-haiku-4-5`, perfil r2b, en su **intento 0**: la primera respuesta de E1, sin el ratchet de E3
(`corpus_tanda0/salida_r2b/<to>/extracciones_e1.jsonl`, una fila por unidad; difiere de la final en toda unidad con reintento). Las
lecturas de T4 adjudicadas por la autora (`04cec96`, `c9d4c40`) valen como lecturas del intento 0 en 79 de las 87 unidades (`n_reintentos`
0 en `finales.jsonl`); en las 8 con un reintento (5 `aceptado_tras_reintento`, 3 `cola_humana`) la mesa relee el intento 0 con las mismas
fichas, y la extracción final leída en T4 queda aparte como línea de base del pipeline. Cuatro de las 87 están en la cola humana (3
`cola_humana`, 1 `veredicto_inutilizable`): entran igual, declaradas. No se paga de nuevo.

UNIDADES. Las 87 unidades ya leídas en T4: las 30 del grupo c (`t4/salida/fichas_punto7_grupo_c.json`, `mas_de_un_supuesto`; 137
supuestos clasificados) y las 59 unidades de las 60 omisiones leídas (`fichas_punto8_omisiones.json`; dos unidades están en los dos
grupos). Por TO: cap 15, cla 13, ctacte 7, ext 29, lingob 7, pagjub 2, polcre 3, pro 4, ric 7. Lista sellada en `comp_e1/unidades.json` con su sha256 en C0.

BRAZOS (los de P6, sin el brazo F). En los dos: el prefijo de la release r2b con su punto de caché, el mismo mensaje por unidad que armó
E1 en U-REEXT-T0 (perfil r2b, E0 r2b de `salida_tanda0_r2b/`), el mismo tool schema (sin `strict`), dos corridas por brazo (decisión 3 al firmar), cada una en su base propia y en un
namespace que no es el del pipeline. Los brazos se evalúan en su intento 0: sin ratchet y sin E3 (ajuste a la firma).

| brazo | modelo | qué cambia del pedido de E1 (los modelos nuevos rechazan el pedido de r2b tal cual; P6, consulta del 05/10/2026) | corridas |
|---|---|---|---|
| H | `claude-haiku-4-5` | nada; las salidas de U-REEXT-T0, sin pagar | 1 (la de r2b) |
| S | `claude-sonnet-5-5` | sin `temperature`; `tool_choice` `auto`; `thinking` `between_tools`; `max_tokens` 16.384 | 2 |
| O | `claude-opus-5-5` | sin `temperature`; `tool_choice` `auto`; `output_config.effort` `low`; `max_tokens` 16.384 | 2 |

Reglas del pedido, como en P6: si corta, un reintento a 40.960 con transmisión; respuesta sin llamada a la herramienta o mal formada, un
solo reintento igual en un namespace aparte; cada corte, reintento y rechazo se registra; lo que se compara es «modelo más pedido». E3 no corre
en esta unidad (ajuste a la firma): U-DIAG-E3-LISTAS mostró que el verificador no recibe el bloque que abre la lista y reclama en falso
sobre los ítems; Haiku se compara también sin él, en su intento 0. La verificación de tramos es por código (M2 y M4).

MEDICIONES, por brazo y por corrida, sobre las mismas fichas de T4:
M1. Los 137 supuestos del grupo c, clasificados con las cinco clases de T4 (Condicion con su relación hacia la norma; dentro de una
    norma; fusionado; omitido; sin relación), por el mismo lector y con el mismo criterio con que se clasificaron las salidas de Haiku.
M2. Las 46 omisiones normativas de T4 (y las 14 no normativas, aparte), en cuatro clases: extraída como contenido tipificado con tramo
    verificado por código (`pyd_r2/code/validador_r2.verificar_tramo_entidad`: contra el texto propio y el heredado, con la regla del
    tramo de dos segmentos en los ítems; nivel «exacta» o «tokens»); extraída con tramo no verificable (nivel «no»); registrada otra vez
    como omisión (con su categoría); ausente.
M3. Variación entre las dos corridas de cada brazo: unidades iguales byte a byte con la misma clave; cortes, respuestas sin
    herramienta y rechazos.
M4. Por brazo y corrida: elementos con tramo no verificable por código (nivel «no», sobre todo lo emitido), elementos fuera del esquema
    o del tool schema, y costo real por unidad y por brazo, con tokens de entrada y salida.

LECTURA. Fichas por unidad, brazo y corrida con un código y sin el nombre del brazo (decisión 2 al firmar: cegada con códigos; se
declara qué puede descubrir el brazo, por ejemplo el estilo o el largo). Las 8 relecturas del intento 0 de Haiku van con código entre
las demás. Primera lectura de la instancia; segunda lectura completa de la mesa; adjudicación de la autora
sobre las divergencias, como en T4. Ninguna lectura usa la API.

CRITERIO, ESCRITO ANTES DE CORRER (sellado en C0 con su sha256 y su hora; no se cambia después de la primera llamada paga). Un brazo
«cambia el cuadro» si, en la peor de sus dos corridas, cumple al menos una:
C1. Condicion con su relación en al menos 113 de los 137 supuestos (límite inferior de Wilson al 95 % ≥ 0,75; Haiku: 43).
C2. Al menos 41 de las 46 omisiones normativas extraídas como contenido tipificado con tramo verificado por código (límite inferior
    ≥ 0,75; Haiku: 0 por definición, porque en su intento 0 están registradas como omisión).
Si un brazo lo cumple: la autora abre la decisión de una release nueva, con lo que implica (el modelo entra en la clave de caché y en el
pedido: toda la tanda 0 se re-extrae; la reproducibilidad declarada cambia, porque el pedido adaptado no fija temperatura ni fuerza la
herramienta; costo del escalado multiplicado por 2,6 con S o 5,2 con O; enmienda a la decisión del 05/10/2026 y al laudo de release r2).
Si ninguno lo cumple: las dos fallas se declaran límite del diseño en `docs/insumos_escritura.md` §7, con las cifras de los tres modelos,
y B6.4 queda hecho en su parte esencial. M3 y M4 son descriptivos: no entran al criterio.

QUIÉN LO EJECUTA Y CÓMO CONVIVE. Una instancia nueva, en su propia sesión; ni la de S0-2 de U-SEG-OFICIAL ni la de SC1 de U-SINCOLA-T0.
Es la única de las tres que usa la API: necesita la clave en el entorno (no se lee ni se imprime; las otras dos la tienen prohibida).
Escribe solo en `data/experiment/comp_e1/` (código, bases de caché propias, salidas, fichas, frenos) y en su scratchpad. Lee la E0 r2b
(`salida_tanda0_r2b/`, archivos), el perfil y el prefijo (`e1_extractor/`, `prompt_r2/p3c`), las fichas y tasas de T4 (`reext_t0/t4/`),
el validador r2 (`pyd_r2/code`) y los generados del catálogo; nunca las bases del pipeline (`salida_r2b/`, solo para leer las claves de Haiku en
C0, en modo solo lectura). No toca `e0_chunking/` (S0-2), `corpus_tanda0/ens_*`, `manifiestos/`, la fixture ni `grafos.py` (SC1 y SC2).
`git status --short` completo al inicio: lo ajeno se lista y no se toca. Copia sin enlaces para toda corrida; `PYTHONDONTWRITEBYTECODE=1`;
2.213 `.pyc` al inicio, declarados si difieren.

COSTO. Estimación con la tarifa observada en U-REEXT-T0 (E1 Haiku 0,010135 por unidad; `0a3ac81`), el factor de tamaño de las 87
unidades respecto de la media de la tanda 0 (1,78: 2.069 contra 1.165 caracteres completos; son listas largas), los precios por token
de la página de cada modelo (Sonnet 5.5 el doble de Haiku 4.5; Opus 5.5 el cuádruple) y un 30 % más de tokens por el tokenizador
nuevo: cada corrida de E1 cuesta ≈ USD 4,08 en S y ≈ 8,16 en O; sin E3 (ajuste a la firma), las cuatro corridas ≈ USD 24,5 y con un
15 % de margen por cortes y reintentos ≈ 28,2. **Tope: USD 35** (decisión 3), con freno duro antes de cada llamada (presupuesto propio
en `data/experiment/comp_e1/presupuesto.json`). Si el control previo (C0) estima más que el tope con el conteo real de tokens, se
frena sin gastar y se propone el recorte antes de seguir.

ETAPAS.
C0. Control previo, USD 0: (a) las claves de E1 de las 87 unidades con el perfil r2b son las de las bases de `salida_r2b/` (lectura
    `mode=ro`), y el intento 0 de las 87 está en `extracciones_e1.jsonl` (sha256 de la lista; las 8 con reintento identificadas); (b) los dos modelos están disponibles para la cuenta, y el conteo de tokens con el pedido adaptado de cada brazo da la
    estimación de costo recomputada (≤ 25 o freno); (c) sellos con sha256 y hora, antes de la primera llamada: la lista de unidades, las
    fichas de T4 que se usan de base, el texto del criterio y el de las reglas de lectura. FRENO C0 (corto; la autora da el «seguí»).
C1. E1 de S y de O, dos corridas cada uno, en serie, con el freno duro del presupuesto; sin E3. Registro de cortes, reintentos
    y rechazos. Si el presupuesto llega al tope, parada ordenada y freno con lo que haya.
C2. Fichas de M1 y M2 (instancia), más las 8 fichas del intento 0 de Haiku; M3 y M4 por script. FRENO C2: segunda lectura de la mesa
    y adjudicación de la autora.
C3. Cifras finales con la adjudicación, criterio aplicado tal cual, tabla por brazo y corrida, costo real. FRENO final.

CRITERIOS DE ACEPTACIÓN. Sellos de C0 anteriores a la primera llamada paga; gasto real ≤ 35 con su desglose; las cuatro corridas con su
base y su registro; M1 sobre los 137 supuestos y M2 sobre las 60 omisiones en cada corrida; divergencias de lectura adjudicadas; el criterio
aplicado sin cambios; doble corrida de los scripts de cifras byte a byte; el repo sin cambios fuera de `comp_e1/` (sha256 antes y
después); grep de convenciones.
ESCRITURAS: `data/experiment/comp_e1/` (se crea) y el scratchpad. Paquetes `revision_UCOMP_E1_FRENO_C0/`, `_C2/`, `_C3/` con `manifest.txt`.
PROHIBIDO: tocar el código del pipeline, el prefijo, el mensaje, el tool schema, el perfil, el verificador, las bases del pipeline, los
grafos, la fixture, `grafos.py`, EV2; usar los brazos en cualquier corrida del pipeline; leer o imprimir la clave de la API; commitear.
REQUISITOS: CLAUDE.md §4 (a a l).
DECISIONES TOMADAS AL FIRMAR (06/10/2026; en la cabecera): (1) U-COMP-E1; (2) lectura cegada con códigos; (3) tope USD 35 con doble
corrida en los dos brazos.

NOTAS POSTERIORES A LA FIRMA. El texto firmado son las 116 líneas de arriba (`cbcb823`, sha256 `89ce5508c574c4bc…`) y no cambia.

- **06/10/2026 — las 8 relecturas del intento 0 de Haiku pasan por el mismo proceso que T4 (precisión de la autora).** En las 8
  unidades con reintento (5 `aceptado_tras_reintento`, 3 `cola_humana`), el intento 0 de Haiku se lee con el proceso completo de T4 y
  no solo por la mesa: primera lectura de la instancia con las mismas fichas y clases de M1 y M2, segunda lectura completa de la mesa y
  adjudicación de la autora sobre las divergencias, con código entre las demás fichas (lectura cegada). Se hace en C2, junto con las
  fichas de los brazos, para que la línea de base del intento 0 sea igual de sólida que la de T4 en las otras 79. Donde el texto firmado
  dice «la mesa relee», se lee así.
- **06/10/2026 — revisión del FRENO C0 y decisiones de la autora (C0 sin commit al escribir esta nota).**
  - La revisión independiente reprodujo (a) y (c) sobre una copia sin enlaces: las 87 unidades (por TO igual al mandato), las claves de
    E1 en la base 87 de 87 (`claves_c0.json` byte a byte igual), el intento 0 igual al jsonl (`intento0_haiku.jsonl` igual), 78 iguales a
    la extracción final (8 con reintento y `cap::3.1.1.5` difieren; 6 solo en `marcas_e3`), y los sellos: los 25 sha256 de
    `sellos_c0.json` iguales a los del FRENO (cambian solo la hora y el HEAD), el mandato `82fac65…` igual a las 116 líneas firmadas más
    esta sección de notas, y el control cruzado de las fichas de T4 5 de 5. Los archivos del repo que C0 lee, iguales antes y después;
    2.213 `.pyc`.
  - **El tope es USD 35.** C0 (b) del texto firmado dice «≤ 25 o freno» (:99), escrito antes de la decisión 3 al firmar; manda la cabecera
    (tope USD 35 con doble corrida). La estimación de C0 (A 18,18 y B 22,72; con 15 % de margen 20,91 y 26,13) queda bajo el tope: C1
    sigue. El freno duro del presupuesto (`presupuesto.json`) se crea con 35.
  - **Pensamiento en los brazos.** Lo que fija el mandato (tabla de BRAZOS): S con `thinking` `between_tools` y O con
    `output_config.effort` `low`, sin `temperature` y con `tool_choice` `auto`; lo controla el pedido adaptado (`c0/c0b_api.py`,
    `pedido_adaptado`). Lo que impone la API (referencia de la API de Claude vigente, consultada el 06/10/2026): en `claude-sonnet-5-5` el
    pensamiento está activo por defecto, `disabled` devuelve 400 y `between_tools` es la forma de apagarlo (solo con `effort` alto o
    menor, sin otro campo); en `claude-opus-5-5` el pensamiento no se puede apagar (400 con cualquier `effort`) y `effort` es el único
    control, con `low` como mínimo; en los dos, `tool_choice` forzado devuelve 400 y `temperature` no se admite (Opus) o solo en su valor
    por defecto (Sonnet). Por eso el pedido adaptado es el único que la API acepta: **S corre sin pensamiento, como Haiku (`think=0`); O
    corre con el pensamiento mínimo posible.** No existe la opción «todos sin pensamiento». Decisión: se corre como fija el mandato y se
    declara: la comparación es de «modelo más pedido» (:47); el pensamiento de O se cobra como salida (el escenario B lo supone en +50 %,
    sin medir) y C1 lo mide en `usage.output_tokens` de la primera corrida; el texto del pensamiento no vuelve (`display` omitido por
    defecto) y no se guarda nada más que los conteos.
  - **Los dos intentos 0 de Haiku con marca** (`cap::3.1.14.1`, reintento por corte a 16.384; `ctacte::5.1.2.2`, reintento por forma a
    temperatura 1, namespace `-rforma1`). Los brazos pasan por mecanismos de la misma clase (regla del pedido, :46: si corta, un reintento
    a 40.960 con transmisión; si la respuesta no llama a la herramienta o viene mal formada, un solo reintento igual en un namespace
    aparte), pero no idénticos: el reintento por corte de Haiku fue al segundo escalón (16.384) y el de los brazos va a 40.960; el
    reintento por forma de Haiku cambió la temperatura y el de los brazos repite el mismo pedido (la API no admite la temperatura). Se
    declara en las fichas y en M3: las dos unidades llevan la marca «intento 0 de Haiku = reintento (corte / forma)»; cada brazo se compara
    por unidad con su salida persistida después de su propia regla; los cortes, reintentos y rechazos se cuentan por brazo (M3).
  - C1 se despacha con el «seguí» de la mesa, con el gasto estimado y el tope.
- **07/10/2026 — revisión del FRENO C1 por la mesa (C1 sin commit al escribir esta nota; C0 en `25480b9`).** Reproducido sobre una copia sin
  enlaces, sin API: 4 × 87 registros con 87 ids iguales al conjunto sellado (`unidades.json`, `b607d1f6…`); 0 errores, 0 cortes, 0 sin
  herramienta, 0 mal formadas, 0 refusals, 0 reintentos (`stop_reason = tool_use` en 348 de 348). Gasto recomputado desde
  `cache_usage_c1.jsonl` con los precios de `comun_c1.py:34-35`: 2,915682 / 2,904940 / 5,110691 / 4,905310 = **15,836623** de 35, igual a
  `presupuesto.json`. Pedidos iguales a C0: el sha canónico del request recomputado desde el perfil r2b y los chunks, 87 de 87 en cada brazo
  (sobre el cuerpo completo: modelo, `max_tokens`, system, mensajes, tools, `tool_choice`, `thinking`/`output_config`; sin `temperature`).
  M3 recomputado: S 1 de 87, O 4 de 87. M4: `medir_c1.py` dos veces, byte a byte con el repo. Las cuatro bases SQLite (8,1 MB cada una) traen
  el request completo y la respuesta cruda de cada llamada (87 filas por base), sin claves ni rutas absolutas (grep de `sk-ant`, `api_key`,
  `/Users/`: 0): entran al commit (32,5 MB). Selftest 21/21 sin camino a la API. Los 11 sellos de C0 intactos; 2.213 `.pyc`.
  - **Variabilidad entre corridas** (`trabajo51/out_c1/variabilidad_c1.json`, scratchpad de la mesa; corregido el 08/10/2026, decía `out/`): además de las unidades idénticas (S 1, O 4),
    por unidad la diferencia de relaciones entre las dos corridas es 0 en 39 (S) y 47 (O) de 87, de 1 a 2 en 24 y 21, de 3 a 5 en 17 y 12,
    y más de 5 en 7 y 7; la de entidades es 0 en 54 y 52. Consecuencia para la lectura: el criterio «en la peor de sus dos corridas» es
    conservador por diseño (las dos corridas tienen que pasar); con esta dispersión, C3 reporta las cifras de cada corrida y su diferencia,
    y la tesis dice que el veredicto se apoya en la peor de dos, no en un promedio.
  - **Refusals** (precisión a la declaración 1 del freno; sin efecto en C1): con el SDK instalado (`anthropic` 0.100.0,
    `RefusalStopDetails.category` admite solo `cyber` y `bio`), un refusal con otra categoría en el camino base se registra bien
    (`error = "refusal"`, M3 lo cuenta en refusals); en los caminos que revalidan estricto (hit de caché, `llm_cache.py:211`; transmisión,
    `cliente_e1.py:110`) da `ValidationError`, y `correr_c1.llamar` (`:50-53`) lo registra como `api_error` con `stop_reason` nulo: M3 lo
    cuenta como error de API, no como refusal, y en transmisión la llamada no se persiste ni entra al presupuesto. Ninguna unidad puede quedar
    como salida válida vacía ni como corte: a lo sumo cambia la etiqueta. En C2 y C3 no hay API.
  - Commit de C1 PENDIENTE de la autora; el «seguí» de C2 está preparado por la mesa.
- **07/10/2026 — C1 commiteada en `6e16bb3`; C2 despachada con el «seguí» de la mesa** (fichas cegadas con códigos sellados; M1 y
  M2 por corrida; las 8 relecturas del intento 0 con código). Sigue el FRENO C2: segunda lectura de la mesa y adjudicación de la
  autora sobre las divergencias.
- **07/10/2026 — revisión del FRENO C2 por la mesa (C2 sin commit al escribir esta nota; C1 en `6e16bb3`).** Reproducido sobre una copia sin
  enlaces, sin API: cobertura M1 559 = 137 × 4 + 11 y M2 245 = 60 × 4 + 5 desde `lectura_c2.jsonl` (804 líneas; 0 duplicadas, 0 fuera de las
  bases de T4; 356 fichas); el archivo cerrado de códigos sigue con su sha (`065a272c…`), `fichas_c2.py:136-139` lo verifica y lo carga solo en
  memoria, ningún script lo imprime y no hay fugas de nombres de brazo en `salida/` ni en `material/`; el resumen por código coincide cifra por
  cifra con el freno (sumas 137/46/14 por código); doble corrida byte a byte; los 11 sellos de C0 intactos. La corrección del renderizado
  anterior a toda clasificación: el material no tiene ningún `None` y sus 356 bloques son idénticos a la extracción de las fichas, y la hora
  de `comun_c2.py` coincide con el sello reescrito (11:07:40 UTC); el orden temporal contra la lectura queda NO VERIFICADO (la lectura no lleva
  hora). Precisiones al freno: el cambio del mandato durante C2 fue `604640c` (08:24), no `334bdd1`; los tres subtipos de `sin_relacion`
  están en `tasas_t4.json`, no en `reglas_lectura_c0.md`.
  - **Reglas de lectura declaradas por la instancia, para la adjudicación de la autora:** (1) una Condicion con `condicion_de` hacia una
    Operacion cuenta como relación (como en T4); una Excepcion con relación cuenta solo si es cláusula de excepción (`ext::14.5.7`, código K,
    anotado «a adjudicar»); (2) un supuesto extraído como Restriccion, Obligacion o Definicion sin Condicion es `dentro_de_norma`; (3) en M2,
    «extraída» exige que el tramo verificado de una entidad cubra el tramo omitido, y lo que está solo en la descripción cuenta como ausente
    (12 casos, verificados uno por uno; 99 de 99 extraídas con tramo `[exacta]` o `[tokens]`); (4) precedencia de la entidad sobre la omisión
    para el código N (5 anclas). Decide la autora si las cuatro rigen también para la segunda lectura.
  - **Cifra complementaria, declarada posterior al resultado:** de las 46 omisiones normativas de T4, 20 tienen su oración en el texto
    heredado (campo `en` de T4) y 26 en el propio. Extraídas con tramo verificado sobre las 26 del propio: A 16, H 17 (más 2 no verificables),
    K 16, W 15; sobre las 20 del heredado: A 4, H 5 (más 2), K 3 (más 1), W 5; ausentes en el heredado 15 / 13 / 16 / 15. En M1, T4 marca solo
    4 de los 137 supuestos con la norma en el heredado (0 con relación en los cuatro códigos): la cifra por texto propio/heredado no se
    puede separar con lo que T4 guardó, y se declara. La cifra del criterio sellado no cambia (`complementario_heredado_c2.json`, scratchpad).
  - **Camino crítico:** ningún código llega al criterio en la primera lectura (máximos 96 de 137 en M1 y 22 de 46 en M2, contra 113 y 41;
    con cuatro corridas, el criterio exige la peor de las dos de cada brazo); la decisión de no cambiar de modelo antes de la tanda 1 no
    depende de la segunda lectura, que puede mover decenas de clasificaciones pero no 17 en M1 ni 19 en M2 en un mismo código. C2 sale del
    camino crítico: la segunda lectura a ciegas de la mesa (despacho preparado; material de 87 unidades, 1,5 millones de caracteres) corre
    después del 08/10/2026 y la autora adjudica las divergencias (estimación: 40 a 80).
  - Commit de C2 PENDIENTE de la autora.
- **07/10/2026 — C2 commiteada en `4e9a1fc`; decisión de la autora sobre las reglas de lectura.** Las cuatro reglas declaradas por la
  instancia en C2 (nota anterior: la Condicion con `condicion_de` hacia una Operacion cuenta como relación; la Excepcion con relación cuenta
  solo si es cláusula de excepción; un supuesto extraído como Restriccion, Obligacion o Definicion sin Condicion es `dentro_de_norma`; en M2,
  «extraída» exige que el tramo verificado de una entidad cubra el tramo omitido, y lo que está solo en la descripción cuenta como ausente; la
  precedencia de la entidad sobre la omisión para el código N) **rigen también para la segunda lectura a ciegas de la mesa**. La sesión de la
  segunda lectura se despachó antes de esta nota; la autora le comunicó las cuatro reglas por escrito al despacharla, antes de que estuvieran
  en el mandato. Control de la revisión de esa lectura: su reporte tiene que declarar desde cuándo aplicó las reglas (hora) y, si clasificó
  algo antes de recibirlas, re-clasificar esos ítems con las reglas y contarlos aparte.
- **07/10/2026 (noche) — revisión de la mesa de la segunda lectura a ciegas de C2, y su entrada al repo.**
  - **Dónde quedó.** El paquete de la instancia entró a `data/experiment/comp_e1/c2/segunda_lectura/`: 37 archivos, iguales por sha al
    paquete. Quedaron afuera las dos listas de `.pyc` de los controles, de 1 MB cada una, con rutas absolutas.
  - **Se reproduce**, sobre una copia y sin escribir en el repo:
    - **El sello antes de la apertura:** `segunda_lectura_c2.jsonl` tiene sha256 `04406c97…`, rearmado byte a byte desde las fuentes. En
      la transcripción de la sesión, el sello es de las 20:19:30 y la primera apertura de `lectura_c2.jsonl`, de las 20:19:39.
    - **La tabla de códigos cerrada:** `065a272c…` igual en `4e9a1fc`, en HEAD y en el paquete; la sesión de la lectura no leyó su
      contenido.
    - **La cobertura:** 804 = 559 + 245, sin faltantes ni duplicados.
    - **El acuerdo:** 549 de 559 en M1 y 243 de 245 en M2; kappa 0,967 (5 clases) y 0,986 (4 clases).
    - **Las 19 divergencias:** 12 de clase y 7 solo de subtipo.
    - **Las cinco correcciones propias** son anteriores al sello; con las clases iniciales habría 18 divergencias.
  - **Precisiones.**
    1. **La contaminación declarada estaba incompleta.** Antes de leer, la sesión vio también «99 de 99» y «4 de 137 … 0 con relación en
       los cuatro códigos». Esta última apunta a 16 líneas, y en ellas quedaron 12 de las 19 divergencias: no empujó hacia el acuerdo.
    2. **Las reglas de lectura llegaron a las 17:56:44,** unos seis minutos después del despacho y en otro mensaje. La nota anterior dice
       «al despacharse».
    3. **Las 29 líneas marcadas por tramo cortado:** 28 lo tienen y una no; `lingob::7.1.7` W quedó sin marcar.
  - **Error del verificador de la mesa (declarado).** Abrió el archivo cerrado de códigos, así que conoce la tabla de qué código
    corresponde a qué corrida. Ninguna de sus salidas la contiene, y la hoja de adjudicación de las 19 va solo por código. La autora decide
    si acepta esa hoja o pide que la prepare otra instancia.
  - **Hoja de adjudicación** (paquete de la mesa, `hoja_adjudicacion_19_divergencias_C2_mesa.md`): las 19 divergencias se resuelven con
    8 decisiones (a a h). Solo las filas 11 a 15 pueden mover la cifra del criterio. Con cualquier adjudicación, ningún código llega al
    criterio: los máximos son 96 de 137 en M1 y 22 de 46 en M2, contra 113 y 41.
  - **Para C3:** la adjudicación de la autora; después, abrir la tabla de códigos, aplicar el criterio tal cual, la tabla por brazo y
    corrida, el costo real y el FRENO final.
  - **Contradicción del texto firmado.** El `:76` manda declarar el límite en `docs/insumos_escritura.md` §7, y las ESCRITURAS (`:111`)
    no incluyen ese archivo. Decisión de la autora, PENDIENTE. Recomendación de la mesa: que la unidad deje el texto del ítem en su FRENO
    C3 y que la mesa lo asiente en insumos §7, para que la unidad no escriba fuera de sus escrituras firmadas.
- **07/10/2026 (noche, más tarde) — decisiones de la autora sobre la adjudicación de C2 y sobre C3.**
  1. **La hoja de adjudicación** es la que armó la instancia de la segunda lectura: `c2/segunda_lectura/adjudicacion_c2_worksheet.md`
     y `.json`, sha256 `32a0c7d8…` y `d6cb9af0…`. La mesa confirmó que es idéntica byte a byte en el paquete de la instancia, en
     `be8d6f2` y en el árbol.
  2. **La adjudicación de las 19 la hace la autora**, sin pasar por la sesión de la mesa, porque esa sesión ya conoce la tabla de códigos.
     La hoja que preparó la mesa no se usa.
  3. **El límite de C3** (`:76`) lo asienta la mesa en `docs/insumos_escritura.md`, §7, desde el FRENO C3 de la unidad. La unidad no
     escribe fuera de sus escrituras firmadas (`:111`). Con esto queda resuelta la contradicción de la nota anterior.
- **07/10/2026 (noche) — adjudicación de la autora de las 19 divergencias de C2**, hecha sobre `c2/segunda_lectura/adjudicacion_c2_worksheet.md`
  sin conocer la tabla de códigos.
  - **Regla de adjudicación, declarada y aplicada pareja:**
    1. Primero la relación: si el supuesto está en una Condicion conectada a su norma, o a la Operacion por la regla 1, cuenta como
       `condicion_con_relacion` aunque su etiqueta arrastre parte de la norma o su consecuencia; una Excepcion cuenta como con relación
       solo si es cláusula de excepción (regla 2).
    2. Sin relación: `fusionado` si el supuesto comparte nodo con otros supuestos o con su norma; `dentro_de_norma` si quedó dentro de un
       nodo de norma; `sin_relacion`, con su subtipo, si tiene nodo propio sin conexión.
    3. La norma de cada supuesto es la que define la ficha de T4.
  - **Veredictos:**
    - 1, 3, 4, 5, 6, 7 y 8: `sin_relacion` (`norma_en_heredado`);
    - 2, 9, 10, 16, 17, 18 y 19: `fusionado`;
    - 11 y 13: `condicion_con_relacion`;
    - 12: `dentro_de_norma`;
    - 14 y 15 (M2): `ausente`, con la nota «cobertura parcial 0,58; falta el calificador de proporcionalidad».
  - **Asentado por la mesa:**
    - en la hoja (`.md` y `.json`, con la regla);
    - en la lectura adjudicada `data/experiment/comp_e1/c2/lectura_c2_adjudicada.jsonl`: la primera lectura (`lectura_c2.jsonl`, sin
      cambios) con los 19 veredictos y, en cada uno, la primera lectura, la segunda y el veredicto, en el campo `adjudicacion`.
  - **Contra la primera lectura**, 14 de las 19 cambian:
    - 7 solo de subtipo (de `norma_presente` a `norma_en_heredado`);
    - 4 de `sin_relacion` a `fusionado`;
    - 2 de `extraida_tramo_verificado` a `ausente`;
    - 1 de `condicion_con_relacion` a `dentro_de_norma`.
    - Las otras 5 ratifican la primera lectura.
  - C2 queda adjudicada. C3 se despacha con la lectura adjudicada.
- **08/10/2026 — FRENO C3 (final) revisado por la mesa sobre una copia; decisiones de la autora; U-COMP-E1 CERRADA con el commit de C3.**
  - **Se reproduce todo** (copia sin enlaces; repo sin cambios fuera de `docs/`, 2.213 `.pyc`; la tabla de códigos se abrió en esta sesión
    después de la adjudicación, `cf7d7c5`):
    - el paquete de la instancia (17 sha256) y los 11 sellos de C0; `criterio_c0.md` igual a `:68-78` del texto firmado;
    - `cifras_c3.py` dos veces: `control_previo_c3.json` igual byte a byte; las otras cuatro salidas, iguales salvo la hora (el «byte a
      byte» del freno se dio porque sus dos corridas cayeron en el mismo segundo);
    - con un script propio: la lectura adjudicada es la primera con 19 líneas distintas, las que llevan `adjudicacion`, y 785 iguales; 14
      cambian y 5 ratifican; la tabla `065a272c…` da A = S1, H = S2, K = O2, W = O1, N = H0; M1 y M2 por corrida, la peor corrida (S 60 y 20,
      O 91 y 18 contra 113 y 41), los Wilson y la cifra del texto propio (16, 17, 15 y 16 de 26; 4, 5, 4 y 2 de 20 en el heredado).
  - **Precisiones de la mesa** (ninguna cambia el veredicto):
    1. Que el control previo vaya antes de la apertura sale del orden del código (`c3/cifras_c3.py:163-168`), no de una marca de tiempo:
       `control_previo_c3.json` no lleva hora.
    2. La referencia de Haiku de la tabla del freno (43 / 76 / 7 / 3 / 8) sale de `tasas_t4.json`, anterior a la adjudicación de
       `ext::4.1.3.2` (`c9d4c40`). La adjudicada es 43 / 77 / 7 / 2 / 8, la de `docs/insumos_escritura.md` §7, ítem 2, y la de `:15`.
    3. La línea de base del intento 0 de Haiku, la que fija el texto firmado (T4 en 79 unidades y la relectura con código en las 8 con
       reintento), es 40 de 137 en M1 y **3 de 46 en M2**: en el intento 0, 3 de las 4 omisiones normativas de esas 8 unidades salieron
       extraídas con tramo verificado. «Haiku: 0 por definición» (`:72`) vale para la extracción final, no para el intento 0.
    4. La lectura no es simétrica: Sonnet y Opus, con la lectura doble cegada y la adjudicación; Haiku, con la lectura de T4.
  - **El límite**, asentado por la mesa en `docs/insumos_escritura.md` §7, ítem 7, con el texto del freno y cinco correcciones:
    1. el título decía «límite del diseño, no del modelo»; dice «límite del diseño: ningún modelo las lleva al criterio», porque Opus más
       que duplica M1 (91 y 95 contra 43);
    2. Haiku con sus dos líneas de base: 43 y 0 en la extracción final, 40 y 3 en el intento 0;
    3. de dónde sale cada cifra: la lectura doble cegada para Sonnet y Opus, la de T4 para Haiku;
    4. «15 a 17 ausentes» dice «13 a 17» (S2 tiene 13);
    5. «los tres modelos quedan en el mismo tercio (18 a 22 de 46)» dice «los dos modelos nuevos quedan entre 18 y 22 de 46 (39 % a
       48 %)»: Haiku tiene 0, y 18 a 22 de 46 no es un tercio.
  - **Decisiones de la autora (08/10/2026):**
    1. El modelo del extractor no cambia antes de la tanda 1.
    2. La comparación de modelos se reporta como experimento del capítulo 5 (Evaluaciones). Lo necesario para escribirla, con sus anclas,
       está en `docs/insumos_escritura.md` §8, con la propuesta de la mesa de dónde va y qué tabla la resume; en el plan, la fila B6.4.
    3. Opus queda como candidato para la release del grafo corregido, sin abrir hoy la decisión. La relación con D15: U-COMP-E1 antes de
       la tanda 1 y B6.4 después del escalado; B6.4 queda hecho en su parte esencial (`:76`).
    4. El cambio de modelo es una de las palancas del punto de diagnóstico posterior a A2.2 (plan, fila A2.2).
  - **Gasto de la unidad:** USD 15,836623 de 35 (`presupuesto.json`), todo en C1.
  - **U-COMP-E1 CERRADA** con el commit de C3 (PENDIENTE de la autora).
- **08/10/2026 (tarde) — etapa C4 en BORRADOR** (decisión de la autora): una lectura pareada a ciegas, USD 0, sobre las salidas guardadas,
  de una muestra de las 87 unidades con la extracción de Haiku, de Sonnet y de Opus de cada una, recodificadas; unidades con algún error
  con el criterio de U-LECTURA-ACEPTADAS y precisión de las relaciones. Mide lo que C1 a C3 no midieron. No cambia la decisión de la
  tanda 1. Documento aparte: `docs/mandatos/UCOMP_E1_C4_lectura_pareada.md`. Corre en paralelo con el escalado, lista antes del punto de
  diagnóstico posterior a A2.2; sus resultados van a la sección de la comparación de modelos del capítulo 5.
- **08/10/2026 (tarde) — C4 FIRMADA** (`docs/mandatos/UCOMP_E1_C4_lectura_pareada.md`), con la corrida 1 de Sonnet y de Opus, 30 unidades
  y dos sesiones distintas para preparar y para la primera lectura, con la mesa en segunda lectura.
