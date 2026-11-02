#!/bin/zsh
# La corrida de la etapa C: el comando del FRENO de la etapa B («El comando de la etapa C»), con los cuatro cambios del despacho de la C y
# nada más: "$PY" -I -B en lugar de python3 -I -B, --cola y --sha256-cola (la cola candidata que aceptó la autora) y --salida. La consola
# del análisis va a $SP/consola_corrida_C.txt; su código de salida, a $SP/codigo_de_salida_corrida_C.txt.
# Uso: zsh corrida_analisis_C.zsh <scratchpad>
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; SP="$1"
M="$F/hoja_de_ruta_tanda1_mesa"
PA="$F/revision_B63_analisis_A"
CLAVE="$PA/clave_para_despues/clave_adjudicacion_b63.json"
PY="${BCRA_KG_PYTHON:-python3}"
# 1. El sello del código: los dos sha256 de codigo/ tienen que ser los de salidas/b/sello_analisis_B63.txt
for f in analizar_b63.py selftest_analizar_b63.py; do
  grep -qF "$(shasum -a 256 "$F/analisis_b63/codigo/$f" | cut -c1-64)  $(stat -f %z "$F/analisis_b63/codigo/$f")  codigo/$f" \
    "$F/analisis_b63/salidas/b/sello_analisis_B63.txt" || { print -r -- "el código no es el del sello: $f"; exit 20; }
done
# 2. El clon de HEAD, solo con lo que se importa y lee, por rutas explícitas
mkdir "$SP/clon_head_C" && git -C "$R" archive HEAD data/experiment/banco_mcp/b63/v2/b2/comun_b63.py \
  data/experiment/banco_mcp/b63/v2/b2/juez_b63.py data/experiment/banco_mcp/b63/entrada_B63.json data/experiment/banco_mcp/comun_banco.py \
  data/experiment/banco_mcp/lectura_tolerante_juez.py data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py \
  data/experiment/ev2_juez/prompt_juez_v1.md data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json data/experiment/banco_mcp/b63/real/juez/d10_b63.json \
  data/experiment/banco_mcp/b63/real/fechas_b63.json data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json \
  | tar -x -C "$SP/clon_head_C" || { print -r -- "no se pudo armar el clon"; exit 21; }
X="$SP/clon_head_C/data/experiment"
# 3. Las fotos antes y después del repo y de banco_b63/ van aparte (pasos 2 y 5 del despacho)
# 4. La corrida
date "+%Y-%m-%d %H:%M:%S %z la corrida C: empieza" > "$SP/horas_corrida_C.txt"
cd "$SP" && "$PY" -I -B "$F/analisis_b63/codigo/analizar_b63.py" --clon "$X/banco_mcp/b63/v2/b2" \
  --entrada "$X/banco_mcp/b63/entrada_B63.json" --manifiesto-fuera "$X/banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json" \
  --banco-b63 "$F/banco_b63" \
  --agregados "$F/analisis_b63/salidas/aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json" \
  --agregados-tolerante "$F/analisis_b63/salidas/aplicacion/agregados_de_las_que_no_se_leian_b63.json" \
  --veredictos-tolerante "$F/analisis_b63/salidas/aplicacion/veredictos_lectura_tolerante_b63.jsonl" \
  --planilla "$F/analisis_b63/adjudicacion/para_leer/planilla_adjudicacion_b63.csv" \
  --sello-planilla "$F/analisis_b63/adjudicacion/para_leer/sello_adjudicacion_b63.txt" \
  --estructura-planilla "$F/analisis_b63/adjudicacion/para_leer/estructura_planilla_adjudicacion_b63.json" \
  --clave-adjudicacion "$CLAVE" --d10 "$X/banco_mcp/b63/real/juez/d10_b63.json" --fechas "$X/banco_mcp/b63/real/fechas_b63.json" \
  --relevancia "$M/decisiones_279_mesa/relevancia_96/relevancia_96_B63.json" --etapa1 "$F/b63_etapa1" \
  --tabla-cruce "$M/decisiones_182_mesa/cruce/tabla_cruce_ext_v2_mesa.json" \
  --sello-tabla "$M/decisiones_182_mesa/cruce/sello_tabla_cruce_ext_v2_mesa.txt" \
  --pesos-mesa "$M/decisiones_182_mesa/cruce/salida_aplicar_cruce_ext_mesa.json" \
  --cola "$M/decisiones_329_mesa/cola/cola_grafo_evaluado_b63_CANDIDATA_mesa.json" \
  --sha256-cola 9c865fc416f4238791d6437df9d64d1e3c0a47724cf7ec98e23f0edc26cb00ab \
  --kg "$R/data/experiment/reaplicacion_unica/acumulado/ens_128_r2b_sincola/r2/kg.json" \
  --e0 "$R/data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b" \
  --armado-e0 "$X/tanda_final/t3/acumulado/armado_acumulado_128_tf.json" --expertos "$F/b63_material_expertos" \
  --ucita "$R/scripts/ucita2_indicadores_banco.py" --salida "$F/analisis_b63/salidas/c/analisis" > "$SP/consola_corrida_C.txt" 2>&1
rc=$?
print -r -- "$rc" > "$SP/codigo_de_salida_corrida_C.txt"
date "+%Y-%m-%d %H:%M:%S %z la corrida C: termina (salida $rc)" >> "$SP/horas_corrida_C.txt"
exit 0
