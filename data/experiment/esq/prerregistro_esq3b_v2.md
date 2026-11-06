# Pre-registro de la VUELTA 2 de ESQ-3b — revisión de retoques post-regresión

**FIRMADO por la autora — 02/09/2026** (§0 resuelto por decisión de autora;
correcciones de no-filtración de mesa revisora aplicadas; enmienda al laudo
(e) ratificada; firmado ANTES de correr nada). Ejecuta los laudos de autora sobre el §7 de la tabla de
resultados (`0c19dc8`): re-corrida única de los retoques revisados, con
predicciones re-selladas ANTES de correr. Gobernada por: pre-registro de
ESQ-3b (`01bf046` + Adenda 1 `f1fe0d8`), tabla `0c19dc8`, desvíos
(`desvios_lectura_esq3b.md`). Regla rectora sin cambio: **ningún retoque
entra al esquema congelado sin sus brazos pasando** — y ahora con **regla
de DOS STRIKES** (§4).

## §0. RESUELTO POR DECISIÓN DE AUTORA — regla de regresión fresca sustituida (la dictada era vacía por construcción)

El laudo (a)(iv) dictó: «fichas con q2=ninguna entre las 32 de ESQ-2 que no
entraron a ESQ-3b». **Verificado por mesa: ese conjunto es VACÍO** — las 35
fichas q2=ninguna se agotaron exactas entre los dos brazos de la vuelta 1
(26 regresión + 9 objetivo); las 32 restantes son 29 con firma y 3 duda. El
error es de la recomendación de mesa que el laudo adoptó, y se declara.
**Sustitución ADOPTADA por decisión de autora:** la regresión
fresca sale de las **687 unidades extraídas y NO fichadas** de ESQ-2
(extracción vieja ya paga; sin marcas previas — la métrica de §4 no las
necesita: la adjudicación es fresca sobre la ficha pareada): **12 unidades**
por sorteo estratificado por TO (mínimo 1 por TO, proporcional al resto),
semilla sellada `20260903:regresion_fresca_v2`, generador nuevo por TO
sobre ids ordenados (patrón de ESQ-2), **con exclusión explícita de las 75
unidades fichadas de ESQ-2 (y por lo tanto de todo brazo previo) y de las
15 del brazo objetivo de esta vuelta** — el pool es exactamente las 687 no
fichadas. Sin cruce con el desvío (a): ninguna
proviene de fichas (no hay marcas que contaminar); se declara así en la
tabla. La alternativa (mezclar las 3 fichas duda de las 32 restantes con 9
de las 687) queda DESCARTADA por la autora: mezcla poblaciones.

## §1. Qué cambia en el prefijo (v2) — textos exactos de las delimitaciones revisadas

El prefijo v2 = prefijo v1 sellado (`f0a421fb9466`) + los cambios de abajo
− el predicado `exceptua_operacion` (R6a RECHAZADO: sale de la matriz, del
catálogo y del conteo de predicados; residuo documentado junto a R6b,
promovible en r2). Mismo mecanismo de reemplazos declarados con ancla
única; namespace de caché nuevo; `prompt_e1.py` no se toca.

**Regla de redacción de estas delimitaciones (corrección de mesa
revisora, vinculante)**: las delimitaciones nuevas DESCRIBEN los patrones
sin citar texto de ninguna unidad de predicción ni de la selección — una
cita verbatim en el prefijo sembraría la predicción. Donde el laudo (e)
dictaba un patrón citado como ejemplo, se reemplaza por su descripción; el
reemplazo queda registrado acá y está **RATIFICADO por decisión de autora
como enmienda al laudo (e)**: la regla de no-filtración supersede el
ejemplo dictado. Las marcas léxicas ya presentes en el
prefijo v1 sellado no se re-citan en el texto nuevo (son simétricas en el
pareo por preexistentes).

**Potestad — se agrega al final de su definición:**
> «POLARIDAD (no la confundas): la SUPRESIÓN o exención de un requisito NO
> es una potestad — un enunciado cuyo efecto es negar la exigibilidad de
> algo dice que un deber no aplica, no que alguien quede habilitado; ese
> contenido va a la caja que corresponda (Excepcion si suspende una regla)
> y NUNCA a Potestad. El disparador de Potestad es la MODALIDAD deóntica de
> habilitación (las marcas listadas arriba), no el léxico: la mera
> presencia de vocabulario de autorización o permiso no hace Potestad. El
> contenido HABILITANTE —una norma cuyo efecto es que un sujeto PUEDA
> realizar algo— es Potestad y SÍ se extrae: no es contenido
> meta-normativo.»

**Definicion — se agrega al final de su delimitación:**
> «QUE EL CUERPO DEFINA, NO QUE EL ENCABEZADO LO SUGIERA: un encabezado o
> título que nombra un término o anuncia contenido conceptual no vuelve
> definitoria a la unidad si el cuerpo prescribe, aplica o delimita alcance
> en vez de definir. Y si el definiendum es un ACTO regulado, va SOLO en
> Operacion: NO emitas un nodo Definicion además de la Operacion — el
> mismo contenido no se duplica en dos cajas.»

