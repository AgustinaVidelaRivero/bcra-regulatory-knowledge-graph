# Laudo ESQ-3a — Retoques del esquema pre-congelado

**FIRMADO por la autora — 02/09/2026** (revisión de autora aplicada:
R1–R3, R5, R6a, R7–R9 aprobados; R4 invertido a regla de omisión declarada;
R6b rechazado). Primer tiempo del gate ESQ-3 (`docs/plan_tesis.md`,
bloque ESQ; estructura aprobada sobre `esq3_estructura_borrador.md`).
Insumos: tabla de resultados de ESQ-2 (`bbac990`), desvíos (`685fc8a` +
adenda), escalera P1/P1′/P1″ (`181e262`…`0e50e3d`), calibración
U-ESQ-2-cal (`eadf4a5`), scoping D8 (`94bb7a7`), frozen de Fase 2.3
(`frozen_run/reporte_final.md`), mapa de related work
(`docs/mapa_related_work.md`), cola de mejoras diferidas. Cada retoque de
§3 es **aprobable o rechazable por sí solo**; ninguno entra al esquema
congelado sin pasar ESQ-3b (dos brazos, pre-registro aparte).

## §1. Decisión madre (decisión de autora, registrada)

Sobre el menú de cinco escalones (ampliar enums · tipos/predicados para las
candidatas · properties en relaciones · núcleo+extensión · schema-light):

- **Escalones 1 y 2: SÍ** — ampliación del vocabulario DENTRO del paradigma
  de esquema cerrado, desagregada en los retoques de §3.
- **Escalón 3 (properties en relaciones): DIFERIDO** explícitamente a
  **ESQ-RI-3 / C1.7**. Fundamento: 0/38 apariciones azarosas en ESQ-2 (la
  familia de hechos con valor no promovió por criterio); su motor real es
  el régimen informativo, que tiene secuencia propia ya laudada
  (`94bb7a7` §D10: ESQ-RI-1→4); y la vertiente de cardinalidad (f. 35) ni
  siquiera se resuelve con properties en relaciones. Diferir es la
  decisión, no una omisión.
- **Escalón 4 (núcleo + zona de extensión): RECHAZADO** con evidencia
  interna: una zona de extensión ES el canal abierto en producción, y el
  canal abierto fue falsado dos veces — P1′/P1″ (el modelo no propone:
  deforma en cajas válidas, de forma inestable) y la calibración
  (`eadf4a5`: el descubrimiento sobrecuenta, 7/10 falsos positivos).
- **Escalón 5 (schema-light pleno): RECHAZADO** con evidencia interna y
  literatura leída: ya corrió como run_4 del frozen y perdió contra el
  esquema cerrado (estabilidad 93 % vs 86 %, precisión de punto 20 vs 14,
  hit_limit 38 % vs 49 %, `frozen_run/reporte_final.md` §2); RAGulating
  (resumen 00) reporta mejora marginal y dependiente del umbral; el KG
  legal (paper 04) solo logra T-Box sin instancias en su brazo LLM.
- **Posición registrada para la exigencia 10 del mapa** (schema-based vs
  schema-free): **schema-based con vocabulario ampliado por medición** —
  el paradigma se sostiene con evidencia propia (frozen) y el vocabulario
  se corrige donde ESQ-2 midió que quedaba corto.
- Regla de frontera: si una revisión futura quisiera reabrir los escalones
  4–5, es **CONSULTA DE ALCANCE a mentores** antes de cualquier laudo.

## §2. Cláusula de justificación — fidelidad del recurso, no rendimiento del agente

La ampliación del escalón 2 se justifica por **FIDELIDAD DEL RECURSO**:
ESQ-2 midió pérdida y deformación de representación (74 % [58, 85]
parcial+no como cota superior; firma real 42 % [28, 58]); NO midió si un
vocabulario más rico produce mejores respuestas, y la evidencia propia
desaconseja prometerlo: run_3 vs run_4 difieren en trazabilidad más que en
correctitud; r1 quedó dentro de la banda de no-señal de EV2 pese a mejor
extracción; y la clase modal de fallas del sistema es **generación**
(17/25/21 por grafo, `atribucion_fallas.md`). **Consecuencia operativa**:
ESQ-3b mide **fidelidad de extracción** en sus dos brazos y **NO evalúa
respuestas del agente**; medir el efecto en respuestas sería otra unidad,
con la expectativa declarada de que probablemente no se mueva.

