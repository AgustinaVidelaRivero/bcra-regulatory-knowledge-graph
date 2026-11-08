# Notas técnicas de la publicación

Estas secciones estaban en el README de la primera versión, y su texto no cambió salvo las cuentas. El README nombra este archivo.

## Mapa por etapa

El código conserva las rutas que tenía en el repo de la tesis, para que los import y las rutas relativas a la raíz
sigan andando.

| Carpeta | Archivos | Qué hay |
|---|---:|---|
| `(raíz)` | 8 | `README.md`, licencias, `NOTICE`, `CITATION.cff`, `requirements.txt`, `.gitignore` y `SHA256SUMS` |
| `corpus/` | 3 | Manifiesto del corpus; los Textos Ordenados con su enlace y su sha256 |
| `evaluacion/` | 7 | Las 192 preguntas de B6.3 y B6.4 con sus criterios, la respuesta final del agente y su veredicto en cada corrida, y el programa que reproduce la fidelidad |
| `data/experiment/b54_catalogo_v3/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/reextraccion_v2/` |
| `data/experiment/banco_mcp/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/`, `data/experiment/banco_mcp/adaptador/`, `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/aislamiento/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/mcp_vector/`, `data/experiment/banco_mcp/n6/`, `data/experiment/banco_mcp/paralelo/`, `data/experiment/banco_mcp/smoke/`, `scripts/` |
| `data/experiment/banco_mcp/a2_1/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `data/experiment/banco_mcp/paralelo/`; 1 dato(s) chico(s) |
| `data/experiment/banco_mcp/adaptador/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/`, `data/experiment/banco_mcp/smoke/` |
| `data/experiment/banco_mcp/agentes/` | 8 | Lanzador de agentes y su entorno limpio; 1 dato(s) chico(s); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/aislamiento/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/` |
| `data/experiment/banco_mcp/b63/` | 87 | B6.3: corrida de evaluación (código y resultados agregados; las preguntas, las respuestas y los veredictos están en `evaluacion/`) |
| `data/experiment/banco_mcp/b64/` | 54 | B6.4: análisis confirmatorio y exactitud de cita (código y resultados agregados; las preguntas, las respuestas y los veredictos están en `evaluacion/`) |
| `data/experiment/banco_mcp/coincidencias_con_el_grafo/` | 15 | Scripts que sostienen la declaración de las coincidencias del grafo con criterios (`docs/formato_del_grafo.md`) |
| `data/experiment/banco_mcp/gate/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/adaptador/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/smoke/`, `scripts/` |
| `data/experiment/banco_mcp/mcp_kg/` | 22 | Servidor MCP del grafo (navegación por el grafo) |
| `data/experiment/banco_mcp/mcp_vector/` | 11 | Servidor MCP de recuperación por fragmentos (BM25, denso e híbrido; los índices se regeneran desde el corpus); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/n6/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/` |
| `data/experiment/banco_mcp/n7/` | 5 | Solo datos chicos; 1 dato(s) chico(s); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/n7c/` | 4 | Solo datos chicos; 1 dato(s) chico(s); suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/banco_mcp/paralelo/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/agentes/`, `data/experiment/banco_mcp/aislamiento/`, `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/` |
| `data/experiment/banco_mcp/smoke/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/a2_1/` |
| `data/experiment/catalogo_unico/` | 7 | Lo que lee `prompt_r2b.py`, y el catálogo de sujetos |
| `data/experiment/escalado_prep/` | 5 | Inventario y registro de la descarga del corpus |
| `data/experiment/esq/` | 23 | Cierre de los imports: lo importa el código de `data/experiment/b54_catalogo_v3/`, `data/experiment/reextraccion_v2/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/esq_v3_miembros/` | 1 | Clases del esquema final |
| `data/experiment/ev2_corrida/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/ev2_reporte/`, `data/experiment/neo4j/`, `data/experiment/tanda0/` |
| `data/experiment/ev2_juez/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/b64/`, `scripts/`; 1 dato(s) chico(s) |
| `data/experiment/ev2_reporte/` | 2 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/smoke/` |
| `data/experiment/evaluacion/` | 5 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/gate/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/ev2_corrida/`, `data/experiment/ev2_juez/`, `data/experiment/ev2_reporte/`, `data/experiment/exploracion/`, `data/experiment/neo4j/`, `data/experiment/reextraccion_v2/`, `data/experiment/tanda0/`, `scripts/` |
| `data/experiment/exploracion/` | 4 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/gate/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/ev2_corrida/`, `data/experiment/ev2_reporte/` |
| `data/experiment/grafo_v2/` | 7 | Cierre de los imports: lo importa el código de `data/experiment/esq/`, `data/experiment/reextraccion_v2/`, `data/experiment/tanda0/`, `scripts/`; 1 dato(s) chico(s) |
| `data/experiment/job_actualizacion/` | 11 | Trabajo de actualización |
| `data/experiment/mantenimiento/` | 23 | Control del sitio y empalme |
| `data/experiment/med_desamb/` | 1 | Cierre de los imports: lo importa el código de `data/experiment/reaplicacion_unica/`, `data/experiment/tanda0/` |
| `data/experiment/neo4j/` | 11 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/b63/`, `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/banco_mcp/mcp_vector/`, `data/experiment/banco_mcp/smoke/`, `scripts/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/prompt_r2/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/reextraccion_v2/` |
| `data/experiment/pyd_r2/` | 7 | Cierre de los imports: lo importa el código de `data/experiment/prompt_r2/`, `data/experiment/reextraccion_v2/`, `data/experiment/tanda0/`, `scripts/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/reaplicacion_unica/` | 22 | Reaplicación única: ensamblado y sellado del grafo evaluado, con el grafo y su sello |
| `data/experiment/reextraccion_v2/` | 68 | Reextracción: corpus, fragmentación (e0), extractor (e1), reducción (e2) y verificador (e3) de tripletas |
| `data/experiment/segmentacion_oficial_e0r2/` | 270 | Segmentación oficial de los Textos Ordenados en puntos (E0) |
| `data/experiment/tanda0/` | 3 | Cierre de los imports: lo importa el código de `data/experiment/banco_mcp/mcp_kg/`, `data/experiment/reaplicacion_unica/`; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `data/experiment/tanda_final/` | 2 | Planes derivados de la tanda final |
| `data/experiment/tripletas_v/` | 2 | Instrucciones sin casos del juez de las tripletas |
| `docs/` | 55 | Pre-registros, enmiendas, adendas y el formato del grafo; suma lo del tramo de las instrucciones, los planes y la 6.3 |
| `ejemplos/` | 2 | Los 2 programas de ejemplo |
| `fuera_del_repo/b63_etapa1/scripts/` | 2 | Las funciones de P1 que carga el análisis de B6.3, tal cual |
| `preregistros/` | 1 | sha256 de los pre-registros, las enmiendas y las adendas |
| `scripts/` | 25 | Scripts de verificación y de indicadores |
| `src/` | 7 | Código común: descarga del corpus y utilidades |
| `tests/` | 1 | Pruebas del código común |

La columna cuenta todos los archivos del árbol bajo cada carpeta, y suma 820, los de `SHA256SUMS` más ese archivo.

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
`lanzar_agente.py`, que van tal cual, y 61 renglones en 38 archivos que nombran `hoja_de_ruta_tanda1_mesa`, `scratchpads`,
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
| `data/experiment/mantenimiento/control_sitio/selftest_control_sitio.py` | datos que no se publican: falta data/experiment/job_actualizacion/corridas/2026-09-07/indice_crudo.json |
| `data/experiment/mantenimiento/control_sitio/selftest_correr_control.py` | datos que no se publican: falta data/experiment/job_actualizacion/corridas/2026-09-07/indice_crudo.json |
| `data/experiment/neo4j/test_equivalencia.py` | necesita Neo4j corriendo; esta corrida fue sin red ni Docker |
| `data/experiment/reextraccion_v2/corpus_v2/selftest_corpus.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_pro.json |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b52.py` | datos que no se publican: falta data/experiment/subset/TO_proteccion_usuarios_servicios_financieros_actual.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b581.py` | datos que no se publican: falta data/experiment/escalado_prep/pdfs/ri_ieccm.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b582.py` | datos que no se publican: falta data/experiment/escalado_prep/pdfs/ri_ieccm.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_b583.py` | datos que no se publican: falta data/experiment/subset/TO_capitales_minimos_actual.pdf |
| `data/experiment/reextraccion_v2/e0_chunking/selftest_e0.py` | datos que no se publican: falta data/experiment/exploracion/mapa_territorio_quemado_5TOs_5sets.json |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_canal_abierto_e1.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_cap.json |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_e1.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida_enm01/chunks_cap.json |
| `data/experiment/reextraccion_v2/e1_extractor/selftest_prompt_r2b.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e1_extractor/candado_mensaje_r2b.json |
| `data/experiment/reextraccion_v2/e2_reduce/selftest_e2.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e1_extractor/salida/faseB_pro/extracciones.jsonl |
| `data/experiment/reextraccion_v2/e3_verificador/selftest_e3.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/reextraccion_v2/selftest_cablev3.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/reextraccion_v2/selftest_manifiesto.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/reextraccion_v2/selftest_ub53.py` | datos que no se publican: falta data/experiment/reextraccion_v2/e0_chunking/salida/chunks_cla.json |
| `data/experiment/segmentacion_oficial_e0r2/s0_5/scripts/selftest_control_continuidad.py` | pide por argumento datos que no se publican: pide --antes, --despues, --lineas |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/prueba_cierre_S1quater.py` | prueba cifras_lectura_S1quater.py, que no se publica por el control de fuga; con ese archivo pasa |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/prueba_cifra_control_S1quater.py` | prueba cifras_lectura_S1quater.py, que no se publica por el control de fuga; con ese archivo pasa |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/adjudicacion/prueba_preparar_pasada_1_S1quater.py` | pide por argumento datos que no se publican: pide --script, --carpeta, --orden, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_S1quater.py` | pide por argumento datos que no se publican: pide --copia, --s1ter-scripts, --planillas-s1ter, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_1_S1quater.py` | pide por argumento datos que no se publican: pide --v1, --v2, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --tanda0, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_2_S1quater.py` | pide por argumento datos que no se publican: pide --v2, --v3, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --diseno-s0-6a, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_3_S1quater.py` | pide por argumento datos que no se publican: pide --v3, --v4, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --diseno-s0-6a, --adenda-3, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1quater/diseno/scripts/prueba_adenda_4_S1quater.py` | pide por argumento datos que no se publican: pide --v4, --v5, --e0, --manifest, --manifiesto-tos, --orden-s1ter, --diseno-s0-6a, --adenda-3, --adenda-4, --e0-corregida, --manifest-corregida, --sha-manifest-corregida, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/adjudicacion/prueba_acuerdo_etapa_1_S1ter.py` | pide por argumento datos que no se publican: pide --planilla-vacia, --script, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/adjudicacion/prueba_adjudicacion_dos_pasadas_S1ter_v2.py` | pide por argumento datos que no se publican: pide --s1ter, --carpeta-lectora, --scripts, --trabajo |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/scripts/prueba_aplicar_adjudicacion_S1ter.py` | pide por argumento datos que no se publican: pide --s1ter, --trabajo, --sha-orden, --sha-poblaciones-finales |
| `data/experiment/segmentacion_oficial_e0r2/s1ter/scripts/prueba_cifras_S1ter.py` | pide por argumento datos que no se publican: pide --orden, --sha-orden, --poblaciones-finales, --poblaciones, --trabajo |
| `scripts/selftest_gate6.py` | busca .venv/bin/python en la raíz del repositorio, y el .venv no se publica; además necesita la historia de git |
| `scripts/selftest_muestra_aristas_obs12.py` | datos que no se publican: falta reports/obs12_selftest_r1/muestra_obs12.json |
| `scripts/selftest_regression_kg.py` | datos que no se publican: falta reports/u_estudio_matriz/lectura/uestmat_muestra_60_leida.csv |

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
