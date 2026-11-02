#!/bin/zsh
# E0 de los 152 con el código de E0 de commits anteriores a la corrección (U-SEG-OFICIAL, S2, tramo 2; USD 0, sin API).
# Uso: zsh lote_e0_historicas_S2b.sh <repo> <raíz mínima de la E0 corregida> <trabajo> <commit> [<commit> …]
#   <repo>: solo se lee (git show); <raíz mínima>: la que arma s0_4/scripts/raiz_minima.sh desde una copia;
#   <trabajo>: carpeta fuera del repo. Por commit: copia la raíz mínima a <trabajo>/raiz_<commit>, pone ahí los tres
#   archivos de E0 de ese commit (e0_lib.py, correr_e0.py, e0_tablas.py, con git show) y corre los 152 con
#   s0_1/scripts/correr_152.py (de la copia: <trabajo>/../copia2 no hace falta; se toma de <repo> por git show HEAD).
# Las corridas van en secuencia: dos lecturas de `manual` a la vez hacen paginar la máquina.
set -e
R="$1"; RZ="$2"; T="$3"; shift 3
PY="$R/.venv/bin/python"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$T"
git -C "$R" show HEAD:data/experiment/segmentacion_oficial_e0r2/s0_1/scripts/correr_152.py > "$T/correr_152.py"
for c in "$@"; do
  D="$T/raiz_$c"
  rm -rf "$D"; cp -R "$RZ" "$D"
  for f in e0_lib.py correr_e0.py e0_tablas.py; do
    git -C "$R" show "$c:data/experiment/reextraccion_v2/e0_chunking/$f" > "$D/data/experiment/reextraccion_v2/e0_chunking/$f"
  done
  shasum -a 256 "$D/data/experiment/reextraccion_v2/e0_chunking/"{e0_lib.py,correr_e0.py,e0_tablas.py} | awk '{print $1}' > "$T/codigo_$c.sha256"
  print -r -- "inicio $c $(date '+%F %T')" >> "$T/tiempos.txt"
  "$PY" -B "$T/correr_152.py" --codigo "$D" --salida "$T/e0_$c" --workers 8 > "$T/corrida_$c.log" 2>&1
  print -r -- "fin $c rc=$? $(date '+%F %T')" >> "$T/tiempos.txt"
done
