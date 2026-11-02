#!/bin/zsh
# Las pruebas de la corrección del H-6 (B6.4: el código del análisis, el de la exactitud de cita, el envoltorio de la lectura tolerante,
# el armado de la adjudicación, el control del juez y los comandos), dos corridas sobre datos de juguete. USD 0, sin API. Antes controla
# los sha256 del código sellado de B6.3 que se importa y del código de HEAD con que se arman las salidas de juguete de N7c+ (en un clon de
# HEAD armado con git archive, por rutas explícitas), del instrumento de citas del repo, que corre desde el repo en solo lectura, y del
# juez y lo común del runner de H-4 (runner_b64/para_el_repo/). Las consolas, los informes, sus códigos de salida y su comparación van a
# $F/analisis_b64_corr/prueba/ (que no puede existir; otra carpeta nueva, como segundo argumento, para depurar); los mundos de juguete, al
# scratchpad.
# Uso: zsh pruebas_H6.zsh <scratchpad> [<carpeta nueva para las salidas>]
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; SP="$1"
PY="${BCRA_KG_PYTHON:-python3}"; H6="$F/analisis_b64_corr"; PR="${2:-$H6/prueba}"
V="$F/runner_b64/para_el_repo/data/experiment/banco_mcp/b64/v1"
# 1. El clon de HEAD, solo con lo que se importa y lee, por rutas explícitas
mkdir "$SP/clon_head_pruebas_H6_corr" && git -C "$R" --no-optional-locks archive HEAD \
  data/experiment/banco_mcp/b63/v2/b2/comun_b63.py data/experiment/banco_mcp/b63/v2/b2/juez_b63.py \
  data/experiment/banco_mcp/comun_banco.py data/experiment/banco_mcp/lectura_tolerante_juez.py \
  data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py data/experiment/ev2_juez/prompt_juez_v1.md \
  data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py \
  data/experiment/banco_mcp/b63/analisis/codigo/exactitud_de_cita_9_4_b63.py data/experiment/banco_mcp/b63/analisis/codigo/armar_adjudicacion_b63.py \
  data/experiment/banco_mcp/b63/analisis/codigo/selftest_analizar_b63.py \
  data/experiment/banco_mcp/b63/analisis/codigo/selftest_exactitud_de_cita_9_4_b63.py \
  data/experiment/banco_mcp/mcp_kg/familias_nav_rel_amp.py data/experiment/banco_mcp/mcp_kg/familias_nav_rel.py \
  data/experiment/banco_mcp/mcp_kg/familias_nav_cand.py data/experiment/banco_mcp/mcp_kg/familias_nav.py \
  data/experiment/banco_mcp/mcp_kg/indice_puntos.py data/experiment/banco_mcp/mcp_vector/bm25_fragmentos.py \
  data/experiment/banco_mcp/mcp_vector/servidor_mcp_vector.py data/experiment/exploracion/sinteticas/resolucion.py \
  data/experiment/exploracion/sinteticas/comun.py data/experiment/exploracion/validar_anclas.py \
  data/experiment/evaluacion/harness.py data/experiment/evaluacion/loader.py \
  | tar -x -C "$SP/clon_head_pruebas_H6_corr" || { print -r -- "no se pudo armar el clon"; exit 21; }
X="$SP/clon_head_pruebas_H6_corr/data/experiment"; C="$X/banco_mcp/b63/analisis/codigo"; K="$X/banco_mcp/mcp_kg"
# 2. Los sha256 de lo que se importa, antes de correr
typeset -A SHA
SHA=("$C/analizar_b63.py" 9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb
     "$C/aplicar_lectura_tolerante_b63.py" 5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372
     "$C/exactitud_de_cita_9_4_b63.py" 5207941b4a54dd2e7071e5d1438fe0b664c0cfd2df56794614ab56de4e6f272a
     "$C/armar_adjudicacion_b63.py" 32daed5cbe1608097592d3cdb6301713df18258ca8bcc98d4d55429b43962aba
     "$C/selftest_analizar_b63.py" e1c37aa300c1954e8cdda8cbac76425e3cbbcc1e1a77449d3bb8d420b85b70ed
     "$C/selftest_exactitud_de_cita_9_4_b63.py" 36744c73a9d36f68771b7fb3403b5d99a7384048fd9f041bb288f1b433f9ca50
     "$X/banco_mcp/lectura_tolerante_juez.py" 191e65bba5527f4f4b6ea2fe826b2b9bcee37d9979c666fa9d61af6c4d13fc06
     "$X/banco_mcp/b63/v2/b2/juez_b63.py" 266dd6f0c3a4c6c0146a5d37657ff14826e93a4c5f2585711dd22f420ce094d2
     "$X/banco_mcp/b63/v2/b2/comun_b63.py" 0100be8f85c425749574adad9cf7c922a0030f4ac5ebdb12f4c83e5b7bcc9b4b
     "$K/familias_nav_rel_amp.py" d5e9aff19bd7d26143b0a9b7a7074844d90bac6405a2dd1a30bd119ff46f9022
     "$K/familias_nav_rel.py" 1b368333838b3d090b923e7d4b3db31751b7e06946ccc31038b4d41a30f125a7
     "$K/familias_nav_cand.py" b8a2e828314a54f62928a6351eacedc1cfdd8178f654ba632d6374ac0bb66d0e
     "$K/familias_nav.py" c27bc888224051de2d2959227479e31e5190027078d5fe405ccb1bd5582da22d
     "$K/indice_puntos.py" 2474ce5eb43974529d85ca96f3317c81e9565c0af2f6debb95cd383002ce58fe
     "$X/banco_mcp/mcp_vector/bm25_fragmentos.py" 7e26c29c51ae47e394c5bd42424a3319eb45243840846df5f700aebfd82c414d
     "$X/banco_mcp/mcp_vector/servidor_mcp_vector.py" cd68f32948bb05fff7357fa6f3f572d3c1db53a5f5ebfbd41c83596e2c081b8b
     "$X/banco_mcp/comun_banco.py" f65ae54503d8205befe8a7c0399204726b609a2e15d69413be075716ee6f6d1d
     "$X/exploracion/sinteticas/resolucion.py" afe66ee951cd847bc4e02486c8086b06e7a588c59a48b385b2245e6214b6c51b
     "$X/exploracion/sinteticas/comun.py" 94c1d4fe0d31e75c5b673889af86b7bf3dbeee53e8142fef5189d0f8d067cca3
     "$X/exploracion/validar_anclas.py" 9efda31a0fdb251050aaded467b70b13ac2e7af598671e9fe78a0289b6c8aebc
     "$X/evaluacion/harness.py" fd267e833866f86850e43130e627b08d78e05523b97484696de0ab0c8c9fba9e
     "$X/evaluacion/loader.py" 5aba8b7a0aa46e8d5c4c83b33884b8cae7d0a099884a7d3bc935de4d3097af8b
     "$R/scripts/ucita2_indicadores_banco.py" 3a58e5be33f2e7b1903c7c07ccfba00ef135f3b8da930f62490449577810e920
     "$V/juez_b63.py" 4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b
     "$V/comun_b63.py" 631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc
     "$F/runner_b64/lista_H34.txt" 6d8ecc0e03eec8f2d5acc0d37889f820888a409233d5b227d88a640f72b6c931)
