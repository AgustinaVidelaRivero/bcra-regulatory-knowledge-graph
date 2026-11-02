# Enmienda 4 al protocolo entre tandas — cómo crece el catálogo de sujetos, cuándo se lee el alcance de un documento nuevo y la regla de cruce del tercer escalón

**FIRMADA por la autora el 07/10/2026** (versión para firmar commiteada en `1190a8a`; firma por mensaje de la autora). Rige desde esta firma.
Redactada el 04/10/2026 (BORRADOR); versión para firmar del 07/10/2026, al cierre de
R2 de U-RERESOL-CAT (R2-1 y R2-1 bis `0737497`, R2-2 `a079275`, R2-3 `803623a`, R2-3 bis `dac7d57`). Actualizada el 07/10/2026 (noche) con lo
que congela la firma (§6) y lo que hace falta antes de la tanda 1 (§7).

Enmienda con fecha al protocolo entre tandas (`docs/protocolo_entre_tandas.md`, FIRMADO en `a304b89`; texto
firmado: las primeras 398 líneas, sha256 `b23d37c5396a…`). El protocolo no se edita: esta enmienda vive al lado
y se lee junto con él, con la enmienda sobre la cola humana (`8d01b04`), la enmienda 2 (`0b98045`) y la
enmienda 3 (`0cb0c70`, con su §3 en `bd77541`).

La condición para firmarla (R2 de U-RERESOL-CAT con el script de re-resolución funcionando, con su prueba;
enmienda 2, punto 3) está cumplida: `reresolver_catalogo.py` y su selftest (66/66), la prueba T1–T4 sobre el crudo r2b (R2-1), el registro
de alcance legible por código (R2-2), la salida de S19 con el runner alineado (R2-3) y la regla general del padre del propuesto en un
documento sin alcance, con cualquier motivo (R2-3 bis).

---

## 0. Qué enmienda y por qué

- **Lo que dice el protocolo.** No fija cómo crece el catálogo de sujetos durante el escalado, ni cuándo se
  decide el alcance de un documento nuevo. La enmienda 2 pone una sola condición: que exista, con su prueba, el
  script que re-resuelve y rehace el grafo.
- **Lo que hay hoy.**
  - De los 157 documentos, 86 no tienen entrada de alcance (`docs/plan_tesis.md:404`). Sin entrada, el mensaje
    de E1 no lleva la línea de alcance.
  - R1 de U-RERESOL-CAT (`data/experiment/reresolucion_catalogo/freno_r1.md`, `c98093a`) diseñó dos catálogos:
    el del request, fijo por release, y el de resolución, que lee el código y puede crecer entre tandas. Con
    esa separación, un alta no cambia ningún request.
  - En el registro de KG-Tanda0-Diez-r2a hay 27 filas en cuarentena con la mención verificada, en 18 claves.
    Dos claves llegan a 2 unidades, las dos en cap; ninguna llega a 3 (`salidas/r1_medicion.json`, clave
    `frecuencias`).
- **Por qué una enmienda.** Agrega dos reglas, una con umbral, a un texto firmado, y extiende su regla de cruce. El mandato de U-RERESOL-CAT
  ya lo preveía: hasta que esta enmienda se firme, ninguna de las dos rige
  (`docs/mandatos/URERESOL_CAT_reresolucion_catalogo.md`, primera nota del 04/10/2026).

## 1. La regla de crecimiento del catálogo

1. **Dos fuentes.** Las entradas nuevas salen de:
   - el alcance de los documentos nuevos, antes de su extracción (§2);
   - la cuarentena, al cierre de cada tanda.
2. **Umbral, para la cuarentena.** Una clave es candidata cuando su mención verificada está en cuarentena en
   al menos 2 unidades distintas del registro acumulado. El número se confirma o se recalibra con el registro
   de U-REEXT-T0, antes de la firma.
