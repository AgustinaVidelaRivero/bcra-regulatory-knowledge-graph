# Procedimiento de empalme de un subgrafo re-extraído

U-MANT, etapa M2 (e). Cuando un TO cambia en el sitio, este procedimiento
dice cómo se identifican las unidades que cambiaron, qué se re-extrae, cómo se
sustituyen sus salidas, qué se re-ensambla y qué controles se corren después.
La re-extracción real y su costo son de U-SUBGRAFO (plan, fila B2.11, unidad
13). Acá el procedimiento queda escrito y demostrado en seco (USD 0, sin API).

Reglas que rigen (mandato U-MANT, decisiones 2 a 4):
- el corpus no se actualiza;
- los PDFs congelados, el inventario y las salidas selladas se leen y no se
  tocan;
- toda actualización es una release declarada, con laudo de la autora
  (plan, principio 9, `docs/plan_tesis.md:277`). El empalme produce un grafo
  nuevo, no corrige el evaluado.

## Paso 1. Detectar

- El job de actualización marca un TO como `contenido_modificado` cuando
  cambia el sha256 del PDF (`job_actualizacion/diseno_job_actualizacion.md`, §3).
- Antes de empalmar, el control del sitio tiene que estar en verde
  (`control_sitio/control_sitio.py`). Si S7 se rompe, E0 no reconoce el pie
  nuevo y el pie entra al texto de las unidades: el empalme se frena hasta
  resolverlo (tabla de M1, filas F01 y F18b).

## Paso 2. Identificar las unidades cambiadas

Hay tres fuentes para localizar y explicar el cambio, y un criterio que decide
qué se paga.

**Fuente 1 — sha del PDF y diff por página del job.**
- Qué da: las páginas cuyo texto extraído cambió.
- Cómo llega a unidades: por las páginas de cada unidad de E0 (`paginas` del
  chunk) o por la provenance del grafo.
- Límite: es un localizador, no un comparador de sentido. Una página puede
  marcarse por un reordenamiento de la extracción
  (`job_actualizacion/corridas/2026-09-07/reporte.md:91-99`; plan, fila
  U-JOB-ACT).
- Ejemplo: en `capmin`, 46 páginas de 206, que tocan 128 chunks de r1
  (`reporte.md:28-30`).
- El pie de cada página («Versión: Na. COMUNICACIÓN "A" NNNN», supuesto S6
  del control) agrega la Comunicación de cada página. Una página que cambió de
  Comunicación es una página modificada con su procedencia.

**Fuente 2 — la tabla de origen de las disposiciones.**
- Cobertura: la tienen 90 de 152 TOs (`reports/u_insumos_cap/estadisticas_corpus.md:222`,
  regla R14, `ded3494`) y 4 de los 5 de desarrollo (`ric` no).
- Qué da: por punto, la Comunicación de origen. Comparar la tabla vieja con la
  nueva lista los puntos que cambiaron de origen.
- Límite: en el pipeline de generación 3 no hay un lector de la tabla por
  punto. E0 solo clasifica sus páginas y las deja fuera de las unidades
  (`e0_chunking/e0_lib.py:366-368`, `:678-679`). Ese lector es NO ENCONTRADO:
  usar esta fuente exige escribirlo.

**Fuente 3 — las Comunicaciones que citan el punto que modifican.** Medida en
la sección 7: en la ventana declarada, 7 de 21 citas se mapean a TO y
unidades. Las fórmulas declaradas cubren una parte chica de lo que escribe el
BCRA.

**Criterio que decide: la clave de la caché.**
- Qué se hace: se corre E0 (código, USD 0) sobre el PDF nuevo y se calcula la
  clave de E1 de cada unidad con el armado del pipeline, sin llamar a la API
  (`mantenimiento/code/selftest_clave_cache.py`, clase `Armado`).
- Qué decide: una unidad cuya clave ya está en la caché no se paga; una que
  no está es la que hay que re-extraer.
- Es la proyección de misses del laudo de r2, §3.2.5
  (`docs/laudo_release_r2_pipeline.md:300-306`).
- Uso de las fuentes 1 a 3: explican por qué cambió una unidad y sirven de
  contraste. Un miss en una página que el diff no marcó, o un punto citado por
  una Comunicación sin miss, es una señal a mirar antes de pagar; no se paga
  en silencio.

