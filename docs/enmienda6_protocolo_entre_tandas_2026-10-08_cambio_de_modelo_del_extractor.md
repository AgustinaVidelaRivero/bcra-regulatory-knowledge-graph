# Enmienda 6 al protocolo entre tandas — el cambio de modelo del extractor entra por el procedimiento (c), y el grafo sale de un solo modelo

**FIRMADA por la autora el 08/10/2026** (firma por mensaje de la autora; versión para firmar en `08ccdfa`, redactada por la mesa el mismo día
sobre la decisión de la autora), con su decisión 1 al firmar. Rige desde esta firma.

Enmienda con fecha al protocolo entre tandas (`docs/protocolo_entre_tandas.md`, FIRMADO en `a304b89`; texto firmado: las primeras 398
líneas, sha256 `b23d37c5396a…`). El protocolo no se edita: esta enmienda vive al lado y se lee junto con él y con las enmiendas
anteriores (la de la cola humana, `8d01b04`; la 2, `0b98045`; la 3, `0cb0c70` y `bd77541`; la 4, firmada en `53bbd6f`; la 5, firmada el
06/10/2026).

## 0. Qué enmienda y por qué

- **Lo que dice el protocolo.** El §6 fija la regla (a), sin cambios de prefijo, de esquema ni de formato de salida hasta después de B6.3,
  con el procedimiento (c) para un hallazgo grave (decisión D1 del 03/10/2026). El §6 no nombra el modelo del extractor.
- **El modelo es un cambio de clase «todo».** El modelo del request base de E1 está en la clave de la caché: cambiarlo vuelve a pagar E1
  y E3 de todas las unidades (`data/experiment/mantenimiento/tabla_reprocesamiento.md`, fila F08). El pedido de los modelos nuevos
  tampoco es el mismo: no aceptan la `temperature` fijada ni el `tool_choice` forzado del perfil r2b, y su pensamiento no siempre se
  apaga (filas F08c y F08e; C0 de U-COMP-E1, `data/experiment/comp_e1/freno_c0.md`, y `docs/insumos_escritura.md` §8).
- **Lo que ya está decidido.** U-COMP-E1 cerró sin que ningún brazo cumpliera el criterio sellado, y el modelo del extractor no cambia
  antes de la tanda 1 (decisión de la autora del 08/10/2026; `docs/insumos_escritura.md` §7, ítem 7). El plan deja el cambio de modelo
  como una de las palancas del punto de diagnóstico posterior a A2.2 (`docs/plan_tesis.md`, fila A2.2, nota del 08/10/2026), y Opus como
  candidato para la release del grafo corregido (fila B6.4).
- **Por qué una enmienda.** Sin regla escrita, un cambio de modelo durante el escalado no tiene camino: no es un hallazgo grave con el
  umbral del §6 (c), y la regla (a) no lo nombra. Decidir de antemano cuándo puede entrar y con qué condición cambia un texto firmado, y
  va por enmienda, no por nota.

## 1. Qué decide

1. **El cambio de modelo del extractor durante el escalado entra solo por el procedimiento (c) del §6**, con el disparador de esta
   enmienda en lugar del umbral de gravedad: el punto de diagnóstico posterior a A2.2. Se activa si en A2.2 el grafo pierde contra el RAG
   (en el global o en los tipos de pregunta donde debería ayudar) y el análisis de fallas por capa atribuye las preguntas perdidas al
   contenido del grafo, en la parte que depende del modelo del extractor. Ninguna otra vía lo abre.
2. **Condición: si el modelo cambia, se re-extrae todo lo anterior.** El grafo evaluado sale de un solo modelo: todas las unidades
   extraídas hasta ese momento (las tandas cerradas y la que esté en curso) pasan E1 y E3 de nuevo con el modelo nuevo (clase «todo»,
   F08), antes de sellar el grafo evaluado. Nunca un grafo evaluado con documentos extraídos por dos modelos.
