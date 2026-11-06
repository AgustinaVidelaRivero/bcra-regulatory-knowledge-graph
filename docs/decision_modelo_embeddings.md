# Decisión A2.0b — Modelo de embeddings del brazo RAG (laudo)

Fecha: 2026-08-23 · Estado: **laudado**. Unidad del plan: A2.0b (`docs/plan_tesis.md`).
Evidencia: `data/experiment/bakeoff_embeddings/` (relevamiento, reglas selladas, reporte del
bake-off, extracción verbatim de la model card, hallazgo de la frontera ancla/chunk, código y
resultados por modelo).

## 1. Qué se decide y por qué importa

Este laudo fija el modelo de embeddings que usará el índice vectorial del brazo RAG en la
evaluación head-to-head (A2) y, después, el índice denso sobre nodos del grafo (B1.10). La
elección afecta la fuerza del sistema **rival** del KG, no la del KG: un modelo débil haría
ganar la comparación por default e invalidaría el resultado central de la tesis. El criterio
rector es elegir el rival más fuerte posible dentro de las restricciones de licencia y entorno.

## 2. Por qué los rankings públicos no deciden esta elección

Relevé el leaderboard MTEB en dos pasadas (método, snapshots y citas en
`data/experiment/bakeoff_embeddings/research_embeddings.md`):

- **MTEB(spa, v1)** — snapshot 2026-08-18, 21:35–21:47 EDT, leído del DOM del Space (la
  página no es legible estáticamente). Cobertura parcial: de 219 modelos listados, solo 30
  tienen puntaje de retrieval; su columna `Retr.` promedia 5 tareas. Candidatos fuertes quedan
  fuera por falta de dato, no por desempeño (entre ellos `Qwen/Qwen3-Embedding-0.6B`).
- **MTEB(Multilingual, v2)** — snapshot 2026-08-19, 17:21–17:37 EDT. Su `Retr.` promedia 18
  tareas de retrieval, de las cuales solo 4 incluyen español: es un puntaje de capacidad
  multilingüe general, no de desempeño en castellano.
- Varios candidatos tienen contaminación declarada por el propio leaderboard (tareas del
  promedio presentes en sus datos de entrenamiento), en proporciones desiguales (de 0 a 5 de
  18 sumandos), lo que invalida comparaciones finas entre puntajes.
- La columna "Spanish" de la pestaña por idioma se registró y se descartó como criterio:
  agrega tareas de forma no declarada (un mismo modelo marca 91,65 ahí contra 51,74 en el
  `Retr.` español).
- Ninguna tarea de ninguno de los dos benchmarks se asemeja a normativa bancaria argentina en
  castellano.

Conclusión metodológica: los rankings sirvieron como criterio de **entrada** (detección de
candidatos); la elección se hizo por **medición directa sobre el corpus de la tesis**.

## 3. Filtros y excluidos

Criterios de entrada: tarea retrieval; español declarado o multilingüe; licencia abierta y
permisiva; ≤ 1B parámetros (ejecución local, Apple Silicon M4 / MPS); ventana que no trunque
el corpus.

Excluidos, con motivo (ids exactos según el relevamiento):

| excluido | motivo |
|---|---|
| `BAAI/bge-m3` | el más débil por ambas varas (49,40 español; 54,59 multilingüe) |
| `google/embeddinggemma-300m` | licencia propia con restricciones — motivo de licencia, no técnico |
| `intfloat/multilingual-e5-large-instruct` | ventana de 512 tokens: truncaría los pasajes más densos del corpus (361 de 1.763 chunks superan 512 tokens con el tokenizador de Qwen2) |
| `jinaai/jina-embeddings-v5-text-small` | CC-BY-NC-4.0: restringe la reutilización del release sin condición de uso, que es lo que el proyecto promete (C2). Se midió igualmente como **referencia no elegible** para cuantificar el costo de la restricción (§6) |
| `geevec-ai/geevec-embeddings-1.0-lite` y `perplexity-ai/pplx-embed-v1-0.6b` | no declaran español entre sus idiomas; sin evidencia directa en castellano |

## 4. El bake-off: material y método

Medición propia (unidad U-A2.0b-bakeoff; reporte en
`data/experiment/bakeoff_embeddings/bakeoff_embeddings.md`), USD 0 de API, ejecución local
(M4/MPS), determinismo verificado por doble corrida byte-idéntica en los cinco modelos.

- **Corpus indexado**: los 1.763 chunks de E0 en composición **propio + herencia** — la forma
  que E0 sella como `completo` (reproduce `sha256_completo` de los 1.763 sin excepción) y la
  misma que usará el brazo RAG en A2.
- **Consultas**: los 100 casos de los pares sintéticos v3 (50 pares × variantes literal y
  anti-léxica; material propio sellado en `68c79dc`; EV2 no se abrió — principio 7).
