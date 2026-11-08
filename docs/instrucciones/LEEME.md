# Las instrucciones de los modelos

Cada fila da el archivo con el texto completo, su sha256 y dónde está sellado. La columna «Dónde» usa `archivo:renglón`.

## Apéndice D

| Pieza | Archivo | sha256 | Dónde |
|---|---|---|---|
| El extractor | `docs/instrucciones/extractor_instrucciones.txt` | `ccffa4e36ba26a4b63b5760a7657d4bb5f5357ccd2392fe2b67584e4c2efb775` | `data/experiment/reextraccion_v2/e1_extractor/perfil_e1.py:79` |
| El verificador | `docs/instrucciones/verificador_instrucciones.txt` | `128fa60feb4791b142e62bb6eec06e8ddcb5dd58a0a0476692831fb35b15c983` | Sale del prefijo de la fila siguiente |
| El prefijo del verificador, tal como llega al modelo | `docs/instrucciones/verificador_prefijo_canonico.json` | `21a836c7de6dbbee038ceb3c0eaae8edee753eb9feb23c6f4ab2aa8453371b53` | `data/experiment/reextraccion_v2/e3_verificador/prompt_e3.py:450`, con sus primeros 12 caracteres |

`data/experiment/reextraccion_v2/e1_extractor/prompt_r2b.py` no importa con este repositorio. Le falta `candado_mensaje_r2b.json`, que trae el texto de 17 unidades de la normativa y no se publica. Por eso el texto del extractor va ya armado, con el sha256 que sella la primera fila.

`data/experiment/reextraccion_v2/e3_verificador/prompt_e3.py` no importa con este repositorio. Le faltan `chunks_cla.json`, `chunks_pro.json`, `chunks_ric.json`, `extracciones.jsonl` y `candado_mensaje_e3.json`. Esos 5 archivos traen el texto de los documentos o salidas del extractor, y no se publican. Por eso el texto del verificador va ya armado.

El texto del verificador trae enteras 2 unidades de la norma, `ric::7.1` (1.104 caracteres, renglones 61 a 78 de `verificador_instrucciones.txt`) y `cla::6.5::intro` (2.403 caracteres, renglones 186 a 212), porque sus instrucciones las citan como ejemplo. El prefijo de `verificador_prefijo_canonico.json` trae las mismas 2. Son la única excepción al control que impide publicar, fuera del grafo, un tramo de 1.000 caracteres o más igual al texto de una unidad de la E0. Sin ellas, el texto no sería el que recibió el modelo y no daría el sha256 sellado. Ese texto es del BCRA (`NOTICE`).

## Apéndice E, sección E.4

| Pieza | Archivo | sha256 | Dónde |
|---|---|---|---|
| La plantilla del agente | `data/experiment/banco_mcp/n7/plantilla_prompt_n7.txt` | `822aa4e72517bee7a3bd0ed4c80776548622930e54159c16562b874745e771b9` | `docs/preregistro_N7_UNAV_configuracion_elegida_B63.md:27-29` |
| Las herramientas del agente con el grafo | `data/experiment/banco_mcp/n7/bloque_tools_kg_n7.txt` | `7ced741bffce79c339c741546df10393271e79a40a26341a92c5f47232a1f38c` | `docs/preregistro_N7_UNAV_configuracion_elegida_B63.md:27-29` |
| Las herramientas del agente con los fragmentos | `data/experiment/banco_mcp/n7/bloque_tools_fragmentos_n7.txt` | `0c42964fbb565ca35b70cae2b7a27ddeb701a2e7f9345871acdf095eeed8b0e6` | `docs/preregistro_N7_UNAV_configuracion_elegida_B63.md:27-29` |
| El bloque de herramientas de la configuración de partida | `data/experiment/banco_mcp/agentes/bloque_tools_vector.txt` | `d2f853b47caa4cba3bbc6395f1a0546cc562e440b19ea025ed52909943734ba2` | `data/experiment/banco_mcp/agentes/config_agentes.json:23`, que lo nombra sin su sha256 |
| El juez de las respuestas | `data/experiment/ev2_juez/prompt_juez_v1.md` | `fd446f8e61f46033d7de9b862121c698b2c52dcc2696b7f10993f44e509f5455` | `docs/preregistro_B6_3_evaluacion_final.md:383` |

## El juez de las tripletas

| Pieza | Archivo | sha256 | Dónde |
|---|---|---|---|
| Sus instrucciones, sin los casos resueltos | `data/experiment/tripletas_v/juez_v2/instrucciones_juez_tripletas_sin_ejemplos_v2_y_v3.txt` | `f29de17b2dcf4b11eacf615b65e025fc85874c76ff24a29393e2f959c2a01517` | `prompt_juez_v3.py`, que no se publica |
| Su nota | `data/experiment/tripletas_v/juez_v2/NOTA_instrucciones_sin_ejemplos_v2_y_v3.md` | `e993987ec22d1161fd411d02ca5dbd697da8c720af6ecb98d466dcf2dda9a433` | Va junto a las instrucciones |
| Sus instrucciones completas, con los casos resueltos | `docs/instrucciones/juez_tripletas_instrucciones_completas.txt` | `1743db388eb2ffee9c93f0326062a24a4421d086dd750001edeba7ad456aaf18` | `data/experiment/tripletas_v/juez_v3/congelacion_juez_v3_sha256.txt:11` (repositorio de la tesis) |

Las instrucciones completas traen sus casos resueltos, tripletas que la autora ya decidió, con su porqué. Salen de las tripletas que la autora leyó durante el desarrollo del juez y, en parte, de las 100 con que se mide la precisión (sección E.1.3). Van tal como se sellaron, sin la marca de `evaluacion_contenido/`, para que den el sha256 de la congelación.

## El juez de presencia

| Pieza | Archivo | sha256 | Dónde |
|---|---|---|---|
| Sus instrucciones completas, con los casos resueltos | `docs/instrucciones/juez_presencia_instrucciones_completas.txt` | `84cf47a2c1bc3bd6bcb7eae60ab07cf4e868c5ef4ace057de6901fc9dfb11e34` | El campo `prompt_sha256` de sus veredictos, cuyo sha256 está en `data/experiment/tripletas_t_cob/vuelta_e/manifiesto_fuera_del_repo_cob_t_e.json:78` (repositorio de la tesis) |

Sus casos resueltos salen de otros 20 hechos, de pasajes fuera de la muestra, con la presencia que decidió la autora antes de la corrida (sección E.1.5). Van tal como se sellaron, sin la marca de `evaluacion_contenido/`, para que den el sha256 que usó la corrida.
