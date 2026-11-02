# Enmienda 5 al protocolo entre tandas — el grafo evaluado de cada tanda deja fuera la cola humana, y cómo vuelve una unidad

**FIRMADA por la autora el 06/10/2026** (firma por mensaje de la autora; redactada el 2026-10-06 sobre su decisión del mismo día). Rige desde
esta firma, para la tanda 1 en adelante.

Enmienda con fecha al protocolo entre tandas (`docs/protocolo_entre_tandas.md`, FIRMADO en `a304b89`; texto firmado: las primeras 398
líneas, sha256 `b23d37c5396a…`). El protocolo no se edita: esta enmienda vive al lado y se lee junto con él, con la enmienda sobre la
cola humana (`docs/enmienda_protocolo_entre_tandas_2026-10-04_cola_humana.md`, FIRMADA el 04/10/2026, `8d01b04`), la enmienda 2
(`0b98045`), la enmienda 3 (`0cb0c70`, con su §3 en `bd77541`) y la enmienda 4 (BORRADOR).

## 0. Qué enmienda y por qué

- **Lo que dice la enmienda de la cola.** Al cierre de cada tanda se lee una muestra de la cola humana (30 si la cola tiene más de 30; si
  no, toda), con el criterio de unidad con error fijado en su §1.4, y rige una regla con umbral (§1.6): si el límite superior de Wilson
  al 95 % de la tasa de error supera el 25 % (o la tasa observada supera el 10 % con la cola entera leída), las unidades de la cola de
  esa tanda se re-procesan o salen del grafo evaluado de esa tanda. §3: la marca de la cola en el grafo y la decisión D2 no cambian.
- **Lo que pasó en la tanda 0.** La cola fue 74 de 2.439 unidades (43 `veredicto_inutilizable`, 29 `cola_humana`, 2 inválidas); la
  lectura de T4 de U-REEXT-T0 dio 12 de 30 con error y la regla se disparó; la salida fue un ensamblado sin la cola, sellado como grafo
  evaluado (U-SINCOLA-T0: KG-Tanda0-Diez-r2b-sincola `e22fae1a…` y KG-Tanda0-Desarrollo-r2b-sincola `2922b72d…`; SC2 en `dde9f44`, sello
  en `235a295`), con el grafo completo sellado al lado como medición del pipeline.
- **Por qué una enmienda.** Decidir de antemano, para todas las tandas, que el grafo evaluado deja fuera la cola cambia la definición del
  grafo evaluado de la tanda (hoy, el grafo de la tanda con la cola adentro y marcada; `docs/plan_tesis.md:363`) y la función de la regla
  del §1.6 (de disparador a cifra). Son decisiones nuevas sobre un texto firmado, y van por enmienda, no por nota.

## 1. Qué decide

1. **El grafo evaluado de cada tanda, desde la tanda 1, es el ensamblado sin la cola humana.** Se ensambla y se sella junto con el grafo
   completo (con la cola adentro y marcada, que sigue siendo la medición del pipeline), con el procedimiento de U-SINCOLA-T0: la bandera
   `--sin-cola` del ensamblador (`descartar_cola_r2`, el único punto de descarte después de `entrada_r2`), manifiesto propio, entrada
   propia en la suite con las expectativas de la entrada completa, clave propia en `grafos.py`, carga propia en Neo4j con el control de
   0 marcas de la cola. Las vigilancias, las observaciones y las lecturas del §1 se miden sobre los dos grafos y se dice sobre cuál.
2. **La lectura de la cola sigue igual, y la regla pasa a ser una cifra.** La muestra, el criterio y el intervalo de la enmienda de la
   cola no cambian. La regla del §1.6 deja de decidir la salida (ya decidida por el punto 1) y se reporta con la tanda como cifra y como
   vigilancia: si se dispara, se investiga la causa antes de la tanda siguiente y se reporta; no cambia el grafo evaluado de la tanda.
3. **Cómo vuelve una unidad de la cola al grafo evaluado.** Solo si una corrección posterior, registrada en la tabla de reprocesamiento
   (`data/experiment/mantenimiento/tabla_reprocesamiento.md`), permite procesarla de nuevo y el verificador la acepta: la unidad recibe
   un registro final nuevo en `finales.jsonl` con validación final, y el ensamblado de la release siguiente la toma (toma la última
   versión de cada unidad y descarta solo las que siguen sin validación final). Nunca por una lectura humana sola: una unidad leída como
   correcta por una persona sigue en la cola hasta que el verificador la acepte. Por el principio 9 del plan (`docs/plan_tesis.md:277`) y
   la decisión D3 del protocolo (§10), el grafo evaluado de una tanda ya sellado no se corrige: la unidad vuelve en la versión siguiente,
   declarada como tal.
4. **La tanda 0 queda como está.** Sus dos grafos evaluados sin la cola siguen sellados (`dde9f44`, `235a295`); las 74 unidades de su
   cola no vuelven por esta enmienda. La medición de O3 de U-E3-LISTAS sobre las unidades afectadas de la tanda 0 se declara al lado de
   la cifra de la cola («de las 74, N aceptarían con el E3 corregido»), sin re-sellar (decisión de la autora del 06/10/2026, `9bca986`).
5. **Lo que entra al pre-registro de la tanda 1.** La fila de la cola dice: grafo evaluado = ensamblado sin cola (esta enmienda); lectura
   de 30 con el criterio de la enmienda de la cola, Wilson al 95 %, la regla del 25 % como cifra y vigilancia; línea de base de la tanda 0:
   12 de 30 con error; tamaño y composición de la cola, línea de base 74 de 2.439 (3,0 %; 43/29/2), umbral de atención 6 %; camino de
   vuelta por release, según el punto 3.

