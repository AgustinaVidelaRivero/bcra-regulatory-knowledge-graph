# Pre-registro — B6.1 tanda final: la última tanda del escalado con la release r2

**FIRMADO por la autora el 18/10/2026** (firma por mensaje recibido a las 19:40:51; hoja de ruta de la mesa, §171), sobre la v3
para firmar (sha256 `0897d609851ae712768f0c1b68c2a485d5d8d91903aca84f3b54df58664d488b`, commiteada en `5289b02f`), con la precisión de la firma que la autora aceptó el 18/10/2026
a las 19:15:01 (sección «Precisión de la firma», al final). Rige desde esta firma.

La v3 (redactada por la mesa el 18/10/2026, hoja de ruta de la mesa, §155, §156 y §163; para firmar el lunes
19/10 temprano). Pedido de la autora del 18/10/2026, recibido a las 11:45:00. La v2 cambió la decisión 4 y el guardado del grafo
(respuesta de la autora recibida a las 12:19:47). La v3 trae los trece cambios y las cuatro decisiones del §9 que la autora pidió al
revisar la v2 (sha256 `a8870ab1…`; mensaje recibido a las 17:01:45). Va al repo en `docs/preregistro_tanda_final.md` en dos commits que
prepara la mesa: esta versión para firmar y, después, la firmada, que nombra su sha256 (§6, las semillas). Sus archivos (los scripts
de las cifras, del control entre tramos y del completador, con sus salidas y sus pruebas, las listas de los tramos y el JSON de huecos)
entran con esta versión en `data/experiment/tanda_final/preregistro/`.

- **Las cifras de T4, de T5 y de la revisión entre tandas** son huecos `⟦…⟧`. Los completa `completar_preregistro_tanda_final_mesa.py`,
  desde los archivos que nombra `huecos_preregistro_tanda_final.json`, en una versión derivada con su sha256. Si falta una fuente, frena.
  El texto firmado no cambia. Cuándo se completa cada hueco: la sección «Huecos».
- **Las demás cifras ya salen de un script:** `cifras_preregistro_tanda_final_mesa.py` → `salida_cifras_preregistro_tanda_final.json`.
- **Si la revisión entre tandas saca un documento,** el mismo script, con `--sin <TOs>`, recalcula con la misma regla U, el estimado, el
  tope (1,45 × U × 0,021115), las listas de los tramos y las bases del control entre tramos. **Mandan las cifras de la versión derivada,**
  que las trae en su sección final; las de este texto son las de los 98 documentos.
- **Lo que rige y este texto no cambia:**
  - el protocolo entre tandas (`a304b89`) y sus enmiendas 4 (`53bbd6fa`), 5 (`ccd8fad`), 8 (`54902301`) y 9 (`756a0394`);
  - la regla de caída sellada (`docs/regla_de_caida_grafo_evaluado_2026-10-15.md`) y su enmienda 1;
  - el laudo de la release r2 (`94087a7f`);
  - lo del pre-registro de la tanda 1 (`docs/preregistro_tanda1.md`, firma en `95b18217`) que este texto no reemplaza;
  - el registro de decisiones (`docs/registro_decisiones_calidad_y_evaluacion_2026-10-15.md`), hasta su última sección en el commit de
    la firma (con la del 18/10/2026, la §35).

## 0. Qué pre-registra y qué no

- **Pre-registra:**
  - el alcance y los dos tramos;
  - la versión;
  - el costo y el tope;
  - la corrida en seco y los criterios de corte;
  - el control entre tramos;
  - las lecturas y sus momentos;
  - las mediciones al cerrar;
  - lo que se declara;
  - la regla de caída y la pausa entre documentos.
- **No pre-registra:**
  - A2.2, U-NAV-DISENO, U-MED-DESAMB, U-MED-VERIF ni B6.3, que tienen sus propios documentos;
  - la re-aplicación única del código (R3 de la enmienda 8, `:50-57`), que va sobre el acumulado antes del sello del grafo evaluado.

## 1. Alcance

### 1.1 Los documentos

- **98 TOs y 4.951 unidades** de la E0 corregida (`data/experiment/segmentacion_oficial_e0r2/s2/cifras/tanda_final_S2c.json`). Por modo:
  68 `vigente`, 26 `sin_raiz` y 4 `marcadores`.
