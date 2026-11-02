# Enmienda 1 al pre-registro de la evaluación por tripletas — vía de umbrales: exactitud de los campos de los umbrales

**FIRMADA por la autora el 08/10/2026** (firma por mensaje de la autora; versión para firmar en `97bc53d`), con las decisiones D1 a D10
del §14.1, tomadas el mismo día. Rige desde esta firma. Redactada en la unidad U-MED-UMBRALES (solo diseño, USD 0), sobre HEAD `1f9b262`;
los archivos citados no cambian hasta `18d9e05`, y sus anclas siguen valiendo en `a91f95f` (el único cambio en un archivo citado es la
nota de la fila B6.3, `plan:778`, que no mueve líneas). Revisión de la mesa sobre una copia (08/10/2026): los recuentos del marco, los
vacíos, los estratos y el tamaño se reproducen con los scripts de `data/experiment/med_umbrales/` (nota del plan, fila B6.3). El texto
firmado son las líneas anteriores a «## Firma»: no se edita después y recibe notas fechadas debajo de la sección «Firma».

Enmienda con fecha a `docs/preregistro_evaluacion_tripletas.md`, FIRMADO por la autora el 07/10/2026 en `4afbe51` (sha256
`8ce611ba…`; el archivo de HEAD es idéntico, verificado con `git show 4afbe51:docs/preregistro_evaluacion_tripletas.md | shasum -a 256`).
El pre-registro no se edita: su cabecera dice que el texto firmado recibe notas fechadas al pie (`4afbe51:…:6-7`); al firmarse esta
enmienda, recibe la nota del §14.3. Ninguna de las once decisiones de su §10 cambia (§13).

## 0. De dónde sale y por qué es admisible

- **El hueco.** VERIF-UMBRALES (FRENO del 08/10/2026, solo lectura, sin commit; paquete en
  `fuera_del_repo/scratchpads/61c6bddf-8da2-47b9-80c4-be576b464778/scratchpad/reports/verificaciones_tesis/VERIF-UMBRALES/`, reporte
  sha256 `7e09514a…`, §4): las pruebas automáticas de las reglas pasan, pero ninguna lectura ni evaluación compara el valor, la unidad,
  la comparación o la base de un umbral con lo que dice la norma. Este pre-registro juzga los «valores» de cada arista como componente
  (iii) del juez (`4afbe51:…:103-114`), sin una cifra propia para los umbrales.
- **Admisible.** La evaluación no corrió: el sorteo de la etapa V espera el re-sellado único de la tanda 0
  (`docs/laudo_release_r2_pipeline.md:53`), y en el repo no hay muestra, ficha ni etiqueta (`git ls-files | grep -i tripleta`: solo el
  laudo D-f, este pre-registro y la figura de la tripleta). Una vía nueva, registrada antes de sortear nada, no mira ningún dato.
- **Precedente.** Enmiendas separadas con fecha a un pre-registro firmado: las tres al de la tanda 0
  (`docs/enmienda_preregistro_tanda0_2026-09-27_fase2a2b.md`, `…_2026-09-27_observacion12.md`, `…_2026-09-30_ventana.md`).
- **Por qué acá y no en un pre-registro aparte** (decisión D1): mide el contenido del grafo, igual que las vías de precisión y de
  cobertura; corre sobre los mismos grafos sellados; usa el mismo armador de fichas, el mismo sorteo sellado y los mismos estimadores; y entra al
  mismo componente (d) de B6.3 (`plan:778`). Lo que la separa (otra unidad, otra población y una etapa de desarrollo con correcciones
  de código) cabe como una vía con secciones propias.
- **Definiciones de referencia.** El sentido de cada valor de los campos lo fijan L-ESQ-R2, §1.3, FIRMADA en `4ef7650` (sha256
  `66c4a1b9…`, `:240-340`); su enmienda 3, FIRMADA en `8d01b04` (el plazo sin marcador queda `no_determinada`); su enmienda 5, FIRMADA en
  `3a4b980` (alcance de la negación y comparador pegado a la cuantía); y la calibración P3 de U-PYD (`57a8dd2`, resumida en `plan:401`).
  El código (`data/experiment/pyd_r2/code/reglas_comparacion.py`, sha256 `69c48d24…`; `data/experiment/tanda0/code/ensamblar_tanda0.py`,
  `d5a2f27c…`; `data/experiment/pyd_r2/code/validador_r2.py`, `86464bfc…`) es lo que se mide, nunca la referencia.

## 1. Qué mide y qué no

Mide si los campos de cada elemento de umbral del grafo (la lista `properties.umbrales` de Restriccion, Obligacion, Condicion y
Excepcion; `modelos_r2.py:270-315`) dicen lo que dice la norma, leída con las definiciones del §0.

No mide: (a) los umbrales que la norma tiene y el grafo no guarda (recall; queda como límite declarado, y la vía de cobertura lo toca en
parte); (b) la respuesta del agente, que es B6.3 (b); (c) el tramo guardado, que en los elementos del ensamblado es solo la cuantía, por
diseño (`ensamblar_tanda0.py:755`; VERIF-UMBRALES, §1). Sus cifras no se suman ni se comparan con las de precisión: una cuenta
elementos de umbral y la otra aristas (la misma regla del §1 del pre-registro, `:39-42`).

## 2. Unidad y campos

**2.1 Unidad.** El elemento de umbral, no el nodo: un nodo puede tener varios (1.306 elementos en 1.123 nodos en el grafo sin cola de la
tanda 0, `estratos_umbrales_salida_UMEDUMBRALES.txt`).

**2.2 Referencia.** El texto de la unidad de E0 del nodo, propio y heredado, y la página del PDF si el texto de E0 es dudoso. Nunca la
descripción del nodo ni otra salida de un modelo.

**2.3 Resultado por campo.** *Correcto*; *contradicho* (el grafo dice otra cosa); *omitido* (la letra lo fija y el campo está vacío o
`no_determinada`); *espurio* (el campo está lleno y la letra no lo fija); *parcial* (solo la base); *no aplica*; *no decidible* (necesita
un experto, o el texto o la tabla no se leen), que se reporta aparte con sus dos cotas.

