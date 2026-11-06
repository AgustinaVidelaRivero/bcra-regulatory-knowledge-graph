# Enmienda 2 a L-ESQ-R2 — la remisión entre puntos como relación propia: `remite_a`

**FIRMADA por la autora** el 02/10/2026 · Redactada: 2026-10-02.

Enmienda con fecha a L-ESQ-R2 (`data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`, FIRMADA en `4ef7650`;
sha256 del texto firmado `66c4a1b9…`). L-ESQ-R2 no se edita: esta enmienda vive al lado y se lee junto con
ella y con sus dos notas posteriores a la firma. Por la regla k de CLAUDE.md §4, toda cita de L-ESQ-R2 es
del texto firmado (`git show 4ef7650:data/experiment/esq/enmienda_L-ESQ-R2_2026-09-30.md`), con su línea.

Las decisiones 1 a 7 que cito abajo son decisiones de la autora del 02/10/2026, enumeradas en
`docs/plan_remite_a.md`. Las decisiones D1, D2, D3 y D5 de ese plan, del mismo día, están incorporadas en
§3, §4 y §7.

---

## 0. Qué enmienda y por qué

**Lo que dicen los documentos.** Los textos ordenados remiten de un punto a otro. El caso del ejemplo de la
tesis: el punto 5.1.1.1 de Clasificación de deudores dice «dos veces el importe de referencia establecido
en el punto 3.7.» (`docs/tesis/figuras/ejemplo_prestamo_datos.json:65`).

**Lo que hace el pipeline hoy.**
- La remisión no está declarada en ningún esquema. La escribe el ensamblado como arista `referencia` con
  `rol_fuente = referencia_cruzada` (`data/experiment/reextraccion_v2/corpus_v2/r1_referencias.py:227-237`,
  llamado en `ensamblar_r1.py:164-165` y en `data/experiment/tanda0/code/ensamblar_tanda0.py:408`).
- Los tres esquemas declaran `referencia` solo como TextoOrdenado → Comunicacion:
  `data/experiment/grafo_v2/code/schema.py:169`, la matriz congelada
  (`data/experiment/esq/code/prompt_congelado.py:96-99`, la del prompt v2 sin cambios) y
  `data/experiment/pyd_r2/code/modelos_r2.py:102`.
- L-ESQ-R2 nombra «el mecanismo de remisiones» sin darle predicado (§1.3, orientación c, `:254-255`) y
  no agrega predicados (§10, `:998`).
- El validador la admite por `rol_fuente`, no por firma (`scripts/shapes_validator.py:624-626`).
- Solo parten remisiones de cuatro tipos (`TIPOS_ORIGEN`, `r1_referencias.py:51`, aplicada en `:243`). En
  la tanda 0, el 5.1.1.1 se extrae como Condicion y el 3.7 como Definicion, y la remisión del ejemplo no
  existe en KG-Tanda0-Desarrollo-r1 ni en KG-Tanda0-Diez-r1 (laudo de r2, §4,
  `docs/laudo_release_r2_pipeline.md:329` y `:334`).

**Medición de hoy.** Aristas de remisión en los tres grafos sellados (comando [m1] de
`docs/plan_remite_a.md`):

| Grafo | Remisiones | clase interna | clase externa, a nodos | clase externa, a un TO | Firmas distintas | Con destino Condicion, Definicion o Potestad |
|---|--:|--:|--:|--:|--:|--:|
| KG-Reextraído-r1 (`0226e947…`) | 5.645 | 5.451 | 188 | 6 | 17 | 0 |
| KG-Tanda0-Desarrollo-r1 (`eab2fdd0…`) | 4.242 | 4.114 | 124 | 4 | 30 | 1.349 |
| KG-Tanda0-Diez-r1 (`dd42d6d9…`) | 4.819 | 4.627 | 178 | 14 | 30 | 1.488 |

En ninguno de los tres hay una remisión con origen en Condicion, Definicion o Potestad.

---

## 1. La relación

- **Nombre:** `remite_a` (decisión 3). `referencia` queda solo para TextoOrdenado → Comunicacion.
- **Qué afirma:** el texto del punto de origen cita un punto, una sección o un texto ordenado, y el nodo
  de origen remite al contenido citado.
- **Lugar en el esquema:** es una relación propia, con firma, y el validador la controla como a cualquier
  otra (decisión 2). Deja de admitirse por `rol_fuente`.
