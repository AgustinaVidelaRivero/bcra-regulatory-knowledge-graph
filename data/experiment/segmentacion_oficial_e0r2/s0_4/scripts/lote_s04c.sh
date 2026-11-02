#!/bin/zsh
# Lote complementario de S0-4: 4a y 4b solas y sobre S0-3, sobre los 52 TOs con algún punto candidato (la condición
# común de 4a y 4b en la estructura de la base de S1 o de S0-3: trabajo/tos_candidatos_4ab.txt); en los demás TOs las
# dos reglas no pueden actuar y la referencia es la base. Uso: lote_s04c.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=trabajo/logs/lote_s04c.log
S03="m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c"
TOS=$(cat trabajo/tos_candidatos_4ab.txt)
corre() {
  local sal="$1" reglas="$2" rc
  echo "C2 $sal inicio $(date '+%H:%M:%S') reglas=[$reglas]" >> "$L"
  rm -rf "corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo raices/proto4 --salida "corridas/$sal" --workers 2 --tos "$TOS" > "trabajo/logs/$sal.log" 2>&1
  rc=$?
  echo "C2 $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
corre r_4a_s 4a
corre r_4b_s 4b
corre s03_4a_s "$S03,4a"
corre s03_4b_s "$S03,4b"
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
true
