# Laudo ESQ-1 — Diseño del test ciego de generalización del esquema

**Estado: FIRMADO — Agustina Videla Rivero, 27/08/2026**
Documento de análisis que este laudo resuelve: `data/experiment/esq/scoping_esq1.md`
(unidad U-ESQ-0, diagnóstico puro, USD 0).

## 1. Resoluciones

**D1 — Modo de extracción.** Se adopta el **modo (i)**: un pase con canal abierto
(`tipo_propuesto` y `predicado_propuesto`, calcados de `sujeto_propuesto`),
manteniendo los enums vigentes. Fundamento: sobre la misma corrida de desarrollo,
los canales cerrados reportaron 0 de 8.162 entidades y 2 de 11.827 relaciones fuera
de esquema —ambas variantes léxicas—, mientras el único canal abierto disparó 56
veces sobre 39 sujetos distintos. El corpus tiene contenido fuera de esquema y los
canales cerrados no pueden reportarlo. El mecanismo adoptado no es una apuesta: ya
está validado dentro de este pipeline. El modo (iii) queda descartado por evidencia
—el canal de rechazos está mudo— y el modo (ii) por duplicar a ESQ-2 a mayor costo.

**D2 — Control de instrumento.** Obligatorio y previo a ESQ-1: 40 unidades ya
pagadas donde el extractor declaró por escrito lo que dejó afuera
(`omisiones_no_prosa`). Sin control aprobado, ningún resultado de ESQ-1 es
admisible, ni cero ni distinto de cero.

**D3 — Universo de selección.** `escalado_prep/` (152 TOs con manifiesto, hashes y
chunks de E0 calculados), **no** `data/raw`. El plan indicaba `data/raw`; mandan los
archivos: allí hay 3.171 PDFs cuyos nombres no cruzan contra el inventario y 62 de
152 TOs producen cero unidades, de modo que un sorteo uniforme daría documentos
vacíos y un cero nulo por la razón equivocada. Se declara la corrección al plan.

**D4 — Regla de selección y semilla.** Sorteo estratificado por cuartiles con semilla
**20260827**. ESQ-1: ayccef, expaef, opefci, adrei, cryl, actgar, prevmi, lavdin,
traval, ctacor (762 unidades, 254 páginas). ESQ-2: ctacte, depinv, lingob, rrci,
polcre, gescre, pagjub, retype, docvig, snp_atm. Disjuntos entre sí y del subset,
verificado, los 20 con sha256. Los IDs de los 20 van al archivo de exclusión que
exige el plan, y quedan fuera del eval set de la evaluación final.

**D5 — Baseline.** Se adopta la **lectura absoluta** (opción b), con el canal de
sujetos en cuarentena. Fundamento: el 83,2 % de las relaciones de sujeto del conjunto
de desarrollo pasa por el atajo del rol, que no estará presente en los 20 documentos,
de modo que la tasa de desarrollo no es comparable. Parametrizar el rol se descarta
por circular: obligaría a forzar la entrada más parecida del catálogo —lo que el
prompt prohíbe y que suprimiría la señal que ESQ-1 busca— o a crear una clase nueva,
que es retocar el esquema antes del test que debe informarlo. Se incorpora el **brazo
D**: 20 unidades de desarrollo re-corridas con el rol suprimido, como referencia
pareada del único canal contaminado.

**D6 — Tope autorizado.** **USD 9,00.** Presupuesto esperado 6,38 (control 0,32 +
brazo D 0,16 + corrida 5,91), cota alta 7,14. La tarifa del modo abierto incluye un
recargo **supuesto**, no medido, declarado como tal y factorizado; su sensibilidad no
altera la elección de modo en ninguna banda. La referencia de USD 15–20 del plan no
se sostiene como estimación y queda como tope holgado.

**D7 — Re-presupuesto con dato (7bis).** El control de D2 devuelve el recargo
**medido** del modo abierto. La corrida de ESQ-1 se re-presupuesta con ese dato antes
de ejecutarse, y el supuesto se retira del documento.

**D8 — Firmas inválidas.** Los 304 `firma_invalida` entran como insumo de ESQ-3, con
prioridad al subconjunto de 196 (64 %) que es el mismo pedido: ampliar el dominio de
`aplica_a` a Operacion/Excepcion.

**D9 — Bandas de lectura y regla de normalización.** Se adoptan las bandas de lectura
de §7.4 y la regla de normalización de §7.5 del documento de scoping, y **se sellan
en un mismo acto**: sellar los umbrales sin la regla dejaría el pre-registro abierto
por el lado de la medición, porque quien normalizara después de ver los resultados
podría mover el conteo a través de un corte sin tocar el umbral.