3. **Lectura y aprobación.** Cada candidata se lee contra el texto (lectura asistida, declarada) y entra solo
   con la aprobación de la autora, como alias de un id que ya existe o como id nuevo con su padre.
4. **Solo al catálogo de resolución.** El catálogo del request no cambia entre tandas: ni el bloque del
   prefijo, ni el enum, ni el tool schema. Lo agregado actúa por las reglas, sobre la mención guardada; el
   modelo no lo sugiere (L-ESQ-R2 §7, `4ef7650:862-864`).
5. **Después corre el script de re-resolución** (enmienda 2): re-resuelve el registro, rehace el grafo desde el
   crudo guardado a USD 0 y lo verifica. El reporte de la tanda dice cuántas relaciones resolvió cada versión
   del catálogo.
6. **Límites.**
   - Una mención que no verifica nunca resuelve por crecimiento.
   - En la release siguiente, las ampliaciones pasan al catálogo del request.

## 2. El paso de lectura del alcance, antes de cada tanda

1. **Cuándo.** Antes de la primera extracción de cada tanda, para cada documento de la tanda que no tenga
   entrada de alcance.
2. **Cómo.** Con el método del laudo de B5.4 (`docs/laudo_B5.4_fase1_catalogo.md:15-20`, `dea56ba`): se lee el
   pasaje de alcance del documento y se cita textual.
3. **Solo clases que ya existen.** Si el pasaje nombra exactamente una o dos clases del catálogo, el documento
   recibe esa entrada de clase. Cambia solo el mensaje de sus unidades: el de toda unidad ya extraída sale
   byte a byte igual, y se controla.
4. **Si no.** Un documento sin pasaje de alcance, o que necesite un rol nuevo, entra sin línea de alcance,
   declarado. Su rol se decide en la release que corresponda. Mientras tanto, lo que el texto no identifica va
   a cuarentena, como fije la enmienda 6 a L-ESQ-R2 cuando se firme.
5. **Quién decide.** La lectura es asistida y declarada. La aprueba la autora, documento por documento, antes
   de extraer.
6. **Costo.** La lectura se hace siempre sin API.
7. **El título como pasaje de alcance** (regla general declarada por la autora el 06/10/2026 y precisada el mismo día). El
   título vale como pasaje de alcance solo si el cuerpo del documento no tiene frase de alcance, y si nombra una o dos
   clases exactas del catálogo que son el sujeto obligado o el informante del documento, no el objeto de la norma («una o
   dos», como la regla del pasaje del punto 3). El documento recibe esa entrada de clase; se aplica igual a todo documento
   en esa situación, y la lectura deja constancia de que la base es el título. Primer caso: ri_cc → `Sujeto_caja_de_credito`.
   Fuera de la regla por nombrar el objeto: fimipyme, ri_fcem y ri_pfmipyme (MiPyME) y ri_dsf y ri_esd (deudores).
8. **Secciones de un mismo régimen informativo** (decisión de la autora del 06/10/2026, acotada). Un documento que es una
   sección de un régimen informativo cuyo rol ya está en el catálogo reutiliza ese rol (primer caso: ri_rml y ri_gerc →
   `Sujeto_rol_entidad_comprendida_reginf`, el del Régimen Informativo Contable Mensual). No decide ESQ-RI-3, que es la
   pregunta entre regímenes distintos.
   **Precedencia (decisión de la autora del 07/10/2026):** entre secciones de un mismo régimen informativo, el rol del régimen
   prevalece aunque el pasaje de la sección nombre una clase exacta del catálogo (por ejemplo, «las entidades financieras» en
   `ri_pgn::S1`), para que todas las secciones del régimen compartan el mismo sujeto; la clase nombrada queda en la ficha como
   observación. Tercer caso: ri_pgn → `Sujeto_rol_entidad_comprendida_reginf` (reemplaza a ri_cc en la tanda 1).

## 3. La regla de cruce para F08d

