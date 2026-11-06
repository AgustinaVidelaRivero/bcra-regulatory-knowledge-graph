# Protocolo entre tandas para el escalado

FIRMADO por la autora el 03/10/2026. Redactado el 03/10/2026 sobre HEAD `e91f864` (borrador commiteado en
`9eabab0`; las decisiones de la autora, D1 a D9 del §10, aplicadas el 03/10/2026) sin costo de API. Unidad de planificación: no cambia código, esquema ni pre-registros. Toda cifra lleva
su fuente; lo que no está en una fuente dice NO ENCONTRADO.

## 0. Qué hay hoy y qué falta

**Procedimiento general existente.** El plan tiene una regla de tres oraciones, no un procedimiento:
«Regla del escalado por etapas (30/09/2026). Cada tanda prueba sobre documentos nuevos lo corregido
en la anterior. Entre tandas se admiten correcciones en código, como releases del pipeline
declaradas antes de sellar el pre-registro de B6.3. Los cambios de esquema, prefijo o formato de
salida de E1 posteriores al ciclo B2.11 van a la versión posterior a la evaluación»
(`docs/plan_tesis.md:741`; fuente: `data/experiment/esq/enmienda_uso_ventana_2026-09-30.md`, §2.7
y §3.3, firmada en `30f106c`). Lo demás está repartido:
- composición: B6.1 «20 TOs digeribles (normativa general prioritaria)» (`docs/plan_tesis.md:765`) y
  B6.2 «resto de digeribles (48)» más «EN PRINCIPIO los TOs no-RI que B5.8 reconozca» (`:771`;
  re-laudo del 06/09, `:734`); el bloque RI no tiene fila de tanda (`:1053` lo deja fuera de las
  tandas 1 y 2); la partición final es 138 reconocidos plenos + 2 parciales + 12 no segmentables
  (`:738`);
- gate por release: laudo de r2, §3.1, puntos 1 a 8 (`docs/laudo_release_r2_pipeline.md:243-283`);
- condiciones de la tanda 1: `docs/checklist_pre_escalado.md:52-77` (cuatro condiciones) y la
  operación del escalado (`:80-101`, P9 a P19);
- lo que se mide en cada tanda: vigilancias (1) a (9) y observaciones (10) a (12), con muestreo a
  fijar en el mandato de la tanda (`docs/plan_tesis.md:765-770`; checklist P10 y P14);
- qué obliga a reprocesar: `data/experiment/mantenimiento/tabla_reprocesamiento.md` (21 filas, cuatro
  clases, §2 y §3);
- el tablero, con una columna por tanda (`docs/tablero_correcciones.md:47`).

**Qué falta** respecto de los puntos 1 a 9: la lista única de lo que se mide al cerrar cada tanda
(1); la clasificación de hallazgos que junte la tabla de reprocesamiento con la enmienda de uso de
la ventana (2); cuándo se re-aplica una corrección de código a las tandas anteriores (3); el formato
de las condiciones para las tandas 2 en adelante y el sellado del grafo de cada tanda (4); la
composición hasta los 152, con el bloque RI (5); el procedimiento para un cambio de prompt o de
esquema durante el escalado (6); el criterio de diversidad de la tanda 1 (7); el criterio de revisión
del prompt (8) y las válvulas de escape (9). Este borrador cubre esos nueve puntos.

## 1. Qué se mide al cerrar cada tanda

Sobre el grafo de la tanda (sus TOs solos) y sobre el grafo acumulado (todos los TOs extraídos hasta
esa tanda, con el mismo código), en este orden y con salida versionada en el directorio de la tanda:

1. **Suite y shapes del perfil vigente, contra la fixture.** Suite: `scripts/regression_kg.py
   --perfil r2 --esperado scripts/regression_kg_esperado.json` (los perfiles existentes, sin
   `--perfil`); criterio: 0 regresiones contra la entrada sellada del grafo anterior (laudo de r2,
   §3.1, punto 2). Shapes: `scripts/shapes_validator.py --perfil r2 --fase <r2a|r2b> --e0 <E0 de la
   tanda>`; bloqueantes en PASS, con los FAIL conocidos declarados (hoy S18 por los límites relativos,
   nota del 02/10/2026 a L-ESQ-R2 §1.5). El `--out` va a una ruta versionada y fechada de la tanda
   (`docs/plan_tesis.md:766`). Se suman los puntos 3 a 7 del gate de r2 (contadores de E1, intrínsecas
   de generación 3 en modo informativo, indicadores de cita, reproducibilidad de los sellados, nunca
   EV2; `docs/laudo_release_r2_pipeline.md:264-277`).
2. **La columna nueva del tablero de correcciones**, con el comando de cada fila ([c1] a [c24] y los
   que sume la unidad 9) sobre el grafo de la tanda y el acumulado; cada celda con cifra o con su causa
   de no medición (`docs/tablero_correcciones.md:47`, columna «Tanda 1»; para las siguientes se agrega
   una columna por tanda). Las vigilancias (1) a (9) y las observaciones (10) a (12) se miden contra
   sus líneas de base, sin umbral; el único criterio de retiro es el principio de gobierno del §1
   (`docs/preregistro_tanda0.md:832-862`, decisión 6; `docs/plan_tesis.md:765-770`).
3. **Lecturas asistidas por muestra**, con la regla de lectura fijada antes de leer y rotuladas
   «lectura asistida» con el modelo y la versión declarados (precedente:
   `docs/mandatos/ULECTURA_LIMITA_lectura_asistida.md`, decisiones 1 a 4): la observación (12)
   (30 aristas sorteadas con `scripts/muestra_aristas_obs12.py`, semilla declarada, Wilson al 95 %;
   `docs/enmienda_preregistro_tanda0_2026-09-27_observacion12.md` §2.1 y §2.2), las vigilancias (2) y
   (7), y las lecturas que el mandato de la tanda declare (remisiones, sujetos, omisiones). Quién
   adjudica se define antes de leer (checklist P15 y Q12, decisión pendiente con los mentores).
4. **El costo real contra el estimado**, por etapa y por TO, con la fórmula de caching (decisión 2 de
   `docs/decisiones_caching_extraccion.md`), contra la tarifa de referencia de la tanda 0: E1 USD
   0,007425 y E3 USD 0,009179 por unidad, USD 0,0166 juntas (`tabla_reprocesamiento.md`, §5; laudo de
   r2 §1.3). La desviación se declara y entra al re-presupuesto de la tanda siguiente (B5.7,
   `docs/plan_tesis.md:732`; checklist P9).

## 2. Cómo se clasifica cada hallazgo

Cada hallazgo del cierre (una fila del tablero que no cumple su meta, una incorrecta de la lectura,
una vigilancia fuera de su línea de base) se clasifica en dos ejes, y los dos van al reporte:

