#!/bin/zsh
# Lote de S0-4 tras el corte de la sesión: rehace enteras las corridas que quedaron a medias y completa las que no
# empezaron (ESTADO_S0-4a.md). Paso 1, en paralelo: todo apagado, solo S0-3 y la segunda final, sin manual (3 procesos
# cada una), y la segunda tanda 0 final. Paso 2: manual de a una (las corridas que lo incluyen), en paralelo con los
# selftests de E0 sobre la copia. Paso 3: uniones (herr/juntar_por_to.py). Uso: lote_s04f.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=trabajo/logs/lote_s04f.log
S03="m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c"
SINM=$(cat trabajo/tos_sin_manual.txt)
corre() {   # corre <raíz> <salida> <reglas> <workers> <tos>
  local raiz="$1" sal="$2" reglas="$3" w="$4" tos="$5" rc
  echo "F $sal inicio $(date '+%H:%M:%S') reglas=[$reglas] tos=[${tos[1,40]}]" >> "$L"
  rm -rf "corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers "$w" --tos "$tos" > "trabajo/logs/$sal.log" 2>&1
  rc=$?
  echo "F $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
corre_t0() {
  local raiz="$1" sal="$2" reglas="$3" rc
  echo "F $sal inicio $(date '+%H:%M:%S') reglas=[$reglas]" >> "$L"
  rm -rf "corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0_par.py --codigo "raices/$raiz" --salida "corridas/$sal" --workers 2 > "trabajo/logs/$sal.log" 2>&1
  rc=$?
  echo "F $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
selftests() {
  local E="$S/copia/data/experiment/reextraccion_v2/e0_chunking" t rc
  rm -rf "$S/tmp_selftest"; mkdir -p "$S/tmp_selftest"
  : > trabajo/logs/selftests_e0_S0-4.txt
  for t in selftest_e0 selftest_b52 selftest_b581 selftest_b582 selftest_b583; do
    echo "F $t inicio $(date '+%H:%M:%S')" >> "$L"
    echo "== $t inicio $(date '+%H:%M:%S')" >> trabajo/logs/selftests_e0_S0-4.txt
    (cd "$E" && TMPDIR="$S/tmp_selftest" PYTHONDONTWRITEBYTECODE=1 "$PY" -B -u "$t.py") >> trabajo/logs/selftests_e0_S0-4.txt 2>&1
    rc=$?
    echo "== $t rc=$rc fin $(date '+%H:%M:%S')" >> trabajo/logs/selftests_e0_S0-4.txt
    echo "F $t fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
  done
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
corre proto4 off_x "" 3 "$SINM" &
corre proto4 s03cfg_x "$S03" 3 "$SINM" &
corre impl4 final2_x TODAS 3 "$SINM" &
corre_t0 impl4 t0_final2 TODAS &
wait
selftests &
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
PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py corridas/r_m2c corridas/r_m2c_x corridas/r_m2c_m >> "$L" 2>&1
PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py corridas/final_proto corridas/final_proto_x corridas/final_proto_m >> "$L" 2>&1
wait
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
true
