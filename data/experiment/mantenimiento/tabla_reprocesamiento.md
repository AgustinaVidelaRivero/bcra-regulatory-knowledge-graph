# Qué obliga a reprocesar y qué no

Tabla de mantenimiento del pipeline: para cada tipo de cambio, en qué paso entra, qué obliga a recomputar y
cuánto cuesta. La armé en U-MANT, etapa M1 (`e18d616`), para el perfil de la tanda 0 (`v3_b54`), y la actualicé
en U-TABLA-REPROC al perfil `r2b`, el de U-REEXT-T0 y de las tandas. La verifiqué contra la clave de la caché local
de E1 y de E3 con un selftest que arma los requests con el código del pipeline y no llama a la API
(`data/experiment/mantenimiento/code/selftest_clave_cache.py`). Costo: USD 0, sin red. El freno de
U-TABLA-REPROC, con la comparación contra la tabla de `e18d616`, está en
`data/experiment/mantenimiento/freno_utabla_reproc.md`.

## 1. Cómo se forma la clave (perfil r2b)

La clave de la caché local es sha256 del namespace, un salto de línea y el request canónico, que serializa todos
los kwargs del request con las claves ordenadas (`data/experiment/evaluacion/llm_cache.py:110-126`). Un cambio
obliga a pagar una unidad solo si mueve alguna de las dos cosas.

**Namespace.**
- E1: dominio, `CODE_VER` manual (`e1-extractor-v1`), hash del prefijo (system y tools) y marca de thinking
  (`reextraccion_v2/e1_extractor/cliente_e1.py:50`, `:122-143`). Con el perfil r2b:
  `e1_extraccion|cv=e1-extractor-v1-p322c5a23e9b7|think=0` (`prompt_r2b.py:170-172`).
- Reintento por salida mal formada: el mismo patrón con el sufijo `-rforma1` (`cliente_e1.py:76`):
  `e1_extraccion|cv=e1-extractor-v1-p322c5a23e9b7-rforma1|think=0`.
- Segundo reintento por salida mal formada (U-REEXT-T0, T2-bis): el sufijo `-rforma2` (`cliente_e1.py:77-80`):
  `e1_extraccion|cv=e1-extractor-v1-p322c5a23e9b7-rforma2|think=0`.
- E3: `e3_verificacion|cv=e3-verificador-v1-p21a836c7de6d|think=0` (`reextraccion_v2/e3_verificador/cliente_e3.py:49`,
  `:55-62`). Es el mismo de la tanda 0: el prompt de E3 no cambió con r2b.
- Los reintentos de E1 del ratchet usan el namespace de E1 del perfil, en `e3_verificador/cache/e1_reintentos.db`
  (`corpus_v2/runner_corpus.py:1431-1436`).

**Request de E1** (`reextraccion_v2/e1_extractor/prompt_r2b.py:440-450`):
- modelo, `max_tokens` (8.192, `:103`) y `temperature` 0 (U-PROMPT-R2, P5, `:109`);
- el prefijo de sistema (`:101-122`): el prefijo sellado v3, los reemplazos anclados, el bloque del catálogo r2 y el
  parche de P3b;
- el tool schema (`pyd_r2/generados/tool_schema_r2.json`, `:123`), con el enum de `sujeto_id`;
- `tool_choice`;
- el mensaje de usuario (`:342-388`), que lleva:
  - archivo, TO, tipo de unidad y rol del bloque, número y título, y los puntos admitidos;
  - la línea de alcance del TO (`rol_por_to_r2.json`, `:328-339`, `:356`);
  - el rótulo de la herencia (ítem de una lista y mini-chunk a mitad de oración, `:357-369`) y la línea del recorte
    (`:370-371`);
  - cada bloque heredado (tipo, unidad de origen y texto);
  - el bloque de tablas y marcas de E0 (`:232-265`): las tablas de e0-r2 con sus metadatos, la marca de contenido
    tabular y la de residual, la de fórmula, las evidencias y la lista de tablas forzadas a residual;
  - el texto y la línea de cierre (`:385-387`).

  No lleva el id de la unidad, sus páginas, sus sha256, sus conteos ni el detalle de `sub_chunk` o de
  `herencia_recortada` (de este último, solo si está).

**Request de E3** (`prompt_e3.py:422-439`):
- modelo, `max_tokens` (4.096) y thinking deshabilitado;
- el prefijo: instrucciones y calibradores (`:57-145`);
- el tool schema (`:152-196`);
- el mensaje (`:384-419`), que lleva:
  - archivo, TO, unidad y título;
  - las NOTAS: con la forma r2, las de `notas_r2` (`:333-381`), que cubren las tablas confiables, la estructura
    sin resolver, el encabezado de lista, el ítem de lista (U-E3-LISTAS, `:265-323`) y las omisiones de esquema;
  - el texto fuente: los encabezados heredados más el texto propio (`comun_e3.py:131-160`) y, con la forma r2, en
    un ítem de lista, el bloque que abre la lista (`comun_e3.py:111-128`);
  - la salida validada de E1 (`comun_e3.py:167-219`). Con la forma r2, esa salida la traduce `validador_e1`
    (`validador_e1.py:135-183`).

E3 no recibe los bloques de prosa heredados, salvo uno desde U-E3-LISTAS (fila F23b): con la forma r2, en un ítem
de lista recibe el bloque que abre la lista, con los bloques contiguos del mismo tipo y la misma unidad de origen
(D2), en el fuente del mensaje y en el de las citas (`ratchet_e3.py:283`). Los cierres que siguen a ese bloque y
los bloques de prosa de los ancestros siguen sin entrar: para ellos, la frase de las instrucciones de E3 que dice
que E3 recibe «párrafos introductorios, intersticiales y de cierre» (`prompt_e3.py:57`) no se cumple, y no se
edita porque es el prefijo de E3 (F10).

**Reintento del ratchet:**
- el request de E1 del perfil, con el bloque de feedback anexado al mensaje (`ratchet_e3.py:311-374`);
- `max_tokens` de 16.384 (`runner_corpus.py:89`); en las unidades cuyo E1 usó el tercer escalón, 40.960 (fila F08d).

**Archivos de datos que entran a los requests** (inventario del selftest, proceso hijo con registro de aperturas):
- Al construir el perfil r2b:
  - `catalogo_unico/catalogo_sujetos_r2.json` y `catalogo_unico/generados_r2/enums_tool_schema_r2.json`;
  - `bloque_catalogo_r2.txt`, `rol_por_to_r2.json` y `labels_e2_r2.json`, de los mismos generados, y el derivado del registro de
    alcance por tanda, `catalogo_unico/registro_alcance_r2b.json` (F13c; desde A2 de U-ALCANCE-E1);
  - `pyd_r2/generados/tool_schema_r2.json`;
  - `prompt_r2b_reemplazos.json`, `prompt_r2b_parche_p3b.json`, `prompt_r2b_parche_p3c.json`,
    `tablas_residuales_forzadas_r2b.json` y `candado_mensaje_r2b.json`;
  - `grafo_v2/esquema_v2_clases.json`, por la cadena sellada.
- Al importar E3: los cuatro archivos de los calibradores (`calibradores_e3.py:82-84`) y `candado_mensaje_e3.json`.
- Al validar la salida de E1: `pyd_r2/politica_campos_r2.json`.
- No los abre el armado de ningún request:
  - `pies_<to>.json`;
  - `indice_e4_r2.json`, `entrada_esqueleto_r2.json`, `ids_s19_r2.json` y `catalogo_suite_r2.json`;
  - el registro de alcance por tanda (`catalogo_unico/registro_alcance_por_tanda.md`; el mensaje lee su derivado, F13c) y los
    generados del catálogo de resolución (`manifest_generados_resolucion_r2.json`, sus ampliaciones y el compuesto).

**Candados:**
- Del perfil r2b, contra el congelado de P3c-2:
  - los sha256 y el hash canónico del prefijo (`perfil_e1.py:78-81`, `:213-218`);
  - el sha256 de cada insumo del prefijo y del mensaje (`prompt_r2b.py:77-98`, `:113-118`, `:130-162`).
- Del catálogo r2 (`pyd_r2/code/modelos_r2.py:61-96`) y del manifiesto de sus generados en el ensamblado
  (`corpus_v2/r1_e4.py:564-583`).
- De la cadena sellada v2 (`esq/code/prompt_congelado.py:156-160`).
- Del prefijo de E3, desde `924ef4d` (`prompt_e3.py:450-456`).
- De la política r2, en los dos lugares que la leen (`validador_e1.py:102` y `r1_e4.py:541`).

Desde P3c-2 de U-PROMPT-R2 tienen candado: la lista de tablas forzadas (su sha256), las líneas del mensaje de E1 y
las NOTAS de E3 (el sha256 del mensaje de un conjunto fijo de unidades). Un cambio frena hasta re-sellar (filas F04b,
F22, F22b y F23). Desde U-E3-LISTAS el conjunto fijo de E3 tiene tres ítems de lista, y frena también un cambio
del bloque que abre la lista o de la NOTA del ítem (F23b).

## 2. Las cuatro clases y el principio de cada fila

- **nada**: ningún paso se vuelve a correr; el grafo guardado sigue valiendo.
- **solo código sobre lo guardado**: se re-aplican pasos determinísticos sobre la salida guardada de E1 y E3, sin
  llamadas a la API.
- **E1 y E3 de las afectadas**: llaman a la API solo las unidades cuyo request cambia, en E1, en E3 o en las dos;
  el resto sale de la caché.
- **todo**: llaman a la API todas las unidades del corpus en al menos una de las dos etapas.

Dos estados más, que no son clases:
- **frena**: un candado detiene la corrida antes de armar ningún request; una vez re-sellado, rige la clase de la
  fila del contenido;
- **PENDIENTE**: la fila depende de un diseño todavía no cerrado.

Principio 12 (plan, `docs/plan_tesis.md:299`): rige las filas en las que el cambio vive en código y se re-aplica
sobre lo guardado a USD 0. Principio 9 (`docs/plan_tesis.md:277`): rige las filas que obligan a llamar a la API o
que vienen de la fuente; el resultado es otra versión del grafo, declarada como release, y el grafo evaluado no se
corrige.

Lectura de las columnas de clave: **Clave E1** y **Clave E3** dicen el efecto directo del cambio sobre el request
de cada etapa, con todo lo demás fijo. Con el perfil r2b, E1 corre con temperatura 0, fijada en el pedido
(U-PROMPT-R2, P5; fila F08e), y eso no vuelve determinística la respuesta: en P5, 6 de 27 respuestas salieron iguales
byte a byte entre dos corridas del mismo pedido (`data/experiment/prompt_r2/freno_p5.md`). E3 corre sin temperatura
fijada, porque su modelo rechaza un valor distinto del de por defecto. De modo que toda unidad que se vuelve a llamar
en E1 puede traer una salida nueva y, con ella, un request de E3 nuevo: eso va en la columna «Qué obliga a
recomputar», no en la de la clave de E3.