**Eje A, qué obliga a reprocesar** (`data/experiment/mantenimiento/tabla_reprocesamiento.md`, §2 y
§3, con la fila F01 a F19 que corresponda):
- **nada**: el grafo guardado sigue valiendo; el hallazgo se declara como residuo;
- **solo código sobre lo guardado** (filas F13 a F16: validador, E2 y ensamblado, remisiones, E4 y
  esqueleto): se re-aplica sobre la salida guardada de E1 y E3, a USD 0 (principio 12,
  `docs/plan_tesis.md:299`);
- **E1 y E3 de las afectadas** (F01 a F05 y F19: texto o marcas de E0, numeración): pagan solo las
  unidades cuyo request cambia, al promedio de la tanda 0;
- **todo** (F06 a F11: prefijo, tool schema, modelo, versión de código, catálogo del prompt): todas
  las unidades pagan E1 y E3; es la clase que la enmienda de la ventana regula.

**Eje B, qué puede corregirse ahora** (`data/experiment/esq/enmienda_uso_ventana_2026-09-30.md`):
- las correcciones de código sobre lo guardado no consumen ventana: siguen el ciclo de releases del
  pipeline, cada una con su laudo, declaradas antes de sellar el pre-registro de B6.3 (§2.7, §3.3);
- la tanda 1 corre sin ventana (§2.1, §3.1; checklist P19 y Q11); si revela una falla de esquema, su
  corrección es release posterior declarada (laudo congelado §7 y línea 202; principio 9,
  `docs/plan_tesis.md:277`);
- un cambio de prompt, de esquema o de formato de salida de E1 posterior al ciclo B2.11 queda fuera
  del grafo que evalúa B6.3 (§3.3): se registra en el backlog con `capa_pipeline` y espera la versión
  posterior a la evaluación.

Regla de cruce: un hallazgo de clase «solo código» o «E1 y E3 de las afectadas» (por E0) se corrige
entre tandas; uno de clase «todo» que exija prefijo, esquema o formato de salida se difiere, salvo el
procedimiento del §6 (c). Las incorrectas van al backlog con `capa_pipeline` (B2.5), como las cinco de
la observación (12) de la tanda 0 (`BKL-0032` a `BKL-0036`; `docs/plan_tesis.md:770`).

## 3. Cómo se aplica una corrección de código a las tandas anteriores

**Mecánica (principio 12).** Se re-ejecutan los pasos en código sobre la salida guardada de E1 y E3
de cada TO: E0 de la versión vigente, lectura del crudo con el validador r2, E2, resolución de sujetos
y registro, umbrales, `remite_a`, E4 y esqueleto, ensamblado (hoy `ensamblar_tanda0.py --perfil-r2
--e0-r2`; con U-PROMPT-R2, el despacho por el perfil del manifiesto). Precondición: el crudo de E1 de
cada unidad, incluido el del reintento de E3 (`e1_reintentos.db`, `tabla_reprocesamiento.md`, nota a
F14), y las dbs de caché resguardadas fuera del repo (laudo de r2 §3.2, punto 6). USD 0; el tiempo es
el del ensamblado (la prueba r2 de los diez TOs corre en minutos: batería de cierre de U-R2-CODIGO,
`data/experiment/r2_codigo/cierre_freno.md`).

**En qué momento.** Dos opciones:
- **(i) En cada tanda.** Cada release de código re-ensambla el grafo acumulado al cerrar la tanda que
  la motivó, y ese grafo acumulado es el que entra a la tanda siguiente. Ventajas: la tanda siguiente
  mide sobre documentos nuevos lo corregido en la anterior (regla del plan, `:741`); un defecto de la
  corrección aparece una tanda antes; el tablero compara columnas homogéneas. Costo: USD 0 por
  corrección; un re-ensamblado por release y un sellado por tanda (sha, suite, shapes, tablero).
- **(ii) Una sola vez antes de B6.3.** Las tandas se extraen con el código vigente al momento y las
  correcciones se acumulan; un único re-ensamblado final produce el grafo que evalúa B6.3. Ventajas:
  menos sellados. Costo: el mismo USD 0, pero cada tanda mide con un pipeline distinto del que se va a
  evaluar, y una corrección que rompe algo se descubre al final, sin tanda que la pruebe.

Decidido (D3, 03/10/2026): la opción (i). El código se re-aplica al grafo acumulado en cada release y el grafo
de cada tanda se sella sin corregirlo (principio 9): la corrección produce una versión posterior,
no edita la sellada.

## 4. Sellado del grafo de cada tanda y condiciones de la siguiente

**Sellado.** Al cerrar la tanda k se sellan por commit: la E0 de sus TOs; `kg.json` de la tanda
sola y del acumulado, con su sha256 y su nombre (`KG-Tanda<k>-<release>`, como KG-Tanda0-Diez-r1
`dd42d6d9…`, `docs/tablero_correcciones.md:35`); los registros del ensamblado; la salida fechada de
suite y shapes; el reporte de la tanda con costo real y la columna del tablero. La entrada de la
fixture de la tanda la sella la autora antes de la tanda siguiente (decisión 9 del mandato de
U-R2-CODIGO; `docs/laudo_release_r2_pipeline.md:253-263`).

**Condiciones de la tanda k+1**, con el formato de la tanda 1 (`docs/checklist_pre_escalado.md:52-77`):

1. La tanda k cerrada: grafo sellado, suite con 0 regresiones contra su entrada sellada, shapes con
   las bloqueantes en PASS o los FAIL declarados, selftests del pipeline en verde (laudo de r2 §3.1,
   puntos 1, 2 y 6).
2. El tablero con la columna de la tanda k completa: cada meta cumplida o con su residuo declarado
   (laudo de r2 §3.1, punto 8; R28).
3. Los hallazgos de la tanda k clasificados (§2) y las correcciones de clase «solo código» aplicadas
   como release declarada, con su laudo, y el grafo acumulado re-ensamblado (§3, opción i). Lo
   diferido, en el backlog con `capa_pipeline`.
4. El costo real de la tanda k contra el estimado, y el re-presupuesto de la tanda k+1 con la tarifa
   observada (B5.7, `:732`; P9), con tope en el mandato de la tanda.
5. La lista de TOs de la tanda k+1 fijada por el criterio del §5 y del §7, con el health-check de E0
   en verde por TO (`docs/plan_tesis.md:734`, condición de entrada por documento) y con su E0 regenerada
   con el código vigente (checklist `:77`).
6. El pre-registro o mandato de la tanda k+1 declara que corre sin ventana (P19) y fija el muestreo de
   las vigilancias, las lecturas y quién adjudica (P10, P15).