## 2. Efectos declarados

- **Dos grafos por tanda,** los dos sellados: el completo (medición del pipeline, con la cola marcada) y el evaluado (sin la cola). Las
  cifras de la tesis dicen sobre cuál se miden; la nomenclatura (`docs/nomenclatura_grafos.md`) y el tablero (`docs/tablero.md`) nombran
  el evaluado como «sin cola», como ya pasa en la tanda 0.
- **Reprocesamiento.** Ninguna fila nueva en la tabla: la re-verificación de una unidad de la cola por una corrección de E3 es «E3 de
  las afectadas» (F10, F23); su vuelta al grafo evaluado es ensamblado en código.
- **El texto de la tesis** (capítulo 4, el grafo evaluado): las unidades que el verificador no aceptó entran al grafo completo con su
  primera extracción, marcadas, y quedan fuera del grafo evaluado; vuelven en la release siguiente si una corrección las lleva a la
  aceptación.

## 3. Qué no cambia

- El texto del protocolo, sus demás notas y las enmiendas 2, 3 y 4.
- La enmienda de la cola humana: su lectura, su criterio de unidad con error, su muestra, su intervalo y sus umbrales (solo cambia qué
  hace la regla cuando se dispara: reportar, no decidir la salida).
- La marca de la cola en el grafo completo y la decisión D2.
- Los dos grafos evaluados sellados de la tanda 0.

## Firma

FIRMADA por la autora el 06/10/2026. Rige desde esta firma. El pre-registro de la tanda 1 la cita como fuente de la fila de la cola.

## Notas posteriores a la firma

El texto firmado son las 71 líneas de arriba (`ccd8fad`, sha256 `84dff0a3e925…`) y no cambia.

- **07/10/2026 — nombres (decisión D13 de la autora, RECONC-DISENO-EVAL).** Donde esta enmienda dice «grafo evaluado de cada tanda» (el
  ensamblado sin la cola humana), léase **«grafo sin cola de la tanda N»**; el ensamblado sellado al lado, con la cola adentro y marcada, es
  **«grafo completo de la tanda N»**. «El grafo evaluado» queda reservado al escalado sellado antes del pre-registro de B6.3 (laudo 3 del
  20/09/2026) y «el grafo corregido» a la release posterior a la evaluación (`docs/protocolo_dos_grafos.md`, BORRADOR). Las reglas de esta
  enmienda no cambian.
- **08/10/2026 — corrección de la mesa** (barrido de límites, contradicción 6; autorizada por la autora). La nota anterior llama BORRADOR al
  protocolo de los dos grafos (`docs/protocolo_dos_grafos.md`): se firmó el 07/10/2026 (`53bbd6f`). La nota no cambia en lo demás.
- **08/10/2026 — precisión de la mesa** (barrido de límites, contradicción 11). Las 74 unidades de la cola de la tanda 0 de esta enmienda
  (§0 y §1.5) son las de r2b (43 `cola_humana_veredicto_inutilizable`, 29 `cola_humana` y 2 `cola_humana_reextraccion_invalida`, en
  `corpus_tanda0/salida_r2b/*/finales.jsonl`); las 71 de la enmienda de la cola humana (`docs/enmienda_protocolo_entre_tandas_2026-10-04_cola_humana.md:15-17`)
  son las de r2a (35 y 36, en `corpus_tanda0/salida/*/finales.jsonl`). No se contradicen: al citarlas, se nombra el grafo.
- **08/10/2026 — la decisión de la autora sobre los ítems de lista de la tanda 0 (E3-01 del barrido de límites) choca con el §1.4** («La
  tanda 0 queda como está … sin re-sellar»). Va por la enmienda 7 al protocolo entre tandas, en BORRADOR
  (`docs/enmienda7_protocolo_entre_tandas_2026-10-08_excepcion_tanda0_en_el_resellado.md`); hasta su firma rige el §1.4.
- **08/10/2026 (tarde) — la enmienda 7 al protocolo entre tandas quedó FIRMADA** (con el tope de R0 en USD 1,50): desde su firma rige la
  excepción declarada al §1.4 para los dos grupos de unidades de la tanda 0 que nombra.

- **15/10/2026 — el re-sellado único de los grafos r2b de la tanda 0.** Los grafos sellados que cita este documento tienen una versión posterior, del re-sellado único (`docs/mandatos/URESELLADO_T0_resellado_unico_grafos_r2b.md`, firmado; FRENO en `data/experiment/resellado_t0/FRENO_resellado_T0.md`): `e22fae1a…` (KG-Tanda0-Diez-r2b-sincola) → `61dd1b69…` (KG-Tanda0-Diez-r2b-sincola-rs1, 8.491 nodos y 25.976 aristas); `2922b72d…` (KG-Tanda0-Desarrollo-r2b-sincola) → `66e745f5…` (KG-Tanda0-Desarrollo-r2b-sincola-rs1, 6.711 nodos y 21.996 aristas). Cambian por el código de U-OMISIONES-COD (`ded41d50`) y por las salidas de R0 (`1d690df3` y `2d0f5277`); los de diez, además, por R2-3 (`803623a`), que los sellados no tenían. El diff por campo y por causa está en `data/experiment/resellado_t0/salidas/`. Los sellados siguen sellados (principio 9); el commit del sello de los nuevos queda en `commit_sellado` de `data/experiment/neo4j/grafos.py`. La cola de la tanda 0 pasa de 74 a 69 unidades: salen, por R0, `ext::2.6.1.1`, `ext::3.5.6.1`, `ext::3.6.1.1`, `ext::3.6.4.2` y `ext::3.13.1.10`, y no entra ninguna. El texto firmado no cambia.
