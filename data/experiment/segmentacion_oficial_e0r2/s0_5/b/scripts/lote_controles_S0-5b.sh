#!/bin/zsh
# Controles de S0-5b (USD 0, sin API): los 152 dos veces y la tanda 0, con el código de E0 del repo ya aplicado,
# desde una raíz mínima armada de la copia (nunca del repo); las salidas quedan en el directorio de trabajo.
# Uso: lote_controles_S0-5b.sh <dir de trabajo> <copia> <python>
W="$1"; C="$2"; PY="$3"
L="$W/trabajo/logs/lote.log"; mkdir -p "$W/trabajo/logs" "$W/corridas"
H="$C/data/experiment/segmentacion_oficial_e0r2/s0_1/scripts"
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
for k in 1 2; do
  rm -rf "$W/corridas/c152_$k"
  echo "inicio c152_$k $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
  PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$H/correr_152.py" --codigo "$W/raices/repo" --salida "$W/corridas/c152_$k" \
    --workers 9 > "$W/trabajo/logs/c152_$k.log" 2>&1
  echo "fin c152_$k rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls "$W/corridas/c152_$k" | wc -l) entradas" >> "$L"
done
rm -rf "$W/corridas/t0"
echo "inicio t0 $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
PYTHONDONTWRITEBYTECODE=1 "$PY" -B "$H/correr_tanda0.py" --codigo "$W/raices/repo" --salida "$W/corridas/t0" \
  > "$W/trabajo/logs/t0.log" 2>&1
echo "fin t0 rc=$? $(date '+%Y-%m-%d %H:%M:%S') $(ls "$W/corridas/t0" | wc -l) entradas" >> "$L"
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
