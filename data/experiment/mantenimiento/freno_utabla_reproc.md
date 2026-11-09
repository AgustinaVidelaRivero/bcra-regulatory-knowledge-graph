# U-TABLA-REPROC — freno

Mandato: `docs/mandatos/UTABLA_REPROC_tabla_reprocesamiento_r2b.md`, FIRMADO por la autora el 04/10/2026
(`3a4b980`, sha256 `85df5030…`, igual en el árbol). USD 0, sin API y sin red.

## 1. FRENO intermedio (04/10/2026)

**Precondición.** Cumplida: P3b-2 de U-PROMPT-R2 en `c8c3970` y C2 de U-R2-CODIGO-2 en `9f6361e`, que es
HEAD al empezar.

**Fuentes firmadas, leídas en su commit, con su sha256:**
- protocolo entre tandas, `a304b89`: `b23d37c5…`. Es el mismo sha de las primeras 398 líneas del archivo
  actual, como fija la enmienda 2.
- enmienda 2, `0b98045`: `ba94398f…`, igual en el árbol.
- mandato de U-RERESOL-CAT, `f87ec4a`: sus 105 líneas firmadas dan `c8ee1382…`, igual en el árbol.
- tabla de reprocesamiento, `e18d616`: `0568e82e…`, igual en el árbol.

**Qué hice hasta acá.** En el repo, solo este archivo. En una copia del repo en el scratchpad, sin enlaces:
1. Corrí el selftest de M1 con el código de `9f6361e`. Su salida es idéntica byte a byte a la de `e18d616`:
   - anclaje de E1, 2.434 de 2.434;
   - anclaje de E3, 2.430 de 2.430;
   - las 25 variaciones del perfil sellado dan lo esperado;
   - contraste, OK.
2. Lo extendí al perfil r2b (borrador, todavía no copiado al repo).
   - Corre 40 variaciones, de `R00` a `R32`, sobre 13 unidades de `salida_tanda0_r2b/`. Las 40 dan lo que
     esperan.
   - La clave de E3 se arma con una salida sintética de E1 en la forma r2, validada con `validador_e1`.
   - Anclaje de r2b: NO_VERIFICABLE. La db de E1 no tiene ninguna clave en el namespace
     `e1-extractor-v1-p3817de475c93`, porque U-REEXT-T0 no corrió. Por eso rige, declarado, el anclaje del
     perfil sellado (decisión 3).
3. Controlé el repo antes y después con el sha256 de todos sus archivos (salvo `.git`). Ningún archivo
   existente cambió. Aparecieron tres archivos nuevos que no escribí:
   - `data/experiment/reresolucion_catalogo/r1_medicion.py` y `salidas/r1_medicion.json`: R1 de
     U-RERESOL-CAT, en curso y sin freno;
   - `data/experiment/prompt_r2/p4/apoyo_lectura_p4.py`.

**Contradicciones.** En las cuatro, la composición real de la clave dice que el texto firmado es el que está
mal. Por eso no lo toco. Para cada una propongo cómo queda la tabla, y la enmienda la decide la autora.

1. **F05** (páginas, id, sha256 y conteos de una unidad, sin cambio de texto).
   - Protocolo, `a304b89:82`: F05 va entre las filas que pagan E1 y E3 de las afectadas («texto o marcas de
     E0»).
   - Evidencia: R05 (páginas) y R06 (id, sha256 y conteos) no mueven ninguna clave de E1 ni de E3 con el perfil
     r2b. Con el sellado tampoco (V05 y V06). Ni el mensaje de E1 r2b (`prompt_r2b.py:342-388`) ni el de E3
     (`prompt_e3.py:317-349`) leen esos campos. Se rehacen E2 y el ensamblado, en código.
   - Propuesta: la tabla deja F05 en «solo código», con principio 12. En el protocolo, el rango de las afectadas
     pasaría a «F01 a F04 y F19». Ninguna unidad paga en las dos lecturas: cambian la clase y el principio
     declarados, no el costo.
2. **F10** (prompt de E3 o su modelo).
   - Protocolo, `:84-85`: en la clase «todo», «todas las unidades pagan E1 y E3».
   - Evidencia: R16 (texto de sistema de E3) y R17 (modelo de E3) mueven la clave de E3 de las 13 unidades de la
     muestra y ninguna de E1. Desde `924ef4d`, un cambio en los calibradores frena antes de armar el request
     (R22d: E1 no cambia y E3 frena; `prompt_e3.py:380-386`). E1 sale de la caché. Pagan E3 de todas las
     unidades y los reintentos de E1 del ratchet donde cambia el feedback.
   - La definición de la clase «todo» de la tabla le cabe a F10 («llaman a la API todas las unidades en al
     menos una de las dos etapas», `tabla_reprocesamiento.md:64-65`). Lo que no vale para F10 es «pagan E1 y
     E3».
   - Propuesta: F10 sigue en «todo», con «E3 de todas» en lo que se rehace.
