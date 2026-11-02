# Pre-registro de la evaluación por tripletas (B4)

**FIRMADO por la autora el 07/10/2026** (versión para firmar commiteada en `865a5b2`, con las once decisiones del §10 y sus siete ajustes;
firma por mensaje de la autora, que ratifica los topes de USD 35 para la etapa V y USD 55 para la etapa T; borrador del mismo día en `93bebd2`).
Desde esta firma es el pre-registro de B4 y el laudo D-b (`plan:961`: alcance, escala de importancia, regla de presencia y umbral de acuerdo
del juez). No sellado como medición: ningún número de este documento es un resultado. El texto firmado no se edita después: recibe
notas fechadas al pie.

## 0. De dónde sale

- Decisiones D9 a D12 de las reuniones del 18 y el 19/08/2026 (acta confirmada por la autora el 07/10/2026,
  `docs/registro_reunion_mentores_2026-08-18_19.md`).
- Bloque B4 del plan (`plan:412-459`), con los dos requisitos de B4.1: intervalos de Wilson en toda proporción
  (exigencia 4) y precisión desagregada por etapa E0–E5, además de por predicado y por TO (exigencia 5) (`plan:416-423`).
- Laudo D-f, FIRMADO el 27/08/2026 (`966253e:docs/laudo_D-f_secuencia_tripletas.md`, sha256 `85f48f14…`): el instrumento se
  valida en desarrollo y la medición que cuenta se corre una sola vez sobre el grafo escalado, dentro de B6.3 (`:8-18`). Este
  pre-registro declara el **doble rol** que pide su §5 (`:47-49`): **etapa V** (validación del instrumento, desarrollo) y
  **etapa T** (medición única sobre el grafo evaluado, componente (d) de B6.3, `plan:773`). La nota del 07/10/2026 al pie del laudo
  D-f asienta que el grafo de la etapa V es el de desarrollo r2b sin cola y no r1 (decisión 1 del §10).
- Metodología de calibración de jueces del proyecto (la del juez de fidelidad de EV2, `evaluacion/02_calibracion_juez.md` y
  `ev2_juez/calibracion/registro_calibracion.md`): el LLM clasifica, el código computa el veredicto; calibradores como casos resueltos;
  N repeticiones que re-muestrean; salida «requiere adjudicación humana»; ningún ajuste del prompt sin decisión de la autora.

## 1. Qué mide, y en qué se diferencia de U-LECTURA-ACEPTADAS

Mide el contenido del grafo a nivel de tripleta: si cada relación que el grafo afirma es correcta según su texto
(precisión), si merece estar (importancia), y qué parte de lo más importante de los textos está en el grafo (cobertura).

| | U-LECTURA-ACEPTADAS (cerrada en `86324cc`) | esta evaluación |
|---|---|---|
| pregunta | tasa de unidades aceptadas con error: línea de base del pipeline y vigilancia por tanda (`9502ca4:docs/mandatos/ULECTURA_ACEPTADAS_tasa_error_tanda0.md:9-18`) | calidad del contenido del recurso: precisión, importancia y cobertura (promesa P-1, `plan:1278`) |
| unidad | la unidad de E0 (el chunk), con error si **al menos un** nodo o relación no se sostiene | la **tripleta** (nodo, relación, nodo) con su evidencia |
| población | 2.366 unidades aceptadas de los diez TOs de la tanda 0, sin la cola | aristas de contenido del grafo de validación (V) y del grafo evaluado (T) |
| lectores | instancia, mesa a ciegas y adjudicación de la autora | gold de la autora y juez LLM calibrado contra ella |
| importancia | no se juzga | se juzga (escala de tres valores) |
| omisiones | aparte, no cuentan | son el objeto de la vía de cobertura |
| resultado | ítems 6 de 30, no ítems 4 de 30, ponderada 0,1616 [0,0689; 0,2543] (`86324cc:…/reporte_l2.md`, §2) | — |

Las dos cifras no se comparan: una cuenta unidades con algún error y la otra relaciones correctas. Se reusan el formato de
ficha (texto propio y heredado, tramo), el sorteo sellado con semilla antes de abrir (patrón `lectura_aceptadas/l0_sellos.py`)
y el Wilson con z = 1,959964 (`reext_t0/t4/tasas_t4.py:244-249`). Si una unidad de la muestra de U-LECTURA-ACEPTADAS aporta
una tripleta a la muestra de V, se declara el solapamiento; no se excluye.

## 2. Grafos

- **Etapa V (decisión 1): KG-Tanda0-Desarrollo-r2b-sincola** (`2922b72d…`; 6.723 nodos y 22.084 aristas; sello `dde9f44`/`235a295`;
  «grafo sin cola de la tanda 0», nombres D13), porque tiene el esquema congelado y la cadena r2b del escalado: la escala de importancia
  y la regla de presencia se validan sobre el vocabulario que después se mide. La letra del laudo D-f decía KG-Reextraído-r1 (`0226e947…`,
  `966253e:…:8-12`), de una generación de esquema anterior; la nota fechada al pie del laudo (07/10/2026) asienta el cambio del objeto de
  la validación, no de la secuencia. Si el grafo sin cola de la tanda 0 se re-sella antes de abrir la muestra (parte A y S19,
  `hoja_de_ruta_tanda1_mesa/borrador_resellado_grafo_evaluado_tanda0_mesa.md`), la etapa V corre sobre el sello vigente al sortear,
  con su sha en el acta de sorteo.
- **Etapa T**: el grafo evaluado, el escalado sellado antes de B6.3 (laudo 3 del 20/09, `plan:284`), sin la cola humana
  (enmienda 5, `ccd8fad`, §1). La cola tiene su propia lectura (T4: 12 de 30).

## 3. Vía de precisión (D9)

**3.1 Unidad y población (decisión 2).** Una arista emitida por la extracción entre dos nodos de contenido, con su evidencia. Quedan
**fuera** de la población las aristas que arma el código: `remite_a`, `establecida_en`, `subclase_de`, `miembro_de`, `instancia_de`,
`parte_de`, `modificada_por`, `padre_sugerido` y `referencia` (su corrección la controlan el código y lecturas propias; `remite_a`: 0 de
167 no sostenidas, `86324cc:…/reporte_l2.md`, §2 (ii)). Quedan **dentro** las diez relaciones de contenido del esquema, con `aplica_a`
incluida: en el grafo de V son 3.983 aristas (recuento propio sobre su `kg.json`): `aplica_a` 1.770, `condicion_de` 1.379, `limita` 267,
`regula` 169, `requiere` 117, `condiciona` 85, `exceptua_obligacion` 69, `exceptua` 62, `prohibe` 54, `ejecuta` 11. La lista se fija al
sellar la muestra leyendo la cadena de ensamblado del grafo que se mide: todo predicado que el código derive se agrega a la lista de
fuera; ninguno de contenido sale.

**3.2 Muestra.** 100 aristas, estratificadas por predicado (asignación proporcional, con un mínimo de 3 por predicado que
tenga 30 aristas o más; los de menos de 30 se agrupan en un estrato «otros») y al azar dentro de cada estrato; el TO se reporta como
covariable. Semilla fijada en la firma; lista de la población, hora y sha256 de la muestra sellados antes de abrir una ficha.
**Pool de calibración, aparte:** en el mismo sorteo se reserva un segundo conjunto de 20 aristas, disjunto de las 100, del que salen
los calibradores del juez (§4.2); se sella con la muestra y no entra a ninguna cifra.

**3.3 Ficha.** Nodo de origen (tipo, etiqueta, descripción, propiedades), predicado, nodo de destino; evidencia: texto propio y
heredado de la unidad de procedencia, tramo literal si lo hay, páginas, ruta del PDF y número de página. Sin ninguna salida de
un modelo (§6.2).

**3.4 Juicios (decisión 3).** *Correcta*: sí / no / no decidible por la autora; criterio de B4.1 (a): la evidencia sostiene la relación
entre esos dos nodos, con sus sujetos, valores, calificadores y modalidad. *Importancia*, tres valores: **esencial** (una respuesta de
cumplimiento sobre esa unidad la necesita), **útil** (agrega contexto), **accesoria** (no merece estar en un grafo regulatorio). Sin
pesos: la precisión sobre las esenciales se reporta como cifra aparte (3.6).

**3.5 Procedimiento.** Lote piloto de 10; FRENO para ajustar la ficha, no el juez (`plan:445-447`); después nueve lotes de 10
con la ficha fija. Si la ficha cambió en algo que el juicio usa, las 10 del piloto se vuelven a etiquetar.

**3.6 Estimadores (ajuste 1).** Dos cifras de precisión, siempre juntas:
- **cruda**: correctas / decididas sobre las 100, con Wilson al 95 % (con 100 y una precisión cercana a 0,85, unos ± 0,07);
- **ponderada por el tamaño de cada estrato de predicado**, que es la cifra del grafo (la muestra no es proporcional por el mínimo
  de 3): p̂_w = Σ_h W_h · p̂_h, con W_h = N_h / N (N_h aristas de contenido del predicado h en el grafo medido, N su total; en V, N = 3.983) y
  p̂_h la precisión cruda del estrato; varianza Σ_h W_h² · p̂_h (1 − p̂_h) / n_h e intervalo de Wald al 95 % (z = 1,959964), la misma
  construcción que la cifra ponderada de U-LECTURA-ACEPTADAS (`reporte_l2.md`, §5). Los estratos con n_h < 5 se reportan con su
  fracción cruda «n de N» y, para la varianza, se agrupan en «otros» (declarado).
- Las mismas dos cifras para la **precisión sobre las esenciales** (correctas / decididas entre las que la autora marcó esenciales; la
  ponderada con los mismos W_h, sobre las esenciales de cada estrato), que es la cifra aparte de la decisión 3.
- Por predicado y por TO, fracción cruda «n de N» donde N < 20. Por etapa E0–E5, por la procedencia de la arista (`chunk_id`,
  `estado_e3`). Las no decidibles se reportan aparte, con las dos cotas (todas correctas, todas incorrectas).

## 4. Juez de precisión y su calibración (D10; decisiones 4 y 5; ajustes 2, 3 y 5)

**4.1 Modelo y vía (decisión 4).** `claude-sonnet-4-6` a temperatura 0, el del juez de fidelidad de EV2 (`plan:1282`), por la API con
captura íntegra y caché (`CachingClient`, `evaluacion/llm_cache.py`); prompt congelado por sha256 y declarado; ciego al grafo de origen
y a las etiquetas de la autora (`plan:435-436`); la misma ficha que ve la autora.