La tanda 1 conserva además sus cuatro condiciones propias (checklist `:52-77`): validación del
capítulo (P6), B2.10 y B2.11 cerradas hasta U-REEXT-T0 con el gate de r2 en verde y el criterio de la
remisión del ejemplo (X17), las decisiones X1 a X4 y X11, y el tablero con r2a y r2b completas.

## 5. Qué TOs entran en cada tanda y cuántas tandas hay

**Universo.** 157 textos ordenados: 152 en el inventario del escalado (`inventario_tos.csv`: 99 de
normativa general y 53 regímenes informativos) más los 5 de desarrollo (`inventario_resumen.json`,
`subset_excluido`). Partición final de los 152 (plan `:738`): 138 reconocidos plenos, 2 parciales
declarados (`manual`, `ri2_pm`) y 12 no segmentables declarados (`adjudicaciones_b584.json`,
`e_no_segmentables`: optico, plandecuentas, ri_chr, ri_con, ri_fcem, ri_itme, ri_pfmipyme, ri_pscpp,
ri_pspii, ri_rem, ri_spi, ri_tii). Unidades de E0 de la partición: 9.324 (`conteos_b584.json`;
tablero `:73`). Veredictos del inventario (`inventario_unidades.csv`, campo `veredicto`): 68
digeribles (todos de normativa general, 6.340 unidades) y 84 «necesita reglas» (53 RI y 31 no-RI,
2.984 unidades en la partición).

**Lo hecho.** Tanda 0: 5 digeribles (`ctacte`, `lingob`, `polcre`, `pagjub`, `docvig`, 671
unidades; `docs/preregistro_tanda0.md:130-140`) más los 5 de desarrollo (1.763): 10 TOs, 2.434
unidades, USD 40,35 en E1 y E3 (`tabla_reprocesamiento.md`, §5).

**Lo que queda: 147 TOs**, con las filas del plan tal como están:

| Tanda | TOs | Criterio del plan | Unidades (partición) | E1 y E3 a USD 0,0166 |
|---|--:|---|--:|--:|
| 1 | 20 | digeribles, normativa general prioritaria (`:765`); criterio de diversidad del §7 | depende de la lista; ejemplo del §7: 3.292 | ≈ 54,65 |
| 2 | 43 digeribles + no-RI reconocidos | «resto de digeribles» (`:771`) y los no-RI de B5.8 (`:734`), con health-check por TO y re-presupuesto (`:732`) | digeribles restantes: 63 TOs, 5.669 unidades (USD 94,1) menos los que entren a la tanda 1; no-RI plenos: hasta 31 TOs, 2.008 unidades | a recomputar con la lista |
| 3 | RI plenos | NO ENCONTRADO en el plan: el bloque RI no tiene fila (`:1053`) | 53 RI, 976 unidades, menos los no segmentables y los que entren antes | ≈ 16 |
| fuera | 14 | 12 no segmentables y 2 parciales, declarados (`:738`) | — | — |

Corrección de la aritmética del plan, decidida (D4, 03/10/2026): B6.1 (20) y B6.2 (48) sumaban los 68
digeribles sin descontar los 5 de la tanda 0; quedan 63, así que la tanda 2 tiene 43 digeribles, la tanda
1 sigue en 20 y los regímenes informativos reciben una fila propia en el plan (tanda 3). Total: 20 + (43 + no-RI) + RI = 147 − 14 fuera = 133 TOs plenos a extraer en tres
tandas, con un costo de referencia de E1 y E3 de USD 154,8 para toda la partición (9.324 × 0,0166),
de los que la tanda 0 ya pagó los suyos. El criterio de entrada por documento es el health-check de
E0 en verde y el modo de lectura declarado (`vigente`, `marcadores` o `sin_raiz`;
`conteos_b584.json`, `modo_lectura`).

## 6. Cambios de prompt o de esquema durante el escalado

**Por qué la ventana se cierra después de la tanda 0.** Tres razones, cada una con su fuente:
- **Contaminación del conjunto de evaluación.** Un documento que informó el esquema deja de ser
  virgen y sale del conjunto fresco de B6.3 (a): así salieron los 5 de desarrollo y los 10 de ESQ-2
  (`documentos_excluidos_esq.json`; plan `:772` (a)), y así salieron los 5 de la tanda 0 al usarse la
  ventana (`enmienda_ventana_correccion_2026-09-25.md` §2, precisión 4; `enmienda_uso_ventana_2026-09-30.md`
  §3.2; checklist X3 y Q10). Cada ventana nueva achica el conjunto sobre el que la tesis puede medir.
- **Coherencia del grafo.** Un grafo con documentos extraídos bajo dos prefijos no es una versión
  del pipeline: la evaluación final mide un grafo de una sola release (principio 9, `:277`; laudo
  congelado §7, «sellado ese pre-registro, la ventana muere»). Hacer todas las correcciones de
  prefijo en un solo ciclo antes de escalar evita re-extraer después el corpus escalado
  (`enmienda_uso_ventana_2026-09-30.md` §2.3).
- **Costo.** Un cambio de prefijo o de tool schema es clase «todo»: todas las unidades extraídas
  pagan E1 y E3 de nuevo (`tabla_reprocesamiento.md`, F06 y F07; laudo de r2 §3.2, punto 1). A la
  tarifa de la tanda 0 son USD 0,0166 por unidad: USD 40,4 por los diez TOs de la tanda 0 y USD
  154,8 por la partición completa.

**Opciones, con lo que queda en la evaluación, el costo y lo que gana la tesis.** Conjunto elegible
hoy para B6.3 (a): 157 − 20 excluidos = 137 TOs (si se extraen todos).

- **(a) Mantener la regla tal cual.** Ningún cambio de prefijo, esquema ni formato de salida hasta
  después de B6.3; lo que las tandas revelen de ese tipo va al backlog y a la versión posterior
  (`enmienda_uso_ventana_2026-09-30.md` §3.3). Evaluación: 137 TOs elegibles. Costo de re-extracción:
  USD 0. Gana: una sola release evaluada, el conjunto de evaluación más grande posible y la tesis
  puede describir el residuo del prompt como hallazgo medido sobre documentos nuevos. Pierde: un
  defecto de prompt que aparezca en la tanda 1 se mide y se declara, no se corrige antes de evaluar.