| campo | aplica a | correcto si | casos límite |
|---|---|---|---|
| **pertinencia** (precondición) | todo elemento | la cuantía (en los del validador, el límite relativo) está en el texto de la unidad y fija un umbral, plazo, porcentaje o coeficiente de la regla que representa el nodo | *no pertinente*: el número de una norma citada, una fecha, el número de un punto, un ejemplo, o la cuantía de otra regla del mismo párrafo; *inexistente*: la cuantía no está en la norma (sale de la descripción); *duplicado*: un segundo elemento de la misma cuantía en el mismo nodo |
| **valor** | elementos con cuantía; en los del validador, que la cláusula no traiga cuantía | numéricamente igual a la cuantía, normalizada | «1,25 %» → 1.25; «$ 5.000 millones» → 5000000000; «dos veces» → 2; «180 (ciento ochenta) días» → 180; «el quinto día hábil» después de «hasta el» → 5; *contradicho*: otro número, otro multiplicador, un compuesto partido («treinta y cinco» leído como 5); *omitido*: un elemento del validador sin valor cuando la cláusula trae cuantía |
| **unidad** | ídem | la de la norma en la lista cerrada (porcentaje, moneda, días, meses, años, veces, UVA); horas y semanas, con la marca `fuera_de_lista` | «puntos básicos», «por mil» o una fracción guardados como porcentaje: *contradicho*; horas sin la marca: *contradicho*; la unidad que hereda una celda del rótulo de su tabla: correcta si el rótulo rige esa celda |
| **moneda** | unidad moneda | el código de la moneda que nombra la norma (ARS, USD, EUR) | «pesos o su equivalente en otras monedas» → ARS; «dólares estadounidenses» sin código: *omitido*; UVA es unidad, no moneda |
| **tipo de días** | unidad días | lo que dice la cláusula de la cuantía («hábiles», «corridos»); vacío si no lo dice | una regla general del TO («los plazos se computan en días hábiles») no se le exige al campo (decisión D8): se registra como dato informativo; hábiles por corridos: *contradicho* |
| **comparación** | todo elemento con contenido (los vacíos, §2.5) | el sentido que las definiciones del §0 dan a la letra de la cláusula | tabla del §2.4 |
| **base literal** | porcentaje y veces; los límites relativos del validador | identifica la magnitud sobre la que se aplica la cuantía, con los calificadores que cambian el monto, sin agregar texto que no es base | «10 % de la responsabilidad patrimonial computable del mes anterior»: sin «del mes anterior» es *parcial*; cortada en la coma o en la palabra 20 antes de terminar: *parcial*; un artículo inicial o una conjunción final de más no cuentan; otra magnitud: *contradicho*; vacía con base en la letra: *omitido*; llena sin base: *espurio*. El inicio de un plazo («dentro de los 10 días de recibida la solicitud») no es base: límite del esquema (L-ESQ-R2 §1.3 (c) habla de umbrales relacionales) |
| **destino de la base** | elementos con `base_destino` | el punto, la sección, el TO o la Definicion donde la norma establece la magnitud de la base | «importe de referencia establecido en el punto 3.7» → `cla::3.7` (caso de control de L-ESQ-R2, `4ef7650:…:303-306`); una Definicion homónima con otro sentido: *contradicho*. Informativo, sin cifra: en los marcados `base_no_resuelta`, si la base nombra un punto que existe |

Una base *parcial* cuenta como incorrecta si con la base guardada se calcula otro monto, y como correcta si no.

**2.4 Comparación: la tabla de sentidos** (L-ESQ-R2 §1.3, puntos 2 y 3; enmiendas 3 y 5; calibración P3).

| la letra de la cláusula | sentido |
|---|---|
| «superen», «exceda», «más de», «mayor(es) a», «superior a» | mínimo estricto |
| «igual o superior», «al menos», «por lo menos», «como mínimo», «un mínimo de», «no inferior a», «no menos de», «… o más» pospuesto | mínimo inclusivo |
| «inferior a», «menos de», «menor(es) a» | máximo estricto |
| «no podrá superar», «sin exceder», «no excedan, al momento de los acuerdos, del», «hasta», «como máximo», «dentro de», «igual o inferior», «máximo de» pegado a la cuantía | máximo inclusivo |
| «igual a», «equivalente a» pegados a la cuantía, sin otro comparativo en la cláusula | igual |
| «pondera», «ponderador», «coeficiente», «factor», sin un comparador pegado a la cuantía | coeficiente |
| sin marcador, también en un plazo (enmienda 3) | no_determinada |

- *Correcta*: el valor del grafo es el de la lectura. *Contradicha*: los dos fijan un sentido y no es el mismo, o el grafo fija uno y la
  letra no. «Mayor que» frente a «mayor o igual que» cuenta: estricto por inclusivo es *contradicha*, porque la distinción cambia la
  respuesta (L-ESQ-R2 §1.3, punto 2). *Omitida*: el grafo dice `no_determinada` y la letra fija un sentido.
- Cada *omitida* lleva una clase: **de implementación**, si la forma de la letra está en la tabla (el código no aplicó la definición), o
  **de la definición**, si no está («entre 30 días y 90 días», límite declarado en `plan:401`; «será de»; «límite de»).
- Más casos límite: «no superarán el 1,25 % de los activos ponderados» es máximo inclusivo y no coeficiente (comparador pegado,
  enmienda 5, punto 2); «sea o no superior» no es una negación (enmienda 5); «hasta el 31 de diciembre» no tiene cuantía.

**2.5 Veredictos del elemento.**
- **Núcleo correcto** (la cifra de la afirmación, §8): pertinente, y correctos el valor, la unidad, la moneda si aplica, la comparación y
  la base literal si la letra tiene base o el campo está lleno. Una comparación *omitida*, de cualquier clase, no es correcta: el grafo
  no dice el sentido.
- **Completo correcto**: el núcleo, más el tipo de días si aplica y el destino si está guardado.
- **Núcleo contra la definición** (diagnóstico, para el §10): igual al núcleo, pero la comparación *omitida de la definición* cuenta como
  correcta. La diferencia entre las dos cifras es lo que el esquema no expresa, no un error del código.
- **Elementos vacíos.** Un elemento sin valor, sin base y con la comparación `no_determinada` no afirma ningún monto: no tiene campos que
  puedan estar bien o mal. En el grafo sin cola de la tanda 0 son 305 de 1.306, todos del validador (`vacios_y_resueltas_salida_UMEDUMBRALES.txt`).
  Quedan fuera del núcleo y del completo, que se calculan sobre los elementos con contenido, y se leen aparte con una sola pregunta, en
  tres clases: *oculta un umbral* (la letra fija una cuantía, un sentido o una base que el elemento no guarda: campos omitidos), *límite
  sin cuantía en la letra* (la norma nombra un límite y no lo cuantifica, por ejemplo porque lo delega) o *no es un umbral*. Contarlos
  como correctos inflaría la cifra; contarlos como errores de monto mezclaría dos preguntas.

## 3. Grafos y población