**4.2 Qué clasifica el juez y qué computa el código (ajuste 2).** El juez no responde «¿es correcta?». Clasifica, **componente por
componente contra la evidencia**, cada uno en {sostenido, contradicho, no_consta}: (i) el **sujeto** (el nodo de origen o el sujeto de la
norma: que la evidencia hable de ese sujeto), (ii) el **predicado** (que la relación afirmada sea la que la evidencia establece entre
los dos nodos), (iii) los **valores** (cuantías, plazos, porcentajes, fechas), (iv) los **calificadores** (condiciones, excepciones,
alcances) y (v) la **modalidad** (deber, prohibición, permiso, condición); y marca **requiere adjudicación humana** cuando la evidencia
no le alcanza para clasificar un componente (por ejemplo, el tramo está en una tabla ilegible o la relación depende de una remisión
que la ficha no trae). Para la importancia, el juez clasifica tres rasgos en sí/no: la relación fija una conducta exigible
(deber/prohibición/condición), tiene un valor o plazo concreto, y es la relación principal de la unidad o una accesoria.
El **código** computa el veredicto con esta regla fija, escrita acá y en el script, que no cambia sin firma: *correcta* = los cinco
componentes sostenidos o no_consta sin ningún contradicho y con sujeto y predicado sostenidos; *incorrecta* = al menos un componente
contradicho; *adjudicación* = algún componente marcado «requiere adjudicación humana» sin ningún contradicho. Importancia: *esencial* =
conducta exigible y (valor concreto o relación principal); *accesoria* = ni conducta exigible ni valor concreto; *útil* = el resto.

**4.3 Calibradores (ajuste 2).** El prompt lleva una sección de **casos resueltos**: entre 10 y 20 aristas del **pool de calibración**
(§3.2), nunca de las 100 del gold, etiquetadas por la autora componente por componente antes de escribir el prompt, elegidas cerca de las
fronteras (modalidad ambigua, calificador que cambia el alcance, valor con redondeo, tabla). Ningún criterio problemático se escribe como
regla declarativa sin su caso resuelto. Cuando un tipo de error se repita en la calibración, la corrección es agregar un caso resuelto del
pool (o de una arista nueva fuera de la muestra), no una regla.

**4.4 Repeticiones que re-muestrean (ajuste 3).** N = 3 por ficha, con **un cliente, una base de caché y un namespace por repetición**
(`juez_tripletas_r1`, `_r2`, `_r3`, con la versión de código y la marca de thinking), como el juez de EV2 (`ev2_juez/juez.py:150-170`,
patrón `rt_c6_n3`): la clave de la caché es sha256(namespace + request), así que el mismo pedido en tres namespaces son tres llamadas
distintas y la caché no puede devolver tres copias; el driver verifica 0 cross-hits entre las tres bases antes de agregar. Agregación
por **veredicto modal** sobre el veredicto computado; empate = `sin_consenso`, que va a adjudicación. Se registra la distribución
completa (unanimidad, 2 a 1, sin consenso) por dimensión.

**4.5 Gold a ciegas (decisión 9).** La autora etiqueta las 100 sin ver ninguna propuesta del modelo. D9 y D10 juntos lo piden: el acuerdo
juez–autora solo mide algo si las dos etiquetas son independientes. El modo asistido de D12 se usa en lo que no es gold (§6). Se aparta
de la letra de D12 para la parte del gold; declarado a los mentores (§11).

**4.6 Criterio de acuerdo (decisión 5; ajuste 5; va al laudo D-b).** Para «correcta», las tres condiciones a la vez, sobre las fichas que
el juez decide (las que manda a adjudicación se cuentan aparte, con su proporción): (i) acuerdo en al menos 84 de 100 (límite inferior de
Wilson 0,7558; el piso de 0,75 es el del criterio de U-COMP-E1, `cbcb823:docs/mandatos/UCOMP_E1_comparacion_chica_modelo.md:70-72`);
(ii) la precisión según el juez y según la autora difieren en 0,05 o menos (cruda y ponderada), para que el juez no corra la cifra que
escala; (iii) de las que la autora marca incorrectas, el juez marca incorrecta al menos la mitad, reportado como fracción cruda (con unas
15 incorrectas no se estima con precisión, y se declara). **Cifra reportada, no umbral: el kappa de Cohen** entre juez y autora para
«correcta» (dos clases, sobre las decididas por los dos) y, para la importancia, el kappa de Cohen sobre los tres valores y su variante
ponderada lineal. Para importancia, el acuerdo exigido es exacto en al menos 60 de 100 y a un nivel de distancia en al menos 90 de 100.
Si no pasa: el juez no escala; la precisión de V queda con las 100 de la autora y la de T se mide con muestra humana (§7). Si más de 15
de las 100 van a adjudicación, el instrumento se declara con esa frontera y las adjudicadas quedan como lectura humana.

**4.7 Candado de ajuste (ajuste 2).** El prompt del juez lleva escrita esta prohibición: *«Este prompt no se modifica sin decisión
escrita de la autora. Todo cambio se justifica con evidencia del texto de la norma, nunca con la etiqueta esperada de un caso.»* Una
sola recalibración, declarada, con casos resueltos del pool y nunca con las 100; después de cada cambio se re-corre todo el conjunto de
calibración. Los desacuerdos residuales se clasifican (de evidencia o de etiqueta) y quedan documentados como límite del instrumento.

## 5. Vía de cobertura (D11; decisiones 6, 7 y 8)

**5.1 Fragmentos.** Unidades terminales de E0 con texto propio de 80 a 1.500 caracteres, que es el tamaño de párrafo de D11 (en la E0
r2b de desarrollo: 1.491 de 1.768, recuento propio; mediana del texto propio con herencia 979 caracteres, percentil 90 2.078; se
recomputa sobre la E0 del grafo medido al sellar). Se excluyen las anclas de EV2 y de los pares sintéticos v3 y v4 con sus descendientes
(B4.1 (g)).

**5.2 Tamaños (decisión 6).** V: 300 fragmentos; T: 600. Las primeras 100 tienen que ser una selección (un tercio en V, un sexto en
T); el ancho del recall@100 no depende del tamaño del conjunto, y una tripleta más por fragmento cuesta poco.

**5.3 Extracción (decisión 7, con condición; ajuste 4).** Un modelo **distinto del extractor del grafo** (E1 es `claude-haiku-4-5`):
`claude-opus-5-5`, con un prompt de extracción abierta, sin el esquema: sujeto, relación y objeto en las palabras del texto, una por
fragmento, «la más importante, la que no puede faltar en un grafo de regulación», con el tramo literal que la sostiene. El código
verifica el tramo contra el texto; sin tramo verificado, la tripleta se descarta y se cuenta. **Condición:** si el resultado de
U-COMP-E1 lleva a cambiar el extractor del grafo a `claude-opus-5-5`, el extractor del recall pasa a `claude-sonnet-5-5` y el modelo
de puntaje (5.4) a `claude-sonnet-4-6`; la regla es que el extractor del recall nunca sea el modelo que extrajo el grafo medido. Mismo
modelo y mismo esquema que E1 darían sesgos compartidos y una cobertura inflada.

**5.4 Orden (decisión 7).** `claude-sonnet-5-5` puntúa la importancia de cada tripleta de 1 a 5 con una rúbrica fija, N = 3 con el
mismo mecanismo de re-muestreo de 4.4, y se ordena por el puntaje medio, con desempate por sorteo. Ordenar cientos de tripletas en un
solo pedido no es confiable; puntuar y ordenar es la forma operativa de «ordenarlas de la más importante a la menos importante».

**5.5 Calibración del orden.** La autora marca la importancia (escala de 3.4) de las 100 primeras y de 30 sorteadas entre las
posiciones 101 y 300, mezcladas y sin ver la posición. El orden pasa si al menos 80 de las 100 primeras son esenciales o útiles y si
esa proporción supera a la de las 30 de control. Si no pasa, el recall se reporta sobre las que la autora marcó esenciales, sin ranking.

**5.6 Presencia en dos pasos (decisión 8; ajuste 2).** (1) Subgrafo candidato, determinístico: los nodos cuya procedencia es la unidad
del fragmento, sus ancestros (herencia) o sus descendientes según la política de descendientes declarada (frontera ancla/chunk, B4.1
(b)), con las aristas de contenido entre ellos; su tamaño se registra por fragmento (en V, mediana unos 21.000 caracteres y percentil 90
unos 68.000, dimensionado provisorio del §8). (2) Un **juez de presencia** con la misma metodología del §4: `claude-sonnet-4-6` a
temperatura 0, por la API con caché; clasifica tres componentes de la tripleta abierta contra el subgrafo, {sujeto, predicado, objeto}
en {expresado, parcial, ausente}, nombrando el nodo o la arista que lo expresa; el **código** controla que lo nombrado exista y computa:
*presente* = los tres expresados; *parcial* = sujeto y objeto expresados con el predicado parcial, o dos expresados y uno parcial;
*ausente* = el resto; *requiere adjudicación humana* cuando el juez lo marca. Calibradores: casos resueltos por la autora sobre fragmentos
del pool de calibración (20 fragmentos reservados en el sorteo, disjuntos de los 300), nunca sobre las 100 primeras; N = 3 con el
re-muestreo de 4.4; veredicto modal; la misma prohibición de ajuste de 4.7. La autora decide la presencia de las 100 primeras con el
subgrafo a la vista; el juez escala si acuerda en al menos 84 de 100, con el kappa de Cohen reportado. Una regla solo de cadenas no
alcanza: la tripleta abierta está en las palabras del texto y el grafo en el esquema. **Se aparta de la letra de B4.1 (b)** («match de
sujeto/objeto normalizados + relación», `plan:433-434`); declarado a los mentores (§11).

**5.7 Recall@k** con k = 10, 50 y 100 (`plan:450-451`): presentes / k, con Wilson; «parcial» aparte.

**5.8 Revisión de las ausentes** (B4.1 (e)). La autora revisa cada ausente de las 100 primeras: si la tripleta es correcta según el
fragmento (si no, error del gold: sale del denominador y se cuenta), si está en el grafo y el juez no la vio (error de presencia:
se corrige y se cuenta) y si es importante. Recall crudo y depurado, los dos con sus conteos. Las ausentes importantes van al
backlog con su `capa_pipeline` (B4.4): son insumo del grafo corregido, nunca del evaluado.

## 6. Etiquetado asistido y experticia (D12; decisiones 9 y 10)

**6.1 Asistente.** Claude Code (`claude -p --bare`, solo lectura sobre el paquete de fichas) arma cada ficha y, donde se usa, una
propuesta de etiqueta con el tramo que la sostiene y la información para comprobarla: texto propio y heredado, ruta del PDF y
página, y la dirección del TO en el sitio del BCRA si el manifiesto la tiene.

**6.2 Dónde se usa la propuesta (la autora confirma sí o no).** En la revisión de las ausentes (5.8), en la clasificación por
experticia (6.3) y, si el juez no pasa, en la ampliación de la muestra de precisión, declarada como asistida; en 20 de esas
tripletas se toma además la etiqueta a ciegas, para medir cuánto cambia la propuesta la respuesta. No se usa en el gold (4.5), en
el pool de calibración ni en las calibraciones de 5.5 y 5.6.

**6.3 Clasificación por experticia.** El asistente marca cada tripleta como «la decide la autora» o «necesita un experto del
dominio», con el motivo; la autora confirma sí o no **después** de etiquetarla, para no sesgar el juicio. Las confirmadas como
«necesita experto» quedan como no decidibles por la autora (3.6).

