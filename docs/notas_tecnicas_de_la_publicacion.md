# Notas técnicas de la publicación

Estas secciones estaban en el README de la primera versión. Al reordenar el repositorio, el código de las 5 piezas del cap. 4 se mudó a `src/` y salió lo que no hacía falta. El mapa, las pruebas y la guía están al día, y «La mudanza a `src/`», «Las ediciones», «Lo que salió» y «La variable `NEO4J_PASSWORD`» cuentan lo que cambió. El README nombra este archivo.

## Mapa por etapa

El código de la segmentación, el extractor, el validador, el verificador y el ensamblado está en `src/`, una carpeta por pieza, y lo que usan 2 piezas o más está en `src/comun/` (ver «La mudanza a `src/`»). El resto del código conserva las rutas que tenía en el repo de la tesis, para que los import y las rutas relativas a la raíz sigan andando.

| Carpeta | Archivos | Qué hay |
|---|---:|---|
| `(raíz)` | 8 | `README.md`, licencias, `NOTICE`, `CITATION.cff`, `requirements.txt`, `.gitignore` y `SHA256SUMS` |
| `corpus/` | 3 | Manifiesto del corpus; los Textos Ordenados con su enlace y su sha256 |
| `evaluacion/` | 7 | Las 192 preguntas de B6.3 y B6.4 con sus criterios, la respuesta final del agente y su veredicto en cada corrida, y el programa que reproduce la fidelidad |
| `evaluacion_contenido/` | 15 | Las 400 tripletas y los 130 hechos de la evaluación del contenido del grafo, con su veredicto, el código sellado de sus análisis y el programa que rehace sus cifras |
| `data/experiment/b54_catalogo_v3/` | 1 | Cierre de los imports: lo importa el código de `src/comun/`, `src/extractor/` |
| `data/experiment/banco_mcp/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/`, `data/experiment/banco_mcp/adaptador/`, `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/aislamiento/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/mcp_vector/`, `data/experiment/banco_mcp/n6/`, `data/experiment/banco_mcp/paralelo/`, `data/experiment/banco_mcp/smoke/`, `ejemplos/`, `scripts/` |
| `data/experiment/banco_mcp/a2_1/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `data/experiment/banco_mcp/paralelo/`; 1 dato(s) chico(s) |
| `data/experiment/banco_mcp/adaptador/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/`, `data/experiment/banco_mcp/smoke/` |
| `data/experiment/banco_mcp/agentes/` | 8 | Lanzador de agentes y su entorno limpio; 1 dato(s) chico(s); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/aislamiento/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/` |
| `data/experiment/banco_mcp/b63/` | 87 | B6.3: corrida de evaluación (código y resultados agregados; las preguntas, las respuestas y los veredictos están en `evaluacion/`) |
| `data/experiment/banco_mcp/b64/` | 54 | B6.4: análisis confirmatorio y exactitud de cita (código y resultados agregados; las preguntas, las respuestas y los veredictos están en `evaluacion/`) |
| `data/experiment/banco_mcp/coincidencias_con_el_grafo/` | 15 | Scripts que sostienen la declaración de las coincidencias del grafo con criterios (`docs/formato_del_grafo.md`) |
| `data/experiment/banco_mcp/gate/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/adaptador/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/smoke/`, `scripts/` |
| `data/experiment/banco_mcp/mcp_kg/` | 24 | Servidor MCP del grafo (navegación por el grafo); suma el manifiesto de referencia del índice de puntos y la matriz densa de ese índice |
| `data/experiment/banco_mcp/mcp_vector/` | 13 | Servidor MCP de recuperación por fragmentos (BM25, denso e híbrido; los índices se regeneran desde el corpus); suma lo del tramo de las instrucciones, los planes y la 6.3, y la matriz densa del índice denso con su manifiesto |
| `data/experiment/banco_mcp/n6/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/` |
| `data/experiment/banco_mcp/n7/` | 5 | Solo datos chicos; 1 dato(s) chico(s); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/n7c/` | 4 | Solo datos chicos; 1 dato(s) chico(s); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/paralelo/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/aislamiento/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/` |
| `data/experiment/banco_mcp/smoke/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/` |
| `data/experiment/catalogo_unico/` | 7 | Lo que lee `prompt_r2b.py`, y el catálogo de sujetos |
| `data/experiment/escalado_prep/` | 5 | Inventario y registro de la descarga del corpus |
| `data/experiment/esq/` | 23 | Cierre de los imports: lo importa el código de `data/experiment/b54_catalogo_v3/`, `src/comun/`, `src/extractor/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/esq_v3_miembros/` | 1 | Clases del esquema final |
| `data/experiment/ev2_corrida/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/ev2_reporte/`, `data/experiment/neo4j/`, `data/experiment/tanda0/` |
| `data/experiment/ev2_juez/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `scripts/`; 1 dato(s) chico(s) |
| `data/experiment/ev2_reporte/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/smoke/` |
| `data/experiment/evaluacion/` | 5 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/gate/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/ev2_corrida/`, `data/experiment/ev2_juez/`, `data/experiment/ev2_reporte/`, `data/experiment/exploracion/`, `data/experiment/mantenimiento/`, `data/experiment/neo4j/`, `data/experiment/tanda0/`, `ejemplos/`, `scripts/`, `src/comun/`, `src/extractor/`, `src/verificador/` |
| `data/experiment/exploracion/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/gate/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/ev2_corrida/`, `data/experiment/ev2_reporte/` |
| `data/experiment/grafo_v2/` | 7 | Cierre de los imports: lo importa el código de `data/experiment/esq/`, `data/experiment/tanda0/`, `scripts/`, `src/comun/`, `src/ensamblado/`, `src/extractor/`, `src/validador/`; 1 dato(s) chico(s) |
| `data/experiment/job_actualizacion/` | 20 | Trabajo de actualización, con su corrida del 7 de septiembre de 2026 y sus sondas |
| `data/experiment/mantenimiento/` | 26 | Control del sitio, empalme y medición de las citas a comunicaciones |
| `data/experiment/neo4j/` | 11 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/mcp_vector/`, `data/experiment/banco_mcp/smoke/`, `scripts/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/prompt_r2/` | 3 | Cierre de los imports: lo importa el código de `src/extractor/`, `src/verificador/` |
| `data/experiment/pyd_r2/` | 5 | El esquema final, `code/modelos_r2.py`, con sus archivos generados y su política de campos; lo importa el código de `scripts/`, `src/ensamblado/`, `src/extractor/`, `src/validador/` |
| `data/experiment/reaplicacion_unica/` | 17 | El grafo evaluado, con su sello y los archivos de su ensamblado; en `G_catalogo_resolucion_ureapl/`, el catálogo y los archivos de la resolución de sujetos que lee la suite de regresión |
| `data/experiment/reextraccion_v2/` | 3 | Los manifiestos de corpus de las 3 tandas. El código que estaba en esta carpeta se mudó a `src/` (ver «La mudanza a `src/`»), y sus datos no se publican |
| `data/experiment/tanda0/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/mcp_kg/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/tanda_final/` | 4 | Planes derivados de la tanda final, y el armado y el manifiesto de la E0 acumulada |
| `data/experiment/tripletas_v/` | 4 | Instrucciones sin casos del juez de las tripletas; la entrada del análisis de las 400 tripletas y el programa que calcula sus intervalos, los 2 que usa `evaluacion_contenido/reproducir_contenido.py` |
| `docs/` | 46 | Pre-registros, enmiendas, los 3 laudos que usan los planes, el formato del grafo y estas notas; suma lo del tramo de las instrucciones, los planes, la 6.3 y las instrucciones completas de los 2 jueces del contenido del grafo |
| `ejemplos/` | 2 | Los 2 programas de ejemplo |
| `fuera_del_repo/b63_etapa1/scripts/` | 2 | Las funciones de P1 que carga el análisis de B6.3, tal cual |
| `preregistros/` | 1 | sha256 de los pre-registros, las enmiendas y las adendas |
| `reconstruccion/` | 5 | La guía para reconstruir los índices desde los PDF y arrancar los servidores, con sus 4 programas |
| `scripts/` | 12 | Scripts de verificación y de indicadores |
| `src/segmentacion/` | 9 | La segmentación (E0), con sus pruebas. Estaba en `data/experiment/reextraccion_v2/e0_chunking/`, carpeta que ya no se publica |
| `src/extractor/` | 15 | El extractor (E1), con su perfil, lo que arma sus instrucciones y sus pruebas. Estaba en `data/experiment/reextraccion_v2/e1_extractor/`, carpeta que ya no se publica |
| `src/validador/` | 3 | El validador: `validador_e1.py`, que estaba en `data/experiment/reextraccion_v2/e1_extractor/` (carpeta que ya no se publica), y `validador_r2.py` y `reglas_comparacion.py`, que estaban en `data/experiment/pyd_r2/code/` |
| `src/verificador/` | 14 | El verificador (E3), con sus pruebas. Estaba en `data/experiment/reextraccion_v2/e3_verificador/`, carpeta que ya no se publica |
| `src/ensamblado/` | 16 | El ensamblado de cada documento (E2) y del corpus, con sus pruebas. Estaba en `data/experiment/reextraccion_v2/e2_reduce/` y `data/experiment/reextraccion_v2/corpus_v2/`, carpetas que ya no se publican |
| `src/comun/` | 4 | Lo que usan 2 piezas o más: `manifiesto_corpus.py` y sus 3 pruebas. Estaba en la raíz de `data/experiment/reextraccion_v2/` |

La columna cuenta todos los archivos del árbol bajo cada carpeta, y suma 547, los de `SHA256SUMS` más ese archivo. En «Qué hay», «lo importa el código de» nombra las carpetas con código que importa algo de la carpeta en este árbol.

## La mudanza a `src/`

El código de las 5 piezas del cap. 4 se mudó a `src/`, una carpeta por pieza:

- `data/experiment/reextraccion_v2/e0_chunking/` (9 archivos) va a `src/segmentacion/`.
- `data/experiment/reextraccion_v2/e1_extractor/` (15), salvo `validador_e1.py`, va a `src/extractor/`.
- `validador_e1.py`, y `validador_r2.py` y `reglas_comparacion.py` de `data/experiment/pyd_r2/code/`, van a `src/validador/`.
- `data/experiment/reextraccion_v2/e3_verificador/` (14) va a `src/verificador/`.
- `data/experiment/reextraccion_v2/e2_reduce/` y `data/experiment/reextraccion_v2/corpus_v2/` (16) van a `src/ensamblado/`.
- Los 4 archivos de la raíz de `data/experiment/reextraccion_v2/`, que usan 2 piezas o más, van a `src/comun/`.

Cada archivo conserva su nombre y va directo a la carpeta de su pieza. Un import de una pieza a otra apunta a la carpeta de la otra pieza.

Los datos no se mudaron. El código de cada pieza los busca donde estaban, en `data/experiment/reextraccion_v2/` y en sus carpetas `e0_chunking/`, `e1_extractor/`, `e2_reduce/`, `e3_verificador/` y `corpus_v2/`. De esos datos, el repositorio trae solo los 3 manifiestos de corpus de `data/experiment/reextraccion_v2/manifiestos/`: las salidas de las piezas son salidas intermedias y no se publican, y `corpus_v2/` quedó sin archivos.

El esquema se queda en `data/experiment/pyd_r2/`, con sus 5 archivos, porque `code/modelos_r2.py` arma la raíz del repositorio desde su carpeta y está sellado en `generados/manifest_generados_r2.json` (ver «Archivos sellados»).

Los 9 archivos del catálogo de la resolución de sujetos estaban en `data/experiment/reaplicacion_unica/paquete_UREAPL/`, con el prefijo `ureapl_claves__G_catalogo_resolucion_ureapl__`. Se mudaron sin el prefijo a `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/`, de donde los lee la suite de regresión con `--catalogo` y `--generados-resolucion` (ver «Lo que lee la suite de regresión y no se publica»).

Los comentarios y los docstrings del código que nombran una ruta vieja no se cambiaron. Esta tabla da la ruta nueva de cada archivo que se mudó:

| Ruta vieja | Ruta nueva |
|---|---|
| `data/experiment/pyd_r2/code/reglas_comparacion.py` | `src/validador/reglas_comparacion.py` |
| `data/experiment/pyd_r2/code/validador_r2.py` | `src/validador/validador_r2.py` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__ampliaciones_resolucion_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/ampliaciones_resolucion_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__catalogo_resolucion_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/catalogo_resolucion_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__catalogo_suite_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/catalogo_suite_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__entrada_esqueleto_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/entrada_esqueleto_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__ids_s19_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/ids_s19_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__indice_e4_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/indice_e4_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__labels_e2_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/labels_e2_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__manifest_generados_resolucion_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/manifest_generados_resolucion_r2.json` |
| `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_claves__G_catalogo_resolucion_ureapl__rol_por_to_r2.json` | `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/rol_por_to_r2.json` |
| `data/experiment/reextraccion_v2/corpus_v2/ensamblar_corpus.py` | `src/ensamblado/ensamblar_corpus.py` |
| `data/experiment/reextraccion_v2/corpus_v2/ensamblar_r1.py` | `src/ensamblado/ensamblar_r1.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_cola_flaggeada.py` | `src/ensamblado/r1_cola_flaggeada.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_comun.py` | `src/ensamblado/r1_comun.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_e4.py` | `src/ensamblado/r1_e4.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_e5_esqueleto.py` | `src/ensamblado/r1_e5_esqueleto.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_invariantes.py` | `src/ensamblado/r1_invariantes.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_provenance.py` | `src/ensamblado/r1_provenance.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_referencias.py` | `src/ensamblado/r1_referencias.py` |
| `data/experiment/reextraccion_v2/corpus_v2/r1_tests.py` | `src/ensamblado/r1_tests.py` |
| `data/experiment/reextraccion_v2/corpus_v2/reextraccion_dirigida.py` | `src/ensamblado/reextraccion_dirigida.py` |
| `data/experiment/reextraccion_v2/corpus_v2/runner_corpus.py` | `src/ensamblado/runner_corpus.py` |
| `data/experiment/reextraccion_v2/corpus_v2/selftest_corpus.py` | `src/ensamblado/selftest_corpus.py` |
| `data/experiment/reextraccion_v2/e0_chunking/correr_e0.py` | `src/segmentacion/correr_e0.py` |
| `data/experiment/reextraccion_v2/e0_chunking/e0_lib.py` | `src/segmentacion/e0_lib.py` |
| `data/experiment/reextraccion_v2/e0_chunking/e0_tablas.py` | `src/segmentacion/e0_tablas.py` |
| `data/experiment/reextraccion_v2/e0_chunking/healthcheck_e0.py` | `src/segmentacion/healthcheck_e0.py` |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b52.py` | `src/segmentacion/selftest_b52.py` |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b581.py` | `src/segmentacion/selftest_b581.py` |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b582.py` | `src/segmentacion/selftest_b582.py` |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b583.py` | `src/segmentacion/selftest_b583.py` |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_e0.py` | `src/segmentacion/selftest_e0.py` |
| `data/experiment/reextraccion_v2/e1_extractor/cliente_e1.py` | `src/extractor/cliente_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/comun_e1.py` | `src/extractor/comun_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/estimacion_e1.py` | `src/extractor/estimacion_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/perfil_e1.py` | `src/extractor/perfil_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/prompt_e1.py` | `src/extractor/prompt_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/prompt_r2b.py` | `src/extractor/prompt_r2b.py` |
| `data/experiment/reextraccion_v2/e1_extractor/prompt_r2b_parche_p3b.json` | `src/extractor/prompt_r2b_parche_p3b.json` |
| `data/experiment/reextraccion_v2/e1_extractor/prompt_r2b_parche_p3c.json` | `src/extractor/prompt_r2b_parche_p3c.json` |
| `data/experiment/reextraccion_v2/e1_extractor/prompt_r2b_reemplazos.json` | `src/extractor/prompt_r2b_reemplazos.json` |
| `data/experiment/reextraccion_v2/e1_extractor/runner_faseB_e1.py` | `src/extractor/runner_faseB_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/runner_faseB_e1_enm01.py` | `src/extractor/runner_faseB_e1_enm01.py` |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_canal_abierto_e1.py` | `src/extractor/selftest_canal_abierto_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_e1.py` | `src/extractor/selftest_e1.py` |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_prompt_r2b.py` | `src/extractor/selftest_prompt_r2b.py` |
| `data/experiment/reextraccion_v2/e1_extractor/tablas_residuales_forzadas_r2b.json` | `src/extractor/tablas_residuales_forzadas_r2b.json` |
| `data/experiment/reextraccion_v2/e1_extractor/validador_e1.py` | `src/validador/validador_e1.py` |
| `data/experiment/reextraccion_v2/e2_reduce/correr_e2.py` | `src/ensamblado/correr_e2.py` |
| `data/experiment/reextraccion_v2/e2_reduce/e2_lib.py` | `src/ensamblado/e2_lib.py` |
| `data/experiment/reextraccion_v2/e2_reduce/selftest_e2.py` | `src/ensamblado/selftest_e2.py` |
| `data/experiment/reextraccion_v2/e3_verificador/analisis_enm01.py` | `src/verificador/analisis_enm01.py` |
| `data/experiment/reextraccion_v2/e3_verificador/calibradores_e3.py` | `src/verificador/calibradores_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/cliente_e3.py` | `src/verificador/cliente_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/comun_e3.py` | `src/verificador/comun_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/estimacion_e3.py` | `src/verificador/estimacion_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/estimacion_enm01.py` | `src/verificador/estimacion_enm01.py` |
| `data/experiment/reextraccion_v2/e3_verificador/generar_fixtures_e3.py` | `src/verificador/generar_fixtures_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/prompt_e3.py` | `src/verificador/prompt_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/ratchet_e3.py` | `src/verificador/ratchet_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/recompute_politica_enm01.py` | `src/verificador/recompute_politica_enm01.py` |
| `data/experiment/reextraccion_v2/e3_verificador/runner_faseB_e3.py` | `src/verificador/runner_faseB_e3.py` |
| `data/experiment/reextraccion_v2/e3_verificador/runner_faseB_e3_enm01.py` | `src/verificador/runner_faseB_e3_enm01.py` |
| `data/experiment/reextraccion_v2/e3_verificador/runner_remedicion_citas.py` | `src/verificador/runner_remedicion_citas.py` |
| `data/experiment/reextraccion_v2/e3_verificador/selftest_e3.py` | `src/verificador/selftest_e3.py` |
| `data/experiment/reextraccion_v2/manifiesto_corpus.py` | `src/comun/manifiesto_corpus.py` |
| `data/experiment/reextraccion_v2/selftest_cablev3.py` | `src/comun/selftest_cablev3.py` |
| `data/experiment/reextraccion_v2/selftest_manifiesto.py` | `src/comun/selftest_manifiesto.py` |
| `data/experiment/reextraccion_v2/selftest_ub53.py` | `src/comun/selftest_ub53.py` |

## Las ediciones

Del código que se mudó o que lo usa se cambió solo lo que hacía falta para que corra desde su lugar nuevo: los import y las rutas que se abren. Además, la contraseña de Neo4j dejó de tener un valor por defecto (ver «La variable `NEO4J_PASSWORD`»), y la prueba T5 de la suite da `no_aplicable` sin su muestra. Así, ese código ya no es idéntico al que corrió en la tesis. Ningún archivo sellado se editó.

Son 131 renglones en 49 archivos, con los números de renglón de este árbol:

| Archivo | Renglones | Qué cambió |
|---|---|---|
| `data/experiment/esq/code/prompt_esq3b.py` | 74 | busca los módulos de las piezas en sus carpetas de `src/` |
| `data/experiment/mantenimiento/code/empalme_subgrafo.py` | 126 | busca los módulos de las piezas en sus carpetas de `src/` |
| `data/experiment/mantenimiento/code/selftest_clave_cache.py` | 106, 162-163, 189-190, 196, 1509, 1511, 1513, 1517, 1519 | busca los módulos de las piezas en sus carpetas de `src/`; abre o corre por su ruta archivos que se mudaron |
| `data/experiment/mantenimiento/control_sitio/control_sitio.py` | 62 | busca los módulos de las piezas en sus carpetas de `src/` |
| `data/experiment/neo4j/README.md` | 38, 42 | usa la variable `NEO4J_PASSWORD` en lugar de un valor |
| `data/experiment/neo4j/conexion.py` | 9, 24, 29-31 | toma `NEO4J_PASSWORD` sin valor por defecto, y `abrir_driver()` frena con un mensaje si falta |
| `data/experiment/neo4j/docker-compose.yml` | 25, 40, 51 | usa la variable `NEO4J_PASSWORD` en lugar de un valor |
| `data/experiment/prompt_r2/p3b/mensaje_p3b_borrador.py` | 40-41 | busca los módulos de las piezas en sus carpetas de `src/` |
| `data/experiment/prompt_r2/p3c/mensaje_p3c_borrador.py` | 34-35 | busca los módulos de las piezas en sus carpetas de `src/` |
| `data/experiment/tanda0/code/ensamblar_tanda0.py` | 84-85, 971 | busca los módulos de las piezas en sus carpetas de `src/` y abre `tablas_residuales_forzadas_r2b.json` en `src/extractor/` |
| `ejemplos/arrancar_servidores.py` | 46-47 | les pasa a los servidores `NEO4J_PASSWORD` de su propio entorno, si está |
| `reconstruccion/LEEME.md` | 287, 290 | la guía pide elegir la contraseña de Neo4j, exportarla como `NEO4J_PASSWORD` y ponerla antes del primer arranque |
| `reconstruccion/correr_e0_sin_roles.py` | 24, 34-35 | busca los módulos de las piezas en sus carpetas de `src/` |
| `scripts/metricas_intrinsecas.py` | 629 | busca los módulos de las piezas en sus carpetas de `src/` |
| `scripts/regression_kg.py` | 113, 529-530, 541, 1254, 1344-1346 | busca el código del ensamblado en `src/ensamblado/` y el de `validador_r2.py` en `src/validador/`; si la muestra de T5 no está, T5 da `no_aplicable` (ver «Lo que lee la suite de regresión y no se publica») |
| `scripts/shapes_validator.py` | 220 | abre `reglas_comparacion.py` en `src/validador/`, adonde se mudó |
| `src/comun/manifiesto_corpus.py` | 37, 41 | busca sus datos en `data/experiment/reextraccion_v2/`, donde estaban; de ellos se publican solo los manifiestos de corpus; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/comun/selftest_cablev3.py` | 51, 53-55, 461 | busca sus datos en `data/experiment/reextraccion_v2/`, donde estaban; de ellos se publican solo los manifiestos de corpus; busca los módulos de las piezas en sus carpetas de `src/`; abre o corre por su ruta archivos que se mudaron |
| `src/comun/selftest_manifiesto.py` | 63-66, 186, 352, 443-446, 518 | busca sus datos en `data/experiment/reextraccion_v2/`, donde estaban; de ellos se publican solo los manifiestos de corpus; busca los módulos de las piezas en sus carpetas de `src/`; abre o corre por su ruta archivos que se mudaron |
| `src/comun/selftest_ub53.py` | 57-61 | busca sus datos en `data/experiment/reextraccion_v2/`, donde estaban; de ellos se publican solo los manifiestos de corpus; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/ensamblado/correr_e2.py` | 28 | busca sus datos en `data/experiment/reextraccion_v2/e2_reduce/`, donde estaban; esos datos no se publican; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/ensamblado/e2_lib.py` | 46 | busca sus datos en `data/experiment/reextraccion_v2/e2_reduce/`, donde estaban; esos datos no se publican |
| `src/ensamblado/ensamblar_corpus.py` | 59-60, 334 | busca sus datos en `data/experiment/reextraccion_v2/corpus_v2/`, donde estaban; esos datos no se publican; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/ensamblado/r1_comun.py` | 25, 27-28, 40-41 | busca sus datos en `data/experiment/reextraccion_v2/corpus_v2/`, donde estaban; esos datos no se publican; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/ensamblado/r1_e4.py` | 548-550 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/ensamblado/reextraccion_dirigida.py` | 49 | busca sus datos en `data/experiment/reextraccion_v2/corpus_v2/`, donde estaban; esos datos no se publican |
| `src/ensamblado/runner_corpus.py` | 63-66, 68-69, 1332 | busca sus datos en `data/experiment/reextraccion_v2/corpus_v2/`, donde estaban; esos datos no se publican; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/ensamblado/selftest_corpus.py` | 20, 24 | busca los módulos de las piezas en sus carpetas de `src/`, y escribe su salida en `data/experiment/reextraccion_v2/corpus_v2/`, donde la escribía y que no se publica |
| `src/extractor/comun_e1.py` | 21 | busca sus datos en `data/experiment/reextraccion_v2/e1_extractor/`, donde estaban; esos datos no se publican |
| `src/extractor/perfil_e1.py` | 62 | arma la raíz del repositorio desde su carpeta nueva |
| `src/extractor/prompt_r2b.py` | 57, 70 | arma la raíz del repositorio desde su carpeta nueva, y busca `candado_mensaje_r2b.json`, que no se publica, en `data/experiment/reextraccion_v2/e1_extractor/`, donde estaba |
| `src/extractor/runner_faseB_e1.py` | 38 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/extractor/runner_faseB_e1_enm01.py` | 37 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/extractor/selftest_canal_abierto_e1.py` | 46 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/extractor/selftest_e1.py` | 54, 422 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/extractor/selftest_prompt_r2b.py` | 57 | arma la raíz del repositorio desde su carpeta nueva |
| `src/segmentacion/correr_e0.py` | 53, 624, 1875, 1879 | busca sus datos en `data/experiment/reextraccion_v2/e0_chunking/`, donde estaban; esos datos no se publican; arma la raíz del repositorio desde su carpeta nueva; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/segmentacion/healthcheck_e0.py` | 75 | arma la raíz del repositorio desde su carpeta nueva |
| `src/segmentacion/selftest_b52.py` | 202 | arma la raíz del repositorio desde su carpeta nueva |
| `src/segmentacion/selftest_b581.py` | 391, 403 | arma la raíz del repositorio desde su carpeta nueva |
| `src/segmentacion/selftest_b582.py` | 155, 337, 352 | arma la raíz del repositorio desde su carpeta nueva |
| `src/segmentacion/selftest_b583.py` | 56 | arma la raíz del repositorio desde su carpeta nueva |
| `src/segmentacion/selftest_e0.py` | 387 | arma la raíz del repositorio desde su carpeta nueva |
| `src/validador/validador_e1.py` | 30-31, 112 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/validador/validador_r2.py` | 76-78, 81 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/verificador/comun_e3.py` | 30, 43-44 | busca sus datos en `data/experiment/reextraccion_v2/e3_verificador/`, donde estaban; esos datos no se publican; busca los módulos de las piezas en sus carpetas de `src/` |
| `src/verificador/prompt_e3.py` | 471 | busca su candado, que no se publica, en `data/experiment/reextraccion_v2/e3_verificador/`, donde estaba |
| `src/verificador/ratchet_e3.py` | 93, 123 | busca los módulos de las piezas en sus carpetas de `src/` |
| `src/verificador/selftest_e3.py` | 717 | arma la raíz del repositorio desde su carpeta nueva |

`data/experiment/tanda0/code/ensamblar_tanda0.py` cambió en `:84-85`, donde busca los módulos de las piezas, y en `:971`, la ruta de `tablas_residuales_forzadas_r2b.json`, que se mudó a `src/extractor/`. Con `--union-comunicaciones` (`:80`) lee un archivo de una medición que no se publica, así que esa opción no corre con este repositorio. Como el resto del programa necesita datos que tampoco se publican, `ensamblar_tanda0.py` no corre solo.

## Lo que salió

Salieron 339 archivos de la primera versión:

| Carpeta | Archivos | Qué eran |
|---|---:|---|
| `data/experiment/segmentacion_oficial_e0r2/` | 270 | La segmentación oficial de los Textos Ordenados en puntos (E0). Ningún programa que queda la abre al correr; la guía de `reconstruccion/` la rehace desde los PDF |
| `data/experiment/reaplicacion_unica/` | 21 | Copias de archivos del paquete de la reaplicación única que ningún archivo lee ni nombra, y un programa interno |
| `scripts/` | 13 | Scripts que ningún programa abre al correr y que no respaldan cifras de la tesis |
| `docs/` | 11 | Registros internos: laudos, adendas, mandatos, una fe de erratas y enmiendas de un diseño o de un laudo |
| `data/experiment/reextraccion_v2/` | 9 | La versión R0 de la reextracción (`r0/`), que la tesis no usa |
| `src/` | 7 | El código común de la primera versión, de la descarga del corpus y utilidades, que no usa ningún programa que queda |
| `data/experiment/mantenimiento/` | 5 | Una propuesta, un freno, una demostración y una medición interna que la tesis no cita |
| `data/experiment/med_desamb/` | 1 | Una herramienta interna de la revisión de la tesis, que ningún programa abre |
| `data/experiment/tanda0/` | 1 | Un programa que carga el grafo de la tanda 0, que no se publica |
| `tests/` | 1 | La prueba de ese código común |

Los 11 documentos de `docs/` que salieron siguen listados en `preregistros/FIRMAS.md`, con su huella. Su sha256 es este:

| Documento | Renglón de `preregistros/FIRMAS.md` | sha256 |
|---|---|---|
| `docs/adenda2_laudo_B5.5_cobertura.md` | `preregistros/FIRMAS.md:29` | `a08ef592439f70dcca610372ce2d0fa96539f37793a898a3aa250cdaf32b93e2` |
| `docs/adenda_laudo_B5.5_segmentacion_universal.md` | `preregistros/FIRMAS.md:30` | `4e528fab3c827e40a9e9fa69f06cc0f33310795c9d052da64944ac8b4003f259` |
| `docs/enmienda_01_diseno_reextraccion_v2.md` | `preregistros/FIRMAS.md:43` | `aaa940ac5e6faa20d157a17e484d6868a3759ced06d8d46506b924da00bfb707` |
| `docs/enmienda_laudo_B_guarda_ratchet_2026-10-03.md` | `preregistros/FIRMAS.md:45` | `7009d7d02f9d562eb924e7ab20254185757a354db7591fff231641eb3c154c61` |
| `docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md` | `preregistros/FIRMAS.md:50` | `b55cce7ee27c156dbfbd7410330c6bc4ed8858feb0ae0d22311c43c2fcd0b6d6` |
| `docs/fe_erratas_fecha_corpus_congelado.md` | `preregistros/FIRMAS.md:51` | `f1d977547ccaf063cf8c3d851b417ba77848c7d91fa497884a35d05b5194653e` |
| `docs/laudo_B5.5_alcance_corpus_y_catalogo.md` | `preregistros/FIRMAS.md:53` | `89591de0760f166d2ca1c16ccef7fed943d2490523b9df204d1dc4748d2d532c` |
| `docs/mandatos/UCOMP_E1_comparacion_chica_modelo.md` | `preregistros/FIRMAS.md:57` | `a03a484e4b665e0bef2fcb5e425af7b03ebdcb76d4a4b3b7494f20340253c0bc` |
| el que nombra ese renglón | `preregistros/FIRMAS.md:58` | `a2b83ec99eda42d8b4661b5418adc73cfd70fd6f47a648d75b12ffe2fab02378` |
| `docs/mandatos/UPREG_B63_preguntas_por_tipo.md` | `preregistros/FIRMAS.md:59` | `754a017e122143ddba058ddd39c35b6ab4601a8245c72ea4db372d7f79222ad1` |
| `docs/mandatos/UREAPL_reaplicacion_unica.md` | `preregistros/FIRMAS.md:60` | `b8ff123d4fe828b8b393a2a71d53ea545492f409fa23529d539bd876414acc25` |

Estos archivos del árbol nombran archivos que salieron. Los nombran como estaban en la primera versión; esos archivos no se publican:

| Archivo | Renglón | Archivos que salieron que nombra |
|---|---|---|
| `data/experiment/banco_mcp/mcp_kg/familias_nav.py` | 22 | `data/experiment/tanda0/code/cargar_neo4j_tanda0.py` |
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav.py` | 4 | `data/experiment/tanda0/code/cargar_neo4j_tanda0.py` |
| `data/experiment/esq/enmienda2_L-ESQ-R2_remite_a_2026-10-02.md` | 158 | 1 archivo cuyo nombre no se reproduce aquí |
| `data/experiment/job_actualizacion/code/correr_job.py` | 61 | `src/scraper/download_bcra.py` |
| `data/experiment/job_actualizacion/code/lib_job.py` | 31 | `docs/fe_erratas_fecha_corpus_congelado.md` |
| `data/experiment/job_actualizacion/code/reporte_corrida.py` | 224 | `docs/fe_erratas_fecha_corpus_congelado.md` |
| `data/experiment/job_actualizacion/corridas/2026-09-07/reporte.md` | 106 | `docs/fe_erratas_fecha_corpus_congelado.md` |
| `data/experiment/job_actualizacion/diseno_job_actualizacion.md` | 108 | `src/scraper/download_bcra.py` |
| `data/experiment/job_actualizacion/diseno_job_actualizacion.md` | 572 | `docs/laudo_B5.5_alcance_corpus_y_catalogo.md` |
| `data/experiment/mantenimiento/procedimiento_empalme.md` | 128 | `data/experiment/mantenimiento/demo_empalme_renumeracion.json` |
| `data/experiment/mantenimiento/procedimiento_empalme.md` | 228 | `data/experiment/mantenimiento/demo_empalme_renumeracion.json` |
| `data/experiment/mantenimiento/procedimiento_empalme.md` | 281 | `data/experiment/mantenimiento/citas_comunicaciones_2.json` |
| `data/experiment/mantenimiento/procedimiento_empalme.md` | 301 | `data/experiment/mantenimiento/citas_comunicaciones_2.json` |
| `data/experiment/mantenimiento/procedimiento_empalme.md` | 317 | `data/experiment/mantenimiento/citas_comunicaciones_2.json`, `data/experiment/mantenimiento/code/medir_citas_comunicaciones_2.py` |
| `data/experiment/mantenimiento/procedimiento_empalme.md` | 320 | `data/experiment/mantenimiento/citas_comunicaciones_2.json` |
| `data/experiment/mantenimiento/tabla_reprocesamiento.md` | 9 | `data/experiment/mantenimiento/freno_utabla_reproc.md` |
| `data/experiment/mantenimiento/tabla_reprocesamiento.md` | 176 | 1 archivo cuyo nombre no se reproduce aquí |
| `data/experiment/mantenimiento/tabla_reprocesamiento.md` | 548 | 1 archivo cuyo nombre no se reproduce aquí |
| `data/experiment/tanda0/code/ensamblar_tanda0.py` | 80 | 1 archivo cuyo nombre no se reproduce aquí |
| `docs/enmienda2_protocolo_entre_tandas_2026-10-04_catalogo.md` | 68 | `data/experiment/mantenimiento/freno_utabla_reproc.md` |
| `docs/enmienda3_protocolo_entre_tandas_2026-10-04_clases_de_reprocesamiento.md` | 18 | `data/experiment/mantenimiento/freno_utabla_reproc.md` |
| `docs/enmienda8_protocolo_entre_tandas_2026-10-15_calendario_hacia_B6.3.md` | 34 | `docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md` |
| `docs/enmienda_preregistro_tanda0_2026-09-27_observacion12.md` | 132 | 1 archivo cuyo nombre no se reproduce aquí |
| `docs/preregistro_B6_3_evaluacion_final.md` | 7 | `docs/mandatos/UPREG_B63_preguntas_por_tipo.md` |
| `docs/preregistro_evaluacion_tripletas.md` | 135 | `docs/mandatos/UCOMP_E1_comparacion_chica_modelo.md` |
| `docs/preregistro_tanda1.md` | 158 | 1 archivo cuyo nombre no se reproduce aquí |
| `docs/protocolo_entre_tandas.md` | 61 | 1 archivo cuyo nombre no se reproduce aquí |
| `docs/protocolo_entre_tandas.md` | 432 | `docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md` |
| `preregistros/FIRMAS.md` | 29 | `docs/adenda2_laudo_B5.5_cobertura.md` |
| `preregistros/FIRMAS.md` | 30 | `docs/adenda_laudo_B5.5_segmentacion_universal.md` |
| `preregistros/FIRMAS.md` | 43 | `docs/enmienda_01_diseno_reextraccion_v2.md` |
| `preregistros/FIRMAS.md` | 45 | `docs/enmienda_laudo_B_guarda_ratchet_2026-10-03.md` |
| `preregistros/FIRMAS.md` | 50 | `docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md` |
| `preregistros/FIRMAS.md` | 51 | `docs/fe_erratas_fecha_corpus_congelado.md` |
| `preregistros/FIRMAS.md` | 53 | `docs/laudo_B5.5_alcance_corpus_y_catalogo.md` |
| `preregistros/FIRMAS.md` | 57 | `docs/mandatos/UCOMP_E1_comparacion_chica_modelo.md` |
| `preregistros/FIRMAS.md` | 58 | 1 archivo cuyo nombre no se reproduce aquí |
| `preregistros/FIRMAS.md` | 59 | `docs/mandatos/UPREG_B63_preguntas_por_tipo.md` |
| `preregistros/FIRMAS.md` | 60 | `docs/mandatos/UREAPL_reaplicacion_unica.md` |
| `preregistros/FIRMAS.md` | 83 | `docs/adenda2_laudo_B5.5_cobertura.md` |
| `preregistros/FIRMAS.md` | 84 | `docs/adenda_laudo_B5.5_segmentacion_universal.md` |
| `preregistros/FIRMAS.md` | 155 | `docs/adenda_laudo_B5.5_segmentacion_universal.md`, `docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md` |
| `preregistros/FIRMAS.md` | 163 | `docs/enmiendas_adendas_1_y_2_laudo_B5.5_2026-10-04.md` |
| `scripts/regression_kg.py` | 87 | `scripts/selftest_regression_kg.py` |
| `scripts/remisiones.py` | 10 | 1 archivo cuyo nombre no se reproduce aquí |
| `src/segmentacion/e0_lib.py` | 48 | `docs/enmienda_01_diseno_reextraccion_v2.md` |
| `src/segmentacion/selftest_e0.py` | 1906 | 1 archivo cuyo nombre no se reproduce aquí |
| `src/segmentacion/selftest_e0.py` | 1907 | 1 archivo cuyo nombre no se reproduce aquí |
| `src/verificador/ratchet_e3.py` | 55 | `docs/enmienda_laudo_B_guarda_ratchet_2026-10-03.md` |