La normalización la ejecuta la autora, sobre la lista deduplicada de cadenas
distintas, sin frecuencias, sin documento de origen y sin spread; el mapeo se sella
antes de computar un solo conteo. Se acepta el sesgo deliberado de la regla: lo que
ninguna regla alcanza cae en familia nueva, y está prohibido fusionar familias nuevas
durante el conteo aunque la sinonimia sea evidente. Ambos sesgos apuntan en contra
del resultado cómodo, de modo que la regla no puede fabricar un veredicto de «el
esquema generaliza».

Las bandas quedan marcadas como **no calibradas**: no existe corrida previa de
esquema abierto en este repositorio de la cual derivar los cortes. Su virtud es ser
anteriores y auditables, no óptimas.

Se agrega una regla de lectura no prevista en el scoping: **un resultado en banda A
obliga a revisar el instrumento antes de aceptarlo**. Si el resultado indica que el
esquema generaliza, contra la evidencia del canal de sujetos del conjunto de
desarrollo, la primera hipótesis es una falla del instrumento, no una virtud del
esquema. Se deja escrito acá porque después de conocer el resultado esta cautela ya
no sería creíble.

**D10 — Alcance del esquema y régimen informativo.**

*Hecho constatado.* Ninguno de los 53 Textos Ordenados de régimen informativo es
digerible por el pipeline vigente: no producen unidades de extracción, de modo que
ESQ-1 y ESQ-2 no pueden alcanzarlos. La causa no es el esquema sino la estructura
tabular de esos documentos, que la etapa E0 no procesa. «No testeado» no equivale a
«fallido»: el esquema no fue evaluado en esa familia.

*Dirección de la autora.* El objetivo es **validar el esquema sobre el corpus
completo**, no sobre una de sus dos familias. Un test de generalización que cubre
únicamente la familia donde el esquema tiene más probabilidad de funcionar, y que
omite justamente la más difícil, está sesgado hacia el resultado cómodo, y esa es una
objeción legítima en una tesis cuyo aporte es metodológico. La intención declarada
es, por lo tanto, construir el módulo de extracción tabular (B5.6) y someter el
régimen informativo al mismo ciclo de validación de esquema que la normativa general.

*Lo que este laudo NO compromete.* La ejecución de esa dirección queda **condicionada
al scoping de B5.6**, que se despacha como unidad de diagnóstico de costo cero:
cuántos de los 53 TOs tienen tablas parseables, qué unidad de extracción produce el
parser sobre una muestra, si esa unidad es compatible con el esquema vigente o exige
tratamiento propio, y cuánto trabajo es construir el módulo. Comprometer hoy la
construcción sin ese número sería fijar alcance sin respaldo.

*Decisión que no es de la autora.* Con el número del scoping en la mano, la elección
entre escalar una familia con validación completa o dos con el calendario que eso
implique **se lleva a los mentores**, porque modifica el alcance del corpus, que es
objeto de D5 del plan y toca compromisos declarados en el PPF. Se lleva ANTES de
laudar D5, no después.

*Mientras tanto.* ESQ-1 y ESQ-2 corren sobre normativa general en cualquiera de los
dos escenarios: esos 20 documentos deben testearse igual. Lo que queda en suspenso es
únicamente el momento de congelar el esquema (ESQ-3), que está más adelante en la
ruta crítica. Si B5.6 se construye y produce unidades sobre régimen informativo, esa
familia corre su propio ciclo ESQ **antes** de que el esquema se congele para ella.

## 2. Qué NO decide este laudo

- No autoriza ESQ-1: la corrida arranca recién con su pre-registro sellado, que
  incluye predicciones declaradas y los criterios de lectura ya firmados acá.
- No congela el esquema: eso es ESQ-3.
- No resuelve dónde vive el código de ESQ-1: eso se fija en el pre-registro.
- No modifica el principio 10: los 20 documentos pasan al conjunto de desarrollo a
  efectos del esquema y quedan excluidos de la evaluación final.

## 3. Consecuencias operativas — checkbox de implementación

- [ ] Pre-registro de ESQ-1 redactado y sellado por commit, con predicciones
      declaradas antes de correr y con los V3 reportados a ESQ-3 como categoría con
      nombre.
- [ ] `data/experiment/esq/documentos_excluidos_esq.json` creado con los IDs de los
      20 documentos y sus sha256.
- [ ] Control de instrumento ejecutado y aprobado ANTES de ESQ-1.
- [ ] Recargo re-presupuestado con el dato del control (D7).
- [ ] Scoping de B5.6 despachado y su resultado laudado.
- [ ] Frontera del régimen informativo llevada a mentores ANTES de laudar D5.
- [ ] Tope de USD 9,00 respetado; costo real registrado contra lo estimado.

---
**Firma:** Agustina Videla Rivero · **Fecha:** 27/08/2026