3. **Catálogo** (enmienda 2, `0b98045:13-16`: el crecimiento del catálogo va con F13).
   - Con el código de hoy, un id nuevo en `catalogo_sujetos_r2.json` frena antes de armar ningún request (R22c,
     candado de `modelos_r2.py:61-96`).
   - Al re-sellar, el id entra al bloque del prefijo y al enum de `sujeto_id` (candados en `prompt_r2b.py:65` y
     `:68`). Eso mueve la clave de E1 de todas las unidades, con un namespace nuevo (R10 y R10b): es F11, clase
     «todo».
   - El lado que no toca el request no puede cambiar solo. R20 muestra que el armado no lee
     `indice_e4_r2.json`, pero ese archivo sale del mismo catálogo y su manifiesto frena el ensamblado
     (`r1_e4.py:522-541`).
   - Propuesta: F13 queda PENDIENTE de R1 de U-RERESOL-CAT (decisión 2 de la autora). Una fila nueva, F13b,
     registra lo de hoy: frena y, re-sellado, F11. La enmienda 2 describe lo que R1 tiene que construir, no el
     código de hoy. Queda a decisión de la autora si su §0 lleva fe de erratas ahora o al cerrar R1.
4. **F14** (validador). Hallada en esta unidad: no está en el mandato.
   - Protocolo, `:79-80`: «solo código (filas F13 a F16: validador, …)».
   - Con r2b hay dos validadores. `validador_e1` corre antes de E3, y su salida es el mensaje de E3 (R18: cambia
     la clave de E3, no la de E1). El ensamblado r2b deja entrar solo lo que vio E3 (`validador_r2.py:681-682`,
     `:997-999` y `:1214-1216`; los índices salen de la validación guardada, `runner_corpus.py:1041-1048`;
     P3 de U-PROMPT-R2, `4aa92c7`, posterior a la firma del protocolo).
   - Por eso un cambio en `validador_e1`, o en las correcciones de tipo y predicado que toma de `validador_r2`
     y de su política (`validador_e1.py:98-118`), no llega al grafo sin volver a correr E3 en las unidades
     cuya salida validada cambia.
   - Propuesta: F14 (`validador_e1`) pasa a «E1 y E3 de las afectadas», con E3 de esas unidades y E1 desde la
     caché. Una fila nueva, F14b (`validador_r2` en el ensamblado), queda en «solo código», que es lo que el
     protocolo dice de «validador» leído como el validador r2.

**Qué sigue con el «seguí».**
1. Con las resoluciones que decida la autora, escribo la tabla. Son las 21 filas revisadas y 17 nuevas:
   - tablas forzadas a residual y techos de los reintentos;
   - reintento por forma y candado del prefijo de E3;
   - crecimiento del catálogo hoy y validador r2;
   - umbrales, `remite_a`, sujetos por relación y unión de las operaciones;
   - versión del TextoOrdenado desde los pies y partición por corte;
   - recorte de la herencia, plantilla del mensaje de E1 (dos filas), NOTA de E3 y lazo de E3.
2. Copio el selftest al repo y lo corro sobre la copia, con el contraste.
3. Actualizo el §5 con la tarifa del prefijo nuevo (P1 `B_central` más los componentes de P3b-2,
   `costo_p3b2.json`).
4. Armo el FRENO final.

## 2. FRENO final (04/10/2026)

**Decisiones de la autora sobre el freno intermedio, aplicadas.**
1. F05, F10 y F14 quedan según la composición real de las claves, con F14b para `validador_r2`. Cada una lleva,
   en su celda de clase y en su nota, que difiere del texto firmado del protocolo entre tandas (`a304b89`) y que la
   enmienda al protocolo está en curso.
2. F13 queda PENDIENTE de R1 de U-RERESOL-CAT, y F13b registra lo de hoy: un id nuevo frena y, re-sellado, es F11.
   La fe de erratas de la enmienda 2 no es mía: queda PENDIENTE, a cargo de la mesa revisora.

**Escrituras.**
- `data/experiment/mantenimiento/tabla_reprocesamiento.md`, reescrita.
- `data/experiment/mantenimiento/code/selftest_clave_cache.py`: el borrador del freno intermedio, sin cambios.
- `data/experiment/mantenimiento/selftest_clave_cache.json`, la salida.
- Este freno.

Sin commit.

**La tabla nueva contra la de `e18d616`.** Pasa de 21 a 38 filas: 15 iguales, 6 cambiadas y 17 nuevas. La
comparación fila por fila está en el paquete (`lado_a_lado_tabla_e18d616_vs_UTABLA.md`).
- Iguales en claves, clase y principio: F01, F02, F03, F04, F05, F06, F07, F09, F10, F11, F15, F16, F17, F18b y
  F19. Su descripción y sus anclas pasan al código r2b, y F05 y F10 llevan la nota sobre el protocolo.