- **Dónde existe:** en el grafo escalado, para todos los tipos de contenido, como origen y como destino
  (decisión 1).

## 2. Firma

- **Origen:** los siete tipos de contenido: Operacion, Restriccion, Excepcion, Obligacion, Potestad,
  Condicion y Definicion.
- **Destino:**
  - cualquiera de esos siete tipos, cuando la cita nombra un punto o una sección: la arista va a cada nodo
    de contenido anclado en la unidad citada, como hoy (`r1_referencias.py:26-28`);
  - TextoOrdenado, cuando la cita nombra solo la norma. Es la remisión a un texto ordenado entero.
- **Fuera de la firma:** Comunicacion y Sujeto, ni como origen ni como destino.
- **Reglas que se conservan** (`r1_referencias.py:25-32`): una remisión sin destino resoluble no genera
  arista y queda en el registro de irresolubles; el nodo de origen y su propio punto nunca son destino.

Son 56 firmas admitidas: 7 × 7 entre tipos de contenido y 7 hacia TextoOrdenado.

## 3. Propiedades de la arista

- **`alcance`** (decisión 6): propiedad de la arista, no predicados distintos. Lista cerrada de tres
  valores:
  - `to_entero`: el destino es un nodo TextoOrdenado;
  - `interna`: la unidad citada es del mismo texto ordenado que la procedencia desde la que se resolvió la
    cita;
  - `externa`: es de otro texto ordenado.

  El alcance se decide comparando textos ordenados, no por la forma de la cita. Hoy la arista guarda
  `properties.clase`, que registra la forma: una cita que nombra una norma es «externa» aunque nombre la
  propia. En KG-Reextraído-r1 hay 5 aristas de clase externa dentro de Capitales mínimos (destinos
  `cap::1.4`, una, y `cap::S2`, cuatro): con esta regla son `interna`. La cuenta de hoy con la regla
  nueva:

  | Grafo | `interna` | `externa` | `to_entero` |
  |---|--:|--:|--:|
  | KG-Reextraído-r1 | 5.456 | 183 | 6 |
  | KG-Tanda0-Desarrollo-r1 | 4.118 | 120 | 4 |
  | KG-Tanda0-Diez-r1 | 4.631 | 174 | 14 |

- **`destino`:** el código de la unidad citada (`cla::3.7`, `ext::TO`), como hoy.
- **`evidencia`:** el ancla literal, el tramo de la cita tal como está en el texto de E0 del punto de
  origen (decisión 5). Conserva el nombre de la clave de hoy (D2).
- **Procedencia:** la del origen desde la que se resolvió la cita, con su `chunk_id`.
- **`rol_fuente`:** no lo lleva (D2). Que la arista es derivada por código lo dice el predicado.
- **`clase` y `via`** de la arista de hoy no pasan a `remite_a` (D2). La forma de la cita queda en el
  registro de remisiones del ensamblado.
- **Nombre `alcance`** (D5): los nodos de contenido ya tienen una propiedad `alcance`, que dice a qué
  alcanza la regla y que el resolvedor de hoy lee (`r1_referencias.py:52`). La de la arista es otra propiedad, en
  otro objeto, y no chocan. Se mantiene el nombre y se declara.

## 4. Procedencia de la relación (decisión 5)

- La deriva el código del ensamblado, a partir del texto de E0 del punto de origen, por `chunk_id`. No se
  lee la paráfrasis del extractor.
- E1 no la emite. No entra en el tool schema de E1 ni en sus listas de predicados: los predicados que
  emite E1 siguen siendo trece.
- E3 no la verifica. La marca `no_verificada_e3` es de las relaciones que emite E1 y no se le aplica.
- Su garantía es determinística: el ancla es un tramo literal del texto de E0 del origen, y el destino es
  una unidad que existe en la estructura de E0.
- Por ser código sobre la salida guardada, entra en r2a y se re-aplica sin re-extraer (principio 12).

**Atribución de la cita a los nodos del punto de origen (D1).** La detección deja de leer el texto de
cada nodo, así que hace falta la regla:
- la cita se atribuye a los nodos del punto cuyo texto guardado contiene la unidad citada;
- si ninguno la contiene, a todos los nodos de contenido del punto.

Se reporta cuántas citas caen en cada rama.

## 5. Cómo se cuenta (decisión 6)

