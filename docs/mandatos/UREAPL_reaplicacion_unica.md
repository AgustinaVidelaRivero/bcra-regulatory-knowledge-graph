# Mandato U-REAPL: la re-aplicación única del código al acumulado de las tres tandas, antes del sello del grafo evaluado (v2 de la mesa, 19/10/2026, §185; firmado el 20/10/2026)

**FIRMADO por la autora el 20/10/2026** (por mensaje recibido a las 10:01:39; hoja de ruta de la mesa, §195), sobre el borrador v2 (sha256
`65531aaf…`, en el paquete de la mesa, `decisiones_185_mesa/reapl/`), que reemplazó a la v1 de la §184. Las cinco precisiones de la sección
«Firma» mandan sobre su texto. El texto firmado es el del borrador v2, con este encabezado y esa sección. Lo pide el mandato de
U-PROC-HERENCIA («Lo usa la re-aplicación única, que tiene su propio mandato»,
`docs/mandatos/UPROC_HERENCIA_procedencia_de_tramos_heredados.md:157`). Las decisiones del §9 quedan como dice la sección «Firma». USD 0:
no llama a la API. La v2 cambia dos cosas del §6: la nota al pie del pre-registro de la tanda final sobre `r1_referencias.py` entra antes,
con la §53 del registro de decisiones; y `r1_invariantes.py`, que toca C1, queda declarado como otra de las 78 rutas.

## 0. De dónde sale

- **La enmienda 8 al protocolo** (`54902301`):
  - **R3:** las correcciones de código se re-aplican una sola vez al acumulado, antes de sellar el grafo evaluado. El grafo de cada tanda
    se sigue sellando sin corregir (principio 9);
  - **R5:** entra lo del grupo 2 que a las 12:00 del sábado 24/10/2026 tenga mandato firmado, código listo y su medición hecha. Lo demás va
    al grafo corregido, declarado.
- **El registro de decisiones:**
  - §32 y §33: C1 y C2 de U-PROC-HERENCIA, con una sola regla para las tres tandas («Nada se corrige a mano»);
  - §46 y §47: C1 de U-MED-DESAMB entra con la re-aplicación, después de la relectura del censo por la autora, y con la regla de la
    colisión mal unida;
  - §47: «en la re-aplicación, si la medición frena por algo no declarado, eso queda fuera del grafo evaluado, declarado y al grafo
    corregido, y el resto entra»;
  - §49 y §52: D, con la versión de la segunda pasada;
  - §41: la lectura de las claves del catálogo no se recorta.
- **El pre-registro de la tanda final** (`docs/preregistro_tanda_final.md`):
  - §7 y §9, decisión 4: la lectura de las claves del catálogo, una sola vez, sobre el acumulado de las tres tandas, antes de la
    re-aplicación y a más tardar a las 12:00 del sábado;
  - `:289-293`: las 78 rutas no cambian hasta el sello de la tanda final, y U-PROC-HERENCIA entra después de ese sello.
- **El diseño sellado de U-MED-DESAMB,** §6 (C1, su normalización y su código preparado) y §10 (el orden de recorte).

## 1. Lo que entra, y con qué

| Pieza | Qué hace | Código | Estado hoy |
|---|---|---|---|
| **D** (U-PROC-HERENCIA, opción D) | C1 de procedencia sin uniones, C2 y las remisiones de C1 con el punto de E1 | `ensamblar_tanda0.py` (blob `58e736db`) y `r1_referencias.py` (`84e8831f`), detrás de `--procedencia-heredada` | código listo y medido en el acumulado de las tandas 0 y 1 (segunda pasada, revisada en la §184) |
| **Las claves del catálogo** | el catálogo de resolución crece con las claves que apruebe la autora, y E4 re-resuelve con él | `--catalogo-resolucion` (`r1_e4.catalogo_resolucion_r2`, con su candado), ya en la cadena | falta la lectura de la autora (a más tardar el sábado a las 12:00) |
| **C1 de U-MED-DESAMB** | une las Comunicación de documentos distintos con el mismo código normalizado | `r1_invariantes.merge_grafos_guardado(…, codigo_comunicacion)` (parche preparado en `data/experiment/med_desamb/parte3/codigo_preparado/`), con `codigo_normalizado` sellado | falta integrarlo detrás de una bandera, con su lista de colisiones que no se unen, y la relectura del censo por la autora |

