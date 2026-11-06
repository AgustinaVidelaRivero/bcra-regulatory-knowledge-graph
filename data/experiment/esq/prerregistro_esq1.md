# Pre-registro — ESQ-1 · Test ciego de generalización del esquema

**Estado: SELLADO al commitear.** Desde ese momento no se modifica: los desvíos se
declaran, no se recomponen.
Laudo que lo gobierna: `docs/laudo_ESQ-1_diseno.md` (commit `94bb7a7`).
Análisis que lo funda: `data/experiment/esq/scoping_esq1.md` (unidad U-ESQ-0).

## 1. Qué se hereda del laudo, sin re-discutir

Modo (i) con canal abierto · control de instrumento obligatorio y previo · 10
documentos de `escalado_prep/`, semilla 20260827 · lectura absoluta con brazo D
pareado · bandas de §7.4 y regla de normalización de §7.5, selladas en un mismo acto
y declaradas **no calibradas** · tope USD 9,00, a re-presupuestar con el recargo
medido que devuelva el control.

## 2. Fe de erratas heredada

El laudo y el mensaje del commit `94bb7a7` consignan «0 de 8.162 entidades» fuera de
esquema. El 8.162 no corresponde ni a las entidades crudas (14.639) ni a las
validadas (8.009). La conclusión no cambia —cero tipos fuera de esquema en cualquiera
de los dos denominadores— pero la etiqueta era errada y se declara acá. En este
documento y en adelante se usa **8.009 entidades validadas**, y se aclara el alcance
cada vez.

## 3. Predicciones

Se declaran antes de correr. No se ajustan post-hoc. Cada una indica qué resultado la
falsaría.

**P1 — El control aprueba en sus tres brazos.**
Brazo A (20 unidades con `omisiones_no_prosa`): ≥10 de 20 emiten algún propuesto.
Brazo B (10 unidades de presión conocida sobre dominio/rango): ≥7 de 10 vuelven a
reportar la relación. Brazo C (10 unidades limpias, control negativo): ≤1 de 10 emite
un tipo propuesto.
*Fundamento, con su debilidad declarada:* que el extractor haya declarado una omisión
en prosa no garantiza que, con canal abierto disponible, la emita como
`tipo_propuesto`. Son dos comportamientos distintos, y el brazo A es exactamente la
apuesta de que el segundo sigue al primero.
*Falsada si:* cualquiera de los tres brazos no alcanza su umbral.

**P2 — El resultado cae en banda B: el esquema tiene huecos.**
Es decir, T_fam+P_fam ≥ 3, o alguna familia con spread ≥ 3/10, o vol ≥ 3 % — los
cortes heredados de D9, no calibrados.
*Fundamento:* sobre el conjunto de desarrollo el único canal abierto disparó 54 veces
sobre 38 cadenas distintas, en documentos que el esquema ya había visto. Sobre 762
unidades de documentos nuevos, esperar banda A sería optimismo.
*Falsada si:* el resultado cae en banda A.

**P3 — Aparecen más familias nuevas de predicado que de tipo.**
*Fundamento:* los seis tipos de entidad son categorías gruesas y estables —una
obligación es una obligación en cualquier Texto Ordenado—, mientras que los predicados
codifican relaciones específicas del dominio de cada norma. *Precisión sobre la
evidencia:* los 304 `firma_invalida` NO fundan esta predicción por vocabulario: los
196 mayoritarios son presión para ampliar el dominio de `aplica_a`, un predicado que
ya existe. Son evidencia de tensión en la matriz dominio/rango, no en el vocabulario
de predicados. La predicción se sostiene sobre el argumento de estabilidad de los
tipos, no sobre ese conteo.
*Falsada si:* P_fam ≤ T_fam. Y si falla, el hallazgo es peor y más importante: los
seis tipos no alcanzan.

**P4 — El brazo D confirma el confusor del rol.**
Las 20 unidades de desarrollo re-corridas con el rol suprimido producen
sustancialmente más `sujeto_propuesto` que las mismas unidades con el atajo presente.
*Fundamento:* el 83–84 % de las relaciones de sujeto del conjunto de desarrollo pasa
hoy por el atajo del rol.
*Falsada si:* la diferencia es nula o marginal. En ese caso, la lectura absoluta
adoptada en D5 del laudo fue una precaución innecesaria y debe reinterpretarse.

**P5 — Si el resultado cae en banda B, será por familias y/o spread, no por volumen.**
Es decir: vol < 3 %.
*Fundamento:* en desarrollo el canal abierto disparó 54 veces sobre 19.518 elementos
emitidos, o sea 0,28 % — un orden de magnitud por debajo del corte de 3 %.
*Por qué se declara:* «banda B» admite tres caminos, y no elegir cuál deja margen
narrativo. Predecirlo cierra de antemano los dos relatos cómodos, «salió mucho ruido»
y «fue un documento raro».
*Falsada si:* vol ≥ 3 %.