- **(b) Una segunda ventana después de la tanda 1**, con sus 20 TOs fuera de B6.3 (a), como los cinco
  de la tanda 0. Exige una enmienda nueva al laudo congelado §7 (hoy dice «una sola ventana»:
  `enmienda_ventana_correccion_2026-09-25.md` §2, precisión 3) y al pre-registro de la tanda 1 antes de
  correrla. Evaluación: 137 − 20 = 117 TOs elegibles, y menos si los 20 de la tanda 1 se eligen entre los
  ya excluidos (§7). Costo: re-extraer todo lo extraído hasta ahí con el prefijo nuevo: 2.434 unidades
  de la tanda 0 más las de la tanda 1 (3.292 en el ejemplo del §7) ≈ 5.726 × 0,0166 ≈ USD 95, más
  el ciclo de laudo y de prueba pareada (referencia: USD 0,2902 la pareada de B5.4, `d3f2214`). Gana:
  el prefijo que se evalúa vio dos rondas de documentos nuevos. Pierde: un conjunto de evaluación
  menor, dos releases con re-extracción antes de evaluar y el precedente de reabrir lo cerrado.
- **(c) Procedimiento para un hallazgo grave en cualquier tanda.** Umbral de gravedad: el principio
  de gobierno del §1 del laudo congelado, tal como lo precisó la enmienda del 25/09: una falla de
  esquema que produzca falsedad en campo estructurado en material fresco
  (`enmienda_ventana_correccion_2026-09-25.md` §2, precisión 1); una omisión visible o un error con tasa
  medida y balance favorable se acepta con residuo declarado y no la abre. Procedimiento:
  1. el hallazgo se documenta con su tasa sobre la muestra leída y sus casos, y se clasifica (§2);
  2. si cumple el umbral y la corrección exige prefijo, esquema o formato de salida, la autora decide
     por enmienda fechada al laudo congelado y al pre-registro de la tanda si abre una ventana
     excepcional; sin esa enmienda rige (a);
  3. si la abre: laudo propio del cambio, prueba pareada con tope, re-extracción de todo lo extraído
     hasta esa tanda con el prefijo nuevo (clase «todo»: unidades acumuladas × 0,0166), y salen de
     B6.3 (a) los TOs de todas las tandas cuya lectura informó el cambio (los que se leyeron para
     decidirlo), registrados en `documentos_excluidos_esq.json` con la fecha de la enmienda;
  4. el pre-registro de B6.3 no se sella hasta cerrar ese ciclo; una vez sellado, nada de esto aplica
     (laudo congelado §7).
  Costo según la tanda: tras la tanda 1, el de (b); tras la tanda 2, con los digeribles y los no-RI
  extraídos, del orden de 7.700 unidades ≈ USD 128; tras la tanda 3, los 9.324 de la partición más
  desarrollo ≈ USD 155 más 1.763 × 0,0166 ≈ USD 184 en total. Lo que gana la tesis: no evaluar un
  grafo con falsedades estructuradas conocidas. Lo que pierde: los TOs que informaron el cambio y el
  tiempo del ciclo.

Decidido (D1, 03/10/2026): la opción (a) como regla, con el procedimiento (c) de hallazgo grave tal como
queda escrito arriba, acotado a su umbral. La opción (b) no se adopta; queda descrita como alternativa
evaluada, con su costo.

## 7. Composición de la tanda 1 para detectar temprano

**Criterio propuesto**: la tanda 1 no se elige por tamaño sino por diversidad de las formas que el
pipeline r2 trata por primera vez, con estratos y cuotas fijados antes y un orden determinístico
dentro de cada estrato (desempate por id). Fuentes por TO: categoría (`inventario_tos.csv`), modo de
lectura, páginas y unidades (`conteos_b584.json`), tablas serializadas por e0-r2 (chunks con bloque de
tabla contra la partición, `r5_escalera_particion.py --comparar`, `por_to.texto.tablas`), citas sin
comillas y anáforas de la norma en el texto de E0 (conteo con las regex de [c24] del tablero), líneas
conservadas por K (`r2_codigo/rk_fuera_de_muestra.json`, `por_to`) y pies de página
(`r4_pies_e0.json`, `particion.casos`). Candidatos: los 147 menos los 14 fuera, 133 TOs.

Estratos y cuotas, fijados por la autora (D5, 03/10/2026):
1. **TOs ya excluidos de B6.3 (a)** (los diez de ESQ-2, todos digeribles): 4, los más largos. Su
   lectura no le quita nada al conjunto de evaluación: son los únicos TOs donde una ventana
   excepcional del §6 (c) saldría gratis en evaluación.
2. **Regímenes informativos**: 4, los que más tablas, anáforas y líneas de K suman. Contradice la
   fila B6.1 («digeribles, normativa general prioritaria»), que se enmienda (D5): entran porque e0-r2
   ya los segmenta (escalera, 152/152 TOs; `r2_codigo/cierre_freno.md` §1) y porque son el bloque sin
   fila de tanda (§5). Motivo declarado de la enmienda: con la regla (a) del §6, detectar temprano
   abarata el procedimiento (c).
3. **TOs con más tablas**: 4 (prueba del bloque serializado y de la lectura confiable del prompt
   nuevo).
4. **Los más largos**: 3 (prueba de herencia, sub-chunking y volumen de remisiones).
5. **Formas de cita nuevas**: 3, los que más citas sin comillas y anáforas de la norma tienen
   (reglas (e) y (g) de `remite_a`).
6. **Escalera de E0**: 2 TOs con modo `marcadores` o `sin_raiz` (prueba de las etapas 2 y 3 fuera
   de la tanda 0, que es toda `vigente`).

Ejemplo de aplicación del criterio con esas cuotas (es una ilustración recomputable, no la lista;
`scratchpad` de esta unidad): ayccef, expaef, opefci, adrei (estrato 1); ri_ccna, ri_cc, ri_rml,
ri_gerc (2); snp_cheq, ceninf, cirmo3, snp_tr (3); lingeef, depaho, cajasc (4); manori, efemin,
nmcief (5); ri_dcpc, ri_oc (6). Son 20 TOs, 3.292 unidades, E1 y E3 ≈ USD 54,65 (la fila B6.1 estima
~USD 40 para 20 digeribles, `:765`), 10 de ellos digeribles y 10 «necesita reglas», 6 RI, 4 fuera de
la evaluación. Cubre las cuatro recuperaciones de K-a′+K-b (ri_rml, snp_cheq; nmaeef y snp_dd no
entran), los tres TOs con más tablas y el TO con más anáforas (manori).

**Efecto sobre el conjunto de evaluación.** Con la regla (a) del §6, ninguno: extraer un TO no lo
excluye de B6.3 (a); solo lo excluye haber informado el esquema. Con la opción (b) o una ventana del
§6 (c) tras la tanda 1, salen los 20 TOs de la tanda: con el ejemplo, 16 TOs elegibles menos (los 4
del estrato 1 ya estaban fuera), de 137 a 121. Cuanto más TOs del estrato 1 lleve la tanda 1, menor
ese costo. El criterio no toca la construcción del conjunto de B6.3 (a), que se pre-registra aparte
(plan `:772`; checklist Q3 a Q5, Q10).

