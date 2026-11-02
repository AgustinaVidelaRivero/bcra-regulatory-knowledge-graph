# Adenda 2 al laudo B5.5 — Ampliación de cobertura a los bloques excluidos

**Estado: FIRMADA — [nombre omitido] [nombre omitido] [nombre omitido], 07/09/2026** (versión enmendada con las tres enmiendas de su laudo del 07/09). Segunda adenda al laudo
`docs/laudo_B5.5_alcance_corpus_y_catalogo.md` (firmado 04/09, `c0daef1`);
el laudo original y la adenda 1 (segmentación universal, firmada 06/09)
se conservan íntegros. Implementación:
`docs/diseno_B5.9_ampliacion_cobertura.md` (en freno de diseño).

## §1. La evidencia que motiva el laudo

Unidades U-COB-EXCL y U-COB-EXCL-2 (adjudicación registrándose en
U-COB-EXCL-3):

1. El instrumento deóntico original **no contaba el futuro impersonal**,
   que es la forma con que este corpus manda. Corregido, la relación
   entre el material excluido y el articulado cayó de **5,58× a 1,56×**.
2. **Lectura a ciegas de 32 páginas** por la autora, con pre-registro
   sellado y enmendado antes de leer: **23 prescriptivo / 9 referencia /
   0 duda**.
3. **Diez de los doce** documentos declarados no segmentables contienen
   contenido prescriptivo. Solo `plandecuentas` y `optico` son referencia
   pura, y son exactamente los dos con densidad deóntica **0,000** en las
   tres variantes del instrumento.

**Conclusión de la autora:** el criterio de forma (¿tiene espina
numerada?) no coincide con el criterio de contenido (¿manda algo?). El
recurso, tal como estaba planificado, excluiría normativa vigente.

## §2. El laudo

**Se amplía la cobertura a los dos bloques hoy excluidos, ANTES del
escalado. Ambos, no uno.**

- **Bloque A — EXTRACCIÓN sobre DIEZ documentos y 41 páginas**
  (enmienda 1 de la autora, recomputada contra `particion_152.json`:
  ri_con 16, ri_spi 11, ri_tii 6, ri_rem 2, y seis de 1 página —
  ri_chr, ri_fcem, ri_itme, ri_pfmipyme, ri_pscpp, ri_pspii; control
  161 − 43 − 77 = 41). **`optico` (43 pág) y `plandecuentas` (77 pág) NO
  se extraen**: ya están adjudicados como referencia pura por la lectura
  a ciegas y son los dos con densidad deóntica 0,000 en las tres
  variantes; se censan para el registro y se DECLARAN. `plandecuentas`
  es además material ficha (76/77 páginas), de modo que esta enmienda
  resuelve su caso y no la herencia del bloque B. Proyección de costo
  recalculada: 41 × 1,38 = **57 unidades ≈ USD 1,10**.
- **Bloque B**: el bloque ficha de los 2 parciales — **2.175 páginas**
  (manual 1.830, ri2_pm 345; ídem verificado).

## §3. Guardas vinculantes (las cinco del laudo, más una del diseño)

1. **Regresión de no-cambio**, como en B5.8: ninguna regla ni unidad
   nueva altera la segmentación ya obtenida — verificación documento por
   documento contra **1.763 / 762 / 6.340 / 9.266**. Diferencia = FRENO.
2. **Esquema congelado**: se verifica sobre muestra pequeña que el
   material nuevo cabe en el vocabulario del laudo `2593d4d` (9 tipos /
   13 relaciones / enum de 6) ANTES de extraer a escala. Si no cabe,
   FRENO y reporte: reabrir el esquema es laudo de la autora, nunca
   efecto colateral.
3. **Modelo de unidad y procedencia — LAUDADO (enmienda 3).** Se aprueba
   el modelo del diseño §2: unidad = bloque de prosa contiguo dentro de
   una página, **sin fabricar espina**; procedencia = documento + página
   + offset; campo `granularidad_procedencia` distinguiendo `punto` de
   `pagina` por elemento. La afirmación de la tesis pasa a «cada
   elemento cita su ubicación en el texto oficial, con la granularidad
   que el documento permite». **EXIGENCIA AGREGADA**: el reporte entrega
   el **conteo exacto** de elementos con procedencia a nivel de página
   sobre el total del recurso, para escribir «N elementos de M, todos
   provenientes de los diez documentos sin numeración» y no una salvedad
   general.
