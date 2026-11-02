#!/bin/zsh
# Controles finales de S0-6a (USD 0, sin API): los 152 dos veces y la tanda 0 dos veces, con el código final del parche,
# desde una raíz mínima armada de una copia (nunca del repo); las salidas quedan en el directorio de trabajo.
# Uso: lote_controles_S0-6a.sh <dir de trabajo> <copia> <raíz final> <python>
W="$1"; C="$2"; R="$3"; PY="$4"
L="$W/logs/lote_controles.log"; mkdir -p "$W/logs" "$W/corridas"
H="$C/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts"
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
shasum -a 256 "$R/data/experiment/reextraccion_v2/e0_chunking/"{e0_lib,correr_e0,e0_tablas}.py >> "$L"
for k in 1 2; do
  rm -rf "$W/corridas/c152_$k"
  echo "inicio c152_$k $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
  PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$H/correr_152.py" --codigo "$R" --salida "$W/corridas/c152_$k" --workers 9 \
    > "$W/logs/c152_$k.log" 2>&1
  echo "fin c152_$k rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls "$W/corridas/c152_$k" | wc -l) entradas" >> "$L"
done
for k in 1 2; do
  rm -rf "$W/corridas/t0_$k"
  echo "inicio t0_$k $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
  PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$H/correr_tanda0.py" --codigo "$R" --salida "$W/corridas/t0_$k" > "$W/logs/t0_$k.log" 2>&1
  echo "fin t0_$k rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls "$W/corridas/t0_$k" | wc -l) entradas" >> "$L"
done
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