- **Nada más entra:** las remisiones y los vaciamientos (§41) entran solo si llega antes del corte un mandato firmado, con código y
  medición. Hoy no hay ninguno.
- **Lo que no entra y va al grafo corregido, declarado:**
  - las 12 uniones evitadas de D (7 de la tanda 0 y 5 de la tanda 1 en el grafo con cola; 4 y 5 sin cola);
  - las colisiones de C1 que la autora no une;
  - lo que frene la medición (§5).

## 2. El orden en que se aplican

Una sola corrida de la cadena r2 (`correr_cadena_r2`, `ensamblar_tanda0.py`) sobre el acumulado de las tres tandas, con las tres piezas.
Su orden es el de la cadena, y no se elige (las líneas son las del código de la segunda pasada, blob `58e736db`):
1. **Por documento:** G-r y, con D, C1 y C2 de procedencia (`:1779`). Después E4 con el catálogo de resolución, que es donde entran las
   claves (`:1783`). Después E2 (`:1784`).
2. **La unión entre documentos** (`merge_grafos_guardado`, `:1819`): ahí actúa C1 de U-MED-DESAMB.
3. **El esqueleto** (`:1853`).
4. **Las remisiones** (`:1859`), con el punto de E1 en las procedencias de D.
5. **`establecida_en`** (`:1874`).

**Las piezas no se pisan:**
- D cambia solo entidades de `TIPOS_G_R` (`ensamblar_tanda0.py:1363`: Operacion, Restriccion, Excepcion, Obligacion, Potestad,
  Condicion y Definicion; ni Comunicación ni Sujeto);
- las claves cambian Sujetos;
- C1 cambia solo Comunicación.
El script de la medición lo controla: cada pieza toca solo sus tipos.

**La medición va en cuatro pasos,** para que cada cambio tenga su causa y se pueda sacar una pieza sin sacar las otras:
1. el sello (sin banderas);
2. + D;
3. + D + las claves;
4. + D + las claves + C1.

## 3. Las tablas de ids

- **Cada pieza que cambia un id deja su tabla, por grafo** (con cola y sin cola por separado: no son la misma, como muestran las tres
  entidades de ctacte de la segunda pasada):
  - **D:** id viejo → id nuevo de los nodos que C1 de procedencia corrige (el punto va en el id). Con par único por tipo, etiqueta y
    `chunk_id`, como en la segunda pasada;
  - **las claves:** el Sujeto propuesto → el Sujeto del catálogo al que se re-resuelve;
  - **C1:** la Comunicación → el id de la primera de su código (`uniones_c1`).
- **La tabla compuesta,** por grafo: id del sello → id del grafo evaluado, con la pieza que lo cambió. Va con el sello, y se publica con
  el grafo.
- **Cómo se usa:**
  - **en el censo de C1:** el censo se arma y se lee antes de la re-aplicación, sobre el acumulado sellado. D no toca ninguna Comunicación,
    así que sus colisiones no cambian. El script lo controla: las colisiones del censo son las mismas en el paso 2 que en el paso 1. Las
    listas que el censo declara se reexpresan con la tabla compuesta en el FRENO;
  - **en los controles del cegamiento, que van por código de id** (sha256(id)[:12]):
    - todo código de una lista anterior a la re-aplicación se traduce con la tabla compuesta antes de compararlo con el grafo evaluado. Por
      ejemplo, los nodos de las unidades de la muestra de U-MED-VERIF;
    - un nodo de una unidad de la muestra que D renombra sigue cegado con su id nuevo;
    - la traducción corre en memoria, sin escribir la muestra;
  - **en N7, en el pre-registro de B6.3 y en la muestra de control de B6.3:** los hubs y el filtro de unidades se calculan sobre el grafo
    evaluado, y la tabla da el puente con lo que se midió antes (N6 sobre el acumulado de las tandas 0 y 1, sin la re-aplicación).