**Condicion — se agrega a su delimitación:**
> «El supuesto puede estar enunciado por el ENCABEZADO HEREDADO: si el
> contexto heredado termina anunciando las condiciones o supuestos que los
> ítems siguientes enumeran, la unidad entera es una Condicion de la norma
> de ese encabezado — NO una Obligacion autónoma, aunque su verbo esté en
> subjuntivo con forma de deber.»

**Regla 9 (R4) — dos retoques en su texto:**
> (i) tras «cláusulas interpretativas», se agrega la descripción explícita:
> «(típicamente, construcciones que niegan que un acto o una participación
> tenga determinado significado o efecto jurídico)»;
> (ii) al final: «NO es meta-normativo el contenido HABILITANTE: una norma
> cuyo efecto es que un sujeto pueda realizar algo PRESCRIBE (es Potestad)
> y SÍ se extrae — esta regla prohíbe fabricar prescripciones falsas, no
> omitir permisos reales.»

**`requisito_de_estructura` — su descripción en el enum se reemplaza por:**
> «`requisito_de_estructura` es el deber de DISPONER de algo con carácter
> permanente: políticas, procedimientos, manuales, sistemas, órganos,
> personal designado, forma jurídica, sede. NO son requisito_de_estructura:
> las constancias documentales, las condiciones de elegibilidad, las
> aprobaciones puntuales de un órgano, las autorizaciones previas — eso va
> a su clase o a "otra".»

## §2. Selección de la corrida (mecánica, se persiste ANTES de extraer)

- **Objetivo (15 unidades)**: las 3 falladas (`actgar::1.3.1::intro`,
  `prevmi::1.2`, `actgar::2.11.3`) + anclas R1 (`opefci::6.3`,
  `ctacor::1.1`) + anclas R3 (`adrei::1.3.1`, `cryl::1.2`,
  `traval::1.1.1.1`) + R2 (`lavdin::3.3.4.3`) + R4 (`cryl::1.2` ya
  contada, `opefci::2.1`) + RE (`ayccef::5.1.1`, `traval::3.1`, y las
  portadoras de emisiones avaladas: `adrei::2.1.2::intro`,
  `adrei::4.1.1.4`, `expaef::9.1`).
- **Regresión fresca (12 unidades)**: según §0 (la regla que la firma
  resuelva).
- Brazos disjuntos; archivo sin timestamp, byte-reproducible; el brazo base
  de las 15 del objetivo es la extracción de la vuelta 1 (`pareado_esq3b.jsonl`)
  y el de las 12 frescas es la extracción de ESQ-2 (`cobertura/`).

## §3. Predicciones RE-SELLADAS (una por línea; se adjudican por separado, sobre fichas pareadas cegadas)

**Declaración de alcance (extendida por la autora)**: P1–P3, P10 y P12–P13
son **test del parche sobre casos conocidos, no de generalización** — todas
son predicciones sobre unidades que motivaron el ajuste que verifican. La
generalización la miden la **regresión fresca** (12 unidades que jamás
informaron ajuste alguno) y la **ventana de la tanda 1 de B6**.

**Anti-atracción (las 3 falladas — su cumplimiento levanta el primer strike):**
- **P1** `actgar::1.3.1::intro`: no emite Potestad ni ningún tipo nuevo (la
  exención de requisito no migra).
- **P2** `prevmi::1.2`: no emite Definicion (la regla de aplicación no es
  definitoria).
- **P3** `actgar::2.11.3`: no emite Definicion (cláusula anti-encabezado).

**Re-confirmación de anclas (que el parche no rompa lo que R1/R3 ya
cumplían):**
- **P4** `opefci::6.3`: sigue emitiendo Potestad para «podrán negociar».
- **P5** `ctacor::1.1`: sigue emitiendo Potestad para «se encuentran
  facultadas».
- **P6** `adrei::1.3.1`: sigue emitiendo Definicion con su término.
- **P7** `cryl::1.2`: sigue emitiendo Definicion con término «cuenta de
  registro».
- **P8** `traval::1.1.1.1`: la Operacion se conserva Y NO se emite
  Definicion (la sobre-emisión de la vuelta 1 corregida).

**R2 (última chance; condición de salida sellada):**
- **P9** `lavdin::3.3.4.3`: produce Condicion, no una Obligacion con deber
  autónomo. **Si P9 falla: alcance de R2 reducido y declarado (condiciones
  intra-chunk), f. 39 residuo con destino E3/r2 — sin tercera corrida.**

**R4 afinada:**
- **P10** `cryl::1.2`: la cláusula interpretativa del BCRA no genera ningún
  nodo prescriptivo (compatible con P7: Definicion sí, Restriccion no).
- **P11** `opefci::2.1`: la habilitación de entidades produce Potestad — la
  unidad NO queda vacía.

