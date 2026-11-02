#!/bin/zsh
# Selftests de S0-6b sobre una copia del repo con el código del repo (el parche aplicado) (CLAUDE.md §4.l; nunca sobre el repo):
# selftest_e0, b52, b581, b582 y b583 (el de claves de la caché, después del paso 3: clave_cache_S0-6b.sh). Uso: selftests_S0-6b.sh <dir de logs> <copia> <python> <tmp>
O="$1"; C="$2"; PY="$3"; T="$4"; mkdir -p "$O" "$T"
E="$C/data/experiment/reextraccion_v2/e0_chunking"
cd "$E" || exit 1
shasum -a 256 e0_lib.py correr_e0.py selftest_e0.py e0_tablas.py > "$O/sha_codigo_selftests_S0-6b.txt"
TMPDIR="$T" PYTHONDONTWRITEBYTECODE=1 "$PY" -B selftest_e0.py > "$O/selftest_e0_S0-6b.txt" 2>&1
echo "rc=$?" >> "$O/selftest_e0_S0-6b.txt"
: > "$O/selftests_b5x_S0-6b.txt"
for b in b52 b581 b582 b583; do
  echo "== selftest_$b inicio $(date '+%H:%M:%S')" >> "$O/selftests_b5x_S0-6b.txt"
  TMPDIR="$T" PYTHONDONTWRITEBYTECODE=1 "$PY" -B "selftest_$b.py" >> "$O/selftests_b5x_S0-6b.txt" 2>&1
  echo "== selftest_$b rc=$? fin $(date '+%H:%M:%S')" >> "$O/selftests_b5x_S0-6b.txt"
done
echo "selftests fin $(date '+%Y-%m-%d %H:%M:%S')" >> "$O/selftests_fin_S0-6b.txt"