## 8. Criterio de revisión del prompt: literal contra interpretación

Campos del tool schema r2 (`data/experiment/pyd_r2/generados/tool_schema_r2.json`; `required`:
`entities`, `relations`, `omisiones`), tal como los conecta el borrador de U-PROMPT-R2
(`docs/mandatos/UPROMPT_R2_prefijo_nuevo.md`, decisiones 3 a 12):

**Piden copiar texto literal** (verificables en código como subcadena del texto de E0):
`umbrales[].tramo` («copiado tal cual»), `properties.frecuencia` de Obligacion («tramo literal»),
`relations[].sujeto_mencion` («copiado tal cual aparece»), `omisiones[].tramo` («copiado tal cual»).
`Comunicacion.codigo` es casi literal (la forma «A-7825»).

**Piden interpretación al modelo**, y si podrían resolverse en código desde un tramo literal:

| Campo | Qué pide | ¿Resoluble en código? |
|---|---|---|
| `type` (9 tipos) | clasificar la entidad | No: es la decisión central del extractor. La válvula es la omisión `fuera_de_tipos` (§9). |
| `label` | nombre corto canónico | No; no es verificable. Se acepta como paráfrasis. |
| `properties.descripcion` | paráfrasis del contenido | No desde el prompt actual: ninguna entidad lleva un tramo literal propio, así que el código no puede verificar la paráfrasis (límite ya declarado en L-ESQ-R2 §1.4, fila 26: la inversión de sentido con el valor literal no se detecta). Un tramo de evidencia por entidad lo haría verificable (decidido, D6). |
| `Restriccion.tipo` (3 valores) | clasificar el tope | Parcialmente: `limite_cuantitativo` se infiere de una lista de umbrales con valor; `prohibicion` de marcadores en el tramo. Hoy el código controla la coherencia tipo–predicado como marca (`BKL-0038`), no deriva el tipo. Conviene dejarlo así: derivar cambiaría el esquema. |
| `Obligacion.tipo` (6 valores) | clasificar la obligación | Solo `periodica` se infiere de la presencia de `frecuencia`; el resto no. |
| `Comunicacion.tipo` (4) y `numero` | clasificar y numerar | Sí, los dos, desde `codigo` (L-ESQ-R2 §2.4: el tipo ya se deriva en r2a). En el prompt nuevo, `codigo` es el literal y `tipo` y `numero` son redundantes: candidatos a derivarse en código y salir del prompt (decidido, D7). |
| `Definicion.termino` | el término definido | Debe pedirse literal («copiado tal cual»); hoy la descripción del campo está vacía en el tool schema. Con el término literal el código lo verifica y `remite_a` lo lee (regla H4). |
| `TextoOrdenado.materia`, `archivo`, `version` | datos del TO | Sí: `archivo` lo conoce E0, `materia` sale del título del inventario y `version` de la portada; hoy E4 ya canoniza el TextoOrdenado desde E0 (`data/experiment/r2_codigo/r3_freno.md`, §3). Candidatos a derivarse en código (decidido, D7). |
| `predicate` (13) | clasificar la relación | No: lo controla la matriz; la válvula es `relacion_sin_predicado`. |
| `punto` (entidad y relación) | elegir entre los puntos admitidos | Estructural, no interpretación; el validador lo controla. |
| `sujeto_id`, `sujeto_propuesto_padre_sugerido` | sugerir el id del catálogo | Ya resuelto en código desde la mención (R1 a R4; `r1_e4.resolver_relaciones_r2`): el prompt lo pide solo como sugerencia. |
| `omisiones[].categoria` (5) | clasificar la omisión | `tabla` y `formula` se cruzan con las marcas de E0 (P-e2.5); `meta_normativo`, `fuera_de_tipos` y `relacion_sin_predicado` son del modelo. |
| `omisiones[].nota`, `otras_propiedades` | texto libre | Son válvulas (§9), no se verifican. |

Regla que se desprende, para la revisión del borrador: todo campo cuyo valor sea función de un tramo
literal se resuelve en código a partir del tramo (`sujeto_id` desde la mención, umbral desde el
tramo, `Comunicacion.tipo` y `numero` desde `codigo`, el TextoOrdenado desde E0), y el prompt pide
el tramo; así un hallazgo futuro sobre esos campos se corrige en código (clase «solo código», §2)
sin tocar el prefijo. Los campos de clasificación (`type`, `predicate`, `tipo`) se quedan en el
modelo, con sus válvulas. Decidido (D6 y D7, 03/10/2026): el tool schema r2 suma un tramo literal de
evidencia por entidad; `Comunicacion.tipo` y `numero` se derivan en código desde `codigo` y el
TextoOrdenado desde E0, y salen del prompt; `Definicion.termino` se pide literal. Lo aplica U-PROMPT-R2
(decisiones 15 a 17 de su mandato), y la etapa de diseño estima el costo del tramo de evidencia en
tokens de salida y su verificación en código.

## 9. Las válvulas de escape

Lo que el tool schema r2 guarda cuando el esquema no prevé algo (`tool_schema_r2.json`):
- `entities[].otras_propiedades` (objeto nombre → valor): «propiedades que el texto expresa y la
  definición del tipo no prevé. Nunca se descartan: se registran aparte». Presente en los nueve
  tipos; el ensamblado las lleva a `properties_no_definidas` (LN-2, S26).
- `omisiones[]` con `categoria` de cinco valores (`meta_normativo`, `tabla`, `formula`,
  `fuera_de_tipos`, `relacion_sin_predicado`), `tramo` literal y `nota`, obligatoria en todo chunk.
  `fuera_de_tipos` guarda lo que no entra en los nueve tipos; `relacion_sin_predicado`, toda relación
  que el texto expresa y el esquema no representa (L-ESQ-R2 §8.3).
- `relations[].sujeto_mencion`, literal, y `sujeto_propuesto_padre_sugerido` para el sujeto que no
  está en el catálogo: la resolución y el registro de no mapeados viven en código.
El borrador de U-PROMPT-R2 los conserva (decisiones 4, 5, 12 y el control de LN-1, LN-2 y LN-7).

**Lo que falta** para que un hallazgo del tipo «nos falta representar X» quede entero en el crudo:
1. **Las relaciones no tienen campo libre**: `otras_propiedades` existe solo en entidades. Un
   atributo de la relación que el texto exprese (condición, alcance, modalidad) no tiene dónde
   guardarse salvo como omisión. Decidido (D8): `otras_propiedades` también en `relations[]`.
2. **`relacion_sin_predicado` pierde la estructura**: la omisión lleva tramo y nota, pero no los
   `local_id` de origen y destino. Decidido (D8): `source` y `destino` opcionales en la omisión.
