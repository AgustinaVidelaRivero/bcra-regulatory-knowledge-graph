# Enmienda 9 al protocolo entre tandas — el tramo 1 de la tanda final, sellado como respaldo

**FIRMADA por la autora el 17/10/2026 a las 09:07:58** (firma por mensaje de la autora; hoja de ruta de la mesa, §138), tal como estaba la
versión para firmar (sha256 `e7245b61…`, en el paquete de la mesa, `decisiones_137_mesa/para_firmar/`). Rige desde esta firma. La sella
`docs/sello_enmienda9_protocolo_entre_tandas_2026-10-17.txt`.

La redactó la mesa sobre las decisiones de la autora del 17/10/2026, recibidas a las 08:17:24 (hoja de ruta de la mesa, §137). Elige la
opción (c) de la §133 de la mesa (`decisiones_133_mesa/division/opcion_c_tramo_1_de_respaldo_mesa.md`) con tres decisiones.

Es una enmienda con fecha a:
- `docs/protocolo_entre_tandas.md` (FIRMADO en `a304b89`);
- su enmienda 5 (`ccd8fad`);
- su enmienda 8 (`54902301`).

Ninguno de los tres se edita. La acompaña una enmienda a la regla de caída, en un documento aparte
(`enmienda1_regla_de_caida_grafo_evaluado_2026-10-17_tramo_1.md`). La regla sellada no se toca.

## 0. Por qué

- **La tanda final corre en dos tramos** (registro de decisiones, §12):
  - el tramo 1, con 30 TOs y 601 unidades: los 24 regímenes informativos y los 6 NG con modo `sin_raiz`;
  - el control entre tramos;
  - el tramo 2, con 68 TOs y 4.350 unidades, todos NG `vigente` o `marcadores`.
- **La regla de caída sellada:** si la tanda final no está sellada el viernes 23/10/2026 a las 18:00, el grafo evaluado son las tandas 0 y 1.
  Con esa rama, los elegibles de O2 son 4 RI, 1 NG digerible y 2 NG «necesita reglas», y O2 no se cumple en ninguna clase
  (`decisiones_133_mesa/division/opcion_c_tramo_1_de_respaldo_mesa.md`, §4).
- **Con el tramo 1 sellado como respaldo,** la rama de caída pasa a 26, 1 y 6: O2 se cumple en RI y en «necesita reglas».
- **Lo que no cambia:** no se saca ninguna revisión entre tandas, lectura, verificación, control ni prueba en seco (enmienda 8, `:25` y
  `:112`).
  - El protocolo sella al cerrar una tanda, y la revisión es la condición para despachar la siguiente (`docs/protocolo_entre_tandas.md:130`,
    `:137-139`).
  - Entre los dos tramos no hay despacho: la revisión de la tanda 1 se hace completa antes de despachar la tanda final, como manda la
    enmienda 8 (`:40`).

## 1. Qué decide

1. **El tramo 1 se sella como respaldo**, mientras corre el tramo 2, con lo que pide el protocolo para el sello de una tanda (`:130-135`) y
   la enmienda 5 (`:27`, `:52`):
   - su E0;
   - el `kg.json` del tramo 1 solo y el del acumulado de las tandas 0 y 1 con el tramo 1, cada uno completo y sin cola;
   - los registros del ensamblado;
   - la suite y las shapes, que son su T3;
   - las lecturas de la cola y de las aceptadas de sus celdas (punto 2);
   - su columna del tablero y su costo, que son su T5.
   Se sella sin corregir (principio 9). La re-aplicación única del código (enmienda 8, R3) va después, sobre el acumulado, antes del sello
   del grafo evaluado.
2. **Las lecturas de la tanda final siguen siendo un solo juego** (enmienda 8, `:42`), con las celdas del pre-registro de la tanda 1
   (§5.4 bis, punto 2), leído en dos momentos:
   - **al cerrar el tramo 1,** la cola y las aceptadas de sus celdas: RI `sin_raiz`, RI resto y NG `sin_raiz`, 20 de cada muestra de 30.
     Las tres salen enteras del tramo 1;
   - **al cerrar el tramo 2,** las de NG resto, 10 de cada 30;
   - **las lecturas de elementos del grafo** (vigilancias (1), (2), (3) y (7), y la observación (12)) no se leen temprano. Se sortean, de
     todas las celdas, sobre el ensamblado de la tanda entera, como sin dividir. El ensamblado del tramo 1 solo no resuelve las remisiones
     a documentos del tramo 2;
   - **si se aplica la enmienda a la regla de caída,** las lecturas de elementos del grafo del tramo 1 se sortean sobre su acumulado
     sellado, antes del sello del grafo evaluado del sábado 24/10/2026.