**6.4 Vía al experto (decisión 10).** U-PREP-CONTACTO (`plan:1174-1178`) y el registro del 04/09, §3: anotación experta de una submuestra
en modo literal (`docs/registro_reunion_mentores_2026-09-04.md:77-97`). Quién adjudica (checklist P15 y Q12, `:105` y `:209`; F-7 y C-8)
se decide con los mentores. Sin experto, la evaluación corre igual y declara las no decidibles con su conteo.

## 7. Etapa T, dentro del pre-registro de B6.3

- Precisión: el juez calibrado sobre 400 aristas del grafo evaluado, con la estratificación de 3.2 y los dos estimadores de 3.6 (unos
  ± 0,035 con 0,85); control a ciegas de la autora sobre 30 sorteadas entre ellas. Si el acuerdo es menor que 26 de 30 (límite inferior
  de Wilson 0,7032), la cifra del juez se declara no validada en el escalado y se reporta la de las 30.
- Cobertura: 600 fragmentos de los TOs del conjunto de test (disjuntos de los 15 y de los 5 de la tanda 0, checklist Q10, `:207`),
  con 5.3 a 5.8 iguales y control de 30 en la presencia.
- B6.3 (d) incorpora todo esto en su pre-registro sellado (laudo D-f §5, `966253e:…:52`; checkbox del plan `:977-978`).

## 8. Costo y topes (decisión 11; ajuste 6)

**Dimensionado sobre datos reales** (grafo de V `2922b72d…` y E0 r2b de desarrollo; sorteo provisorio con otra semilla, solo para medir
tamaños, que no es la muestra): ficha de precisión (los dos nodos con sus propiedades, el predicado y la evidencia con herencia) mediana
2.044 caracteres, media 2.152, percentil 90 3.435; fragmento con herencia mediana 979, media 1.127, p90 2.078; subgrafo de presencia
(nodos y aristas de la unidad y sus descendientes) mediana 21.126, media 30.196, p90 68.298. Conversión a tokens con la razón marginal
medida en los pedidos de E1 (3,06 caracteres por token, ajuste sobre 2.438 pedidos; `data/experiment/e3_listas/freno_o1.md:21`): ficha 703 tokens (p90 1.123),
fragmento 368 (p90 679), subgrafo 6.904 (p90 22.320). **Los tokens no están contados con el tokenizador de la API: el lote piloto de 10
mide los tokens reales de cada pedido (`usage`) y re-ajusta esta tabla antes de seguir.**

Precios por millón de tokens (entrada / salida / escritura de caché / lectura de caché): `claude-opus-5-5` 4 / 20 / 5 / 0,2 y
`claude-sonnet-5-5` 2 / 10 / 2,5 / 0,2, los medidos en C1 de U-COMP-E1 (`comp_e1/c1/comun_c1.py:34-35`); `claude-sonnet-4-6` 3 / 15
(`plan:775`), con escritura 3,75 y lectura 0,30 (regla general de 1,25× y 0,1×, NO VERIFICADA contra la tarifa publicada). Supuestos de
prefijo fijo cacheado (instrucciones y calibradores): juez 3.000 tokens, extracción 1.000, puntaje 600; salidas: juez 300, extracción
150, puntaje 50, presencia 200.

| componente | llamadas V | USD V (mediana / p90) | llamadas T | USD T (mediana / p90) |
|---|---|---|---|---|
| juez de precisión (Sonnet 4.6, N = 3) | 300 | 2,44 / 2,82 | 1.290 | 10,47 / 12,10 |
| extracción abierta (Opus 5.5) | 300 | 1,41 / 1,78 | 600 | 2,81 / 3,55 |
| puntaje de importancia (Sonnet 5.5, N = 3) | 900 | 0,78 | 1.800 | 1,55 |
| juez de presencia (Sonnet 4.6, N = 3, 100 primeras) | 300 | 7,53 / 21,40 | 300 | 7,53 / 21,40 |
| **total** | | **12,2 / 26,8** | | **22,4 / 38,6** |

**Topes (decisión 11): V USD 35 y T USD 55.** El margen cubre el percentil 90 del subgrafo de presencia, que es el término que más varía
(si los subgrafos salen más grandes que el p90, se acota la política de descendientes antes de seguir, declarado), más la recalibración
única del §4.7. Freno duro por presupuesto en el script, con registro de gasto por llamada, como en C1 de U-COMP-E1. Tiempo de la autora:
gold de 100, pool de 20, orden de 130, presencia de 100 (más 20 del pool), ausentes de hasta 100 y controles de T; unas 10 a 14 horas.

## 9. Q7 (B4.2 contra B6.3 (d))

B6.3 (d) pasa a decir «con el instrumento validado en desarrollo (B4.2 y B4.3), cerrado antes de sellar el pre-registro de B6.3»; B4.2 y
B4.3 quedan como precondición de ese pre-registro (asentado en el plan el 07/10/2026). Resuelve la inconsistencia de `plan:445` y del
checklist Q7 (`:204`).

## 10. Lo decidido al firmar (decisiones de la autora del 07/10/2026)

1. Grafo de la etapa V: el de desarrollo r2b sin cola (`2922b72d…`), con la nota al laudo D-f. 2. Predicados derivados fuera de la
muestra: la lista del §3.1, fijada al sellar; `aplica_a` dentro. 3. Importancia en tres valores (esencial, útil, accesoria); la
precisión sobre las esenciales como cifra aparte, sin pesos. 4. Juez: `claude-sonnet-4-6` a temperatura 0, por la API. 5. Criterio de
acuerdo: las tres condiciones del §4.6, con el kappa de Cohen reportado y no como umbral. 6. Tamaños: 100 y 300 en V; 400 + 30 y 600 en
T. 7. Extracción `claude-opus-5-5` y puntaje `claude-sonnet-5-5`, con la condición del §5.3. 8. Presencia en dos pasos, declarada como
desvío de la letra de B4.1 (b). 9. Gold a ciegas, con los usos del modo asistido del §6.2. 10. Vía al experto del §6.4. 11. Topes: V USD 35
y T USD 55, re-estimados con el piloto.

## 11. Desvíos declarados (van a la lista para los mentores)

- El gold de 100 se etiqueta sin ver la sugerencia del modelo: se aparta de la letra de D12 para la parte del gold (la sugerencia con
  sí/no sigue en ausentes, experticia y ampliación).
- La presencia de una tripleta la decide un juez calibrado en dos pasos sobre el subgrafo de su unidad, no una regla de cadenas: se
  aparta de la letra de B4.1 (b).
- El instrumento se valida sobre el grafo de desarrollo r2b y no sobre r1: se aparta de la letra del laudo D-f (nota al pie del laudo).
- Los jueces corren por la API, no con Claude Code (ya en la lista por D2).

## Comandos de los recuentos de este documento (regla i)

```
# aristas por predicado del grafo de desarrollo r2b sin cola (22.084; contenido 3.983)
python3 -c "import json,collections;kg=json.load(open('data/experiment/reextraccion_v2/corpus_tanda0/ens_desarrollo_r2b_sincola/r2/kg.json'));print(len(kg['edges']),collections.Counter(e['relation'] for e in kg['edges']).most_common())"
# unidades de la E0 r2b de desarrollo con texto propio de 80 a 1.500 caracteres (1.491 de 1.768)
python3 -c "import json,glob;L=[len(u.get('texto') or '') for p in glob.glob('data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b/chunks_*.json') for u in (lambda d: d['chunks'] if isinstance(d,dict) and 'chunks' in d else d)(json.load(open(p)))];print(len(L),sum(80<=x<=1500 for x in L))"
# Wilson al 95 % (z = 1,959964): 84/100 -> 0,7558; 26/30 -> 0,7032; ancho con 0,85: n=100 0,0699, n=400 0,0350
# dimensionado del §8: sorteo provisorio random.Random("DIMENSIONADO_PROVISORIO_NO_ES_LA_MUESTRA").sample(...) sobre las 3.983 aristas de contenido y 1.491 fragmentos; caracteres de ficha, fragmento y subgrafo como se describe; conversión a 3,06 caracteres por token; costos con los precios de arriba
```

## Firma

FIRMADO por la autora el 07/10/2026 (versión para firmar en `865a5b2`). Rige desde esta firma. Decisiones al firmar: las once del §10, con los
topes de USD 35 (V) y USD 55 (T).

## Notas al pie

- **08/10/2026** — Enmienda 1 (vía de umbrales: exactitud de los campos de los umbrales), FIRMADA por la autora el 08/10/2026 (versión
  para firmar en `97bc53d`; el commit de la firma es el que agrega esta nota):
  `docs/enmienda1_preregistro_evaluacion_tripletas_2026-10-08_umbrales.md`. El texto firmado no cambia.
- **15/10/2026** — Quién adjudica (§6.4). La autora lo decidió para B6.3 con lo acordado con los mentores en las reuniones del 18 y el
  19/08, y pidió aplicar el mismo criterio a lo que este pre-registro deja abierto (decisión recibida a las 15:59:03; hoja de ruta de la
  mesa, §107; registro de decisiones del 15/10/2026, §8):
  - el juez hace el grueso, calibrado contra el gold de la autora (§1);
  - la autora adjudica lo que el juez manda a adjudicación, y una muestra de control de tamaño fijado antes;
  - sin experto del dominio: las tripletas que lo necesitan se marcan y se declaran como no decidibles (§6.3).
  - El texto firmado no cambia.

- **15/10/2026 — el re-sellado único de los grafos r2b de la tanda 0.** Los grafos sellados que cita este documento tienen una versión posterior, del re-sellado único (`docs/mandatos/URESELLADO_T0_resellado_unico_grafos_r2b.md`, firmado; FRENO en `data/experiment/resellado_t0/FRENO_resellado_T0.md`): `2922b72d…` (KG-Tanda0-Desarrollo-r2b-sincola) → `66e745f5…` (KG-Tanda0-Desarrollo-r2b-sincola-rs1, 6.711 nodos y 21.996 aristas). Cambian por el código de U-OMISIONES-COD (`ded41d50`) y por las salidas de R0 (`1d690df3` y `2d0f5277`). El diff por campo y por causa está en `data/experiment/resellado_t0/salidas/`. Los sellados siguen sellados (principio 9); el commit del sello de los nuevos queda en `commit_sellado` de `data/experiment/neo4j/grafos.py`. El sorteo de la etapa V, que espera este re-sellado, queda habilitado por `66e745f5…` (KG-Tanda0-Desarrollo-r2b-sincola-rs1), la versión posterior de `2922b72d…`, una vez sellado; no se corrió (vale el sello vigente al sortear: laudo D-f, nota posterior a la firma). El texto firmado no cambia.
- **19/10/2026** — Enmienda 2 (el solapamiento con la lectura de la desambiguación y la etapa T sin la tanda 0), FIRMADA por la autora
  el 19/10/2026 a las 12:13:24, tal cual (por mensaje; hoja de ruta de la mesa, §178; el commit de la firma es el que agrega esta nota):
  `docs/enmienda2_preregistro_evaluacion_tripletas_2026-10-17_desambiguacion.md`. El texto firmado no cambia.
