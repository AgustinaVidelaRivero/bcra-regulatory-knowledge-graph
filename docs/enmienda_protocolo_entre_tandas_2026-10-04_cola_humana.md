# Enmienda al protocolo entre tandas — lectura de la cola humana al cierre de cada tanda

**FIRMADA por la autora el 04/10/2026.**

Enmienda con fecha al protocolo entre tandas (`docs/protocolo_entre_tandas.md`, FIRMADO en `a304b89`; texto
firmado: las primeras 398 líneas, sha256 `b23d37c5396a…`). El protocolo no se edita: esta enmienda vive al lado
y se lee junto con él. Reemplaza la nota del 04/10/2026 al §1 («muestra de la cola humana al cierre de cada
tanda», asentada en `4f3bcff`), que queda sin efecto.

## 0. Qué enmienda y por qué

- **Lo que dice el protocolo.** El §1 enumera qué se mide al cerrar cada tanda (`:38-69`), y su punto 3 fija
  las lecturas asistidas por muestra (`:58-64`). No dice nada de las unidades que E3 no terminó.
- **Lo que hace el pipeline.** Esas unidades, la cola humana, entran al grafo marcadas (`cola_humana` y
  `estado_e3`; `docs/plan_tesis.md:363`). En la tanda 0 son 71: 35 con el ratchet agotado y 36 con el
  veredicto inutilizable (`data/experiment/reextraccion_v2/corpus_tanda0/salida/*/finales.jsonl`, campo
  `estado`). En KG-Tanda0-Diez-r2a llevan la marca 291 nodos y 466 aristas.
- **Por qué una enmienda.** Agrega una obligación de cada cierre y una regla con umbral a un texto firmado.

## 1. Qué decide

1. **Lectura al cierre de cada tanda.** Se suma a las lecturas del §1, punto 3.
2. **Cuántas unidades se leen.** Si la cola humana de la tanda tiene más de 30 unidades, se sortean 30, con
   la semilla declarada antes de leer. Si tiene 30 o menos, se leen todas.
3. **Quién lee.** Lectura asistida con revisión de la autora (decisión D2, §10, `:371`), contra el texto de la unidad.
4. **Unidad con error.** Una unidad con al menos un nodo o una relación que el texto de la unidad no
   sostiene. Las omisiones se reportan aparte y no cuentan como error para esta regla. La definición queda
   fijada con esta firma, antes de la primera lectura.
5. **Reporte, con la tanda.** Las unidades con error sobre las leídas y las omisiones, aparte. Con muestra,
   además, el intervalo de Wilson al 95 % de la tasa de error.
6. **Regla, fijada de antemano.**
   - Con muestra (30 leídas de una cola mayor): se dispara si el límite superior de Wilson al 95 % de la tasa
     de error supera el 25 %.
   - Con la cola entera leída (30 unidades o menos): se dispara si la tasa de error observada supera el 10 %.

   Si se dispara, las unidades de la cola humana de esa tanda se re-procesan o salen del grafo evaluado de
   esa tanda, y se reporta cuál de las dos y por qué.

## 2. Aritmética de la regla

- **Con muestra.** Con 30 leídas, el límite superior de Wilson es 11,4 % con 0 errores, 16,7 % con 1, 21,3 %
  con 2 y 25,6 % con 3: la regla tolera hasta 2 errores. Comando:

  ```
  .venv/bin/python -B -c "from math import sqrt;z=1.959964;[print(k,round(100*((k/30+z*z/60)/(1+z*z/30)+z*sqrt(k/30*(1-k/30)/30+z*z/3600)/(1+z*z/30)),1)) for k in range(4)]"
  ```

- **Con la cola entera.** «Supera» es estrictamente mayor: una tasa de 10 % justo no dispara la regla. Tolera
  3 errores con 30 unidades, 2 con 20 a 29, 1 con 10 a 19 y ninguno con menos de 10.

## 3. Qué no cambia

- El texto del protocolo y sus demás notas.
- La marca de la cola humana en el grafo y la decisión D2.
- Las otras lecturas del §1, punto 3.

## Firma

FIRMADA por la autora el 04/10/2026. Rige desde esta firma.

## Notas posteriores a la firma

El texto firmado no se edita (59 líneas, sha256 `b9c2e7fd039f…`, `8d01b04`); estas notas se leen junto con él.

- **04/10/2026 — la regla rige también para la cola de U-REEXT-T0 (decisión de la autora).** La lectura del
  §1 se hace también sobre la cola humana del grafo de U-REEXT-T0, la tanda 0 re-extraída, con la misma
  regla y los mismos umbrales. Es la primera medición, antes de la tanda 1. Queda registrado en la fila de
  esa unidad (`docs/plan_tesis.md:400`).