3. **Los umbrales** (decisión de la autora, salida (ii) de la §133):
   - la atención propia de RI se calcula al cerrar el tramo 1, antes de leer: sus pesos son solo de RI;
   - la atención y el freno de cada estrato se calculan con los pesos reales, con el script sellado, al cerrar el tramo 2 y antes de leer
     NG resto. Se declara que se calculan después de leer las celdas del tramo 1. La fórmula está sellada antes, y los pesos son conteos,
     no lecturas: no queda ninguna elección después de ver datos.
4. **La cola entera.** Si al final la cola de la tanda tiene 30 unidades o menos, se lee entera (pre-registro de la tanda 1, `:642`).
   También se leen las del tramo 1 que no salieron en su sorteo.
5. **El commit del sello del tramo 1 puede correr con el lanzador vivo.** Es una excepción declarada a «una ejecutora por vez en el repo»,
   y vale solo con estas cinco condiciones (decisión de la autora):
   - toca solo las rutas del tramo 1, con `git add` de rutas explícitas;
   - los archivos de la raíz de la salida que cambian durante el tramo 2 no van al sello: `estado_corpus.json`,
     `presupuesto_compartido.json`, `ultimo_checkpoint.json` y `checkpoints/`. Va su copia tomada al cerrar el tramo 1;
   - el control de sha256 de las carpetas de salida del tramo 1 (punto 6) se toma antes y después del commit;
   - ninguna otra ejecutora trabaja en el repo;
   - el trabajo del tramo 1 mientras corre el tramo 2 (T3, T4 y T5) se hace sobre una copia de sus salidas, sin escribir en el repo, y
     entra por ese commit.
6. **El control del tramo 2 sobre las salidas del tramo 1:** el sha256 de las carpetas de salida de los 30 TOs del tramo 1 se toma al cerrar
   el tramo 1, antes y después del commit del sello, y al cerrar el tramo 2. Si cambia, frena y decide la autora.
7. **Depende del ensamblado de un subconjunto.** El sello existe solo si la corrida en seco de la tanda final prueba que se ensambla un
   subconjunto de documentos: la misma condición de T3 sobre el tramo 1 (registro, §12, 11d). Si no lo prueba, no hay sello del tramo 1.
   La lectura temprana de la cola y las aceptadas sigue, porque sale de `finales.jsonl` y no del ensamblado.
8. **Los `nombres_remision` de los dos ensamblados nuevos** siguen la regla de la §19 del registro: la raya entra en un ensamblado solo si su
   contraste contra los 157 títulos da 0 resoluciones distintas. Medidos por la mesa el 17/10/2026, sobre la E0 regenerada con el código
   del gate (150 de 150 archivos iguales a S0-6b; `decisiones_137_mesa/raya/`):
   - **el tramo 1 solo:** 309 menciones, 1 resuelta con la regla y con la raya, 0 distintas. La raya entra, sin cambiar ninguna
     resolución;
   - **las tandas 0 y 1 con el tramo 1:** 1.113 menciones. Con la regla, 429 resueltas y 0 distintas; con la raya, 455 resueltas y 23
     distintas. La raya no entra.

## 2. Lo que no cambia

- la revisión completa después de la tanda 1, antes del despacho;
- el control entre tramos, con sus bases (registro, §13);
- T3 sobre el tramo 1;
- un solo despacho;
- las lecturas a ciegas pre-registradas, los pisos y la regla de fijar todo antes de leer, salvo el momento de los umbrales del punto 3,
  declarado;
- el alcance congelado; el prompt, el esquema y los modelos;
- la regla de reemplazo de las preguntas de B6.3 (registro, §13);
- las enmiendas 5 y 8 y la regla de caída sellada.

## Firma

FIRMADA por la autora el 17/10/2026 a las 09:07:58 (por mensaje; hoja de ruta de la mesa, §138), tal como estaba. Rige desde esta firma. La
firmada cambia solo la cabecera y esta sección de la versión para firmar (sha256 `e7245b61…`). La mesa la selló con su sha256 y la hora:
`docs/sello_enmienda9_protocolo_entre_tandas_2026-10-17.txt`.