### TOs sin tabla de origen (62 de 152)

Sin la fuente 2, el procedimiento usa:
- la fuente 1 (diff por página y pie por página);
- la fuente 3, si alguna Comunicación cita puntos de ese TO;
- y el criterio de la clave.

Si ninguna localiza el cambio, por ejemplo con un PDF re-diagramado entero, el
diff marca casi todas las páginas y el pie no da la Comunicación por página:
- se pasa el TO entero por E0, E1 y E3 con el runner;
- aun así, solo pagan las unidades cuya clave no está en la caché, así que
  «el TO entero» es la cota superior, no el costo seguro.

Costo por clase según la tabla de M1 (`tabla_reprocesamiento.md`, sección 5):
- es «E1 y E3 de las afectadas», con todas las unidades del TO como
  afectadas;
- referencia: USD 0,007425 de E1 y USD 0,009179 de E3 por unidad, promedio de
  la tanda 0;
- es un promedio, no una estimación: las unidades largas cuestan mucho más
  (tres unidades de cap, USD 0,461274).

## Paso 3. Qué se re-extrae

- **E1 y E3** de las unidades cuya clave de E1 no está en la caché. Son las
  filas F01 a F04 y F19 de la tabla de M1:
  - texto propio;
  - encabezado heredado;
  - prosa heredada;
  - marcas de E0;
  - número de la unidad.
- **E3** de esas mismas unidades: E1 corre sin temperatura fijada, así que su
  salida nueva arma un request de E3 nuevo.
- **Nada** para las unidades con cambios de páginas, ids o sha sin cambio de
  texto (fila F05): eso se corrige en código en E2.
- Se corre con el runner sobre una copia, nunca sobre la salida sellada. El
  precedente es `corpus_tanda0/salida_dirigida/`, copia completa de
  `salida/` (U-TANDA0-2A-DIR, `tanda0/code/reextraccion_dirigida_tanda0.py:30`).
- Las llamadas van en secuencia (`docs/decisiones_caching_extraccion.md`,
  decisión 4).

### Renumeración

Insumo: insertar un punto antes de `pro::2.3` renumera 2.3 a 2.7 y cambia 42
de las 101 claves de pro, en E1 y en E3 (selftest de M1, V24).

- **Qué se re-extrae:** el punto nuevo y las 42 unidades renumeradas con sus
  descendientes. La caché no reconoce «mismo contenido, otro número».
- **Cuánto cuesta**, con la referencia de la tabla de M1: 42 × (0,007425 +
  0,009179) = USD 0,70 por las renumeradas, más el punto nuevo. Es un
  promedio, no una estimación.
- **Hay forma de identificar que solo se movió el número, a USD 0:**
  - una firma de contenido toma todo lo que entra al request de E1 salvo los
    números de punto: tipo, archivo, TO, título, marcas de E0, tipo y texto de
    cada bloque heredado y texto propio, sin el numeral inicial
    (`code/empalme_subgrafo.py`, `firma_contenido`);
  - en la demostración (`demo_empalme_renumeracion.json`) las 101 unidades de
    pro tienen firmas distintas;
  - de las 42 claves que no están en la caché, las 42 tienen la firma de una
    unidad vieja, y 0 son contenido nuevo.
- **Qué se hace con eso** (decisión de la autora del 02/10/2026): **se
  re-extrae.** Las unidades renumeradas pasan por E1 y E3 como cualquier
  unidad cuya clave no está en la caché; la firma de contenido sirve para
  declarar en la release que su contenido no cambió, no para evitar el pago.
- **Alternativa escrita para U-SUBGRAFO, que pide laudo:** reutilizar la
  salida guardada de esas unidades y renumerar en código los `punto` de su
  provenance (principio 12), a USD 0. Deja en el grafo salidas extraídas con
  un request que ya no coincide con el texto de E0 de la release, por eso no
  se aplica sin laudo y no la implemento.
- **Límite:** si la fuente actualiza las remisiones internas («ver punto
  2.4») de otras unidades, esas unidades cambiaron de verdad: su firma no
  coincide y se re-extraen.

### Cambio fuera de las páginas de cuerpo: la página 85 de ctacte