for f s in "${(@kv)SHA}"; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$s" ]] || { print -r -- "no da su sha256: ${f:t}"; exit 20; }
done
# 3. Las dos corridas
mkdir "$PR" || { print -r -- "la carpeta de las salidas ya existe"; exit 22; }
print -r -- "HEAD $(git -C "$R" --no-optional-locks rev-parse HEAD)" > "$PR/horas_pruebas_H6_corr.txt"
for n in 1 2; do
  date "+%Y-%m-%d %H:%M:%S %z la corrida $n: empieza" >> "$PR/horas_pruebas_H6_corr.txt"
  T="$SP/pruebas_H6_corr_corrida$n"
  cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/selftest_analizar_b64.py" \
    --clon "$X/banco_mcp/b63/v2/b2" --trabajo "$T/analisis" \
    --informe "$PR/informe_prueba_corrida${n}_analisis_B64.json" > "$PR/consola_prueba_corrida${n}_analisis_B64.txt" 2>&1
  print -r -- "analisis, corrida $n: sale con $?" >> "$PR/codigos_de_salida_pruebas_H6_corr.txt"
  cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/selftest_exactitud_de_cita_9_4_b64.py" \
    --clon "$X/banco_mcp/b63/v2/b2" --ucita "$R/scripts/ucita2_indicadores_banco.py" --trabajo "$T/exactitud" \
    --informe "$PR/informe_prueba_corrida${n}_exactitud_B64.json" > "$PR/consola_prueba_corrida${n}_exactitud_B64.txt" 2>&1
  print -r -- "exactitud, corrida $n: sale con $?" >> "$PR/codigos_de_salida_pruebas_H6_corr.txt"
  cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/controlar_juez_b64.py" \
    --juez-head "$X/banco_mcp/b63/v2/b2/juez_b63.py" --comun-head "$X/banco_mcp/b63/v2/b2/comun_b63.py" \
    --juez-corrida "$V/juez_b63.py" --comun-corrida "$V/comun_b63.py" \
    --salida "$PR/informe_prueba_corrida${n}_juez_B64.json" > "$PR/consola_prueba_corrida${n}_juez_B64.txt" 2>&1
  print -r -- "juez, corrida $n: sale con $?" >> "$PR/codigos_de_salida_pruebas_H6_corr.txt"
  cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/selftest_comandos_b64.py" \
    --comandos "$H6/comandos" --repo "$R" --runner "$F/runner_b64" --trabajo "$T/comandos" \
    --informe "$PR/informe_prueba_corrida${n}_comandos_B64.json" > "$PR/consola_prueba_corrida${n}_comandos_B64.txt" 2>&1
  print -r -- "comandos, corrida $n: sale con $?" >> "$PR/codigos_de_salida_pruebas_H6_corr.txt"
  date "+%Y-%m-%d %H:%M:%S %z la corrida $n: termina" >> "$PR/horas_pruebas_H6_corr.txt"
done
# 4. Las dos corridas, byte a byte
for k in analisis exactitud juez comandos; do
  for t in consola_prueba:txt informe_prueba:json; do
    a="$PR/${t%%:*}_corrida1_${k}_B64.${t##*:}"; b="$PR/${t%%:*}_corrida2_${k}_B64.${t##*:}"
    if cmp -s "$a" "$b"; then r=iguales; else r=DISTINTOS; fi
    print -r -- "$r  $(shasum -a 256 "$a" | cut -c1-64)  $(shasum -a 256 "$b" | cut -c1-64)  ${a:t} y ${b:t}"
  done
done > "$PR/comparacion_pruebas_H6_corr.txt"
exit 0