- **19/10/2026 — El sorteo de la etapa V** (la preparación, en `data/experiment/tripletas_v/preparacion/`: el acta `acta_sorteo_V.json`,
  sha256 `5d6a237e510bcf086db717061dd146eaa9b3181006cb7b1d300164436c720c55`, sellada a las 14:23:55; decisiones de la autora recibidas a
  las 15:04:50; registro de decisiones del 15/10/2026, §49):
  - **la semilla, como desvío declarado:** el §3.2 dice «Semilla fijada en la firma» y el texto firmado no la trae. La semilla,
    `B4-TRIPLETAS-V:sorteo:2026-10-07`, lleva la fecha de la firma (07/10), pero quedó fijada en el despacho de la preparación, pegado el
    19/10/2026 a las 13:45:02, antes del sorteo (14:23:55);
  - **N = 3.967 y no 3.983:** el sorteo corrió sobre `66e745f5…`, la versión posterior del re-sellado (nota del 15/10/2026). La diferencia,
    −16, es del re-sellado: salen 83 aristas de contenido y entran 67, cada una con su fila y su causa en el diff declarado
    (`data/experiment/resellado_t0/salidas/diff_contra_sellado/diff_declarado_contra_sellado_r2b_sincola_desarrollo.json`). Los W_h del
    §3.6 usan N = 3.967;
  - **«otros» sin muestra:** el estrato «otros» (`ejecuta`, 11 aristas) tiene cuota 0,26, que redondea a 0. p̂_w cubre 3.956 de las 3.967
    aristas y se informa con las dos cotas de ese estrato (todas correctas y todas incorrectas);
  - El texto firmado no cambia.
- **19/10/2026 — El juez de precisión de V, antes de su primera corrida** (decisiones de la autora recibidas a las 22:28:02 y a las
  22:53:30, sobre el FRENO de U-TRIP-V-JUEZ, con el prompt v1 `314c62ac…`; registro de decisiones del 15/10/2026, §56). Todo esto se decide antes de cualquier
  corrida del juez:
  - **La calibración, fuera de muestra (§4.3 y §4.7).**
    - Con los casos del pool en el prompt, juzgar esos mismos casos es pedirle al juez que copie la etiqueta que tiene a la vista: así no
      aparece ningún tipo de error, y la recalibración única del §4.7 no tiene de dónde salir.
    - Cada ficha del pool se juzga, con N = 3, con un prompt que trae los otros casos, sin el suyo y sin las notas que lo citan.
    - El prompt del gold lleva todos los casos.
    - El análisis por componente sale de esa corrida, y se declara así.
  - **Las notas del pool, en el prompt,** como el porqué de cada caso, salvo el texto sobre el gold.
    - Cada nota entra tal cual, reescrita o no entra, según una hoja de la autora, sellada (`hoja_notas_pool.csv`).
    - Las referencias a otros casos del pool se traducen por código al número de caso del prompt.
    - Las notas solo las lee la autora.
  - **El hueco de la regla del §4.2:** el texto firmado no cubre una salida sin ningún contradicho, sin marca de adjudicación y con el
    sujeto o el predicado en `no_consta`.
    - Esa arista no es correcta.
    - En el acuerdo del §4.6, que es de dos clases, cuenta como incorrecta, igual que el «no» de la autora del §3.4 cuando el texto no
      sostiene algo.
    - El informe da cuántas incorrectas salen por esta vía y cuántas por un contradicho.
  - **La regla de los Sujetos sin catálogo sale del prompt:** no se aplica a ninguna ficha (0 de 20 en el pool y 0 de 100 en el gold), y
    el §4.3 no admite una regla sin su caso. Se declara con el conteo.
  - **La remisión hacia atrás:** la regla queda, con tres casos resueltos por la autora (R1 a R3, fuera de las 120 del acta, en
    `hoja_remision.csv`, sellada).
  - **Los topes (§8):**
    - el de V pasa de USD 35 a 50, declarado. El prompt v1 del juez tiene 40.406 tokens por caracteres, y el §8 suponía un prefijo de
      3.000. Con la calibración fuera de muestra, los tres casos de la remisión y las notas, el peor caso de la etapa con una recalibración
      da USD 46,84 (hoja de ruta de la mesa, §188);
    - el gold corre con tope 16 y freno en 13, y la calibración con tope 8,5 y freno en 6,5.
  - El texto firmado no cambia.
- **20/10/2026 — P16 del pool, la definición de `requiere` y la lectura de R25, antes de la primera corrida del juez de V** (decisiones de
  la autora recibidas a las 08:51:12; registro de decisiones del 15/10/2026, §59). Todo esto se decide antes de cualquier corrida del
  juez:
  - **La hoja del pool sellada no se toca, ni su sha256** (`097998e8…`).
  - **P16 lleva una corrección registrada:** su `comp_modalidad` pasa de «sostenido» a «contradicho».
    - El motivo, de la autora: la unidad `pro::2.3.5.1` impone un deber de reintegro y no veda el cobro, y la tripleta afirma una
      prohibición que el texto no dice.
    - Se justifica con el texto de la norma y con la definición del prefijo con que se extrajo el grafo de V (`PREFIJO_SISTEMA_R2B`,
      `ccffa4e3…`), no con una etiqueta esperada (§4.7). Es su regla de `regula`, `prohibe` y `limita` (R25), la sección 2 del prompt del
      juez (`6dddd215…`), tal cual: «Si `Restriccion.tipo = "prohibicion"` → usá `prohibe`. Patrón: "no podrá", "se prohíbe", "queda
      prohibido", sin una cuantía que fije hasta dónde.» y «Si dudás entre prohibición y límite, decidí primero el tipo (¿el texto veda el
      acto o lo acota?) y usá el predicado de ese tipo.»
    - Con la corrección, el veredicto que computa el código para P16 pasa de correcta a incorrecta. La importancia no cambia (útil).
    - Entra al juez por una hoja de la autora, sellada (`hoja_correccion_pool.csv`), que el código aplica en memoria. Ninguna otra marca
      del pool cambia.
  - **P16 no entra como caso resuelto en el prompt del juez,** y su nota va «no entra».
    - El §4.3 pide entre 10 y 20 casos del pool: quedan 19. Los tres de la remisión (R1 a R3) son aristas nuevas fuera de la muestra, que
      el mismo §4.3 admite.
    - En la calibración con un caso afuera por vez, P16 se juzga como los demás y se compara contra la marca corregida.
    - Con P16 afuera, el prompt no trae ningún caso resuelto de `prohibe`: R25 entra como sección del prefijo, no como una regla nueva.
  - **La convención de la autora para `requiere`,** tal cual: «requiere une una operación con la obligación que la norma le asocia, sea un
    requisito para realizarla o un deber que nace de realizarla.»
    - El prefijo define `requiere` (sección 1 del prompt del juez, `286b60f2…`, línea 24): «hacer el acto hace nacer el deber; el deber es
      consecuencia del acto». Al requisito previo lo llama `condiciona` (línea 23).
    - Si la convención entra al prompt como definición lo decide la autora (PENDIENTE). Si entra, sus casos resueltos salen del pool:
      P04, P11 y P12 son `requiere` (el acta del sorteo, `5d6a237e…`).
  - **La lectura de R25 es posterior a los sellos del piloto y del pool.** La autora leyó las definiciones del prefijo el 20/10/2026,
    después del sello del piloto (19/10/2026, 17:13:32) y del de la hoja del pool (19:21:53).
    - Las 10 fichas del piloto son 10 de las 100 del gold (el acta, `sorteo.lotes`), y sus marcas quedan como se sellaron.
    - Cómo se declara para el piloto lo decide la autora (PENDIENTE; propuesta de la mesa en su hoja de ruta, §193).
  - El texto firmado no cambia.
- **20/10/2026 — `requiere` con la definición del prefijo, P04, P11 y P12, el caso resuelto de `prohibe` y el piloto, antes de la primera
  corrida del juez de V** (decisiones de la autora recibidas a las 09:25:49; registro de decisiones del 15/10/2026, §60). Resuelve lo que
  la nota anterior dejaba PENDIENTE:
  - **`requiere`:** el juez y la autora juzgan con la definición del prefijo (sección 1 del prompt del juez, `286b60f2…`, línea 24), la
    misma vara con que la autora corrigió P16. La convención de la autora no entra al prompt.
  - **P04, P11 y P12**, los tres `requiere` del pool: la autora revisa sus marcas con esa definición. Si alguna cambia, va en la hoja de la
    corrección con su motivo, como P16, y el código la aplica en memoria. Los tres siguen en el prompt.
  - **Los lotes del gold** los lee la autora con la definición del prefijo.
  - **El piloto:** el informe de V da la precisión y el acuerdo con las 100 y, como sensibilidad fijada antes de cualquier cifra, sin las
    10 del piloto. Si las dos dan otra decisión del §4.6, se declara y rige la de las 100.
  - **El caso resuelto de `prohibe`,** porque con P16 afuera el prompt no traía ninguno:
    - es una arista fuera de la muestra: fuera de las 120 del acta, de R1 a R3 y de toda arista con procedencia en una unidad de las 120;
    - está cerca de la frontera entre prohibición y deber, por una regla fijada antes de leer ningún texto: un patrón de prohibición de
      R25 y un marcador de deber en el mismo texto propio, ordenadas con la semilla `B4-TRIPLETAS-V:prohibe:2026-10-20`;
    - es PR1, con PR2 y PR3 de reserva (`candidatas_prohibe.json`, `807343c5…`). La autora la resuelve en una hoja sellada, y entra como
      caso 23. El §4.3 admite una arista nueva fuera de la muestra.
  - El texto firmado no cambia.
- **20/10/2026** — Enmienda 3 (el intervalo de la precisión ponderada, con Wilson y el n efectivo de Kish), FIRMADA por la autora el
  20/10/2026 a las 10:01:39, tal cual, con la regla del estrato sin esenciales (por mensaje; hoja de ruta de la mesa, §195; registro de
  decisiones del 15/10/2026, §61; el commit de la firma es el que agrega esta nota):
  `docs/enmienda3_preregistro_evaluacion_tripletas_2026-10-20_wilson_kish.md`. Rige desde la firma, antes de cualquier cifra de V. Su
  script entra con el mismo commit: `data/experiment/tripletas_v/analisis/wilson_kish_tripletas_mesa.py`. El texto firmado no cambia.