- **Etapa P (piloto, §9):** el grafo sin cola de la tanda 0 vigente al sortear. Hoy, KG-Tanda0-Diez-r2b-sincola (`e22fae1a…`, sello
  `dde9f44`/`235a295`; 1.306 elementos en 1.123 nodos). Si se re-sella antes de sortear, el sello nuevo, con su sha en el acta (la misma
  regla del §2 del pre-registro, `:50-52`).
- **Etapa T (medición):** el grafo evaluado, sin la cola humana (`docs/protocolo_dos_grafos.md:46-57`), con su sha en el acta.
  **Documentos (decisión D2):** los elementos de los TOs del grafo evaluado que no están en
  `data/experiment/esq/documentos_excluidos_evaluacion_final.json` (n = 15: los diez de ESQ-2 y los cinco nuevos de la tanda 0; los
  cinco de desarrollo no son documentos del escalado). Es la misma disjunción del conjunto de B6.3 (a) y de la cobertura de la etapa T
  (`4afbe51:…:220-221`; checklist Q10, `:207`), y separa a la medición de todo documento que vio el piloto.
- **Elementos de `origen` = `campo_v3`:** en r2b no hay (`conteo_umbrales_VERIF_rerun_a9631a64_UMEDUMBRALES.txt`: 1.239 e1 y 134 descripción). Si aparecen, van a
  los estratos de descripción (las dos son fuentes distintas del tramo de E1), declarado.

## 4. Estratos y tamaño

**4.1 Estratos** (definidos por los campos guardados, en código; `estratos_umbrales_UMEDUMBRALES.py`). Autor: el validador si `regla_comparacion`
empieza con «limite_relativo:» (`validador_r2.py:440`), el ensamblado si no. Origen: `e1` o descripción. Base: con o sin. En el
validador, los vacíos (§2.5) son un estrato propio.

| estrato | definición | tamaño en el grafo sin cola de la tanda 0 |
|---|---|---|
| E-e1-sin | ensamblado, origen e1, sin base | 652 |
| E-e1-con | ensamblado, origen e1, con base sin resolver | 76 |
| E-desc-sin | ensamblado, origen descripción, sin base | 88 |
| E-desc-con | ensamblado, origen descripción, con base sin resolver | 18 |
| V-sin-cont | validador, sin base, con la comparación determinada | 7 |
| V-con | validador, con base (el validador no resuelve) | 150 |
| base resuelta (censal) | ensamblado con `base_destino` (8 de origen e1 y 2 de descripción) | 10 |
| **elementos con contenido** | | **1.001** |
| V-vacío (aparte) | validador, sin valor, sin base y `no_determinada` | 305 |
| **total** | | **1.306** |

**4.2 Tamaño de la etapa T (decisión D4).** Objetivo de precisión declarado: la mitad del ancho del intervalo al 95 % del núcleo
ponderado, a lo sumo 0,05, con 0,85 como valor de planificación (el mismo del pre-registro, `:86`). Cálculo (`tamano_muestra_UMEDUMBRALES.py`):
- muestreo simple: n₀ = z² · p (1 − p) / d² = 1,959964² · 0,85 · 0,15 / 0,05² = 196;
- la asignación con mínimo por estrato pierde eficiencia: con los pesos de la tanda 0, el efecto de diseño de 240 con mínimo 25 es 1,21
  sin corrección por población finita, y la mitad del ancho da 0,0498 (con 0,80, 0,0557);
- **propuesta: 240 elementos con contenido** en los seis estratos de muestreo, un mínimo de 25 por estrato (censo si N_h ≤ 25) y el resto
  proporcional a N_h; con los tamaños de la tanda 0 serían 103 / 34 / 35 / 18 / 7 / 43; **más el censo de las bases resueltas**, hasta
  40 (si son más, 40 al azar); **más 30 vacíos** al azar, que dan su propia cifra (§7.2) y no entran al núcleo;
- **regla de ajuste, fijada ahora:** al sellar el grafo evaluado se recuentan los N_h, se recalcula la asignación y la mitad del ancho
  con 0,85 y corrección por población finita, y se escriben en el acta antes de abrir una ficha; si pasa de 0,05, se agregan elementos
  con la misma regla hasta bajar de 0,05, con un tope de 300.

**4.3 Sorteo.** Semillas fijadas en la firma (decisión D7), una para P y otra para T. Lista de la población, hora y sha256 de la muestra
sellados antes de abrir una ficha, con el patrón de `data/experiment/lectura_aceptadas/l0_sellos.py` (el del §3.2 del pre-registro). El
orden de lectura es al azar dentro de la muestra, sin el estrato a la vista.

## 5. Ficha y lectura en dos pasos

**5.1 Ficha.** El texto de la unidad de E0 (propio y heredado) con la cuantía resaltada (en los elementos del validador, el tramo de E1);
el tramo que devolvió E1 para ese nodo (de la salida guardada de E1, no del `kg.json`); el tipo y la etiqueta del nodo y su descripción,
marcada como salida del extractor; la ruta del PDF y la página. Si la cuantía no se encuentra en el texto (`tramo_verificado` = no), la
ficha lo dice y muestra el tramo guardado.

**5.2 Paso 1, sin los campos del grafo.** El lector escribe, desde la norma: pertinencia, valor y unidad normalizados, moneda, tipo de
días, el sentido de la comparación con las palabras que lo marcan, la base (el tramo exacto, o «sin base») y, si la base nombra un punto
o un término definido, cuál.

**5.3 Paso 2, el código compara.** Igualdad exacta para valor (como `Decimal`), unidad, moneda, tipo de días y comparación; para la base,
igualdad después de plegar (minúsculas, sin tildes, sin artículo inicial ni conjunción final); para el destino, igualdad de id. Solo
las diferencias vuelven al lector, ahora con el valor del grafo a la vista, que las clasifica con el §2.3 y, en la comparación, con las
clases del §2.4. Si el lector corrige su propio paso 1, se registra con su motivo y se cuenta (como el error del gold del §5.8 del
pre-registro).

**5.4 Regla de calificación sellada.** Al cerrar el piloto, la regla (este §2 con los casos resueltos del piloto, cada uno con su id y su
motivo) y el armador de fichas se sellan por sha256 antes del sorteo de T. Durante T no cambian: un caso que no encaja se marca «no
previsto», con su motivo, y queda no decidible.

## 6. Quién lee (decisión D3)

- **Opción A (recomendada): la autora lee los 240, los 30 vacíos y el censo, con la regla sellada y los dos pasos del §5.** USD 0 de API. Es la lectura
  humana con regla fija; no hay juez que calibrar.
