#!/bin/zsh
# Controles duros de S0-4a-bis sobre las corridas de lote_bis.sh (USD 0, solo lectura). Uso: controles_bis.sh <scratchpad> <python>
S="$1"; PY="$2"; cd "$S" || exit 1
T0=copia/data/experiment/reextraccion_v2/e0_chunking/salida_tanda0_r2b
O=bis/censos/controles_S0-4a-bis.txt; O0=bis/censos/tanda0_S0-4a-bis.txt
c() { PYTHONDONTWRITEBYTECODE=1 "$PY" -B s0_4/scripts/cmp_dirs.py "$@"; }
{
echo "Tanda 0 de S0-4a-bis: cada corrida (scripts/correr_tanda0_par.py de S0-4a, los diez TOs del manifiesto tanda0_10tos.json) contra salida_tanda0_r2b/ del repo (en la copia), byte a byte (s0_4/scripts/cmp_dirs.py). Código: impl4bis (sin interruptores) o proto4bis (S0_4_REGLAS)."
for x in t0_bis_final:TODAS t0_bis_off:ninguna t0_bis_sinmax:todas_menos_sdmax t0_bis_sdmax:sdmax t0_bis_sd_sdmax:sd,sdmax t0_bis_final2:TODAS_segunda; do
  echo "${x%%:*} [${x##*:}]: $(c bis/corridas/${x%%:*} $T0 | head -1)"; done
echo "t0_bis_final2 contra t0_bis_final: $(c bis/corridas/t0_bis_final2 bis/corridas/t0_bis_final | head -1)"
} > "$O0"
{
echo "Controles de configuración de S0-4a-bis sobre los 152 (s0_4/scripts/cmp_dirs.py, byte a byte, los 768 archivos del primer nivel; cada corrida se armó con herr/juntar_por_to.py desde la corrida sin manual y la de manual)"
echo "regla prendida, final (impl4bis) contra S0-4a final (corridas/final): $(c bis/corridas/bis_final corridas/final | tr '\n' ' ')"
echo "regla apagada (proto4bis, todas menos sdmax) contra S0-4a final: $(c bis/corridas/bis_sinmax corridas/final | head -1)"
echo "todo apagado (proto4bis, S0_4_REGLAS=\"\") contra S1 (corridas/base): $(c bis/corridas/bis_off corridas/base | head -1)"
echo "todo apagado contra los sha256 de los 768 archivos e0/ de s1/manifest_salida.json (ee7c07c; la copia no trae s1/e0/): $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B bis/scripts/contra_manifiesto_s1.py bis/corridas/bis_off copia/data/experiment/segmentacion_oficial_e0r2/s1/manifest_salida.json)"
echo "doble corrida: bis_final2 contra bis_final (impl4bis): $(c bis/corridas/bis_final2 bis/corridas/bis_final | head -1)"
echo "prototipo (proto4bis, TODAS) contra el código sin interruptores (bis_final), en los 64 TOs que cambian contra S1: $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B bis/scripts/por_to_iguales.py bis/corridas/bis_proto bis/corridas/bis_final "$(cat trabajo/tos_cambian_final.txt)")"
echo "tanda 0 dentro de los 152 (bis_final): $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B s0_4/scripts/control_tanda0_en_152.py bis/corridas/bis_final $T0)"
echo "tanda 0 dentro de los 152 (bis_final2): $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B s0_4/scripts/control_tanda0_en_152.py bis/corridas/bis_final2 $T0)"
echo "medición de ri_oc, referencia (proto4bis, TODAS, solo ri_oc) contra bis_final: $(PYTHONDONTWRITEBYTECODE=1 "$PY" -B bis/scripts/por_to_iguales.py bis/corridas/oc_ref bis/corridas/bis_final ri_oc)"
} > "$O"
cat "$O0" "$O"
