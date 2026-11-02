#!/bin/zsh
# Corridas de los 152 por configuración de reglas de S0-5a (prototipo con interruptor), en una raíz mínima de la copia.
# Uso: lote_configuraciones.sh <scratchpad s05> <python> <config> [<config> …]   (config: NINGUNA, TODAS, r5a, …; sufijo
# «@2» para una segunda corrida de la misma configuración)
S="$1"; PY="$2"; shift 2
L="$S/trabajo/logs/lote.log"; mkdir -p "$S/trabajo/logs"
for cfg in "$@"; do
  sel="${cfg%@*}"; dir="$S/corridas/c_$(echo $cfg | tr '@,' '_-')"
  echo "inicio $cfg $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
  rm -rf "$dir"
  S0_5_REGLAS="$sel" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$S/copia/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py" \
    --codigo "$S/raices/proto" --salida "$dir" --workers 9 > "$S/trabajo/logs/c_$cfg.log" 2>&1
  echo "fin $cfg rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls $dir | wc -l) archivos" >> "$L"
done