## §3. Retoques desagregados (cada uno aprobable/rechazable por separado)

Formato: qué se cambia · qué lo motiva (fichas/familias/entradas) · qué
ataca · predicción falsable para el brazo objetivo de ESQ-3b (se sellan en
el pre-registro de ESQ-3b antes de correr).

**R1 — Tipo nuevo `Potestad`** (facultad/permiso: contenido deóntico de
habilitación, incluida la facultad discrecional de la autoridad).
Properties: descripcion; entra al dominio de `establecida_en` y `aplica_a`.
· Motiva: candidata (d) (6 azarosas / 5 TOs); familia «potestad omitida»
(f. 2, 24, 26, 53, 66); confirmación independiente en producción
(`eadf4a5`: veedor, extensión de plazo, permiso adicional, códigos).
· Ataca: candidata (d); parte de (a) (facultades forzadas a Obligacion,
f. 15, 23).
· Predicción: la unidad de la f. 26 (`opefci::6.3`, «podrán negociar»)
produce un nodo Potestad con la habilitación (hoy se evapora); la de la
f. 15 (`ctacor::1.1`, «se encuentran facultadas para») deja de tipar la
facultad como Obligacion.

**R2 — Tipo nuevo `Condicion` + predicado `condicion_de`**
(Condicion → {Excepcion, Obligacion, Restriccion}): antecedente de una
salvedad, que hoy no tiene caja (f. 39: «ninguno de los 6 tipos admite
condición») ni predicado.
· Motiva: f. 39 (condición de excepción invertida en deber autónomo, con el
subjuntivo como evidencia); f. 26 de EV2-lectura («siempre que cumplan»
reescrito como deber, citada en f. 39).
· Ataca: parte de (a) FORZADA.
· Predicción: la unidad de la f. 39 (`lavdin::3.3.4.3`) produce Condicion,
no Obligacion; el vínculo cross-unidad hacia 3.3.4 queda para E3, que con
este retoque ya tiene firma posible (hoy no la tiene ni con E3, f. 39).

**R3 — Tipo nuevo `Definicion`** (término + definiens), con la
delimitación de la f. 37: SOLO para definienda que no son actos ni
prescripciones (clases, conjuntos, conceptos, parámetros); los actos
definidos siguen en Operacion.
· Motiva: familia «definición sin fuerza deóntica» (f. 8, 21, 25, 46;
2 az / 4 TOs); f. 46: el término central del TO («cuenta de registro»)
no está definido en ningún nodo; contrastes f. 37 y 20.
· Ataca: parte de (a) y de las omisiones ESQUEMA.
· Predicción doble: la f. 25 y la f. 46 producen nodo Definicion con el
término; y (anti-atracción específica) el atesoramiento de la f. 37
(`traval::1.1.1.1`) SIGUE en Operacion.

