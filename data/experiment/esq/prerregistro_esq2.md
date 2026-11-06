# Pre-registro — ESQ-2 · Test de cobertura del esquema, protocolizado

**Estado: FIRMADO — Agustina Videla Rivero, 01/09/2026. Sellado por el commit
que lo contiene; la unidad no gasta sin este sello previo.** Laudo que lo gobierna: `docs/laudo_ESQ-2_diseno.md`. Vía única por la
rama (b) del árbol de U-ESQ-2-cal (`eadf4a5`, pre-registro `bca863f`): el censo
por LLM quedó cerrado con doble evidencia — extrayendo deforma (escalera
P1/P1′/P1″), descubriendo sobrecuenta (P-cal). ESQ-2 **mide, no testea**: no
hay bandas pasa/no-pasa; lo que se sella acá es el diseño de la medición, la
regla de adjudicación y el criterio de decisión de ESQ-3 — antes de leer nada.

## 1. Universo y extracción

- **Universo**: los 10 TOs del sorteo sellado de D4 para ESQ-1 (semilla
  20260827; universo laudado D3 = `escalado_prep/`): ayccef, expaef, opefci,
  adrei, cryl, actgar, prevmi, lavdin, traval, ctacor — 762 unidades, 254
  páginas. Corrección de D4 declarada en el laudo ESQ-2 §1.iii; los 10 de la
  lista original de ESQ-2 quedan vírgenes para la evaluación final.
- **Extracción**: **E1-solo**, runner propio de la unidad sobre los chunks de
  E0 de `escalado_prep/e0_dry/<to>/chunks_<to>.json`; modo cerrado, flag
  apagado; **sin el atajo del rol de alcance** (cuarentena de D5 heredada);
  caché y namespace propios; tope de la unidad **USD 6,50** (laudo §1.i), con
  estimación anclada previa y freno duro del runner. Modelo resuelto por
  llamada declarado en el reporte (precedente U-ESQ-2-cal).
- **Naturaleza declarada**: material de medición y desarrollo, **provisional
  pre-B5.4**. No es el arranque del escalado; «byte-idéntico a lo que
  escalaría» está retirado (laudo §1.ii).
- **Advertencia sellada — cota superior de omisiones**: la firma (f) se lee
  sobre extracción **sin verificador de completitud (E3)**: el conteo de
  omisiones es **COTA SUPERIOR** de las del pipeline completo, y ESQ-3 lo
  interpreta con E3 en mente. Las demás firmas no se afectan.
- **Registro obligatorio**: `data/experiment/esq/documentos_excluidos_esq.json`
  se crea con los 10 IDs y sus sha256; los 10 TOs pasan al conjunto de
  desarrollo a efectos del esquema y quedan excluidos de la evaluación final
  (nota de alcance del bloque ESQ, `docs/plan_tesis.md`, citada como regla).

## 2. Precondición: gate de paridad por caché

Antes de la corrida grande: **10 unidades del conjunto de desarrollo** (de los
5 TOs del subset), corridas con el runner de esta unidad en flag apagado
**contra el namespace de producción**. Criterio: **10/10 cache hits, 0 misses,
USD 0** — si las requests son byte-idénticas a las de producción, la caché las
devuelve gratis (never-pay-twice); un solo miss = el camino flag-off no es el
de producción y la corrida NO arranca. Además: la validación recomputada por
el validador vigente sobre esas 10 debe coincidir con la persistida en
producción. Motivo: `cliente_e1.py` y `validador_e1.py` fueron tocados por
U-ESQ-1b (solo rama abierta, según sus selftests); este gate verifica la
equivalencia funcional del camino completo, no solo del prompt.

## 3. Muestra de lectura: 75 fichas

- **Azarosa (38)**: estratificada por TO, asignación proporcional al número de
  unidades extraídas por TO con mínimo 2 por TO (redondeo determinístico
  declarado en el código); sorteo con semilla sellada **20260901**, generador
  nuevo por TO sobre ids ordenados (patrón de las unidades previas).
  **Generaliza**: sobre ella se computan frecuencias e intervalos de Wilson.
- **Dirigida (37)**: seleccionada por **disparadores mecánicos** computados
  sobre la extracción completa: (1) labels que nominalizan relaciones,
  (2) `properties.tipo = "otra"`, (3) entidades sin relaciones semánticas,
  (4) densidad anómala de entidades/relaciones por unidad. Si los candidatos
  exceden 37: ranking determinístico round-robin por disparador y orden por
  `chunk_id`; si faltan, el déficit se reasigna a la azarosa (declarado en el
  reporte). **No generaliza**: se reporta aparte, como búsqueda dirigida.