3. **Ninguna entidad lleva un tramo literal propio** (solo sus cuantías): la descripción no es
   verificable y una entidad de tipo dudoso no deja su evidencia. Decidido (D6): tramo literal de
   evidencia por entidad.
4. **No hay `tipo_propuesto` ni `predicado_propuesto`**: el canal abierto experimental de
   `prompt_e1.py:200-247` está apagado y fuera del perfil r2; las omisiones `fuera_de_tipos` y
   `relacion_sin_predicado` lo reemplazan con la nota libre. Es suficiente si la nota lleva el tipo o
   el predicado que el modelo habría usado; la instrucción lo pide (D8).
Con 1, 2 y 3 decididos, todo hallazgo de representación queda en el crudo con su tramo, su ubicación y
su estructura, re-leíble en código a USD 0 (principio 12), sin abrir ninguna ventana.

## 10. Decisiones de la autora (03/10/2026)

| # | Decisión | Resuelto | Costo |
|---|---|---|---|
| D1 | Cambios de prompt o esquema durante el escalado (§6) | opción (a), con el procedimiento (c) de hallazgo grave escrito en el §6 | USD 0 salvo que (c) se dispare; la opción (b) queda descrita y no adoptada |
| D2 | Quién adjudica las lecturas asistidas de cada tanda (P15, Q12) | lectura asistida con revisión de la autora, como hasta ahora | USD 0 de API; tiempo de la autora |
| D3 | Cuándo se re-aplican las correcciones de código (§3) | opción (i): al grafo acumulado en cada release; el grafo de cada tanda se sella sin corregirlo | USD 0; un sellado por tanda |
| D4 | Aritmética de las tandas y el bloque RI (§5) | el plan se corrige: 43 digeribles en la tanda 2, descontados los 5 de la tanda 0; fila nueva para la tanda de los regímenes informativos | tanda de RI ≈ USD 16 en E1 y E3 |
| D5 | Composición de la tanda 1 (§7) | por diversidad, con los seis estratos y cuotas del §7 (4/4/4/3/3/2); se enmienda la fila B6.1 con el motivo: con la regla (a), detectar temprano abarata el procedimiento (c) | ejemplo: 3.292 unidades ≈ USD 54,65 contra ~USD 40 de la fila; tope en el mandato de la tanda |
| D6 | Tramo literal de evidencia por entidad (§8, §9) | sí: entra al tool schema r2 por U-PROMPT-R2; su costo en tokens de salida y su verificación en código los estima la etapa de diseño de esa unidad | a estimar en U-PROMPT-R2 P1 |
| D7 | Campos que salen del prompt y se derivan en código (§8) | sí: `Comunicacion.tipo` y `numero` desde `codigo`; el TextoOrdenado desde E0; `Definicion.termino` se pide literal | USD 0; cambio del tool schema en U-PROMPT-R2 |
| D8 | Válvulas que faltan (§9) | sí: `otras_propiedades` en las relaciones y `source` y `destino` en la omisión `relacion_sin_predicado`; la nota declara el tipo o predicado faltante | USD 0; cambio del tool schema en U-PROMPT-R2 |
| D9 | Nombre y directorio de los grafos de tanda (§4) | `KG-Tanda<k>-<release>` en `corpus_tanda<k>/` | USD 0 |

Asientos que siguen a estas decisiones: plan, filas B6.1 y B6.2 y fila nueva de la tanda de regímenes
informativos, y la regla de `:741`; checklist, condición nueva de la tanda 1 (criterio de diversidad);
mandato de U-PROMPT-R2, decisiones 15 a 17 (D6 a D8).

## 11. Comandos

- Perfil por TO de la partición (categoría, unidades, tablas, formas de cita, K, pies): script de
  esta unidad sobre `inventario_tos.csv`, `conteos_b584.json`, la salida de `r5_escalera_particion.py
  --comparar`, `rk_fuera_de_muestra.json`, `r4_pies_e0.json` y los `chunks_<to>.json` de
  `b584_particion/` (regex de [c24]); salida `perfil_tos_particion.json` en el paquete de la unidad.
- Unidades y costo por grupo: `inventario_unidades.csv` (`veredicto`) cruzado con `conteos_b584.json`
  (`unidades_extraccion`) y la tarifa de `tabla_reprocesamiento.md` §5.
- Campos del tool schema: recorrido de `tool_schema_r2.json` (`input_schema.properties`, con `$defs`).

## Firma

FIRMADO por la autora el 03/10/2026. Rige desde esta firma para la tanda 1 y las siguientes. El texto de
los §1 a §9 es el del borrador commiteado en `9eabab0`, con las marcas de decisión abierta reemplazadas por
las decisiones del §10; toda modificación posterior es nota fechada aparte, nunca ajuste silencioso.

## Notas posteriores a la firma

El texto firmado no se edita; estas notas se leen junto con él.

- **03/10/2026 — §6, lista de tablas forzadas a residual (decisión de la autora).** El perfil r2b tiene
  prevista una lista explícita, en código, de tablas serializadas por E0 que el mensaje de E1 trata como
  contenido tabular residual (nota fechada del 03/10/2026 al mandato de U-PROMPT-R2, `e7f7a2e`; borrador
  en `data/experiment/prompt_r2/p1/mensaje_r2_borrador.py`, `TABLAS_RESIDUALES_FORZADAS`, sin commit al
  03/10/2026). Dar de alta una tabla en esa lista no cambia el prefijo, el esquema ni el formato de
  salida de E1: no es un cambio de los que difiere la opción (a) (`:213-214`;
  `enmienda_uso_ventana_2026-09-30.md` §3.3). Tampoco es una corrección en código sobre la salida ya
  guardada (§2.7 de esa enmienda): cambia el mensaje de E1 y re-extrae solo las unidades que traen la
  tabla. Cada alta se declara con la tabla, el motivo y la fecha. Durante las tandas 1 a 3 se clasifica
  con la tabla de reprocesamiento en la clase «E1 y E3 de las afectadas» (§2, eje A, `:82-83`;
  `tabla_reprocesamiento.md:62-63`): pagan solo las unidades que traen la tabla y, como las de esa clase
  por E0, se corrige entre tandas (regla de cruce, `:97-98`). La tabla de reprocesamiento no tiene una
  fila propia para este cambio; su efecto sobre las claves es el de la fila F04
  (`tabla_reprocesamiento.md:87`: cambian la línea de marcas del mensaje de E1 y la nota de E3 de esas
  unidades). Por analogía con las correcciones de E0 entre tandas, un alta en la lista no saca a su TO del
  conjunto de evaluación de B6.3 (a).