- **Gold**: regla de mapeo ancla → chunk declarada y sellada por sha antes de aplicarla
  (`regla_mapeo_declarada.md`, `reglas_puntuacion_declaradas.md`). La coincidencia exacta
  sola resultó degenerada: **26 de 50 pares** quedan con un gold compuesto únicamente por un
  `mini_chunk` introductorio que no contiene la respuesta (`entregable1_mapeo.md`). Se midió
  bajo la regla principal **R2** (subárbol completo del ancla; mediana |gold| 11) y un
  **control "gold bien formado"** (n = 30 casos con gold sustantivo y unívoco; mediana 1).
  Este problema es la cuarta aparición documentada de la frontera ancla/chunk en el proyecto
  (`hallazgo_frontera_ancla_chunk.md`).
- **Control léxico**: fila BM25 sobre los mismos pasajes, mismas métricas.
- **Truncamiento**: 0 chunks truncados en los cinco modelos (mayor chunk 8.233 tokens;
  ventanas ≥ 32.768), contado con el tokenizador de cada modelo (`resultados/e2_truncamiento.json`).

## 5. Resultados

Recall@k del chunk gold bajo R2 (100 casos), por variante:

| modelo | lit@1 | lit@5 | lit@10 | anti@1 | anti@5 | anti@10 | brecha @1 |
|---|---|---|---|---|---|---|---|
| bm25 (control léxico) | 72 | 86 | 86 | 16 | 34 | 46 | +56 pp |
| **harrier-oss-v1-0.6b** | **52** | **72** | **76** | **36** | **50** | **56** | **+16 pp** |
| granite-embedding-311m-multilingual-r2 | 46 | 60 | 68 | 22 | 36 | 44 | +24 pp |
| Qwen3-Embedding-0.6B | 44 | 64 | 68 | 24 | 46 | 48 | +20 pp |
| F2LLM-v2-0.6B | 46 | 58 | 68 | 16 | 38 | 46 | +30 pp |
| jina-embeddings-v5-text-small (no elegible: licencia) | 46 | 66 | 70 | 28 | 42 | 50 | +18 pp |

Tabla del control (n = 30) y detalle por corte en `bakeoff_embeddings.md` §4.

## 6. La decisión y su fundamento, con el criterio declarado a la vista

El criterio de lectura sellado ex ante establecía: *si el orden de modelos difiere entre la
regla principal y el control, no se elige mecánicamente*. **El criterio no resolvió**: hubo
dos inversiones de pareja en el control. Dejo constancia y elijo bajo las siguientes
consideraciones adicionales, declaradas:

1. **`harrier-oss-v1-0.6b` gana las 6 celdas** (dos variantes × tres cortes) contra todos los
   elegibles bajo la regla principal (n = 50 por variante). Los cortes @5 y @10 son los
   mejores proxies del uso real: en A2 el brazo RAG es un agente que itera consultas y examina
   el top-k, no una consulta única a top-1.
2. El control no contradice ese orden: está **subpotenciado** (n = 15 por variante; un caso
   equivale a 6,7 pp; ninguna diferencia entre densos supera dos casos). Bajo la regla
   principal harrier domina; bajo el control el instrumento no separa a nadie. Son
   afirmaciones distintas y la segunda no debilita a la primera.
3. La ventaja es la **mejor estimación puntual, no una separación estadística** (12 pp sobre
   el segundo en anti-léxica@1 son 6 casos de 50). Alcanza para una elección de ingeniería; no
   autoriza afirmar superioridad como resultado de tesis, y no se afirmará como tal.
4. Tiene la **menor brecha literal − anti-léxica (+16 pp)**: es el más robusto al fenómeno
   central que el brazo RAG debe enfrentar.
5. **El costo de la restricción de licencia es cero, medido**: la referencia no elegible
   (jina, CC-BY-NC) no supera al elegido en ninguna columna.
6. Licencia MIT, español declarado por los autores, ventana 32.768 sin truncamiento sobre este
   corpus, arquitectura estándar sin código remoto, determinismo verificado.

**Elijo `microsoft/harrier-oss-v1-0.6b`.**

Alternativa operativa asentada (no elegida): `ibm-granite/granite-embedding-311m-multilingual-r2`
indexa ~4× más rápido (104 s vs 428 s) con vectores de 768 dimensiones; si el índice del corpus
escalado (T2) llegara a pesar, es el reemplazo natural — la calidad decide primero.

## 7. Parámetros de uso del modelo elegido (leídos de la fuente)

Extracción verbatim completa y contraste card ↔ aplicado en
`data/experiment/bakeoff_embeddings/extraccion_verbatim_harrier.md` (sha256 de la card
descargada `8c571701…aa81`; copia en `model_cards/`). Revisión del repo del modelo pinneada:
**`f9b9dc8d367d443f2479d27aa5d8d2850c0774ee`** (`resultados/e3_entorno.json`).

