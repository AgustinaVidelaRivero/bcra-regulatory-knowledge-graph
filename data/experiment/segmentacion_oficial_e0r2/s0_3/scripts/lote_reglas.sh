#!/bin/zsh
# Lote de S0-3: cada regla sola (y dos variantes) sobre los 152 TOs (flujo A, 7 procesos) y sobre la tanda 0
# (flujo B, de a dos). Uso: lote_reglas.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=trabajo/logs/lote.log
VARS=(m1a=m1a m1b=m1b m2a=m2a m2b=m2b m2c=m2c m3=m3 m4=m4 m5a=m5a m5b=m5b m5c=m5c sin_m4=m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c m4_t0m4=m4)
flujo_a() {
  for v in $VARS; do
    n="${v%%=*}"; r="${v#*=}"; x=0; [[ "$n" == m4_t0m4 ]] && x=1
    echo "A $n inicio $(date '+%H:%M:%S')" >> $L
    rm -rf "corridas/v_$n"
    S0_3_M4_EN_TANDA0=$x S0_3_REGLAS="$r" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo proto3 --salida "corridas/v_$n" --workers 7 > "trabajo/logs/v_$n.log" 2>&1
    echo "A $n fin $(date '+%H:%M:%S') rc=$?" >> $L
  done
}
t0() {
  n="$1"; r="$2"; x=0; [[ "$n" == m4_t0m4 ]] && x=1
  rm -rf "corridas/t0_$n"
  S0_3_M4_EN_TANDA0=$x S0_3_REGLAS="$r" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0.py --codigo proto3 --salida "corridas/t0_$n" > "trabajo/logs/t0_$n.log" 2>&1
  echo "B $n fin $(date '+%H:%M:%S') rc=$?" >> $L
}
flujo_b() {
  local i=0
  for v in $VARS; do
    n="${v%%=*}"; r="${v#*=}"
    [[ "$n" == sin_m4 ]] && continue
    t0 "$n" "$r" &
    i=$((i+1)); if (( i % 2 == 0 )); then wait; fi
  done
  wait
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" > $L
flujo_a &
flujo_b &
wait
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> $L
