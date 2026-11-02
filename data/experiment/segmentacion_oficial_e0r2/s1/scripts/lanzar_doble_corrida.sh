#!/bin/zsh
# Doble corrida de S1.2 sobre la copia, con el comando de correr_e0.py, en dos directorios distintos.
S="$1"; C="$S/copia"; PY="$2"
M="$C/data/experiment/segmentacion_oficial_e0r2/s1/manifiesto/segmentacion_oficial_e0r2_152.json"
cd "$C/data/experiment/reextraccion_v2/e0_chunking" || exit 1
for k in 1 2; do
  ( date "+inicio %Y-%m-%d %H:%M:%S %z" > "$S/trabajo/logs/corrida_$k.tiempo";
    PYTHONDONTWRITEBYTECODE=1 "$PY" -B correr_e0.py --version-e0 e0-r2 --manifiesto "$M" --salida "$S/corridas/corrida_$k" > "$S/trabajo/logs/corrida_$k.stdout" 2> "$S/trabajo/logs/corrida_$k.stderr";
    echo "rc=$?" >> "$S/trabajo/logs/corrida_$k.tiempo";
    date "+fin %Y-%m-%d %H:%M:%S %z" >> "$S/trabajo/logs/corrida_$k.tiempo" ) &
done
wait