**Relación con el protocolo entre tandas.** El eje A del protocolo (`docs/protocolo_entre_tandas.md`, FIRMADO en
`a304b89`, `:76-85`) clasifica los hallazgos con esta tabla. Tres filas difieren del texto firmado, y en las tres
la tabla sigue la composición real de la clave, por decisión de la autora del 04/10/2026:
- F05: el protocolo la pone en «E1 y E3 de las afectadas» (`:82`);
- F10: en «todo» con E1 y E3 (`:84-85`);
- F14: en «solo código» (`:79-80`).

La enmienda 3 al protocolo quedó firmada el 04/10/2026 (`0cb0c70`; asentado el 06/10/2026 en T5 de U-REEXT-T0). F13 quedó implementada por R2 de U-RERESOL-CAT (R1 en `c98093a`; R2-1 y R2-1 bis en `0737497`; R2-2 en `a079275`; asentado el 07/10/2026): ver las filas F13, F13b y F13c y su nota.

## 3. La tabla

| Fila | Cambio | Dónde entra | Qué obliga a recomputar | Clave E1 | Clave E3 | Clase | Principio | Ancla | Variación del selftest |
|---|---|---|---|---|---|---|---|---|---|
| F01 | Texto propio de una unidad de E0, incluidas las correcciones de e0-r2 que cambian texto (números de encabezado corregidos, cola de título estricta, renglones conservados por K) | E0; texto del mensaje de E1 y texto propio del fuente de E3 | E1 y E3 de esa unidad; E2 y ensamblado en código | cambia (esa unidad) | cambia (esa unidad) | E1 y E3 de las afectadas | 9 | `prompt_r2b.py:433`; `comun_e3.py:155-159`; `correr_e0.py:86-94` | R01 |
| F02 | Texto de un bloque heredado de tipo encabezado (título de un ancestro) | E0; herencia del mensaje de E1 y del fuente de E3 de cada unidad que lo hereda | E1 y E3 de todas las unidades que heredan ese encabezado | cambia (las que lo heredan) | cambia (las que lo heredan) | E1 y E3 de las afectadas | 9 | `prompt_r2b.py:423-425`; `comun_e3.py:150-154` | R02 |
| F03 | Texto de un bloque heredado de prosa (intro, cierre, chapeau de sección, intersticial) | E0; mini-chunk del bloque (fila F01) y herencia del mensaje de E1 de los descendientes; no entra al fuente de E3 de los descendientes, salvo el bloque que abre la lista de un ítem, con la forma r2 (F23b) | E1 del mini-chunk y de los descendientes que lo heredan; E3 de esas unidades porque cambia su salida de E1, y el de los ítems cuyo bloque que abre la lista es ese | cambia (los descendientes que lo heredan) | cambia (solo los ítems cuyo bloque que abre la lista es ese, con la forma r2; los demás descendientes, no, con la salida de E1 fija) | E1 y E3 de las afectadas | 9 | `prompt_r2b.py:423-425`; `comun_e3.py:150-152`, `:111-128` | R03 |
| F04 | Marcas de E0 sin cambio de texto: contenido tabular, residual, fórmula y sus evidencias, y los metadatos de las tablas serializadas por e0-r2 (modo, celdas propagadas o con alcance, filas de subtítulo, combinadas sin propagar) | E0; bloque de tablas y marcas del mensaje de E1 y NOTA de E3 | E1 y E3 de las unidades re-marcadas | cambia (las re-marcadas) | cambia (las re-marcadas) | E1 y E3 de las afectadas | 9 | `prompt_r2b.py:206-303`; `prompt_e3.py:224-239`, `:333-374` | R04, R04b |
| F04b | Lista de tablas forzadas a residual (`tablas_residuales_forzadas_r2b.json`): alta o baja de una tabla | al construir el perfil de E1: la lista se lee con su sha256 (candado de U-PROMPT-R2, P3c-2), y el candado del mensaje de E1 la ejercita; re-sellada, el mensaje de E1 y la NOTA de E3 de las unidades que traen la tabla | nada se arma hasta re-sellar la lista y el candado del mensaje; re-sellada, E1 y E3 de las unidades que traen la tabla | frena (candado de la lista) | frena (sin perfil no hay salida validada de E1) | frena; re-sellada, E1 y E3 de las afectadas | 9 | `prompt_r2b.py:180-189` (candado `TABLAS_FORZADAS_SHA256_ESPERADO`), `:491-513`; `prompt_e3.py:333-381` | R32 |
| F05 | Páginas, id, sha256 y conteos de caracteres de una unidad sin cambio de texto (corrimiento de páginas; ids desambiguados por e0-r2, `BKL-0037`) | E0; procedencia que arma E2 e identidad de los registros persistidos | E2 y ensamblado en código | no cambia | no cambia | solo código sobre lo guardado (difiere del protocolo, `a304b89:82`; lo fija la enmienda 3 al protocolo entre tandas, firmada el 04/10/2026 en `0cb0c70`, §1, punto 1) | 12 | `prompt_r2b.py:395-437` y `prompt_e3.py:384-419` no leen esos campos; `runner_corpus.py:163-175` | R05, R06 |
| F06 | Prefijo de E1 r2b (texto de sistema: prefijo sellado v3, reemplazos anclados, parche de P3b) | E1; system del request y hash del prefijo en el namespace | E1 de todas las unidades; E3 de todas por la salida nueva de E1; re-sello del perfil (antes frenan los candados: F11b) | cambia (todas, con namespace nuevo) | no cambia (con la salida de E1 fija) | todo | 9 | `prompt_r2b.py:130-159`, `:170-177`; `cliente_e1.py:122-143`; candado `perfil_e1.py:213-218` | R08 |
| F07 | Tool schema de E1 r2b (`tool_schema_r2.json`) | E1; tools del request y hash del prefijo | igual que F06 | cambia (todas, con namespace nuevo) | no cambia (con la salida de E1 fija) | todo | 9 | `prompt_r2b.py:160`, `:170-172` | R09 |
| F08 | Modelo o `max_tokens` del request base de E1 (modelo, `max_tokens` de 8.192) | E1; request | E1 de todas; E3 de todas por la salida nueva | cambia (todas) | no cambia (con la salida de E1 fija) | todo | 9 | `runner_corpus.py:91`; `prompt_r2b.py:103`, `:440-450` | R12, R13 |
| F08b | Techos de los reintentos: el del corte de E1 del perfil r2 (16.384) y el del ratchet de E3 (16.384) | request del reintento, solo en las unidades que reintentan | E1 de las unidades que cortan o que reintentan en el ratchet, y su E3 | cambia (solo los requests de reintento) | no cambia (con la salida de E1 fija) | E1 y E3 de las afectadas | 9 | `cliente_e1.py:68`, `:411-450`; `runner_corpus.py:89`, `:625-626` | R13b |
| F08c | Reintento por salida de E1 mal formada: el request que produjo la salida, con `temperature` 1 (perfil r2b, U-PROMPT-R2, P5), en el namespace `-rforma1`; si vuelve mal formado, un segundo reintento con el mismo request en el namespace `-rforma2`, una sola vez (U-REEXT-T0, T2-bis) (sufijos, disparos, motivos de forma o temperatura del reintento) | namespace y temperatura de los reintentos; solo las unidades cuya salida `validador_e1` rechaza entera por su forma | E1 de esas unidades en su namespace y su E3 | cambia (solo los reintentos de las mal formadas) | no cambia (con la salida de E1 fija) | E1 y E3 de las afectadas | 9 | `cliente_e1.py:76`, `:77-80`, `:122-143`, `:285-300`; `prompt_r2b.py:110`, `:453-456`; `runner_corpus.py:475-480`, `:505-513`, `:529-541`, `:680-709`, `:808-815` | R25, R25b |
| F08d | Tercer escalón del reintento por corte del perfil r2 (U-PROMPT-R2, P3c-2): transmisión por partes con techo 40.960, solo si el reintento de 16.384 corta y la unidad no se parte, o si corta una parte; y el reintento del ratchet de esas unidades al mismo techo | request del tercer intento y del reintento del ratchet, solo en esas unidades; mismo namespace de E1, por el adaptador de transmisión debajo de la caché | E1 de esas unidades y su E3 | cambia (solo esos requests) | no cambia (con la salida de E1 fija) | E1 y E3 de las afectadas | 9 | `cliente_e1.py:83-119`, `:265-283`, `:411-450`; `runner_corpus.py:482-502`, `:646-659`, `:736-739`, `:892` | R13c |
| F08e | Temperatura del pedido de E1 del perfil r2b (U-PROMPT-R2, P5): `temperature` 0, fijada en el pedido base, del que salen el primer intento, el reintento por corte, el tercer escalón y el reintento del ratchet | E1; request (`temperature`); no entra al hash del prefijo ni al namespace | E1 de todas; E3 de todas por la salida nueva | cambia (todas) | no cambia (con la salida de E1 fija) | todo | 9 | `prompt_r2b.py:105-110`, `:445`; `cliente_e1.py:441-449`; `ratchet_e3.py:366-368` | R14 |
| F08f | Reparación acotada de la salida de E1 sin la clave `relations` (U-REEXT-T0, T2-ter; decisión de la autora del 06/10/2026): la forma reparable (dict con `entities` lista y sin la clave `relations`), el momento (agotados los dos reintentos por forma, solo con el perfil r2b) y la condición de aceptación (con `relations = []`, `validador_e1` no rechaza el chunk); la unidad queda marcada (`reparacion_forma`) y contada aparte (`reparadas_forma`) | runner, al cerrar el camino de forma, después de agotar los reintentos; sobre la respuesta guardada, no sobre el request | E3 de las reparadas (reclama las relaciones que falten); E2 de su TO en código | no cambia | cambia (las reparadas: su validación es otra) | E3 de las afectadas | 9 | `runner_corpus.py:542-559`, `:710-720`, `:727-728`, `:816-819` | R18 (la misma variación que F14: la salida validada de E1 alterada en código mueve la clave de E3 y no la de E1); una variación propia de la reparación queda pendiente para la unidad de mantenimiento del runner (checklist, fila P20) |
| F09 | Versión de código del namespace (`CODE_VER` de E1), con el request idéntico | namespace de la caché | igual que F06, sin cambiar un byte del request | cambia (todas) | no cambia | todo | 9 | `cliente_e1.py:50`, `:139-143` | R15 |
| F10 | Prompt de E3 (instrucciones, calibradores o tool schema) o su modelo | E3; system, tools y modelo del request, y hash del prefijo en el namespace | E3 de todas las unidades; E1 base sale de la caché; los reintentos de E1 del ratchet cambian donde cambia el feedback | no cambia | cambia (todas, con namespace nuevo si cambia el prefijo; antes frena el candado: F10b) | todo, con E3 de todas (difiere del protocolo, `a304b89:84-85`; lo fija la enmienda 3 al protocolo entre tandas, firmada el 04/10/2026 en `0cb0c70`, §1, punto 2) | 9 | `prompt_e3.py:57-145`, `:152-196`, `:213-217`, `:422-439`; `cliente_e3.py:55-62`; `runner_corpus.py:94` | R16, R17 |
| F10b | Archivos de datos de los calibradores de E3, con el candado del prefijo de E3 (`924ef4d`) | al importar `prompt_e3` | nada se arma hasta re-sellar el prefijo de E3; re-sellado, F10 | no cambia | frena (candado del prefijo de E3) | frena; re-sellado, todo (F10) | 9 | `prompt_e3.py:450-456`; `calibradores_e3.py:82-84` | R22d |
| F11 | Catálogo de sujetos en el bloque del prefijo de E1 o en el enum de `sujeto_id`, incluido un rol de alcance nuevo (sección «Roles de alcance por TO» del bloque) | E1; system y tools | igual que F06; los candados frenan hasta el re-sello (F11b, F13b) | cambia (todas, con namespace nuevo) | no cambia (con la salida de E1 fija) | todo | 9 | `prompt_r2b.py:72`, `:80`, `:137-142`; `modelos_r2.py:692`; `generar_desde_catalogo.py:118`, `:133` | R10, R10b |
| F11b | Archivos de datos con candado que arman el prefijo o el mensaje de E1 r2b: reemplazos anclados, parche de P3b, bloque de catálogo, tool schema, `rol_por_to_r2.json`, `labels_e2_r2.json`, el derivado del registro de alcance por tanda (`registro_alcance_r2b.json`, desde A2 de U-ALCANCE-E1) y, por la cadena sellada, `esquema_v2_clases.json` | al construir el perfil de E1 | nada se arma hasta re-sellar; re-sellado, la fila del contenido (F06, F07, F11, F12 o F13c) | frena (candado al construir el perfil) | frena (sin perfil no hay salida validada de E1) | frena; re-sellado, la clase de la fila del contenido | 9 | `prompt_r2b.py:77-98`, `:113-118`, `:130-162`, `:477-479`; `perfil_e1.py:213-218`; `prompt_congelado.py:156-160` | R21, R22, R22b |
| F12 | Tabla TO→rol de alcance (`rol_por_to_r2.json`, línea «Alcance de este TO»): una entrada de clase para un TO en la tabla de la release (entre tandas, la entrada de un documento nuevo va al registro de alcance por tanda, F13c) | E1; mensaje de usuario de las unidades de ese TO; en el ensamblado, el sujeto por defecto de una expresión colectiva | E1 y E3 de las unidades de ese TO; ensamblado en código | cambia (las del TO) | no cambia (con la salida de E1 fija) | E1 y E3 de las afectadas | 9 | `prompt_r2b.py:376-392`, `:409`; `r1_e4.py:391`; candado `prompt_r2b.py:81` | R11 |
| F13 | Catálogo de resolución, que lee solo el código: la lista de ampliaciones que solo agrega (alta de un id con su padre, o de un alias de un id existente), compuesta con el catálogo del request y leída con su candado (`r1_e4.catalogo_resolucion_r2`; manifiesto `manifest_generados_resolucion_r2.json`) | E4, E2, merge entre TOs, esqueleto, S19 y la suite, sobre lo guardado; el bloque del prefijo, el enum y el tool schema salen solo del catálogo del request | re-resolución del registro de no mapeados, E2 y ensamblado en código (`reresolver_catalogo.py` rehace el grafo desde el crudo guardado a USD 0 y lo verifica; el reporte dice cuántas relaciones resolvió cada versión del catálogo); ningún request | no cambia | no cambia | solo código sobre lo guardado | 12 | `r1_e4.py:598-647`; `ensamblar_tanda0.py:1847-1909` (`--catalogo-resolucion`, W1 de R2-1); `scripts/regression_kg.py:467-471`, `:1820-1830` (`--generados-resolucion`, W3); `reresolucion_catalogo/reresolver_catalogo.py`; enmienda 2 al protocolo (`0b98045`) y enmienda 4 §1 (BORRADOR) | R20 |
| F13b | Un id nuevo en `catalogo_sujetos_r2.json`, el catálogo del request (cambio de release; entre tandas, un id o un alias nuevo va al catálogo de resolución, F13, sin tocar el request) | candado del catálogo al construir el perfil; re-sellado, el bloque del prefijo y el enum (F11) | nada se arma hasta re-sellar el catálogo y sus generados; re-sellado, E1 y E3 de todas | frena (candado del catálogo) | frena (sin perfil no hay salida validada de E1) | frena; re-sellado, todo (F11) | 9 | `modelos_r2.py:61-96`; `prompt_r2b.py:80`; `r1_e4.py:570-577`; `generar_desde_catalogo.py:118`, `:133`, `:138` | R22c |
| F13c | Registro de alcance por tanda (`catalogo_unico/registro_alcance_por_tanda.md`, legible por código desde R2-2 de U-RERESOL-CAT) y su derivado para E1 (`catalogo_unico/registro_alcance_r2b.json`, que escribe `catalogo_unico/code/derivar_registro_alcance_r2b.py` con el mismo lector): una entrada de clase o de rol reutilizado para un documento nuevo, o un documento declarado sin alcance | en el ensamblado, el `rol_por_to` del catálogo de resolución: la resolución por relación (R4 o R3 si el documento recibe alcance; cuarentena por la parte A de la enmienda 6 a L-ESQ-R2 si no lo tiene, solo en r2b); en E1, desde A2 de U-ALCANCE-E1 (15/10/2026), la línea «Alcance de este TO» del mensaje: `prompt_r2b.py` lee el derivado al importar, con su candado, y lo usa cuando el documento no tiene entrada en la tabla de la release (F12); un documento declarado sin alcance no tiene entrada en el derivado y va sin línea. El perfil r2b expone la misma regla en su tabla TO→rol, la que valida el manifiesto de la tanda (`perfil_e1.py:236`). Hasta A2 el mensaje no leía el registro (R2-2 lo midió idéntico en las 2.439 unidades y en los 13 casos del candado). Desde A3 de U-ALCANCE-E1 (18/10/2026), el derivado de la tanda final: `--tandas 1,final` suma las 33 entradas con alcance de la tabla «## Tanda final» del registro, sin reprocesamiento, porque la tanda final no está extraída; las 10 de la tanda 1 y los mensajes de las tandas 0 y 1 salen byte a byte iguales | regenerar el derivado y re-sellar su sha (el candado del derivado frena hasta entonces, y el del mensaje si el documento está en su fixture); el manifiesto de una tanda ya armado declara el rol anterior y frena al cargarse hasta volver a armarlo; resolución, E2 y ensamblado en código; E1 y E3 de las unidades del documento que recibe alcance, como F12, si ya estaban extraídas | cambia (las unidades del documento que recibe alcance, como F12; con el derivado regenerado y sin re-sellar, el candado frena) | no cambia (con la salida de E1 fija) | E1 y E3 de las afectadas (F12); sin unidades ya extraídas del documento, solo código sobre lo guardado | 9 | `prompt_r2b.py:409`, `:477-479` (derivado y su candado), `:482-488` (`alcance_del_documento`); `perfil_e1.py:236`; `catalogo_unico/code/derivar_registro_alcance_r2b.py`; `r1_e4.py:422-428` (parte A), `:598-647`; `reresolucion_catalogo/reresolver_catalogo.py:159`, `:199` (lector), `--registro-alcance`; enmienda 4 al protocolo, §2 y §7 (FIRMADA, `53bbd6f`) | R34 |
| F14 | Validador de E1 (`validador_e1`), con las correcciones de tipo y predicado que toma de `validador_r2` y su política, la traducción de la forma r2 y el índice del crudo | sobre la salida cruda de E1 guardada, antes de E3: su salida es el mensaje de E3 | validación en código y E3 de las unidades cuya salida validada cambia, porque el ensamblado r2b toma solo lo que vio E3; E1 sale de la caché | no cambia | cambia (las unidades cuya salida validada cambia) | E1 y E3 de las afectadas (difiere del protocolo, `a304b89:79-80`; lo fija la enmienda 3 al protocolo entre tandas, firmada el 04/10/2026 en `0cb0c70`, §1, punto 3, con la regla de cruce del §3, `bd77541`) | 9 | `validador_e1.py:98-118`, `:135-222`, `:388-391`; `comun_e3.py:167-219`; `runner_corpus.py:1188-1195` | R18 |
| F14b | Validador r2 y su política en el ensamblado (`validador_r2.validar` con lo que vio E3) | sobre el crudo guardado del intento que aceptó E3 | entrada r2, E2 y ensamblado en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `validador_r2.py:781`, `:793-794`, `:1119-1121`, `:1336-1338`; `runner_corpus.py:1231-1243`; candados `r1_e4.py:541`, `validador_e1.py:102`; U-OMISIONES-COD: la mención con contracciones (`validador_r2.py:212`, `:219`, `:1285`) y el tipo de la Comunicacion desde el código (`:543`, `:1047`, `:1052`) | R19 |
| F15 | E2 r2 y ensamblado (entrada r2, fusión, merge cross-TO, cola humana marcada, omisiones, aristas derivadas que tocan la cola, procedencia, reportes) | después de E3, sobre el crudo guardado y `finales.jsonl` | E2 y ensamblado en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `runner_corpus.py:1151-1206`, `:1246-1296`; `tanda0/code/ensamblar_tanda0.py:1846-2125`; U-OMISIONES-COD: G-r (`ensamblar_tanda0.py:1372`, `:1415`, `:1925`), las marcas del registro de omisiones y los supuestos dentro de una norma (`:1612`, `:1639`, `:1937`), las aristas por origen (`:1658`) y la causa de la unidad excluida (`:1682`, `:2028`) | R19 |
| F15b | Umbrales (cuantías, comparador, negación, plazo sin marcador, base) | ensamblado r2 | umbrales y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `ensamblar_tanda0.py:792`, `:2085`; `reglas_comparacion.py:246`, `:502`, `:710`; U-OMISIONES-COD: la base (`ensamblar_tanda0.py:668`, `:677`, `:731`, `:764`) y el tramo de E1 (`:742`) | R19 |
| F15c | `remite_a` (detector de citas: reglas (a) a (i), citas a otra norma y a anexos de Comunicaciones) | ensamblado r2, sobre el texto de la E0 e0-r2 | remisiones y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `r1_referencias.py:702`, `:1027`; `ensamblar_tanda0.py:2021`; U-OMISIONES-COD: la procedencia de cada origen y el agrupamiento sin el rol (`r1_referencias.py:1139`, `:1144`; `ensamblar_tanda0.py:2022`) | R19 |
| F15d | Sujetos por relación (reglas R1 a R4, registro de no mapeados y, solo en r2b, la parte A de la enmienda 6 a L-ESQ-R2: cuarentena en los documentos sin alcance, R2-2) | ensamblado r2 | resolución, E2 y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `r1_e4.py:306`, `:388`, `:422-428`; `ensamblar_tanda0.py:993` (normalizar_propuestos_r2b), `:1060-1085` (padre del propuesto sin padre del modelo en un documento sin alcance, con cualquier motivo: R2-3 para la parte A, R2-3 bis `dac7d57` para el resto), `:1929`; U-OMISIONES-COD: el singular «entidad» de R3 con la opción (ii) (`r1_e4.py:310`, `:381`) | R19 |
| F15e | Unión de las operaciones por punto (fase r2b) | E2 r2 | E2 y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `e2_lib.py:845-871`, `:869-870` | R19 |
| F15f | Procedencia de un tramo que solo vio E1 (C1 y C2, U-PROC-HERENCIA): el punto y el rol de una entidad declarada con el punto propio cuyo tramo está solo en un bloque heredado que E3 no ve, y la marca tramo_fuera_del_texto_de_e3; con la opción D (registro de decisiones, §49): C1 no se aplica si la entidad pasaría a tener el id de otro nodo del ensamblado (unión evitada), y el detector de remisiones lee y resuelve la procedencia de C1 con el punto y el rol que declaró E1 | ensamblado r2, sobre el crudo guardado, con --procedencia-heredada (apagada por defecto: sin ella, el ensamblado de siempre) | E2, remisiones y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | la función: `ensamblar_tanda0.py:1415-1416` (`corregir_procedencia_g_r` con la bandera), `:1425-1430` (lo que declaró E1, antes de G-r), `:1457`, `:1461` (`bloque_ubicado_g_r`), `:1474` (`id_nodo_e2_r2`, el id de E2) y `:1485` (`procedencia_heredada_c1_c2`), con la unión evitada en `:1542-1558`; `r1_referencias.py:1261-1269` (la procedencia de C1 leída con el punto de E1) y `:1089`; el parámetro: `ensamblar_tanda0.py:1848` y `:1899-1900` (`correr_cadena_r2`), `:2200` (`ensamblar_manifiesto_r2`) y `:2344` (`--procedencia-heredada`); `r1_referencias.py:1034` (`detectar_y_resolver_r2`); su llamada: `ensamblar_tanda0.py:1925-1928`, `:2023` (el detector), `:2241-2243`, `:2245-2247` y `:2386`, con el registro en `:2072-2082`; `comun_e3.py:111`, `:131`, `:226` | R19 |
| F15g | Unión de las Comunicacion de documentos distintos con el mismo código normalizado (C1 de U-MED-DESAMB), con la lista de los códigos que no se unen | ensamblado r2, sobre el crudo guardado, con --union-comunicaciones (apagada por defecto: sin ella, el ensamblado de siempre) | E2, remisiones y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | la función: `ensamblar_tanda0.py:1727` (`cargar_union_comunicaciones`: las dos listas con su sha256 y la normalización cargada de su archivo con su candado, `:80-82`), `:1763` (`ids_con_la_guarda`) y `:1772` (`preparar_union_c1`: los grupos por código, la lista de los códigos, la de los nodos y la regla de los menos de 2 nodos o de 2 documentos, con el renombre previo de la guarda en `:1812`); `r1_invariantes.py:113` (`merge_grafos_guardado` con `codigo_comunicacion`), `:133` (la colisión unida no va a la adjudicación) y `:174` (`_unir_comunicaciones_c1`); la normalización: `med_desamb/parte2/tamanos_desamb_mesa.py:215` (`codigo_normalizado`); el parámetro: `ensamblar_tanda0.py:1848` (`correr_cadena_r2`), `:2201` (`ensamblar_manifiesto_r2`) y `:2348-2370` (`--union-comunicaciones`, `--union-comunicaciones-nodos` y sus sha256), con `:2398` (solo en la cadena r2); su llamada: `ensamblar_tanda0.py:1965-1969` (`INV.merge_grafos_guardado` recibe `codigo_comunicacion` solo con la bandera), con el registro (uniones_c1.json) y el resumen en `:1974-1982`, `:2242`, `:2246` y `:2382-2387`; la lista de los códigos: `med_desamb/c1_cadena/armar_no_unir_c1.py`; la normalización, entre los módulos que R19 bloquea: `selftest_clave_cache.py:180-181` | R19 |
| F15h | Remisión a un punto padre o a una sección cuyos subpuntos tienen nodos: el primer nivel con nodos de su subárbol (opción B, con D-3), en una segunda pasada que no toca las remite_a que ya existen | ensamblado r2, sobre el crudo guardado, con --remisiones-a-subpuntos (apagada por defecto: sin ella, el ensamblado de siempre) | remisiones y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | la opción: `r1_referencias.py:1377-1433` (la segunda pasada sobre el registro, antes de armar `nuevas`), con la cita a una unidad excluida en `:1398-1401`, el primer nivel con nodos del subárbol en `:1402-1407`, D-3 en `:1408-1409`, el par que ya es arista de la resolución exacta, sin tocar, en `:1421-1423` y la marca del destino en `:1426-1427`; la procedencia de cada cita: `:1142`, `:1181`; el resumen: `:1495-1496`; el parámetro: `r1_referencias.py:1034-1035` (`detectar_y_resolver_r2`), `ensamblar_tanda0.py:1849` (`correr_cadena_r2`), `:2201` (`ensamblar_manifiesto_r2`) y `:2360` (`--remisiones-a-subpuntos`); su llamada: `ensamblar_tanda0.py:2019-2020` (la lista `excluidas`, armada antes del detector), `:2021-2024` (el detector), `:2028` (su uso de siempre), `:2243`, `:2247`, `:2387` y `:2399` | R19 |
| F16 | E4 y esqueleto (TextoOrdenado canónico, esqueleto del catálogo r2, `establecida_en` derivada) | después del merge | E4, esqueleto y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `ensamblar_tanda0.py:1994`, `:2012`, `:605`, `:2036` | R19 |
| F16b | Metadato de los pies (`pies_<to>.json`): versión vigente y carátula del TextoOrdenado | E0 e0-r2 escribe el archivo; lo lee el ensamblado, no el armado de los requests | versión y materia del TextoOrdenado y lo que sigue, en código | no cambia | no cambia | solo código sobre lo guardado | 12 | `correr_e0.py:1767-1768`; `e0_lib.py:1602-1632`; `ensamblar_tanda0.py:1288` | R28 |
| F17 | Un TO nuevo | E0 e0-r2 sobre su PDF; E1 y E3 de sus unidades; ensamblado | E0, E1 y E3 de todas sus unidades; los demás TOs salen de la caché. Más F12 si recibe una entrada de clase; si necesita un rol nuevo, entra sin línea de alcance, declarado; su alcance se lee antes de extraer y entra por el registro por tanda (F13c) | cambia (todas las del TO nuevo: sin clave previa) | cambia (todas las del TO nuevo; no verificable en el selftest: no hay salida de E1 previa) | E1 y E3 de las afectadas | 9 | `runner_corpus.py:616-623`; `prompt_r2b.py:383-385`; `docs/mandatos/URERESOL_CAT_reresolucion_catalogo.md:165-171` | R23 |
| F18a | Un TO modificado en el sitio, con el cambio solo en páginas que E0 no convierte en unidades (portada, índice, tabla de origen, historial) | E0 e0-r2 sobre el PDF nuevo, dentro de una release declarada | ninguna llamada si E0 devuelve las mismas unidades byte a byte; se re-sella el sha del PDF; si cambia el pie de alguna página, F16b | no cambia (unidades idénticas) | no cambia (unidades idénticas) | nada; solo código si cambia la versión del pie (F16b) | 9 | `e0_chunking/e0_lib.py:1131-1185`, `:2068-2069` | A1, A3, A1r, A3r, R00 |
| F18b | Un TO modificado en el sitio, con cambio en páginas de cuerpo | E0 e0-r2 sobre el PDF nuevo, dentro de una release declarada | E1 y E3 de las unidades cuyo request cambia (filas F01 a F04, F19 y F21); el resto sale de la caché; F16b por el pie | cambia (las unidades cuyo request cambia) | cambia (las unidades cuyo request cambia) | E1 y E3 de las afectadas | 9 | `e0_lib.py:2068-2069`; `prompt_r2b.py:395-437` | R01, R02, R04, R07 |
| F19 | Una unidad agregada o retirada por un cambio de numeración | E0; la unidad nueva y las renumeradas cambian su número, el numeral del texto y la herencia de sus descendientes | E1 y E3 de la unidad nueva, de las hermanas renumeradas y de sus descendientes; una unidad retirada no llama a la API y sale del ensamblado en código | cambia (nueva, renumeradas y descendientes) | cambia (renumeradas y descendientes) | E1 y E3 de las afectadas | 9 | `prompt_r2b.py:402-407`, `:423-425`; `comun_e1.py:63-87` | R24, R07 |
| F19b | Una unidad agregada o retirada por una regla de segmentación de E0 (release de e0-r2), sin cambio en el PDF | E0 e0-r2: texto, id y herencia de la unidad nueva, y la herencia de las unidades que la citan | E1 y E3 de las unidades nuevas y de las que cambian texto o herencia (F01 a F03); una unidad retirada no llama a la API y sale del ensamblado en código | cambia (nuevas: sin clave previa) | cambia (nuevas) | E1 y E3 de las afectadas | 9 | `correr_e0.py:95-100` (reglas de S0-2), `:474-486` (regla 6), `:723-732` (regla 9), `:1452` (T); `e0_lib.py:394` (regla 8), `:782` (regla 3, ampliación); `correr_e0.py:119-138` (reglas de S0-4, de `REGLAS_S0_4` a `TOS_TANDA0_SIN_4AB`), `:140-205` (reglas de S0-5: sus constantes, de `REGLAS_S0_5` a `RAICES_POR_LISTA_S0_5`, con `LISTAS_R5A_S0_5` y `ROTULOS_POR_LISTA_S0_5`), `:246-252` (`_r5`); `e0_lib.py:203-226` (la descripción de las reglas de S0-4 y S0-5, en el docstring del módulo) | R24 (la unidad nueva de la renumeración; sin variación propia: en la tanda 0 no ocurre) |
| F19d | Release de E0 (e0-r2) con reglas generales antes de una tanda, con la tanda 0 fuera por lista: reglas que crean, quitan o cambian unidades de las tandas siguientes sin cambiar la tanda 0 | E0 e0-r2 de las tandas siguientes; la de la tanda 0, byte a byte igual | en la tanda 0, nada; en las siguientes, las unidades nuevas y las que cambian texto o herencia entran a E1 y E3 por F19b y F01 a F03, cuando esa tanda se extraiga | cambia (en las tandas siguientes: las unidades nuevas y las que cambian texto o herencia; en la tanda 0, no cambia) | cambia (en las tandas siguientes, las mismas; en la tanda 0, no cambia) | ninguna en la tanda 0 | 9 (como F19b) | `correr_e0.py:207-252` (las constantes de S0-6, `_r6`, `_sd_s04` y `_r5`), `:851-860` (`_filas_tabla_a`), `:1444-1448` (B, D y M en `procesar_tablas_r2`), `:1492` (A en `escalera_e0_r2`), `:1518-1525` (A, E, F1, G, H, I, J, K y L en `escalera_e0_r2`), `:1697-1718` (R5-a, A, C y F2 en `correr`); `e0_lib.py:228-243` (el docstring del módulo), `:550-655` (las constantes de A, B, C, F, G, H, I, J y K), `:766-779` (L y M), `:794-851` (`lineas_de_indice_l`), `:1716-1829` (G, I, J y F), `:2067-2073` (la carátula de A en `parsear_cuerpo`), `:2273-2274` (L en `parsear_cuerpo`), `:3163-3364` (C), `:3367-3658` (A), `:3661-3707` (F2), `:4085-4095` (`_marca_hijo` y `_es_raiz_subdoc`), `:4324-4367` (B), `:4572-4589` (M en `construir_chunks`) | R24 (las unidades nuevas y las que cambian de las tandas siguientes; sin variación propia: en la tanda 0 no ocurre) |
| F20 | Partición por corte (perfil r2): una unidad que corta también en el reintento se parte por ítems sin cortar tablas; un cambio del mecanismo (ítems, tope de la herencia de las partes) | runner, con `correr_e0.particionar_por_corte`; partes `::parteK` registradas en `particiones_por_corte.json` | E1 y E3 de las partes; la unidad entera conserva sus claves | cambia (las partes: sin clave previa) | cambia (las partes) | E1 y E3 de las afectadas | 9 | `correr_e0.py:410-471`, `:490-528`; `runner_corpus.py:67-68`, `:473-586`, `:741-750` | R26 |
| F21 | Recorte de la herencia de e0-r2 (tope U = 13.091 y B = 2.000 caracteres; marca y línea del recorte) | E0 e0-r2: herencia y `herencia_recortada` de las unidades cuya herencia pasa U; línea del recorte en el mensaje de E1 | E1 de esas unidades (en la tanda 0, solo `ric::11.2.3`); su E3 por la salida nueva y, con la forma r2, el de los ítems cuyo bloque que abre la lista se recorta | cambia (las recortadas) | cambia (solo los ítems cuyo bloque que abre la lista se recorta, con la forma r2; las demás, no: encabezados enteros, con la salida de E1 fija) | E1 y E3 de las afectadas | 9 | `correr_e0.py:77-80`; `e0_lib.py:4170-4245`; `prompt_r2b.py:362-365`, `:421-422` | R27 |
| F22 | Plantilla del mensaje de E1 r2b: una línea presente en todo mensaje (cierre, rótulos fijos) | mensaje de usuario; no entra al hash del prefijo ni al namespace; candado del mensaje de E1 (U-PROMPT-R2, P3c-2) al importar `prompt_r2b`: el sha256 del mensaje de las unidades de `candado_mensaje_r2b.json` | nada se arma hasta re-sellar el candado del mensaje; re-sellado, E1 de todas las unidades y E3 de todas por la salida nueva | frena (candado del mensaje de E1) | frena (sin perfil no hay salida validada de E1) | frena; re-sellado, todo | 9 | `prompt_r2b.py:354-361`, `:395-437`; candado `:491-513` | R29b |
| F22b | Plantilla del mensaje de E1 r2b: una línea condicional (ítem de una lista, mini-chunk a mitad de oración, recorte, rótulos de la herencia, línea de alcance) o la regla que la dispara (`bloque_lista`, `mini_a_mitad`) | mensaje de las unidades que llevan la línea; candado del mensaje de E1 (U-PROMPT-R2, P3c-2), con una unidad de la fixture por rama | nada se arma hasta re-sellar el candado del mensaje; re-sellado, E1 de las unidades que llevan la línea y su E3 | frena (candado del mensaje de E1) | frena (sin perfil no hay salida validada de E1) | frena; re-sellado, E1 y E3 de las afectadas | 9 | `prompt_r2b.py:306-353`, `:376-392`; candado `:491-513` | R29 |
| F23 | NOTA del mensaje de E3 en la forma r2 (tablas confiables, estructura sin resolver, encabezado de lista, omisiones de esquema) | mensaje de E3; no entra al prefijo de E3 ni a su namespace; candado del mensaje de E3 (U-PROMPT-R2, P3c-2) al importar `prompt_e3`: el sha256 del mensaje de los casos de `candado_mensaje_e3.json` | nada se arma en E3 hasta re-sellar el candado del mensaje de E3; re-sellado, E3 de las unidades que llevan la nota; E1 sale de la caché; los reintentos cambian donde cambia el feedback | no cambia | frena (candado del mensaje de E3) | frena; re-sellado, E1 y E3 de las afectadas | 9 | `prompt_e3.py:246-264`, `:333-381`; candado `:459-495` | R30 |
| F24 | Lazo de E3 (ratchet): plantilla del feedback y aviso del reintento, criterio de bloqueantes y guarda estructural (LAUDO B y su enmienda), lectura del veredicto como texto, tope de reintentos | fase E3: decide qué unidades reintentan y arma su request de re-extracción | E1 de reintento de las unidades con faltantes bloqueantes y su re-verificación; el primer intento de E1 y la primera verificación de E3 salen de la caché | cambia (solo los requests de reintento) | no cambia (primera verificación) | E1 y E3 de las afectadas | 9 | `ratchet_e3.py:96-110`, `:230-304`, `:311-374`; `runner_corpus.py:888-894` | R31 |
| F23b | Bloque que abre la lista y NOTA del ítem en el mensaje de E3, con la forma r2 (U-E3-LISTAS): la regla que elige el bloque (el de `LINEA_ITEM` en E1 y los contiguos del mismo tipo y la misma unidad de origen, D2), que entra al fuente del mensaje y al de las citas, y el texto de la NOTA del ítem | mensaje de E3 de los ítems y verificación de sus citas en el lazo (`ratchet_e3.py:283`); no entra al prefijo de E3 ni a su namespace; candado del mensaje de E3, con tres ítems en su fixture desde U-E3-LISTAS | nada se arma en E3 hasta re-sellar el candado del mensaje de E3; re-sellado, E3 de los ítems (1.054 en la tanda 0, A3r); E1 sale de la caché; cambia qué reclamos tienen cita verificada y, con eso, qué unidades reintentan o van a la cola | no cambia | frena (candado del mensaje de E3) | frena; re-sellado, E3 de las afectadas (los ítems) | 9 | `comun_e3.py:111-128`, `:148-152`, `:255-257`; `prompt_e3.py:265-323`, `:375-378`, `:398`, `:407`; `ratchet_e3.py:283`; candado `prompt_e3.py:459-495` | R33, R33b, A3r |