- **Exclusión de la cuarentena D5 (heredada)**: el vacío del rol de alcance
  (relaciones de sujeto sin atajo, `sujeto_propuesto` abundante) **no se ficha
  como hueco** y los disparadores lo excluyen explícitamente: no es señal del
  esquema sino condición conocida de esta extracción.
- **Checkpoint de ritmo**: tras la primera tanda (10–15 fichas) se mide el
  tiempo por ficha; si la proyección excede lo tolerable, **N se ajusta por
  laudo declarado** (recorte documentado, nunca silencioso).

## 4. Firmas buscadas (lista cerrada + residual)

(a) **re-tipado semántico** (contenido en caja errónea); (b) **nominalización
de relaciones** (relación sin firma posible convertida en entidad);
(c) **inconsistencia entre unidades del mismo contenido repetido** — **hallazgo
de lectura, NO disparador** (detectar repetición cross-unidad no es mecánico);
(d) **potestades/facultades** (familia confirmada en corpus real por
U-ESQ-2-cal); (e) **hechos con valor aplastados o perdidos** (hallazgo del
modelo de datos, `fe1fe36`); (f) **omisiones de contenido normativo** (cota
superior, §1); (g) **OTRO**, con descripción libre.

## 5. Instrumento y regla de adjudicación

- **Ficha pareada** texto-fuente vs extracción de la unidad (patrón de
  `adjudicar.py` de EV2, **copiado dentro del código de la unidad** — el
  instrumento es auto-contenido; `adjudicar.py` se versiona en un pase de
  higiene aparte). Tres preguntas por ficha:
  1. ¿El contenido normativo de la unidad está **representado**? (sí completo
     / parcial / no)
  2. Si hay **deformación**: ¿qué firma (a–g)? — con **cita textual del
     pasaje** + qué produjo la extracción + por qué no se representa sin
     deformar.
  3. Si hay **omisión**: ¿qué familia? (leída como cota superior).
- **Lectura de la autora en tandas de 10–15**, con las fichas en orden
  aleatorizado con semilla declarada.
- **DUDA como categoría propia, reportada aparte**: ni hallazgo ni descarte.
  Acá el resultado cómodo es «el esquema alcanza»; la duda no puede engordar
  ninguno de los dos lados.
- **Spot-check de mesa**: re-lectura independiente de una submuestra (10 de
  75, sorteo con semilla declarada); las discrepancias se reportan; la marca
  de la autora manda.

## 6. Resultado para ESQ-3 y criterio de decisión (sellado, NO CALIBRADO)

- **Salida**: tabla de familias/firmas con frecuencia n/N e **intervalo de
  Wilson al 95 %** sobre la muestra azarosa (exigencia 4 del mapa de related
  work — estreno de la práctica); la dirigida en tabla aparte, sin Wilson.
- **Alcance declarado de Wilson**: con n≈38 los intervalos son anchos — la
  azarosa dimensiona **magnitudes gruesas**, no diferencias finas; los
  estratos por TO son cobertura, no comparación por TO.
- **Criterio de decisión de ESQ-3** (se sella acá, antes de leer; declarado
  **NO CALIBRADO**, como D9 con sus bandas — su virtud es ser anterior y
  auditable, no óptima): una familia es **candidata a ampliación** si en la
  muestra azarosa aparece en **≥3 fichas**, o si aparece en **≥3 TOs
  distintos** contando ambas muestras; es **residuo documentado** si aparece
  en ≤2 fichas azarosas y ≤2 TOs. La muestra dirigida **corrobora pero nunca
  promueve por sí sola**. Las DUDAS no cuentan para ningún lado y se listan.
  ESQ-3 puede apartarse del criterio **solo con laudo que lo declare**.
- SIN bandas pasa/no-pasa: ESQ-2 mide; el que decide es ESQ-3, con este
  criterio más todo el material acumulado (escalera, calibración, deformación
  e inestabilidad, potestades, firmas de la cola, D8).

## 7. Artefactos de salida

Este pre-registro sellado · laudo ESQ-2 firmado · runner E1-cerrado propio con
caché/namespace propios · estimación anclada (json+md) · output del gate de
paridad · extracción completa persistida (jsonl por TO + resumen con modelo
resuelto, usage y gasto db==jsonl) · disparadores computados (json, con conteo
de candidatos por disparador) · `documentos_excluidos_esq.json` · las 75
fichas + la adjudicación de la autora (marcas verbatim) · registro del
spot-check de mesa · tabla de resultado (azarosa con Wilson / dirigida aparte)
· checkpoint de ritmo · sellos verbatim inicio/fin · gasto real contra
estimado.

---
**Firma:** Agustina Videla Rivero · **Fecha:** 01/09/2026