- En la corrida del 2026-09-07, `ctacte` cambió solo en la página 85 de 86, y
  el reporte muestra una lista de Comunicaciones «C»
  (`job_actualizacion/corridas/2026-09-07/reporte.md:80`).
- En la E0 de la tanda 0, las unidades de ctacte usan las páginas 5 a 64.
  E0 clasificó 60 páginas de cuerpo, 12 de historial y 10 de tabla de origen
  (`e0_chunking/salida_tanda0/conteos.json`, clave `ctacte`).
- Si E0 sobre el PDF nuevo devuelve las mismas unidades byte a byte, el
  empalme es de clase «nada» (fila F18a de M1): no se llama a la API.
- Aun así, la release se declara, porque cambia el sha del PDF.
- Que E0 devuelva las mismas unidades es NO VERIFICADO: es el primer paso de
  U-SUBGRAFO.

## Paso 4. Cómo se sustituyen las salidas

En cada TO afectado y en cada archivo por unidad (`extracciones_e1.jsonl`,
`finales.jsonl`, `veredictos.jsonl`, `cola_humana.jsonl`):
- se sacan todas las líneas de las unidades re-extraídas;
- se agregan las líneas de esas unidades que trae la corrida de
  re-extracción, en su orden;
- el resto queda byte a byte. Como la lectura de esos archivos es «la última
  línea gana» (`runner_corpus.py:280-291`), la salida nueva reemplaza a la
  vieja.

Después se re-compacta E1 y se cierra E2 del TO con las funciones del runner
(`runner_corpus.py:574-585` y `:665-709`).

## Paso 5. Qué se re-ensambla

- Todos los ensamblados que contienen un TO afectado, con el mismo ensamblador
  y el mismo manifiesto (`tanda0/code/ensamblar_tanda0.py`, o el de la release
  vigente).
- E2 se re-cierra solo en los TOs afectados.
- El merge entre TOs, E4, el esqueleto, las referencias y la provenance corren
  sobre el ensamblado entero, en código y a USD 0.
- Los nodos anclados en más de un TO (16 en r1,
  `diseno_job_actualizacion.md:440-448`) los resuelve el merge. No se
  reemplazan a mano por TO.

## Paso 6. Controles después del empalme

1. Doble corrida del ensamblado, byte a byte idéntica.
2. Shapes con perfil congelado y regression suite con la entrada de la release
   (gate del laudo de r2, §3.1, `docs/laudo_release_r2_pipeline.md:243-282`).
3. Tabla de M1: los misses de la corrida coinciden con las unidades declaradas
   afectadas en el paso 2. Un miss de más es deriva de clave y FRENO sin
   gastar (laudo de r2, §3.2.5).
4. El control del sitio, en verde.
5. Los TOs no afectados conservan sus `grafo_<to>.json` byte a byte.

## Demostración en seco

Reproduje los ensamblados sellados de la tanda 0 (`1b8916c`) a partir de la
salida base (`corpus_tanda0/salida/`) y de las tres unidades de cap
re-extraídas (`cap::3.1.14.1`, `cap::4.2.1.2` y `cap::4.3.3.1`, tomadas de
`corpus_tanda0/salida_dirigida/`), siguiendo los pasos 4 y 5. Todo se escribió
en un directorio de trabajo fuera del repo.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/code/empalme_subgrafo.py dirigida --trabajo <dir fuera del repo> --out data/experiment/mantenimiento/demo_empalme_dirigida.json
```

Resultado (`demo_empalme_dirigida.json`):
- Sustitución en cap: en `extracciones_e1.jsonl` se quitaron 3 líneas y se
  agregaron 6. La copia `salida_dirigida/` trae los 3 intentos fallidos y las
  3 re-extracciones; gana la última. En `finales.jsonl` se agregaron 3 líneas
  y en `veredictos.jsonl`, 4.
- `grafo_cap.json` de E2: 2.026 nodos y 3.459 aristas, sha256 `625c47c6…`,
  igual al de `salida_dirigida/`.
- **Los seis `kg.json` iguales a los sellados**, sha por sha:
  - `ens_desarrollo` `921ec9c4…` y `r1` `eab2fdd0…`;
  - `ens_cinco` `5e3deca8…` y `r1` `4097d4fd…`;
  - `ens_diez` `c5be2a34…` y `r1` `dd42d6d9…`.

  `ens_cinco` no contiene cap: sirve de control de un ensamblado no afectado.
- Dos corridas dan el mismo JSON. El repo no recibió ninguna escritura salvo
  el JSON de salida (verificado con `find -newer` contra un marcador tomado
  antes de cada corrida).

La renumeración se demuestra con el mismo script:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/code/empalme_subgrafo.py renumeracion --out data/experiment/mantenimiento/demo_empalme_renumeracion.json
```

