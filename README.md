# Grafo de conocimiento sobre normativa del BCRA — repositorio de publicación

## Qué es

Un grafo de conocimiento construido sobre Textos Ordenados de la normativa del Banco Central de la República Argentina
(BCRA), y el código que lo produce y lo evalúa contra la recuperación por fragmentos. Es el material publicable de un
proyecto final de Ingeniería en Inteligencia Artificial; la tesis se publica por su propio canal.

## Términos

Cada definición sale del archivo publicado que trae su ancla (`archivo:renglón`).

| Término | Qué es | Dónde |
|---|---|---|
| B6.3 | La evaluación final de la tesis: una sola medición, sobre preguntas nuevas de documentos distintos de los del desarrollo, que compara el grafo con el sistema por fragmentos con el mismo agente, las mismas preguntas y el mismo juez. | `docs/preregistro_B6_3_evaluacion_final.md:1`, `:92`, `:96-98` |
| B6.4 | La segunda evaluación confirmatoria, con su propio pre-registro: mide si el grafo supera a los dos sistemas por fragmentos en preguntas que necesitan juntar información de varios puntos o documentos, y se diseñó después de ver el resultado de B6.3. | `docs/preregistro_B6_4_evaluacion_confirmatoria_varios_puntos.md:1`, `:39-41` |
| EV2 | Una evaluación anterior de la tesis, con 40 preguntas y 164 criterios, en la que un juez clasifica cada par de respuesta y criterio. | `docs/preregistro_evaluacion_fidelidad_ev2.md:1`, `:23-24` |
| P1 | La clasificación sellada de unidades de la normativa, con 289 decididas, de la que salen los pesos de los tipos de pregunta en el total ponderado de B6.3 («P1 a P8», en `:902` y `:912` del mismo pre-registro, son otra cosa: las pruebas de un script). | `docs/preregistro_B6_3_evaluacion_final.md:440-441`, `:582` |
| E0 | La primera etapa del proceso de construcción, E0 a E5, que parte cada Texto Ordenado en las unidades (los chunks) sobre las que trabaja el resto. | `docs/preregistro_tanda0.md:29`, `docs/preregistro_evaluacion_tripletas.md:32`, `docs/preregistro_B6_3_evaluacion_final.md:182` |
| brazo | Cada sistema que responde las mismas preguntas dentro de una evaluación: el agente con el grafo o el agente con un sistema por fragmentos. | `docs/preregistro_B6_3_evaluacion_final.md:303-308`, `docs/preregistro_B6_4_evaluacion_confirmatoria_varios_puntos.md:182` |
| tripletas | La evaluación del contenido del grafo a nivel de tripleta (nodo, relación, nodo): si cada relación es correcta según su texto, si merece estar y qué parte de lo más importante de los textos está en el grafo. | `docs/preregistro_evaluacion_tripletas.md:26-27`, `:32` |
| mandatos | Los documentos firmados que encargan una unidad de trabajo de la tesis y fijan sus etapas; están en `docs/mandatos/` del repositorio de la tesis, y los pre-registros los citan por su ruta. | `docs/preregistro_B6_3_evaluacion_final.md:6-7`, `docs/preregistro_A2_2_sistema_por_fragmentos.md:6`, `:227` |

## Lo que todavía no está

Esta primera versión no trae todo lo que la tesis cita. Lo que sigue se suma antes de la defensa, en commits aparte, con los
controles del resto del árbol (fuga del gold por texto y por hash, nombres, rutas y secretos) y con `SHA256SUMS` rehecho en cada uno:

