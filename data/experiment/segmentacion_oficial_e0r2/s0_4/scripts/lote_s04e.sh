#!/bin/zsh
# Lote de S0-4, con el TO manual aparte (pide unos 5 GB por proceso: dos lecturas suyas a la vez hacen paginar la
# máquina). Paso 1, en paralelo y sin manual (3 procesos cada una): todo apagado, solo S0-3, la segunda final y las
# reglas de S0-3 solas que faltaban (sobre los TOs de su censo de S0-3). Paso 2, de a una, solo manual: las mismas
# corridas que lo incluyen y el prototipo con todas las reglas (que en el paso 1 corre sobre los TOs que cambian en la
# corrida final). Paso 3: juntar (herr/juntar_por_to.py).
# Uso: lote_s04e.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=trabajo/logs/lote_s04e.log
S03="m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c"
SINM=$(cat trabajo/tos_sin_manual.txt)
CAMB=$(cat trabajo/tos_cambian_final_sin_manual.txt)
corre() {   # corre <raíz> <salida> <reglas> <workers> <tos>
  local raiz="$1" sal="$2" reglas="$3" w="$4" tos="$5" rc
  echo "E $sal inicio $(date '+%H:%M:%S') reglas=[$reglas] tos=[${tos[1,60]}]" >> "$L"
  rm -rf "corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers "$w" --tos "$tos" > "trabajo/logs/$sal.log" 2>&1
  rc=$?
  echo "E $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
corre proto4 off_x "" 3 "$SINM" &
corre proto4 s03cfg_x "$S03" 3 "$SINM" &
corre impl4 final2_x TODAS 3 "$SINM" &
corre proto4 final_proto_x TODAS 2 "$CAMB" &
( corre proto4 r_m2a_x m2a 1 ri_ao,ri_dsf,ri_icpipsp,seggar,verac
  corre proto4 r_m2b m2b 1 ri2_pm
  corre proto4 r_m2c_x m2c 1 ri_tar
  corre proto4 r_m3 m3 1 ri2_ae
  corre proto4 r_m5a m5a 1 fimipyme,ri_cc
  corre proto4 r_m5b m5b 1 ri2_ci,snp_cheq
  corre proto4 r_m5c m5c 1 ri_ai ) &
wait
corre impl4 final2_m TODAS 1 manual
corre proto4 off_m "" 1 manual
corre proto4 s03cfg_m "$S03" 1 manual
corre proto4 r_m2a_m m2a 1 manual
corre proto4 r_m2c_m m2c 1 manual
corre proto4 final_proto_m TODAS 1 manual
for x in off s03cfg final2; do
  PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py "corridas/$x" "corridas/${x}_x" "corridas/${x}_m" >> "$L" 2>&1
done
PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py corridas/r_m2a corridas/r_m2a_x corridas/r_m2a_m >> "$L" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py corridas/final_proto corridas/final_proto_x corridas/final_proto_m >> "$L" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py corridas/r_m2c corridas/r_m2c_x corridas/r_m2c_m >> "$L" 2>&1
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
true