La fila F08d de la tabla de reprocesamiento es el tercer escalón del reintento de E1, de clase «E1 y E3 de las
afectadas» (la suma P3c-2 de U-PROMPT-R2). La regla de cruce del §2 del protocolo (`a304b89:97-100`) cubre esa
clase cuando el hallazgo es por E0, y la enmienda 3 la extendió a F14. Un cambio del techo del tercer escalón se
corrige entre tandas igual que los de E0 y los de F14: se vuelven a correr E1 y E3 solo de las unidades
afectadas, con su costo declarado antes de correr.

## 4. Qué falta para que se pueda aplicar

- **El script de re-resolución,** con su prueba: R2 de U-RERESOL-CAT. **[07/10/2026] Hecho:** `reresolver_catalogo.py`, selftest 66/66, prueba T1–T4
  (`0737497`, `a079275`).
- **El registro de alcance por tanda.** Las entradas de clase de los documentos nuevos no pueden ir a
  `catalogo_sujetos_r2.json` sin romper sus candados. R1 propone un registro que solo agrega, leído junto con
  el de la release (`freno_r1.md`, §4). Lo implementa R2 de U-RERESOL-CAT (decisión de la autora del
  04/10/2026), con `e1_extractor/prompt_r2b.py` autorizado solo para leer ese registro al armar el mensaje,
  sin cambiar el prefijo. **[06/10/2026]** El registro arranca con las doce entradas de la tanda 1 decididas por la autora,
  en `data/experiment/catalogo_unico/registro_alcance_por_tanda.md` (lectura humana, una fila por documento y por tanda);
  R2-2 define el formato legible por código y lo carga desde ahí, sin cambiar las decisiones. **[07/10/2026] Hecho en el ensamblado:**
  formato `registro_alcance_por_tanda/1` (`reresolucion_catalogo/reresolver_catalogo.py:86`, lector en `:159`; R2-2, `a079275`). Falta
  el cableado en el mensaje de E1 (§7).
- **La fila F08d,** que existe cuando P3c-2 de U-PROMPT-R2 la sume a la tabla. **[07/10/2026] Existe**
  (`data/experiment/mantenimiento/tabla_reprocesamiento.md:156`).

## 5. Qué no cambia

- El texto del protocolo, sus notas y sus enmiendas anteriores.
- El catálogo de sujetos de r2 y sus candados: esta enmienda no agrega ningún id ni ningún alcance.
- El criterio de admisión de ids de L-ESQ-R2 §7 (`4ef7650:861`).
- El laudo B5.5: ESQ-RI-3 sigue abierta y atada a la release (`docs/plan_tesis.md:695`).

## 6. Lo que congela la firma

| Qué | Dónde | Sello al 07/10/2026 | Cómo cambia después |
|---|---|---|---|
| Las reglas de §1 a §3 | este documento | el texto firmado | solo por otra enmienda |
| El catálogo del request (bloque del prefijo, enum, tool schema) | `catalogo_unico/catalogo_sujetos_r2.json` | sha256 `c3ad15811c7e…` | no cambia entre tandas (§1, punto 4); las ampliaciones pasan en la release siguiente |
| El formato del registro de alcance por tanda | `registro_alcance_por_tanda/1` (`reresolver_catalogo.py:86`) | — | solo por otra enmienda |
| Las filas de la tanda 1 del registro | `catalogo_unico/registro_alcance_por_tanda.md` | sha256 `ce402aad7c84…` (12 filas: 9 con alcance; ri_oc, ceninf y cirmo3 sin alcance) | solo agrega: un documento nuevo de la lista final de la tanda 1 suma su fila por el §2, antes de extraerse |
| El comportamiento de la parte A y del padre del propuesto | `corpus_v2/r1_e4.py` (`58a54db13136…`), `tanda0/code/ensamblar_tanda0.py` (`d5a2f27c07b1…`), en `dac7d57` | los casos T11g a T11i y T12a a T12g de `selftest_r3` y los 66 de `selftest_reresolver_catalogo` | el ensamblador cambia en U-OMISIONES-COD: se congela la regla, verificada por esos casos, no el sha del archivo |
| El script de re-resolución y su procedimiento | `reresolucion_catalogo/reresolver_catalogo.py` (`f871d88a16b9…`), `procedimiento_crecimiento_catalogo.md` (`cd2d6237ef12…`) | `dac7d57` | correcciones de código entre tandas, como releases declaradas |