## El cierre de los imports

El código que va tiene que importar completo. A los archivos de código de las etapas publicadas se agregaron los
módulos del repo de la tesis que importan, y los que importan esos, hasta que no apareció ninguno nuevo (análisis
estático de los `import`; cada módulo se resuelve como lo resuelve quien lo importa: su carpeta, sus
`sys.path.insert` y la raíz del repo). Entraron 56 archivos. Cada uno pasó los mismos controles que el
resto (fuga del gold, nombres y rutas), salvo los de esta tabla, que no van; los archivos que los importan no corren:

| Archivo que no va | Por qué | Lo importan |
|---|---|---|
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/cifras_lectura_S1quater.py` | fuga del gold: un criterio del gold (no de B6.3, B6.4 ni EV2), igual por espacios y por palabras | los 2 archivos que lo importaban salieron en esta versión |

En la primera versión, 4 programas de `data/experiment/reaplicacion_unica/paquete_UREAPL/` importaban `muestra_memoria`, un módulo que no tiene archivo en el repo de la tesis. Esos 4 programas salieron en esta versión.

El código de `evaluacion_contenido/codigo/` no pasó por este cierre. Importa 14 módulos que no se publican, de las corridas de los jueces y de la lectura de la autora, así que no corre solo. `evaluacion_contenido/reproducir_contenido.py` lo carga con su sha256 y pone en lugar de esos módulos rellenos vacíos que ninguna cifra usa.

`requirements.txt` lleva los paquetes de terceros, con las versiones del `.venv`.

## Python

La tesis corrió con dos intérpretes. El código que llama a `.venv/bin/python` (los agentes, los servidores MCP y lo que corre con
ellos) usó Python 3.10.13, con los paquetes de `requirements.txt`. Los comandos que usan `BCRA_KG_PYTHON` o `python3` usaron el
`python3` del sistema, que hoy es 3.12.13. Tres archivos usan sintaxis de Python 3.12 y no corren con 3.10:

- `data/experiment/banco_mcp/b63/analisis/at/at2_bis/controles_salida_at2_bis.py`
- `data/experiment/banco_mcp/b63/analisis/at/at2_bis/controles_salida_at2_bis_pasada1.py`
- `scripts/ucita2_indicadores.py`

`torch`, `transformers` y `sentence-transformers` tienen las versiones de `data/experiment/banco_mcp/requirements_vector.txt`, que va tal cual. Su venv no se
publica.

## Datos chicos

No son gold y hacen falta para el código y sus pruebas. Pasaron los mismos controles que el resto y van tal cual:

| Archivo |
|---|
| `data/experiment/banco_mcp/a2_1/config_agentes_a2_1.json` |
| `data/experiment/banco_mcp/agentes/config_agentes.json` |
| `data/experiment/banco_mcp/n7/config_mcp_kg_n7_evaluado.json` |
| `data/experiment/banco_mcp/n7c/config_mcp_kg_n7c_evaluado.json` |
| `data/experiment/ev2_juez/prompt_juez_v1.md` |
| `data/experiment/grafo_v2/esquema_v2_clases.json` |

`data/experiment/banco_mcp/agentes/config_credenciales.json` no se publica.

## Las funciones de P1 de B6.3

`analizar_b63.py` carga dos scripts de `b63_etapa1/scripts/`, dentro de la carpeta `--etapa1` que recibe, y verifica su
sha256. Van en `fuera_del_repo/b63_etapa1/scripts/`, que es donde los encuentran los comandos del análisis con el valor
por defecto de `BCRA_KG_FUERA_DEL_REPO`:

| Archivo | sha256 (el que espera el código) |
|---|---|
| `fuera_del_repo/b63_etapa1/scripts/proporciones_P1.py` | `9db5a4af13e72c0b275a4dac090b9057bcbcc4ad85ae8b56afc5516a6d7f6711` |
| `fuera_del_repo/b63_etapa1/scripts/sensibilidad_P1.py` | `0bf82f60463730452ab522e7be2cf53f9e8419c99e9458b768030377fbe7937a` |

El análisis de B6.3 no corre solo con ellos: también pide la clasificación y la población de P1, la tabla del cruce y
otros archivos sellados que no se publican.

## Archivos sellados

Otro archivo del repositorio verifica el sha256 de estos 22, así que van tal cual, sin ninguna edición.
Sus renglones con rutas se conservan (`Path.home()`, la carpeta `INGENIERIA IA/TESIS/`, `~/`) y solo resuelven en una
máquina con esa forma:

| Archivo | Renglones con rutas |
|---|---:|
| `data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py` | 1 |
| `data/experiment/banco_mcp/b63/analisis/codigo/armar_adjudicacion_b63.py` | 1 |
| `data/experiment/banco_mcp/b63/control_36/sorteo/sortear_control_36_B63.py` | 1 |
| `data/experiment/banco_mcp/b63/control_36/sorteo/sortear_control_36_B63_v1.py` | 1 |
| `data/experiment/banco_mcp/b63/v2/b2/comun_b63.py` | 3 |
| `data/experiment/banco_mcp/b64/control_36/sorteo/sortear_control_36_B64.py` | 1 |
| `data/experiment/banco_mcp/b64/v1/comun_b63.py` | 5 |
| `data/experiment/banco_mcp/b64/v1/correr_b63.py` | 11 |
| `data/experiment/banco_mcp/comun_banco.py` | 1 |
| `data/experiment/tripletas_v/analisis/wilson_kish_tripletas_mesa.py` | 0 |
| `data/experiment/tripletas_v/juez_v3/entrada_analisis_400_T.json` | 0 |
| `evaluacion_contenido/codigo/tripletas_t_cob/codigo/acuerdo_juez_cob_t.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_t_cob/codigo/cifras_600_cob_t.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_t_cob/codigo/cifras_cob_t.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/codigo/analisis_gold_juez_v.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/codigo/juez_v.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/v2/codigo/analisis_T_v2.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/v2/codigo/juez_v2.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/v3/codigo/analisis_400_v3.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/v3/codigo/analisis_validacion_v3.py` | 0 |
| `evaluacion_contenido/codigo/tripletas_v_juez/v3/codigo/juez_v3.py` | 0 |
| `scripts/ucita2_indicadores_banco.py` | 2 |

`data/experiment/banco_mcp/agentes/lanzar_agente.py` va aparte: ningún archivo verifica su sha256, pero `docs/preregistro_A2_2_sistema_por_fragmentos.md:39` lo cita, así que también va
tal cual. 5 de sus renglones traen rutas del mismo tipo. `preregistros/FIRMAS.md` lista todos los archivos cuyo sha256 cita un pre-registro.

La mudanza movió sin cambiar un byte los archivos cuyo sha256 trae otro archivo del árbol. Son 5 de las piezas: `src/validador/reglas_comparacion.py`, en `data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/reporte_ensamblado_r2.json`; `src/extractor/prompt_r2b_parche_p3b.json`, en `src/extractor/prompt_r2b.py`; `src/extractor/prompt_r2b_parche_p3c.json`, en `data/experiment/reextraccion_v2/manifiestos/tanda0_10tos_r2b.json`, `data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json`, `data/experiment/reextraccion_v2/manifiestos/tanda_final_98tos_r2b.json`, `src/extractor/prompt_r2b.py`; `src/extractor/prompt_r2b_reemplazos.json`, en `src/extractor/prompt_r2b.py`; `src/extractor/tablas_residuales_forzadas_r2b.json`, en `data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/reporte_ensamblado_r2.json`, `data/experiment/reextraccion_v2/manifiestos/tanda0_10tos_r2b.json`, `data/experiment/reextraccion_v2/manifiestos/tanda1_20tos_r2b.json`, `data/experiment/reextraccion_v2/manifiestos/tanda_final_98tos_r2b.json`, `src/extractor/prompt_r2b.py`. Y son 8 de los 9 del catálogo de la resolución de sujetos, cuyo sha256 trae `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/manifest_generados_resolucion_r2.json` y, de algunos, también los archivos del ensamblado del grafo evaluado. `data/experiment/pyd_r2/code/modelos_r2.py`, sellado en `data/experiment/pyd_r2/generados/manifest_generados_r2.json`, se quedó en su carpeta.

## Lo que citan los pre-registros y no se publica

| Renglón | Causa |
|---|---|
| `docs/preregistro_tanda0.md:174` | datos que no se publican: falta data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json |
| `docs/preregistro_tanda0.md:625` | datos que no se publican: falta data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json |

## Rutas y variables de entorno

Salvo lo que declara esta sección, el código no nombra ninguna carpeta de la máquina en que se escribió. Lo declarado: los archivos sellados y
`lanzar_agente.py`, que van tal cual, y renglones de otros archivos (61, en 38 archivos, en la primera versión) que nombran `hoja_de_ruta_tanda1_mesa`, `scratchpads`,
un id de sesión o `.claude`: carpetas y sesiones de trabajo de la tesis, y la carpeta de configuración de Claude Code. Se conservan como
corrieron, sobre todo en los scripts de `coincidencias_con_el_grafo/`, y como los citan los pre-registros. Esas carpetas y sesiones no se publican: sus rutas
no resuelven en otra máquina.

Lo que está en el repo se ubica relativo a la
raíz del repo (desde `__file__` en Python y desde `${0:A:h…}` en los comandos zsh); los entornos virtuales, en
`venvs/` bajo la raíz. Lo que la tesis guarda fuera del repo se ubica con una variable de entorno:

| Variable | Valor por defecto | Para qué |
|---|---|---|
| `BCRA_KG_FUERA_DEL_REPO` | `<raíz del repo>/fuera_del_repo` | la carpeta de lo que la tesis guarda fuera del repo: sesiones de los agentes, salidas de las corridas, índices, lecturas ciegas, originales sin enmascarar y el material de la evaluación. Nada de eso se publica; el código la usa para leer y escribir ahí |
| `BCRA_KG_PYTHON` | `python3` | el intérprete con que los comandos zsh corren los scripts de Python |
| `NEO4J_PASSWORD` | ninguno: hay que exportarla | la contraseña de Neo4j, para lo que abre el grafo en Neo4j (ver «La variable `NEO4J_PASSWORD`») |

Quedan usos de la carpeta personal de quien corre el código que no nombran ninguna máquina: enmascararla como `$HOME`
en los registros, pasarla a un subproceso y expandir una ruta que declara quien corre.

## La variable `NEO4J_PASSWORD`

`data/experiment/neo4j/conexion.py` toma la contraseña de Neo4j de la variable `NEO4J_PASSWORD`, que no tiene valor por defecto (`data/experiment/neo4j/conexion.py:24`). Al importarse no pide nada: `abrir_driver()` frena con un mensaje que dice cómo exportarla si falta (`data/experiment/neo4j/conexion.py:29-31`). Ese módulo es el que usan los programas que abren el grafo en Neo4j: la carga del grafo y sus índices, `data/experiment/neo4j/test_equivalencia.py` y el servidor del grafo cuando usa Neo4j.

- La guía de `reconstruccion/LEEME.md` pide elegir la contraseña y exportarla (`reconstruccion/LEEME.md:287`), y la pone en Neo4j antes del primer arranque (`reconstruccion/LEEME.md:290`).
- `ejemplos/arrancar_servidores.py` les pasa a los 4 servidores la variable de su propio entorno, si está (`ejemplos/arrancar_servidores.py:46-47`).
- `data/experiment/neo4j/README.md` y `data/experiment/neo4j/docker-compose.yml` usan la variable en lugar de un valor.
- Los agentes del banco no la reciben: `data/experiment/banco_mcp/agentes/lanzar_agente.py` les pasa solo `PATH`, `HOME` y `NEO4J_URI` (`data/experiment/banco_mcp/agentes/lanzar_agente.py:180`), y el banco no se cambió. Para correr el banco con el grafo en Neo4j, hay que pasarles `NEO4J_PASSWORD`.

## Las pruebas

Las pruebas corren desde la raíz del repositorio con el intérprete de `requirements.txt`, en una ruta que no tenga nombres de configuración
(como `kg`). Las que necesitan el gold de otras evaluaciones, la API, otros datos que no se publican o el `.venv` de la tesis no corren con este repositorio solo; son
estas, con su causa:

| Prueba | Causa |
|---|---|
| `data/experiment/banco_mcp/agentes/selftest_lanzar_lote_paralelo_r5.py` | pide por argumento datos que no se publican: pide --entradas, --tmp, --resultado |
| `data/experiment/banco_mcp/agentes/selftest_metadata.py` | datos que no se publican: falta data/experiment/banco_mcp/agentes/precios_sellados.json |
| `data/experiment/banco_mcp/aislamiento/test_aislamiento.py` | necesita BANCO_VENV_VECTOR, el venv del servidor de fragmentos, que no se publica |
| `data/experiment/banco_mcp/b63/analisis/codigo/selftest_analizar_b63.py` | pide por argumento datos que no se publican: pide --clon, --proporciones, --mesa-cruce, --trabajo, --informe |
| `data/experiment/banco_mcp/b63/analisis/codigo/selftest_exactitud_de_cita_9_4_b63.py` | pide por argumento datos que no se publican: pide --clon, --ucita, --trabajo, --informe |
| `data/experiment/banco_mcp/b63/control_36/sorteo/probar_sorteo_control_36_B63_v1.py` | ya rota en la tesis: KeyError 'final' al correr su script, sin ningún archivo faltante; la prueba y el script van tal cual |
| `data/experiment/banco_mcp/b63/selftest_b63.py` | fallan 7 de sus 19 comprobaciones: le faltan el mundo de juguete de b63/seco/, a2_2/config_agentes_a2_2.json, a2_2/guardas_a2_2.zsh y el venv (BANCO_VENV_VECTOR), que no se publican |
| `data/experiment/banco_mcp/b63/v2/b1bis/selftest_b63.py` | datos que no se publican: falta data/experiment/banco_mcp/b63/v2/b1bis/formas_reales_b63.json |
| `data/experiment/banco_mcp/b63/v2/b2/selftest_b63.py` | datos que no se publican: falta data/experiment/banco_mcp/b63/v2/b2/formas_reales_b63.json |
| `data/experiment/banco_mcp/b63/v2/selftest_b63.py` | datos que no se publican: falta data/experiment/banco_mcp/b63/v2/formas_reales_b63.json |
| `data/experiment/banco_mcp/b64/analisis/codigo/selftest_analizar_b64.py` | pide por argumento datos que no se publican: pide --clon, --trabajo, --informe |
| `data/experiment/banco_mcp/b64/analisis/codigo/selftest_comandos_b64.py` | pide por argumento datos que no se publican: pide --comandos, --repo, --runner, --trabajo, --informe |
| `data/experiment/banco_mcp/b64/analisis/codigo/selftest_exactitud_de_cita_9_4_b64.py` | pide por argumento datos que no se publican: pide --clon, --ucita, --trabajo, --informe |
| `data/experiment/banco_mcp/b64/analisis/comandos/pruebas_H6.zsh` | pide el scratchpad del análisis con sus salidas, que no se publica |
| `data/experiment/banco_mcp/b64/analisis/esperado/probar_llenar_esperado_B64.py` | necesita la historia de git del repo de la tesis (la plantilla en HEAD) |
| `data/experiment/banco_mcp/b64/analisis/esperado/probar_llenar_esperado_real_sin_escribir_B64_mesa.py` | pide por argumento datos de la corrida real (lecturas, banco, manifiestos) |
| `data/experiment/banco_mcp/b64/control_36/cruce/probar_cruce_control_36_B64.py` | ya rota en la tesis: busca su material en control_36/control_36/material/, que no existe |
| `data/experiment/banco_mcp/b64/control_36/cruce/probar_cruce_sobre_la_v1_B64.py` | pide por argumento datos de la corrida real (lecturas, banco, manifiestos) |
| `data/experiment/banco_mcp/b64/control_36/material_v1/probar_fichas_y_sellador_control_36_B64.py` | necesita la historia de git del repo de la tesis (el script del sorteo en HEAD) |
| `data/experiment/banco_mcp/b64/control_36/material_v1/probar_lectura_real_sin_escribir_B64_mesa.py` | pide por argumento datos de la lectura real (carpeta de lectura, banco, manifiesto, clave) |
| `data/experiment/banco_mcp/b64/control_36/sorteo/probar_lectura_real_sin_sortear_B64_mesa.py` | pide por argumento datos de la corrida real (lecturas, banco, manifiestos) |
| `data/experiment/banco_mcp/b64/v1/selftest_b64.py` | datos que no se publican: falta data/experiment/banco_mcp/b63/v2/seco/preguntas_ventana_b63.json |
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav.py` | pide por argumento datos que no se publican: pide --config |
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_cand.py` | pide por argumento datos que no se publican: pide --config |
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_rel_amp.py` | necesita Python 3.12 y pide por argumento --trabajo y --salida; con el python3 del sistema (3.12.13) pasan 46 de sus 47 comprobaciones: la que falta pide el paquete mcp, que ese python3 no tiene |
| `data/experiment/banco_mcp/mcp_kg/selftest_indice_puntos_union.py` | pide por argumento datos que no se publican: pide --respaldo-n5, --out |
| `data/experiment/banco_mcp/mcp_kg/selftest_servidor_mcp_kg_nav_cand.py` | datos que no se publican: falta data/experiment/banco_mcp/n6/config_agentes_n6.json |
| `data/experiment/banco_mcp/mcp_kg/test_paridad_mcp_kg.py` | datos que no se publican: falta data/experiment/banco_mcp/mcp_kg/config_mcp_kg.json |
| `data/experiment/banco_mcp/mcp_vector/test_fragmentos_a2_1.py` | datos que no se publican: falta data/experiment/banco_mcp/mcp_vector/config_fragmentos_bm25_r2b.json |
| `data/experiment/banco_mcp/mcp_vector/test_fragmentos_f1.py` | datos que no se publican: falta data/experiment/tanda1/t3/acumulado/manifiestos/acumulado_30tos_r2b.json |
| `data/experiment/banco_mcp/mcp_vector/test_mcp_vector.py` | datos que no se publican: falta data/experiment/banco_mcp/mcp_vector/config_mcp_vector.json |
| `data/experiment/mantenimiento/code/selftest_clave_cache.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/mantenimiento/control_sitio/selftest_control_sitio.py` | datos que no se publican: falta data/experiment/job_actualizacion/corridas/2026-09-07/pdfs/capmin.pdf |
| `data/experiment/mantenimiento/control_sitio/selftest_correr_control.py` | datos que no se publican: falta data/experiment/job_actualizacion/corridas/2026-09-07/pdfs/snp_psp.pdf |
| `data/experiment/neo4j/test_equivalencia.py` | necesita Neo4j corriendo y la variable `NEO4J_PASSWORD`; esta corrida fue sin red ni Docker |
| `src/ensamblado/selftest_corpus.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_pro.json |
| `src/segmentacion/selftest_b52.py` | datos que no se publican: falta data/experiment/subset/TO_proteccion_usuarios_servicios_financieros_actual.pdf |
| `src/segmentacion/selftest_b581.py` | datos que no se publican: falta data/experiment/escalado_prep/pdfs/ri_ieccm.pdf |
| `src/segmentacion/selftest_b582.py` | datos que no se publican: falta data/experiment/escalado_prep/pdfs/ri_ieccm.pdf |
| `src/segmentacion/selftest_b583.py` | datos que no se publican: falta data/experiment/subset/TO_capitales_minimos_actual.pdf |
| `src/segmentacion/selftest_e0.py` | datos que no se publican: falta data/experiment/exploracion/mapa_territorio_quemado_5TOs_5sets.json |
| `src/extractor/selftest_canal_abierto_e1.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_cap.json |
| `src/extractor/selftest_e1.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_cap.json |
| `src/extractor/selftest_prompt_r2b.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e1_extractor/candado_mensaje_r2b.json |
| `src/ensamblado/selftest_e2.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e1_extractor/salida/faseB_pro/extracciones.jsonl |
| `src/verificador/selftest_e3.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `src/comun/selftest_cablev3.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `src/comun/selftest_manifiesto.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `src/comun/selftest_ub53.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |

En esta versión se corrieron de nuevo, sin red, antes y después de la mudanza, las 18 pruebas de las piezas, de `data/experiment/mantenimiento/` y de `data/experiment/neo4j/`: no corren, por la misma causa que da la tabla. `scripts/selftest_kg_gz.py` y `scripts/selftest_shapes_congelado.py` corren y pasan.

## Lo que leen el trabajo de actualización y el control del sitio y no se publica

`data/experiment/job_actualizacion/` y `data/experiment/mantenimiento/control_sitio/` leen archivos que no están en este repositorio, así que no corren con él solo. Son estos, por grupo:

| Qué | Dónde está en el repo de la tesis | Lo lee | Archivos |
|---|---|---|---:|
| El manifiesto de la descarga cruda | `data/raw/manifiesto.csv` | `data/experiment/job_actualizacion/code/lib_job.py:24` y `:55` | 1 |
| El manifiesto del conjunto de desarrollo | `data/experiment/reextraccion_v2/manifiestos/desarrollo_5tos.json` | `lib_job.py:23`, `:52` y `:155` | 1 |
| El inventario de unidades y la referencia del conjunto de desarrollo | `data/experiment/escalado_prep/inventario_unidades.csv` y `data/experiment/escalado_prep/referencia_subset.json` | `lib_job.py:135` y `:154` | 2 |
| El grafo sobre el que se mapean los cambios | `data/experiment/reextraccion_v2/corpus_v2/salida_r1/kg.json` | `data/experiment/job_actualizacion/code/adjudicar_deltas.py:35` | 1 |
| Los PDF de la línea base que no son de los 128 del grafo | `data/experiment/escalado_prep/pdfs/` | `lib_job.py:145`, `adjudicar_deltas.py:205` y `data/experiment/mantenimiento/control_sitio/control_sitio.py:272-273` | 29 |
| Los PDF de la corrida del 7 de septiembre de 2026 | `data/experiment/job_actualizacion/corridas/2026-09-07/pdfs/` | `adjudicar_deltas.py:274`, `data/experiment/job_actualizacion/code/verificar_corrida.py:77-81`, `control_sitio.py:274` y `data/experiment/mantenimiento/control_sitio/selftest_control_sitio.py:118` | 157 |
| Los PDF del control del 2 de octubre de 2026 | `data/experiment/mantenimiento/control_sitio/corridas/2026-10-02/pdfs/` | `control_sitio.py:498` y `data/experiment/mantenimiento/control_sitio/correr_control_sitio.py:321` | 19 |
| La E0 guardada, con la que el control clasifica lo que cambió | `data/experiment/reextraccion_v2/e0_chunking/salida_tanda0/` (10) y `data/experiment/segmentacion_84/b584_particion/` (147) | `correr_control_sitio.py:172` y `:174` | 157 |

Estos PDF no se redistribuyen (ver «El corpus» en el README).

## Lo que lee la suite de regresión y no se publica

`scripts/regression_kg.py` también lee `data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/omisiones.jsonl`, el registro de omisiones del ensamblado del grafo evaluado. Ese archivo no se publica porque trae tramos de la normativa de 1.000 caracteres o más fuera del grafo y notas de texto libre del extractor, que no se verifican. Sin él, la prueba LN-7 de la suite da «no aplicable» en este repositorio (`scripts/regression_kg.py:1866-1869`).

Tampoco se publica la muestra de 30 referencias inspeccionadas que usa la prueba T5, `data/experiment/reextraccion_v2/corpus_v2/salida_r1/referencias_muestra30_inspeccionada_A2.json` (`scripts/regression_kg.py:116-117`). Sin ella, T5 da «no aplicable», como LN-7 sin `omisiones.jsonl`: `scripts/regression_kg.py:529-530` no lee la muestra si el archivo no está, y `scripts/regression_kg.py:1344-1346` da el resultado. Con el archivo en su ruta, T5 corre como antes.

`scripts/regression_kg_esperado.json` trae una entrada para el grafo evaluado, `KG-ReaplicacionUnica-128-r2b-sincola`, con LN-7 y T5 en `no_aplicable` y una nota que dice por qué. La suite lee el catálogo y los archivos de la resolución de sujetos de `data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/`. Con este comando, después de `gunzip -k data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz`, da 0 regresiones en sus 68 controles: 45 en `resuelto`, 12 en `persiste` y 11 en `no_aplicable`, con `EJ-cla-5.1.1.1` en `resuelto`:

```bash
.venv/bin/python scripts/regression_kg.py --kg data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json --generacion 3 --catalogo data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl/catalogo_suite_r2.json --politica-cuarentena flaggeada --perfil r2 --sin-censos --manifiesto data/experiment/tanda_final/t3/acumulado/manifiestos/acumulado_128tos_r2b.json --generados-resolucion data/experiment/reaplicacion_unica/G_catalogo_resolucion_ureapl --esperado scripts/regression_kg_esperado.json
```

## Lo que ya estaba roto en el repo de la tesis

Estos problemas vienen del repo de la tesis y no se arreglaron, para que el código publicado sea el que corrió:

- `data/experiment/banco_mcp/b64/control_36/cruce/probar_cruce_control_36_B64.py` busca su material en `data/experiment/banco_mcp/b64/control_36/control_36/material/`, una ruta que no existe (el material está en `b64/control_36/material_v1/material/`).
- `data/experiment/banco_mcp/b63/control_36/sorteo/probar_sorteo_control_36_B63_v1.py` falla con `KeyError 'final'` al correr su script, y no le falta ningún archivo: la prueba y el script van tal cual de la tesis.

## Secretos

El código no trae ninguna clave. Nueve archivos traen cadenas que empiezan con `sk-ant-`, 11 en total, y ninguna es una clave
válida: son señuelos de prueba (los controles los usan para verificar que una clave no se filtre), un relleno para el modo de
arranque, que no llega a ningún servidor, y un ejemplo en un mensaje de error:

| Archivo | Renglones | Qué es |
|---|---|---|
| `data/experiment/banco_mcp/agentes/lanzar_agente.py` | 141, 157 | Relleno del modo `init`, con la base de la API en un puerto cerrado |
| `data/experiment/banco_mcp/agentes/selftest_entorno_limpio.py` | 87, 89 | Señuelos de la prueba del entorno limpio |
| `data/experiment/banco_mcp/aislamiento/testigo_aislamiento_b63_v2.py` | 105 | El relleno del modo `init`, para compararlo |
| `data/experiment/banco_mcp/b63/seco/herramientas_seco.py` | 105 | Señuelo con forma de clave, para un cliente de prueba sin red |
| `data/experiment/banco_mcp/b63/v2/seco/herramientas_b1.py` | 134 | Señuelo con forma de clave, para un cliente de prueba sin red |
| `data/experiment/banco_mcp/b63/v2/b1bis/seco/herramientas_b1bis.py` | 141 | Señuelo con forma de clave, para un cliente de prueba sin red |
| `data/experiment/banco_mcp/b63/v2/b2/seco/herramientas_b2.py` | 160 | Señuelo con forma de clave, para un cliente de prueba sin red |
| `data/experiment/banco_mcp/b63/v2/formas_error_b63.py` | 139 | Señuelo armado al correr, para un servidor de prueba local |
| `data/experiment/evaluacion/harness.py` | 655 | Ejemplo en un mensaje de error, con tres puntos en lugar de la clave |

## La guía de reconstrucción

La segmentación de `reconstruccion/` corre con `reconstruccion/correr_e0_sin_roles.py`, y no con `correr_e0.py --manifiesto`. Al
cargar el manifiesto de corpus, `correr_e0.py` compara el rol de alcance de cada Texto Ordenado con el catálogo del perfil r2b
(`src/comun/manifiesto_corpus.py:249-250`). Esa comparación arma el perfil r2b
(`manifiesto_corpus.py:161-162`), el perfil importa `prompt_r2b.py`
(`src/extractor/perfil_e1.py:210`), y `prompt_r2b.py` lee `candado_mensaje_r2b.json`
(`prompt_r2b.py:70` y `prompt_r2b.py:505`), que no se publica. `correr_e0_sin_roles.py` carga el mismo manifiesto con
`validar_roles=False` y llama a la misma función `correr()` de `src/segmentacion/correr_e0.py`, sin
copiar ni cambiar su código. Saltear la comparación no cambia la segmentación, porque `correr()` toma del manifiesto solo los
ids, los archivos, las rutas de los PDF, el mapa y el oráculo (`correr_e0.py:1650-1654`). Las demás validaciones del manifiesto
siguen, incluido el sha256 de cada PDF. Con Python 3.10.13, la segmentación reconstruida coincide en sus 640 archivos con el
armado de la E0 acumulada (`data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json`).
`manifiesto_corpus.py:193-195` reserva ese parámetro para pruebas sintéticas, y este es otro uso.

`requirements.txt` y `data/experiment/banco_mcp/requirements_vector.txt` no fijan la versión de la mayoría de los paquetes que
llegan como dependencia de otros, y pip instala de esos la más nueva compatible. En la prueba de la guía del 10 de noviembre de
2026 se instalaron `pypdfium2` 5.15.2 en el `.venv`, y `filelock` 4.2.10 y `typer` 0.29.0 en el entorno vectorial, más nuevos
que en una prueba anterior. Con esas versiones, la guía dio todos sus valores de referencia. Los apéndices de
`reconstruccion/LEEME.md` traen el `pip freeze` de los 2 entornos en esa prueba.

Los programas de la guía importan el código de las piezas desde `src/` (`reconstruccion/correr_e0_sin_roles.py:24` y `reconstruccion/correr_e0_sin_roles.py:34-35`), y la guía pide exportar `NEO4J_PASSWORD` (ver «La variable `NEO4J_PASSWORD`»).