| Qué | De dónde sale, en el repo de la tesis | Qué falta para sumarlo |
|---|---|---|
| El texto completo de las instrucciones del extractor y del verificador: `prompt_r2b.py` y `prompt_e3.py` están, pero lo arman con datos que todavía no están, así que hoy no importan | 15 archivos de `data/experiment/reextraccion_v2/`, `data/experiment/catalogo_unico/` y `data/experiment/pyd_r2/` | Pasar los controles |
| Las instrucciones del agente: la plantilla y los bloques de herramientas | `data/experiment/banco_mcp/n7/` | Pasar los controles |
| El sha256 de todos los documentos del corpus: `corpus/manifiesto_corpus.csv` trae los 129 Textos Ordenados de los que sale el grafo | `data/experiment/escalado_prep/` | Pasar los controles |
| Las semillas de las muestras del esquema, que la tesis dice registradas | `data/experiment/esq/` | Pasar los controles |
| El mantenimiento del grafo: el procedimiento de empalme, la tabla de reprocesamiento y el control del sitio | `data/experiment/mantenimiento/` (31 archivos) y `data/experiment/job_actualizacion/` (20) | Pasar los controles |
| Los reportes y las cifras de las etapas | `data/experiment/tanda1/`, `data/experiment/tanda_final/`, `data/experiment/segmentacion_oficial_e0r2/s2/`, `data/experiment/comp_e1/`, `data/experiment/reext_t0/`, `data/experiment/e3_listas/`, `reports/` | Pasar los controles |
| Los mandatos que citan los pre-registros | `docs/mandatos/` | Pasar los controles |
| La evaluación por tripletas: los scripts, las fichas y los resultados | `data/experiment/tripletas_v/` (59 archivos) y `data/experiment/tripletas_t_cob/` (13) | Un control propio: el gold son veredictos ficha por ficha, y un agregado de una sola ficha alcanza para deducir el suyo |
| Los resultados de EV2 | `data/experiment/ev2_reporte/`, `data/experiment/ev2_adjudicacion/` y `data/experiment/ev2_fidelidad_eval/` | El mismo control, por pregunta y por ficha |
| La revisión de expertos de B6.4 | `data/experiment/banco_mcp/b64/expertos/` | Su devolución y su análisis, en cifras agregadas |
| La demostración de la actualización sobre los tres documentos que cambiaron en el sitio | Se corre sobre una copia del grafo: no toca el grafo evaluado | Correrla |

## Contenido del repositorio

| Ruta | Qué es | Licencia |
|---|---|---|
| `data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz` | El grafo evaluado en B6.3 y B6.4 | CC BY 4.0 (`LICENSE-DATA`) |
| `data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json.gz.sello.json` | Su sello (sha256 del archivo y del JSON) | CC BY 4.0 |
| `corpus/manifiesto_corpus.csv` | Enlace y huella de cada documento de origen | CC BY 4.0 |
| `docs/preregistro_*.md`, `docs/enmienda*`, `docs/adenda*` | Los 11 pre-registros y sus 22 enmiendas y adendas | CC BY 4.0 |
| `preregistros/FIRMAS.md` | sha256 de cada pre-registro, enmienda y adenda, tal como se publica | CC BY 4.0 |
| `docs/formato_del_grafo.md` | Formato del grafo y cómo verificar el sello | CC BY 4.0 |
| Los 5 archivos de resultados de B6.3 y B6.4 (abajo) | Cifras agregadas de las dos evaluaciones | CC BY 4.0 |
| `data/experiment/…`, `src/`, `scripts/`, `tests/` | El código (624 archivos), con sus rutas del repo de la tesis | MIT (`LICENSE`) |
| `fuera_del_repo/b63_etapa1/scripts/` | Las 2 funciones de P1 que carga el análisis de B6.3 | MIT |
| Los 6 datos chicos (abajo) | Esquema, prompt del juez y configuraciones que usan el código y sus pruebas | CC BY 4.0 |
| `requirements.txt` | Paquetes de terceros, con las versiones del `.venv` | MIT |
| `data/experiment/banco_mcp/requirements_vector.txt` | Paquetes del servidor MCP de fragmentos | MIT |
| `.gitignore` | Lo que el código escribe y no se versiona | MIT |
| `SHA256SUMS` | sha256 de cada archivo del árbol | — |

Los pre-registros, las enmiendas y las adendas van tal cual, salvo 2 adendas que van con cada
nombre de persona reemplazado por «[nombre omitido]» (`preregistros/FIRMAS.md` declara la omisión, con el sha256 del original):

| Archivo | Reemplazos |
|---|---:|
| `docs/adenda2_laudo_B5.5_cobertura.md` | 6 |
| `docs/adenda_laudo_B5.5_segmentacion_universal.md` | 6 |

## Mapa por etapa

El código conserva las rutas que tenía en el repo de la tesis, para que los import y las rutas relativas a la raíz
sigan andando.