Notas a filas:

- **Anclas al ensamblador (`tanda0/code/ensamblar_tanda0.py`) corridas el 07/10/2026 por R2-3 de U-RERESOL-CAT**, cuyo código suma 41
  líneas (1.608 → 1.649) y la verificación de la mesa encontró que 10 de las 14 anclas de las filas F13, F15, F15b, F15c, F15d, F16 y F16b
  venían corridas desde `2a857db` (el archivo tenía 1.299 líneas) y que `:955` de F15d no nombraba lo que la fila dice: todas se
  reescribieron contra el árbol con R2-3, por el texto que nombran (`def` o llamada), y se verifican con `grep -n` antes de cada edición.

- **[10/10/2026, U-OMISIONES-COD, O2] La release de código del ensamblado** (mandato firmado en `c90d3d9`, con las notas del
  10/10/2026 al pie). Todos sus cambios son solo código sobre lo guardado (principio 12) y caen en filas que ya existen, sin filas
  nuevas:
  - f y H en F14b: la mención de sujeto con contracciones y el tipo de la Comunicacion desde el código, en `validador_r2`;
  - las marcas del grupo A, G-r, (h) y K en F15;
  - g a g3 (la base) y L (el tramo de E1) en F15b;
  - J (la procedencia de cada origen) y el agrupamiento sin el rol de la atribución de `remite_a` en F15c;
  - f′ (el singular «entidad» de R3) en F15d.

  Ninguna clave de E1 ni de E3 cambia: con el código nuevo, `selftest_clave_cache` da OK y su JSON es igual al del repo. Re-anclé
  F14b, F15, F15b, F15c, F15d, F16 y F16b por el texto que nombran (`data/experiment/omisiones_cod/o2/scripts/anclas_tabla.py`, que
  da la línea de cada texto en HEAD y en el código nuevo); en F16b solo cambia el ancla de `ensamblar_tanda0.py`, y las de
  `correr_e0.py` y `e0_lib.py` quedan como las corrigió la nota sobre el parche de S0-5a-bis, más abajo. La pieza (e), el
  clasificador de la copia de la nota de E3, no está aplicada: entra solo si su lectura llega al piso.