**`requisito_de_estructura` afinado:**
- **P12** `ayccef::5.1.1`: su obligación no lleva `requisito_de_estructura`.
- **P13** `traval::3.1`: ídem.
- **P14 (conservación de lo avalado)**: las emisiones avaladas de la tabla
  conservan el valor — `adrei::2.1.2::intro` (×2), `adrei::4.1.1.4`,
  `expaef::9.1` (×2).

## §4. Métrica, reglas de falla y DOS STRIKES

- **Métrica de regresión vigente** (§3 del pre-registro v1, sin cambio):
  migración a caja nueva adjudicada INCORRECTA por la autora; variaciones
  de label/descripcion sin cambio de tipo no cuentan. En la regresión
  fresca (sin marcas previas) la adjudicación es directa contra el texto en
  la ficha pareada.
- **Adjudicación de `requisito_de_estructura` (regla no circular, sellada)**:
  en la regresión fresca, **TODA emisión de `requisito_de_estructura` se
  adjudica avala/objeta en la lectura de la autora**; la falla de RE es
  ≥1 objetada.
- **REGLA DE DOS STRIKES (sellada)**: un retoque que falla su SEGUNDA
  regresión queda **FUERA del esquema congelado y va a r2 — sin
  re-iteración**. Aplica a R1 y R3 (primer strike en la vuelta 1) y a
  cualquier retoque cuya emisión atraiga incorrectamente en la regresión
  fresca.
- La **ventana de la tanda 1 de B6** sigue como test de generalización de
  lo que esta vuelta no cubre (política post-congelado del laudo ESQ-3a §8).

## §5. Reglas de ejecución

- **No-filtración extendida a TODO el texto agregado**: ninguna ventana de
  5 palabras del texto de ninguna unidad seleccionada (objetivo Y regresión
  fresca) aparece en el texto agregado o modificado por los retoques v2;
  coincidencias preexistentes del prefijo v1/producción se declaran
  (simétricas en el pareo). ADEMÁS (corrección de mesa revisora): el
  selftest verifica que ninguna delimitación nueva contenga citas de las
  unidades de predicción aun por debajo de la ventana de 5 palabras —
  bigramas y trigramas distintivos incluidos (lista de n-gramas de las
  unidades P1–P14 contra el texto agregado, con las palabras funcionales
  excluidas). Verificado en selftest antes del freno 1.
- **Instrumento**: el arreglo del **bug de pegado** (el volcado del render
  en un campo de respuesta, nota de la tabla) es **PRERREQUISITO de la
  lectura** — con selftest que pegue un render de ficha y verifique que no
  contamina el campo. Rigen además: cegado (entrada 10; fichas sin brazo,
  retoque, origen ni marca previa), entrada de textos largos (entrada 11),
  DUDA con nota, observaciones por unidad.
- **Caching**: decisiones de `docs/decisiones_caching_extraccion.md`
  vinculantes; namespace nuevo por prefijo-hash; db propia de la vuelta
  (`esq_3b_v2.db`); modelo resuelto por llamada.
- **Freno 1 obligatorio**: manifiesto (diff del prefijo v2 + sha, selección
  persistida, estimación) ANTES de gastar; freno final antes de toda
  adjudicación. La lectura y toda adjudicación son de la autora;
  spot-checks de mesa posteriores con semilla declarada.

## §6. Costo y tope

~27 unidades (15 objetivo + 12 regresión fresca) con prefijo nuevo:
estimación ≈ USD 0,20 (por unidad promedio de las corridas previas + techo
de escrituras de prefijo). **TOPE PROPIO: USD 0,40**, dentro del remanente
de ESQ-3b (0,7529) y de la saga.

## §7. Registro — fe de erratas acumulada de mensajes de commit

Los mensajes de `01bf046`, `930f289` y `0c19dc8` tienen artefactos
cosméticos de pegado de terminal (espacios comidos: «extraccionespersistidas»,
«decada», «PASAcon», entre otros); **los archivos están intactos en los
tres** — se declara, no se reescribe (patrón de la fe de erratas de
mensajes del plan, donde esta lista se consolida en el próximo pase).

## §8. Salida

Tabla de la vuelta 2 por predicción (P1–P14) y por retoque, con la doble
lectura que corresponda; veredictos finales de R1, R2, R3, R4 y RE; con eso
—y con R5, R7, R8, R9-núcleo ya adjudicados y R6a/R6b como residuos— queda
TODO el material del **laudo de esquema congelado**.

## Firma

Firmado por la autora, 02/09/2026, con el §0 resuelto (regresión fresca de
las 687 no fichadas, alternativa descartada), la declaración de alcance de
§3 extendida a P1–P3 y P10, y la enmienda al laudo (e) ratificada. Las
delimitaciones de §1, las predicciones de §3, las reglas de §4 (dos strikes
incluida) y el tope de §6 quedan sellados: nada se modifica después de la
primera llamada de la corrida.
