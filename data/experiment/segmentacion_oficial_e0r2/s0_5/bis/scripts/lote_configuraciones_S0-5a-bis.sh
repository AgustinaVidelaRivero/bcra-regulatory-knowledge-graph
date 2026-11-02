#!/bin/zsh
# Corridas de los 152 de S0-5a-bis: por configuración de reglas con el prototipo (interruptor S0_5_REGLAS) y, con
# «FINAL», con el código final sin interruptor; en raíces mínimas armadas desde la copia.
# Uso: lote_configuraciones_S0-5a-bis.sh <dir de trabajo> <copia> <python> <config> [<config> …]
#   config: NINGUNA, TODAS, r5a, r5a2, r5b, r5c, r5d, r5e, r5f o FINAL
W="$1"; C="$2"; PY="$3"; shift 3
L="$W/trabajo/logs/lote.log"; mkdir -p "$W/trabajo/logs"
for cfg in "$@"; do
  dir="$W/corridas/c_$cfg"
  echo "inicio $cfg $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
  rm -rf "$dir"
  if [[ "$cfg" == "FINAL" ]]; then
    PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$C/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py" \
      --codigo "$W/raices/final" --salida "$dir" --workers 9 > "$W/trabajo/logs/c_$cfg.log" 2>&1
  else
    S0_5_REGLAS="$cfg" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$C/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py" \
      --codigo "$W/raices/proto" --salida "$dir" --workers 9 > "$W/trabajo/logs/c_$cfg.log" 2>&1
  fi
  echo "fin $cfg rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls $dir | wc -l) archivos" >> "$L"
done