## 7. Medición de la tercera fuente

Declaración: `declaracion_citas_comunicaciones.json` (sha256 `82df4d5b…`).
- Fijé la ventana, las cuatro fórmulas con sus plurales, el segmento de cada
  cita, la lectura del punto, la regla del nombre del TO y las categorías.
- La escribí y le tomé el sha antes de escribir el script de medición, que la
  lee tal cual y deja su sha en la salida.
- Extensión declarada: los cinco TOs de desarrollo no están en
  `inventario_tos.csv`; sus títulos salen de `inventario_resumen.json` y sus
  unidades, de la E0 de la tanda 0.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/code/medir_citas_comunicaciones.py --out data/experiment/mantenimiento/citas_comunicaciones.json
```

Resultado (`citas_comunicaciones.json`, dos corridas byte a byte idénticas):

- **Ventana:** `fecha_documento` mayor que 2025-05-08 y hasta 2026-05-08. La
  fecha de referencia, recomputada, es 2026-05-08. Hay 195 Comunicaciones
  «A» en la ventana y las 195 se leyeron, con el sha256 de cada PDF.
- **Conteo:**
  - Comunicaciones con al menos una fórmula: 8;
  - citas: 21, todas «Sustituir el punto» o su plural;
  - citas que nombran un punto y un texto ordenado: 7, todas del corpus de
    152.
- **Categorías:** 7 mapeadas a TO y unidades, 0 solo a TO, 14 no mapeables y
  0 no decidibles. Las 7 son:
  - `ayccef`: 1 cita con 3 puntos, en la «A» 8242;
  - `rdbcra`: 2 citas, una con 5 puntos en la «A» 8248 y otra con 1 en la
    «A» 8278;
  - `lingeef`: 1 cita con 1 punto, en la «A» 8249;
  - `snp_psp`: 3 citas, el punto 1.5 en la «A» 8411 y los puntos 1.3 y 2.5
    en la «A» 8432.
- **No mapeables:** las 14 se reparten así:
  - 11 nombran a `rdbcra` solo por la primera mitad de su título. El
    inventario agrega «y tramitación de sumarios cambiarios (Ley 19.359)» y la
    regla declarada exige el título completo;
  - 1 trae el título de `rrci` cortado por un guion de fin de línea
    («Re- cuperación»);
  - 2 sustituyen puntos del Anexo de una Comunicación, no de un texto
    ordenado (`citas_comunicaciones.json`, campo `segmento` de cada cita).

  No cambié la regla después de ver estos casos.

  **[Fe de erratas, 02/10/2026.]** La causa que atribuí a las 11 citas de
  `rdbcra` es errónea. Sus segmentos traen el título completo, segunda parte
  incluida («… y Tramitación de Sumarios …»). Lo que impidió el mapeo fue un
  guion de fin de línea dentro del título («Cen- tral» y otros cortes), la
  misma causa que en `rrci`.
  - Medido con la segunda medición (sección 8,
    `citas_comunicaciones_2.json`): con el guion unido, las 11 se mapean por
    el título completo.
  - Las 14 no mapeables de esta primera medición quedan así: 12 por guion de
    fin de línea (11 de `rdbcra` y 1 de `rrci`) y 2 por el Anexo de una
    Comunicación.
  - Causa del error: leí los segmentos cortados a 150 caracteres y no
    verifiqué el resto.
  - La primera medición no cambia: este párrafo corrige solo la explicación.
- **Fórmulas de descubrimiento, aparte y sin sumar:** «incorporar» 126,
  «reemplazar» 62, «sustituir» fuera de la fórmula declarada 16, «dejar sin
  efecto» 13, «modificar» 13, «eliminar» 4, «agregar» 2, «suprimir» 2,
  «derogar» 1. Las fórmulas del mandato son una parte chica de las que usa el
  BCRA. Ampliarlas es una decisión pendiente, no aplicada.
- **Caso de control:** la «A» 8432, página 1, se mapea a `snp_psp`, punto
  1.3, con 5 unidades: `snp_psp::1.3.1.1`, `1.3.1.2`, `1.3.2::intro`,
  `1.3.2.1` y `1.3.2.2`. La página 4 de la misma Comunicación se mapea al
  punto 2.5, también con 5 unidades.

## 8. Segunda medición de la tercera fuente (M3, USD 0, sin red)

Declaración: `declaracion_citas_comunicaciones_2.json` (sha256 `0d5d5ee6…`).
- La escribí y le tomé el sha antes de escribir el script, que la lee tal cual
  y deja su sha en la salida.
- Misma ventana, mismo segmento, misma lectura del punto, mismas categorías y
  mismo caso de control que la primera.
- Cambian dos cosas:
  - las fórmulas: las cuatro de la primera más los nueve infinitivos que la
    primera había reportado aparte; un solapamiento cuenta una vez, con la
    fórmula de la primera;
  - el nombre del TO: se une el guion de fin de línea, y un título compuesto
    («… ) y …») se acepta por su primera parte si es inequívoca. Solo
    `rdbcra` es compuesto, y su primera parte se aceptó sin conflictos.
- La primera medición no se tocó: `citas_comunicaciones.json` mantiene su
  sha256 `0c034a43…`.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/code/medir_citas_comunicaciones_2.py --out data/experiment/mantenimiento/citas_comunicaciones_2.json
```

