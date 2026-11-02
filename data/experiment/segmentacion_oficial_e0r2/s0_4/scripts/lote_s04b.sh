#!/bin/zsh
# Lote de S0-4 (USD 0, sin API). Tres flujos en paralelo:
#  A, corridas de los 152 TOs (6 procesos): las de configuración (final, doble, todo apagado, solo S0-3, prototipo) y
#     las reglas que no están acotadas por una lista de TOs (4a y 4b, solas y sobre S0-3);
#  C, corridas sobre los TOs de una regla (2 procesos): las reglas acotadas por lista en el código (sd, sdg3, ap) y
#     cada regla de S0-3 sola sobre los TOs que lista su censo de S0-3 (s0_3/censos/censo_v_<regla>.json);
#  B, la tanda 0 (en paralelo por TO, 3 procesos): configuración final, doble, todo apagado y cada regla sola.
# Uso: lote_s04b.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=trabajo/logs/lote_s04b.log
S03="m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c"
SD5="ri_sef,nmcief,ri_ccna,ri_icpipsp,ri_cc"
corre() {   # corre <flujo> <raíz> <salida> <reglas> <workers> [tos]
  local fl="$1" raiz="$2" sal="$3" reglas="$4" w="$5" tos="$6" rc
  echo "$fl $sal inicio $(date '+%H:%M:%S') reglas=[$reglas] tos=[$tos]" >> "$L"
  rm -rf "corridas/$sal"
  if [[ "$fl" == B ]]; then
    S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0_par.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers "$w" > "trabajo/logs/$sal.log" 2>&1
  elif [[ -n "$tos" ]]; then
    S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers "$w" --tos "$tos" > "trabajo/logs/$sal.log" 2>&1
  else
    S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers "$w" > "trabajo/logs/$sal.log" 2>&1
  fi
  rc=$?
  echo "$fl $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
fA() {
  corre A impl4 final TODAS 6
  corre A proto4 off "" 6
  corre A proto4 s03cfg "$S03" 6
  corre A proto4 r_4a 4a 6
  corre A proto4 r_4b 4b 6
  corre A impl4 final2 TODAS 6
  corre A proto4 s03_4a "$S03,4a" 6
  corre A proto4 s03_4b "$S03,4b" 6
  corre A proto4 final_proto TODAS 6
}
fC() {
  corre C proto4 r_sd sd 2 "$SD5"
  corre C proto4 sin_sdg3 "$S03,sd,4a,4b,ap" 2 "$SD5"
  corre C proto4 s03_sd "$S03,sd" 2 "$SD5"
  corre C proto4 r_ap ap 2 ri_ai
  corre C proto4 s03_ap "$S03,ap" 2 ri_ai
  corre C proto4 r_m1a m1a 2 nmcief,ri_dcpc,ri_mmsef
  corre C proto4 r_m1b m1b 2 snp_cheq
  corre C proto4 r_m2a m2a 2 manual,ri_ao,ri_dsf,ri_icpipsp,seggar,verac
  corre C proto4 r_m2b m2b 2 ri2_pm
  corre C proto4 r_m2c m2c 2 manual,ri_tar
  corre C proto4 r_m3 m3 2 ri2_ae
  corre C proto4 r_m5a m5a 2 fimipyme,ri_cc
  corre C proto4 r_m5b m5b 2 ri2_ci,snp_cheq
  corre C proto4 r_m5c m5c 2 ri_ai
}
fB() {
  corre B impl4 t0_final TODAS 3
  corre B proto4 t0_off "" 3
  for r in sd sdg3 4a 4b ap m1a m1b m2a m2b m2c m3 m5a m5b m5c; do
    if [[ "$r" == sdg3 ]]; then corre B proto4 t0_sdg3 sd,sdg3 3; else corre B proto4 "t0_$r" "$r" 3; fi
  done
  corre B impl4 t0_final2 TODAS 3
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
fA & fC & fB & wait
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
true