- **F03.** El mini-chunk del bloque cambió su propio texto: para él rige F01. Desde U-E3-LISTAS, con la forma r2, el
  bloque que abre la lista de un ítem entra al fuente de E3 (F23b): cambiar su texto mueve también la clave de E3 de
  esos ítems, con la salida de E1 fija (R03; en la muestra, `docvig::3.3.1`, `ext::7.1.1.3` y `polcre::2.1.1`).
- **F04 y F04b.** Con una tabla serializada, la NOTA de E3 depende de la marca de residual, no de la de contenido
  tabular (`prompt_r2b.py:206-208`): R04 invierte las dos. Un alta en la lista de tablas forzadas a residual tiene
  el efecto de F04 sobre las unidades que traen la tabla, como dice la nota del 03/10/2026 al protocolo (§6). El
  archivo tiene candado desde P3c-2 de U-PROMPT-R2 (`prompt_r2b.py:96`, `:182`, `TABLAS_FORZADAS_SHA256_ESPERADO`): un alta frena al
  construir el perfil (R32) y, re-sellada la lista, mueve esas claves como F04. La disciplina de declarar cada alta con su
  tabla, su motivo y su fecha sigue, para el re-sellado. (Corregido el 07/10/2026: el texto anterior decía que el archivo no
  tenía candado, en contradicción con la fila F04b y con el código.)