- **20/10/2026 — El subgrafo de la vía de cobertura, acotado a los hijos directos, y el dimensionado del §8** (decisión de la autora
  recibida a las 14:49:10; registro de decisiones del 15/10/2026, §67):
  - **P1:** en toda la vía de cobertura (V y T), el subgrafo candidato del §5.6 toma, de los descendientes de la unidad, solo sus hijos
    directos. Es el acotamiento de la política de descendientes que prevé el §8, decidido antes de ver ninguna salida de un modelo, porque
    un subgrafo de los 300 de V pasaba el p90 del §8 (68.298 caracteres). Con P1, ninguno de los 300 queda sobre ese umbral, y cambian 10
    de los 300 (FRENO a2 de U-TRIP-V-COB, punto 4.2).
  - **El dimensionado del §8 no se reproduce:** el texto no dice con qué serialización se midió el subgrafo de presencia (mediana 21.126,
    p90 68.298), y su script no está en el repo. Sobre la población elegible de V, la forma compacta (la que ve el juez de presencia) da
    medianas de 2.407 a 4.636 caracteres, y la forma completa del `kg.json`, de 181.525 a 191.694, según la definición del subgrafo y el
    grafo (medición de la mesa; hoja de ruta, §201). La vía de cobertura mide y declara sus tamaños en la forma compacta, y el informe de V
    declara la diferencia.
  - El texto firmado no cambia.
- **20/10/2026 — La recalibración única del juez de precisión de V (§4.7), declarada antes de correrla** (decisión escrita de la autora
  recibida a las 16:27:56; registro de decisiones del 15/10/2026, §69 y §70):
  - **qué cambia:** la modalidad (§4.2) la computa el código. Por cada nodo de tipo Obligacion, Restriccion, Potestad o Condicion, el juez
    cita la marca de la evidencia que lleva su fuerza y le da su clase (deber, prohibición, permiso, condición o sin marca); el código
    controla que la marca esté literal y compara la clase con el tipo del nodo, con una tabla fija: Obligacion, deber; Restriccion de tipo
    prohibición, prohibición; Restriccion de tipo límite, prohibición o deber; Potestad, permiso; Condicion, condición. Lo demás del juez
    no cambia;
  - **por qué:** en la calibración fuera de muestra (17 de 20 en el veredicto), dos de las tres incorrectas que el juez dejó pasar no
    confrontaban la marca del texto con el tipo del nodo. El componente ya estaba definido como «deber, prohibición, permiso, condición», y
    el prefijo del extractor decide los tipos por esas marcas;
  - **cómo:** con casos resueltos del pool y nunca con las 100, re-corriendo la calibración entera fuera de muestra;
  - **fijado antes de correr:** si la versión recalibrada da menos acuerdo de veredicto que la anterior en el pool (17 de 20), el gold corre
    con la anterior, declarado;
  - **límite del instrumento:** los desacuerdos residuales de la calibración (uno de evidencia y cinco de etiqueta) quedan documentados
    como tales en el informe de V.
  - El texto firmado no cambia.
- **23/10/2026 — Enmienda 4: el juez de precisión v2, su calibración con el gold de V y su prueba sobre la muestra humana de T, que decide
  si la v2 mide la T.** FIRMADA por la autora el 23/10/2026; el commit de la firma es el que agrega esta nota (decisiones de la autora
  del 22/10/2026, recibidas a las 10:44:50, a las 11:19:29 y a las 12:24:43; registro de decisiones del 15/10/2026, §88 y §89).
  Rige desde la firma, antes de la primera iteración paga de la v2. Se fija sin haber visto ninguna salida de la v2 ni ninguna ficha de T.
  1. **Por qué.** La v1.1 no pasó el §4.6 sobre el gold de V (registro, §87): el juez no escala y la precisión de V queda con las 100 de
     la autora. La v2 es otra versión del juez, con una sola prueba fuera de muestra.
  2. **El modelo** (cambia el §4.1, solo para la v2): `claude-opus-5-5`, sin `temperature` (la API no la acepta en ese modelo) y con el
     razonamiento adaptativo, que en ese modelo no se apaga, con el esfuerzo `medium` puesto explícito y fijado antes de iterar. No se
     comparan modelos ni esfuerzos sobre el material.
     - Siguen los tres pedidos por ficha y el veredicto modal del §4.4. Con el muestreo por defecto, los tres vuelven a muestrear.
     - Sin respaldo en otro modelo: un pedido que la API rechaza deja esa repetición sin voto, y se cuenta.
  3. **El material** (se aparta del §4.3 y del §4.7, declarado):
     - el gold de V (las 10 hojas selladas, leídas por código contra su sello, solo `correcta` e `importancia`) y el pool de 20, con las
       marcas de la autora como verdad;
     - las correcciones entran como casos resueltos en las fronteras de la importancia y de «correcta», no como reglas. Las instrucciones
       de la v1.1 no cambian, y sus casos del pool quedan;
     - cada caso nuevo sale de un desacuerdo, con el porqué tomado del texto del TO, nunca de una nota de la autora. La autora lo aprueba
       antes de cada iteración paga;
     - es una segunda recalibración (la única del §4.7 fue la de la v1.4, nota del 20/10/2026), y usa las 100 del gold, que el §4.3 y el
       §4.7 dejaban fuera. Por eso la v2 no se vuelve a medir contra el gold de V.
  4. **La regla de freno, fijada antes de iterar:**
     - como máximo 3 iteraciones;
     - en cada una, la v2 juzga las fichas del gold que no son casos de su prompt: juzgar un caso con su etiqueta a la vista es copiarla
       (nota del 19/10/2026);
     - se frena antes si una iteración no mejora en al menos 2 puntos ni el acuerdo de «correcta» ni el acuerdo exacto de la importancia,
       contra la anterior y sobre las fichas que no son casos en ninguna de las dos, o si no deja ningún caso nuevo;
     - la primera no se compara: la v1.1 es otro modelo;
     - se congela la última que mejoró; si la segunda no mejora, la primera;
     - las cifras de las iteraciones son internas de la calibración: no se informan como precisión ni como acuerdo del juez.
  5. **La congelación,** antes de la prueba y con su commit: el sha256 del prompt de la v2 y de su bloque de casos, el registro de las
     iteraciones, y el código del análisis sobre T con su selftest.
  6. **La muestra de T** (cambia el §7): el sorteo de T saca del grafo evaluado 400 aristas, con la estratificación de 3.2, y dentro de
     ellas las 100 de la autora, con la misma estratificación para n = 100.
     - La semilla es `B4-TRIPLETAS-T:sorteo:2026-10-22`.
     - El sorteo y las fichas se arman apenas se selle el grafo evaluado. Las dos listas se sellan juntas, con su hora y su sha256, antes de
       que la autora abra una ficha.
  7. **La lectura de la autora:** sus 100, después de la firma del pre-registro de B6.3, como dice el §7; ciega al juez y sin propuestas de
     ningún modelo, como el gold de V (§4.5). Ningún pedido de la v2 sobre fichas de T corre antes de su sello.
  8. **La prueba,** una sola vez, apenas la autora sella su lectura y con prioridad: la v2 congelada corre sobre esas 100, y se le aplica
     el §4.6 tal cual. Son las tres condiciones de «correcta» y la importancia, con el borde de (ii) redondeado a 10 decimales y la
     importancia en proporción sobre los pares válidos (registro, §84).
  9. **Si pasa,** la v2 mide la T con el diseño del §7:
     - las 400, con los dos estimadores de 3.6 y el intervalo de la enmienda 3;
     - en las 100 de la autora cuenta el veredicto de la v2. Las 100 quedan como su validación, en lugar del control de 30 del §7;
     - lo que la v2 manda a adjudicación lo adjudica la autora (nota del 15/10/2026).
  10. **Si no pasa,** la precisión de T queda con las 100 de la autora, con los mismos estimadores (§4.6; registro, §87). No hay otra
      versión del juez en esta tanda.
  11. **Los topes,** con freno por proyección en el script: el humo, USD 2 (freno 1,70); cada iteración, USD 42 (freno 35,70); la prueba,
      USD 42 (freno 35,70); las 300 restantes de las 400, USD 125 (freno 106,20). El humo mide los tokens reales; si su proyección pasa un
      tope, el paso no arranca y decide la autora.
  12. **Desvíos declarados** (van a la lista del §11):
      - del §4.1: el modelo;
      - del §4.3 y del §4.7: los casos del gold y la segunda recalibración;
      - del §7: la validación con 100 en lugar de 30;
      - de la letra del laudo D-f, §1, que pide el instrumento validado sobre el conjunto de desarrollo. La v2 se valida sobre T una sola
        vez, con el criterio escrito antes y con la medición humana de T como respaldo, así que T no se itera (nota al pie del laudo, del
        23/10/2026).
  - El texto firmado no cambia.
- **25/10/2026 — La congelación de la v2 del juez de precisión (enmienda 4, punto 5), antes de la prueba sobre T** (hechos de la autora
  recibidos a las 12:48:23; registro de decisiones del 15/10/2026, §113; H-17 del pre-registro de B6.3):
  - **La regla de freno (punto 4):** la iteración 2 no mejora en al menos 2 puntos ninguna de las dos cifras, contra la 1 y sobre las 82
    fichas que no son casos en ninguna de las dos. Se frena, y se congela la primera. Las cifras de las iteraciones son internas de la
    calibración y no se informan.
  - **El prompt de la v2 congelada,** el de la iteración 1: sha256 `cf40964da9718181595a85b18485af02fb74c0dd255df9e9de28404acc82dfa5`.
  - **Su bloque de casos** (`casos/bloque_casos_nuevos_iteracion_1.txt`, con los 9 casos del gold de
    `casos/casos_iteracion_1.json`): sha256 `bd25f95dc30ca6053635fd111c9bf9c9520e1946a136408ab5b4c21186477ffd`.
  - **El registro de las iteraciones y el código de la v2:** el sha256 de los 87 archivos que la definen (18 de código
    y comandos, 42 de las corridas del humo y de las dos iteraciones con la regla de freno, y los de los casos, el costo y los FRENOs),
    en `data/experiment/tripletas_v/juez_v2/congelacion_juez_v2_sha256.txt`, con sha256
    `48c5ec6e5ccde53e4d0467e230ef8610ebad3c7dc502ada6b95f342be27cfeb5`. Los archivos siguen fuera del repo, en
    `fuera_del_repo/tripletas_v_juez/v2/`.
  - **El código del análisis sobre T con su selftest,** la cuarta pieza del punto 5, todavía no está escrito: entra con su propio commit,
    también antes de la prueba, y se declara como desvío de la letra del punto 5, que pone las cuatro piezas en un commit.
  - El texto firmado no cambia.