## 4. Lo que se mide en cada paso

Sobre los dos grafos del acumulado de las tres tandas (`KG-Acumulado-Tandas0y1yFinal-r2b` y su `-sincola`). El grafo evaluado es el sin
cola, y el con cola se sella como grafo completo (`docs/protocolo_dos_grafos.md`, §1):
- los nodos por tipo y las aristas por predicado, contra el paso anterior;
- con la tabla de ese paso, las triplas de cada predicado, contra el paso anterior;
- las `remite_a` que cambian, una por una, con su causa, y que cada una tenga un extremo en un nodo que cambió esa pieza;
- la suite y las shapes, regla por regla, con las regresiones declaradas al lado;
- por pieza:
  - D: C1 de procedencia, C2, las uniones evitadas y las de C1 sin las otras dos;
  - las claves: los Sujetos re-resueltos, por clave;
  - C1: las uniones, por código, y las que no se unen por la decisión de la autora.

## 5. Los casos de freno y lo que pasa con ellos (§47, tal cual)

- **Frena la pieza** si en su paso:
  - cambia una tripla de un predicado que esa pieza no debe tocar;
  - aparece una regresión no declarada;
  - cambia una regla bloqueante de las shapes;
  - o la pieza toca tipos que no son los suyos.
- **Lo que frena por algo no declarado queda fuera del grafo evaluado, declarado y al grafo corregido, y el resto entra.** Si es una parte de
  la pieza (por ejemplo, una clave o una colisión), sale esa parte, por su id, y se vuelve a medir.
- La ejecutora frena y muestra los casos con la regla del §7 bis de U-PROC-HERENCIA (códigos, unidades y conteos, nada de contenido de la
  tanda 1). La autora decide los casos.

## 6. El código y su sello

- **D:** los dos archivos de la segunda pasada, por blob. Su commit va después del sello de la tanda final y antes de esta corrida, con
  las anclas de F13 a F16b y F15f. La nota al pie del pre-registro de la tanda final sobre `r1_referencias.py` entra antes, en el commit
  de la §53 del registro de decisiones.
- **C1 de U-MED-DESAMB:**
  - el parche de `r1_invariantes.py` integrado detrás de una bandera nueva de la cadena (`--union-comunicaciones`), con `codigo_normalizado`
    de `parte2/tamanos_desamb_mesa.py` (sha256 sellado en el diseño, §11);
  - la lista de los códigos que no se unen, de la relectura del censo, como argumento con su sha256;
  - el selftest de la unión y R19 («solo código»);
  - una fila nueva en la tabla de reprocesamiento.
  - Es una unidad corta de código antes de esta corrida, con su despacho.
  - `r1_invariantes.py` también es una de las 78 rutas del código de la cadena (grupo «ensamblado»). Como los dos de D, entra después del
    sello de la tanda final, y antes del sello no se toca (pre-registro de la tanda final, §8).
- **Las claves:** el catálogo de resolución con las claves aprobadas, armado por script desde la hoja sellada de la autora, con su sha256 y
  su candado.
- **La lista de las 78 rutas** se vuelve a sellar con los archivos nuevos, y su sha256 va al sello del grafo evaluado.

## 7. El cegamiento

- Rige el §7 bis de U-PROC-HERENCIA, con la muestra de U-MED-VERIF-FICHAS en memoria y la lista de exclusión del despacho.
- Ninguna salida muestra contenido de nodos de la tanda 1 ni de la tanda final de las unidades de la muestra. Nada por estado de E3 ni de
  los reintentos (pre-registro de la tanda final, §4.1).