**No congela:** el catálogo de resolución, que crece por el §1 al cierre de cada tanda, ni el mensaje de E1, que cambia una sola vez
en la unidad del §7. Hasta el cableado, `prompt_r2b.py` (`dd13db2e6584…` en `dac7d57`) arma la línea de alcance solo desde el
`rol_por_to` del catálogo (`prompt_r2b.py:409`). Por eso hoy el registro rige solo en el ensamblado (fila F13c de la tabla de
reprocesamiento).

## 7. Lo que hace falta antes de la tanda 1

1. **La unidad del cableado** (nombre propuesto: U-ALCANCE-E1; USD 0, sin API). Corre después de esta firma, antes de la extracción de
   la tanda 1 y en paralelo con U-OMISIONES-COD, que no toca sus archivos.
   - **Qué cambia.** `prompt_r2b.py` lee el registro de alcance por tanda al armar el mensaje, cuando el documento no tiene entrada en el
     `rol_por_to` del catálogo, con el lector de R2-2 y sin cambiar el prefijo. Escrituras: `prompt_r2b.py`, su selftest
     (`selftest_prompt_r2b`) y la fila F13c de la tabla.
   - **Controles.**
     - Los mensajes de las 2.439 unidades de la tanda 0 salen byte a byte iguales, y `selftest_clave_cache` sigue OK con A1r intacto.
     - Cambian solo los mensajes de los documentos de la tanda 1 con alcance nuevo (los 9 del registro): se listan, con caracteres y
       tokens agregados y su costo a la tarifa de E1, medidos en seco.
     - Casos nuevos del selftest: entrada de clase, rol reutilizado y documento declarado sin alcance, que no lleva línea.
   - **Candado.** Los dos valores del candado del mensaje de E1 se recomputan y quedan PROPUESTOS hasta la confirmación de la autora.
   - **Reprocesamiento.** Ninguno: la tanda 1 no está extraída. Si un documento de la tanda 0 recibiera alcance, sería F12/F13c, E1 y E3
     de sus unidades.
2. **La fila 11-bis del checklist**, que se agrega con la firma. Texto propuesto: «**11-bis.** El registro de alcance por tanda está
   cableado en el mensaje de E1 (unidad del §7 de la enmienda 4 al protocolo), con los mensajes de la tanda 0 iguales byte a byte y el
   candado del mensaje re-sellado; previa a la extracción de la tanda 1».
3. **La lista final de la tanda 1.** La fija U-SEG-OFICIAL, después de S0-4, S1-bis y S2, y puede cambiar respecto de los 20 del ejemplo.
   Todo documento de la lista final sin fila en el registro pasa por la lectura del §2, con la aprobación de la autora, antes del
   cableado o junto con él.
4. **Lo que no hace falta antes de la tanda 1:** el crecimiento del catálogo (§1). Corre al cierre de cada tanda, con el registro
   acumulado. Al cierre de la tanda 0 hay 14 claves sobre el umbral (decisión 1). Su lectura y aprobación es la primera aplicación del
   §1, después de esta firma; no es condición de la tanda 1.

## Decisiones al firmar (propuestas por la mesa el 07/10/2026; confirmadas por la autora con la firma del 07/10/2026)

