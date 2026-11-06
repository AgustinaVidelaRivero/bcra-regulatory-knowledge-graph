# Mandato U-CONF-MATRIZ — lectura de confirmación de la matriz ampliada (`condicion_de` → Operacion y → Potestad)

**FIRMADO por la autora el 09/10/2026** (versión para firmar en `0c27146`), con las decisiones del §9. Rige desde esta firma. El
despacho, PENDIENTE de la autora. USD 0, sin API. El texto firmado son las líneas anteriores a «## Firma»: no se edita después y recibe
notas fechadas debajo de la sección «Firma».

## 0. Qué confirma y por qué

- **La decisión.** L-ESQ-R2 (FIRMADA, `4ef7650`), §6.3, decisión de la autora del 30/09: se ampliaron `condicion_de` → Operacion y
  `condicion_de` → Potestad.
  - → Potestad entró con un desvío declarado: 27 de 30, piso de Wilson 0,744, frente al criterio de 0,75.
- **La confirmación que pide el laudo:** «En r2b, E3 verifica cada relación nueva. Sobre el grafo re-extraído se lee una muestra de los
  dos pares, con lectura asistida y revisión de la autora. […] Si → Potestad no se confirma, se retira en el validador, en código, sin
  re-extraer».
- **Cuándo:** es requisito de B6.1, la tanda 1 (`docs/plan_tesis.md:405`, nota del 30/09, y `:409`: «Depende de 11, de la lectura de
  confirmación de la matriz posterior a 11 y del tablero»).
- **Qué se confirma:** que, en las aristas del grafo r2b (ya verificadas por E3), la Condicion es el antecedente de la Operacion o de la
  Potestad de destino, según el texto. Es la misma pregunta del estudio original, ahora sobre lo que produce el pipeline r2b.

## 1. Sobre qué grafo

**KG-Tanda0-Diez-r2b-sincola** (`e22fae1a…`, registrado en `data/experiment/neo4j/grafos.py:172`; sello `dde9f44` y `235a295`): el grafo
sin cola de la tanda 0, que es el que entra en la cadena de la evaluación. **Decisión de la autora del 09/10/2026.**
- **Población:**
  - 643 aristas `condicion_de` → Operacion;
  - 264 aristas `condicion_de` → Potestad.

  Comando: `poblacion_conf_matriz_mesa.py`, en el paquete de la mesa (`hoja_de_ruta_tanda1_mesa/conf_matriz/`); salida en
  `poblacion_conf_matriz_salida.txt`.
- **Como referencia:** en el grafo completo (`a9631a64`) son 676 y 273; en desarrollo sin cola (`2922b72d`), 546 y 237.

**El re-sellado.** Ningún ítem de U-OMISIONES-COD v7 cambia aristas `condicion_de`. Si → Potestad no confirma y el resultado llega antes
del FRENO de O2, el re-sellado saca sus aristas (§7).
- R0 (E3-01) re-verifica 20 unidades de la tanda 0 y puede cambiar lo que E3 acepta en ellas.
- **Control después del re-sellado:** las 60 aristas leídas siguen en el grafo re-sellado, con los mismos extremos, salvo las 30 de
  → Potestad si su retiro entró. Las que cambien se listan y se declaran. La cifra no se recalcula salvo que cambie el resultado del
  criterio.

**Solapamiento.** La etapa V del pre-registro de tripletas sortea en el grafo de desarrollo sin cola (`2922b72d`), cuyos TOs están en
diez. Si una arista leída acá cae también en la muestra de V, se declara el solapamiento; no se excluye (pre-registro, `:42`).

## 2. Criterio, sellado antes de leer

**El protocolo del 28/09/2026,** tal como está asentado en `reports/u_estudio_matriz/lectura/resultado_lectura_matriz.md` (`c671b52`,
sección «Protocolo, tal como está asentado»). Su sha256 en ese commit va al acta.
- **Correcta:** el texto del fragmento (propio y heredado de la unidad de procedencia) sostiene que el origen es condición del destino.
  Si el nodo parece mal tipado pero la relación es cierta, cuenta como correcta y se anota.
- **Incorrecta:** el texto no sostiene que la Condicion sea el antecedente del destino.
- **No decidible:** el texto no alcanza para decidir; va con su motivo.
- **El criterio, por par:** el par se confirma si el límite inferior de Wilson al 95 % de correctas / (correctas + incorrectas) es al
  menos 0,75, con las no decidibles excluidas y reportadas. Con más de 6 no decidibles, el par no se decide con esta muestra. Con 30
  decididas hacen falta 28 correctas; con 29, 27. Para otro n, el umbral se recalcula con el mismo piso.