- **26/10/2026 — El código de la prueba de la v2 sobre T, el corredor y el análisis, con sus selftests (enmienda 4, punto 5), antes de la
  prueba** (decisiones de la autora recibidas el 25/10/2026 a las 13:42:24, a las 18:22:29, a las 19:13:16 y a las 22:39:18, y el
  26/10/2026 a las 09:31:22, a las 11:59:01, a las 14:05:07 y a las 15:21:34; registro de decisiones del 15/10/2026, §114 y §116 a §122):
  - **El desvío de la letra del punto 5,** declarado: la cuarta pieza entra en su propio commit, después del de la congelación. Lo
    decidió la autora, tal cual: «La congelación va como la armaste: el 186 sin el código del análisis sobre T. Ese código va en su propio
    commit, antes de la prueba, declarado como desvío del punto 5 de la enmienda 4.»
  - **El corredor y el análisis,** tal cual los decidió la autora: «La prueba sobre T corre con un corredor nuevo que importa el código
    congelado de la v2 sin editarlo (el prompt, el modelo y el armado del pedido, controlados por su sha256) y cambia solo la entrada, las
    fichas de T. Antes de la prueba, el análisis suma la cifra por etapa E0–E5 y por procedencia del §3.6, con esos campos en el JSON de
    entrada que armás vos.» Los escribió la sesión del juez v2 sin ver T, en sus etapas c, d, e y f, y los revisó la mesa por código. El
    selftest del corredor (`correr-prueba-T-v2.1`) da 101 casos y el del análisis (`analisis-T-v2.4`), 168, sin ningún dato real.
  - **En las 100 de la autora que la v2 manda a adjudicación** cuenta su hoja sellada. Lo decidió la autora, tal cual: «En mis 100 de T
    que la v2 mande a adjudicación cuenta la marca de mi hoja sellada, sin una adjudicación nueva.»
  - **La corrida cortada,** tal cual la decidió la autora: «La corrida cortada en la prueba sobre T. Rige tu regla, con dos cambios. Una
    falla de infraestructura se re-corre hasta dos veces, cada vez desde cero, como las fallas de infraestructura de B6.3, y el gasto de
    todas las corridas cuenta para el mismo tope de USD 42. Si una repetición corta por el tope o por el freno, no se re-corre nada y la
    prueba no se completa: rige el punto 10 de la enmienda 4, sin otra decisión mía. Los archivos de cada corrida cortada salen por código
    a una carpeta aparte, con su sha256 y sin abrirse, y se declaran.»
    - Una falla de infraestructura es una repetición que termina sin juzgar sus fichas por algo que no es el tope ni el freno: el corte
      por errores de la API, la red, el proceso muerto o la máquina dormida. La clasifica, la mueve y la re-corre el comando de la mesa.
    - El corredor le pasa a la guarda el tope y el freno decididos menos el gasto de las bases de las corridas cortadas, medido sobre una
      copia. Si ese gasto llega al freno, no llama.
  - **Las 300 restantes,** tal cual: «Las 300 restantes de T se rigen por la misma regla de la corrida cortada que la prueba, con su tope
    de USD 125: una falla de infraestructura se re-corre hasta dos veces, cada vez desde cero, y el gasto de todas las corridas cuenta
    para el mismo tope; si una repetición corta por el tope o por el freno, no se re-corre nada y las 300 no se completan.» Lo que se
    informa entonces, tal cual: «Si las 300 no se completan, se informa como propusiste: la precisión de T con mis 100, como en el punto
    10 de la enmienda 4; al lado, la prueba de la v2 sobre mis 100 como su validación; las 300 como no completadas, con sus intentos, sus
    motivos y el gasto contra los USD 125; y ninguna cifra de las fichas de las 300 que sí se juzgaron.»
  - **El caso que la regla no preveía,** que una repetición corte por infraestructura y, en el mismo intento, otra por el tope o el
    freno, lo decidió la autora, tal cual: «El análisis acepta una repetición cortada por infraestructura con menos de 3 intentos solo
    si otra repetición de la misma corrida cortó por el tope o por el freno. En ese caso la prueba, o las 300, no se completa, como dice
    mi regla de la corrida cortada, y se declara.» Lo aplica el análisis desde su etapa f.
  - **El sha256 de los 37 archivos** (el corredor, el análisis, sus selftests, sus comandos y sus salidas, y las versiones
    anteriores, en `etapa_c_original/`, `etapa_c_mesa/`, `etapa_d/` y `etapa_e/`), en
    `data/experiment/tripletas_v/juez_v2/sha256_analisis_T_v2.txt`, con sha256
    `80667d81485be96ead5df371dafff3b91472630d05a7bba55e03ebe36d484318`.
    Los archivos siguen fuera del repo, en `fuera_del_repo/tripletas_v_juez/v2/`.
  - **Lo que la sesión imprimió en su consola,** declarado:
    - en la etapa c, al buscar lo del juez en el registro de decisiones, 28 renglones de su §84 y su §103 (19 y 9), con renglones del
      banco y de B6.3, y 5 asuntos de commits. Ninguno trae un tramo de las preguntas, los criterios o las citas de B6.3, un id de
      pregunta de EV2 ni un «%» (la mesa, por código, en su transcripción);
    - en la etapa e, el nombre de un archivo de `docs/`, el pre-registro de B6.3, sin abrirlo (su FRENO, §7).
  - **Las cinco carpetas temporales** que dejaron las etapas a a b en la carpeta temporal del sistema, sin declararlas: 923 archivos y
    523.576.558 bytes, cachés y salidas del cliente simulado de sus corridas en seco y de sus selftests. La mesa las inventarió por nombre,
    tamaño y sha256, sin abrir ninguno, y el inventario queda en su paquete. La autora las borró a las 19:46 del 25/10/2026, con el
    script de la mesa y después de su prueba en seco exacta (registro, §117 y §118).
  - **Las coincidencias con los casos del prompt de la v2** (registro, §117): ninguna de las 100 de la autora; de las 300 restantes,
    una arista es un caso de la iteración 1 (V097). Lo decidió la autora, tal cual: «La medición de las 400 se informa también sin la
    arista de V097, como sensibilidad, igual que la prueba sin las coincidentes.» El análisis la calcula con la misma medición.
  - El texto firmado no cambia.
- **27/10/2026 — Enmienda 5: el juez de precisión v3, con casos nuevos sacados de T, el criterio del sujeto del alcance del TO y una
  validación sobre 100 fichas nuevas.** FIRMADA por la autora; el commit de la firma es el que agrega esta nota. Son decisiones de la
  autora del 27/10/2026, recibidas a las 09:30:04, 10:24:11, 11:15:38, 14:25:04, 15:04:04 y 15:30:25 (registro de decisiones del
  15/10/2026, §130, §132, §134, §138, §139 y §142). Rige desde la firma. Se fija antes de cualquier salida de la v3 y antes de que la
  autora lea ninguna de las 100 nuevas.
  1. **Por qué.** La v2 no pasó la prueba sobre T (registro, §127): la (ii) y la importancia exacta quedaron fuera. Rige el punto 10 de
     la enmienda 4, y la precisión de T es 78 de 100 con la lectura de la autora (§128). La autora decidió probar otra versión, la v3,
     después de ver que la v2 no pasó, y así se declara.
  2. **Lo que no cambia:** la cifra principal de la precisión de T es el 78 de 100 de la lectura de la autora, el resultado del protocolo
     firmado (punto 10 de la enmienda 4). Si la v3 pasa, la precisión de las 400 va al lado, como extensión declarada (punto 10); si no
     pasa, no hay otra versión.
  3. **Lo que juzga la v3:** solo «correcta». Lo demás, como la v2:
     - tres pedidos por ficha, y el veredicto modal del §4.4;
     - clasifica los cinco componentes, y el código computa «correcta» con la misma regla fija;
     - devuelve los rasgos de importancia, porque sus instrucciones son las de la v2, y el análisis no los usa: la importancia de T queda
       con la lectura de la autora;
     - lo que manda a adjudicación lo adjudica la autora.
  4. **El modelo:** el de la v2, `claude-opus-5-5`, con el esfuerzo `medium`. Cambian solo los casos: su ficha y sus instrucciones son las
     de la v2. Las instrucciones sin sus ejemplos, las mismas para la v2 y la v3, quedan en el repo con el commit de esta nota:
     `data/experiment/tripletas_v/juez_v2/instrucciones_juez_tripletas_sin_ejemplos_v2_y_v3.txt`, sha256
     `f29de17b2dcf4b11eacf615b65e025fc85874c76ff24a29393e2f959c2a01517`, con su nota al lado.
  5. **El criterio del sujeto del alcance del TO,** decisión de la autora, tal cual: «una aplica_a cuyo sujeto no nombran la unidad ni su
     contexto heredado, pero que es el sujeto del alcance del TO, es correcta. Es como leí mis 100 de T, y rige igual para mis 100
     nuevas. La ficha trae el PDF del TO (§3.3 del pre-registro de tripletas), y su alcance sostiene al sujeto. La enmienda 5 lo declara,
     junto con que el esquema no permite emitir esa relación: la precisión mide si la relación es verdadera según el TO, no si la
     extracción cumplió su regla de emisión.»
     - El esquema de la extracción no emite esa relación (sus instrucciones: «Si ni la unidad ni el contexto heredado nombran al sujeto,
       no emitas la relación»). Se declara: la precisión no mide esa regla.
     - El juez juzga con la ficha, que no trae el alcance del TO: el caso muestra el razonamiento, y si la v3 lo generaliza lo dice la
       calibración.
  6. **Los casos nuevos,** aprobados con esta enmienda. Cada uno sale de un desacuerdo de la v2 con la autora en sus 100. El bloque de
     casos de la v3 es el de la v2 más estos cinco. Cada caso trae su ficha como la recibe el juez y la clasificación de los cinco
     componentes: el del desacuerdo, como dice su porqué; los demás, como el modal de la v2 cuando ninguna de sus repeticiones los
     contradice. Los porqués:
     - **T020** (`aplica_a`, `cajasc::4.4`, sujeto). La unidad, «De corresponder, deberán observarse los recaudos…», no nombra al
       sujeto. El TO es «Cajas de crédito cooperativas (Ley 26.173)» (su portada), y su 1.2.1 dice que, «para poder actuar como cajas de
       crédito cooperativas», las interesadas deben contar con autorización del BCRA «para funcionar con ajuste a las previsiones
       contenidas en el presente ordenamiento». El sujeto de todo el ordenamiento es la caja de crédito cooperativa: el sujeto, sostenido.
     - **T030** (`requiere`, `pro::3.2.3.4`, predicado). El 3.2.3 manda que, en la sede del responsable de atención, «deberán encontrarse a
       disposición del BCRA» los reportes que ese responsable elabora (3.1.1.8). El esquema: `requiere` es «hacer el acto hace nacer el
       deber». Elaborar los reportes hace nacer el deber de tenerlos a disposición: el predicado, sostenido.
     - **T064** (`condiciona`, `snp_cheq::3.5.3`, predicado). Las entidades «deberán adoptar los mecanismos… que resulten necesarios para
       que sus clientes puedan transmitir, ceder, avalar, negociar y/o cobrar las FCEM». El esquema: `condiciona` es «el acto solo puede
       hacerse si antes se cumplió el deber». Sin esos mecanismos los clientes no pueden operar las FCEM: el predicado, sostenido.
     - **T052** (`condiciona`, `depinv::3.7.2`, modalidad). «Se admitirá la aplicación de comisiones sobre los saldos inmovilizados,
       únicamente en la medida que las entidades lo comuniquen previamente a los titulares.» El permiso es de la operación (aplicar
       comisiones); la comunicación previa es un deber que la condiciona, que es lo que el esquema modela con `condiciona` desde una
       Obligacion. La modalidad del origen, deber, sostenida.
     - **T085** (`aplica_a`, `ext::8.5.10`, modalidad). Bajo «La entidad podrá considerar cumplimentado… el seguimiento… cuando cuente con
       los elementos…» (8.5), el 8.5.10 admite imputar el valor de los bienes siniestrados «en la medida que la entidad interviniente
       cuente con» la documentación de transporte, entre otras. La facultad es la del 8.5; contar con la documentación es el requisito
       que la entidad debe cumplir para usarla, que el esquema tipifica como Obligacion. La modalidad del origen, deber, sostenida.
     - **Lo que un caso no arregla, declarado como límite de la v3:** T007 y T095, en las que el texto nombra al sujeto con una expresión
       genérica y la ficha no trae el rol del alcance del TO.
     - **Lo que no entra como caso:** T099 (`regula`), porque `requiere` también le cabe: no es un caso limpio. Queda como desacuerdo de
       etiqueta, declarado.
  7. **La calibración,** con las 100 de la autora:
     - en cada iteración, la v3 juzga solo las de sus 100 que no son casos de su prompt (95 con estos cinco);
     - como máximo 3 iteraciones, con la regla de freno del punto 4 de la enmienda 4. Como la v3 no juzga la importancia, se frena por el
       acuerdo de «correcta» solo;
     - cada caso nuevo de una iteración siguiente sale de un desacuerdo, con su porqué tomado del texto del TO y nunca de la marca de la
       autora, y la autora lo aprueba antes de esa iteración paga;
     - las cifras de las iteraciones son internas de la calibración: no se informan como precisión ni como acuerdo del juez.
  8. **La congelación,** antes de la validación y con su commit: el sha256 del prompt de la v3 y de su bloque de casos, el registro de las
     iteraciones y el código del análisis con su selftest.
  9. **La validación,** una sola vez:
     - sobre las 100 fichas nuevas, sorteadas por código de las 300 restantes, sin la de la arista de V097 (T287), con la estratificación
       de 3.2 para n = 100 y la regla (a) para los estratos cortos, decidida por la autora antes del sorteo: «la opción (a), con n = 100 y
       la semilla que propusiste, B4-TRIPLETAS-T:v3_validacion:2026-10-27, con :empate y :orden»;
     - el acta del sorteo: `acta_sorteo_T_v3.json`, `f5ce6589315a167f7e532e9709ec49e2ed89f6c8089ce6627b37e5ef51ed6ac3`, sellada el
       27/10/2026 a las 10:29:41 con el script `sortear_100_T_v3_mesa.py` (`ee0f3ce9…`). Asignación: `aplica_a` 53, `condicion_de` 22,
       `regula` 6, `limita` 5, `requiere` 3, `condiciona` 3, `ejecuta` 3, `prohibe` 2, `exceptua_obligacion` 2 y `exceptua` 1;
     - la autora las lee a ciegas, como sus 100, y la lista y su hoja se sellan antes de que la v3 vea ninguna;
     - se aplican tal cual las tres condiciones de «correcta» del §4.6, con el borde de (ii) redondeado a 10 decimales, como en el punto
       8 de la enmienda 4. La (ii) ponderada usa la importancia de la autora.
  10. **Si pasa,** la v3 mide la precisión de las 400, con los dos estimadores del 3.6 y el intervalo de la enmienda 3, que va al lado
      del 78 de 100 como extensión declarada:
      - en las 100 de la autora, que fueron la calibración de la v3, cuenta la lectura de la autora en todas, porque la v3 se ajustó sobre
        ellas;
      - en las 100 de la validación cuenta el veredicto de la v3, como el de la v2 en el punto 9 de la enmienda 4;
      - las 200 que faltan las juzga la v3 congelada;
      - al lado, la precisión con la lectura de la autora en las 200 que leyó, y la de las 400 sin la arista de V097;
      - lo que la v3 manda a adjudicación lo adjudica la autora.
  11. **Si no pasa,** queda el 78 de 100 (punto 2), con la prueba de la v3 declarada con sus cifras, y al lado la precisión con la lectura
      de la autora en las 200 que leyó.
  12. **Cuándo,** tal cual: «Ningún paso pago de la v3 corre antes de mi firma ni al lado de B6.3» (09:30:04), y «Ningún paso pago de
      la v3 corre antes de que termine B6.3» (14:25:04).
  13. **La corrida cortada:** en cada paso pago de la v3 rige la regla de la prueba de la v2 (nota al pie del 26/10/2026). Una falla de
      infraestructura se re-corre hasta dos veces, cada vez desde cero, y el gasto de todas las corridas cuenta para el mismo tope. Si
      una repetición corta por el tope o por el freno, no se re-corre nada y ese paso no se completa.
  14. **Los topes,** con freno por proyección en el script, con el costo por ficha del punto 11 de la enmienda 4: el humo, USD 2 (freno
      1,70); cada iteración, USD 42 (freno 35,70); la validación, USD 42 (freno 35,70); las 200 que faltan de las 400, USD 83,33 (freno
      70,83).
  15. **Desvíos declarados** (van a la lista del §11):
      - del punto 10 de la enmienda 4, que dice «No hay otra versión del juez en esta tanda.»: la v3 es otra versión;
      - del punto 12 de la enmienda 4, que dice «así que T no se itera», y de la nota al pie del laudo D-f del 23/10/2026, que dice «y T no
        se itera»: la v3 se calibra con las 100 de la autora en T;
      - del §4.1: el modelo, como en la enmienda 4;
      - del §4.3 y del §4.7: una tercera recalibración, con las 100 de la autora en T, que fueron la prueba de la v2;
      - del §7: la validación con 100 fichas nuevas de las 300;
      - el criterio del sujeto del alcance del TO (punto 5), que juzga la verdad de la relación según el TO y no la regla de emisión;
      - el límite de la 1b (punto 6).
  - El texto firmado no cambia.