1. **Umbral de la cuarentena (§1, punto 2): 2 unidades distintas**, confirmado con el registro de U-REEXT-T0: en diez, 145 filas en cuarentena
   con la mención verificada, en 87 claves; 14 claves llegan a 2 unidades o más (`data/experiment/reresolucion_catalogo/freno_r2_1.md:152-154`).
2. **La parte A de la enmienda 6 a L-ESQ-R2 corre solo en r2b** (`ensamblar_tanda0.py`, `parte_a=(fase == "r2b")`; el runner alineado en R2-3), y el
   propuesto que produce recibe como padre la sugerencia guardada del modelo con marca, o la raíz del catálogo con marca (R2-3; la regla
   general para todo propuesto sin padre en un documento sin alcance, en R2-3 bis, `dac7d57`).
3. **El registro de alcance por tanda** (§2 y §4) rige con esta firma para el ensamblado; su cableado en `prompt_r2b.py` (solo lectura del registro
   al armar el mensaje, sin cambiar el prefijo) es la condición 11-bis del checklist, previa a la extracción de la tanda 1, en una unidad propia
   que mueve el candado del mensaje de E1 y las claves de E1 de los documentos con alcance nuevo. La fila 11-bis no existe hoy en el
   checklist: se agrega con la firma, con el texto del §7.
4. **La precedencia del rol del régimen** (§2, punto 8, 07/10/2026) y **ri_pgn** como tercer caso.
5. **Lo que congela la firma** (§6) y **la unidad del cableado** (§7), con su lugar en el orden de la tanda 1.

## Firma

FIRMADA por la autora el 07/10/2026 (versión para firmar en `1190a8a`). Rige desde esta firma, con las cinco decisiones al firmar. Lo
primero que dispara: la fila 11-bis del checklist y la unidad U-ALCANCE-E1 (§7), antes de la extracción de la tanda 1.

## Notas posteriores a la firma

- **17/10/2026 — Las filas de alcance de cada tanda y el mensaje de E1** (decisión de la autora del 17/10/2026, recibida a las 20:20:12;
  hoja de ruta de la mesa, §147; mandato de U-ALCANCE-E1, etapa A3, firmado el 17/10/2026,
  `docs/mandatos/UALCANCE_E1_A3_filas_de_la_tanda_final.md`, §1). El mecanismo del mensaje de E1 cambió una sola vez, con el cableado de
  la tanda 1 (A2 de U-ALCANCE-E1, `42823df0`). Después, cada tanda suma sus filas al registro de alcance por la enmienda 4, §2, punto 3
  (`53bbd6fa:64-66`): la lectura «cambia solo el mensaje de sus unidades: el de toda unidad ya extraída sale byte a byte igual, y se
  controla». Con cada tanda se regeneran el derivado del registro (`catalogo_unico/registro_alcance_r2b.json`) y su sha en
  `reextraccion_v2/e1_extractor/prompt_r2b.py` (`:477`), y se recomputan los dos valores del candado del mensaje (`:97-98`), con el
  control byte a byte de los mensajes de lo ya extraído. Es lo que previó la decisión 1 del mandato de U-ALCANCE-E1 al firmar
  (`21e55a07`). La release sigue siendo r2. Los valores nuevos los confirma la autora antes de la extracción de la tanda. El texto firmado
  no cambia. Precisa el «No congela» del §6 (`:130-131`).
- **18/10/2026 — El ancla de la nota del 17/10, corrida por A3** (decisión de la autora del 18/10/2026, recibida a las 18:42:24;
  hoja de ruta de la mesa, §169). El renglón de comentario que agrega A3 en el bloque del candado del derivado (mandato de
  U-ALCANCE-E1, A3, `:44-45`) corre en uno los renglones de `reextraccion_v2/e1_extractor/prompt_r2b.py` desde el 476: el sha del
  derivado, que la nota del 17/10 cita en `:477`, pasa a `:478` con el commit de A3. Los dos valores del candado del mensaje siguen en
  `:97-98`. El texto firmado y la nota del 17/10 no cambian.