## 3. Muestra

- **30 aristas por par,** por muestreo simple sobre la lista de aristas ordenada por (origen, destino):
  `random.Random(semilla).sample(lista, 30)`.
- **Semillas, fijadas por la firma:** `int(sha256("U-CONF-MATRIZ|Operacion|<sha256 del texto firmado>")[:16], 16)` y la misma con
  «Potestad». El texto firmado son las líneas de este archivo anteriores a «## Firma», en el commit de la firma.
- **El acta:** la población (sus dos sha256), la hora, la muestra y su sha256, el sha256 del criterio y el del grafo. Se sella antes de
  abrir una ficha, con el patrón de `data/experiment/lectura_aceptadas/l0_sellos.py`.
- **El orden de lectura es al azar, mezclando los dos pares:** el lector no ve el par al leer.

## 4. Ficha

- **El nodo Condicion:** tipo, etiqueta y descripción, con la descripción marcada como salida del extractor.
- **El predicado y el nodo de destino:** tipo, etiqueta y descripción, con la misma marca.
- **El texto de la unidad de procedencia de cada extremo,** propio y heredado (`e0_chunking/salida_tanda0_r2b/chunks_<to>.json`), con
  el tramo de E1 si lo hay. Si los dos extremos están en unidades distintas, van las dos.
- **Las páginas y la ruta del PDF.**
- **Sin el veredicto de E3, sin otras aristas del nodo y sin el resultado del estudio original.**

## 5. Quién lee

- **La lectura:** una sesión nueva de la mesa (lectura asistida por una instancia de modelo; desvío declarado, como el 28/09).
  - **Dónde corre:** abierta fuera del repo, con la cláusula de lecturas a ciegas de la plantilla de la mesa, porque la memoria del
    proyecto y los commits citan las cifras del estudio original.
  - **Qué hace:** lee las 60 fichas, marca cada una y sella la planilla (sha256 y hora) antes de calcular ninguna cifra.
- **La revisión** (decisión de la autora del 09/10/2026): la autora revisa todas las incorrectas y no decidibles, y 5 correctas por par.
  Adjudica las que no comparta.
  - **Las 5 correctas se sortean en C3,** entre las correctas del par ordenadas por (origen, destino), con
    `random.Random(semilla).sample(lista, 5)`; si son menos de 5, van todas.
  - **Semilla de revisión de cada par:** `int(sha256("U-CONF-MATRIZ|revision|Operacion|<sha256 del texto firmado>")[:16], 16)` y la
    misma con «Potestad». Queda sellada con la firma, antes de que exista ningún resultado.

## 6. Etapas

- **C1. El acta y las fichas** (la sesión lectora, antes de leer): población, sorteo, acta sellada y 60 fichas con su render.
- **C2. La lectura:** la planilla sellada.
- **C3. Las cifras:** por par, correctas, incorrectas y no decidibles, Wilson, y si cumple. La lista para la autora, con cada ficha.
  FRENO.
- **C4. La revisión de la autora y su adjudicación,** y la cifra final.

## 7. Qué pasa en la ruta si no confirma

Lo que sigue lo fija la autora el 09/10/2026, antes de la lectura.

- **→ Operacion no confirma: la relación no se retira** (decisión de la autora del 09/10/2026).
  - Queda en el grafo, con su cifra declarada.
  - Los errores se clasifican. Las clases salen de las notas de C2: la sesión lectora las propone en C3 y la autora las adjudica en C4.
  - Una clase sistemática que se pueda corregir con código va al grupo 2.