- **Opción B: un juez por la API**, `claude-sonnet-4-6` a temperatura 0, con la maquinaria de los §4.1 a 4.7 del pre-registro (captura
  íntegra y caché, prompt sellado por sha256, N = 3 con un namespace por repetición, veredicto modal, salida «requiere adjudicación
  humana», candado de ajuste). El juez hace el paso 1 y el código compara. **Calibración, solo con la tanda 0:** casos resueltos de un
  pool de 20 elementos etiquetados por la autora; validación sobre 100 elementos más, que la autora lee a ciegas, disjuntos del piloto y
  del pool. **Pasa** si el veredicto del núcleo coincide en al menos 90 de 100 (Wilson 0,8256), si la exactitud del núcleo según el juez y
  según la autora difieren en 0,03 o menos, y si de los núcleos incorrectos según la autora el juez marca al menos dos tercios
  (fracción cruda). **Cuándo se deja de ajustar:** una sola recalibración, declarada, con casos nuevos del pool y nunca con las 100 de
  validación; si después no pasa, el juez no escala y T se lee con la opción A. En T, el juez lee 400 elementos con contenido y los 30 vacíos, y la autora controla 30 a ciegas;
  con menos de 27 de 30 de acuerdo (Wilson 0,7438), la cifra del juez queda no validada y T se lee con la opción A.
- **Opción C, descartada:** la lectura doble de dos sesiones de Claude Code con adjudicación de la autora. Sería un juez de modelo sin la
  captura, la caché y el prompt sellado que el principio 8 exige a los jueces de las evaluaciones nuevas (`plan:272-279`).
- Quién lee y adjudica en B6.3 es un punto a acordar con los mentores (checklist Q12, `:209`): esta enmienda lo declara (§15).

## 7. Estimadores e informe

**7.1 Las dos cifras de siempre** (las del §3.6 del pre-registro, `:85-95`): la **cruda**, con Wilson al 95 % (z = 1,959964,
`reext_t0/t4/tasas_t4.py:244-249`), y la **ponderada por el tamaño de cada estrato**, p̂_w = Σ_h W_h · p̂_h con W_h = N_h / N (N, los elementos con contenido de la población), varianza
Σ_h W_h² · p̂_h (1 − p̂_h) / n_h · (1 − n_h / N_h) e intervalo de Wald; el estrato censal aporta varianza 0. Los estratos con n_h < 5 se
reportan con su fracción cruda «n de N» y se agrupan para la varianza (declarado).

**7.2 Qué se informa.**
- El **núcleo** y el **completo**, cruda y ponderada; el **núcleo contra la definición**, al lado.
- **Por campo:** la exactitud sobre los elementos donde el campo aplica, cruda con Wilson y ponderada como estimador de razón (correctos
  sobre aplicables, con la varianza linealizada), con el n de aplicación. Para la comparación, también la distribución
  correcta / contradicha / omitida (de implementación y de la definición).
- **Por estrato:** fracción cruda «n de N» si n_h < 20, Wilson si no.
- **Vacíos:** su número en la población, por censo (es un dato del grafo, no de la muestra), y las tres clases del §2.5 sobre los 30
  leídos, con Wilson.
- **Covariables, en fracción cruda:** tipo de nodo, unidad, familia de `regla_comparacion`, TO, tanda, `tramo_verificado`.
- **Inventario de clases de error** (§10.1), con su conteo.
- **No decidibles**, con las dos cotas (todas correctas y todas incorrectas); **pertinencia**: no pertinentes, inexistentes y duplicados.
- **Tiempo por ficha** medido en el piloto y en T.

## 8. La afirmación en la tesis (decisión D5)

- **Para escribir que el grafo guarda correctamente hasta qué monto, porcentaje o plazo se aplica una norma** hace falta que el límite
  inferior del intervalo al 95 % del **núcleo** sea al menos **0,90** en las dos cifras (cruda con Wilson y ponderada con Wald), y que el
  de la **comparación**, sobre todos los elementos con contenido, también lo sea. La frase dice «en los TOs del conjunto de test del grafo evaluado».
- **Entre 0,80 y 0,90:** se escribe la cifra con su intervalo y la frase «la mayoría de los umbrales tiene sus campos correctos; X de
  cada 100 tienen un error que cambia la respuesta», con el tramo literal como respaldo. **Debajo de 0,80:** límite declarado, sin
  afirmación. Si un estrato queda 0,10 o más por debajo del umbral en su estimación puntual, la frase lo nombra.
- **Qué se puede esperar con 240** (efecto de diseño 1,21, n efectivo cerca de 198; `tamano_muestra_salida_UMEDUMBRALES.txt`, §4, fila de 200): la
  afirmación con 0,90 sale con probabilidad 0,70 si la exactitud real del núcleo es 0,95, 0,98 si es 0,97 y 0,25 si es 0,93.
- **Lo que la cifra no dice:** que el agente responda bien. Un umbral bien guardado no garantiza la respuesta (grounded ≠ correct). La
  respuesta la mide B6.3 (b); recomiendo que su pre-registro informe aparte la fidelidad en las preguntas cuyo gold depende de un umbral
  (fuera de esta enmienda; se decide al sellar B6.3).

## 9. Etapa P: el piloto

**9.1 Para qué.** Fijar la regla de calificación (§5.4) y la ficha, y encontrar errores sistemáticos de las reglas (§10). No da ninguna
cifra del capítulo 5; si sus conteos aparecen en la tesis, es en el capítulo 4, como validación de diseño de la tanda 0, en fracción
cruda (como toda cifra de la tanda 0, `plan:751`).

**9.2 Muestra.** 40 elementos del grafo del §3: 4 de cada uno de los ocho estratos del §4.1 (los seis de muestreo, el de base resuelta y
el de vacíos; 32) y 8 más de los cinco TOs nuevos (143 de los 1.306 elementos; el resto es de los cinco de desarrollo).

**9.2 bis Lo primero que mira el piloto.** La comparación `no_determinada`: además de los 305 elementos vacíos del grafo sin cola
(del validador, sin valor, sin base y con la comparación `no_determinada`), afecta a 331 de los 1.001 elementos con contenido (en el
grafo completo, `a9631a64`: 314 vacíos y 338 de los 1.059 con contenido; `vacios_y_resueltas_UMEDUMBRALES.py` y recuento de la mesa del
08/10/2026). El piloto empieza por ahí: si es una regla del código que no determina la comparación cuando el texto la trae, es una clase
de error del §10.

**9.2 ter Cuándo.** Lo antes posible después de la firma, para que los errores de código que encuentre se corrijan antes de sellar el
grafo evaluado (§10, grupo 2). La medición final (T) va sobre el grafo escalado, sellado.

