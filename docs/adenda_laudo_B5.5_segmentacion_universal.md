# Adenda al laudo B5.5 — Segmentación universal del corpus antes del escalado

**Estado: FIRMADA — [nombre omitido] [nombre omitido] [nombre omitido], 06/09/2026.** Adenda al laudo
`docs/laudo_B5.5_alcance_corpus_y_catalogo.md` (firmado 04/09, sello
`c0daef1`): el laudo original SE CONSERVA ÍNTEGRO; esta adenda registra la
ampliación dictada por la autora el 06/09. Implementación:
`docs/diseno_B5.8_segmentacion_universal.md` (secuencia B5.8, en freno de
diseño).

## §1. La ampliación

El escalado NO se limita a describir los 68 TOs con segmentación
reconocida: **los 84 restantes deben volverse segmentables ANTES del
escalado** — con reglas mecánicas de parseo, sin modelo de lenguaje en el
corte ni en la partición — para que el capítulo del esquema describa la
partición del corpus como HECHO verificado (N reconocidos con health-check
por TO / M declarados no segmentables con causa) y no como etapa
pendiente. Los 62 TOs que hoy producen cero unidades se tratan como
familia aparte: lo que no sea segmentable con reglas se DECLARA, no se
fuerza.

## §2. Qué NO cambia (fronteras del laudo original, ratificadas)

1. **El corpus de EXTRACCIÓN de las tandas 1–2 sigue siendo los 68
   digeribles** (laudo B5.5 §2). La incorporación de los TOs no-RI que
   B5.8 reconozca (~31 candidatos de normativa general, cubiertos por el
   esquema congelado) queda como **RE-LAUDO explícito de la autora con el
   censo de B5.8.0 en la mano**, con re-presupuesto — no se decide acá.
2. **El bloque RI sigue FUERA de la extracción** hasta su ciclo propio
   (laudo `94bb7a7` §D10: ESQ-RI-1→4; su familia mayor exige extender el
   esquema — hechos con valor). Esta adenda lo vuelve **segmentable**, no
   extraíble: segmentable ≠ extraíble, y la prosa del capítulo respeta esa
   distinción.
3. El gate de validación del escalado (lectura del capítulo, B5.5 §5.1),
   la Rama B del catálogo (§5.3) y la condición de U-B5.3 (cerrada,
   `0515fa6`) quedan intactos.

## §3. Regresión de no-cambio (vinculante para toda la secuencia)

Las reglas nuevas no alteran la segmentación sellada: **byte-identidad**
de los artefactos E0 de los 5 TOs de desarrollo (contra `salida_enm01`),
de los 68 reconocidos y de los 10 de ESQ (contra `e0_dry`), con los tres
conteos de control recomputados (1.763 / 6.340 / 762). Cualquier
diferencia = FRENO: invalidaría números sellados en laudos y en la
Introducción.

## §4. Efecto en la ruta crítica

B5.8 corre en paralelo a la escritura del capítulo; **B5.8.4 (partición
final) pasa a ser prerrequisito del CIERRE del capítulo** (no de su
escritura): la pasada final del tramo 5 incorpora los números nuevos, y
las filas 10–15 del mapa de fuentes se reescriben desde los artefactos de
B5.8.4 con sus comandos de recómputo. La ruta sigue: capítulo →
validación por lectura → escalado → B6.3.

## Firma

**Firma: [nombre omitido] [nombre omitido] [nombre omitido] · Fecha: 06/09/2026.** Con la firma quedan
resueltos los tres puntos del §7 del diseño: (1) el corpus de extracción
de tandas 1–2 sigue en los 68; la incorporación de los no-RI reconocidos
se RE-LAUDA con el censo de B5.8.0 en la mano; (2) segmentable ≠
extraíble ratificado — el RI sigue gateado por D10; (3) ESQ-RI-1 y B5.6
se ejecutan como B5.8.1 y B5.8.3, con sus filas marcadas sin duplicar.