- **→ Potestad no confirma con el criterio del §2: rige L-ESQ-R2 §6.3** (`4ef7650`): se retira en el validador, en código, sin
  re-extraer. Cuándo, lo fija la autora el 09/10/2026, antes de la lectura:
  - **Si el resultado está antes del FRENO de O2 de U-OMISIONES-COD,** el retiro entra al re-sellado único de la tanda 0, como única
    excepción al alcance congelado (hoja de ruta de la mesa, §29). Toca:
    - la matriz del validador r2 (`AMPLIACION_R2`);
    - S3 de los shapes;
    - la fila de la matriz en el laudo de la release r2;
    - y saca del grafo de la tanda 0 las 264 aristas del sin cola (273 en el completo).

    Rige también desde la tanda 1: el prefijo de E1 (congelado en la release r2) sigue pidiendo esas relaciones y el validador las
    rechaza. Quedan en el registro de rechazos, declaradas, y ninguna clave de caché de E1 se mueve.
  - **Si llega después,** el retiro va al grupo 2 del barrido de límites: antes de sellar el grafo evaluado, en paralelo con el escalado
    (`docs/plan_tesis.md:778`). Hasta entonces, las aristas → Potestad quedan en el grafo de la tanda 0 y en el de la tanda 1, con la
    cifra de esta lectura declarada.
  - **«El resultado»** es la cifra final de C4, después de la adjudicación de la autora.
  - **Condición de ejecución, no decisión:** el retiro toca archivos que la v7 firmada no autoriza (`validador_r2.py` fuera de f y g1, y
    los shapes) y cambia `kg.json` fuera de los grupos de su §4. Si se dispara antes del FRENO de O2, necesita su autorización de
    escritura: una nota fechada debajo de la sección «Firma» de la v7, o el mandato de la etapa del re-sellado. La elige la autora en
    ese momento.
- **Un par no se decide** (más de 6 no decidibles): una muestra complementaria de 30 del par, entre las aristas que no salieron, con la
  semilla `int(sha256("U-CONF-MATRIZ|complementaria|<par>|<sha256 del texto firmado>")[:16], 16)`, sellada con la firma. Suma un día,
  y «el resultado» de ese par es el de la muestra complementaria.
- **Calendario estimado** (NO VERIFICADO): despacho lun 12/10, C1 y C2 mar 13, C3 mié 14 y la revisión de la autora mié 14/10. Llega
  antes de O2.

## 8. Escrituras y prohibiciones

**ESCRITURAS:**
- `data/experiment/conf_matriz/`, que se crea: el acta, las fichas, la planilla sellada, las cifras y los scripts;
- el scratchpad de la sesión.

**PROHIBIDO:**
- la API;
- todo otro archivo del repo;
- los grafos sellados;
- el validador y la matriz;
- el criterio una vez sellado;
- commitear.

**REQUISITOS:**
- CLAUDE.md §4 (a a l);
- la cláusula «límites medidos, caso por caso» de la plantilla de la mesa;
- los mensajes de commit sin unidades, documentos ni mecanismos;
- la tesis: la versión vigente está en Overleaf, y `docs/tesis/main.tex` no se usa como fuente sin declararlo.

## 9. Decisiones

**Tomadas por la autora el 09/10/2026, antes de la lectura:**
- el grafo: el sin cola, `e22fae1a` (§1);
- si → Operacion no confirma, la relación no se retira: queda con su cifra declarada, los errores se clasifican, y una clase sistemática
  que se pueda corregir con código va al grupo 2 (§7);
- si → Potestad no confirma, rige L-ESQ-R2 §6.3: con el resultado antes del FRENO de O2, el retiro entra al re-sellado como única
  excepción al alcance congelado; después, va al grupo 2 (§7);
- la revisión: las no correctas más 5 correctas por par, con la semilla de revisión sellada con la firma (§5).

No queda ninguna decisión pendiente para leer.

## Firma

FIRMADO por la autora el 09/10/2026 (versión para firmar en `0c27146`). Rige desde esta firma.

- **Qué cambió de `0c27146` al asentar la firma:**
  - la cabecera;
  - el §1, por el retiro de → Potestad en el re-sellado;
  - en el §3, la llamada del sorteo;
  - el §5, con la revisión decidida y su semilla;
  - el §7, con cuándo se retira → Potestad y la semilla de la muestra complementaria. Sale la mención a la «opción III», que no aplica
    a esta lectura;
  - el §9.
