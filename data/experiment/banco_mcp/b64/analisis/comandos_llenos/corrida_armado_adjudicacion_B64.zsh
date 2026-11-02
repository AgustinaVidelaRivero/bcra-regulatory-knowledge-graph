#!/bin/zsh
# El armado de la adjudicación de B6.4 (§5): armar_adjudicacion_b64.py, después de la lectura tolerante. Escribe el material para la
# autora en $F/analisis_b64_corr/adjudicacion/para_leer/ (que tiene que estar vacía) y la clave en el scratchpad, para el paquete de la
# revisión. Con la corrección del H-6 (decisión 3), la población suma las respuestas sin lectura que dejó el envoltorio de la lectura
# tolerante (aplicacion/agregados_sin_lectura_b64.json), enteras. Controla antes los sha256: la lista y el sello de la corrección del H-6 y
# el código de B6.4 en ellos, el código de B6.3 en un clon de HEAD (por rutas explícitas), el juez de la corrida (b64/v1) y la entrada; y
# que la lectura tolerante se haya aplicado con su prueba dada. Lo que todavía no existe va como PENDIENTE, y el comando no corre hasta
# que se llene.
# Uso: zsh corrida_armado_adjudicacion_B64.zsh <scratchpad>
set -u
R="${0:A:h:h:h:h:h:h:h}"; F="${BCRA_KG_FUERA_DEL_REPO:-$R/fuera_del_repo}"; SP="$1"
PY="${BCRA_KG_PYTHON:-python3}"; H6="$F/analisis_b64_corr"
ENTRADA="$R/data/experiment/banco_mcp/b64/entrada_B64.json"            # H-3: la entrada de B6.4 (llenado, §382)
SHA_ENTRADA="9064066b5caaec6b373087f37c429cbf6058ec0c07ee89a91380d8f0c040932c"        # H-3: su sha256 (llenado, §382)
BANCO="$F/banco_b64"           # §4 y H-4
SA="$H6/salidas/a"             # la de corrida_lectura_tolerante_B64.zsh
for v in ENTRADA SHA_ENTRADA; do [[ "${(P)v}" == PENDIENTE ]] && { print -r -- "falta llenar $v"; exit 22; }; done
# 1. La lista y el sello de la corrección del H-6, y el código de B6.4 en la lista
grep -qF "sha256: $(shasum -a 256 "$H6/lista_H6_corr.txt" | cut -c1-64)" "$H6/sello_H6_corr.txt" || { print -r -- "la lista no es la del sello de la corrección del H-6"; exit 20; }
for f in codigo/armar_adjudicacion_b64.py codigo/analizar_b64.py codigo/aplicar_lectura_tolerante_b64.py; do
  grep -qF "$(shasum -a 256 "$H6/$f" | cut -c1-64)  $(stat -f %z "$H6/$f")  $f" "$H6/lista_H6_corr.txt" || { print -r -- "no es el de la lista: $f"; exit 20; }
done
# 2. El clon de HEAD, solo con lo que se importa y lee, por rutas explícitas, y sus sha256; el juez de la corrida; la entrada
mkdir "$SP/clon_head_armado_B64" && git -C "$R" --no-optional-locks archive HEAD \
  data/experiment/banco_mcp/b63/v2/b2/comun_b63.py data/experiment/banco_mcp/b63/v2/b2/juez_b63.py \
  data/experiment/banco_mcp/comun_banco.py data/experiment/banco_mcp/lectura_tolerante_juez.py \
  data/experiment/ev2_juez/juez.py data/experiment/ev2_juez/mapping.py data/experiment/ev2_juez/prompt_juez_v1.md \
  data/experiment/evaluacion/llm_cache.py \
  data/experiment/banco_mcp/b63/analisis/codigo/analizar_b63.py data/experiment/banco_mcp/b63/analisis/codigo/aplicar_lectura_tolerante_b63.py \
  data/experiment/banco_mcp/b63/analisis/codigo/armar_adjudicacion_b63.py \
  | tar -x -C "$SP/clon_head_armado_B64" || { print -r -- "no se pudo armar el clon"; exit 21; }
X="$SP/clon_head_armado_B64/data/experiment"; C="$X/banco_mcp/b63/analisis/codigo"
typeset -A SHA
SHA=("$C/analizar_b63.py" 9a9d04914c17b0e5604d8f6144f6ef84fc6b37ae3318b0a434d7bbf5ab3cdceb
     "$C/aplicar_lectura_tolerante_b63.py" 5f608a58eaaa65cac7ea1cc55585c9fb70b39df9d9079122230b0e971f774372
     "$C/armar_adjudicacion_b63.py" 32daed5cbe1608097592d3cdb6301713df18258ca8bcc98d4d55429b43962aba
     "$R/data/experiment/banco_mcp/b64/v1/juez_b63.py" 4fa095019dfa5d085ca5eeff1acc40f05f50ee482de9e649d9d042d03012e53b
     "$R/data/experiment/banco_mcp/b64/v1/comun_b63.py" 631037e968174a5743869a27d0a5b4275cf5bb5cdaa2bc1dfc3a49890d6998cc
     "$ENTRADA" "$SHA_ENTRADA")
for f s in "${(@kv)SHA}"; do
  [[ "$(shasum -a 256 "$f" | cut -c1-64)" == "$s" ]] || { print -r -- "no da su sha256: ${f:t}"; exit 20; }
done
# 3. La lectura tolerante, aplicada con su prueba dada, y las respuestas sin lectura del envoltorio
grep -qx 0 "$SA/codigo_de_salida_aplicacion_B64.txt" && grep -qF '"prueba_da": true' "$SA/aplicacion/informe_lectura_tolerante_b63.json" \
  && [[ -f "$SA/aplicacion/agregados_sin_lectura_b64.json" ]] \
  || { print -r -- "la lectura tolerante no está aplicada con su prueba dada"; exit 23; }
# 4. El armado
cd "$SP" && B64_CODIGO_B63="$C" PYTHONDONTWRITEBYTECODE=1 "$PY" -I -B "$H6/codigo/armar_adjudicacion_b64.py" --salida-b64 "$BANCO" \
  --entrada "$ENTRADA" --clon "$X/banco_mcp/b63/v2/b2" --aplicacion "$SA/aplicacion" --para-leer "$H6/adjudicacion/para_leer" \
  --clave "$SP/clave_para_despues_B64" --informe "$SA/informe_adjudicacion_b64.json" > "$SA/consola_armado_adjudicacion_B64.txt" 2>&1
print -r -- "$?" > "$SA/codigo_de_salida_armado_adjudicacion_B64.txt"
exit 0