- **03/10/2026 — §5, costo de referencia de las tandas a la tarifa del prefijo nuevo (decisión de la
  autora).** Cifras de E1 y E3 de la estimación central del FRENO P1 de U-PROMPT-R2
  (`git show fca019d:data/experiment/prompt_r2/p1/salida/censo_p1.json`, `recalculo_tandas_usd`): tanda
  1, ejemplo del §7 (3.292 unidades), USD 66,43; tanda 2, digeribles restantes (5.669), USD 114,39, y
  no-RI plenos (2.008), USD 40,52; tanda 3, RI plenos (976), USD 19,69; partición completa (9.324), USD
  188,14. Son USD 0,0202 por unidad, contra 0,0166 de la tanda 0 (`:179-181`, `:187`). Son estimaciones
  sobre el crudo de la tanda 0, no mediciones del prefijo nuevo. Esas cifras corresponden a la variante
  A de `frecuencia`; con la variante B, que es la aprobada, son 66,39 / 114,33 / 40,50 / 19,68 y 188,05.
  Las filas no se suman: la tanda 1 del ejemplo toma TOs de los grupos de las tandas 2 y 3, y esas filas
  están antes de descontarlos (`:180-181`); la fila de la partición es el universo de los 152 TOs, que
  incluye los cinco TOs nuevos de la tanda 0, no la suma de las otras.
- **04/10/2026 — §5, fila «fuera, 14» (decisión de la autora).** La fila se precisa por las enmiendas del
  04/10/2026 a las adendas 1 y 2 del laudo B5.5 (`docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md`,
  firmadas por la autora el 04/10/2026; commit de la firma PENDIENTE). Con la tanda 3 entran: las 77
  unidades de prosa del bloque A, con procedencia por página; las 25 unidades por punto de ri2_pm; y
  ri_spi, si su unidad de E0 cerró. Quedan fuera del recurso: `manual`, histórico; optico y
  plandecuentas, referencia; y ri_ao, derogado, que sale de la tanda 3. Queda como release posterior el
  bloque B: 366 páginas de ri2_pm y la planilla de los nueve. Los candidatos de la tanda 1 (§7) pasan de
  133 a 132 TOs, sin ri_ao.
- **04/10/2026 — §1, muestra de la cola humana al cierre de cada tanda (decisión de la autora).** Las
  unidades que E3 no terminó entran al grafo marcadas (`cola_humana` y `estado_e3`;
  `docs/plan_tesis.md:363`). Al cierre de cada tanda se suma a las lecturas del §1, punto 3:
  - **Muestra:** 20 unidades de la cola humana de la tanda, sorteadas con semilla declarada antes de
    leer; si la cola tiene menos de 20, todas.
  - **Lectura:** asistida, con revisión de la autora (decisión D2, §10), contra el texto de la unidad.
    Qué cuenta como unidad con error se escribe antes de leer la primera muestra y no se cambia
    después.
  - **Reporte:** con la tanda, las unidades con error sobre las leídas y su intervalo de Wilson al
    95 %.
  - **Regla fijada de antemano:** si el límite superior de Wilson de la tasa de error supera el 20 %,
    las unidades de la cola humana de esa tanda se re-procesan o salen del grafo evaluado de esa
    tanda, y se reporta cuál de las dos y por qué.
  Aritmética de la regla, para leerla sin sorpresa. Con 20 unidades leídas, el límite superior es
  16,1 % con 0 errores y 23,6 % con 1: la regla se cumple solo con 0 errores. Con menos de 16 unidades
  leídas, el límite superior pasa el 20 % aun con 0 errores (0 de 15 da 20,4 %).
- **04/10/2026 — la nota anterior sobre la cola humana queda reemplazada por una enmienda firmada (decisión de
  la autora).** La nota del 04/10/2026 al §1 queda sin efecto: agregaba una obligación de cada cierre y una
  regla con umbral a un texto firmado, y eso va por enmienda. Rige
  `docs/enmienda_protocolo_entre_tandas_2026-10-04_cola_humana.md`, FIRMADA por la autora el 04/10/2026. Cambia
  la muestra (30 unidades) y los umbrales (25 % sobre el límite superior de Wilson con muestra; 10 % sobre la
  tasa observada si se lee la cola entera) y fija qué es una unidad con error.
- **04/10/2026 — crecimiento del catálogo de sujetos durante el escalado (decisión de la autora).** Antes del
  primer crecimiento del catálogo durante el escalado tiene que existir, con su prueba, el script que toma el
  catálogo nuevo, re-resuelve el registro de sujetos en cuarentena, rehace el grafo desde el crudo guardado
  (USD 0) y lo verifica. Hoy no existe: `r1_e4.reresolver_registro` (`corpus_v2/r1_e4.py:469-489`) solo se usa
  en la suite (LN-6, `scripts/regression_kg.py:1766`) y en un selftest, y
  `data/experiment/catalogo_unico/code/reresolver_tanda0.py` calcula la re-resolución sin aplicarla. El cambio
  es el de la fila F13 de la tabla de reprocesamiento
  (`data/experiment/mantenimiento/tabla_reprocesamiento.md:97`): E4, el esqueleto y lo que sigue del
  ensamblado, en código. La unidad que lo construye se registra en el plan (`docs/plan_tesis.md:402`).
- **04/10/2026 — la nota anterior sobre el crecimiento del catálogo queda reemplazada por una enmienda firmada
  (decisión de la autora).** La nota del 04/10/2026 sobre el crecimiento del catálogo de sujetos durante el
  escalado queda sin efecto: agregaba una obligación nueva a un texto firmado, y eso va por enmienda. Rige
  `docs/enmienda2_protocolo_entre_tandas_2026-10-04_catalogo.md`, FIRMADA por la autora el 04/10/2026. El
  script lo construye una unidad propia (`docs/mandatos/URERESOL_CAT_reresolucion_catalogo.md`, BORRADOR —
  PENDIENTE DE FIRMA).
- **04/10/2026 — enmienda 3 y fe de erratas de la enmienda 2, FIRMADAS por la autora (decisión de la autora,
  tras el freno de U-TABLA-REPROC).** La composición real de las claves de la caché contradice el §2 en tres
  filas. Rige `docs/enmienda3_protocolo_entre_tandas_2026-10-04_clases_de_reprocesamiento.md`: F05 pasa a
  «solo código sobre lo guardado»; F10 paga E3 de todas las unidades, más los reintentos de E1 donde cambie
  el feedback; F14, `validador_e1`, pasa a «E1 y E3 de las afectadas»; y `validador_r2` queda en «solo código»,
  como F14b. La enmienda 2 lleva al pie su fe de erratas: con el código de hoy, un id nuevo en el catálogo es
  F11 y no F13.
