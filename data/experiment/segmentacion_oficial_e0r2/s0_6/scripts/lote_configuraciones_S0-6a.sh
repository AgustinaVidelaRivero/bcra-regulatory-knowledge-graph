#!/bin/zsh
# Corridas de los 152 de S0-6a (U-SEG-OFICIAL; USD 0, sin API): por configuración de reglas con el prototipo (S0_6_REGLAS)
# y, con «FINAL», con el código final sin interruptor. Corre sobre una copia del repo, nunca sobre el repo (CLAUDE.md §4.l).
# Uso: lote_configuraciones_S0-6a.sh <copia> <raíz del prototipo> <raíz final> <dir de corridas> <config> [<config> …]
#   config: NINGUNA, TODAS, a..k, FINAL, o «x,y»; las raíces las arma s0_4/scripts/raiz_minima.sh (el prototipo, con
#   armar_proto_S0-6a.py). Variables: PY (el python del entorno; por defecto python3), TOS (lista de TOs separada por
#   comas, opcional), SUF (sufijo del directorio de salida, opcional).
C="$1"; PROTO="$2"; FINAL="$3"; D="$4"; shift 4; PY="${PY:-python3}"
L="$D/lote.log"; mkdir -p "$D"
for cfg in "$@"; do
  dir="$D/c_${cfg//,/+}${SUF:-}"
  echo "inicio $cfg $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
  rm -rf "$dir"
  extra=(); [[ -n "$TOS" ]] && extra=(--tos "$TOS")
  if [[ "$cfg" == "FINAL" ]]; then
    PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$C/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py" \
      --codigo "$FINAL" --salida "$dir" --workers 9 $extra > "$D/c_${cfg//,/+}${SUF:-}.log" 2>&1
  else
    S0_6_REGLAS="$cfg" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$C/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py" \
      --codigo "$PROTO" --salida "$dir" --workers 9 $extra > "$D/c_${cfg//,/+}${SUF:-}.log" 2>&1
  fi
  echo "fin $cfg rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls $dir | wc -l) archivos" >> "$L"
  tail -1 "$D/c_${cfg//,/+}${SUF:-}.log"
done