- **Instrucción de query** — obligatoria según la FAQ de los autores («this is how the model
  is trained, otherwise you will see a performance degradation»): prompt preconfigurado
  `web_search_query` = `"Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "`.
- **Documentos sin instrucción** — asimetría declarada por los autores en tres lugares de la
  fuente (sin prompt de documento en `config_sentence_transformers.json`; `model.encode(documents)`
  sin prompt en el ejemplo; «no need to add instructions to the document side» en la FAQ).
- **Pooling**: last-token (`pooling_mode_lasttoken: true`). **Normalización**: L2 (módulo
  `2_Normalize` del propio repo). **Similitud**: coseno. **Dimensión**: 1.024.
- **Longitud máxima**: la fuente declara valores en conflicto (README y `config.json`: 32.768;
  `tokenizer_config.json`: 131.072). **Valor desplegado en el banco: 32.768** (techo
  documentado). El bake-off corrió con 16.384 sin efecto (0 truncados; mayor chunk 8.233
  tokens), por lo que ambos valores producen los mismos embeddings sobre este corpus. Nota de
  escalado (proyección, no medición): el corpus completo no se tokenizó; lo único medido está
  en caracteres (`data/experiment/escalado_prep/reporte_generalizacion.md`, criterio C8:
  chunks terminales de hasta 126.723 chars en tramos que E0 aún no segmenta), así que **podría
  haber unidades que superen 32.768 tokens**; a verificar con el tokenizador del modelo en B6,
  y si ocurre, el truncamiento deja de ser cero y se declara.
- **`trust_remote_code`**: no requerido (arquitectura estándar `Qwen3Model`, sin `auto_map`).
- **Entorno de referencia del bake-off**: torch 2.13.0, transformers 5.15.1,
  sentence-transformers 6.0.0, tokenizers 0.22.2; dtype `float32` (decisión propia: precisión
  igualada entre candidatos; mayor que el `bfloat16` del `config.json`); device MPS.
- **Decisión asentada**: la instrucción de query no se personalizó ni se tradujo al castellano;
  se usa la preconfigurada tal cual. Si se explorara una instrucción personalizada, será una
  variable declarada en el pre-registro de A2.1, medida con material propio — nunca un ajuste
  posterior a resultados.
- **Licencia**: MIT según metadatos de la card; el repo no incluye archivo `LICENSE`
  (asentado; referencia: SPDX MIT).

## 8. Consecuencias para A2.0-banco (requisitos)

1. **Se despliega exactamente lo medido**: revisión `f9b9dc8d…`, `float32`, composición
   propio + herencia, `max_seq_length = 32768`, versiones de librería del bake-off
   **pinneadas en el `requirements.txt` del banco** (la FAQ 2 de los autores advierte
   diferencias entre versiones).
2. El servidor MCP vectorial aplica `web_search_query` **a las consultas y nada a los
   documentos**, con un **test** que verifique que una misma consulta con y sin prompt produce
   embeddings distintos. Es el error silencioso que invalidaría el head-to-head.
3. Toda variación de configuración (instrucción en castellano, dtype, longitud) es una variable
   pre-registrada de A2.1 con material propio; no se ajusta mirando EV2 (principio 7).
4. B1.10 (índice denso sobre nodos) usa este mismo modelo y **pares frescos**, nunca v3.

## 9. Qué deja el bake-off además de la elección

1. **Complementariedad medida entre léxico y denso**: BM25 gana literal@1 por 20 pp sobre el
   mejor denso (72 vs 52) y pierde anti-léxica@1 por 20 pp contra el mismo modelo (16 vs 36).
   No miden lo mismo. Esta evidencia motiva el brazo híbrido (B1.10 / A2.1).
2. **La brecha anti-léxica sobrevive a un tercer instrumento**: tras el índice booleano y BM25
   (A1.4), tampoco los embeddings densos la cierran — en el propio modelo elegido, 36 %
   anti-léxica contra 52 % literal, y ningún denso alcanza el 72 % literal de BM25. El
   fenómeno es robusto a la familia de retrieval.
3. **Cautela de comparabilidad**: el BM25 de este bake-off (pasajes de E0) no es comparable con
   el de A1.4 (nodos del grafo). Mismo algoritmo, objetos distintos.
4. **Contaminación de material declarada**: los pares v3 ya se usaron para medir (A1.4) y aquí
   para elegir; ninguna medición posterior del modelo elegido sobre v3 es independiente. El
   brazo RAG de A2 se mide sobre EV2, que permanece intacto.
5. **recall@k estático es una heurística de selección**, no desempeño agéntico: no se citará
   como resultado del baseline.
6. **Frontera ancla/chunk, cuarta aparición** (`hallazgo_frontera_ancla_chunk.md`): toda
   medición cross-capa declara su política de descendientes antes de medir. Pendiente de
   numerar en `docs/hallazgos_tesis.md` (C0.3).