- **F05. Difiere del texto firmado del protocolo entre tandas** (`a304b89:82`), que pone F05 entre las filas que
  pagan E1 y E3 de las afectadas. La tabla sigue la composición real de la clave: ni el mensaje de E1 ni el de E3
  leen páginas, id, sha256 ni conteos (R05, R06; con el perfil sellado, V05, V06). La enmienda 3 al protocolo quedó
  firmada el 04/10/2026 (`0cb0c70`; asentado el 06/10/2026 en T5 de U-REEXT-T0). Ninguna unidad paga en ninguna de las dos lecturas.
  Como el id no entra al request, desambiguar los ids repetidos de la partición (69 en cuatro TOs,
  `docs/tablero_correcciones.md:70`) no cambia ninguna clave. Lo que cambia es la identidad de los registros
  persistidos, que el runner indexa por id y protege ante ids repetidos (`runner_corpus.py:163-175`).
- **F08 y F08b.** El docstring de `ratchet_e3.py:355-359` aclara que cambiar `max_tokens` no invalida el caché de
  prefijo de la API pero sí la clave local, que lo hashea. El techo del corte del perfil r2 (16.384,
  `cliente_e1.py:61-68`) reemplaza al de 32.768 de los perfiles existentes porque el SDK rechaza el request sin
  streaming. R13b: el request del reintento cambia de clave con el techo; el del primer intento no.