| Carpeta | Archivos | Qué hay |
|---|---:|---|
| `(raíz)` | 8 | `README.md`, licencias, `NOTICE`, `CITATION.cff`, `requirements.txt`, `.gitignore` y `SHA256SUMS` |
| `corpus/` | 1 | Manifiesto del corpus |
| `data/experiment/b54_catalogo_v3/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/reextraccion_v2/` |
| `data/experiment/banco_mcp/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/`, `data/experiment/banco_mcp/adaptador/`, `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/aislamiento/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/mcp_vector/`, `data/experiment/banco_mcp/n6/`, `data/experiment/banco_mcp/paralelo/`, `data/experiment/banco_mcp/smoke/`, `scripts/` |
| `data/experiment/banco_mcp/a2_1/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `data/experiment/banco_mcp/paralelo/`; 1 dato(s) chico(s) |
| `data/experiment/banco_mcp/adaptador/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/`, `data/experiment/banco_mcp/smoke/` |
| `data/experiment/banco_mcp/agentes/` | 7 | Lanzador de agentes y su entorno limpio; 1 dato(s) chico(s) |
| `data/experiment/banco_mcp/aislamiento/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/` |
| `data/experiment/banco_mcp/b63/` | 86 | B6.3: corrida de evaluación (código y resultados agregados; sin preguntas ni respuestas) |
| `data/experiment/banco_mcp/b64/` | 54 | B6.4: análisis confirmatorio y exactitud de cita (código y resultados agregados; sin preguntas ni respuestas) |
| `data/experiment/banco_mcp/coincidencias_con_el_grafo/` | 12 | Scripts que sostienen la declaración de las coincidencias del grafo con criterios (`docs/formato_del_grafo.md`) |
| `data/experiment/banco_mcp/gate/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/adaptador/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/smoke/`, `scripts/` |
| `data/experiment/banco_mcp/mcp_kg/` | 22 | Servidor MCP del grafo (navegación por el grafo) |
| `data/experiment/banco_mcp/mcp_vector/` | 6 | Servidor MCP de recuperación por fragmentos (BM25, denso e híbrido; los índices se regeneran desde el corpus) |
| `data/experiment/banco_mcp/n6/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/` |
| `data/experiment/banco_mcp/n7/` | 1 | Solo datos chicos; 1 dato(s) chico(s) |
| `data/experiment/banco_mcp/n7c/` | 1 | Solo datos chicos; 1 dato(s) chico(s) |
| `data/experiment/banco_mcp/paralelo/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/aislamiento/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/` |
| `data/experiment/banco_mcp/smoke/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/` |
| `data/experiment/esq/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/b54_catalogo_v3/`, `data/experiment/reextraccion_v2/` |
| `data/experiment/ev2_corrida/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/ev2_reporte/`, `data/experiment/neo4j/`, `data/experiment/tanda0/` |
| `data/experiment/ev2_juez/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `scripts/`; 1 dato(s) chico(s) |
| `data/experiment/ev2_reporte/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/smoke/` |
| `data/experiment/evaluacion/` | 5 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/gate/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/ev2_corrida/`, `data/experiment/ev2_juez/`, `data/experiment/ev2_reporte/`, `data/experiment/exploracion/`, `data/experiment/neo4j/`, `data/experiment/reextraccion_v2/`, `data/experiment/tanda0/`, `scripts/` |
| `data/experiment/exploracion/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/gate/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/ev2_corrida/`, `data/experiment/ev2_reporte/` |
| `data/experiment/grafo_v2/` | 7 | Cierre de los imports: lo importa el código de `data/experiment/esq/`, `data/experiment/reextraccion_v2/`, `data/experiment/tanda0/`, `scripts/`; 1 dato(s) chico(s) |
| `data/experiment/med_desamb/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/reaplicacion_unica/`, `data/experiment/tanda0/` |
| `data/experiment/neo4j/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/mcp_vector/`, `data/experiment/banco_mcp/smoke/`, `scripts/` |
| `data/experiment/prompt_r2/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/reextraccion_v2/` |
| `data/experiment/pyd_r2/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/prompt_r2/`, `data/experiment/reextraccion_v2/`, `data/experiment/tanda0/`, `scripts/` |
| `data/experiment/reaplicacion_unica/` | 22 | Reaplicación única: ensamblado y sellado del grafo evaluado, con el grafo y su sello |
| `data/experiment/reextraccion_v2/` | 64 | Reextracción: corpus, fragmentación (e0), extractor (e1), reducción (e2) y verificador (e3) de tripletas |
| `data/experiment/segmentacion_oficial_e0r2/` | 270 | Segmentación oficial de los Textos Ordenados en puntos (E0) |
| `data/experiment/tanda0/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/reaplicacion_unica/` |
| `docs/` | 34 | Pre-registros, enmiendas, adendas y el formato del grafo |
| `fuera_del_repo/b63_etapa1/scripts/` | 2 | Las funciones de P1 que carga el análisis de B6.3, tal cual |
| `preregistros/` | 1 | sha256 de los pre-registros, las enmiendas y las adendas |
| `scripts/` | 25 | Scripts de verificación y de indicadores |
| `src/` | 7 | Código común: descarga del corpus y utilidades |
| `tests/` | 1 | Pruebas del código común |

La columna cuenta todos los archivos del árbol bajo cada carpeta, y suma 684, los de `SHA256SUMS` más ese archivo.

Los 38 archivos con `_mesa` en el nombre son scripts de la mesa de revisión de la tesis (controles, pruebas y armado de
material), aparte del código de cada etapa; conservan el nombre que tenían en el repo de la tesis.

## El cierre de los imports

El código que va tiene que importar completo. A los archivos de código de las etapas publicadas se agregaron los
módulos del repo de la tesis que importan, y los que importan esos, hasta que no apareció ninguno nuevo (análisis
estático de los `import`; cada módulo se resuelve como lo resuelve quien lo importa: su carpeta, sus
`sys.path.insert` y la raíz del repo). Entraron 56 archivos. Cada uno pasó los mismos controles que el
resto (fuga del gold, nombres y rutas), salvo los de esta tabla, que no van; los archivos que los importan no corren:

| Archivo que no va | Por qué | Lo importan |
|---|---|---|
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/cifras_lectura_S1quater.py` | fuga del gold: un criterio del gold (no de B6.3, B6.4 ni EV2), igual por espacios y por palabras | `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/aplicar_adjudicacion_S1quater.py`, `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/cifra_control_sin_vistas_S1quater.py` |

