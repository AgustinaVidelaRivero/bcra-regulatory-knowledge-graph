# Enmiendas a las adendas 1 y 2 del laudo B5.5 — qué regímenes informativos entran al recurso y cuándo

**FIRMADAS por la autora el 04/10/2026.** Son dos enmiendas, firmadas juntas.

Las dos adendas no se editan: estas enmiendas viven al lado y se leen junto con ellas. Fuentes, leídas en el
commit de su firma:

| documento | commit | sha256 |
|---|---|---|
| adenda 1 al laudo B5.5 (`docs/adenda_laudo_B5.5_segmentacion_universal.md`) | `a06cdab` | `a68818c4c5dc…` |
| adenda 2 al laudo B5.5 (`docs/adenda2_laudo_B5.5_cobertura.md`) | `1ae387e` | `7baf6ee0fa4c…` |
| adenda 2, registros §6 y §7, posteriores a la firma | `074a712` | — |
| protocolo entre tandas (`docs/protocolo_entre_tandas.md`) | `a304b89` | — |

## Parte I — Enmienda a la adenda 1, §2.2

### I.1 Qué dice hoy

§2.2: «El bloque RI sigue FUERA de la extracción hasta su ciclo propio» (ESQ-RI-1 a 4). La adenda lo vuelve
segmentable, no extraíble. ESQ-RI-3 y ESQ-RI-4 siguen abiertas (`docs/plan_tesis.md:695-696`).

### I.2 Qué decide

1. Se extraen, con el esquema congelado, los regímenes informativos que e0-r2 segmenta por punto. En la
   partición son 40 reconocidos plenos, con 919 unidades y 904 páginas; sin ri_ao (Parte III, punto 2), 39, con
   914 unidades y 903 páginas.
2. El §2.2 sigue rigiendo para la familia que pide extender el esquema: las fichas y las planillas. Queda fuera
   hasta su ciclo (ESQ-RI-3 y ESQ-RI-4), como release posterior.
3. Lo que el esquema congelado no represente en los regímenes extraídos se registra por las omisiones y los no
   mapeados, y se reporta por tanda.
4. El §2.1 no cambia: los no-RI reconocidos entran con re-presupuesto, como ya lo fija el protocolo en la
   tanda 2.

### I.3 Justificación técnica

- El protocolo entre tandas ya creó la tanda de los regímenes informativos (decisión D4) y puso cuatro en la
  tanda 1 (D5), sin citar la adenda 1. Esta enmienda deja escrito qué parte del §2.2 levantan esas decisiones.
- La escalera de e0-r2 segmenta los 152 TOs de la partición
  (`data/experiment/r2_codigo/cierre_freno.md`, §1).
- La familia que el esquema no puede representar es otra: la de las fichas y las planillas, el 71 % de las
  páginas del bloque (`docs/plan_tesis.md:695`).

## Parte II — Enmienda a la adenda 2, §4

### II.1 Qué dice hoy

- §2: la cobertura se amplía a los dos bloques excluidos, antes del escalado.
- §4: el bloque A va antes del escalado; el bloque B queda como release posterior declarada.
- §7 (registro): tres destinos. Nueve documentos del bloque A; ri_spi, por su espina; y el bloque B.

### II.2 Qué decide

1. **Bloque A, calendario.** Las 77 unidades de prosa de los nueve documentos (13 páginas) entran al grafo con
   la tanda de los regímenes informativos (protocolo, tanda 3), con procedencia por página. Es un desacople de
   calendario, como el que el §6 registra para el bloque B. El qué del §2 no cambia.
2. **ri_spi.** Entra por su espina, con la tanda 3, si antes cierra su unidad de E0.
3. **ri2_pm, parte por punto.** Sus 25 unidades por punto (10 páginas) entran con la tanda 3, por el camino
   normal y con el alcance declarado.
4. **Bloque B, release posterior declarada.** Son 366 páginas de ri2_pm: 345 de ficha y 21 de cuerpo entre
   fichas, donde están sus 2 unidades que cruzan fichas. Se suma la planilla de los nueve: 114 unidades en 17
   páginas.
5. **optico y plandecuentas** quedan fuera del recurso como documentos de referencia, sin contenido
   prescriptivo. Fuentes de esa clasificación:
   - adenda 2, §1, punto 3 (`1ae387e`): «Solo `plandecuentas` y `optico` son referencia pura», con densidad
     deóntica 0,000 en las tres variantes del instrumento y la lectura a ciegas; y §2, que los deja sin extraer;
   - censo de U-COB-A (`data/experiment/cobertura_bloque_a/censo_referencia.md`, `074a712`): en sus 120
     páginas no hay ninguna de prosa.

### II.3 Justificación técnica

- El ingreso del bloque A pide código: una vía de páginas en E0, la procedencia con su granularidad, la forma
  «Página N» en la métrica de citas y los tests de unidades de página
  (`data/experiment/no_segmentables_limite/freno_U-NOSEG-LIMITE.md`, L5 c; `7aed71c`). Antes de la tanda 1, ese
  código entra en la ruta crítica de la re-extracción de la tanda 0.
- El prefijo de E1 no cambia. El crudo de U-COB-A es del perfil `v3_b54` y solo de E1
  (`data/experiment/cobertura_bloque_a/a2_salida/resumen_corrida_a2.json`): hay que re-extraer con el perfil de
  la release, por USD 0,30 a 1,56 (ESTIMACIÓN NO VERIFICADA), en cualquier fecha.
- Los nueve documentos son regímenes informativos, como el resto de la tanda 3.

## Parte III — Vigencia: lo que queda fuera del recurso por no ser normativa vigente