En dos unidades, porque una cita genera una arista por cada nodo anclado en la unidad citada:
- **citas resueltas:** chunk de origen, tramo y unidad citada;
- **aristas.**

Cada conteo se da por alcance y por firma (tipo de origen, tipo de destino). Las citas irresolubles se
cuentan aparte, por causa.

## 6. Cita a una Comunicación (decisión 7)

- La cita de un nodo de contenido a una Comunicación («según la Comunicación A 6847») queda **fuera de
  alcance en r2**: no genera arista.
- El ensamblado lleva un **registro contado**: citas, chunks y Comunicaciones distintas.
- Motivo: las Comunicaciones no son documentos del corpus, y la arista llevaría a un nodo sin contenido.
- Conteo preliminar sobre el texto de E0 de la tanda 0, NO VERIFICADO por un artefacto del repo (script
  de la mesa en el paquete `revision_REMITE_A/`): 31 citas en 19 chunks, de 14 Comunicaciones distintas.
  Al menos una es un pie de página que E0 no recortó (`ctacte::6.1.2.3`). La medición del registro
  reemplaza este conteo.

## 7. Efectos declarados

- **Lo que lee el agente.** Las herramientas del agente devuelven el tipo de la arista tal como está en
  el grafo (`data/experiment/neo4j/neo4j_index.py:240-253`), y su prompt no nombra relaciones. Desde r2,
  el agente lee `remite_a` donde antes leía `referencia`. Se acepta y se declara; no hay alias en la carga.
- **Neo4j.** La carga crea el tipo de relación desde el campo `relation`
  (`data/experiment/neo4j/cargar_kg.py:153-171`), así que `remite_a` se carga sin cambio de código. La
  carga exporta solo `orden` y `provenances_json`: `alcance` no llega a Neo4j. Su exportación queda para
  A1.8.
- **Grafos sellados.** KG-Reextraído-r1 y los ensamblados de la tanda 0 conservan `referencia` con
  `rol_fuente = referencia_cruzada`. Quien los lee reconoce la remisión con una función común a las dos
  formas.
- **Universo de la observación 12** (D3). Su definición pre-registrada dice «menos relation ==
  'referencia'» (`scripts/muestra_aristas_obs12.py:22-25`). Con el nombre nuevo, `remite_a` queda fuera
  del universo igual que `referencia`: la composición no cambia. El pre-registro de la tanda que use la
  observación 12 lleva una nota fechada de equivalencia.

## 8. Qué cambia en la suite y en las shapes

- **Shapes del perfil r2:**
  - `remite_a` se controla por su firma (§2);
  - una `referencia` con origen distinto de TextoOrdenado es una violación, con o sin `rol_fuente`;
  - `alcance` pertenece a la lista cerrada y es coherente con los extremos;
  - `evidencia` es un tramo literal del texto de E0 del `chunk_id` de la arista.
- **Suite:** el test del ejemplo `cla::5.1.1.1` exige `remite_a` sobre los grafos del perfil r2 (§9).
- **Perfil congelado:** no cambia.

## 9. Criterio de aceptación (decisión 4)

En el grafo construido con el perfil final existe al menos una arista `remite_a` desde un nodo anclado
en `cla::5.1.1.1` hacia un nodo anclado en `cla::3.7`, con `destino = cla::3.7`. Es condición para
escalar.

## 10. Qué no cambia

- El texto de L-ESQ-R2 y el del laudo congelado.
- Los nueve tipos de entidad.
- Los trece predicados que emite E1, su tool schema y sus listas. L-ESQ-R2 §10 (`:998`) se lee así: los
  trece predicados emitidos por E1 no cambian, y se agrega uno derivado por código, `remite_a`.
- `referencia` como TextoOrdenado → Comunicacion.
- Los grafos sellados y los perfiles existentes, que siguen emitiendo `referencia` para reproducir lo
  sellado.

## 11. Dependencias

- **Antes de firmar:** nada pendiente. D1, D2, D3 y D5 quedaron decididas el 02/10/2026.
- **Después de la firma:**
  - la enmienda 1 al mandato de U-R2-CODIGO (`docs/mandatos/UR2CODIGO_enmienda1_remite_a.md`) la aplica
    en R3 y en R5;
  - U-PROMPT-R2 controla que `remite_a` no entre en el tool schema de E1;
  - la medición r2a y U-REEXT-T0 miden el §5 y el §9.

## Firma

FIRMADA por la autora el 02/10/2026. Rige desde esta firma.