- **30/10/2026 — La congelación de la v3 del juez de precisión (enmienda 5, punto 8), antes de la validación** (decisión de la
  autora recibida a las 09:50:13; registro de decisiones, §191):
  - **La regla de freno (punto 7; punto 4 de la enmienda 4):** la iteración 1 no deja ningún caso nuevo. De sus desacuerdos salió un
    caso limpio, T048, y la autora no lo aprobó: «No apruebo T048 y se congela la iteración 1. El "no" no juzga el caso.» Se frena,
    y se congela la iteración 1. Las cifras de la iteración son internas de la calibración y no se informan.
  - **El prompt de la v3 congelada,** el de la iteración 1: sha256 `1743db388eb2ffee9c93f0326062a24a4421d086dd750001edeba7ad456aaf18`.
  - **Su bloque de casos nuevos** (`casos/bloque_casos_nuevos_iteracion_1.txt`, los cinco casos de la enmienda 5): sha256
    `5e9052750b17e4f1cb3c4ccab2550920e45d3b3453ad23ae23114c0c9686f1e4`.
  - **El registro de la congelación, el código y su validación:** el sha256 y los bytes de los 59 archivos que definen
    esta versión: el prompt y los casos, la hoja de aprobación y su sello, las corridas de la iteración 1 con su regla, el
    registro de la congelación, y el código y los comandos de las etapas a, b y c, con el corredor y el análisis de la validación
    y sus pruebas. Por carpeta:
    5 de `casos/`, 25 de `codigo/`, 12 de `comandos/`, 1 de `congelacion/`, 5 de `corridas/`, 3 de la raíz, 8 de `pruebas_c/`.
    Van en `data/experiment/tripletas_v/juez_v3/congelacion_juez_v3_sha256.txt`,
    con sha256 `4e7a7238eba6edfc73b2257450a894a7b5c0eccf3df4bb6d21890795b47d618f`. Los archivos siguen fuera del repo, en
    `fuera_del_repo/tripletas_v_juez/v3/`.
  - El texto firmado no cambia.
- **30/10/2026 — La condición (ii) de la validación de la v3: la ponderada por estrato de predicado, antes de la validación**
  (decisión de la autora recibida a las 10:45:46; registro de decisiones, §194):
  - **La corrección:** la frase del punto 9 de la enmienda 5, «La (ii) ponderada usa la importancia de la autora.», es un error de
    redacción de la mesa. La (ii) del §4.6 se aplica tal cual: la precisión según el juez y según la autora difieren en 0,05 o menos,
    cruda y ponderada por el tamaño de cada estrato de predicado (§3.6), como en la prueba de la v2 (`criterios()` de
    `analisis_gold_juez_v.py`, `0952806a…`).
  - **La importancia de la autora,** porque la v3 no la juzga, entra en la precisión sobre las esenciales del §3.6:
    - en la validación, al lado y como descriptiva, sin decidir el pase;
    - en la medición de las 400 (punto 10), en sus estimadores.
  - **La decisión, tal cual:** «Confirmo la (ii) de la validación de la v3 ponderada por estrato de predicado, como fijan el §3.6 y el
    §4.6 y como se hizo con la v2, con las esenciales al lado como descriptivas. La frase de la enmienda 5 sobre la importancia queda
    corregida en una nota fechada del pre-registro. Lo decido antes de que corra la validación y sin haber visto ningún resultado.»
  - El texto firmado no cambia.
- **30/10/2026 — La validación de la v3: no pasa (ii). Desvío del pre-registro: la v3 juzga igual las 200 que faltan** (decisiones de la
  autora recibidas antes de las 17:45:11 y, la 3 en su versión final, la 5 y la 6, antes de las 17:57:54; todas antes de correr las
  200 y sin ningún veredicto de la v3 sobre ellas; registro, §202 y §203):
  - **La validación, tal cual salió** (enmienda 5, punto 9): 300 de 300 llamadas completas, sin rechazos, por USD 15,4589, de las
    17:08:22 a las 17:27:40 (`juez_v3/validacion/resumen.json`). De las 100 del acta, 98 las deciden los dos y 2 van a adjudicación
    (`juez_v3/validacion/analisis_validacion_v3.json`):
    - (i) pasa: acuerdo en 86 de 98 (0,8776; Wilson inferior 0,7981);
    - **(ii) no pasa**, cruda ni ponderada. La precisión del juez menos la de la autora da −0,0816 cruda (0,7959 contra 0,8776) y
      −0,0748 ponderada por estrato de predicado (0,8054 contra 0,8802). El borde es 0,05;
    - (iii) pasa: el juez marca incorrectas 10 de las 12 que la autora marca incorrectas;
    - el kappa de «correcta», 0,5572, se informa.
  - **Las decisiones, tal cual:**
    1. «La validación queda registrada tal cual salió. No hay recalibración ni otra validación.»
    2. «Decido usar igual la v3 como juez de las tripletas, como desvío declarado del pre-registro. Mi razón: considero que la
       coincidencia ficha por ficha es la medida relevante de la calidad del juez.»
    3. «La v3 juzga las 200 tripletas. Donde aparezca la precisión que da el juez, va con la nota del desvío: qué exigía el
       pre-registro, que (ii) no pasó, la diferencia medida con su signo y mi precisión sobre las mismas fichas de la validación, 86 de
       98.»
    4. «Esta decisión queda registrada con fecha y hora antes de correr las 200, sin haber visto ningún veredicto de la v3 sobre
       ellas.»
    5. «La precisión de las 400 se arma con mi lectura en mis 100 de calibración y en las 100 de la validación, y con la v3 solo en las
       200 (opción B).»
    6. «La corrección de la cifra de la v3 por el sesgo medido, por doble muestreo (Tenenbein, 1970), con intervalo por bootstrap, se
       informa solo como análisis de sensibilidad, no como cifra principal.»
  - **El desvío del pre-registro:** el §4.6 dice «Si no pasa: el juez no escala», y la enmienda 5 da la medición de las 400 con la v3
    solo si pasa (punto 10). Si no pasa, deja el 78 de 100 (punto 11). La v3 no pasa (ii) y juzga igual las 200. La decisión 5 se
    aparta también del punto 10, que en las 100 de la validación cuenta el veredicto de la v3. Va a la lista del §11.
  - **La diferencia medida, con su signo** (decisión 3): −0,0816 cruda y −0,0748 ponderada. El juez da una precisión más baja que la
    de la autora.
  - El texto firmado no cambia: la enmienda 1 y la enmienda 5 quedan como están.