Módulos que el código importa y que no tienen archivo en el repo de la tesis (quien los importa no corre tal cual):

| Módulo | Lo importan |
|---|---|
| `muestra_memoria` | `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_scripts__censo_c1_pasos.py`, `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_scripts__control_cegamiento_salidas.py`, `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_scripts__medir_paso.py`, `data/experiment/reaplicacion_unica/paquete_UREAPL/ureapl_scripts__tablas_compuestas.py` |

`requirements.txt` lleva los paquetes de terceros, con las versiones del `.venv`.

## Python

La tesis corrió con dos intérpretes. El código que llama a `.venv/bin/python` (los agentes, los servidores MCP y lo que corre con
ellos) usó Python 3.10.13, con los paquetes de `requirements.txt`. Los comandos que usan `BCRA_KG_PYTHON` o `python3` usaron el
`python3` del sistema, que hoy es 3.12.13. Tres archivos usan sintaxis de Python 3.12 y no corren con 3.10:

- `data/experiment/banco_mcp/b63/analisis/at/at2_bis/controles_salida_at2_bis.py`
- `data/experiment/banco_mcp/b63/analisis/at/at2_bis/controles_salida_at2_bis_pasada1.py`
- `scripts/ucita2_indicadores.py`

`torch`, `transformers` y `sentence-transformers` tienen las versiones de `data/experiment/banco_mcp/requirements_vector.txt`, que va tal cual. Su venv no se
conserva.

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

Otro archivo del repositorio verifica el sha256 de estos 10, así que van tal cual, sin ninguna edición.
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
| `scripts/ucita2_indicadores_banco.py` | 2 |

