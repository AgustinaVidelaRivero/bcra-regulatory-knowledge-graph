#!/bin/zsh
# Lote de corridas de E0: cada argumento es <tipo>:<raíz>:<salida>[:<reglas>] con tipo 152, t0 o t0p (tanda 0 en paralelo); corre en serie los
# de tipo 152 (W procesos) y, en paralelo con ellos, los t0 en serie. Uso: lote.sh <scratchpad> <python> <W> <log> args…
S="$1"; PY="$2"; W="$3"; L="$4"; shift 4
cd "$S" || exit 1
A=(); B=()
for x in "$@"; do if [[ "$x" == 152:* ]]; then A+=("$x"); else B+=("$x"); fi; done
uno() {
  local tipo raiz sal reglas; tipo="${1%%:*}"; local r1="${1#*:}"; raiz="${r1%%:*}"; local r2="${r1#*:}"; sal="${r2%%:*}"
  reglas=""; [[ "$r2" == *:* ]] && reglas="${r2#*:}"
  echo "$tipo $sal inicio $(date '+%H:%M:%S') reglas=[$reglas]" >> "$L"
  rm -rf "corridas/$sal"
  if [[ "$tipo" == 152 ]]; then
    S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers "$W" > "trabajo/logs/$sal.log" 2>&1
  elif [[ "$tipo" == t0p ]]; then
    S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0_par.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers 4 > "trabajo/logs/$sal.log" 2>&1
  else
    S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0.py --codigo "raices/$raiz" --salida "corridas/$sal" > "trabajo/logs/$sal.log" 2>&1
  fi
  local rc=$?
  echo "$tipo $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
fa() { for x in "${A[@]}"; do uno "$x"; done }
fb() { for x in "${B[@]}"; do uno "$x"; done }
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
fa & fb & wait
true
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