**9.3 Procedimiento.** Lote 1 de 20 → FRENO para ajustar la regla y la ficha, con la lista de clases de error que aparecieron → lote 2 de
20 con la regla fija. Si el lote 2 obliga a cambiar algo que el juicio usa, se re-leen los dos lotes y, como máximo, se agrega un lote 3
de 20. Después, la regla se sella. La autora lee el piloto en las opciones A y B.

**9.4 Por qué no contamina la medición.**
1. **Documentos disjuntos.** El piloto lee la tanda 0; la medición excluye los quince de `documentos_excluidos_evaluacion_final.json`, y
   los cinco de desarrollo no están en el escalado (§3). Ningún elemento ni ninguna norma del piloto entra a T.
2. **Orden.** Regla sellada → correcciones (§10) → grafo evaluado sellado → sorteo de T → lectura. Nada de T llega al código ni a la
   regla: después del sorteo no cambian (principio 9, `plan:281-288`).
3. **Lo que T mide es justamente lo que el piloto no puede mostrar:** si la regla y las correcciones generalizan a TOs que nadie leyó.
4. **Lo que queda:** una regla escrita sobre la tanda 0 puede no prever formas de otros TOs. Por eso existen el «no previsto» y las cotas
   de los no decidibles, y la regla no se ajusta durante T.

## 10. Errores sistemáticos: corrección de código antes de sellar el grafo evaluado

**10.1 Qué es una clase.** Un error que se repite por una misma forma de la letra y una misma regla del código (el mismo campo, la misma
familia de `regla_comparacion` o el mismo patrón de detección): dos o más casos en el piloto, o uno cuyo mecanismo se ve en el código y
cuyo censo determinístico sobre la tanda 0 encuentra más.

**10.2 Qué se corrige y qué no.**
- **De implementación** (el código no hace lo que dice la definición): corrección de código.
- **De la definición** (la letra tiene una forma que la definición no cubre): solo después de una enmienda firmada a L-ESQ-R2, como las
  enmiendas 3 y 5.
- **De E1 o de E0** (el tramo o la descripción del modelo están mal, o el texto de E0): no se corrigen por esta vía, porque exigirían
  re-extraer; van al backlog con su `capa_pipeline` y quedan como límite declarado. Lo mismo un cambio de política, por ejemplo dejar
  afuera los elementos de la descripción que no verifican (L-ESQ-R2 §1.3 (b): lo que no verifica se marca, sin corregirlo).

**10.3 Cómo, por clase** (principio 12, `plan:303`: en código y re-aplicable sobre lo guardado, USD 0; grupo 2 del barrido de límites,
`plan:778`):
1. ficha de la clase: los casos del piloto, el censo determinístico de candidatos en la tanda 0 y su clase (§10.2), con la decisión de la
   autora;
2. **un test de regresión por clase**, en el selftest del módulo que toca (`data/experiment/pyd_r2/code/selftest_pyd_r2.py`, 398 de 398
   en `data/experiment/prompt_r2/freno_p5.md:247`; para `resolver_base`, que no tiene prueba de la remisión según VERIF-UMBRALES §4, una prueba nueva
   junto a las del ensamblado): el tramo real del piloto, con su id, y al menos una variante sintética de la misma forma;
3. control negativo: los tests nuevos fallan con el código anterior a la corrección y pasan con el nuevo, y el resto de la suite sigue
   pasando (el control de A1 de U-ALCANCE-E1, `ab59034`);
4. re-ensamblado sobre la salida guardada de E1 de las tandas ya corridas y censo de los elementos que cambian; la mesa lee con la regla
   sellada todos los que cambian si son 30 o menos, y 30 sorteados si son más, para confirmar que la clase se corrige sin errores nuevos;
5. entra a la release previa al sello del grafo evaluado, con su gate de release (`docs/protocolo_dos_grafos.md:65-67`).

**10.4 Por qué no contamina la medición.** Las correcciones salen de la tanda 0, son reglas generales que se aplican a todo el corpus y
se prueban con casos de la tanda 0; la medición se hace sobre otra muestra, de otros documentos, en el grafo sellado después. Si una
corrección generaliza o no a TOs nuevos es lo que la medición mide. Los elementos que motivaron una corrección quedan fuera de toda
cifra: son casos de test, no evidencia de mejora. El capítulo 4 cuenta las clases y sus tests; el capítulo 5, la cifra del grafo
sellado; nunca en la misma tabla. Si una vigilancia de una tanda del escalado (sobre TOs que sí pueden entrar a T) motiva una
corrección de umbrales, se registra con ese origen y T reporta esos TOs como covariable.

## 11. Relación con la vía de precisión: qué se comparte

- **Se comparte:** el armador de fichas (texto propio y heredado, PDF y página: §3.3 del pre-registro), el patrón del sorteo sellado,
  las funciones de Wilson y del estimador ponderado, el acta de sorteo de T (una por vía, con su semilla, del mismo grafo sellado) y,
  si se elige la opción B, la maquinaria del juez y su freno por presupuesto.
- **Ficha común:** cuando un elemento de la muestra de umbrales está en un extremo de una arista que la autora lee en la vía de precisión,
  se lee en una sola sesión, con dos formularios y orden fijo: primero la tripleta, cerrada; después el umbral, con sus dos pasos. El
  solapamiento se declara y no se excluye (la regla del pre-registro, `:41-42`). Es poco probable: en el control de 30 de T se esperan
  entre 0,35 y 2,0 fichas comunes (`solapamiento_tripletas_salida_UMEDUMBRALES.txt`, con una población de umbrales de 1.000 a 5.000, supuesto NO
  VERIFICADO).
- **Lectura adosada en V, opcional (decisión D9):** en la etapa V se esperan unas 24 aristas de 100 con un extremo con umbrales (956 de
  3.983 en `2922b72d`). Si V corre antes de que cierre el grupo 2, la autora puede anotar, después de cerrar cada tripleta, los errores de
  umbral que vea, como observaciones para el inventario de clases del §10, sin cifra.
- **No se comparte:** ninguna etiqueta de una vía entra a la cifra de la otra; el juez de tripletas no ve las etiquetas de umbrales; la
  muestra de umbrales no se saca de las aristas de tripletas (favorecería a los nodos con más aristas y dejaría de representar a los
  elementos).

## 12. Dependencias, calendario, costo y tiempo

- **Depende de:** la firma de esta enmienda; el armador de fichas y el formulario de dos pasos (código, USD 0); para P, el grafo sin
  cola de la tanda 0 vigente; para T, el grafo evaluado sellado y la lista de exclusión. **No depende** de la etapa V ni del juez de
  tripletas en la opción A.