- La tabla compuesta de ids va en un `NO_ABRIR_`, como la de los códigos de la segunda pasada. El FRENO va por código.

## 8. Escrituras, prohibiciones y requisitos

- **La ejecutora** escribe solo en su scratchpad y en la copia permanente de su paquete. Corre sobre una copia del repo (rsync sin `.git`,
  `.venv`, `.env`, `NO_ABRIR_`, `*_SOLO_MESA*` ni enlaces; nunca un `git clone`; CLAUDE.md, §4.l).
- **Lo que sale de acá al repo** (los grafos del acumulado con la re-aplicación, su sello y sus tablas) entra con los commits de la autora,
  entre ejecutoras.
- **Cláusula v2** de las carpetas vedadas, más las carpetas de lectura de la autora.
- **El calendario:**
  - después de la relectura del censo y de la lectura de las claves (o de las 12:00 del sábado, sin las claves);
  - antes del sello del grafo evaluado.
  - En el v9c central, la medición va el viernes 23 hacia las 14:52, con tus casos (0,5 h) antes de la primera ola de B6.3.
- **FRENO** al final, con su revisión de la mesa.

## 9. Las decisiones de la autora al firmar

1. **La medición en cuatro pasos** (§2), para que cada pieza se pueda sacar sola. Recomiendo que sí: cuesta tres corridas más de la cadena,
   unos 20 min cada una (NO VERIFICADO), y USD 0.
2. **La bandera y la unidad de código de C1 de U-MED-DESAMB** (§6), con su despacho antes del viernes. Recomiendo que sí: el parche está
   preparado pero no integrado.
3. **Sin las claves:** si a las 12:00 del sábado no están aprobadas, la corrida va con D y C1, y el catálogo no crece, declarado (pre-registro
   de la tanda final, §9, decisión 4). Recomiendo dejarlo escrito así.

## Firma

**FIRMADO por la autora el 20/10/2026,** por mensaje recibido a las 10:01:39 (hoja de ruta de la mesa, §195), tal cual: «Firmo la
re-aplicación única en el borrador v2 (decisiones_185_mesa/reapl/UREAPL_reaplicacion_unica_BORRADOR_v2_mesa.md, sha256
65531aaf38d2184c0a9ef36bb870512d33cfad853a80642ec7812c3407ac74a0), con las decisiones 1 y 2 del §9 como las recomendás, la 3 con la
precisión 1, y estas cinco precisiones, que mandan sobre su texto:
1. La corrida va una sola vez (R3), a la hora del calendario vigente: en el v11 central, el jueves 22, antes del sello del evaluado. El §8
   se corrige con el v11, sin la referencia al v9c. Si para entonces una pieza no está lista, las claves incluidas, me lo avisás antes de
   la corrida y decido yo si se espera, como mucho hasta el sábado 24 a las 12:00 (R5), o si va al grafo corregido, declarada. Es la
   condición de R5: lo decido antes del corte, no al llegar. Reemplaza al «o de las 12:00 del sábado, sin las claves» del §8.
2. Las remisiones: si su mandato se firma antes de la corrida, entran como quinto paso (+ las remisiones), después de C1, con su regla de
   aislamiento como las otras piezas. Solo cambian aristas remite_a, cada una con su causa, y las que D ya cambió en el paso 2 se informan
   aparte. Si una arista cambia por las dos piezas, frena y decido yo.
3. Las 12 uniones evitadas de D son del acumulado de las tandas 0 y 1. Las de la tanda final las mide el paso 2, y se declaran igual.
4. El grafo evaluado es el del último paso que entra. Su versión con cola y su versión sin cola se arman dos veces, byte a byte iguales, con
   su sha256 en el FRENO.
5. La unidad de código de C1 se despacha a más tardar el miércoles 21, sobre una copia fuera del repo, y su commit va después del sello de
   la tanda, porque r1_invariantes.py es una de las 78 rutas. Ponela en el calendario con su hora.»