4. **Guarda de volumen** para el bloque B: se mide antes de extraer; si
   el bloque ficha pasara a ser fracción dominante de las unidades del
   recurso, es laudo de la autora y no automático.
5. **Piloto antes de masa** en el bloque B: ri2_pm (345) antes de manual
   (1.830), con techo de gasto declarado por unidad.
6. *(agregada por el diseño, §5)* **Umbral de balance declarado**: si la
   proyección del bloque B supera el **25 %** de las unidades del recurso
   final, su fase de extracción no arranca sin laudo explícito sobre el
   balance del recurso. Convención anterior y auditable, no calibrada.

## §4. Efecto en la secuencia (registrado con todas las letras)

- **El capítulo del esquema y la lectura de mentores NO se detienen**: lo
  que se valida es la metodología y el esquema, no la partición final.
  El tramo 5 narra la partición de B5.8.4 como hecho **y declara el
  hallazgo de cobertura** y la ampliación en curso.
- **La fecha del escalado SÍ se mueve**: del orden de dos a tres semanas
  de trabajo efectivo si ambos bloques van antes, más las adjudicaciones.
- **DECISIÓN DE SECUENCIA (enmienda 2): DESACOPLE.** Bloque A **antes**
  del escalado; bloque B como **release posterior declarada** (principio
  9). El «ambos, no uno» sigue en pie en el qué: B no se abandona, se
  declara con su evidencia medida y su fase B.1 corre cuando el escalado
  esté encaminado. Razones: la superficie real de A es de días y de un
  dólar; A es el único de los dos bloques con evidencia de la autora
  detrás; B exige otra lectura a ciegas antes de extraer una página, que
  es tiempo en la ruta crítica; y su costo no tiene ancla (cota de
  referencia: el escalado completo, ~USD 123). **Efecto sobre la fecha
  del escalado: días, no semanas.** El tramo 5 del capítulo declara el
  hallazgo de cobertura **con la ampliación en dos tiempos**.

## §5. Qué NO cambia

El corpus congelado sigue congelado (principio 9 y regla del inventario
solo-lectura); el esquema sigue congelado salvo laudo propio; los
documentos ya segmentados no se re-segmentan; y el resultado de B5.8.4
(138 / 2 / 12) sigue siendo el hecho verificado sobre el que se escribe
el capítulo, con la ampliación declarada en dos tiempos.

**Nota de coordinación (autora, 07/09): `docs/tesis/main.tex` NO se toca
por nada de esto.** La afirmación sobre la procedencia y el párrafo de la
partición dependen de laudos que recién ahora quedan cerrados, y el tramo
2 está en la mesa de tuneo: **los dos se ajustan en el tramo 5**.

## Firma

**Firma: [nombre omitido] [nombre omitido] [nombre omitido] · Fecha: 07/09/2026.** Firmada sobre la versión enmendada: alcance del bloque A en diez documentos y 41 páginas (cuenta verificada por la autora), desacople de secuencia, y laudo del modelo de procedencia con su conteo exigido.

---

## §6. Registro posterior a la firma (07/09) — el cruce prescriptividad × forma

Agregado después de la firma, con evidencia nueva que **refuerza lo
laudado y no lo modifica**. Fuente: cruce hecho por la instancia del plan
entre la adjudicación v2 de U-COB-EXCL-2 (32 fichas: 23 prescriptivo / 9
referencia) y el censo de forma de U-COB-A fase A.1.

**Origen real de las 32 fichas — el muestreo abarcó los DOS bloques:**

| bloque | fichas | prescriptivo | referencia |
|---|--:|--:|--:|
| A (los 12) | 14 | **10** | 4 |
| B (ficha: manual 12, ri2_pm 5, ri_laft 1) | 18 | **13** | 5 |
| **total** | **32** | **23** | **9** |

