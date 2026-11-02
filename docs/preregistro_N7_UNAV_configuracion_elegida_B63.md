# Pre-registro de N7: la configuración elegida en N6, para B6.3

Escrito por `escribir_preregistro_n7_v3_mesa.py` desde `n7_configuracion_sellada.json` (`dd425094a287491e…`) y el análisis de N6
(`data/experiment/banco_mcp/n6/analisis/analisis_n6_con_lectura_tolerante.json`, `49cee14c2e478f01…`, la elección de `regla.eleccion`). Lo
firma la autora; el commit de la firma lo sella con su sha256, antes de la entrada sellada de B6.3.

## 1. La regla de N4, §5, sobre lo medido en N6

- **Sobre las 26 sin FUERA_D9 (decisión 9).** **Candidatas:** B, T, T-F1, T-F2, T-F3, T-F4, T-F5, T-F6. **Dentro de V(26)** (0,0637): T,
  T-F1, T-F3, T-F4, T-F5, T-F6.
- **El desempate** (menos veces al tope, después menos R9): T-F6, T-F5, T-F3, T, T-F4, T-F1.
- **La elegida: T-F6**, con fidelidad 0,8889 sobre las 26 sin FUERA_D9 (decisión 9). La regla, aplicada otra vez por la mesa sobre los
  agregados del análisis, da la misma elegida y el mismo orden.
- **Con las 30, al lado** (la decisión 9): la elegida es T-F6, con el orden T-F6, T-F5, T-F3, T, T-F4, T-F1, T-F2.
- **La lectura del juez:** los agregados de las 418 respuestas juzgadas, con las salidas que no se leían como JSON leídas con la lectura
  tolerante (decisión de la autora del 27/10/2026, recibida a las 23:26:23; registro, §151).
- **Con la lectura sellada, al lado** (`a2f22b14078c2b99…`): la elegida es T-F6, y con las 30, T-F6. Las dos lecturas eligen lo mismo.
- **El requisito de la jerarquía:** tiene ver_punto: el camino de 2 llamadas probado en T.

## 2. Lo que fija para B6.3

- **H-3, el brazo del grafo:** la configuración T-F6, con las familias [1, 2, 3, 4, 5], servida por
  `data/experiment/banco_mcp/mcp_kg/servidor_mcp_kg_nav_cand.py` sobre el grafo evaluado
  (`KG_Acumulado_Tandas0y1yFinal_r2b_sincola`, `576c97256185a0d5…`). Sus archivos, en `data/experiment/banco_mcp/n7/`:
  - `config_mcp_kg_n7_evaluado.json`, `9e9f0ee5b9be4ff4…`;
  - `mcp_kg_n7_evaluado.json`, `4e3b9ccb062d8eea…`;
  - `bloque_tools_kg_n7.txt`, `7ced741bffce79c3…`;
  - `bloque_tools_fragmentos_n7.txt`, `0c42964fbb565ca3…`;
  - `plantilla_prompt_n7.txt`, `822aa4e72517bee7…`;
  - las herramientas: buscar_nodos, buscar_puntos, indice_to, tipos_de_relacion, vecinos_por_relacion, ver_descendientes, ver_nodo,
    ver_punto, ver_remisiones, ver_vecinos.
- **H-4, la principal del brazo de fragmentos:** la híbrida (F1 de N6: entra la híbrida, sí),
  `mcp_vector/config_fragmentos_hibrida_evaluado_r2b.json` (`a4acb5cff735baf3…`).
  El denso no cambia: `mcp_vector/config_fragmentos_denso_evaluado_r2b.json` (`09b2233d9016dcfb…`).
- **H-5, los índices:** el índice por punto del grafo evaluado, `indice_puntos/KG_Acumulado_Tandas0y1yFinal_r2b_sincola`, con su manifiesto
  `ef036b67032175f3…`, y los hubs esperados al cargarlo: umbral 51, 376 nodos, `bbfa2ccc1e5002fb…`.
- **H-6, R5:** queda en 30, 32 y 1,80. Las sesiones de N6 de lo elegido que llegaron al tope:
  - T-F6: 0 de 30 (0,0000);
  - F1_hibrida: 0 de 30 (0,0000);
  la regla, confirmada por la autora el 27/10/2026 (15:04:04): más del 5 % de las sesiones de N6 de lo elegido, en cualquiera de
  los dos brazos.
- **La plantilla:** la de N6, `n6/plantilla_prompt_n6.txt` (`822aa4e72517bee7…`), en los dos brazos.

## 3. Lo que queda pendiente

- Nada.

## 4. Lo que se declara

- N6 midió sobre el acumulado de las tandas 0 y 1; B6.3 corre sobre el grafo evaluado. N7 lleva la configuración elegida a ese grafo
  sin cambiar sus herramientas, su bloque ni su plantilla.
- La regla de R5 se lee sobre las sesiones de N6 de lo elegido en cada brazo, como lo confirmó la autora.
- **La lectura tolerante es un desvío del análisis sellado de N6,** decidido por la autora antes de ver ninguna cifra (registro, §151),
  con su motivo, tal cual: «las salidas que fallan son las que copian un pasaje con comillas, así que sacarlas o contarlas como no
  cumplidas no es neutral entre configuraciones». El análisis sellado va al lado.
- **La elección va sin FUERA_D9** (la decisión 9, desvío de N4): las cuatro preguntas que comparten texto con los ejemplos de la familia
  6 salen de las comparaciones entre una configuración con esos ejemplos y una sin ellos; la versión con las 30 va al lado.
- **T-F6 no lleva la familia 6:** el brazo del grafo no lleva sus 3 ejemplos, así que el de fragmentos tampoco (decisión 10), y la
  unidad de los ejemplos de fragmentos no corre.
- **Las cuatro clases de N1** sobre los criterios no cumplidos quedan PENDIENTES: las clasifica la regla sellada de N1 (`db2cc290…`),
  que vive en una carpeta que el despacho de N6 veda. No entran en la regla de N4.