- **01/11/2026 — El código de las 200 que faltan y de su análisis, sellado antes de correrlas: la hoja de adjudicación leída por su
  sello y el bootstrap por estrato** (registro de decisiones, §209, §210 y §223):
  - **El código** vive fuera del repo, en `fuera_del_repo/tripletas_v_juez/v3/`.
    - Lo sella su lista de la etapa d, con los dos cambios de abajo: `data/experiment/tripletas_v/juez_v3/etapa_d_juez_v3_sha256.txt`,
      `5762ce24…`, 19 archivos. Son el corredor de las 200 y su comando, el análisis de las 400 y su comando, la entrada sellada de las
      200, las pruebas y sus salidas.
    - La congelación del juez no cambia (`congelacion_juez_v3_sha256.txt`, `4e7a7238…`, 59 archivos).
  - **Los dos cambios,** que la autora aceptó el 30/10/2026, tal cual: «Acepto los dos cambios de la etapa d antes del 248: mi hoja de
    adjudicación con ref y veredicto, leída por su sello, y el bootstrap de la sensibilidad remuestreando las 400 dentro de cada estrato, y
    por separado los 98 pares.»
    - **La hoja de adjudicación de las 200:**
      - el análisis la lee solo después de controlar su sello;
      - sus refs tienen que ser exactamente las que la v3 manda a adjudicación, cada una `correcta` o `incorrecta`;
      - en la cifra principal, esas fichas cuentan con el veredicto de la autora. La cifra de al lado, la de la lectura de la autora
        sola, sigue sobre sus 200 de calibración y validación;
      - en la sensibilidad, la corrección toca solo las fichas que decidió la v3.
    - **Lo que queda abierto, tal cual** (decisión de la autora del 01/11/2026): «Deja abierto que la hoja de adjudicación de las 200
      frena si trae BOM o un renglón vacío en el medio: el convertidor que armes para esa hoja no tiene que dejar ninguno de los dos.»
    - **El bootstrap de la sensibilidad:**
      - en cada réplica, dentro de cada estrato, se remuestrean con reposición todas sus fichas de las 400, cada una con su fuente;
      - por separado, se remuestrean los 98 pares de π₁ y π₀;
      - son 10.000 réplicas, con la semilla 20261030 y los percentiles 2,5 y 97,5.

      La cifra principal sigue con el intervalo analítico (Wilson con el n efectivo de Kish).
  - **La entrada de las 400:** las 400 fichas de T con sus estratos, la que validó la v2, copiada byte a byte en
    `data/experiment/tripletas_v/juez_v3/entrada_analisis_400_T.json` (`d764a18b…`). El análisis controla su sha256.
  - **Lo que se declara:**
    - **Las lecturas fuera del despacho.** La sesión que escribió la etapa d listó carpetas de `tripletas_t/` y de la v2, y leyó por
      código solo nombres de claves, tipos, tamaños, cuentas y sha256. Ninguna lectura mostró el texto de una ficha, un veredicto ni una
      lectura de la autora. Es un desvío del despacho, menor, que encontró la revisión de la mesa del 30/10.
    - **La reproducción de la mesa,** sobre una copia sin ningún `NO_ABRIR_`:
      - las pruebas de la etapa d dan 36 de 36, dos veces, y salen iguales byte a byte a las de la sesión;
      - el seco de las 200 (13 de 13 en la sesión, dos veces igual) no se reprodujo en la copia: lee un prompt `NO_ABRIR_` y el acta
        de la validación, que está en una carpeta vedada para la mesa. Queda verificado por la sesión.
    - **El orden de los commits.** Este commit entra después de los de B6.4 del 31/10 y del 01/11, que no tocan nada de tripletas
      (`git log` desde el de la validación de la v3, sobre este pre-registro y sobre `data/experiment/tripletas_v/`, sale vacío).
  - El texto firmado no cambia.
- **02/11/2026 — Las 200 corridas, el análisis que manda 11 a adjudicación y cómo las adjudica la autora** (registro de decisiones,
  §227 y §228):
  - **Lo decidido antes de correr las 200,** por su commit:
    - el 254 (`1f3c1cc1ac8d9fe8594bc87523c71f5a58b23a81`): la cifra de precisión de T de la tesis (registro, §227);
    - el 255 (`95f2ff1423c098806bf9d9bc86997f7f24363f7e`): el lanzador del análisis de las 400 con la hoja de adjudicación,
      `data/experiment/tripletas_v/juez_v3/adjudicacion_200/lanzar_analisis_400_con_la_hoja_v3.sh` (`dfa9fb74…`; registro, §228).
  - **El 256** (`eb1572d947dbefa924c8eadb9dc0b9c7f8c4f0ec`, de las 23:36:30 del 01/11/2026) entra después de las 200 y no toca nada
    de tripletas. Lleva lo que la tesis cita de las coincidencias del grafo con criterios de B6.3, B6.4 y EV2, y las secciones 229 y
    230 del registro. Ninguno de sus 34 archivos es de `data/experiment/tripletas_v/` ni es este pre-registro.
  - **Las 200,** con el comando sellado, desde las 22:39 del 01/11/2026; sus procesos empezaron a las 22:39:37. Según la consola que
    informa la autora:
    - los controles de antes de llamar, OK en las tres repeticiones;
    - 600 de 600 completas, con 0 errores, 0 reintentos y 0 rechazos; 0 sin voto y 0 cruces;
    - USD 30,9172 contra el tope de 83,33;
    - «FIN: doscientas corrió una sola vez y se completó», y sale con 0.
  - **El análisis,** con el comando sellado tal cual y la entrada `entrada_analisis_400_T.json`, el 01/11/2026: según informa la
    autora, lo corrió después de las 200, y su consola llegó a la mesa antes de las 23:38:32. La hora exacta de la corrida queda NO
    VERIFICADA. Frena con 2, sin leer ninguna hoja, y manda 11 de las 200 a adjudicación: T105, T109, T150, T152, T195, T196, T203,
    T208, T250, T261 y T273.
  - **La adjudicación de esas 11,** como la fija la nota del 01/11 (`:731-738`):
    - la hace la autora, a ciegas. El material trae las 11 fichas de `fichas_T.jsonl` (`299fb76b…`), armadas con el mismo código que
      las de sus lotes de lectura de T, y la regla del §3.4 escrita. No trae ningún veredicto, voto ni razón de la v3, ni por qué cada
      una va a adjudicación;
    - la arma `armar_adjudicacion_200_v3.py` (`c4efc985…`), fuera del repo, en `fuera_del_repo/adjudicacion_200_v3/`. El material
      da `54565a94…`;
    - la hoja es `ref,veredicto`, con cada una de las 11 `correcta` o `incorrecta`;
    - **lo «no decidible» por falta de texto,** como lo decidió la autora el 02/11/2026: no hay regla nueva. Se aplica la de sus
      lecturas de T, la del §3.4 (`:77-78` y `:340-341`): si el texto no alcanza para sostener la tripleta, va `incorrecta`. Queda
      fijado antes de su lectura;
    - **el desvío declarado del pre-registro, solo para las 11 de la adjudicación** (decisiones de la autora del 02/11/2026, antes de
      su lectura):
      - la ficha que necesite un experto del dominio también va `incorrecta`, porque la hoja solo admite `correcta` o `incorrecta`
        (`:733`). Se aparta de `:207-209`, `:213`, `:304` y `:95` con `:86`; además, de `:77`, que da el tercer valor de «correcta»,
        y del §8 del registro de decisiones (`docs/registro_decisiones_calidad_y_evaluacion_2026-10-15.md:263`), que `:304` cita en `:301`;
      - la clasificación por experticia de las 11 la hace la autora sola, después de su veredicto, sin la propuesta del asistente
        ni el motivo. Se aparta de `:198-200`, `:202-203`, `:207-208` y `:271-272`;
      - su razón, tal cual: «El material de la adjudicación se armó con el mismo código que mis lotes de lectura de T y no trae
        ninguna propuesta ni veredicto de un modelo. Una propuesta del asistente sería un paso nuevo, con un modelo que lee mi
        material, antes del lanzador. La clasificación no cambia ninguna cifra, porque la hoja es de dos valores y las dos cotas de
        las 11 cubren cualquier efecto. El conteo es solo descriptivo.»;
      - el conteo que pide `:213`: al leer, la autora da primero el veredicto de cada ficha y después, como en el §6.3, se pregunta
        si necesita un experto. Anota aparte cuántas de las 11 marcaría «necesita un experto del dominio», solo el número, y se lo
        pasa a la mesa junto con el sha256 del sello, antes del lanzador. No toca la hoja, el sello ni el lanzador. Cómo queda
        registrado se propone con los resultados;
      - lo cubren las dos cotas de las 11, como pide `:95`;
    - **las dos cotas de las 11** (decisión de la autora del 02/11/2026, antes de su lectura): la cifra de las 400 de `:734` con las
      11 todas `correcta` y con las 11 todas `incorrecta`, para la cruda y para la ponderada (`:85`):
      - no se llaman «sensibilidad», porque ese nombre es de la corrección por doble muestreo (`:713-714` y `:736`);
      - son de la extensión de las 400, no de la cifra de T de la tesis, que sigue en las 100 de la autora (registro de decisiones,
        §227, `docs/registro_decisiones_calidad_y_evaluacion_2026-10-15.md:9797-9802`);
      - se calculan después del lanzador, con USD 0, sin cambiar el lanzador ni el análisis del 255. Cómo, se propone con los
        resultados;
      - se deciden después de las 200 y sin ninguna cifra de las 400 a la vista: el análisis que frena con 2 no da ninguna por la
        consola (`analisis_400_v3.py`, renglón 48);
    - la sella `sellar_adjudicacion_200_v3.py` (`8a123c18…`). Convierte lo que exporta Numbers sin BOM ni renglones vacíos, controla
      las 11 refs y no pisa un sello que ya exista;
    - el lanzador del 255 le pasa el sello y su sha256 al análisis, que lee la hoja después de controlarlos.
  - **Lo que no cambia:** ni el lanzador ni el análisis leen este pre-registro, así que esta nota no los toca.
  - El texto firmado no cambia.