**Hallazgo 1 — correspondencia 1:1 exacta.** Las 10 fichas
prescriptivas del bloque A pertenecen a **diez documentos distintos**
(ri_chr, ri_con, ri_fcem, ri_itme, ri_pfmipyme, ri_pscpp, ri_pspii,
ri_rem, ri_spi, ri_tii), y `optico` y `plandecuentas` solo tienen
fichas de referencia. La afirmación «diez de los doce contienen
contenido prescriptivo» tiene, por lo tanto, correspondencia exacta y
por documento con la lectura a ciegas.

**Hallazgo 2 — las diez prescriptivas del bloque A son TODAS prosa;
cero planilla.** Las tres fichas de planilla del muestreo (`optico`
p.1, `plandecuentas` p.1, `ri_con` p.16) fueron juzgadas **referencia**.
Salvedad de alcance, corregida por la autora: de esas tres, **solo
`ri_con` p.16 cae dentro de las 41 páginas del alcance de extracción**
(las otras dos son de los documentos declarados referencia y sus
páginas no integran las 41). **La muestra de planilla dentro del
alcance es de UNA página**, y una página no sostiene una declaración
sobre las 21 de planilla del bloque A.

**Hallazgo 3 — el material ficha del bloque B SÍ prescribe: 13 de sus
18 fichas fueron juzgadas prescriptivas** (manual 8, ri2_pm 5). Es
evidencia propia del bloque B, y deja asentado que **el desacople
laudado en §4 es de CALENDARIO y no de fondo**: B no se posterga porque
su material sea referencia, sino porque su superficie, su costo sin
ancla y su lectura a ciegas pendiente lo ponen fuera de la ruta crítica.
**Es así como el capítulo lo declara** al contar el bloque B como
release posterior.

**Consecuencia laudada por la autora (07/09):** la escala del bloque A
—si la planilla entra o queda para B— **no se lauda por la muestra de
una página: se manda al piloto A.2, que corre con DOS BRAZOS
DECLARADOS (prosa y planilla) y predicciones pre-registradas por
separado**. El laudo de escala sale con esa medición.

## §7. Registro posterior a la firma (07/09) — TRES destinos, no dos

Con `ri_spi` fuera del bloque A (laudo 2 de la autora sobre el freno de
A.1: numera el 71 % de sus bloques, de modo que darle procedencia de
página degradaría granularidad real y darle la suya exige código que
A.1 tiene prohibido escribir), la ampliación de cobertura tiene **tres
destinos y no dos**:

1. **Bloque A — NUEVE documentos, ahora**: `ri_chr`, `ri_con`,
   `ri_fcem`, `ri_itme`, `ri_pfmipyme`, `ri_pscpp`, `ri_pspii`,
   `ri_rem`, `ri_tii`.
2. **`ri_spi` — caso propio**: tiene espina, el parser vigente no la
   reconoce; destino regla de variante de marcador (familia B5.8.2) o
   unidad chica propia. No se le escribe código en A.1.
3. **Bloque B — release posterior declarada** (principio 9), con el
   desacople de §4 y la evidencia de §6 (13 de sus 18 fichas juzgadas
   prescriptivas: el desacople es de calendario, no de fondo).

**El hallazgo original de la autora sigue intacto** —diez de los doce
documentos contienen prescripción— **pero esos diez se atienden por
tres vías distintas**. El capítulo debe declararlo así: de otro modo
parecería que un documento se perdió en el camino.

**Efecto medido de sacar `ri_spi` (recomputado sobre el censo de A.1):**
son **141 de los 332 bloques del bloque A, el 42,5 %** — no un décimo.
Sin él, el alcance queda en **9 documentos, 30 páginas y 191 bloques**,
repartidos en **77 de prosa** y **114 de planilla**; y la categoría
mixta desaparece por completo, porque sus 37 bloques eran todos de
`ri_spi`. Dos consecuencias registradas: el brazo de prosa —el que
sostiene el encuadre original de la adenda— queda en **la mitad** de lo
supuesto al firmar, y **la planilla pasa a ser mayoría (60 %)** del
material del bloque A. De ahí el agregado de la autora al freno
exprés: **si tras sacar `ri_spi` alguno de los dos brazos queda sin
material suficiente para medir, eso es hallazgo con su cuenta y no se
compensa ni se sigue con un brazo simbólico.**
