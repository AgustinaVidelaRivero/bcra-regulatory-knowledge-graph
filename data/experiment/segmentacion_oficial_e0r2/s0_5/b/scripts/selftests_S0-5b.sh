#!/bin/zsh
# Selftests de S0-5b sobre la copia del repo aplicado (CLAUDE.md §4.l): selftest_e0, b52, b581, b582, b583 y el de
# claves de la caché. Uso: selftests_S0-5b.sh <dir de trabajo> <copia> <python>
W="$1"; C="$2"; PY="$3"; O="$W/trabajo/logs"; mkdir -p "$O" "$W/tmp_selftest" "$W/salidas"
E="$C/data/experiment/reextraccion_v2/e0_chunking"
cd "$E" || exit 1
shasum -a 256 e0_lib.py correr_e0.py selftest_e0.py > "$O/sha_codigo_selftests.txt"
TMPDIR="$W/tmp_selftest" PYTHONDONTWRITEBYTECODE=1 "$PY" -B selftest_e0.py > "$O/selftest_e0.txt" 2>&1
echo "rc=$?" >> "$O/selftest_e0.txt"
: > "$O/selftests_b5x.txt"
for b in b52 b581 b582 b583; do
  echo "== selftest_$b inicio $(date '+%H:%M:%S')" >> "$O/selftests_b5x.txt"
  TMPDIR="$W/tmp_selftest" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "selftest_$b.py" >> "$O/selftests_b5x.txt" 2>&1
  echo "== selftest_$b rc=$? fin $(date '+%H:%M:%S')" >> "$O/selftests_b5x.txt"
done
cd "$C" || exit 1
TMPDIR="$W/tmp_selftest" PYTHONDONTWRITEBYTECODE=1 "$PY" -B data/experiment/mantenimiento/code/selftest_clave_cache.py \
  --salida-r2b data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b --out "$W/salidas/selftest_clave_cache_S0-5b.json" \
  > "$O/selftest_claves_cache.txt" 2>&1
echo "rc=$?" >> "$O/selftest_claves_cache.txt"
echo "selftests fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$O/selftests_fin.txt"