## 4. Observación registrada, no predicha

33 de las 74 unidades con omisión declarada están en Capitales Mínimos —normativa
general, no régimen informativo— y son tablas de ponderadores de riesgo. Hay, por lo
tanto, contenido tabular filtrado fuera de la familia del régimen informativo. Se
registra como observación y no como predicción, porque de ahí no se sigue que vayan a
aparecer familias nuevas que remitan a estructura tabular: esas 33 unidades ya se
corrieron y no produjeron un solo `type_invalido`. Es insumo para D10 y para el
scoping de B5.6, no un resultado esperado de ESQ-1.

## 5. Orden de operaciones — secuencia cerrada

1. Selftest del instrumento nuevo (§7). Sin PASS, no se gasta.
2. Control de instrumento, tres brazos. Sin aprobación, ESQ-1 no corre.
3. Re-presupuesto de la corrida con el recargo medido por el control (D7).
4. Corrida de ESQ-1 sobre los 10 documentos.
5. Brazo D.
6. Extracción de la lista deduplicada de cadenas distintas, sin frecuencias, sin
   documento de origen, sin spread.
7. Normalización ciega por la autora sobre esa lista pelada.
8. Sellado del mapeo de normalización, por commit, antes de computar un solo conteo.
9. Cómputo de T_fam, P_fam, spread y vol.
10. Lectura de bandas.

Los pasos 6 a 8 son el blindaje de D9: invertir su orden invalida la lectura.

## 6. Qué se hace ante lo imprevisto

- **Control fallido:** resultado NULO del instrumento. Antes de declararlo, distinguir
  si el canal no se pobló (falla de implementación, se corrige y se re-corre) o si el
  modelo no lo usó teniéndolo disponible (hallazgo sobre cómo el esquema condiciona lo
  que el modelo puede decir, y va a ESQ-3).
- **Exceso de tope:** se frena y se declara. No se continúa «porque falta poco».
- **Resultado en banda A:** se revisa el instrumento antes de aceptarlo (regla de D9).
- **Cualquier desvío del protocolo:** se declara con su causa. No se recompone en
  silencio.
- **Los `RECHAZO_PREDECLARADO` (V3):** se reportan a ESQ-3 como categoría con nombre,
  no se archivan. Un concepto que el esquema ya nombró y rechazó, y que reaparece con
  insistencia sobre material nuevo, es un hallazgo sobre el esquema y no ruido de
  seguimiento de instrucciones.

## 7. Instrumento nuevo — declarado antes de existir

No hay hoy en el repositorio ningún script que extraiga valores distintos de un campo
de los jsonl de extracción, deduplicados y sin frecuencias (verificado: los ocho
consumidores de esos archivos son runners y selftests, ninguno hace inventario de
valores). Hay que escribirlo, y produce el número central de ESQ-1.

**Requisito de diseño, no negociable:** su salida es la lista de cadenas distintas,
ordenada y deduplicada, **sin frecuencias, sin documento de origen y sin spread**. Si
emitiera conteos, la normalización del paso 7 dejaría de ser ciega y el blindaje de D9
caería.

**Selftest obligatorio antes del gasto**, con el patrón `[PASS] nombre` /
`RESULTADO: PASS` del precedente `ev2_r1/code/selftest_r1.py`. Debe probar, como
mínimo: que la salida no contiene frecuencias ni referencias a documento; que
deduplica; y que lee los campos correctos.

**Dónde busca:** por analogía estricta con `sujeto_propuesto` —que no existe en el
crudo y lo agrega el validador al normalizar—, `tipo_propuesto` vive en
`validacion.entidades[i]` junto a `type`, y `predicado_propuesto` en
`validacion.relaciones[i]` junto a `predicate`.

## 8. Dónde vive el código

`data/experiment/esq/code/`, con molde `ev2_r1/`: mismo vocabulario de nombres
(`comun_*`, `estimacion_*`, `runner_*`, `selftest_*`, `gasto_*`) y su `.gitignore` de
dos líneas (`cache/`, `selftest_out/`). Fundamento: es la unidad más reciente con la
misma forma de riesgo —corrida pagada, estimación previa, freno por tope—, y el
directorio ya está comprometido por el archivo de exclusión. ESQ-1 **invoca** el
pipeline de extracción sin modificarlo, igual que `ev2_r1` invoca el harness congelado.

## 9. Artefactos de salida

Este pre-registro sellado · `orden/` con la semilla y la regla de selección · sellos
verbatim de inicio y fin · estimación previa en json y md · salida cruda de extracción
persistida · resumen de corrida con modelo, prefijo de caché, usage y wall time ·
inventario de tipos y predicados fuera de esquema en json además de tabla · mapeo de
normalización sellado, con una fila por cadena distinta · gasto real recomputado desde
la fuente primaria · selftest del instrumento nuevo con su output.

---
**Sellado por:** Agustina Videla Rivero · **Fecha:** 2026-08-27