`data/experiment/banco_mcp/agentes/lanzar_agente.py` va aparte: ningún archivo verifica su sha256, pero `docs/preregistro_A2_2_sistema_por_fragmentos.md:39` lo cita, así que también va
tal cual. 5 de sus renglones traen rutas del mismo tipo. `preregistros/FIRMAS.md` lista todos los archivos cuyo sha256 cita un pre-registro.

## Rutas y variables de entorno

Salvo lo que declara esta sección, el código no nombra ninguna carpeta de la máquina en que se escribió. Lo declarado: los archivos sellados y
`lanzar_agente.py`, que van tal cual, y 56 renglones en 34 archivos que nombran `hoja_de_ruta_tanda1_mesa`, `scratchpads`,
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

Quedan usos de la carpeta personal de quien corre el código que no nombran ninguna máquina: enmascararla como `$HOME`
en los registros, pasarla a un subproceso y expandir una ruta que declara quien corre.

## Las pruebas

Las pruebas corren desde la raíz del repositorio con el intérprete de `requirements.txt`, en una ruta que no tenga nombres de brazo
(como `kg`). Las que necesitan el gold, la API, datos que no se publican o el `.venv` de la tesis no corren con este repositorio solo; son
estas, con su causa:

| Prueba | Causa |
|---|---|
| `data/experiment/banco_mcp/agentes/selftest_lanzar_lote_paralelo_r5.py` | pide por argumento datos que no se publican: pide --entradas, --tmp, --resultado |
| `data/experiment/banco_mcp/agentes/selftest_metadata.py` | datos que no se publican: falta data/experiment/banco_mcp/agentes/precios_sellados.json |
| `data/experiment/banco_mcp/aislamiento/test_aislamiento.py` | necesita BANCO_VENV_VECTOR, el venv del servidor de fragmentos, que no se conserva |
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
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_cand.py` | pide por argumento datos que no se publican: pide --config |
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav_rel_amp.py` | necesita Python 3.12; con el python3 del sistema (3.12.13) falla porque faltan data/experiment/banco_mcp/n7c/config_mcp_kg_n7c_amp_evaluado.json y data/experiment/banco_mcp/n7c/lector_cita_n7c_amp.py, que no se publican |
| `data/experiment/banco_mcp/mcp_kg/selftest_familias_nav.py` | pide por argumento datos que no se publican: pide --config |
| `data/experiment/banco_mcp/mcp_kg/selftest_indice_puntos_union.py` | pide por argumento datos que no se publican: pide --respaldo-n5, --out |
| `data/experiment/banco_mcp/mcp_kg/selftest_servidor_mcp_kg_nav_cand.py` | datos que no se publican: falta data/experiment/banco_mcp/n6/config_agentes_n6.json |
| `data/experiment/banco_mcp/mcp_kg/test_paridad_mcp_kg.py` | datos que no se publican: falta data/experiment/banco_mcp/mcp_kg/config_mcp_kg.json |
| `data/experiment/banco_mcp/mcp_vector/test_fragmentos_a2_1.py` | datos que no se publican: falta data/experiment/banco_mcp/mcp_vector/config_fragmentos_bm25_r2b.json |
| `data/experiment/banco_mcp/mcp_vector/test_fragmentos_f1.py` | datos que no se publican: falta data/experiment/tanda1/t3/acumulado/manifiestos/acumulado_30tos_r2b.json |
| `data/experiment/banco_mcp/mcp_vector/test_mcp_vector.py` | datos que no se publican: falta data/experiment/banco_mcp/mcp_vector/config_mcp_vector.json |
| `data/experiment/reextraccion_v2/corpus_v2/selftest_corpus.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_pro.json |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b52.py` | datos que no se publican: falta data/experiment/subset/TO_proteccion_usuarios_servicios_financieros_actual.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b581.py` | datos que no se publican: falta data/experiment/escalado_prep/pdfs/ri_ieccm.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b582.py` | datos que no se publican: falta data/experiment/escalado_prep/pdfs/ri_ieccm.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b583.py` | datos que no se publican: falta data/experiment/subset/TO_capitales_minimos_actual.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_e0.py` | datos que no se publican: falta data/experiment/exploracion/mapa_territorio_quemado_5TOs_5sets.json |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_canal_abierto_e1.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_cap.json |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_e1.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_cap.json |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_prompt_r2b.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e1_extractor/prompt_r2b_reemplazos.json |
| `data/experiment/reextraccion_v2/e2_reduce/selftest_e2.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e1_extractor/salida/faseB_pro/extracciones.jsonl |
| `data/experiment/reextraccion_v2/e3_verificador/selftest_e3.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/reextraccion_v2/selftest_cablev3.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/reextraccion_v2/selftest_manifiesto.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/reextraccion_v2/selftest_ub53.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/segmentacion_oficial_e0r2/s0_5/scripts/selftest_control_continuidad.py` | pide por argumento datos que no se publican: pide --antes, --despues, --lineas |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/prueba_cierre_S1quater.py` | prueba cifras_lectura_S1quater.py, que no se publica por el control de fuga; con ese archivo pasa |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/prueba_cifra_control_S1quater.py` | prueba cifras_lectura_S1quater.py, que no se publica por el control de fuga; con ese archivo pasa |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/prueba_preparar_pasada_1_S1quater.py` | pide por argumento datos que no se publican: pide --script, --carpeta, --orden, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_1_S1quater.py` | pide por argumento datos que no se publican: pide --v1, --v2, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --tanda0, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_2_S1quater.py` | pide por argumento datos que no se publican: pide --v2, --v3, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --diseno-s0-6a, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_3_S1quater.py` | pide por argumento datos que no se publican: pide --v3, --v4, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --diseno-s0-6a, --adenda-3, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_4_S1quater.py` | pide por argumento datos que no se publican: pide --v4, --v5, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --diseno-s0-6a, --adenda-3, --adenda-4, --e0-corregida, --manifest-corregida, --sha-manifest-corregida, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_S1quater.py` | pide por argumento datos que no se publican: pide --copia, --s1ter-scripts, --planillas-s1ter, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/adjudicacion/prueba_acuerdo_etapa_1_S1ter.py` | pide por argumento datos que no se publican: pide --planilla-vacia, --script, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/adjudicacion/prueba_adjudicacion_dos_pasadas_S1ter_v2.py` | pide por argumento datos que no se publican: pide --s1ter, --carpeta-lectora, --scripts, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/scripts/prueba_aplicar_adjudicacion_S1ter.py` | pide por argumento datos que no se publican: pide --s1ter, --trabajo, --sha-orden, --sha-poblaciones-finales |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/scripts/prueba_cifras_S1ter.py` | pide por argumento datos que no se publican: pide --orden, --sha-orden, --poblaciones-finales, --poblaciones, --trabajo |
| `scripts/selftest_gate6.py` | busca .venv/bin/python en la raíz del repositorio, y el .venv no se publica; además necesita la historia de git |
| `scripts/selftest_muestra_aristas_obs12.py` | datos que no se publican: falta reports/obs12_selftest_r1/muestra_obs12.json |
| `scripts/selftest_regression_kg.py` | datos que no se publican: falta reports/u_estudio_matriz/lectura/uestmat_muestra_60_leida.csv |
| `scripts/selftest_shapes_congelado.py` | datos que no se publican: falta data/experiment/pyd_r2/generados/enums_r2.json |

## Lo que ya estaba roto en el repo de la tesis

Estos problemas vienen del repo de la tesis y no se arreglaron, para que el código publicado sea el que corrió:

- `data/experiment/segmentacion_oficial_e0r2/s0_3/scripts/censo_s03.py` y `data/experiment/segmentacion_oficial_e0r2/s0_4/scripts/censo_s04.py` importan `comparar_e0` desde su propia carpeta, donde ese archivo no está (está en `s0_1/scripts/` y en `s0_4/bis/scripts/`). No corren tal cual.
- `data/experiment/banco_mcp/b64/control_36/cruce/probar_cruce_control_36_B64.py` busca su material en `data/experiment/banco_mcp/b64/control_36/control_36/material/`, una ruta que no existe (el material está en `b64/control_36/material_v1/material/`).
- `data/experiment/banco_mcp/b63/control_36/sorteo/probar_sorteo_control_36_B63_v1.py` falla con `KeyError 'final'` al correr su script, y no le falta ningún archivo: la prueba y el script van tal cual de la tesis.

No están en esta lista `prueba_cierre_S1quater.py` y `prueba_cifra_control_S1quater.py`
(`data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/`): en la tesis pasan. Aquí no corren porque prueban
`cifras_lectura_S1quater.py`, que no se publica por el control de fuga.

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

## Resultados de B6.3 y B6.4

Cifras agregadas de las dos evaluaciones, sin preguntas, criterios ni respuestas:

| Archivo |
|---|
| `data/experiment/banco_mcp/b63/analisis/c/analisis_B63.json` |
| `data/experiment/banco_mcp/b63/analisis/d/punto4/punto4_B63.json` |
| `data/experiment/banco_mcp/b63/real/resumen_b63.json` |
| `data/experiment/banco_mcp/b64/analisis/salidas/a/analisis/analisis_B64.json` |
| `data/experiment/banco_mcp/b64/analisis/salidas/a/exactitud_de_cita/exactitud_de_cita_B64.json` |

## El grafo

`docs/formato_del_grafo.md` describe nodos, aristas y procedencia, y cómo verificar el `kg.json.gz` contra su sello.
El texto del BCRA citado dentro del grafo es del BCRA (ver `NOTICE`).

## El corpus

Los PDF no se redistribuyen. `corpus/manifiesto_corpus.csv` trae, por cada documento del que sale el grafo, su
Texto Ordenado, su enlace en `bcra.gob.ar` y su sha256: se baja cada PDF de su enlace y se compara su sha256 con el
del manifiesto. Verificados sin bajar nada: 129 de 129 PDF con un
único enlace del BCRA y 129 de 129 con un único sha256 en los
manifiestos del repo de la tesis; 3 de 4 JSON de origen con su sha256.

## Qué no se publica y por qué

- Las preguntas, los criterios y las respuestas de referencia de la evaluación (el gold): publicarlos invalidaría
  evaluaciones futuras.
- Los PDF: los del BCRA se bajan de su enlace; los demás tienen derechos de terceros.
- Las salidas intermedias, las sesiones, los cachés, los otros grafos, la tesis y la documentación interna del
  proyecto.
- Las consolas y las listas de `data/experiment/banco_mcp/coincidencias_con_el_grafo/`: identificarían criterios. Por la misma razón no va
  `data/experiment/banco_mcp/coincidencias_con_el_grafo/fechas/fechas_de_los_dos_criterios_de_ev2_mesa.py`: trae el sha256 corto de dos criterios, y con el grafo publicado alcanza para ubicar uno.
- `data/experiment/banco_mcp/agentes/config_credenciales.json`.
- El registro de decisiones, el plan, el tablero, las actas de reuniones y el paquete de la mesa de revisión. Los pre-registros los
  citan (`registro, §n`, `plan, :n`, `decisiones_n_mesa/`), así que esas citas no resuelven en este repositorio.
- La historia de commits del repo de la tesis. Los hash de commit que citan los documentos son de esa historia, no de la de este
  repositorio: lo que se puede verificar acá de un pre-registro es su sha256 (`preregistros/FIRMAS.md`).
- Los índices de los sistemas por fragmentos: se regeneran desde el corpus con el código de
  `data/experiment/banco_mcp/mcp_vector/` (modelo de embeddings y revisión fijados en `construir_indice.py`).

## Cómo reproducir lo que se puede

1. Verificar el árbol: `shasum -a 256 -c SHA256SUMS`.
2. Verificar el grafo contra su sello (`docs/formato_del_grafo.md`).
3. Bajar el corpus con los enlaces de `corpus/manifiesto_corpus.csv` y verificar cada sha256.
4. Instalar los paquetes de `requirements.txt` y correr las pruebas que no están declaradas arriba.

## Licencias

El código, bajo MIT (`LICENSE`). El grafo, su sello, el manifiesto del corpus, los resultados, los pre-registros y la
documentación, bajo CC BY 4.0 (`LICENSE-DATA`). El texto del BCRA citado dentro del grafo es del BCRA (`NOTICE`).

## Cómo citar

Ver `CITATION.cff`. Autoría: Agustina Videla Rivero, Universidad de San Andrés.

Titular de las licencias: Agustina Videla Rivero.

Archivos en el árbol: 671 del repo de la tesis, 2 de `fuera_del_repo` y 11 nuevos de esta publicación.