**R4 — Regla de omisión declarada para contenido meta-normativo** (el
contenido que predica sobre el significado o alcance jurídico de actos o
normas, no sobre conducta, NO se extrae; la omisión queda contabilizada
porque (f) ya se lee como cota superior). **INVERTIDO en revisión de
autora**: la propuesta original de mesa (tipo nuevo `Interpretacion`) queda
como **alternativa registrada, promovible en ESQ-3b o después SOLO si
aparece evidencia azarosa**. Fundamento del rechazo del tipo, verificado
por la autora: (i) las 6 fichas del clúster meta-normativo son TODAS
dirigidas, 0 azarosas — la misma base con la que §4 difiere (e);
(ii) el mandato azaroso de la candidata (a) lo consumen íntegramente R2,
R3 y R5 (f. 39, 43, 53: condición, consecuencia, definición — ninguna
meta-normativa): R4 no aportaba azarosas propias; (iii) coherencia interna
con R5 («no se improvisa un tipo con 1 azarosa») y con la marca de
evidencia mínima de R6b; (iv) el tipo estaba definido EN NEGATIVO («no
sobre conducta») — la caja blanda que R5 se negó a crear, sin la
delimitación positiva ni la predicción anti-atracción de R3; (v) la f. 69,
marcada sí_completo, muestra que el clúster no es un tipo sino un NIVEL
(finalidad, vigencia, interpretación y aplicabilidad son cuatro cosas
distintas unidas por una propiedad negativa).
· Motiva: f. 46 (cláusula interpretativa forzada a Restriccion: «una
prohibición inventada, anclada en un nodo real del grafo»), f. 19
(finalidad forzada a Obligacion: deber falso), f. 29 — tres tratamientos
improvisados distintos para el mismo contenido (trío documentado en
f. 46).
· Ataca: la sub-clase de (a) FORZADA con daño directo del tipo
grounded≠correct — que la omisión cura por completo y el tipo solo
redirigiría.
· **Declaración explícita**: esta regla NO es un apartamiento del criterio
sellado sino su aplicación — no agrega vocabulario ni toca el modelo de
datos; es una instrucción de extracción justificada por el daño
documentado (prescripciones falsas ancladas en nodos reales, f. 46 y
f. 19).
· Predicción: la cláusula del BCRA de la f. 46 (`cryl::1.2`) y la
finalidad de la f. 19 no generan ningún nodo prescriptivo
(Restriccion/Obligacion); la pérdida aparece como omisión en la cota
superior, no como falsedad en el grafo.

**R5 — SIN tipo nuevo para consecuencia/sanción: partición declarada.**
Las consecuencias PROHIBITIVAS ya encajan en Restriccion (partición de la
f. 38); las DISCRECIONALES son potestades de la autoridad y las cubre R1
(f. 63: revocación «a juicio del BCRA»).
· Motiva: familia «consecuencia sin vínculo a su condición» (f. 38, 43,
63; 1 az / 3 TOs).
· Ataca: la familia sin agregar caja blanda.
· Predicción: la revocación de la f. 63 (`ayccef::2.11`) cae en Potestad;
las prohibitivas de la f. 38 siguen en Restriccion. Si ESQ-3b muestra que
la partición no cubre (consecuencia automática no prohibitiva sin caja),
este ítem se reabre — no se improvisa un tipo ahora con 1 azarosa.

**R6a — Predicado nuevo `exceptua_operacion`** (Excepcion → Operacion).
· Motiva: familia F2 «predicado faltante», sub-etiqueta excepción→operación
(f. 44, 62, 65; f. 44: «falta el predicado en el esquema — ningún E3 lo
arregla»).
· Ataca: F2; parte de las omisiones ESQUEMA.
· Predicción (chunk-local, limpia): en la unidad de la f. 44
(`lavdin::3.3.5`) las tres Excepcion emiten `exceptua_operacion` hacia las
tres Operacion del MISMO chunk (hoy: seis nodos y cero vínculos entre
ellos).

**R6b — Predicado `instrumenta`: RECHAZADO en revisión de autora** por
evidencia bajo criterio (1 ficha dirigida, 0 azarosas; f. 74,
`cryl::11.3`). Fundamento registrado: sería incoherente aprobarlo mientras
(e), con 4 fichas, queda diferido (§4). La sub-etiqueta
documento→operación de F2 pasa a **residuo documentado para r2** (entrada 8
de la cola, ciclo B2.6).

**R7 — Campo nuevo `descripcion` en Operacion** (campo, no tipo).
· Motiva: familia «atributo de operación sin campo donde alojarse»
(f. 32, 47); medición transversal de la f. 40 (7 de los 8 huérfanos son
Operacion, agravados por no tener descripcion); f. 37 y 46 (el definiens
vive en el label por falta de campo).
· Ataca: la familia; reduce daño colateral de f. 62 («y/o las garantías
que las respalden» sin dónde vivir).
· Predicción: el atributo de la f. 32 (`expaef::9.1`, «con personal y/o
recursos técnicos propios») se aloja en la descripcion de la Operacion.

