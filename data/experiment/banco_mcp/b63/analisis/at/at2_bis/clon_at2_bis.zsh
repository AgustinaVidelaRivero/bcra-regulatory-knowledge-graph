#!/bin/zsh
# El clon de la AT2-bis: git archive HEAD de las tres rutas, con las exclusiones de la AT2 y las cuatro nuevas.
SP=${0:A:h:h}
R="${0:A:h:h:h:h:h:h:h:h}"
K="$SP/trabajo_at2bis/corrida/copia_head"
[[ -e "$K" ]] && { print -r -- "el clon ya existe: no se toca"; exit 1 }
mkdir -p "$K" || exit 1
git -C "$R" archive HEAD -- \
  data/experiment/banco_mcp data/experiment/ev2_juez data/experiment/evaluacion/llm_cache.py \
  ':(exclude,glob)**/*_SOLO_MESA*' ':(exclude,glob)**/*_SOLO_MESA*/**' \
  ':(exclude,glob)**/NO_ABRIR_*' ':(exclude,glob)**/NO_ABRIR_*/**' \
  ':(exclude)data/experiment/banco_mcp/a2_2/adjudicacion' \
  ':(exclude)data/experiment/banco_mcp/smoke/preguntas_smoke.json' \
  ':(exclude)data/experiment/ev2_juez/gold_q12_ajuste' \
  ':(exclude)data/experiment/ev2_juez/gold_q12_verificacion' \
  ':(exclude,glob)**/.env*' ':(exclude,glob)**/*.env' \
  | tar -x -C "$K"
print -r -- "git archive | tar: ${pipestatus[1]} ${pipestatus[2]}"