- **04/10/2026 — la enmienda 3 decide la regla de cruce para F14 (decisión de la autora).** El §3 de la
  enmienda 3 dejaba a decisión de la autora si un cambio de `validador_e1` se corrige entre tandas. Lo decidió
  el 04/10/2026 y firmó la enmienda con ese cambio: los cambios de la clase F14 se corrigen entre tandas igual
  que los de E0, con E1 y E3 solo de las unidades afectadas y su costo declarado antes de correr. La versión
  anterior del §3 es la de `0cb0c70`.
- **06/10/2026 — insumo del pre-registro de la tanda 1: el alcance de los documentos del ejemplo del §7 (decisión de la
  autora).** De los 20 TOs del ejemplo, 8 ya tenían alcance en el catálogo (adrei, ayccef, cajasc, depaho, efemin, expaef,
  lingeef, opefci) y los 12 restantes quedaron decididos: 6 con clase existente (ri_ccna, ri_cc por el título, ri_dcpc,
  snp_cheq con dos clases, manori, nmcief con dos clases), 3 con un rol existente reutilizado (ri_rml y ri_gerc, secciones del
  Régimen Informativo Contable Mensual; snp_tr, por la remisión de su texto a las normas complementarias) y 3 sin alcance
  declarado (ri_oc, ceninf, cirmo3), con sus menciones colectivas a cuarentena según la enmienda 6 a L-ESQ-R2 cuando se firme.
  Registro: `data/experiment/catalogo_unico/registro_alcance_por_tanda.md`; regla general del título y regla de las secciones de
  un mismo régimen en la enmienda 4 (BORRADOR), §2, puntos 7 y 8; checklist `:81`, condición 11. La lista real de la tanda 1 sale
  de la segmentación oficial: lo que cambie respecto del ejemplo se lee con el mismo paso.
- **07/10/2026 — §1, punto 4, y §5: la tarifa de referencia desde la tanda 1 (decisión de la autora).** El texto firmado compara el
  costo de cada tanda con la tarifa de la tanda 0 con el esquema congelado (E1 0,007425 y E3 0,009179 por unidad, USD 0,0166
  juntas, `:66-67`, `:177-187`, `:207`, `:224`, `:238`, `:245`), y la nota del 03/10/2026 estimaba 0,0202 con el prefijo nuevo. La
  tanda 1 corre con las instrucciones finales, cuya tarifa observada es otra: U-REEXT-T0, T5 (`data/experiment/reext_t0/reporte_u_reext_t0.md:183-185`;
  `tabla_reprocesamiento.md` §5, comando 1): E1 USD 0,010135 y E3 USD 0,010226 por unidad (verificación 0,009008 más
  reintentos de E1 del ratchet 0,001218), USD 0,020361 juntas, sobre las 2.439 unidades de la tanda 0. Decisión: desde la tanda 1,
  **la tarifa de referencia es la observada con las instrucciones finales más el agregado medido de U-E3-LISTAS**: O2 (`7fe848c`)
  midió que el bloque que abre la lista y la NOTA del ítem suman 918.107 tokens de entrada de E3 por corrida del tamaño de la
  tanda 0 (1.054 ítems), USD 1,84 a USD 2 por millón, USD 0,000754 por unidad sobre las 2.439. Referencia: **E1 0,010135, E3
  0,010980, USD 0,021115 por unidad** (redondeado, 0,0211). Con ella, el ejemplo del §7 (3.292 unidades) cuesta ≈ USD 69,5 (contra
  54,65 a 0,0166 y 66,4 a 0,0202); la partición completa (9.324), ≈ USD 197; la tanda 3 (976), ≈ USD 20,6. La cifra 0,0166 queda
  como la tarifa de la tanda 0 con el perfil sellado, para el registro, y no se compara más con las tandas. Se lee junto con las
  tablas del §5 (`:177-187`). El pre-registro de la tanda 1 toma esta referencia (A7) y la ajusta si O3 de U-E3-LISTAS (costo
  real por ítem con la NOTA) da un agregado distinto del medido en seco; la desviación real contra el estimado sigue el punto 4
  del §1 y P9.
- **09/10/2026 — referencia vieja en el §6, procedimiento (c), punto 3 (`:239-240`).** Donde dice «registrados en
  `documentos_excluidos_esq.json`», ese archivo está sellado. El registro vigente es
  `data/experiment/esq/documentos_excluidos_evaluacion_final.json`, que lo extiende (su `:3`) y es el que cita el pre-registro de B6.3
  (`docs/checklist_pre_escalado.md`, Q10). El texto firmado no cambia.
- **10/10/2026 — anclas al laudo de la release r2 y el ejemplo del §7 (decisiones de la autora del 10/10/2026).** El texto firmado no
  cambia.
  - **Anclas corridas** (`:21`, `:50-51`, `:134-135`). Citan `docs/laudo_release_r2_pipeline.md:243-283`, `:264-277` y `:253-263`,
    que eran líneas de la v1. En la v2 del laudo esas líneas son el anexo A (§1.3 y §1.4). El gate vigente es el §3 de la v2 (`:63-81`,
    «reemplaza la §3.1 de la v1»), y la §3.1 de la v1 está en `:348-388`.
  - **El ejemplo del §7** (`:285`). Donde dice «10 de ellos digeribles y 10 "necesita reglas"», el recuento da 8 y 12
    (`docs/plan_tesis.md:409`; `docs/checklist_pre_escalado.md`, condición 5). La fe de erratas va también en el pre-registro de la
    tanda 1.
- **15/10/2026 — ri2_pm queda fuera del grafo evaluado (decisión de la autora; hoja de ruta de la mesa, §101).** La nota del
  04/10/2026 al §5 (`:431-438`) cuenta, entre lo que entra con la tanda 3, «las 25 unidades por punto de ri2_pm». La autora decidió que
  no entran en el grafo evaluado: van con el bloque B, en la release posterior, declaradas. Coincide con el acta de S1-bis
  (`data/experiment/segmentacion_oficial_e0r2/s1bis/acta_sorteo_S1bis.md:22-24`) y con la fila B6.2b (`docs/plan_tesis.md:777`). El
  texto firmado no cambia.
- **15/10/2026 — ri_spi y ri_con, con la E0 corregida (decisión de la autora recibida a las 15:54:12; hoja de ruta de la mesa, §106 y
  §107).** La E0 corregida los segmenta por numeración: 96 y 34 unidades (manifiesto de S0-6b, `unidades_por_to`). Se cuentan una sola
  vez, por las decisiones 1 y 2 de la enmienda 8. La fila «fuera, 14» del §5 (`:163-166`) queda como la cifra de la partición legada, en
  la que eran no segmentables. El texto firmado no cambia.