**R8 — Ampliación del dominio de `aplica_a` a {Operacion, Excepcion}.**
· Motiva: entrada 2 de la cola, laudada en D8 (`94bb7a7`): 304
`firma_invalida` en el conjunto de desarrollo, 196 (64 %) siendo este
único pedido; medición transversal de ESQ-2: 11 tripletas de firma
inválida en las 75 fichas (f. 39).
· Ataca: entrada 2 (se RESUELVE con este laudo); recall de sujetos.
· Predicción: las tripletas `aplica_a` desde Operacion/Excepcion de las
unidades de ESQ-2 hoy descartadas por firma pasan a emitirse como válidas
(verificable contra las 11 transversales).

**R9 — Valores nuevos del enum de subtipo de Obligacion.**
Primer valor anclado: `reporte_al_supervisor` (f. 67: reporte a la SEFyC
etiquetado `comunicacion_a_cliente` — tercera aparición del error exacto,
con f. 13 y 45; el par comunicación-al-cliente / reporte-al-supervisor es
la confusión estructurada más dañina del enum actual,
`prompt_e1.py:77`). Lista final: se fija con un **análisis de frecuencia a
costo $0** sobre las 762 extracciones persistidas (¿qué contenidos caen
hoy en el 76 % de `tipo="otra"`, f. 39?), hasta 3 valores adicionales con
conteo, ANTES del pre-registro de ESQ-3b.
· Ataca: el 76 % de «otra» (higiene, escalón 1) y la sub-clase EVITABLE
de (a) — sin prometer que el prompt corrige conducta: eso es B5.
· Predicción: el e2 de la f. 67 (`ayccef::5.2.4.4`) no vuelve a
`comunicacion_a_cliente`.

## §4. Pronunciamiento sobre (e) — hechos con valor

No promovió por criterio (0 azarosas; la dirigida no promueve sola). Llega
por material propio (`fe1fe36`, entrada 5 de la cola). **Decisión: se
difiere junto con el escalón 3 a ESQ-RI-3 / C1.7**, donde vive su motor
(régimen informativo) y su secuencia laudada. El esquema congelado de este
gate rige para normativa general y **declara como limitación conocida** que
no representa hechos con valor n-arios — la conclusión de diseño se escribe
en C1.7 (limitación argumentada = contribución).

## §5. Triage de las 13 familias q3 (columna E3/ESQUEMA/EXTRACTOR de la tabla)

- **ESQUEMA → retoques de este laudo**: potestad omitida → R1 · definición
  sin fuerza deóntica → R3 ·
  consecuencia sin vínculo → R5 (partición R1/Restriccion) · F2 predicado
  faltante → R6a (la sub-etiqueta documento→operación: residuo para r2 por
  rechazo de R6b) · atributo de operación sin campo → R7 · contenido
  explicativo no prescriptivo → R4 (regla de omisión declarada). Hecho con
  valor perdido y criterios de determinación de un parámetro → **§4**
  (diferidas con fundamento).
- **E3 → promesa del ensamblado, B5 la hereda como criterio de
  aceptación**: vínculo normativo cross-unidad (f. 39: «la resuelve E3») y
  la vertiente intra-TO de remisión normativa (f. 71). La vertiente de
  remisión hacia otra norma queda parcialmente cubierta por el grafo
  escalado mismo (el destino pasa a existir como TextoOrdenado del corpus)
  — B5 verifica; lo que aún carezca de predicado se registra en la
  medición de la tanda 1.
- **EXTRACTOR/PIPELINE → B5 con entrada trazable, NO son retoques de
  esquema**: pérdida de contenido del chapeau (F1; f. 11 troceo, f. 64
  extractor) · arista con firma válida no emitida (f. 3) · texto de
  reproducción obligatoria no preservado (f. 28) · calificadores
  recortados (f. 10, 53, 67, medidos en observaciones) · properties
  vacías (32 casos, f. 39) · nodos huérfanos (8/213, f. 40).

## §6. Checklist de la cola (regla del gate: se resuelve o re-difiere con destino)

- **Entrada 2** (304 `firma_invalida` / dominio de `aplica_a`): **RESUELTA
  por R8**, con la prioridad al subconjunto de 196 que D8 mandaba.
- **Entrada 3** (`RECHAZO_PREDECLARADO` que reaparezca): **CERRADA sin
  objeto** — dependía de corridas con canal abierto y el canal se retira
  (entrada 7); su espíritu quedó cubierto por la lectura de ESQ-2 (las
  familias q3 son exactamente el conteo de lo que insiste).