- **F08c.** Con el sufijo vacío, el namespace es el de siempre (R25): agregar el reintento no movió ninguna clave
  del primer intento. Desde U-PROMPT-R2, P5, con el perfil r2b el reintento deja de ser el mismo request: es el que
  produjo la salida con `temperature` 1, para obtener una respuesta distinta (`prompt_r2b.py:453-456`, llamado desde
  `runner_corpus.py:505-513`). R25 verifica que difiere del primer intento solo en la temperatura. Con los perfiles
  existentes y el camino r2, el reintento sigue siendo el mismo request.
  Desde U-REEXT-T0, T2-bis, con el perfil r2b, si el reintento vuelve mal formado hay un segundo, una sola vez: el
  mismo request en el namespace `-rforma2` (`cliente_e1.py:77-80`); R25b verifica que su clave no es la del primer
  intento ni la del reintento. Desde T2-ter, agotados los dos, una salida que trae `entities` como lista y no trae
  la clave `relations` sigue con `relations = []` si así `validador_e1` no la rechaza entera
  (`runner_corpus.py:529-559`, `:692-728`), marcada en su registro (`reparacion_forma`) y contada aparte en el
  resumen de E1 (`reparadas_forma`, `:808-819`); cualquier otra salida mal formada sigue el camino de siempre. La
  reparación no mueve ninguna clave de E1 (actúa sobre la respuesta guardada, no sobre el request); las reparadas
  pagan E3, que reclama las relaciones que falten. Un cambio de la regla de la reparación cambia el E3 de las
  reparadas y no su E1: el comportamiento de clave de la fila F08f (decisión de la autora del 06/10/2026 sobre el FRENO T2-ter.
- **F08e.** Hasta U-PROMPT-R2, P5, E1 corría sin temperatura fijada y la temperatura era un parámetro más de F08:
  R14 agregaba `temperature` a un pedido que no la tenía. Desde P5, el pedido del perfil r2b lleva `temperature` 0,
  y R14 cambia ese valor. Las claves de P4 y de P4b, sin temperatura, no son las del perfil r2b (R14 lo verifica en
  la muestra). Con el perfil sellado, V14 sigue agregando la temperatura a un pedido que no la tiene.
- **F09.** `CODE_VER` se sube a mano «si cambia la lógica sin cambiar el prompt» (`cliente_e1.py:16-19`): es un
  cambio de solo código que, a propósito, obliga a pagar todo.
- **F10. Difiere del texto firmado del protocolo entre tandas** (`a304b89:84-85`), que dice que en la clase «todo»
  todas las unidades pagan E1 y E3. La tabla sigue la composición real de la clave: un cambio del prompt o del
  modelo de E3 mueve la clave de E3 de todas las unidades y ninguna de E1 (R16, R17). F10 cumple la definición de
  «todo» de la sección 2, pero lo que se paga es E3 de todas más los reintentos de E1 donde cambia el feedback. La
  enmienda 3 al protocolo quedó firmada el 04/10/2026 (`0cb0c70`; asentado el 06/10/2026 en T5 de U-REEXT-T0).
- **F10b.** Desde `924ef4d` el prefijo de E3 tiene candado: cambiar un archivo de datos de los calibradores frena
  la importación de `prompt_e3` y, con ella, el runner entero (R22d).
- **F11, F11b, F12 y F13b.** En el perfil r2b, todo lo que el catálogo aporta al request está protegido por
  candado. Un cambio real primero frena (R21, R22, R22b, R22c) y, re-sellado, mueve las claves como dicen R10,
  R10b y R11, que alteran los requests en memoria sin pasar por los candados.
  El hallazgo de M1 sobre los roles de `esquema_v2_clases.json` sin candado (V21) vale solo para el perfil
  sellado: en r2b la línea de alcance sale de `rol_por_to_r2.json`, con candado.
  Una entrada de clase para un TO cambia solo el mensaje de ese TO (F12). Un rol nuevo entra al bloque del prefijo
  y al enum (F11). Un documento que necesite un rol nuevo entra sin línea de alcance, declarado
  (`URERESOL_CAT_reresolucion_catalogo.md:165-171`).
- **F13, F13b y F13c.** F13 quedó implementada por R2 de U-RERESOL-CAT (decisión 2 de la autora al firmar el mandato de
  U-TABLA-REPROC; diseño en R1, `c98093a`; código en R2-1 y R2-1 bis, `0737497`, W1 a W3; parte A y registro de alcance en
  R2-2, `a079275`): el catálogo del request queda fijo por release y el de resolución es el del request más una lista de
  ampliaciones que solo agrega, con su manifiesto y su candado (`r1_e4.py:598-647`). Ningún request lee los generados de
  resolución (R20: el armado no abre `indice_e4_r2.json`). Desde A2 de U-ALCANCE-E1, el mensaje de E1 lee el derivado del
  registro de alcance por tanda (F13c, R34): en la tanda 0, que no tiene documentos en el derivado, sigue idéntico en las
  2.439 unidades, como lo midió R2-2. Un id nuevo en el catálogo del request sigue siendo F13b (frena y, re-sellado, F11).
  La enmienda 2 al protocolo (`0b98045:13-16`) clasifica el crecimiento del catálogo con F13; su fe de erratas del §0 quedó
  FIRMADA el 04/10/2026 (`0cb0c70`, al pie de la enmienda). (Corregido el 07/10/2026: esta nota y la cabecera de la sección 2
  decían F13 pendiente de R1 y de R2, y la fe de erratas pendiente.)
- **F14. Difiere del texto firmado del protocolo entre tandas** (`a304b89:79-80`), que pone el validador entre las
  filas de solo código. Con el perfil r2b hay dos validadores. `validador_e1` corre antes de E3, y su salida es el
  mensaje de E3 (R18). El ensamblado r2b deja entrar solo lo que vio E3 (`validador_r2.py:768-769`, `:1084-1086` y
  `:1214-1216`, con los índices de la validación guardada, `runner_corpus.py:1188-1195`; P3 de U-PROMPT-R2,
  `4aa92c7`). Por eso un cambio en `validador_e1` no llega al grafo sin volver a correr E3 en las unidades cuya
  salida validada cambia. La enmienda 3 al protocolo quedó firmada el 04/10/2026 (`0cb0c70`; asentado el 06/10/2026 en T5 de U-REEXT-T0).
  «Solo código» exige además el crudo de E1 de cada unidad. El de la primera pasada está en
  `extracciones_e1.jsonl`; el de las unidades aceptadas tras un reintento del ratchet, en `reintentos_e3.jsonl`
  desde `924ef4d` y, en corridas anteriores, solo en `e1_reintentos.db` (`runner_corpus.py:1096-1124`).
- **F14b.** Es lo que el protocolo llama «validador» en la clase «solo código», leído como el validador r2. La
  política r2 es un solo archivo con candado en los dos lugares que la leen (`validador_e1.py:102` y
  `r1_e4.py:541`): un cambio frena los dos y, re-sellado, si toca la forma o los alias de los tipos o los
  predicados, también es F14. `validador_r2` usa además las reglas de ítem y de mini-chunk a mitad de oración del
  mensaje de E1 (`validador_r2.py:251-264`): un cambio en esas reglas es F22b y F14b a la vez.
- **F15. Parámetro `con_cola` de la cadena r2 (U-SINCOLA-T0, enmienda 1 al mandato, 06/10/2026).**
  `ensamblar_tanda0.py --sin-cola` llega ahora también a la cadena r2: `correr_cadena_r2` descarta, en un
  único punto y después de `entrada_r2`, los registros de la cola humana (`descartar_cola_r2`), y lo que
  sigue (omisiones, paso por E3, marca de la cola, aristas derivadas que tocan la cola) se computa sobre lo
  que queda; el reporte del ensamblado declara `con_cola` y las unidades descartadas por TO. Es solo código
  sobre lo guardado: no toca el request de E1 ni el de E3, así que no mueve ninguna clave de la caché
  (`selftest_clave_cache` sigue en verde, A1r y A3r OK). Sin la bandera, la salida es la de siempre: los dos
  r2b sellados, byte a byte.
- **F18a.** E0 solo arma unidades con páginas de cuerpo (`e0_lib.py:2068-2069`). Caso a la vista: en la corrida del
  2026-09-07, `ctacte` cambió solo en la página 85 de 86 (`job_actualizacion/corridas/2026-09-07/reporte.md:80`),
  que en la E0 de la tanda 0 no pertenece a ninguna unidad. Que E0 sobre el PDF nuevo devuelva las mismas unidades
  byte a byte es NO VERIFICADO: requiere correr E0 sobre ese PDF, que es de U-SUBGRAFO. Con r2b, el pie de la
  página cambiada entra a `pies_<to>.json` y, si cambia la versión vigente, al TextoOrdenado (F16b).
- **F19.** Con la E0 r2b, el selftest incorpora un punto antes de `pro::2.3`: se renumeran 2.3 a 2.7 y cambian las
  claves de 42 de las 101 unidades de pro, en E1 y en E3. La caché no reconoce «mismo contenido, otro número».
- **F19b.** Fila propuesta en el FRENO S0-2 de U-SEG-OFICIAL (`segmentacion_oficial_e0r2/s0_2/REPORTE_S0-2.md`, §5). F19 cubre
  la unidad que aparece o desaparece por un cambio de numeración del documento y F01 el texto de una unidad que sigue
  existiendo; ninguna decía qué pasa con la unidad que una regla de segmentación agrega o retira sin que el PDF cambie
  (en S0-2, 553 ids nuevos y 384 que desaparecen en 26 TOs; `s0_2/censos/atribucion_S0-2.json`). La clave de una unidad
  nueva no existe en la caché, así que E1 y E3 corren para ella como para la unidad nueva de R24; la fila cita esa
  variación porque el contraste exige una por fila y en la tanda 0 ninguna regla de S0 agrega ni retira unidades
  (57 archivos byte a byte). Las unidades que cambian texto o herencia por la misma regla van por F01 a F03.
- **F20.** En la tanda 0, la única unidad grande que se puede partir por ítems es `cap::4.2.1.2` (borrador del
  mandato de U-REEXT-T0, T1). El selftest la parte en 2 partes, cada una con su propia clave en E1 y en E3 (R26).
- **F21.** Desde U-E3-LISTAS, un recorte que toca el bloque que abre la lista de un ítem cambia también su E3 con la
  forma r2, aunque la salida de E1 no cambie, porque ese bloque entra al fuente de E3 (R27; en la muestra,
  `ext::7.1.1.3` y `polcre::2.1.1`).
- **F22, F22b y F23.** Las líneas fijas del mensaje de E1 y las NOTAS del mensaje de E3 no entran al hash del
  prefijo ni al namespace. Desde P3c-2 de U-PROMPT-R2 tienen candado: el sha256 del mensaje de un conjunto fijo de
  unidades. Un cambio frena hasta re-sellar (R29, R29b y R30). Re-sellado, una línea de todo mensaje hace pagar E1 de
  todas las unidades, y una línea condicional, solo las unidades que la llevan. La NOTA del ítem de una lista
  (U-E3-LISTAS) va con el bloque que abre la lista, en la fila F23b.
- **F23b.** Fila de U-E3-LISTAS (mandato firmado en `d9d8888`; enmienda 1, nota al pie del 06/10/2026; NOTA del
  ítem, versión 2, nota al pie del 07/10/2026). El bloque que abre la lista y la NOTA del ítem van en el mensaje de
  E3 solo con la marca de la forma r2, como `notas_r2`: sin la marca, el mensaje es el de siempre, byte a byte.
  Desde U-E3-LISTAS, la fixture del candado del mensaje de E3 tiene 19 casos: las 6 unidades de P3c-2 con y sin la
  marca, el sintético, y tres ítems con y sin la marca (`ext::3.5.6.1`, con el bloque intro; `cap::6.8.3.1`, con el
  bloque encabezado; `pro::2.3.6.1`, con el bloque intro partido en dos fragmentos). Un cambio de la regla o de la
  NOTA frena hasta re-sellar (R33, R33b); re-sellado, pagan E3 los ítems. A3r lo mide sobre la tanda 0: con el código
  vigente, las claves de E3 de los no ítems están en la db y las ausentes son exactamente las de los ítems (D5). La
  verificación de citas recibe la marca de la forma r2 (`ratchet_e3.py:283`, la única línea del ratchet que cambia,
  D1): una cita al bloque que abre la lista queda verificada (F24).
- **F24.** El tope es de un reintento por unidad (`ratchet_e3.py:96`). Un cambio en el criterio de bloqueantes
  cambia qué unidades reintentan, no la clave de las que ya reintentaron con el mismo feedback. Desde U-E3-LISTAS
  (F23b), con la forma r2 la cita a un bloque que abre la lista verifica (`ratchet_e3.py:283`): cambia qué reclamos
  tienen cita verificada y, con eso, qué unidades reintentan o van a la cola por veredicto inutilizable, sin mover la
  clave de la primera verificación.

### Diferencias con el perfil sellado (`v3_b54`, tanda 0)

El grafo sellado de la tanda 0 se clasifica con estas filas, salvo en estos puntos (variaciones V01 a V24 del
selftest, las mismas de `e18d616`):
- **F04:** solo la marca de contenido tabular y la de fórmula; no hay tablas de e0-r2.
- **F08b:** el techo del corte de E1 es 32.768 (`cliente_e1.py:60`).
- **F11 y F11b:** el bloque y el enum v3 (`b54_catalogo_v3/code/prompt_v3_b54.py:326-392`, `:411-414`), con el
  candado de `perfil_e1.py:178-184`.
- **F12:** la línea de alcance de los cinco TOs de desarrollo sale de los roles de `esquema_v2_clases.json`, sin
  candado (V21).
- **F13:** el catálogo de E4, del esqueleto y de S19 es `esquema_v3_clases.json`, que el armado no abre (V20): solo
  código.
- **F14:** solo código, con la re-verificación en E3 opcional, porque no hay índices de lo que vio E3.
- **Solo r2b:** F04b, F08c, F08d, F08e, F16b, F20, F21, F22, F22b, F23 y F23b.

## 4. El selftest

Comando, desde la raíz del repo o de una copia del repo (la verificación de esta unidad corrió sobre una copia):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B data/experiment/mantenimiento/code/selftest_clave_cache.py --out data/experiment/mantenimiento/selftest_clave_cache.json
```

Qué hace (detalle en el docstring del script):

**Perfil sellado, los bloques de M1 sin cambios:**
- **A1 y A3, anclaje.** Recalcula la clave de E1 de las 2.434 unidades de E0 de la tanda 0 y la de la primera
  verificación de E3 de las 2.430 unidades aceptadas por E1. Las busca en las dbs de caché, abiertas en solo
  lectura (`mode=ro&immutable=1`).
- **V01 a V24.** Las variaciones de M1, cada una con lo que espera.

**Perfil r2b:**
- **A1r y A3r, anclaje sobre las dbs de U-REEXT-T0** (`--salida-r2b`, por defecto `corpus_tanda0/salida_r2b`).
  Hasta que esa salida exista quedan NO_VERIFICABLE, y rige, declarado, el anclaje del perfil sellado (decisión 3
  de la autora al firmar el mandato de U-TABLA-REPROC). Se corre de nuevo cuando existan las dbs de U-REEXT-T0.
  **[06/10/2026, T5 de U-REEXT-T0]** Las dbs existen (`corpus_tanda0/salida_r2b/`, extracción en `3d793aa`, `4ab7a0a` y
  `ad99ac7`): corrido con `--salida-r2b`, A1r y A3r dan OK (resultado abajo).
- **R00 a R34.**
  - Una entrada por vez, sobre una muestra fija de trece unidades de `salida_tanda0_r2b/` (`MUESTRA_R2B`): las
    diez de M1, dos con tablas serializadas y la única con la herencia recortada.
  - La clave de E3 se arma con una salida sintética mínima de E1 en la forma r2, validada con `validador_e1` y el
    esquema del perfil. La salida de U-REEXT-T0 todavía no existe.
  - Las variaciones de archivos de datos corren en un proceso hijo que los sirve alterados desde memoria; ningún
    archivo se escribe.
  - R23 usa `snp_psp::1.3.1.1` de la partición. R24 recorre todo pro. R26 parte `cap::4.2.1.2`. R34 le da a docvig,
    en memoria, una entrada del derivado del registro de alcance (la de ri_ccna).
- **Contraste.** Lee esta tabla, toma de cada fila las columnas «Clave E1» y «Clave E3» y las variaciones del
  perfil r2b, y las compara con lo observado. Toda variación R tiene que tener fila. Una discrepancia hace que el
  selftest salga con código 1 (FRENO).

Resultado (salida en `selftest_clave_cache.json`):

**Perfil sellado:**
- A1: 2.434 de 2.434 claves de E1 presentes en la db. El namespace tiene 2.437; las 3 que sobran son las de la
  re-extracción dirigida de `cap::3.1.14.1`, `cap::4.2.1.2` y `cap::4.3.3.1` con `max_tokens` 16.384.
- A3: 2.430 de 2.430 claves de E3 presentes.
- V01 a V24: las 25 variaciones dan lo esperado. Antes de la extensión, la salida del selftest de M1 con el código
  de `9f6361e` era idéntica byte a byte a la de `e18d616`.

**Perfil r2b:**
- A1r y A3r: OK desde el 06/10/2026 (T5 de U-REEXT-T0; `--salida-r2b corpus_tanda0/salida_r2b`, dos corridas iguales sobre una
  copia y reproducido por la revisión; `data/experiment/reext_t0/t5/comandos_t5.sh`, bloque 5): A1r, 2.449 de 2.449 claves de E1
  presentes en la db r2b (8 en `-rforma1` y 2 en `-rforma2`); A3r, 2.440 pares presentes. Antes de esa salida eran
  NO_VERIFICABLE, con 0 claves en el namespace r2b.
- **[07/10/2026, O2 de U-E3-LISTAS]** A3r cambia de regla (D5, enmienda 1 al mandato): recomputa con el código
  vigente las 2.440 claves de E3 de la tanda 0 y exige las de los no ítems presentes y las de los ítems ausentes,
  exactamente. Resultado: OK, 1.386 de no ítems presentes y 1.054 ausentes, que son los 1.054 ítems
  (`prompt_r2b.es_item`), listados en el JSON; ningún no ítem ausente ni ningún ítem presente.
- **[14/10/2026, R0 de E3-01]** A3r cambia de regla (enmienda 7 al protocolo entre tandas, §1.5). R0 dejó en la db de E3
  la primera verificación con el E3 corregido de las 20 unidades de E3-01: las filas de O3, sembradas. Sus claves son las
  de `verificacion` en `reextraccion_v2/r0/esperados_r0.json` (`81598c97…`), que el selftest lee controlando su sha256.
  - La regla: presentes las claves de los no ítems y las 20 de R0; ausentes, exactamente, las de los ítems que no son de
    R0. Cualquier otra ausencia o presencia es DISCREPANCIA.
  - Dos variaciones de control tienen que dar DISCREPANCIA: A3r_v1 (una de las 20, ausente) y A3r_v2 (la clave de un
    ítem que no es de R0, presente).
  - Resultado: OK. Están presentes las 1.386 de no ítems y las 20 de R0, y faltan 1.034, que son los ítems que no son
    de R0. A3r_v1 y A3r_v2 dan DISCREPANCIA.
  - Con la regla anterior, sobre la misma copia, A3r daba DISCREPANCIA solo por las 20 presentes.
  - En el perfil sellado, A3 sigue OK (2.430 de 2.430), y el namespace de E3 pasa de 7.698 claves a 7.721: las 20
    sembradas y las 3 re-verificaciones de R0.
- R00 a R34: las 45 variaciones dan lo esperado, unidad por unidad. Hasta U-E3-LISTAS eran 42, R00 a R32 (este
  texto decía 41, y el JSON de `0a3ac81` tiene 42). U-E3-LISTAS suma R33 y R33b, que frenan (F23b), y R03 y R27
  esperan el cambio de la clave de E3 en los ítems cuyo bloque que abre la lista tocan (F03 y F21). A2 de U-ALCANCE-E1
  (15/10/2026) suma R34: cambia la clave de E1 de `docvig::3.3.1` y no la de E3 (F13c).

**Inventario:**
- Los procesos hijo sin alteración reproducen las claves del padre, en los dos perfiles.
- Ninguno de los módulos de validación, E2, ensamblado, umbrales, remisiones, E4 o esqueleto se carga al armar los
  requests.
- `validador_e1` y `validador_r2` se cargan solo al validar la salida de E1.

**Contraste con esta tabla:** OK, en las 45 filas (41 hasta la fila F19b, sumada el 06/10/2026 en S0-2 de U-SEG-OFICIAL; 43 con la fila F23b de U-E3-LISTAS, O2, 07/10/2026; 44 con la fila F13c, 07/10/2026, selftest corrido sobre una copia con la tabla corregida y su JSON regenerado; 45 con la fila F19d, `2374968a`, 13/10/2026, que este pie no contaba; desde A2 de U-ALCANCE-E1, 15/10/2026, F13c se contrasta con R34 en lugar de R20, sobre una copia con la tabla corregida y su JSON regenerado).

## 5. Costo de referencia por clase

**Perfil r2b** (U-REEXT-T0 y las tandas). Es la tarifa observada en la corrida de U-REEXT-T0 (T2, 05/10/2026,
prefijo `322c5a23e9b7`; protocolo, §1, punto 4), sobre las 2.439 unidades de E0 de la tanda 0:
- E1: USD 24,7195, USD 0,010135 por unidad.
- E3 con los reintentos del ratchet: USD 24,9403, USD 0,010226 por unidad (verificación 21,9706, 0,009008 por
  unidad; reintentos de E1 del ratchet 2,9697, 0,001218 por unidad).
- E1 y E3: USD 49,6598, USD 0,020361 por unidad.
- **[07/10/2026]** Agregado medido de U-E3-LISTAS (O2, `7fe848c`): el bloque que abre la lista y la NOTA del ítem suman 918.107
  tokens de entrada de E3 por corrida del tamaño de la tanda 0 (1.054 ítems), USD 1,84 a USD 2 por millón: USD 0,000754 por
  unidad sobre las 2.439. La tarifa de referencia de las tandas desde la tanda 1 es 0,020361 + 0,000754 = USD 0,021115 por
  unidad (nota del 07/10/2026 al protocolo entre tandas); O3 mide el costo real por ítem.

La corrida de reparación de U-REEXT-T0 (T2-bis, USD 0,49291, y T2-ter, USD 0,249002, sobre unidades de cap) no
entra en la tarifa por unidad: el presupuesto de la unidad cerró en USD 50,401698 de 80. La estimación que esta
tarifa reemplaza (E1 0,010544 y E3 0,010333 por unidad, de P1 y P3b-2) está en `2a857db`.

| Clase | Costo de referencia (r2b) | Ancla |
|---|---|---|
| nada | USD 0 | — |
| solo código sobre lo guardado | USD 0 | principio 12, `docs/plan_tesis.md:299` |
| E1 y E3 de las afectadas | Por unidad que paga las dos etapas: USD 0,020361 (E1 0,010135 y E3 0,010226). Las filas que pagan solo E3 de las afectadas (F14 y F23) pagan 0,010226; las que pagan solo un reintento (F08b, F08c y F24) pagan el reintento y su re-verificación | comando 1 |
| todo | E1 a E3 de los diez TOs de la tanda 0: USD 49,6598 observados en U-REEXT-T0, de un tope de 80. F10 paga solo E3: 0,010226 por unidad, USD 24,9403 en la tanda 0 | `data/experiment/reext_t0/salida/contadores_t2.json` (`3d793aa`), comando 1 |

**Perfil sellado** (`v3_b54`, la tanda 0), medido en su corrida y sin cambios desde `e18d616`:
- E1: USD 0,007425 por unidad (18,07154 / 2.434).
- E3 con los reintentos del ratchet: USD 0,009179 por unidad (22,277978 / 2.427).
- E1 a E3 de los diez TOs: USD 40,35 (recomputado: 40,349518).
- La re-extracción dirigida de tres unidades largas de cap costó USD 0,461274.

Esos valores salen de los comandos 2 y 3.

Comando 1 (tarifa observada del perfil r2b: E1, E3 y su desglose en verificación y reintentos de E1 del ratchet, y
la suma, cada uno con su tarifa por unidad sobre las 2.439 unidades; fuente: los contadores de la corrida de
U-REEXT-T0, `data/experiment/reext_t0/salida/contadores_t2.json`, commit `3d793aa`, que toman el gasto por etapa de
`estado_corpus.json` y el de cada cliente de los resúmenes de E1 y E3):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -c "import json;g=json.load(open('data/experiment/reext_t0/salida/contadores_t2.json'))['b_gasto'];cl=g['clientes'];v=sum(c['e3']['gasto_usd_real'] for c in cl.values());r=sum(c['e1_reintentos']['gasto_usd_real'] for c in cl.values());n=2439;print(g['total_e1_usd'],round(g['total_e1_usd']/n,6),g['total_e3_usd'],round(g['total_e3_usd']/n,6),round(v,4),round(v/n,6),round(r,4),round(r/n,6),g['total_usd'],round(g['total_usd']/n,6))"
```

Salida: `24.7195 0.010135 24.9403 0.010226 21.9706 0.009008 2.9697 0.001218 49.6598 0.020361`.

Comando 2 (gasto de E1 y E3 de la tanda 0, por fase cerrada):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -c "import json;d=json.load(open('data/experiment/reextraccion_v2/corpus_tanda0/salida/estado_corpus.json'))['fases_cerradas'];e1=[v for k,v in d.items() if k.endswith(':e1')];e3=[v for k,v in d.items() if k.endswith(':e3')];g1=sum(v['gasto_usd'] for v in e1);g3=sum(v['gasto_usd'] for v in e3);n1=sum(v['resumen']['n'] for v in e1);n3=sum(v['resumen']['n'] for v in e3);print(round(g1,6),n1,round(g1/n1,6),round(g3,6),n3,round(g3/n3,6),round(g1+g3,6))"
```

Salida: `18.07154 2434 0.007425 22.277978 2427 0.009179 40.349518`.

Comando 3 (gasto de la re-extracción dirigida):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -c "import json;d=json.load(open('data/experiment/reextraccion_v2/corpus_tanda0/salida_dirigida/reextraccion_dirigida.json'));print(d['gasto_combinado_usd'],{k:v['gasto_usd_real'] for k,v in d['clientes'].items()},sorted(d['casos']),d['max_tokens'])"
```

Salida: `0.461274 {'e1': 0.1898, 'e3': 0.2096, 'reint': 0.0618} ['cap::3.1.14.1', 'cap::4.2.1.2', 'cap::4.3.3.1'] 16384`.

## 6. Límites

- **Perfiles que cubre.**
  - El perfil r2b, con el runner `corpus_v2/runner_corpus.py` y la cadena r2 de `tanda0/code/ensamblar_tanda0.py`.
  - El perfil sellado, en lo que dice la sección 3, «Diferencias con el perfil sellado».
  - El perfil `produccion_dev`, con el que se construyó r1, arma otro request (`prompt_e1.build_request_kwargs`) y
    no lo verifiqué.
- **Anclaje del perfil r2b.** Verificado el 06/10/2026 con las dbs de U-REEXT-T0 (T5 de la unidad; A1r y A3r OK, §4). Hasta
  esa fecha era NO_VERIFICABLE y regían, como sostén:
  - la composición de la clave está probada por las variaciones;
  - el cálculo de la clave, por el anclaje del perfil sellado (mismo `compute_key` y mismo `canonical_request`).
- **Salida sintética de E1.** La clave de E3 del perfil r2b se probó con esa salida, no con la salida real del
  modelo. Prueba el efecto de cada cambio sobre el request, no el contenido de una verificación real.
- **Unidades afectadas por un cambio real de la fuente.** El selftest prueba el efecto de cada cambio sobre la
  clave. Cuántas unidades afecta un cambio real depende de cómo E0 extrae el texto del PDF nuevo (cortes de línea,
  guiones, pies de página); eso no lo mide esta tabla.
- **Dbs de caché.** No se versionan (`docs/laudo_release_r2_pipeline.md:307-312`). Sin ellas el anclaje queda
  NO_VERIFICABLE y toda unidad pasa a pagarse. Las de U-REEXT-T0 existen desde el 05/10/2026 en `corpus_tanda0/salida_r2b/`
  (fuera del versionado) y con ellas el anclaje r2b quedó verificado el 06/10/2026 (§4).
- **Anclas al código de E0 fuera de F19b, corregidas el 08/10/2026 (mesa, por decisión de la autora).** Se escribieron sobre código
  anterior a `26c6502` y ya no nombraban lo que describen: F16b `correr_e0.py:1188-1189 → :1582-1583` y `e0_lib.py:786-816 → :1305-1335`;
  F18a `e0_lib.py:394-439 → :839-893` (la función entera, `clasificar_paginas`) y `:914-915 → :1590-1591`, igual en F18b y en la nota de
  F18a; F20 `correr_e0.py:169-229 → :296-357` y `:232-254 → :376-414` (las funciones enteras, `_sub_chunks_de` y `particionar_por_corte`);
  F21 `e0_lib.py:1808-1883 → :2718-2793`. Verificadas por contenido contra `2a857db` y contra el código de E0 de `18d9e05`. Las citas de
  F20 a `runner_corpus.py` (`:473-586`, `:741-750`) y la de F21 a `prompt_r2b.py` (`:421-422`) siguen apuntando a lo que describen y no
  cambian; F01 (`correr_e0.py:86-94`) y F21 (`correr_e0.py:77-80`), tampoco.
- **Anclas al código de E0 corridas por el parche de S0-5a-bis, corregidas el 10/10/2026 (mesa, por decisión de la autora).** El
  parche que aplicó S0-5b (`421ee913…`; `e0_lib.py` `bd2190ad…`, `correr_e0.py` `68bd74b5…`) corrió 14 de las 17 citas al código de E0:
  F16b `correr_e0.py:1582-1583 → :1688-1689` y `e0_lib.py:1305-1335 → :1391-1421`; F18a `e0_lib.py:839-893 → :925-979` y
  `:1590-1591 → :1718-1719`, igual en F18b y en la nota de F18a; F19b `correr_e0.py:360-372 → :432-444`, `:609-618 → :681-690` y
  `:1302 → :1393`, y `e0_lib.py:360 → :377` y `:556 → :642`; F20 `correr_e0.py:296-357 → :368-429` y `:376-414 → :448-486`; F21
  `e0_lib.py:2718-2793 → :3193-3268`. Verificadas por contenido: cada bloque citado en el código de E0 de `18d9e05` está entero e igual
  en su rango nuevo (`segmentacion_oficial_e0r2/s0_5/b/controles/anclas_e0_tabla_S0-5b.txt`, reproducido por la mesa sobre copias). No
  cambian F01 (`correr_e0.py:86-94`), F19b (`correr_e0.py:95-100`) ni F21 (`correr_e0.py:77-80`).
- **F19b cita además las reglas de S0-4 y S0-5 (10/10/2026, mesa, por decisión de la autora).** Hasta ahora citaba solo las de
  S0-1 bis y S0-2. Se citan los bloques de configuración, que prenden cada regla por TO o por lista, y la descripción de las reglas,
  cada cita con el nombre de su constante para poder volver a encontrarla si el código se corre: `correr_e0.py:119-138` (S0-4, de
  `REGLAS_S0_4` a `TOS_TANDA0_SIN_4AB`), `:140-210` (S0-5, de `REGLAS_S0_5` a `_r5`) y `e0_lib.py:203-226` (el docstring del módulo, de
  «U-SEG-OFICIAL, S0-4» a «S0-5a-bis»). Los rangos son del código de E0 de S0-5b (`e0_lib.py` `bd2190ad…`, `correr_e0.py` `68bd74b5…`).
- **El resultado de (e) (10/10/2026, mesa).** La lectura a ciegas de la pieza (e) no llegó al piso (registro en
  `data/experiment/omisiones_cod/lectura_e/`): la pieza no se aplica, y lo que la nota de U-OMISIONES-COD dice que «entra solo si su
  lectura llega al piso» no entra.
- **Anclas al código de E0 corridas por el parche de S0-6a-bis, corregidas el 13/10/2026 (S0-6b, por decisión de la autora).** El
  parche que aplicó S0-6b (`a0f291c4…`; `e0_lib.py` `d89aab1a…`, `correr_e0.py` `78c54c4c…`) corrió 14 de las 27 citas al código de E0:
  F16b `correr_e0.py:1688-1689 → :1767-1768` y `e0_lib.py:1391-1421 → :1602-1632`; F18a `e0_lib.py:925-979 → :1131-1185` y
  `:1718-1719 → :2068-2069`, igual en F18b y en la nota de F18a; F19b `correr_e0.py:432-444 → :474-486`, `:681-690 → :723-732` y
  `:1393 → :1452`, y `e0_lib.py:377 → :394` y `:642 → :782`; F20 `correr_e0.py:368-429 → :410-471` y `:448-486 → :490-528`; F21
  `e0_lib.py:3193-3268 → :4170-4245`. La cita de F19b a las reglas de S0-5, de `REGLAS_S0_5` a `_r5`, no se encuentra entera en el
  código aplicado, porque el parche cambia `_r5` (su docstring y tres renglones de los reemplazos de S0-6a): pasa a dos, `:140-205`,
  las constantes de S0-5, de `REGLAS_S0_5` a `RAICES_POR_LISTA_S0_5`, iguales byte a byte a las de S0-5b, y `:246-252`, `_r5`, en su
  lugar nuevo. Las otras 12 citas no cambian. Entra la fila F19d (las reglas generales de S0-6a y
  S0-6a-bis, A a M), con anclas al código aplicado. Verificadas por contenido contra el código de E0 de S0-5b y el aplicado, con el
  parche (`segmentacion_oficial_e0r2/s0_6/b/scripts/control_anclas_contenido_S0-6b_mesa.py`; la salida, en
  `segmentacion_oficial_e0r2/s0_6/b/controles/control_anclas_contenido_S0-6b.txt`).