- La enmienda 8 decía 100 TOs y 5.337 unidades. Las notas del 15/10/2026 (enmienda 8, `:174-180`) la dejan en 98 y 4.951: ri_mmsef pasa a
  la tanda 1, y rdbcra queda fuera.
- El manifiesto lo arma T1 del despacho, con el perfil `r2b`, la E0 corregida de los 98, el tope del §3 y el estimado por TO. Tiene el
  formato del de la tanda 1 (`data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json`).

### 1.2 Los dos tramos

Registro de decisiones, §12; enmienda 9, §0. Las listas, en `tramos_tanda_final.json`, que entra con este pre-registro:

| tramo | TOs | unidades | qué tiene |
|---|---:|---:|---|
| 1 | 30 | 601 | los 24 regímenes informativos (444 unidades) y los 6 NG `sin_raiz` (157) |
| 2 | 68 | 4.350 | el resto, todos NG `vigente` o `marcadores` |

Las listas de los tramos son la de S2c, sin repetidos (control del script).

### 1.3 El alcance de cada documento (condiciones 11 y 11-bis)

- **Las filas de la tanda final** están en el registro de alcance (`764768a4`, tabla «## Tanda final»), y salen de la lectura sellada
  de la autora del 18/10/2026:
  - 46 filas: 17 con una clase, 3 con dos clases, 13 con rol reutilizado y 13 sin alcance declarado;
  - los otros 52 documentos tienen entrada en la tabla de la release;
  - ningún documento queda sin fila ni entrada, así que el §4, punto 4, del mandato de A3 no saca ninguno.
- **El cableado (A3)** regenera el derivado con `--tandas 1,final` y recomputa el candado del mensaje. Lo confirma la autora:
  - el derivado, `c8dea08a2ffe2eeb401855f952cc80f26542da8ea2489eac7a6f83530b6857ca`;
  - el candado, `6b758517cee0f2e36c26c54f0f6738b3d49d11d0cf3141c26cff166ce6820325`;
  - el mensaje de la fixture, `eeb11b9a3bf699d5535fcf2bbe79541ba746ae7bdae3341af962840990a97362`;
  - el costo de las líneas de alcance nuevas, `USD 0,209440, 209.440 tokens en 1.178 unidades de 33 documentos`.

### 1.4 La segmentación

- **Sub-documento:** los 14 límites de la tanda 1 están bien, sin error de corte (`73f4fd84`). El rasgo no se confirma, y los 33 límites
  de la tanda final no se leen (registro, §28).
- **1.16:** 10 de 10 cortes correctos, sin errores ni dudosas de corte. Rige la rama 0, y los otros 18 documentos se declaran con «0 de 10»
  (`73f4fd84`).
- **Los rasgos de corte que confirme la tanda 1** (pre-registro de la tanda 1, §5.4 bis, punto 3): `ninguno: sub-documento, 0 errores en 14 límites; 1.16, 0 de 10; la investigación de la cola no encontró un rasgo de corte`. Con
  cada uno, un detector como regla general sobre los 98, antes del manifiesto; sus positivos los lee la autora (§5.4 bis, punto 4).
- **Los documentos que salen antes del despacho,** por las tres salidas del §5.4 bis, punto 6: `ninguno`. Si
  sale uno con preguntas de B6.3, rige la regla de reemplazo (registro, §13).

## 2. Pipeline y versión

- **La release r2,** con las piezas y sellos del pre-registro de la tanda 1 (§2). Cambia solo el mensaje de E1: el derivado, el candado y
  el mensaje de A3 (§1.3).
- **El código de la cadena:** la lista de 78 rutas de la tanda 1 (`data/experiment/controles_tanda1/codigo_de_la_cadena_47c9f1b3_mesa.json`),
  re-sellada en el commit de A3 con el mismo script. Cambia el sha256 de los archivos que toca A3.
  - El commit y el sha256 de la lista: `c66c7ecd; la lista re-sellada, sha256 40de829cfd08b97192944c9e445da8003f6b22e34c6fd45a0ecd5d22dcf4958f`.
  - El despacho la controla en su paso 0, ruta por ruta.
- **Los modelos, como en la tanda 1:**
  - E1 pide `claude-haiku-4-5`, con temperatura 0 y 1 en el reintento por forma. La corrida frena si una llamada devuelve otro id que
    `claude-haiku-4-5-20251001`;
  - E3 usa `claude-sonnet-5`;
  - SDK `anthropic==0.100.0`, sin actualizar.
- **La consulta de deprecaciones** (`https://platform.claude.com/docs/en/about-claude/model-deprecations`), hecha por la mesa el
  18/10/2026 entre las 11:45:19 y las 11:52:07:
  - `claude-haiku-4-5-20251001`: «Active», sin fecha de deprecación, con retiro tentativo «Not sooner than October 15, 2026»;
  - `claude-sonnet-5`: «Active», con retiro tentativo «Not sooner than June 30, 2027»;
  - la página sigue dando un aviso de «at least 60 days».
  - Sin aviso al 18/10/2026, E1 no se retira antes del 17/12/2026. La consulta se repite el día del despacho, y su resultado va al
    FRENO T1. Si hay un retiro anunciado, se frena y entra por el procedimiento (c) (enmienda 6, decisión 1).
- **Los nombres de los grafos** (decisión 1 de la autora, §9):
  - la tanda: `KG-TandaFinal-r2b` y `KG-TandaFinal-r2b-sincola`;
  - el tramo 1: `KG-TandaFinal-Tramo1-r2b` y `KG-TandaFinal-Tramo1-r2b-sincola`;
  - el acumulado de las tres tandas: `KG-Acumulado-Tandas0y1yFinal-r2b` y `KG-Acumulado-Tandas0y1yFinal-r2b-sincola`. La tanda 2 no
    existe desde la enmienda 8;
  - el acumulado con el tramo 1 (enmienda 9, §1, punto 1): `KG-Acumulado-Tandas0y1yTramo1-r2b` y
    `KG-Acumulado-Tandas0y1yTramo1-r2b-sincola`.
  - Los directorios siguen D9 (`docs/protocolo_entre_tandas.md:378`) y la enmienda 5 (`:77-81`).

## 3. Costo y tope

- **La tarifa,** USD 0,021115 por unidad (laudo, §1, fila de la tarifa, `:43`), con **U = 4.951**:
  - el estimado es USD 104,5404;
  - con la razón de la tanda 1 (1,0191: su gasto, 70,991032, sobre su estimado con las líneas de alcance, 69,6592), USD 106,54.
- **El tope:** 1,45 × U × 0,021115 = **USD 151,58** (enmienda 8, `:100`; la regla de la tanda 1, §3).
  - Va en el manifiesto como `tope_global_usd`, y la corrida real exige `--autorizado-tope` igual a ese valor.
- **Las líneas de alcance nuevas** (§1.3): `USD 0,209440, 209.440 tokens en 1.178 unidades de 33 documentos`. Van dentro del margen, con el tope sin cambios, como en la tanda 1
  (registro, §12; decisión 2 de la autora, §9).
- **El gasto real** se compara contra U × tarifa más el costo de las líneas de alcance, como en la tanda 1 (su estimado con las líneas de
  alcance, 69,6592: 3.290 × 0,021115 + 0,190841).
- **Por tramo:** el estimado del tramo 1 es USD 12,6901 (601 unidades) y el del tramo 2, 91,8502 (4.350). Los dos comparten un solo tope,
  que el estado del runner guarda en su `--salida`.
- **El total de USD 341** (enmienda 8, decisión 4): si el gasto acumulado llega a 341, la mesa frena y decide la autora.

## 4. Corrida en seco y criterios de corte

### 4.1 La corrida en seco, que es T1 del despacho

- **El despacho no arranca** sin la revisión entre tandas completa y firmada por la autora (enmienda 8, `:40`). Su paso 0 controla el
  sha256 de la versión derivada de este pre-registro con los huecos de antes de T1, y frena si falta (sección «Huecos»).
- **El despacho lleva** la cláusula v2 de las carpetas vedadas (registro, §31) y la del cegamiento de U-MED-VERIF: ninguna cifra ni lista
  por estado de E3 ni de los reintentos de E3, y la regla de exclusión de las FICHAS antes de mostrar contenido de una extracción de la
  tanda 1 (pre-registro de la tanda 1, §7, `:900-909`; registro, §34).

Como en la tanda 1 (§4.1), sobre una copia sin enlaces, con la foto del repo antes y después:
1. **el mismo camino que el runner,** recorriendo las ramas de corte, reintento, partición, tercer escalón y salida mal formada;
2. **las unidades que no entran en una llamada,** cada una con el mecanismo que la cubre;
3. **los mensajes de E1:**
   - los de las 2.439 unidades de la tanda 0 y los de las 3.290 de la tanda 1, byte a byte iguales;
   - en la tanda final cambia solo la línea de alcance de los documentos con fila nueva (criterio 3 del mandato de A3);
   - `selftest_clave_cache` da OK;
4. **el estimado por TO,** con los clientes stub;
5. **el ensamblado de un subconjunto** (enmienda 9, punto 7; registro, §12): si T1 lo prueba, hay sello del tramo 1 y T3 sobre el tramo 1.
   Si no, no los hay, y se declara;
6. **el piso de espacio:** 30 GB libres en el paso 0 y antes de la corrida real (pre-registro de la tanda 1, `:913-914`).
- T2 no arranca sin que la autora revise el FRENO T1.

### 4.2 Los criterios de corte

Como en la tanda 1 (§4.2):
- el tope global duro, el freno por proyección y el margen por unidad;
- los ids repetidos;
- el id de modelo;
- un retiro anunciado;
- un hallazgo grave, por el procedimiento (c);
- P20 no rige, y se conserva el freno manual.

Se suman:
- **el control entre tramos** (§5);
- **la pausa entre documentos** (registro, §27): si la tanda final no está sellada el viernes 23/10/2026 a las 18:00 y su extracción
  sigue, la ejecutora termina el documento que esté corriendo y no lanza el siguiente hasta que terminen B6.3 y las tripletas T. Después
  retoma, para la versión corregida.

## 5. Los dos tramos y el control entre ellos

- **Cómo se corre, sin tocar código:**
  - un solo manifiesto, con el orden de siempre;
  - `runner_corpus.py --tos <los 30 del tramo 1>`, después el control, y después `--tos <los 68>`, con la misma `--salida`;
  - el tope es compartido.
- **El control:** `control_entre_tramos_tanda_final_mesa.py`, sellado con este pre-registro.
  - Corre al cerrar el tramo 1, sobre una copia. Si da FRENO, frena y decide la autora. Si da OK, sigue sin leer nada.
  - Usa `resumen_t2.resumir`, que junta los estados de aceptación y de cola y no lee los reintentos de E3 (cegamiento de U-MED-VERIF).
  - **Las bases** salen de la tanda 1, con una sola base: las 548 unidades RI o `sin_raiz` (registro, §13). Las calcula
    `cifras_preregistro_tanda_final_mesa.py`.
  - **Probado en seco sobre la tanda 1** (`prueba_control_entre_tramos.txt`), con los 8 TOs de la base como tramo: da OK en los cuatro
    criterios, frena cada criterio en su prueba en contra, y el repo no cambia.

| criterio | base de la tanda 1 | umbral |
|---|---|---|
| costo por unidad | 0,026331: el de sus RI (0,025952) y sus NG `sin_raiz` (0,027403), ponderados por los 444 y los 157 del tramo 1 | 1,3 veces la base: 0,03423 |
| salidas inválidas de E1 | 2 de 3.294 en toda la tanda 1 (información) | 1 % |
| errores definitivos | 0 | 0 |
| proporción a la cola | 11 de 548 (2,01 %). Con 10 o más en la cola rige la proporción, no el límite de Wilson | 1,5 veces la base: 3,01 % |

- **La salida inválida de E1** (decisión 3 de la autora, §9): una unidad cuyo último registro de E1 trae `error` (sin contar la partida
  por corte) o `reparacion_forma`.
- **El control informa además, sin umbral,** cuántas unidades tuvieron reintento por forma de E1 (su último registro trae
  `reintento_forma`). En la tanda 1 fueron 22 de 3.294, como información.
- **El sello del tramo 1 como respaldo** (enmienda 9, §1, puntos 1, 5, 6 y 7), si T1 prueba el ensamblado de un subconjunto:
  - su E0, los `kg.json` del tramo 1 y del acumulado con el tramo 1 (completo y sin cola), los registros, la suite y las shapes (su T3),
    las lecturas de sus celdas y su T5;
  - el commit con el lanzador vivo, con las cinco condiciones de la enmienda;
  - el control de sha256 de las carpetas de salida del tramo 1 antes y después del commit, y al cerrar el tramo 2.

## 6. Las lecturas (enmienda 9, §1, puntos 2 a 4; pre-registro de la tanda 1, §5.4 y §5.4 bis)

- **Un solo juego de lecturas,** con las celdas de la tanda 1 (RI, 10 `sin_raiz` y 5 del resto; NG, 5 `sin_raiz` y 10 del resto),
  leído en dos momentos:
  - **al cerrar el tramo 1:** la cola y las aceptadas de las celdas RI `sin_raiz`, RI resto y NG `sin_raiz`, 20 de cada muestra de 30;
  - **al cerrar el tramo 2:** las de NG resto, 10 de cada 30;
  - **las de elementos del grafo** (vigilancias (1), (2), (3) y (7), y la observación (12)): se sortean sobre el ensamblado de la tanda
    entera;
  - **la rama intermedia de la regla de caída:** «las lecturas de elementos del grafo del tramo 1 se sortean sobre su acumulado sellado»
    (enmienda 9, §1, punto 2, `756a0394:55-56`).
    - La población son los elementos con procedencia en unidades del tramo 1, con las reglas de celda de la tanda 1.
    - Ningún elemento con procedencia solo en las tandas 0 o 1 entra al sorteo. El script del sorteo lo controla y da el conteo;
  - **la cola:** si al final tiene 30 unidades o menos, se lee entera.
- **Las definiciones** son las de la tanda 1, con las decisiones del 18/10/2026 (registro, §29):
  - la (12), con [c1] del tablero y sin `remite_a`;
  - la (2), en la extracción final;
  - (1) y (3), como se decidieron para su T4. En la (3), el par del deber y el acto regulado queda en la población, con el criterio
    de la §31: un grupo es duplicación solo si un nodo repite el contenido normativo de otro.
- **Las dudosas** (registro, §35): en la cola y en las aceptadas, una unidad «dudosa» cuenta como error para la tasa, la atención y el
  freno. La cuenta con las dudosas fuera va al lado como sensibilidad y no decide nada; si diera otra decisión de atención o de freno, se
  declara y rige la primera.
- **Las semillas:** `random.Random(f"tandafinal:{muestra}:{celda}:{base}").sample(sorted(ids_de_la_celda), cuota)`, con las reglas de
  las celdas chicas y de las clases chicas de la tanda 1, y las ampliaciones con `:ampliacion:`.
  - La base es el sha256 de la versión para firmar de este pre-registro, tal como entra con su commit, igual que en la tanda 1.
  - La versión firmada lo nombra.
- **Los umbrales:**
  - salen de `data/experiment/controles_tanda1/umbrales_t4_por_celdas_mesa.py` (sha256
    `f4723e5aced718429e1a644ac919322d359712bf2b99042b760d5d3c4e68639d`), con los pesos reales de la tanda final, como los usó el T3 de la
    tanda 1 (`data/experiment/tanda1/t3/scripts/umbrales_t4_t3f.py`, sha256
    `31bc8adeff8155c58c921b528139c0ef400a0787353904d9a2aa9b8e5c1f9aed`). La atención y el freno se deciden contra esos umbrales;
  - la atención propia de RI se calcula al cerrar el tramo 1, antes de leer;
  - la atención y el freno de cada estrato se calculan al cerrar el tramo 2, con los pesos reales y el script sellado, antes de leer NG
    resto. Se declara que se calculan después de leer las celdas del tramo 1.
- **Las líneas de base de las lecturas** son las de la tanda 1, de su T4:
  - la cola: `14 de 30 con las dudosas como error; ponderada 0,4386, Wilson de Kish [0,2751; 0,6166]; la regla del 25 % se dispara`;
  - las aceptadas ítems: `9 de 30 con las dudosas como error; ponderada 0,2196, Wilson de Kish [0,0784; 0,4822]; atención: no; freno: no`; no ítems: `3 de 30 con las dudosas como error; ponderada 0,0968, Wilson de Kish [0,0214; 0,3446]; atención: no; freno: no`; la ponderada total: `0,1397, Wilson de Kish [0,0532; 0,3196]`;
  - la atención de RI: `7 de 30; ponderada de RI 0,1747; la atención no salta`;
  - las vigilancias (1), (2), (3) y (7), y la (12): `(1) 3 sí de 30; (2) 15 vaciamientos de 30; (3) 9 duplicaciones de 30; (7) 2 sin apoyo de 4; (12) 27 correctas de 30, Wilson [0,7438; 0,9654]`.
  - La tanda 0 queda al lado, como en el pre-registro de la tanda 1.
- **Quién lee:** lectura asistida con revisión de la autora (D2), como en el T4 de la tanda 1.

## 7. Las mediciones al cerrar (T3 a T5)

- **El gate** (laudo, §3), con las decisiones del 18/10/2026 sobre el T3 de la tanda 1 (registro, §29):
  - para S31 rige la E0 con las partes por corte, y se informan las dos corridas;
  - la suite se juzga sobre el acumulado; en el grafo de la tanda y en el de cada tramo, lo «fuera del grafo» se informa aparte, por
    script, y no cuenta;
  - E4-a1 y E4-a4 siguen declaradas (BKL-0048).
- **Los `nombres_remision` de los ensamblados nuevos** siguen la regla de la §19 del registro y la enmienda 9, punto 8 (`756a0394:78`),
  medidos en su T3.
- **La clasificación de los hallazgos y el reporte,** como en la tanda 1 (su pre-registro, §5.6).
- **El registro y Neo4j:** las entradas nuevas en `grafos.py`, con `commit_sellado` en el commit siguiente, y la carga con gate 5 OK.
  - El cargador lee hoy solo las claves `KG_Tanda0_*`. Si N5 de U-NAV-DISENO no lo cambió antes, se usa el envoltorio en memoria del T3
    de la tanda 1, declarado.
- **Lo que se cuenta sin leer:** las observaciones (10) y (11), las vigilancias (4), (5), (8) y (9), la cola y el catálogo al cierre.
  - Su línea de base es la de la tanda 1 (FRENO T3 final, tablas C1 a C4, `eb0711a1`), con la de la tanda 0 al lado.
  - El cegamiento de las cuentas de E3 sigue hasta que la autora lo levante.
- **El costo real** contra el estimado, por tramo y por TO, y la tanda 1 al lado: `⟦T5.costo_real_tanda1⟧`.
- **La señal cid:** las 3 unidades de la tanda final con «(cid:», después de su T5 (registro, §14).
- **El catálogo al cierre** (enmienda 4, §1): las claves candidatas del acumulado de las tres tandas, con su lectura y la aprobación de la
  autora, antes de la re-aplicación única. Cuándo y con qué material: la decisión 4 del §9.
- **Toda cifra del FRENO sale por script** desde sus archivos, ninguna escrita a mano (decisión de la autora del 17/10/2026, a las
  22:10:33). El despacho lo pide como requisito, con cada tabla al lado de su script y su salida. La revisión de la mesa reproduce cada
  cifra; una cifra sin script que la genere es un defecto.

## 8. La regla de caída y lo que se declara

- **La regla sellada y su enmienda 1:**
  - si el miércoles 21/10/2026 a las 18:00 la tanda final no está despachada, o si no está sellada el viernes 23/10/2026 a las 18:00, el
    grafo evaluado son las tandas 0 y 1 (regla sellada, punto 1, `docs/regla_de_caida_grafo_evaluado_2026-10-15.md:12-15`);
  - con el tramo 1 sellado a esa hora (y la tanda despachada el miércoles 21 a las 18:00), son las tandas 0 y 1 y el tramo 1;
  - lo que no entra corre igual después, para el grafo completo y el corregido del cap. 6.
- **Se declaran:**
  - los documentos que salen, con su causa;
  - las desviaciones del estimado;
  - las precisiones tomadas con resultados a la vista (S31 y «fuera del grafo»);
  - U-BLOQUE-A y sus 77 unidades, que quedan fuera del grafo evaluado (enmienda 8, `:46-47`; registro, §4);
  - cómo se guardan los grafos que pasan de 100 MB (decisión de la autora del 18/10/2026; registro, §30): comprimidos de forma
    determinista con `scripts/kg_gz.py`, con el sello al lado. Manda el sha256 del `kg.json` sin comprimir; el del `.gz` va como
    información, con el compresor y la versión de zlib. El grafo evaluado se publica en un release de GitHub, con la copia limpia de las
    rutas del scratchpad.
- **Lo que no cambia durante la tanda,** como en la tanda 1 (§7): el alcance congelado; el prompt, el esquema y los modelos; las
  lecturas y las semillas fijadas antes de leer; y nada de lo que la tanda necesita queda en `/private/tmp`.
- **El código de la cadena** (las 78 rutas re-selladas con A3, §2) no cambia entre el paso 0 del despacho y el sello de la tanda final.
  - U-PROC-HERENCIA toca `data/experiment/tanda0/code/ensamblar_tanda0.py`, que está en la lista, y entra después del sello (registro,
    §33).
  - Si otro commit necesita tocar una de esas rutas, se frena y decide la autora.

## 9. Las decisiones de la autora

Tomadas el 18/10/2026, en el mensaje recibido a las 17:01:45 (hoja de ruta de la mesa, §163), sobre la v2:
1. **Los nombres de los grafos,** los del §2:
   - `KG-TandaFinal-r2b` y `KG-TandaFinal-Tramo1-r2b`, como propuso la mesa;
   - el acumulado de las tres tandas, `KG-Acumulado-Tandas0y1yFinal-r2b`, «porque la tanda 2 no existe desde la enmienda 8»;
   - y el acumulado con el tramo 1 de la enmienda 9, punto 1, `KG-Acumulado-Tandas0y1yTramo1-r2b`;
   - cada uno con su `-sincola`, y los directorios según D9.
2. **Las líneas de alcance nuevas,** dentro del margen y con el tope sin cambios, como propuso la mesa (§3).
3. **La salida inválida de E1,** como propuso la mesa (§5). El control informa además, sin umbral, cuántas unidades tuvieron reintento
   por forma.
4. **La lectura de las claves del catálogo** (§7): una sola vez, sobre el acumulado de las tres tandas, después del sello de la tanda
   final, como propuso la mesa:
   - el material lo arma una ejecutora que conoce la muestra de U-MED-VERIF-FICHAS. Quita toda fila de esas unidades y toda forma que
     aparezca solo en ellas;
   - un script de la mesa lo controla con OK o FRENO, sin mostrar la muestra.
   - Con cuatro agregados de la autora:
     - **a más tardar el sábado 24/10/2026 a las 12:00** (R5). Si a esa hora no está aprobada, el catálogo no crece en el grafo
       evaluado, y se declara;
     - **se declara como desvío** de la enmienda 4, §1, punto 1, y del pre-registro de la tanda 1, §5.5;
     - **una clave es candidata con 2 unidades distintas,** contadas sin las de la muestra de U-MED-VERIF que rija. Lo que llega a 2 solo
       con ellas va al grafo corregido;
     - **el material no muestra** ningún estado de E3 ni conteos que incluyan esas unidades.
   - (La v1 decía «después de la adjudicación de U-MED-VERIF», que cae después del sello del sábado 24.)

## Huecos

- **Los nombra** `huecos_preregistro_tanda_final.json`, cada uno con su fuente, su clave y su momento. La versión derivada los completa
  por script, y frena si falta una fuente.
- **Cuándo se completa cada uno** (`--momento` del script):
  - `A3.*`, `codigo_cadena.*` y `revision.*`: antes de T1. El paso 0 del despacho controla el sha256 de esa versión derivada, y frena si
    falta;
  - `T4.*`: antes de la primera lectura del tramo 1;
  - `T5.*`: antes del FRENO T5 de la tanda final.
- **La fuente y la clave de cada hueco** las fija el «seguí» o el mandato que produce su archivo, antes de que el archivo exista.
- **Cada versión derivada** nombra el sha256 del JSON de huecos que usó, y trae al final las cifras de `cifras_preregistro_tanda_final_mesa.py`
  con las que corre (con `--sin`, si salió un documento).

## Precisión de la firma

Aceptada por la autora el 18/10/2026, a las 19:15:01 (registro de decisiones, §39), por el hallazgo 8 de A3. La preparó la mesa
(`decisiones_169_mesa/precision_tf/`, en su paquete), con su script (`fixture_desde_47c9f1b3_mesa.py`): de las 78 rutas de la lista
sellada en `47c9f1b3`, en la base de A3 difiere una sola, `scripts/regression_kg_esperado.json`. La tocó un solo commit, el del T3 de la
tanda 1 (`eb0711a1`), que le sumó las expectativas de los cuatro grafos de la tanda 1: 1.136 claves nuevas bajo `estado_esperado`,
ninguna quitada ni cambiada.

1. **Al §2, qué cambia en la lista re-sellada.** La lista re-sellada con A3 cambia el sha256 de los dos archivos de la lista que toca A3
   (`reextraccion_v2/e1_extractor/prompt_r2b.py` y `catalogo_unico/registro_alcance_r2b.json`) y el de `scripts/regression_kg_esperado.json`,
   por las cuatro entradas del T3 de la tanda 1. Ninguno más.
2. **Al §2, cuándo se re-sella.** La lista se re-sella sobre el commit de A3, con el mismo script
   (`data/experiment/controles_tanda1/sellar_codigo_de_la_cadena_mesa.py`), en el commit que sigue, porque un commit no puede nombrarse a
   sí mismo. El hueco `codigo_cadena.commit_y_sha256` lleva el commit de A3 y el sha256 de esa lista.
3. **Al §8, la fixture durante la tanda.** «El código de la cadena no cambia entre el paso 0 del despacho y el sello» vale para las 78
   rutas salvo `scripts/regression_kg_esperado.json`, que es un dato de la suite y no código. El T3 de la tanda final le suma las
   expectativas de sus grafos, como el T3 de la tanda 1 (§2: la tanda, el tramo 1, el acumulado de las tres tandas y el acumulado con el
   tramo 1, cada uno con su sin cola). Para ese archivo, el control entre el paso 0 y el sello es:
   - todo lo que trae la versión re-sellada sigue igual, clave por clave;
   - lo nuevo son solo entradas de `estado_esperado` con los nombres de los grafos de la tanda final.

## Firma

**FIRMADO por la autora el 18/10/2026,** por mensaje recibido a las 19:40:51 (hoja de ruta de la mesa, §171): «Firmo el pre-registro de la tanda final en la versión para firmar commiteada en 5289b02f (docs/preregistro_tanda_final.md), con mis cuatro decisiones del §9 y los tres puntos de la precisión del §169.» El texto firmado es el
de la v3 (sha256 `0897d609851ae712768f0c1b68c2a485d5d8d91903aca84f3b54df58664d488b`), con este encabezado, la precisión de la firma y esta sección. En el commit de la firma, la
última sección del registro de decisiones es la §40.

## Versión derivada (la escribe el script; no es parte del texto firmado)

- **El momento:** lectura_tramo1.
- **El pre-registro:** sha256 `b760edf7d341290ad910de993f8a868be426abcf2cfd14459240ad5a2b940cc2`. **El JSON de huecos que usé:** sha256 `0e02eba9a165e32d25bfccccdc93ebe31d16b8c50953cf72525ae1f5226b4a7b`.
- **Los huecos completados:** 13. **Los que esperan a un momento posterior:** T5.costo_real_tanda1 (T5).
- **Las cifras con las que corre la tanda** (`5289b02f:data/experiment/tanda_final/preregistro/salida_cifras_preregistro_tanda_final.json`, sha256 `083dd244eae51b3621f19a27476aa18024c8ee191ad72fee6a590a9f8020fdc9`). Mandan sobre las del texto:
  - documentos fuera: ninguno;
  - 98 TOs y U = 4951 unidades; el estimado, USD 104.5404; el tope, USD 151.58;
  - el tramo 1, 30 TOs y 601 unidades; el tramo 2, 68 TOs y 4350 unidades;
  - las bases del control entre tramos: el costo por unidad 0.026331 (umbral 0.03423), la cola 0.020073 (umbral 0.030109).
