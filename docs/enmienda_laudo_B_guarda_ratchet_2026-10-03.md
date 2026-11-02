# Enmienda a LAUDO B — la guarda de bloques ordenadores cubre cualquier faltante que cite la cláusula ordenadora

**FIRMADA por la autora el 03/10/2026.**

Enmienda con fecha a LAUDO B, uno de los dos laudos posteriores a la mini-recalibración del 11/08/2026.
El único texto de LAUDO B en el repo es el docstring de
`data/experiment/reextraccion_v2/e3_verificador/ratchet_e3.py` (`:44-53`; último commit que toca el archivo,
`924ef4d`; sha256 del archivo en `28e06fb`, `e683f547…`). Lo implementa `_guardia_estructural` (`:102-118`).
El prompt del verificador E3 está sellado y esta enmienda no lo toca: cambia solo la capa determinística.

## 1. Lo que dice LAUDO B hoy

En un mini-chunk cuyo texto cierra abriendo una enumeración (la última línea no vacía termina en «:») y
cuya unidad de origen tiene descendientes en el corpus, un faltante de tipo `enumeracion_incompleta` cuya
cita verificada es esa cláusula ordenadora se marca `estructural_no_bloqueante` y no bloquea. La razón: los
ítems de la enumeración son los puntos hijos, que el mini-chunk no ve por diseño. Sin el conjunto de
unidades del corpus la guarda no se aplica: falla hacia bloquear, nunca hacia aceptar de más.

## 2. Qué decide esta enmienda

1. **Ampliación.** La guarda cubre cualquier faltante cuya cita verificada sea la cláusula ordenadora,
   sea cual sea su tipo. Deja de exigir `enumeracion_incompleta`.
2. **Salvaguarda.** La ampliación se aplica solo si la extracción verificada de la unidad quedó sin
   Obligacion, Restriccion ni Potestad.
3. **Lo que no cambia de la guarda.** Mini-chunk que abre una enumeración; unidad de origen con
   descendientes en el corpus; cita verificada, terminada en «:» y contenida en el bloque. Sin el conjunto
   de unidades del corpus, no se aplica.
4. **Efecto.** El faltante eximido se marca `estructural_no_bloqueante`, queda en el veredicto como
   residual declarado y no dispara reintento.
5. **Alcance.** Rige para la forma de salida «r2» (perfil del prefijo nuevo, U-PROMPT-R2). Los perfiles
   existentes siguen con LAUDO B tal como está, y sus resultados sellados se reproducen byte a byte.
6. **Registro.** El reporte de U-REEXT-T0 lista cada unidad eximida por la ampliación, para su lectura.

## 3. Justificación técnica

- **El prefijo nuevo deja vacía la unidad del encabezado.** Con la regla del encabezado de lista, la
  unidad del encabezado no emite un nodo por el solo anuncio: el sujeto, la modalidad y el cuantificador
  se componen en cada inciso (`docs/mandatos/UPROMPT_R2_prefijo_nuevo.md`, notas del 03/10/2026).
- **E3 reclama ese vacío, y el reintento crea el nodo.** En la tanda 0, de los 212 mini-chunks que abren
  una lista, E1 dejó 9 sin contenido en la primera pasada. E3 bloqueó 6, todos con un faltante `otro` de
  severidad alta; 5 quedaron aceptados tras el reintento, con nodos, y 1 fue a cola humana. En
  `ctacte::8.3::intro`, `ctacte::8.4::intro` y `ctacte::6.4.7::intro` el reintento creó una Obligacion de
  solo anuncio (`BKL-0035` y `BKL-0039`). LAUDO B no eximió esos faltantes porque su tipo no es
  `enumeracion_incompleta`.
- **Sin la salvaguarda, la ampliación acepta de más.** En la verificación inicial de la tanda 0 hubo 32
  encabezados de lista con algún faltante bloqueante (33 faltantes: 22 `otro`, 4
  `contenido_tabular_no_declarado`, 3 `excepcion_ausente`, 2 `enumeracion_incompleta` y 2
  `calificador_despojado`). En 23 la cita verificada es la cláusula ordenadora (17, 4 y 2 de los tres
  primeros tipos). La ampliación sin salvaguarda habría desbloqueado 22 de los 32, entre ellos
  `ext::9.3.3::intro`, cuyo reclamo es legítimo: falta una restricción propia del encabezado.
- **Con la salvaguarda desbloquea 5.** Son `ctacte::6.4.7::intro`, `ctacte::8.3::intro`,
  `ctacte::8.4::intro`, `ext::4.8.6::intro` y `lingob::6.2.4::intro`. `ext::9.3.3::intro` sigue
  bloqueando, porque su extracción tenía Obligacion y Potestad. De los cinco, cuatro son anuncios;
  `ext::4.8.6::intro` trae una condición propia, que con la composición aprobada va en los incisos.
- **Fuentes.** `data/experiment/reextraccion_v2/corpus_tanda0/salida/<to>/veredictos.jsonl`,
  `extracciones_e1.jsonl` y `extracciones_finales_<to>.jsonl` (`ad6d5ad`). El recuento sale de
  `data/experiment/prompt_r2/p1/encabezados_lista.py` (`guarda_ampliada_tanda0`) y se recomputó de forma
  independiente en la revisión, con las funciones del propio ratchet.

## 4. Límites declarados

- La salvaguarda mira los tipos extraídos, no el texto: si un encabezado con contenido propio queda sin
  norma y ese contenido no es de los que se componen en los incisos, la ampliación exime un reclamo
  legítimo. Por eso cada unidad eximida se lista y se lee (§2, punto 6).
- La ampliación no cubre la cita que empieza en la línea de título de la unidad, fuera del bloque. En la
  tanda 0 son 2 de los 6 bloqueos (`ctacte::1.5.4::intro` y `ctacte::3.2.1::intro`), y en los dos el
  encabezado tenía contenido propio: siguen bloqueando.
- Su efecto sobre el prefijo nuevo no está medido: se mide en la pata de E3 de la pareada de U-PROMPT-R2
  y en U-REEXT-T0.

## 5. Qué no cambia

- El prompt de E3, su prefijo y su candado.
- LAUDO A (solo los faltantes de severidad alta bloquean).
- LAUDO B para los perfiles existentes, y los resultados sellados de la tanda 0.
- La condición de cierre de `BKL-0035` y de `BKL-0039`, que se mide sobre la extracción final de
  U-REEXT-T0, después de E3 (`docs/plan_tesis.md:400`).

## 6. Implementación

En U-PROMPT-R2, P2: `e3_verificador/ratchet_e3.py` y `selftest_e3.py`, escrituras autorizadas por la nota
del 03/10/2026 al pie de su mandato. Esta enmienda fija la regla; no modifica código.

## Firma

FIRMADA por la autora el 03/10/2026.
