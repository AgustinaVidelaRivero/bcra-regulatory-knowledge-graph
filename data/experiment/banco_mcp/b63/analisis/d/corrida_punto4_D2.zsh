#!/bin/zsh
# La corrida de la D2: el comando del FRENO de la D1 («El comando de la D2»), copiado de ese FRENO por código, tal cual,
# con el scratchpad por argumento. Uso: zsh corrida_punto4_D2.zsh <scratchpad>
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; SP="$1"
PY="${BCRA_KG_PYTHON:-python3}"
# 1. Los sellos: el código de la D1 contra salidas/d/sello_punto4_B63.txt y analizar_b63.py contra salidas/b/sello_analisis_B63.txt
for f in exactitud_de_cita_9_4_b63.py selftest_exactitud_de_cita_9_4_b63.py; do
  grep -qF "$(shasum -a 256 "$F/analisis_b63/codigo/$f" | cut -c1-64)  $(stat -f %z "$F/analisis_b63/codigo/$f")  codigo/$f" \
    "$F/analisis_b63/salidas/d/sello_punto4_B63.txt" || { print -r -- "no es el del sello: $f"; exit 20; }
done
grep -qF "$(shasum -a 256 "$F/analisis_b63/codigo/analizar_b63.py" | cut -c1-64)  $(stat -f %z "$F/analisis_b63/codigo/analizar_b63.py")  codigo/analizar_b63.py" \
  "$F/analisis_b63/salidas/b/sello_analisis_B63.txt" || { print -r -- "analizar_b63.py no es el del sello de la B"; exit 20; }
# 2. El clon de HEAD, solo con lo que se importa y lee, por rutas explícitas
mkdir "$SP/clon_head_D2" && git -C "$R" archive HEAD data/experiment/banco_mcp/b63/v2/b2/comun_b63.py \
  data/experiment/banco_mcp/b63/v2/b2/juez_b63.py data/experiment/banco_mcp/b63/entrada_B63.json data/experiment/banco_mcp/comun_banco.py \
  data/experiment/banco_mcp/lectura_tolerante_juez.py data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py \
  data/experiment/ev2_juez/prompt_juez_v1.md data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json \
  data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json | tar -x -C "$SP/clon_head_D2"
X="$SP/clon_head_D2/data/experiment"
# 3. Las fotos antes y después del repo y de banco_b63/ (el instrumento corre desde el repo, en solo lectura), y su comparación
# 4. La corrida
cd "$SP" && "$PY" -I -B "$F/analisis_b63/codigo/exactitud_de_cita_9_4_b63.py" --clon "$X/banco_mcp/b63/v2/b2" \
  --entrada "$X/banco_mcp/b63/entrada_B63.json" --manifiesto-fuera "$X/banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json" \
  --banco-b63 "$F/banco_b63" --e0 "$R/data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b" \
  --armado-e0 "$X/tanda_final/t3/acumulado/armado_acumulado_128_tf.json" --ucita "$R/scripts/ucita2_indicadores_banco.py" \
  --salida "$F/analisis_b63/salidas/d/punto4" > "$SP/consola_corrida_D2.txt" 2>&1
print -r -- "$?" > "$SP/codigo_de_salida_corrida_D2.txt"
