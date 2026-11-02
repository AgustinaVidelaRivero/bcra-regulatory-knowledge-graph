#!/bin/zsh
# La corrida de la AT2: el comando de salidas/at/comando_AT2_PREPARADO.md (paso 3), con --salida en salidas/at/salida/.
SP=${0:A:h:h}
R="${0:A:h:h:h:h:h:h:h:h}"
F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"
C="$F/atribucion_nav/copia/data/experiment/ev2_reporte/code"
AT2="$SP/trabajo_at2/corrida"
PY="${BCRA_KG_PYTHON:-python3}"
"$PY" -I -B "$C/atribucion_b63.py" correr \
  --clon "$AT2/copia_head/data/experiment/banco_mcp/b63/v2/b2" \
  --entrada "$R/data/experiment/banco_mcp/b63/entrada_B63.json" \
  --manifiesto-fuera "$R/data/experiment/banco_mcp/b63/real/manifiesto_fuera_resultados_y_juez_B63.json" \
  --banco-b63 "$F/banco_b63" \
  --agregados "$F/analisis_b63/salidas/aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json" \
  --agregados-tolerante "$F/analisis_b63/salidas/aplicacion/agregados_de_las_que_no_se_leian_b63.json" \
  --veredictos-tolerante "$F/analisis_b63/salidas/aplicacion/veredictos_lectura_tolerante_b63.jsonl" \
  --planilla "$F/analisis_b63/adjudicacion/para_leer/planilla_adjudicacion_b63.csv" \
  --sello-planilla "$R/data/experiment/banco_mcp/b63/analisis/adjudicacion/sello_adjudicacion_b63.txt" \
  --estructura-planilla "$R/data/experiment/banco_mcp/b63/analisis/adjudicacion/estructura_planilla_adjudicacion_b63.json" \
  --clave-adjudicacion "$F/revision_B63_analisis_A/clave_para_despues/clave_adjudicacion_b63.json" \
  --e0 "$R/data/experiment/tanda_final/t3/acumulado/e0_acumulado_128_r2b" \
  --armado-e0 "$R/data/experiment/tanda_final/t3/acumulado/armado_acumulado_128_tf.json" \
  --indice "$R/data/experiment/banco_mcp/mcp_kg/indice_puntos/KG_Acumulado_Tandas0y1yFinal_r2b_sincola" \
  --codigo-analisis "$R/data/experiment/banco_mcp/b63/analisis/codigo" \
  --enmienda "$R/data/experiment/ev2_reporte/enmienda1_regla_atribucion_navegacion.md" \
  --raiz-indice "$R" \
  --salida "$F/atribucion_nav/salidas/at/salida" \
  --material "$F/atribucion_b63/para_leer" \
  --clave "$AT2/clave_para_despues/clave_atribucion_b63.json"
