#!/bin/zsh
# Selftest de claves de la caché de S0-6b, después del paso 3 (la tabla de reprocesamiento corregida), sobre una copia del
# repo (CLAUDE.md §4.l; nunca sobre el repo): copia a la copia la tabla del repo y corre el selftest.
# Uso: clave_cache_S0-6b.sh <dir de salida> <copia> <repo> <python> <tmp>
O="$1"; C="$2"; R="$3"; PY="$4"; T="$5"; mkdir -p "$O" "$T"
cp "$R/data/experiment/mantenimiento/tabla_reprocesamiento.md" "$C/data/experiment/mantenimiento/tabla_reprocesamiento.md"
shasum -a 256 "$C/data/experiment/mantenimiento/tabla_reprocesamiento.md" | cut -c1-64 > "$O/sha_tabla_clave_cache_S0-6b.txt"
cd "$C" || exit 1
TMPDIR="$T" PYTHONDONTWRITEBYTECODE=1 "$PY" -B data/experiment/mantenimiento/code/selftest_clave_cache.py \
  --salida-r2b data/experiment/reextraccion_v2/corpus_tanda0/salida_r2b --out "$O/selftest_clave_cache_S0-6b.json" \
  > "$O/selftest_claves_cache_S0-6b.txt" 2>&1
echo "rc=$?" >> "$O/selftest_claves_cache_S0-6b.txt"