- **Entrada 4** (anotados i–iii de U-ESQ-1b): **CERRADA sin objeto** — los
  tres ítems son del modo canal abierto, que no va a producción.
- **Entrada 7** (permanencia del canal abierto): **RESUELTA — SE RETIRA.**
  Fue instrumento de medición; como mecanismo de producción fue falsado
  dos veces (P1′/P1″, `eadf4a5`). El pipeline de producción sigue cerrado.
- **Entrada 5** (modelo de datos sin hechos con valor): **pronunciamiento
  en §4** — diferida a ESQ-RI-3/C1.7, limitación declarada del esquema
  congelado.
- **Entradas 9–11** (revisión): 9 → su destino «ESQ-3 (tratamiento del
  esquema)» queda CUMPLIDO por §1–§3 y la cláusula §2; 10 y 11 → rigen
  para la lectura de ESQ-3b (cegado; instrumento arreglado para textos
  largos ANTES de esa lectura).

## §7. RIESGO DECLARADO (el laudo lo asume por escrito)

**El esquema retocado queda informado por 15 documentos de 157** (5 de
diseño + 10 de ESQ-2, trasladados a desarrollo) **y nunca fue probado
sobre material que no lo informó.** Mitigaciones registradas:

1. Dispersión de las candidatas: (a) presente en los 10 TOs de ESQ-2;
   potestades en 5 TOs **más** confirmación independiente en la
   calibración (`eadf4a5`), sobre documentos distintos.
2. El criterio sellado descartó lo débil: (c), (g) y (e) no promovieron —
   los retoques no persiguen apariciones únicas.
3. Naturaleza jurídico-genérica de los tipos que entran: potestad,
   condición, definición, interpretación son categorías del derecho, no
   idiosincrasias de los 15 documentos leídos.
4. El brazo de regresión de ESQ-3b: la atracción se mide antes de
   congelar.
5. La ventana de la tanda 1 de B6 (§8) opera como test de generalización
   sobre material virgen: 20 TOs nunca vistos, con salida de corrección
   declarada.

**Punto de agenda de mentores — CONSULTADO** (se agrega a la agenda del
plan): «El esquema final queda informado por 15 documentos de 157 (5 de
diseño + 10 de ESQ-2, que pasan a desarrollo). Las mitigaciones son las
cinco registradas en el laudo ESQ-3a §7, incluida la ventana de la tanda 1.
¿Alcanza, o recomiendan reservar TOs vírgenes adicionales como test de
generalización del esquema ANTES del escalado?» Costo estimado de la
alternativa, para respuesta informada: ~5 TOs vírgenes ≈ 380 unidades de
extracción ≈ USD 2,10 (por unidad promedio de ESQ-2) + ~35–40 fichas de
lectura de la autora (~4–5 h) + **quema 5 documentos más del conjunto de
test** (el pool de B6.3 pasa de 142 a 137 TOs elegibles).

**LIMITACIÓN AGREGADA — 08/09/2026** (agregado posterior a la firma del
laudo; entrada nueva, ninguna de las anteriores se modifica).
**FIRMADO por la autora — Agustina Videla Rivero, 08/09/2026.**

*Qué limita*: la **mitigación 4** («El brazo de regresión de ESQ-3b: la
atracción se mide antes de congelar») y, con ella, toda lectura de la
regresión fresca como evidencia de generalización.

**La regresión fresca de ESQ-3b vuelta 2 es fresca a nivel UNIDAD, no a nivel
DOCUMENTO.** Sus 12 unidades salen del pool de las 687 unidades extraídas y no
fichadas **de ESQ-2**, es decir de los **mismos diez documentos** cuya lectura
informó los retoques que la regresión verifica. El sorteo es estratificado por
TO con mínimo 1 por TO, de modo que los diez documentos están representados
por construcción: 2 de `ayccef`, 2 de `expaef` y 1 de cada uno de los ocho
restantes. Fresco es el texto de cada unidad, que ninguna ficha había mirado;
no es fresco el documento del que sale, ni su materia, ni su redacción, ni el
patrón de extracción que ese documento induce.

