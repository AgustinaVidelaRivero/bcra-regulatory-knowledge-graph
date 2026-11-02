#!/bin/zsh
# El análisis confirmatorio de B6.4 (§8, con el §5, el §7, el §10 y la sensibilidad de los expertos): analizar_b64.py, después de la
# lectura tolerante, del armado de la adjudicación, del sello de la planilla de la autora y del manifiesto (corrida_manifiesto_fuera_B64.zsh).
# Controla antes los sha256: la lista y el sello de la corrección del H-6 y el código de B6.4 en ellos, el código de B6.3 en un clon de HEAD
# (por rutas explícitas), el juez de la corrida (b64/v1) y el JSON de los esperados, lleno, con el sha256 de cada entrada (el análisis
# frena si una no lo da). El D-10, las fechas y el manifiesto, con la forma de H-4 (las rutas del runner de B6.4). Lo que todavía no
# existe va como PENDIENTE, y el comando no corre hasta que se llene. La consola va a $SA/consola_analisis_B64.txt; su código de salida,
# al lado.
# Uso: zsh corrida_analisis_B64.zsh <scratchpad> <sha256 de esperado_b64.json> (el segundo argumento, llenado, §384)
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; SP="$1"
PY="${BCRA_KG_PYTHON:-python3}"; H6="$F/analisis_b64_corr"; SA="$H6/salidas/a"; PL="$H6/adjudicacion/para_leer"
ESPERADO="$H6/esperado/esperado_b64.json"   # la copia llena de la plantilla, la escribe llenar_esperado_B64.py (llenado, §384)
SHA_ESPERADO="${2:-PENDIENTE}"   # su sha256: el que imprime llenar_esperado_B64.py, como segundo argumento (llenado, §384)
ENTRADA="$R/data/experiment/banco_mcp/b64/entrada_B64.json"   # H-3: la entrada de B6.4, 9064066b… (llenado, §384)
MANIFIESTO="$F/banco_b64/manifiesto_fuera_B64.json"    # H-4: correr_b63.py --manifiesto-fuera (corrida_manifiesto_fuera_B64.zsh)
D10="$F/banco_b64/juez/d10_b63.json"                    # §7: las marcas del brazo por brazo (H-4: b64/v1/correr_b63.py:440)
FECHAS="$F/banco_b64/resultados/real/fechas_b63.json"  # §6 de B6.3: las sesiones por brazo y por fecha (H-4: b64/v1/correr_b63.py:284)
CLASES="$H6/entradas_mesa/clases_documentos_B64.json"   # §3.1 y §10.4: la armó la mesa, 74fdfbee… (llenado, §384)
LUGARES="$H6/entradas_mesa/lugares_B64.json"   # §10.4: lo armó la mesa, 3e043e7c… (llenado, §384)
EXPERTOS="$F/b64_material_expertos"   # la nota al pie: el material de los expertos (llenado, §384)
CLAVE="$SP/clave_para_despues_B64/clave_adjudicacion_b64.json"
BANCO="$F/banco_b64"
for v in ESPERADO SHA_ESPERADO ENTRADA MANIFIESTO D10 FECHAS CLASES LUGARES EXPERTOS; do
  [[ "${(P)v}" == PENDIENTE ]] && { print -r -- "falta llenar $v"; exit 22; }
done
# 1. La lista y el sello de la corrección del H-6, y el código de B6.4 en la lista
grep -qF "sha256: $(shasum -a 256 "$H6/lista_H6_corr.txt" | cut -c1-64)" "$H6/sello_H6_corr.txt" || { print -r -- "la lista no es la del sello de la corrección del H-6"; exit 20; }
for f in codigo/analizar_b64.py codigo/selftest_analizar_b64.py; do
  grep -qF "$(shasum -a 256 "$H6/$f" | cut -c1-64)  $(stat -f %z "$H6/$f")  $f" "$H6/lista_H6_corr.txt" || { print -r -- "no es el de la lista: $f"; exit 20; }
done
# 2. El clon de HEAD, solo con lo que se importa y lee, por rutas explícitas, y sus sha256; el juez de la corrida; el JSON de los esperados
mkdir "$SP/clon_head_analisis_B64" && git -C "$R" --no-optional-locks archive HEAD \
  data/experiment/banco_mcp/b63/v2/b2/comun_b63.py data/experiment/banco_mcp/b63/v2/b2/juez_b63.py \
  data/experiment/banco_mcp/comun_banco.py data/experiment/banco_mcp/lectura_tolerante_juez.py \
  data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py data/experiment/ev2_juez/prompt_juez_v1.md \
  data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py \
  | tar -x -C "$SP/clon_head_analisis_B64" || { print -r -- "no se pudo armar el clon"; exit 21; }
X="$SP/clon_head_analisis_B64/data/experiment"; C="$X/banco_mcp/b63/analisis/codigo"
typeset -A SHA
SHA=("$C/analizar_b63.py" 9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb
     "$C/aplicar_lectura_tolerante_b63.py" 5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372
     "$R/data/experiment/banco_mcp/b64/v1/juez_b63.py" 4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b
     "$R/data/experiment/banco_mcp/b64/v1/comun_b63.py" 631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc
     "$ESPERADO" "$SHA_ESPERADO")
for f s in "${(@kv)SHA}"; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$s" ]] || { print -r -- "no da su sha256: ${f:t}"; exit 20; }
done
# 3. La corrida
date "+%Y-%m-%d %H:%M:%S %z el análisis de B6.4: empieza" > "$SA/horas_analisis_B64.txt"
cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/analizar_b64.py" --clon "$X/banco_mcp/b63/v2/b2" \
  --entrada "$ENTRADA" --manifiesto-fuera "$MANIFIESTO" --banco-b64 "$BANCO" \
  --agregados "$SA/aplicacion/juez_con_lectura_tolerante/agregados_b63_ciego.json" \
  --agregados-tolerante "$SA/aplicacion/agregados_de_las_que_no_se_leian_b63.json" \
  --veredictos-tolerante "$SA/aplicacion/veredictos_lectura_tolerante_b63.jsonl" \
  --agregados-sin-lectura "$SA/aplicacion/agregados_sin_lectura_b64.json" \
  --planilla "$PL/planilla_adjudicacion_b64.csv" --sello-planilla "$PL/sello_adjudicacion_b64.txt" \
  --estructura-planilla "$PL/estructura_planilla_adjudicacion_b64.json" --clave-adjudicacion "$CLAVE" \
  --d10 "$D10" --fechas "$FECHAS" --clases-documentos "$CLASES" --lugares "$LUGARES" --expertos "$EXPERTOS" \
  --esperado "$ESPERADO" --salida "$SA/analisis" > "$SA/consola_analisis_B64.txt" 2>&1
rc=$?
print -r -- "$rc" > "$SA/codigo_de_salida_analisis_B64.txt"
date "+%Y-%m-%d %H:%M:%S %z el análisis de B6.4: termina (sale con $rc)" >> "$SA/horas_analisis_B64.txt"
exit 0