3. **Qué se aplica del procedimiento (c).** Los pasos 2 a 4, con estas precisiones:
   - la decisión es de la autora, por enmienda fechada al laudo de la release del pipeline (`docs/laudo_release_r2*.md`) y al pre-registro
     de la tanda en curso; sin esa enmienda, rige la regla (a) y el modelo no cambia;
   - laudo propio del cambio, con el pedido adaptado declarado, una prueba pareada con tope y el criterio escrito antes de correr;
   - la re-extracción de todo lo extraído, con tope fijado en el laudo: unidades acumuladas por la tarifa medida del modelo nuevo (para
     Opus, la de C1 de U-COMP-E1: USD 0,0564 a 0,0587 por unidad en E1 sobre las 87 unidades de la comparación, que son 1,78 veces la
     media de la tanda 0; `docs/insumos_escritura.md` §8); el número para decidir lo prepara la mesa con las cifras reales al llegar el
     punto de diagnóstico (plan, fila A2.2);
   - salen de B6.3 (a) los TOs cuya lectura informó el cambio, como dice el paso 3; el diagnóstico de A2.2 trabaja sobre las trazas del
     conjunto de desarrollo, y las 87 unidades de U-COMP-E1 son de la tanda 0, que ya está fuera de B6.3 (a) (checklist Q10);
   - el pre-registro de B6.3 no se sella hasta cerrar ese ciclo; sellado, nada de esto aplica (paso 4; laudo congelado §7).
4. **Qué hay que volver a calibrar o medir** si el modelo cambia, como mínimo:
   - el pedido de E1 (filas F08, F08c y F08e) y el prompt, que se ajustó sobre Haiku (U-PROMPT-R2);
   - las claves de la caché y su selftest (`selftest_clave_cache`), con la clase «todo» declarada;
   - el criterio y la tasa de reintentos del verificador E3, medidos sobre salidas de Haiku (U-E3-LISTAS, O3 a O5);
   - las lecturas de control de las tandas re-extraídas (las de T4 y L2 de la tanda 0, o su equivalente) y las cifras selladas de los grafos
     evaluados de cada tanda;
   - el gate de la release y sus casos de desviación de fidelidad del modelo;
   - el pre-registro de la tanda en curso y su tarifa.

## 2. Lo que no cambia

La regla (a) del §6 para prompt, esquema y formato de salida; el procedimiento (c) para un hallazgo grave, con su umbral; el principio 9
del plan (el grafo evaluado se sella y no se corrige). La decisión de no cambiar de modelo antes de la tanda 1 sigue en pie.

## 3. Decisiones que la autora toma al firmar

1. **Si un retiro anunciado del modelo entra por esta misma vía.** `claude-haiku-4-5-20251001` está activo, con retiro «no antes del 15
   de octubre de 2026», y la documentación oficial promete al menos 60 días de aviso antes de retirar un modelo publicado (página de
   deprecaciones, https://platform.claude.com/docs/en/about-claude/model-deprecations, consultada el 08/10/2026). Un retiro obligaría a
   cambiar de modelo sin pasar por el diagnóstico. Opciones: (i) el retiro entra por el procedimiento (c) con la misma condición de
   re-extraer todo, y el reemplazo se elige con la prueba pareada; (ii) se decide caso por caso. **Recomendación de la mesa: (i)**, con la
   vigilancia de la página de deprecaciones antes de cada tanda (hoja de ruta de la mesa) y el aviso registrado en el pre-registro de la
   tanda que lo reciba.
2. **Si E3 cambia de modelo junto con E1.** E3 corre con `claude-sonnet-5` (`data/experiment/reextraccion_v2/e3_verificador/runner_faseB_e3_enm01.py:40`).
   **Recomendación de la mesa:** no, salvo que el diagnóstico atribuya preguntas perdidas a la verificación; un cambio de E3 es otra
   decisión, con su propia prueba.
3. **El criterio de la prueba pareada del modelo nuevo.** Opciones: el de U-COMP-E1 (Condicion con su relación y omisiones normativas,
   límite inferior de Wilson ≥ 0,75 en la peor de dos corridas), o uno escrito para el defecto que señale el diagnóstico. **Recomendación
   de la mesa:** el segundo, escrito antes de correr, con el de U-COMP-E1 informado al lado.

**Decididas al firmar (08/10/2026):**
1. **El retiro anunciado del modelo entra por esta misma vía: opción (i).** Un retiro de `claude-haiku-4-5` entra por el
   procedimiento (c) con la misma condición de re-extraer todo, y el reemplazo se elige con la prueba pareada; la vigilancia de la página
   de deprecaciones va antes de cada tanda y el aviso se registra en el pre-registro de la tanda que lo reciba.
2. y 3. **PENDIENTES**: no se tomaron al firmar; se deciden si el procedimiento se activa.

## Firma

FIRMADA por la autora el 08/10/2026 (versión para firmar en `08ccdfa`), con la decisión 1 en la opción (i) y las decisiones 2 y 3
PENDIENTES. Rige desde esta firma.