- **Calendario:** P apenas se firme, en paralelo con la preparación de la tanda 1, para que las correcciones del §10 entren al grupo 2
  antes del sello; si P termina antes del re-sellado único de la tanda 0, sus correcciones entran también en él. La regla sellada, el
  tamaño recalculado y el umbral de la afirmación entran al pre-registro de B6.3 como parte de (d), igual que la etapa T de tripletas
  (`4afbe51:…:222`; Q7). T corre después del sello, en paralelo con B6.3.
- **Costo de API:** opción A, USD 0. Opción B, unos USD 13,8 en la mediana y 15,9 en el p90 (1.920 llamadas: pool, validación con hasta
  dos corridas y 400 en T; `costo_juez_umbrales_salida_UMEDUMBRALES.txt`, con las tarifas y la conversión del §8 del pre-registro y supuestos de
  tamaño NO VERIFICADOS); tope propuesto USD 20, aparte de los de V y T.
- **Tiempo de la autora (NO VERIFICADO: el repo no tiene tiempos de lectura medidos; el §8 del pre-registro supone unos 1,3 a 1,8 minutos
  por juicio):** opción A, entre 8 y 13 horas (firma 0,5; piloto 1,5 a 2; clases de error 0,5 a 1; T, 240 a 1,25–1,75 minutos, 5 a 7;
  30 vacíos, 0,5; censo de bases resueltas, 0,3 a 2). Opción B, entre 7 y 10 horas (piloto, clases, pool de 20, validación de 100, control de 30 y
  adjudicaciones). El piloto mide el tiempo real por ficha y re-estima.

## 13. Qué no cambia

Las once decisiones del §10 del pre-registro, las vías de precisión y de cobertura, sus tamaños, estimadores, jueces y topes (USD 35 en
V y USD 55 en T). La medición de umbrales no se suma a ninguna cifra de esas vías.

## 14. Decisiones al firmar, nota al pie y nota al plan

**14.1 Decisiones de la autora** (opciones; recomendación de la mesa en negrita). **Decididas por la autora el 08/10/2026:** D1 (a), esta
enmienda; D2 (a), los TOs del grafo evaluado fuera de los quince; D3 (A), lee la autora; D4, 240; D5, 0,90; D6, 40 elementos en dos
lotes; D7, las semillas, generadas por el procedimiento declarado abajo y selladas en el commit de la firma; D8, dato informativo, con su
cifra aparte en el reporte, porque importa para el agente; D9, opcional, sin cifra; D10, en el grupo 2.
- **D1. Vehículo:** **(a) esta enmienda**; (b) un pre-registro aparte, con el mismo contenido.
- **D2. Documentos de T:** **(a) los TOs del grafo evaluado fuera de los quince**; (b) todo el grafo evaluado, sin los elementos del
  piloto (mezcla documentos que informaron el esquema y el piloto con los de test).
- **D3. Quién lee:** **(A) la autora**; (B) juez por la API, calibrado en la tanda 0.
- **D4. Tamaño de T:** 180 (mitad del ancho cerca de 0,063); **240 (cerca de 0,050)**; 400, solo con la opción B (cerca de 0,036); los
  tres, con 0,85 y sin corrección por población finita (`tamano_muestra_salida_UMEDUMBRALES.txt`, §5), más los 30 vacíos y el censo.