1. **`manual` es histórico y queda fuera del recurso**, con sus 2.037 páginas y sus 17 unidades por punto.
   - Su carátula dice «Vigente hasta el 31/12/2017».
   - El índice del sitio lo titula «RI - Manual de Cuentas vigente al 31/12/17.»
     (`data/experiment/escalado_prep/indice_oficial_raw.json`; igual en el control del 02/10/2026,
     `data/experiment/mantenimiento/control_sitio/corridas/2026-10-02/indice_crudo.json`).
   - Sus páginas llevan versiones hasta 2017.
   - Corrige el alcance del bloque B de la adenda 2, que contaba sus 1.830 páginas de ficha.
2. **ri_ao queda fuera.** Su carátula dice «RI Derogado por la Com. A 8262». La partición lo tiene como
   reconocido pleno, con 1 página y 5 unidades.
3. **Censo de vigencia.** La segmentación oficial (U-SEG-OFICIAL) censa las marcas de carátula de los 152 TOs
   («Derogado», «Vigente hasta») y declara en su manifiesto qué TOs son vigentes.

## Parte IV — Cifras, unidades previas y nota al protocolo

**Las 2.574 páginas de los 14 TOs fuera de las tandas** (`particion_152.json`; 38,1 % de las 6.757 del
universo), después de estas enmiendas:

| destino | páginas | qué |
|---|--:|---|
| fuera del recurso | 2.157 | manual 2.037 (histórico), plandecuentas 77 y optico 43 (referencia) |
| release posterior declarada | 383 | ri2_pm 366 (fichas y cuerpo entre fichas) y planilla de los nueve, 17 |
| entran con la tanda 3 | 34 | prosa del bloque A 13, ri2_pm por punto 10 y ri_spi 11 |

**Evidencia de contenido** (`data/experiment/no_segmentables_limite/l4_planilla.csv`; revisión de la autora
PENDIENTE): muestra de 59 páginas con semilla, declarada antes de leer; 27 prescriben, y 22 de ellas son de
`manual`, 2 de ri2_pm y 3 de ri_spi. La planilla de ri_con, optico y plandecuentas no prescriben en ninguna de
las 16 páginas leídas.

**Unidades que hacen falta antes de la tanda 3**, con mandato propio, a redactar:
1. Ingreso del bloque A con procedencia por página: vía de páginas en E0, `granularidad_procedencia`, forma
   «Página N» en `ucita2`, tests de unidades de página y retiro de las tres `aplica_a`
   (`docs/plan_tesis.md:767`), con la guarda 1 de la adenda 2.
2. E0 de ri_spi: regla de marcador de letra y número, con la misma guarda.

**Nota fechada al protocolo entre tandas, §5** (asentada al pie del protocolo el 04/10/2026):
«La fila "fuera, 14" se precisa por las enmiendas del 04/10/2026 a las adendas 1 y 2 del laudo B5.5. Con la
tanda 3 entran: las 77 unidades de prosa del bloque A, con procedencia por página; las 25 unidades por punto de
ri2_pm; y ri_spi, si su unidad de E0 cerró. Quedan fuera del recurso: `manual`, histórico; optico y
plandecuentas, referencia; y ri_ao, derogado, que sale de la tanda 3. Queda como release posterior el bloque B:
366 páginas de ri2_pm y la planilla de los nueve. Los candidatos de la tanda 1 pasan de 133 a 132 TOs, sin ri_ao.»

## Qué no cambia

- El §2 de la adenda 2 y sus guardas (§3).
- La adjudicación de U-COB-A: la prosa entra, con su residuo declarado; la planilla va al bloque B.
- La partición (138, 2 y 12) y el corpus congelado.
- Los grafos sellados.

## Firma

FIRMADAS por la autora el 04/10/2026, las dos enmiendas.

## Notas posteriores a la firma

El texto firmado no se edita (132 líneas, sha256 `eb2ff46704eb…`, `e82e22f`); estas notas se leen junto
con él.

- **04/10/2026 — la unidad de E0 de ri_spi es la etapa S0 de U-SEG-OFICIAL (decisión de la autora).** La
  Parte IV lista la E0 de ri_spi entre las unidades «con mandato propio, a redactar». Ese mandato es la
  etapa S0 del mandato de U-SEG-OFICIAL (`docs/mandatos/USEG_OFICIAL_segmentacion_e0r2.md`, S0, punto 4;
  BORRADOR — PENDIENTE DE FIRMA al 04/10/2026): no se redacta un mandato aparte. La condición de la
  Parte II, punto 2 («si antes cierra su unidad de E0»), se lee como el cierre de esa etapa (FRENO S0-2).
  La otra unidad de la Parte IV, el ingreso del bloque A con procedencia por página, sigue con mandato
  propio, a redactar.

- **15/10/2026 — la parte por punto de ri2_pm no entra en el grafo evaluado (decisión de la autora; hoja de ruta de la mesa, §101).**
  La Parte II, punto 3 (`:57`), dice que sus 25 unidades por punto «entran con la tanda 3». La autora decidió que quedan fuera del grafo
  evaluado y van con el bloque B, en la release posterior, declaradas. El acta de S1-bis la sacó entera de esa lectura y dejó su vía por
  punto pendiente de una lectura propia «antes de la release que lo incluya»
  (`data/experiment/segmentacion_oficial_e0r2/s1bis/acta_sorteo_S1bis.md:22-24`), y esa lectura no entra en el calendario hacia B6.3. La
  E0 corregida le da 37 unidades a ri2_pm (manifiesto de S0-6b, `unidades_por_to`). El texto firmado no cambia.
