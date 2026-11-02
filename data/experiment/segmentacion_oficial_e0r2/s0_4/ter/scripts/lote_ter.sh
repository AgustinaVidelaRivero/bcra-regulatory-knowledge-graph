#!/bin/zsh
# Lote de S0-4a-ter (U-SEG-OFICIAL), USD 0, sin API, todo en el scratchpad. Raíces: impl4ter (código final, sin
# interruptores) y proto4ter (con S0_4_REGLAS). Paso 1, en paralelo: final, segunda final y todo apagado sin manual, y
# las tandas 0. Paso 2, en paralelo: S0-4a-bis (las reglas nuevas apagadas) y el prototipo con todas sin manual, los
# selftests de E0 sobre la copia y las corridas «todas menos una» en los seis TOs de las reglas de sub-documento.
# Paso 3: manual de a una. Paso 4: uniones. Paso 5: selftest de claves sobre la copia. Uso: lote_ter.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
L=ter/logs/lote_ter.log
SINM=$(cat trabajo/tos_sin_manual.txt)
CAMB=$(tr ',' '\n' < ter/tos_cambian_ter.txt | grep -v '^manual$' | paste -sd, -)
SEIS=ri_oc,ri_ccna,ri_sef,nmcief,ri_icpipsp,ri_cc
S03="m1a,m1b,m2a,m2b,m2c,m3,m5a,m5b,m5c"
BIS="$S03,sd,sdg3,sdmax,4a,4b,ap"
NUEVAS="sdr1,apl,sdl,sdlh,sdla"
menos() { local x="$1"; echo "$BIS,$NUEVAS" | tr ',' '\n' | grep -vx "$x" | paste -sd, -; }
corre() {   # corre <raíz> <salida> <reglas> <workers> <tos>
  local raiz="$1" sal="$2" reglas="$3" w="$4" tos="$5"
  echo "T $sal inicio $(date '+%H:%M:%S') reglas=[$reglas] tos=[${tos[1,40]}]" >> "$L"
  rm -rf "ter/corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_152.py --codigo "raices/$raiz" \
    --salida "ter/corridas/$sal" --workers "$w" --tos "$tos" > "ter/logs/$sal.log" 2>&1
  local rc=$?
  echo "T $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
corre_t0() {   # corre_t0 <raíz> <salida> <reglas>
  local raiz="$1" sal="$2" reglas="$3"
  echo "T $sal inicio $(date '+%H:%M:%S') reglas=[$reglas]" >> "$L"
  rm -rf "ter/corridas/$sal"
  S0_4_REGLAS="$reglas" PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/correr_tanda0_par.py --codigo "raices/$raiz" \
    --salida "ter/corridas/$sal" --workers 2 > "ter/logs/$sal.log" 2>&1
  local rc=$?
  echo "T $sal fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
}
tandas0() {
  corre_t0 impl4ter t0_ter_final TODAS
  corre_t0 proto4ter t0_ter_off ""
  corre_t0 proto4ter t0_ter_bis "$BIS"
  local r
  for r in sdr1 apl sdl sdlh sdla; do corre_t0 proto4ter t0_ter_$r "$BIS,$r"; done
  corre_t0 proto4ter t0_ter_nuevas "$NUEVAS"
  corre_t0 impl4ter t0_ter_final2 TODAS
}
menos_una() {
  local r
  for r in sdg3 sdmax sdr1 apl sdl sdlh sdla; do corre proto4ter ter_sin_$r "$(menos $r)" 2 "$SEIS"; done
}
selftests() {
  local E="$S/copia/data/experiment/reextraccion_v2/e0_chunking" t rc O=ter/logs/selftests_e0_ter.txt
  rm -rf "$S/tmp_selftest_ter"; mkdir -p "$S/tmp_selftest_ter"
  : > "$O"
  for t in selftest_e0 selftest_b52 selftest_b581 selftest_b582 selftest_b583; do
    echo "T $t inicio $(date '+%H:%M:%S')" >> "$L"
    echo "== $t inicio $(date '+%H:%M:%S')" >> "$O"
    (cd "$E" && TMPDIR="$S/tmp_selftest_ter" PYTHONDONTWRITEBYTECODE=1 "$PY" -B -u "$t.py") >> "$O" 2>&1
    rc=$?
    echo "== $t rc=$rc fin $(date '+%H:%M:%S')" >> "$O"
    echo "T $t fin $(date '+%H:%M:%S') rc=$rc" >> "$L"
  done
}
echo "lote inicio $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
shasum -a 256 raices/{impl4ter,proto4ter}/data/experiment/reextraccion_v2/e0_chunking/{e0_lib,correr_e0,selftest_e0}.py \
  copia/data/experiment/reextraccion_v2/e0_chunking/{e0_lib,correr_e0,selftest_e0}.py >> "$L"
corre impl4ter ter_final_x TODAS 3 "$SINM" &
corre impl4ter ter_final2_x TODAS 3 "$SINM" &
corre proto4ter ter_off_x "" 3 "$SINM" &
tandas0 &
wait
corre proto4ter ter_bis_x "$BIS" 3 "$SINM" &
corre proto4ter ter_proto_x TODAS 3 "$CAMB" &
selftests &
menos_una &
wait
corre impl4ter ter_final_m TODAS 1 manual
corre impl4ter ter_final2_m TODAS 1 manual
corre proto4ter ter_off_m "" 1 manual
corre proto4ter ter_bis_m "$BIS" 1 manual
corre proto4ter ter_proto_m TODAS 1 manual
for x in ter_final ter_final2 ter_off ter_bis ter_proto; do
  PYTHONDONTWRITEBYTECODE=1 "$PY" -B herr/juntar_por_to.py "ter/corridas/$x" "ter/corridas/${x}_x" "ter/corridas/${x}_m" >> "$L" 2>&1
done
echo "T claves inicio $(date '+%H:%M:%S')" >> "$L"
(cd copia && PYTHONDONTWRITEBYTECODE=1 "$PY" -B data/experiment/mantenimiento/code/selftest_clave_cache.py \
  --salida-r2b data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b --out "$S/ter/selftest_clave_cache_ter.json") \
  > ter/logs/selftest_claves_ter.txt 2>&1
echo "T claves fin $(date '+%H:%M:%S') rc=$?" >> "$L"
echo "lote fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$L"
true