- **D5. Umbral de la afirmación:** 0,85; **0,90**; 0,95 (con 240, la probabilidad de afirmarlo es 0,43 aun con una exactitud real de 0,98).
- **D6. Piloto:** **40 elementos en dos lotes, sobre el grafo sin cola de la tanda 0 vigente**; 60 elementos.
- **D7. Semillas de P y de T:** generadas por un procedimiento declarado y selladas en el commit de la firma. Procedimiento: para cada
  etapa X (P o T), `semilla_X` = los primeros 16 caracteres hexadecimales de sha256(«U-MED-UMBRALES|X|» + sha256 del texto firmado de
  esta enmienda, es decir, de sus líneas anteriores a «## Firma»); el sorteo por estrato es `random.Random(f"{semilla_X}:{estrato}").sample(sorted(ids), n)`,
  como en U-LECTURA-ACEPTADAS. Las dos semillas se calculan al firmar y se asientan en la sección «Firma», en el mismo commit.
- **D8. Tipo de días fijado por una regla general del TO:** **no se exige al campo; dato informativo**; se exige. Decidido: informativo,
  con su cifra aparte en el reporte, porque importa para el agente.
- **D9. Lectura adosada en V:** **opcional, sin cifra**; no.
- **D10. Corrección de clases (§10):** **como se propone, en el grupo 2**; sin correcciones antes del sello (los errores quedan para el
  grafo corregido).

**14.2 Tope de la etapa P:** USD 0 en las dos opciones (el piloto lo lee la autora).

**14.3 Nota al pie del pre-registro (texto propuesto, PENDIENTE de la firma):** «<fecha> — Enmienda 1 (vía de umbrales: exactitud de los
campos de los umbrales), FIRMADA en <commit PENDIENTE>: `docs/enmienda1_preregistro_evaluacion_tripletas_2026-10-08_umbrales.md`. El
texto firmado no cambia.»

**14.4 Nota al plan** (la mesa la asentó con la versión para firmar, el 08/10/2026, y la completa después de la firma): en `plan:778`, grupo 2, «las correcciones de clase de los
umbrales (U-MED-UMBRALES, etapa P, §10)»; y en B6.3 (d), la vía de umbrales.

## 15. Para la lista de los mentores

- B6.3 (d) agrega una cifra: la exactitud de los campos de los umbrales. Es una medición más, no un desvío de lo acordado.
- Quién lee (Q12): la autora con regla fija (opción A) o un juez calibrado con control de la autora (opción B).
- La afirmación de la tesis sobre los umbrales queda condicionada a un umbral pre-registrado (§8).

## Comandos de los recuentos (regla i)

```
PYTHONDONTWRITEBYTECODE=1 python3 -B estratos_umbrales_UMEDUMBRALES.py kg_t0_diez_r2b_a9631a64.json kg_t0_diez_r2b_sincola_e22fae1a.json kg_t0_desarrollo_r2b_sincola_2922b72d.json
PYTHONDONTWRITEBYTECODE=1 python3 -B vacios_y_resueltas_UMEDUMBRALES.py kg_t0_diez_r2b_a9631a64.json kg_t0_diez_r2b_sincola_e22fae1a.json
PYTHONDONTWRITEBYTECODE=1 python3 -B conteo_umbrales_VERIF_copia_UMEDUMBRALES.py kg_t0_diez_r2b_a9631a64.json
PYTHONDONTWRITEBYTECODE=1 python3 -B tamano_muestra_UMEDUMBRALES.py
PYTHONDONTWRITEBYTECODE=1 python3 -B costo_juez_umbrales_UMEDUMBRALES.py
PYTHONDONTWRITEBYTECODE=1 python3 -B solapamiento_tripletas_UMEDUMBRALES.py
```

`conteo_umbrales_VERIF_copia_UMEDUMBRALES.py` es el `conteo_umbrales.py` del paquete de VERIF-UMBRALES (sha256 `010a3643…`); su salida sobre `a9631a64` es
idéntica a la de ese paquete (`diff` vacío).

Los tres `kg.json` salen de `git show HEAD:data/experiment/reextraccion_v2/corpus_tanda0/<ens>/r2/kg.json` (sha256 verificados contra
`data/experiment/neo4j/grafos.py:138`, `:158` y `:172`). Los scripts y sus salidas están en `data/experiment/med_umbrales/` (`scripts/` y `salidas/`), con
la propuesta y el FRENO de la unidad; entraron al repo con esta versión para firmar.

## Firma

FIRMADA por la autora el 08/10/2026 (versión para firmar en `97bc53d`), con las decisiones D1 a D10 del §14.1. Rige desde esta firma.

**Semillas (D7), selladas con el commit de la firma.** Texto firmado: las líneas de este archivo anteriores a «## Firma», con sha256
`c77e92adface7f9fe7286c1019971fdedafc7af6afbafb7b185f87c38bf77e01`.

| etapa | semilla |
|---|---|
| P (piloto, §9) | `51fbea50388e7481` |
| T (medición final, §4.3) | `acda9e847a4d64d0` |

Se reproducen sobre el archivo del commit de la firma (la segunda y la tercera línea toman el sha256 de la primera):

```
git show <commit de la firma>:docs/enmienda1_preregistro_evaluacion_tripletas_2026-10-08_umbrales.md | sed '/^## Firma$/,$d' | shasum -a 256
printf 'U-MED-UMBRALES|P|%s' <sha256 del texto firmado> | shasum -a 256 | cut -c1-16
printf 'U-MED-UMBRALES|T|%s' <sha256 del texto firmado> | shasum -a 256 | cut -c1-16
```

El sorteo de cada etapa, por estrato: `random.Random(f"{semilla_X}:{estrato}").sample(sorted(ids), n)` (§4.3 y D7). Ninguna muestra
se sortea antes de este commit. La nota del §14.3 al pie del pre-registro entra con esta firma.

## Notas al pie

- **08/10/2026 (noche) — FRENO P-a revisado por la mesa sobre una copia, y decisiones de la autora.** `data/experiment/med_umbrales/p/`,
  sin commit al escribir esta nota.
  - **Lo que se reproduce:**
    - el sorteo, con código propio de la mesa sobre una copia de `e22fae1a`: la misma muestra por estrato, los mismos lotes y el
      mismo orden que el acta (`acta_sorteo_P.json`, `435fc76f…`, sellada a las 17:29:41);
    - el orden de las horas, en la sesión que corrió P-a: acta 17:29:41, diagnóstico 17:35:06, primera ficha 17:38:38;
    - las 47 salidas comparables de P-a (diagnóstico, 20 fichas, 22 páginas, formulario y regla v0), byte a byte, sobre un espejo
      armado por la mesa con los mismos 67 insumos. El acta difiere solo en la hora y en el sha256 de los insumos, porque el espejo
      de la mesa trae 7 archivos de código más;
    - el selftest del comparador, 23 de 23;
    - la regla v0, igual al §2 firmado (líneas 47 a 104 de `a0f9815`);
    - las fichas, que no muestran ningún campo del umbral.
  - **Precisiones del diagnóstico:**
    - la tabla de formas de la familia (ii) suma 142 sobre 120 elementos, porque un elemento puede tener más de una forma; el FRENO no
      lo declara;
    - un elemento del lote 2 comparte nodo con otro que el listado del diagnóstico muestra entero. Por eso la autora no abre el listado
      por elemento antes de cerrar el paso 1 del lote 2.
  - **Decisiones de la autora (08/10/2026):** acepta las familias (i) (132) y (ii) (120) como candidatas a clase, para confirmar con
    su lectura. La decisión de si la regla de comparación lee la oración de E0, y no el tramo de E1 o la descripción (108 de los 132
    de la familia (i)), la toma cuando la lectura confirme la (i).
- **09/10/2026 — El tramo guardado (§1 (c), `:43`).** Por decisión de la autora del 09/10/2026, guardar solo la cuantía fue una decisión
  de implementación, no del esquema. L-ESQ-R2 §1.3 (a) y (b) dice que cada elemento lleva «el tramo literal» y que «E1 copia el tramo
  literal» (`4ef7650`).
  - **Qué cambia:** el ensamblado guardará en `tramo` el tramo de E1 del que sale la cuantía (ítem L de U-OMISIONES-COD v7), dentro del
    re-sellado único y antes del sello del grafo evaluado.
  - **Cómo se lee el §1 (c):** donde dice «el tramo guardado, que en los elementos del ensamblado es solo la cuantía, por diseño»,
    léase «solo la cuantía hasta el re-sellado único; desde entonces, el tramo de E1».
  - **Qué no cambia:** la vía sigue sin medir el tramo. Ningún campo que compara el paso 2 (§5.3) cambia, ni los estratos (§4.1).
  - **Las herramientas del piloto:** las que toman `tramo` como la cuantía (`p/code/comun_P.py:343` y `:386`;
    `p/code/armador_fichas_P.py:75`) se adaptan antes del sello de la regla y el armador (§5.4). Las 20 fichas del lote 1 no cambian.
  - El texto firmado no cambia.
- **10/10/2026 — Lote 1 del piloto, paso 1 (§5.2), sellado por la autora.** Se registra solo el sello, sin el contenido.
  - **Formulario:** `formulario_paso1_lote1_v2.md`, fuera del repo, en `fuera_del_repo/lectura_lote1/`, de solo lectura.
  - **sha256:** `58a56fb5386a334a28d9b911e90b4fb44c003f75b581311d0a4017244ba21f92`.
  - **Hora del sello:** 09/10/2026 17:57:54 (−03).
  - **Se reproduce con:** `shasum -a 256 "$HOME/INGENIERIA IA/TESIS/fuera_del_repo/lectura_lote1/formulario_paso1_lote1_v2.md"`. La mesa lo
    recomputó el 10/10/2026 y da lo mismo.
  - **Sigue el paso 2 del lote 1 (§5.3):** el comparador (`p/code/comparador_paso2_P.py`) compara el formulario con los campos del grafo,
    y solo las diferencias vuelven a la lectora, con el valor del grafo a la vista. Después, el FRENO del lote 1, que ajusta la regla y la
    ficha con la lista de clases de error, y recién entonces el lote 2 (§9.3).
  - El acta del sorteo y el diagnóstico por elemento siguen vedados hasta cerrar el paso 1 del lote 2.
  - El texto firmado no cambia.
- **10/10/2026 — Lote 1 del piloto: paso 2 (§5.3) sellado por la autora, y FRENO del lote 1.** Se registran los sellos, sin el
  contenido.
  - **Lecturas provisionales de la v0,** fijadas antes de abrir las diferencias: `lecturas_provisionales_v0_paso2_lote1.md`, sha256
    `e389b9119f2b2972aa2c337d4c5867416e8ee69d50d590816c98ecdfba98c6dd`, sellada el 10/10/2026 a las 12:00:02 (−03). El paso 2 aplicó la
    regla v0 con esas lecturas, que son la propuesta de la autora para la v1.
  - **Paso 2:** `diferencias_paso2_lote1_autora.md` (sha256 `dc5ea3edd9ebd5402f000148e34344ba3036e79d77693e79fb45251a48064e20`) y
    `notas_paso2_lote1.md` (sha256 `d3f2b4c8cd00af7dc0d7f8ff6a45c37d9e5e0dd390a30304a77bae2a3124fcec`), sellados el 10/10/2026 a las
    14:00:10 (−03).
  - Los tres están fuera del repo, en `fuera_del_repo/lectura_lote1_paso2/`, de solo lectura, y se reproducen con `shasum -a 256`.
  - **FRENO del lote 1:** `data/experiment/med_umbrales/p/lote1/freno/FRENO_lote1.md`, con las cifras de validación de diseño (§9.1),
    la lista de clases de error y lo que decide la autora. Sigue la v1 de la regla, sellada antes del lote 2 (§9.3).
  - El acta del sorteo y el diagnóstico por elemento siguen vedados para la autora hasta cerrar el paso 1 del lote 2.
  - El texto firmado no cambia.
- **10/10/2026 — La regla v1 del piloto, sellada, y los cambios que hace al §5.** Por decisión de la autora del 10/10/2026, que autorizó
  esta nota.
  - **La v1:** `data/experiment/med_umbrales/p/regla_calificacion_v1.md`, sha256
    `70b8dcce5ad0f75eb0befffb3724d278679abd7780b03b352bb46a64fb7dc893`. La mesa la selló tal cual el 10/10/2026 a las 14:32:01 (−03),
    antes del paso 1 del lote 2 (`p/sello_regla_calificacion_v1.txt`).
    - Es la v0 (`p/regla_calificacion_v0.md`, que reproduce el §2) con los cambios C1 a C30, listados al pie de la v1.
    - Rige desde el lote 2 (§9.3). La v0 no se edita, y la regla del §5.4 se sigue sellando al cerrar el piloto.
  - **Por qué entra por nota:** el piloto fija la regla y la ficha (§9.1 y §9.3), pero los cambios C7 y C23 a C27 de la v1 tocan el
    procedimiento del §5, que fija el texto firmado. Desde el lote 2 rige lo que sigue:
    - **§5.1, la ficha:**
      - no muestra ningún campo del grafo: ni el tramo de E1, ni el tipo, ni la etiqueta, ni la descripción del nodo, ni el id del
        elemento (C23);
      - resalta solo la cuantía, ubicada con el tramo del elemento, sin mostrar la extensión del tramo (C24);
      - lleva un id opaco derivado de una semilla, con el mapa sellado aparte y reproducible (C25).
    - **§5.2, el paso 1:** califica los campos de la cuantía resaltada, sin la pertinencia (C7 y C23).
    - **§5.3, el paso 2:**
      - empieza por la pertinencia (C7), que se decide viendo solo la etiqueta, el tramo y los otros elementos del nodo, antes de ver
        los valores del grafo para los demás campos;
      - después, el código compara y devuelve las diferencias, como dice el §5.3.
    - **Los formularios** de los dos pasos llevan una nota por fila (C26).
    - **Dos elementos de la misma unidad de E0** (C27): si el sorteo los da, no se vuelve a sortear. La segunda ficha se declara y se
      lee sabiendo que la primera la informa.
  - **La ficha del paso 1 cuando no hay cuantía que ubicar con el tramo** (decisión de la autora del 10/10/2026). Son dos casos que el
    §5.1 cubre y la v1 no trata:
    - en los elementos del validador, la ficha resalta el tramo de E1 del elemento, como dice el §5.1. Es una excepción declarada a C24;
    - si el elemento no se ubica en el texto o su tramo no está verificado, la ficha lo dice y muestra solo la cuantía guardada, sin
      tramos.
  - **Qué no cambia:**
    - las igualdades del §5.3, el plegado de la base y el id del destino;
    - el registro de las correcciones del paso 1;
    - el sello del §5.4 antes del sorteo de T.
  - El texto firmado no cambia.

- **15/10/2026 — el re-sellado único de los grafos r2b de la tanda 0.** Los grafos sellados que cita este documento tienen una versión posterior, del re-sellado único (`docs/mandatos/URESELLADO_T0_resellado_unico_grafos_r2b.md`, firmado; FRENO en `data/experiment/resellado_t0/FRENO_resellado_T0.md`): `a9631a64…` (KG-Tanda0-Diez-r2b) → `fda6c07d…` (KG-Tanda0-Diez-r2b-rs1, 8.788 nodos y 27.430 aristas); `e22fae1a…` (KG-Tanda0-Diez-r2b-sincola) → `61dd1b69…` (KG-Tanda0-Diez-r2b-sincola-rs1, 8.491 nodos y 25.976 aristas); `2922b72d…` (KG-Tanda0-Desarrollo-r2b-sincola) → `66e745f5…` (KG-Tanda0-Desarrollo-r2b-sincola-rs1, 6.711 nodos y 21.996 aristas). Cambian por el código de U-OMISIONES-COD (`ded41d50`) y por las salidas de R0 (`1d690df3` y `2d0f5277`); los de diez, además, por R2-3 (`803623a`), que los sellados no tenían. El diff por campo y por causa está en `data/experiment/resellado_t0/salidas/`. Los sellados siguen sellados (principio 9); el commit del sello de los nuevos queda en `commit_sellado` de `data/experiment/neo4j/grafos.py`. El sorteo de la etapa V, que espera este re-sellado, queda habilitado por `66e745f5…` (KG-Tanda0-Desarrollo-r2b-sincola-rs1), la versión posterior de `2922b72d…`, una vez sellado; no se corrió. El texto firmado no cambia.