- Cambiadas:
  - F08: los techos de los reintentos pasan a F08b;
  - F11b: de un JSON a todos los insumos con candado, y E3 pasa a «frena»;
  - F12: `rol_por_to_r2.json`, con candado;
  - F13: de «solo código» a PENDIENTE;
  - F14: de «solo código» a «E1 y E3 de las afectadas», con principio 9;
  - F18a: más F16b si cambia el pie.
- Nuevas:
  - F04b, tablas forzadas a residual;
  - F08b, techos de los reintentos;
  - F08c, reintento por salida mal formada;
  - F10b, candado del prefijo de E3;
  - F13b, un id nuevo con el código de hoy;
  - F14b, validador r2;
  - F15b, umbrales;
  - F15c, `remite_a`;
  - F15d, sujetos por relación;
  - F15e, unión de las operaciones por punto;
  - F16b, metadato de los pies;
  - F20, partición por corte;
  - F21, recorte de la herencia de e0-r2;
  - F22 y F22b, plantilla del mensaje de E1 (línea en todo mensaje y línea condicional);
  - F23, NOTA de E3;
  - F24, lazo de E3.
- El §5 pasa a la tarifa del prefijo nuevo, estimada:
  - E1 USD 0,010544 y E3 USD 0,010333 por unidad: 0,020877 juntas;
  - U-REEXT-T0, USD 50,74 de estimación central y 71,04 con el factor 1,4;
  - fuentes: P1 `B_central` (`censo_p1.json`, `20b7f60`) más los componentes de P3b-2 (`costo_p3b2.json`, `c8c3970`),
    con el comando 1 de la tabla.

  La tarifa medida de la tanda 0 queda para el perfil sellado.

**Selftest.** Corrió sobre una copia del repo en el scratchpad, sin enlaces. Dos corridas dan el mismo JSON byte a
byte, y la salida copiada al repo tiene sha256 `f5cf44bb…`.
- Veredicto OK. Contraste con la tabla: OK en las 38 filas, sin discrepancias. Toda variación R tiene fila.
- Perfil sellado:
  - A1, 2.434 de 2.434; A3, 2.430 de 2.430;
  - V01 a V24, 25 de 25;
  - el bloque del perfil sellado de la salida (anclaje, variaciones, inventario, muestra e insumos) es igual al de
    `e18d616`.
- Perfil r2b:
  - R00 a R32, 40 de 40;
  - A1r y A3r, NO_VERIFICABLE: 0 claves en el namespace r2b, porque U-REEXT-T0 no corrió.
- Inventario: los procesos hijo reproducen las claves del padre en los dos perfiles, y ningún módulo de solo código
  se carga al armar. `validador_e1` y `validador_r2` se cargan solo al validar.
- Control del repo: entre antes y después de la corrida final, el único archivo que cambió es la salida del
  selftest, que copié yo. Ningún `.pyc` nuevo.

**Hallazgos.**
1. Tres insumos de los requests r2b no tienen candado ni entran al hash del prefijo: un cambio mueve claves sin que
   nada frene.
   - La lista de tablas forzadas a residual (F04b, R32).
   - Las líneas fijas del mensaje de E1 (F22 y F22b, R29b y R29). Una línea de todo mensaje hace pagar E1 de todas
     las unidades con el mismo namespace.
   - Las NOTAS del mensaje de E3 (F23, R30).
2. El namespace de E3 del perfil r2b es el de la tanda 0 (`p21a836c7de6d`): las claves de r2b se distinguen solo por
   el mensaje. El anclaje A3r exige que las claves calculadas estén en la db, no que sean las únicas.
3. El manifiesto r2b (`manifiestos/tanda0_10tos_r2b.json`) apunta todavía a `salida_tanda0_r2/`. El selftest usa
   `salida_tanda0_r2b/`, que es la que pasa al manifiesto en T1 de U-REEXT-T0, según el borrador de su mandato.

**Pendiente.**
- Correr de nuevo el selftest cuando existan las dbs de U-REEXT-T0, con
  `--salida-r2b data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b`, para el anclaje A1r y A3r. Si cambia la
  E0 que use la corrida, cambia también `E0_TANDA0_R2B`.
- F13, al cerrar R1 de U-RERESOL-CAT (sigue en curso, sin freno).
- La enmienda al protocolo sobre F05, F10 y F14, que está en curso.
- La fe de erratas de la enmienda 2, a cargo de la mesa revisora.
- El §5 con la tarifa observada de U-REEXT-T0.
- El commit, de la autora.

**Grep de convenciones** sobre la tabla, el selftest, su salida y este freno. Se buscan nombres de personas, rutas
absolutas y referencias a mensajes, mails o reuniones. Sin coincidencias, salvo esta misma nota, que nombra lo que
se busca.