*Evidencia*: `data/experiment/esq/prerregistro_esq3b_v2.md` §0 (sellado
`40493c9`) declara el pool como «las **687 unidades extraídas y NO fichadas**
de ESQ-2»; el reparto por TO y las 12 unidades elegidas constan en
`data/experiment/esq/cobertura/orden/seleccion_brazos_esq3b_v2.json`, campo
`regresion_fresca` (`pool_n` 687, `cuotas_por_to`, `brazo_base` = «extracción
de ESQ-2»).

```bash
python3 -c "
import json,collections
d=json.load(open('data/experiment/esq/cobertura/orden/seleccion_brazos_esq3b_v2.json'))['regresion_fresca']
print(d['n_unidades'], d['pool_n'], sorted(d['cuotas_por_to'].items()))
print(collections.Counter(u['to'] for u in d['unidades']))
"
```

*Por qué importa*: el §3 del pre-registro v2 declara que «la generalización la
miden la **regresión fresca** (12 unidades que jamás informaron ajuste alguno)
y la **ventana de la tanda 1 de B6**». Las **dos** vías tienen la misma clase
de limitación de documento — la de la tanda 1 está registrada en
`data/experiment/esq/fe_erratas_laudo_esquema_congelado_virgenes.md` —, y el
riesgo declarado en la cabecera de este §7 («nunca fue probado sobre material
que no lo informó») queda por lo tanto **menos mitigado de lo que la lista de
cinco sugiere**.

*Qué NO se debilita*: los **retiros**. `requisito_de_estructura` salió del
esquema congelado porque falló 3 de 5 en la regresión fresca; fallar sobre
material cercano es al menos tan malo como fallar sobre material lejano, de
modo que el retiro se sostiene igual o con más razón. La métrica de regresión,
los strikes y el balance de R2 tampoco cambian: son mediciones sobre las
unidades efectivamente corridas.

*Qué SÍ se debilita*: las lecturas **positivas** de generalización apoyadas en
la fresca — señaladamente la de R9-núcleo en el laudo de esquema congelado
(«primera señal de generalización positiva: 3 emisiones en material fresco») y
la de R2 («ejecutó el patrón chapeau-deber completo en material fresco»). Un
acierto sobre unidades de los mismos diez documentos es evidencia de que el
retoque no se rompe cerca; no es evidencia de que viaje lejos. Corresponde
decir «material no fichado de los diez de ESQ-2» donde hoy dice «material
fresco».

*Registro previo*: `docs/plan_tesis.md:1086` describe la regresión fresca como
«sobre material que no lo informó». Eso es la descripción del **diseño** —
ninguna de las 12 unidades informó un ajuste—, no el registro de su límite, y
por eso hace falta esta entrada: el diseño es correcto y el alcance de lo que
prueba es menor que el que la frase sugiere.

## §8. Política post-congelado (opción (ii), decidida acá)

**Ventana única de corrección en la tanda 1 de B6**: la tanda 1 (20 TOs)
actúa como health-check de esquema; si revela una clase nueva de falla DE
ESQUEMA (no de pipeline), se admite UN ciclo de corrección con laudo
propio, re-extracción de la tanda 1 incluida, SIEMPRE ANTES de sellar el
pre-registro de B6.3. **Sellado ese pre-registro, la ventana muere** y
rige el congelado definitivo: toda corrección posterior es release
posterior a la evaluación final (principio 9, sin excepciones).

## §9. Salida

Con este laudo firmado: (1) el análisis de frecuencia $0 de R9 fija la
lista del enum; (2) se redacta y sella el **pre-registro de ESQ-3b** (dos
brazos, predicciones de §3 selladas por separado, regla «si regresión
falla, el retoque se revisa aunque el objetivo pase», tope propio
USD 1,00 del remanente de la saga); (3) corre ESQ-3b; (4) con los dos
brazos pasando, se emite el **laudo de esquema congelado** con sha,
posición de la exigencia 10 y la política §8.

## Firma

Firmado por la autora, 02/09/2026. Los retoques aprobados (R1, R2, R3, R5,
R6a, R7, R8, R9 — con R4 como regla de omisión declarada) son la lista
cerrada que ESQ-3b verifica; ninguno entra al esquema congelado sin sus dos
brazos pasando.