- **Semillas, selladas con este commit.** Texto firmado (las líneas anteriores a «## Firma»): sha256
  `1d92fbd6ccfd9404aa3417df96b3fab2ffda1d61aca74074446ea5d6b9366d7d`.

  - muestra de → Operacion: `16560617781465913851` (cadena `U-CONF-MATRIZ|Operacion|` más el sha256 del texto firmado);
  - muestra de → Potestad: `10236682513526931005` (cadena `U-CONF-MATRIZ|Potestad|` más el sha256 del texto firmado);
  - revisión de → Operacion: `3317428300167781795` (cadena `U-CONF-MATRIZ|revision|Operacion|` más el sha256 del texto firmado);
  - revisión de → Potestad: `9868107349525416484` (cadena `U-CONF-MATRIZ|revision|Potestad|` más el sha256 del texto firmado);
  - complementaria de → Operacion: `1949760007166469060` (cadena `U-CONF-MATRIZ|complementaria|Operacion|` más el sha256 del texto firmado);
  - complementaria de → Potestad: `1922576108924699355` (cadena `U-CONF-MATRIZ|complementaria|Potestad|` más el sha256 del texto firmado).

  Se reproducen sobre el archivo del commit de la firma (la segunda línea toma el sha256 de la primera; `<uso>` es lo que va entre
  `U-CONF-MATRIZ|` y el sha256, por ejemplo `Operacion` o `revision|Potestad`):

  ```
  git show <commit de la firma>:docs/mandatos/UCONF_MATRIZ_lectura_confirmacion.md | sed '/^## Firma$/,$d' | shasum -a 256
  python3 -c "import hashlib,sys; print(int(hashlib.sha256(('U-CONF-MATRIZ|'+sys.argv[1]+'|'+sys.argv[2]).encode()).hexdigest()[:16],16))" '<uso>' <sha256 del texto firmado>
  ```

  Ninguna muestra se sortea antes de este commit.

---

**[09/10/2026] Nota de la mesa: C2 contaminada y su repetición, C2-bis (decisiones de la autora del 09/10/2026).** El texto firmado no
cambia.

- **Por qué la primera C2 no se usa para decidir** (revisión de la autora de su FRENO):
  - lo que vio el lector traía la cifra anterior de → Potestad y el umbral (§0);
  - el §3 (el lector no ve el par) y el §4 (la ficha trae el tipo del destino) se contradicen, y el lector siguió el §4;
  - la sesión se abrió dentro del repo y cargó la memoria del proyecto y los últimos mensajes de commit;
  - el lector declaró un cambio de marcas antes del sello, hecho conociendo el par y el umbral.

  La primera lectura queda registrada como contaminada en `data/experiment/conf_matriz/` y no se usa para decidir. La mesa no conoce
  sus cifras ni sus marcas.
- **C2-bis: una lectura nueva, con un lector nuevo,** sobre las mismas 60 fichas selladas en C1 (`c1/fichas_c1.jsonl`, `ebe7dd72…`).
  - **Dónde:** una sesión nueva abierta desde una carpeta fuera del repo. Trabaja solo con una copia de las fichas y sus páginas, sin
    acceso al repo, a la memoria ni a la primera lectura.
  - **Lo que ve el lector:** las fichas, sus páginas y las instrucciones. Ninguna cifra previa, ni el umbral, ni el criterio de
    aceptación, ni las consecuencias, ni que es una repetición.
  - **El criterio de las marcas:** el del protocolo del 28/09 (`c671b52`), sin agregar ninguno, con incorrecta y no decidible como en
    el §2.
  - **El §3 y el §4:** el tipo del destino no hace falta para juzgar la arista, porque el criterio pregunta si el texto sostiene que el
    origen es condición del destino, y muestra el par. Se saca, junto con los ids de los dos nodos (el del destino empieza con su tipo).
    Declarado: la anotación de «mal tipado» del protocolo queda solo para el origen.
  - **La carpeta del lector:** la arma la mesa desde las fichas selladas, con `armar_paquete_lector_C2bis_mesa.py`, en el paquete de
    la mesa (`hoja_de_ruta_tanda1_mesa/conf_matriz_C2bis/`). Su `manifest.txt` empieza con `d6647440bb4b3b81`. Control: 0 fichas con el
    tipo del destino o con ids.
  - **El sello:** la planilla se sella (sha256 y hora) antes de cualquier cálculo. El lector no calcula.
  - **C3:** lo calcula la mesa después del sello, con `c3_C2bis_mesa.py`. El par de cada ficha sale del acta sellada de C1, y el
    criterio es el del §2.
- **Decide la lectura nueva, cualquiera sea el resultado.** «El resultado» del §7 es la cifra final de C4 de esta lectura.
- **C4:** la autora revisa las incorrectas de la lectura nueva, 5 correctas por par y toda ficha en la que las dos lecturas no
  coinciden.
  - **Semillas de las 5 correctas, selladas por esta nota:** Operacion `4532495010434239514` y Potestad `2215609819628898327`, con
    `random.Random(semilla).sample(lista, 5)` sobre las correctas del par ordenadas por (origen, destino).
  - Reemplazan a las de revisión de la sección «Firma».
- **Calendario:** C4 antes del FRENO de O2 de U-OMISIONES-COD.

**[10/10/2026] Nota de la mesa: dos precisiones a la nota de C2-bis** (decisiones de la autora del 10/10/2026). El texto firmado no cambia.

- **C4 incluye además todas las fichas que la lectura nueva marque `no_decidible`,** como decía el §5.
- **La línea del protocolo del 28/09 que respalda que el juicio no necesita el tipo del destino** (`c671b52`,
  `reports/u_estudio_matriz/lectura/resultado_lectura_matriz.md`, «Protocolo, tal como está asentado»):

  > Correcta: el texto del fragmento sostiene que el origen es condición (o excepción, o se aplica a, según el predicado) del destino;
  > si el nodo parece mal tipado pero la relación es cierta, cuenta como correcta y se anota.

  La marca depende de lo que sostiene el texto, y un nodo mal tipado con la relación cierta cuenta como correcta: el tipo no decide.

**[10/10/2026] Nota de la mesa: C3 de C2-bis, la C4 y las clases de → Operacion** (decisiones de la autora del 10/10/2026). El texto
firmado no cambia.

- **C3** (`data/experiment/conf_matriz/c2bis/registro_C2bis.md`): → Operacion, 26 correctas, 4 incorrectas y 0 no decidibles, límite
  inferior de Wilson 0,7032; → Potestad, 29, 1 y 0, 0,8333. Son cifras de C3: la final es la de C4.
- **La C4 la hace la autora** con la lista de la mesa (`c2bis/lista_C4_C2bis.md`, 15 fichas), antes del jueves 15/10/2026. Sigue
  valiendo que va antes del FRENO de O2 (nota de C2-bis).
- **Las clases de los errores de → Operacion** (§7), sobre la propuesta de la mesa en `registro_C2bis.md`, quedan aceptadas:
  - **«tramos contenidos entre los extremos»** (F27, F34 y F45 en C3): va al grupo 2 después de medir su precisión sobre la población
    de la arista;
  - **«condición de otro elemento del punto»** (F15): no se puede detectar con código y queda como error clasificado.
  - Si la C4 deja una incorrecta que no entra en ninguna de las dos, su clase queda PENDIENTE de la autora.
- **→ Operacion no se retira** (decisión del 09/10/2026, §7): queda en el grafo con su cifra declarada, la de C4.

**[15/10/2026] Nota: el re-sellado único de los grafos r2b de la tanda 0.** Los grafos sellados que cita este documento tienen una versión posterior, del re-sellado único (`docs/mandatos/URESELLADO_T0_resellado_unico_grafos_r2b.md`, firmado; FRENO en `data/experiment/resellado_t0/FRENO_resellado_T0.md`): `a9631a64…` (KG-Tanda0-Diez-r2b) → `fda6c07d…` (KG-Tanda0-Diez-r2b-rs1, 8.788 nodos y 27.430 aristas); `e22fae1a…` (KG-Tanda0-Diez-r2b-sincola) → `61dd1b69…` (KG-Tanda0-Diez-r2b-sincola-rs1, 8.491 nodos y 25.976 aristas); `2922b72d…` (KG-Tanda0-Desarrollo-r2b-sincola) → `66e745f5…` (KG-Tanda0-Desarrollo-r2b-sincola-rs1, 6.711 nodos y 21.996 aristas). Cambian por el código de U-OMISIONES-COD (`ded41d50`) y por las salidas de R0 (`1d690df3` y `2d0f5277`); los de diez, además, por R2-3 (`803623a`), que los sellados no tenían. El diff por campo y por causa está en `data/experiment/resellado_t0/salidas/`. Los sellados siguen sellados (principio 9); el commit del sello de los nuevos queda en `commit_sellado` de `data/experiment/neo4j/grafos.py`. El control de después del re-sellado: de las 60 aristas leídas, 59 siguen en `61dd1b69…` con los mismos extremos. F49 no: es de `ext::3.16.2.1`, una unidad de R0 aceptada tras un reintento nuevo, con otra extracción, en la que ya no están ni el origen ni el destino de la arista leída (la unidad pasa de 7 a 10 `condicion_de` hacia una Potestad, que es otro nodo). Ninguna sale por el retiro de → Potestad. La cifra no se recalcula (`:38`) salvo que la autora lo decida (`data/experiment/resellado_t0/salidas/controles_s4_rs1.json`, `A_conf_matriz`). El texto firmado no cambia.

**[15/10/2026] Decisión de la autora sobre F49** (recibida a las 19:33:19; hoja de ruta de la mesa, §113), tal cual: «F49: la cifra de
U-CONF-MATRIZ no se recalcula. Se declara que se midió sobre el grafo sellado, que en el re-sellado 59 de las 60 aristas leídas siguen con
los mismos extremos, y que F49 cambió porque su unidad se re-extrajo en R0.» El texto firmado no cambia.
