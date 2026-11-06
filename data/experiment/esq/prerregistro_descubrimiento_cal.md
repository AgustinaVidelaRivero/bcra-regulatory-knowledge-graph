# Pre-registro — U-ESQ-2-cal · Control del instrumento de descubrimiento (modo ii)

**Estado: FIRMADO — Agustina Videla Rivero, 31/08/2026. Sellado por el commit
que lo contiene; la calibración no corre sin este sello previo.** Este es un **pre-registro nuevo**, no una adenda a `38be6e5`:
instrumento nuevo, examen nuevo. El pre-registro de ESQ-1 (`38be6e5`) queda
**FALSADO-CERRADO** en su modo (i): la escalera de tres controles sellados
(P1 — commit de U-ESQ-1c; P1′ — `c25273f`; P1″ — `0e50e3d`) demostró que el
canal declarativo es inviable con este modelo y este prompt, y su adenda
final (`6cb0121` §5.c) prohíbe el tercer retoque. P2–P5 nunca corrieron y
quedan sin leer; la demostración de la escalera es el resultado.

## 1. Qué se controla y por qué

**Decisión de la autora que este pre-registro implementa**: antes de escalar
se busca el problema de la mejor manera posible, y "la mejor manera" exige
**calibrar antes de censar** — la lección de la escalera. El instrumento
nuevo es el **descubrimiento como tarea principal** (modo (ii) de U-ESQ-0,
revivido): una llamada separada por unidad que pregunta qué contenido
normativo del chunk **no encaja** en el esquema — sin extracción
entrelazada, sin lenguaje de cierre, sin la pulsión de conformidad que la
escalera documentó. Antes de censar nada con él, se calibra contra la vara
ya existente.

## 2. La vara (sellada, cero cambios)

- **Brazo A′ — las 10 unidades dopadas de `c25273f`** (fixtures
  `dopadas_p1bis.json`, verificados por sha; aprobación de la autora
  vigente): 5 con concepto que exige tipo nuevo, 5 con relación que exige
  predicado nuevo. Ni una cláusula se toca.
- **Brazo C — las 10 unidades limpias** del control original.
- Las dopadas siguen siendo material de instrumento: fuera de todo censo,
  del corpus y del archivo de exclusión.

## 3. El instrumento (la variable de esta unidad)

El prompt de descubrimiento es **la variable**: su texto completo y su
formato de salida se presentan a la autora en el freno del mandato ANTES de
gastar, y quedan congelados en el manifiesto aprobado. Reglas duras que el
pre-registro fija desde ya:

- La tarea es identificar y describir contenido que no encaja; **no** se le
  pide extraer, tipar contra el catálogo, ni proponer nombres — describe el
  contenido y por qué no encaja.
- El prompt puede describir el esquema (los 6 tipos y los 12 predicados: sin
  eso la pregunta no tiene referencia), pero **no incluye ningún ejemplo de
  contenido fuera de esquema** ni ninguna cadena de las cláusulas plantadas
  (no sembrar — verificado mecánicamente por selftest).
- Instrumento separado del pipeline: **no toca `prompt_e1.py` ni ningún
  módulo de producción**; vive en `data/experiment/esq/code/` con caché y
  namespace propios.

## 4. Predicción sellada (P-cal) y regla de conteo

**P-cal: el descubrimiento detecta el contenido plantado y no inventa sobre
las limpias.**
A′: **≥7 de 10 en total, y ≥3 de 5 en cada mitad**. C: **≤1 de 10** con
detecciones espurias.

**Regla de conteo (sellada; la adjudicación es de la autora, fila por fila,
con esta regla):** una detección VALE si el reporte de descubrimiento de esa
unidad identifica el contenido de su cláusula plantada — la materia de la
cláusula, no un nombre de tipo ni una cadena exacta. **Ante la duda, NO
cuenta**: el sesgo apunta contra el resultado que revive el censo. En C, es
espuria toda detección que señale como fuera-de-esquema contenido que el
esquema sí captura. Cruces (la dopada de tipo detectada como problema de
relación o viceversa) se reportan aparte y no cuentan para su mitad.

*Falsada si:* cualquiera de los dos brazos no alcanza su umbral.

## 5. FINAL DE UN SOLO TIRO (sin escalera)

**Si el descubrimiento puro no detecta las dopadas, la vía del censo por LLM
queda CERRADA con este modelo** — sin segundo prompt de descubrimiento, sin
retoque, sin iteración. La escalera anterior cerró bien porque su final
estaba escrito antes de correr; esta calibración nace igual: un intento.

## 6. El árbol (sellado)

- **(a) P-cal PASA** → el censo modo (ii) se re-estima bajo tarifas
  actuales, se laudan tope y diseño (laudo propio), y corre sobre el
  universo de ESQ-1 (los 10 documentos de `20260827`, disjuntos del subset).
  ESQ-2 protocolizada queda como **complemento**: mide la deformación
  semántica, fenómeno confirmado que el censo NO mide.
- **(b) P-cal FALLA** → **ESQ-2 protocolizada es la única vía**, con el
  resultado negativo más fuerte posible como fundamento (ni el canal
  declarativo ni el descubrimiento puro funcionan con este modelo).
- **En ambas ramas**: ESQ-3 decide los retoques del esquema con todo el
  material (censo si existe, ESQ-2, las tres falsaciones, la deformación y
  su inestabilidad), y **recién ahí se escala**.

## 7. Presupuesto

Tope parcial **USD 0,50** (referencia ~0,2 por las 20 unidades; estimación
anclada obligatoria antes de correr). D7 del censo: el número dormido
(global 6,52, sello `0e50e3d`) solo revive en la rama (a), re-estimado bajo
el instrumento nuevo.

## 8. Checkbox de implementación

- [ ] Manifiesto del prompt de descubrimiento aprobado por la autora ANTES
      del gasto (freno del mandato).
- [ ] Fixtures de dopadas verificados por sha contra `c25273f`; cláusulas no
      sembradas, verificado por selftest.
- [ ] Selftest completo en PASS antes del gasto.
- [ ] Corrida dentro del tope; cruce db==jsonl; producción intacta.
- [ ] Tabla de adjudicación entregada a la autora; conteo contra P-cal con
      la regla sellada; sub-conteos por mitad.
- [ ] Rama del árbol declarada en el cierre, con su consecuencia.

---
**Firma:** Agustina Videla Rivero · **Fecha:** 31/08/2026
