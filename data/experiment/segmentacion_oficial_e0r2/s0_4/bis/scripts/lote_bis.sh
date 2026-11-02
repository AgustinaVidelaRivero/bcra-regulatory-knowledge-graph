#!/bin/zsh
# Lote de S0-4a-bis (U-SEG-OFICIAL), USD 0, sin API, todo en el scratchpad. Raíces: impl4bis (código final, sin
# interruptores), proto4bis (con S0_4_REGLAS) y oc4bis (la variante de medición de ri_oc, S0_4_SD_MEDICION).
# Paso 1, en paralelo: final, segunda final y todo apagado sin manual (3 procesos cada una), y las tandas 0.
# Paso 2, en paralelo: S0-4a sin sdmax y el prototipo con todas sin manual, los selftests de E0 sobre la copia y la
# medición de ri_oc. Paso 3: manual de a una. Paso 4: uniones. Paso 5: selftest de claves sobre la copia.
# Uso: lote_bis.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=bis/logs/lote_bis.log
SINM=$(cat trabajo/tos_sin_manual.txt)
CAMB=$(tr ',' '\n' < trabajo/tos_cambian_final.txt | grep -v '^manual$' | paste -sd, -)
SINMAX="m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c,sd,sdg3,4a,4b,ap"
corre() {   # corre <raíz> <salida> <reglas> <workers> <tos> [medición]
  local raiz="$1" sal="$2" reglas="$3" w="$4" tos="$5" med="$6"
  echo "B $sal inicio $(date '+%H:%M:%S') reglas=[$reglas] med=[$med] tos=[${tos[1,40]}]" >> "$L"
  rm -rf "bis/corridas/$sal"
  S0_4_REGLAS="$reglas" S0_4_SD_MEDICION="$med" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py \
    --codigo "raices/$raiz" --salida "bis/corridas/$sal" --workers "$w" --tos "$tos" > "bis/logs/$sal.log" 2>&1
  local rc=$?
  echo "B $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
corre_t0() {   # corre_t0 <raíz> <salida> <reglas>
  local raiz="$1" sal="$2" reglas="$3"
  echo "B $sal inicio $(date '+%H:%M:%S') reglas=[$reglas]" >> "$L"
  rm -rf "bis/corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0_par.py --codigo "raices/$raiz" \
    --salida "bis/corridas/$sal" --workers 2 > "bis/logs/$sal.log" 2>&1
  local rc=$?
  echo "B $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
tandas0() {
  corre_t0 impl4bis t0_bis_final TODAS
  corre_t0 proto4bis t0_bis_off ""
  corre_t0 proto4bis t0_bis_sinmax "$SINMAX"
  corre_t0 proto4bis t0_bis_sdmax sdmax
  corre_t0 proto4bis t0_bis_sd_sdmax sd,sdmax
  corre_t0 impl4bis t0_bis_final2 TODAS
}
selftests() {
  local E="$S/copia/data/experiment/reextraccion_v2/e0_chunking" t rc O=bis/logs/selftests_e0_bis.txt
  rm -rf "$S/tmp_selftest_bis"; mkdir -p "$S/tmp_selftest_bis"
  : > "$O"
  for t in selftest_e0 selftest_b52 selftest_b581 selftest_b582 selftest_b583; do
    echo "B $t inicio $(date '+%H:%M:%S')" >> "$L"
    echo "== $t inicio $(date '+%H:%M:%S')" >> "$O"
    (cd "$E" && TMPDIR="$S/tmp_selftest_bis" PYTHONDONTWRITEBYTECODE=1 "$PY" -B -u "$t.py") >> "$O" 2>&1
    rc=$?
    echo "== $t rc=$rc fin $(date '+%H:%M:%S')" >> "$O"
    echo "B $t fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
  done
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
shasum -a 256 raices/{impl4bis,proto4bis,oc4bis}/data/experiment/reextraccion_v2/e0_chunking/{e0_lib,correr_e0,selftest_e0}.py \
  copia/data/experiment/reextraccion_v2/e0_chunking/{e0_lib,correr_e0,selftest_e0}.py >> "$L"
corre impl4bis bis_final_x TODAS 3 "$SINM" &
corre impl4bis bis_final2_x TODAS 3 "$SINM" &
corre proto4bis bis_off_x "" 3 "$SINM" &
tandas0 &
wait
corre proto4bis bis_sinmax_x "$SINMAX" 3 "$SINM" &
corre proto4bis bis_proto_x TODAS 3 "$CAMB" &
selftests &
corre oc4bis oc_med TODAS 1 ri_oc ri_oc &
corre proto4bis oc_ref TODAS 1 ri_oc &
wait
corre impl4bis bis_final_m TODAS 1 manual
corre impl4bis bis_final2_m TODAS 1 manual
corre proto4bis bis_off_m "" 1 manual
corre proto4bis bis_sinmax_m "$SINMAX" 1 manual
corre proto4bis bis_proto_m TODAS 1 manual
for x in bis_final bis_final2 bis_off bis_sinmax bis_proto; do
  PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py "bis/corridas/$x" "bis/corridas/${x}_x" "bis/corridas/${x}_m" >> "$L" 2>&1
done
echo "B claves inicio $(date '+%H:%M:%S')" >> "$L"
(cd copia && PYTHONDONTWRITEBYTECODE=1 "$PY" -B data/experiment/mantenimiento/code/selftest_clave_cache.py \
  --salida-r2b data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b --out "$S/bis/selftest_clave_cache_bis.json") \
  > bis/logs/selftest_claves_bis.txt 2>&1
echo "B claves fin $(date '+%H:%M:%S') rc=$?" >> "$L"
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
true
