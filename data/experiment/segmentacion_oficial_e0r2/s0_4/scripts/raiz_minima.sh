#!/bin/zsh
# Arma una raíz mínima de código de E0 en <destino> a partir de la copia <copia> (nunca del repo) y deja en su
# e0_chunking/ los tres archivos de <dir_codigo> (e0_lib.py, correr_e0.py, selftest_e0.py).
# Uso: raiz_minima.sh <copia> <destino> <dir_codigo>
C="$1"; D="$2"; K="$3"
rm -rf "$D"; mkdir -p "$D/data/experiment/segmentacion_84/b584_particion" "$D/data/experiment/reextraccion_v2/manifiestos" "$D/data/experiment/escalado_prep"
cp -R "$C/data/experiment/subset" "$D/data/experiment/subset"
cp "$C/data/experiment/segmentacion_84/b584_particion/conteos_b584.json" "$D/data/experiment/segmentacion_84/b584_particion/"
cp "$C/data/experiment/reextraccion_v2/manifiesto_corpus.py" "$D/data/experiment/reextraccion_v2/"
cp "$C/data/experiment/reextraccion_v2/manifiestos/tanda0_10tos.json" "$D/data/experiment/reextraccion_v2/manifiestos/"
cp -R "$C/data/experiment/escalado_prep/pdfs" "$D/data/experiment/escalado_prep/pdfs"
mkdir -p "$D/data/experiment/reextraccion_v2/e0_chunking"
for f in e0_tablas.py healthcheck_e0.py selftest_b52.py selftest_b581.py selftest_b582.py selftest_b583.py; do
  cp "$C/data/experiment/reextraccion_v2/e0_chunking/$f" "$D/data/experiment/reextraccion_v2/e0_chunking/"; done
for f in e0_lib.py correr_e0.py selftest_e0.py; do cp "$K/$f" "$D/data/experiment/reextraccion_v2/e0_chunking/"; done
find "$D" -type l | wc -l