Resultado (`citas_comunicaciones_2.json`, dos corridas byte a byte idénticas),
las dos mediciones al lado:

| | Primera | Segunda |
|---|---:|---:|
| Comunicaciones con al menos una fórmula (de 195) | 8 | 145 |
| Citas | 21 | 260 (21 con fórmulas de la primera + 239 con infinitivos) |
| Citas que nombran punto y TO | 7 | 64 |
| Mapeadas a TO y unidades | 7 | 60 |
| Mapeadas solo a TO | 0 | 31 |
| No mapeables | 14 | 160 |
| No decidibles | 0 | 9 |

Desgloses de la segunda medición:
- **Por origen de la fórmula.**
  - Las 21 citas de las fórmulas de la primera: 19 a TO y unidades y 2 no
    mapeables. Las 2 son las del Anexo de una Comunicación.
  - Las 239 de los infinitivos: 41 a TO y unidades, 31 solo a TO, 158 no
    mapeables y 9 no decidibles.
- **Por mayúscula inicial del verbo** (desglose declarado, no filtra).
  - 88 citas con mayúscula: 56 a TO y unidades, 15 solo a TO, 14 no
    mapeables y 3 no decidibles.
  - 172 con minúscula: 4 a TO y unidades, 16 solo a TO, 146 no mapeables y 6
    no decidibles.

  Casi todo lo que se mapea viene de ítems dispositivos («1. Incorporar …»);
  el verbo en minúscula es en su mayoría prosa sin texto ordenado.
- **Por grupo.**
  - Corpus de 152: 47 a TO y unidades y 25 solo a TO.
  - Desarrollo: 13 a TO y unidades (`ext` 9 y `cap` 4) y 6 solo a TO (`ext` 3
    y `cap` 3). `cla` y `ric` no aparecen.
- **Primera parte del título compuesto:** mapea 1 cita (la «A» 8415, página
  1). Las 11 de `rdbcra` que la primera medición no mapeaba se resuelven por
  el guion unido (sección 7, fe de erratas).

Motivos de lo que sigue sin mapear en la segunda medición:
- No mapeables (160):
  - 98: la oración no nombra un texto ordenado;
  - 62: nombra un texto ordenado o normas que no están entre los títulos del
    inventario.
- No decidibles (9): más de un TO en la misma oración, por ejemplo `efemin`
  con `finsec`, o `cirmo3` con `docvig`. La lista completa está en la clave
  `motivos`.
- Solo a TO (31):
  - 17: sin numeral de punto;
  - 10: cita de sección;
  - 4: ningún numeral tiene unidades en la partición.

**Caso de control:** la «A» 8432, página 1, sigue dando `snp_psp`, punto
1.3, con 5 unidades.
