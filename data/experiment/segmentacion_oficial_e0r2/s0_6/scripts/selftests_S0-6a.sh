#!/bin/zsh
# Selftests de S0-6a sobre una copia del repo con el código del parche (CLAUDE.md §4.l; nunca sobre el repo):
# selftest_e0, b52, b581, b582, b583 y el de claves de la caché. Uso: selftests_S0-6a.sh <dir de logs> <copia> <python> <tmp>
O="$1"; C="$2"; PY="$3"; T="$4"; mkdir -p "$O" "$T"
E="$C/data/experiment/reextraccion_v2/e0_chunking"
cd "$E" || exit 1
shasum -a 256 e0_lib.py correr_e0.py selftest_e0.py e0_tablas.py > "$O/sha_codigo_selftests_S0-6a.txt"
TMPDIR="$T" PYTHONDONTWRITEBYTECODE=1 "$PY" -B selftest_e0.py > "$O/selftest_e0_S0-6a.txt" 2>&1
echo "rc=$?" >> "$O/selftest_e0_S0-6a.txt"
: > "$O/selftests_b5x_S0-6a.txt"
for b in b52 b581 b582 b583; do
  echo "== selftest_$b inicio $(date '+%H:%M:%S')" >> "$O/selftests_b5x_S0-6a.txt"
  TMPDIR="$T" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "selftest_$b.py" >> "$O/selftests_b5x_S0-6a.txt" 2>&1
  echo "== selftest_$b rc=$? fin $(date '+%H:%M:%S')" >> "$O/selftests_b5x_S0-6a.txt"
done
cd "$C" || exit 1
TMPDIR="$T" PYTHONDONTWRITEBYTECODE=1 "$PY" -B data/experiment/mantenimiento/code/selftest_clave_cache.py \
  --salida-r2b data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b --out "$O/selftest_clave_cache_S0-6a.json" \
  > "$O/selftest_claves_cache_S0-6a.txt" 2>&1
echo "rc=$?" >> "$O/selftest_claves_cache_S0-6a.txt"
echo "selftests fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$O/selftests_fin_S0-6a.txt"
